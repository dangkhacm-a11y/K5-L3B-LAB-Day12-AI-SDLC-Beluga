"""Buổi tối — khách, giữ chỗ, bếp và phục vụ theo TICKET-02 / PRD D–F.

Kho gồm cả nguyên liệu đang giữ chỗ; chỉ trừ kho khi bắt đầu nấu.
Mỗi món gắn với một đơn qua {order_id, dish_id, base_price}.
"""

import math
from copy import deepcopy
from decimal import Decimal

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import validate_items
from ..scenario import _validate_quan
from .ramp import ramp_velocity


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, *, allowed_dishes=None):
        _validate_quan(scenario, tuning)
        self.t = tuning["quan"]
        self.menu = tuning["menu"]
        if allowed_dishes is not None:
            if (not isinstance(allowed_dishes, (dict, list, tuple, set, frozenset))
                    or any(not isinstance(dish_id, str) or dish_id not in self.menu
                           for dish_id in allowed_dishes)):
                raise BadInput("allowed_dishes phải chứa các id món có trong menu")
            # Chỉ lọc ID; số suất kế hoạch không giới hạn lượt gọi món.
            self.menu = {dish_id: self.menu[dish_id] for dish_id in sorted(allowed_dishes)}
        self.hz = tuning["tick_hz"]
        self.rng = streams
        self.ids = ids
        self.tick = 0
        self.next_customer_tick = self.t["first_customer_tick"]
        self.random_customers = scenario.get("random_customers", True)
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        self.stock = validate_items(inventory if inventory is not None else scenario.get("stock", {}))
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", self.t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.time_left_ticks = scenario.get("time_left_ticks", self._ticks(self.t["duration_s"]))
        self.reputation = scenario.get("reputation", self.t["reputation_initial"])
        self.stoves = self._merge(self.t["stoves"], scenario.get("stoves", []))
        self.tables = self._merge(self.t["tables"], scenario.get("tables", []))
        for stove in self.stoves:
            stove.setdefault("state", "idle")
            stove.setdefault("dish", None)
            stove.setdefault("cook_ticks_left", 0)
            stove.setdefault("ready_ticks", 0)
        self.hand = deepcopy(scenario.get("hand"))
        self.customers = []
        for source in sorted(scenario.get("customers", []), key=self._order_key):
            dish_id = source["dish_id"]
            if dish_id not in self.menu:
                raise BadInput(f"customers.{source['id']}: món ngoài kế hoạch ngày")
            state = source.get("state", "waiting")
            status = source.get("order_status", "reserved")
            if (state == "eating") != (status == "served"):
                raise BadInput(f"customers.{source['id']}: state/order_status mâu thuẫn")
            reserved = self.menu[dish_id]["recipe"] if status == "reserved" else {}
            if "reserved" in source and source["reserved"] != reserved:
                raise BadInput(f"customers.{source['id']}: reserved không khớp đơn/công thức")
            customer = {"id": source["id"], "table_id": source["table_id"], "dish_id": dish_id,
                        "order_tick": source.get("order_tick", 0), "state": state, "order_status": status,
                        "patience_ticks_left": source.get("patience_ticks_left", self._ticks(self.t["patience_s"])),
                        "eat_ticks_left": source.get("eat_ticks_left", 0), "reserved": dict(reserved),
                        "base_price": source.get("base_price", 0), "tip": source.get("tip", 0)}
            if state == "eating":
                if (customer["eat_ticks_left"] <= 0 or customer["base_price"] <= 0
                        or "base_price" not in source or "tip" not in source):
                    raise BadInput(f"customers.{source['id']}: eating cần timer dương và base_price/tip")
            elif customer["eat_ticks_left"] != 0 or customer["tip"] != 0:
                raise BadInput(f"customers.{source['id']}: khách chờ có timer ăn/boa")
            self.customers.append(customer)
            ids.reserve(customer["id"])
        if any(qty < 0 for qty in self._unreserved_stock().values()):
            raise BadInput("khách giữ chỗ vượt quá kho")
        self._validate_food()
        self.money = self.earned = self.shift_earned = 0
        self.done = False
        self.reason = None

    def _ticks(self, seconds):
        return int(round(seconds * self.hz))

    @staticmethod
    def _order_key(customer):
        return customer.get("order_tick", 0), id_key(customer["table_id"])

    @staticmethod
    def _merge(defaults, updates):
        by_id = {obj["id"]: deepcopy(obj) for obj in defaults}
        for update in updates:
            if update["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {update['id']}")
            by_id[update["id"]].update(deepcopy(update))
        return sort_by_id(list(by_id.values()))

    def _validate_food(self):
        assigned = {c["id"]: c for c in self.customers if c["order_status"] == "assigned"}
        food = []
        for stove in self.stoves:
            state = stove["state"]
            if state == "idle":
                if stove["dish"] is not None or stove["cook_ticks_left"] != 0 or stove["ready_ticks"] != 0:
                    raise BadInput(f"stoves.{stove['id']}: idle có món/timer")
                continue
            if (state not in ("cooking", "ready") or stove["dish"] is None
                    or state == "cooking" and (stove["cook_ticks_left"] <= 0 or stove["ready_ticks"] != 0)
                    or state == "ready" and stove["cook_ticks_left"] != 0):
                raise BadInput(f"stoves.{stove['id']}: state/dish/timer mâu thuẫn")
            food.append(stove["dish"])
        if self.hand is not None:
            food.append(self.hand)
        seen = set()
        for dish in food:
            owner = dish["order_id"]
            if owner not in assigned or owner in seen:
                raise BadInput("món không khớp đúng một đơn assigned")
            customer = assigned[owner]
            if (dish["dish_id"] != customer["dish_id"]
                    or customer["base_price"] not in (0, dish["base_price"])):
                raise BadInput("dish_id/base_price của món và khách không khớp")
            customer["base_price"] = dish["base_price"]
            seen.add(owner)
        if seen != set(assigned):
            raise BadInput("mỗi đơn assigned cần đúng một món tại bếp hoặc trên tay")

    def _unreserved_stock(self):
        available = dict(self.stock)
        for customer in self.customers:
            for kind, qty in customer["reserved"].items():
                available[kind] = available.get(kind, 0) - qty
        return available

    def available_stock(self):
        return {kind: qty for kind, qty in sorted(self._unreserved_stock().items()) if qty > 0}

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return deepcopy({
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: qty for k, qty in sorted(self.stock.items()) if qty > 0},
            "hand": self.hand,
            "stoves": sort_by_id(self.stoves),
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])}
                       for tb in sort_by_id(self.tables)],
            "customers": sort_by_id(self.customers),
        })

    def step(self, inp):
        if self.done:
            return []
        self.tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        events = []
        # F: timers/chín -> di chuyển/interact -> quyết toán -> hết ca hoặc khách mới.
        for customer in self.customers:
            key = "eat_ticks_left" if customer["state"] == "eating" else "patience_ticks_left"
            customer[key] = max(0, customer[key] - 1)
        for stove in sort_by_id(self.stoves):
            if stove["state"] == "ready":
                stove["ready_ticks"] += 1
            elif stove["state"] == "cooking":
                stove["cook_ticks_left"] = max(0, stove["cook_ticks_left"] - 1)
                if stove["cook_ticks_left"] == 0:
                    stove.update(state="ready", ready_ticks=0)
                    events.append(("dish_ready", self._food_event(stove)))
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        self._settle_customers(events)
        if self.time_left_ticks == 0:
            self.done, self.reason = True, "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                       "shift_earned": self.shift_earned, "reputation": self.reputation}))
        elif self.random_customers and self.tick == self.next_customer_tick:
            self.next_customer_tick += self._ticks(self.t["customer_interval_s"])
            self._arrive(events)
        return events

    def _find_interact_target(self):
        candidates = []
        for priority, objects in enumerate((self.stoves, self.tables)):
            for obj in objects:
                distance = math.dist(self.pos, obj["pos"])
                if distance <= self.t["interact_radius"]:
                    candidates.append((distance, priority, id_key(obj["id"]), obj))
        return min(candidates, key=lambda item: item[:3]) if candidates else None

    @staticmethod
    def _food_event(stove):
        dish = stove["dish"]
        return {"stove_id": stove["id"], "order_id": dish["order_id"], "dish_id": dish["dish_id"]}

    @staticmethod
    def _clear_stove(stove):
        stove.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)

    def _interact(self, events):
        target = self._find_interact_target()
        if target is None:
            return
        _, priority, _, obj = target
        if priority == 0:
            if self.hand is not None:
                return
            if obj["state"] == "ready":
                events.append(("dish_picked", self._food_event(obj)))
                self.hand = obj["dish"]
                self._clear_stove(obj)
            elif obj["state"] == "idle":
                waiting = [c for c in self.customers if c["order_status"] == "reserved"]
                if not waiting:
                    return
                customer = min(waiting, key=self._order_key)
                items = []
                for kind, qty in sorted(customer["reserved"].items()):
                    self.stock[kind] -= qty
                    items.extend([kind] * qty)
                dish_id = customer["dish_id"]
                price = self.menu[dish_id]["price"]
                customer.update(order_status="assigned", reserved={}, base_price=price)
                obj.update(state="cooking", dish={"order_id": customer["id"], "dish_id": dish_id, "base_price": price},
                           cook_ticks_left=self._ticks(self.menu[dish_id]["cook_s"]), ready_ticks=0)
                events.append(("cook_started", {**self._food_event(obj), "items": items, "base_price": price}))
        elif self.hand is not None:
            customer = next((c for c in self.customers if c["table_id"] == obj["id"]
                             and c["id"] == self.hand["order_id"] and c["state"] == "waiting"
                             and c["order_status"] == "assigned" and c["dish_id"] == self.hand["dish_id"]), None)
            if customer is None:
                return
            price = self.hand["base_price"]
            ratio = customer["patience_ticks_left"] / self._ticks(self.t["patience_s"])
            tip = (math.floor(Decimal(price) * Decimal(str(self.t["tip_rate"])))
                   if ratio >= self.t["tip_min_patience_ratio"] else 0)
            customer.update(state="eating", order_status="served", base_price=price, tip=tip,
                            eat_ticks_left=self._ticks(self.t["eat_s"]))
            self.hand = None
            events.append(("served", {"order_id": customer["id"], "table_id": customer["table_id"],
                "dish_id": customer["dish_id"], "patience_ticks_left": customer["patience_ticks_left"],
                "base_price": price, "tip": tip}))

    def _change_reputation(self, delta):
        value = float(Decimal(str(self.reputation)) + Decimal(str(delta)))
        self.reputation = min(self.t["reputation_max"], max(self.t["reputation_min"], value))

    def _remove_customer(self, customer):
        for stove in self.stoves:
            if stove["dish"] is not None and stove["dish"]["order_id"] == customer["id"]:
                self._clear_stove(stove)
        if self.hand is not None and self.hand["order_id"] == customer["id"]:
            self.hand = None
        self.customers.remove(customer)

    def _settle_customers(self, events):
        closing = self.time_left_ticks == 0
        for customer in sort_by_id(self.customers, key=lambda c: c["table_id"]):
            if customer["state"] == "eating":
                if customer["eat_ticks_left"] > 0 and not closing:
                    continue
                amount = customer["base_price"] + customer["tip"]
                self.money += amount
                self.earned += amount
                self.shift_earned += amount
                if customer["tip"] > 0:
                    self._change_reputation(self.t["tip_reputation"])
                events.append(("paid", {"order_id": customer["id"], "table_id": customer["table_id"],
                    "base_price": customer["base_price"], "tip": customer["tip"], "amount": amount,
                    "reason": "finished_eating" if customer["eat_ticks_left"] == 0 else "closing"}))
            elif customer["patience_ticks_left"] == 0 or closing:
                if not closing:
                    self._change_reputation(self.t["left_reputation_delta"])
                events.append(("customer_left", {"order_id": customer["id"], "table_id": customer["table_id"],
                    "reason": "closing" if closing else "patience", "reputation": self.reputation}))
            else:
                continue
            self._remove_customer(customer)

    def _arrive(self, events):
        occupied = {c["table_id"] for c in self.customers}
        table = next((tb for tb in sort_by_id(self.tables) if tb["id"] not in occupied), None)
        if table is None:
            return
        available = self.available_stock()
        dishes = [dish_id for dish_id in sorted(self.menu)
                  if all(available.get(kind, 0) >= qty for kind, qty in self.menu[dish_id]["recipe"].items())]
        if not dishes:
            events.append(("no_dish", {}))
            return
        dish_id = self.rng.get("customer_order").choice(dishes)
        customer = {"id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish_id,
                    "order_tick": self.tick, "state": "waiting", "order_status": "reserved",
                    "reserved": dict(self.menu[dish_id]["recipe"]),
                    "patience_ticks_left": self._ticks(self.t["patience_s"]),
                    "eat_ticks_left": 0, "base_price": 0, "tip": 0}
        self.customers.append(customer)
        events.append(("customer_arrived", {"order_id": customer["id"], "table_id": table["id"], "dish_id": dish_id}))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t["ramp_max_ticks"]))
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / self.hz
            lo, hi = self.t["bounds"][axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
