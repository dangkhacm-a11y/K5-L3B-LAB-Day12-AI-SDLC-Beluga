"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Nhóm viết tiếp (PRD-0 mục F, Quán):
  TODO(nhóm, lát 3): khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu, kiên nhẫn,
                     bỏ đi (customer_left), no_dish, vòng đời khách.
  TODO(nhóm, lát 4): interact tại bếp/bàn (cook_started, dish_ready, dish_picked, served),
                     ăn xong trả tiền (paid), boa, uy tín, hết ca (quan_end).
"""

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity
import math

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = float(scenario.get("reputation", t["reputation_initial"]))
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = []
        for c in scenario.get("customers", []):
            dish = c.get("dish") or c.get("dish_id")
            pmax = c.get("patience_max_ticks", c.get("patience_ticks", int(round(t["patience_s"] * TICK))))
            cust = dict(c,
                        dish=dish,
                        reserved=c.get("reserved", {}),
                        state=c.get("state", "waiting"),
                        patience_ticks=c.get("patience_ticks", pmax),
                        patience_max_ticks=pmax,
                        eat_ticks_left=c.get("eat_ticks_left", 0))
            self.customers.append(cust)
            ids.reserve(cust["id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def _find_interact_target(self):
        """Tìm đối tượng tương tác trong interact_radius:
        Ưu tiên: khoảng cách gần nhất -> bếp (0) trước bàn (1) -> id nhỏ trước.
        """
        radius = self.t["interact_radius"]
        candidates = []
        for s in self.stoves:
            d = math.dist(self.pos, s["pos"])
            if d <= radius:
                candidates.append((d, 0, id_key(s["id"]), "stove", s))
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= radius:
                candidates.append((d, 1, id_key(tb["id"]), "table", tb))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        return candidates[0]

    def _can_cook(self, dish_name):
        recipe = self.menu[dish_name]["recipe"]
        return all(self.stock.get(ing, 0) >= qty for ing, qty in recipe.items())

    def _deduct_stock(self, dish_name):
        recipe = self.menu[dish_name]["recipe"]
        for ing, qty in recipe.items():
            self.stock[ing] -= qty

    def step(self, inp):
        events = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Cập nhật bếp (stoves)
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
                if s["cook_ticks_left"] == 0:
                    s["state"] = "ready"
                    s["ready_ticks"] = 0
                    events.append(("dish_ready", {"stove_id": s["id"], "dish": s["dish"]}))
            elif s["state"] == "ready":
                s["ready_ticks"] += 1

        # 2. Cập nhật khách (customers): ăn uống & thanh toán / kiên nhẫn
        remaining_customers = []
        for c in sort_by_id(self.customers):
            if c.get("state") == "eating":
                c["eat_ticks_left"] = max(0, c.get("eat_ticks_left", 0) - 1)
                if c["eat_ticks_left"] == 0:
                    dish = c["dish"]
                    price = self.menu.get(dish, {}).get("price", 0)
                    patience_ratio = c.get("patience_ratio", 1.0)
                    min_ratio = self.t.get("tip_min_patience_ratio", 0.5)
                    if patience_ratio >= min_ratio:
                        tip = int(round(price * self.t.get("tip_rate", 0.2)))
                        self.reputation = min(self.t["reputation_max"], round(self.reputation + self.t["tip_reputation"], 3))
                    else:
                        tip = 0
                    total = price + tip
                    self.money += total
                    self.earned += total
                    self.shift_earned += total
                    events.append(("paid", {
                        "customer_id": c["id"],
                        "table_id": c["table_id"],
                        "dish": dish,
                        "price": price,
                        "tip": tip,
                        "total": total,
                        "reputation": self.reputation
                    }))
                    continue
            elif c.get("state") == "waiting":
                c["patience_ticks"] = max(0, c.get("patience_ticks", int(round(self.t["patience_s"] * TICK))) - 1)
                if c["patience_ticks"] == 0:
                    delta = self.t.get("left_reputation_delta", -0.5)
                    self.reputation = max(self.t.get("reputation_min", 0.0), round(self.reputation + delta, 3))
                    events.append(("customer_left", {
                        "customer_id": c["id"],
                        "table_id": c["table_id"],
                        "dish": c.get("dish"),
                        "reputation": self.reputation,
                        "reason": "patience_expired"
                    }))
                    continue
            remaining_customers.append(c)
        self.customers = remaining_customers

        # 3. Di chuyển người chơi
        self._move(inp)

        # 4. Tương tác interact (tối đa một mục tiêu)
        if inp.pressed("interact"):
            target = self._find_interact_target()
            if target:
                kind = target[3]
                obj = target[4]
                if kind == "stove":
                    if obj["state"] == "ready" and self.hand is None:
                        self.hand = obj["dish"]
                        dish = obj["dish"]
                        obj["state"] = "idle"
                        obj["dish"] = None
                        obj["cook_ticks_left"] = 0
                        obj["ready_ticks"] = 0
                        events.append(("dish_picked", {"stove_id": obj["id"], "dish": dish}))
                    elif obj["state"] == "idle" and self.hand is None:
                        dish_to_cook = None
                        for c in sort_by_id(self.customers):
                            if c.get("state") == "waiting" and c.get("dish"):
                                if self._can_cook(c["dish"]):
                                    dish_to_cook = c["dish"]
                                    break
                        if not dish_to_cook:
                            for dname in sorted(self.menu.keys()):
                                if self._can_cook(dname):
                                    dish_to_cook = dname
                                    break
                        if dish_to_cook:
                            self._deduct_stock(dish_to_cook)
                            obj["state"] = "cooking"
                            obj["dish"] = dish_to_cook
                            obj["cook_ticks_left"] = int(round(self.menu[dish_to_cook]["cook_s"] * TICK))
                            obj["ready_ticks"] = 0
                            events.append(("cook_started", {"stove_id": obj["id"], "dish": dish_to_cook}))
                elif kind == "table":
                    customer = next((c for c in self.customers if c.get("table_id") == obj["id"]), None)
                    if customer and customer.get("state") == "waiting" and self.hand is not None:
                        if self.hand == customer.get("dish"):
                            dish = self.hand
                            self.hand = None
                            customer["state"] = "eating"
                            customer["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
                            pmax = customer.get("patience_max_ticks", int(round(self.t["patience_s"] * TICK)))
                            pcur = customer.get("patience_ticks", pmax)
                            customer["patience_ratio"] = (pcur / pmax) if pmax > 0 else 1.0
                            events.append(("served", {
                                "customer_id": customer["id"],
                                "table_id": obj["id"],
                                "dish": dish
                            }))

        # 5. Hết ca
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
