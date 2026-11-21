"""Buổi tối — khách, độ tươi cá thể, giữ chỗ theo ID, đặt trước, bếp và phục vụ (TICKET-02 / TICKET-03).

Hỗ trợ song song:
- v1.1 (kho đếm dict): giữ tương thích 100% với test Phase 1–2 khi chưa bật `freshness`.
- v1.2 (kho cá thể `[{"id","kind","fresh"}]` + độ tươi chính xác bằng `Fraction` + `reservations` + `burn_s`).
"""

from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import KINDS_P1, validate_items
from ..scenario import _validate_quan
from .ramp import ramp_velocity

DEFAULT_FRESHNESS = {
    "initial": 100,
    "gather_decay_per_s": 0.5,
    "quan_decay_per_s": 0.25,
    "spoiled_below": 30,
}

DEFAULT_RESERVATIONS = {
    "count": 2,
    "table_hold_s": 30,
    "price_multiplier": 1.5,
    "failed_reputation_delta": -1,
}

QUAN_V12_KEYS = {
    "player", "stock", "hand", "stoves", "tables", "customers",
    "random_customers", "reservations", "random_reservations",
    "reputation", "time_left_ticks",
}


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _to_fraction(v) -> Fraction:
    return Fraction(str(v))


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, *, allowed_dishes=None, reservations=None):
        self.item_mode = (
            "freshness" in tuning
            or isinstance(inventory, list)
            or isinstance(scenario.get("stock"), list)
        )
        self.reservations_enabled = (
            "reservations" in tuning
            or reservations is not None
            or "reservations" in scenario
            or "random_reservations" in scenario
        )
        if not self.item_mode and not self.reservations_enabled:
            _validate_quan(scenario, tuning)
        else:
            self._validate_scenario_v12(scenario, tuning)

        self.t = tuning["quan"]
        self.menu = tuning["menu"]
        if allowed_dishes is not None:
            if (not isinstance(allowed_dishes, (dict, list, tuple, set, frozenset))
                    or any(not isinstance(dish_id, str) or dish_id not in self.menu
                           for dish_id in allowed_dishes)):
                raise BadInput("allowed_dishes phải chứa các id món có trong menu")
            self.menu = {dish_id: self.menu[dish_id] for dish_id in sorted(allowed_dishes)}

        self.hz = tuning["tick_hz"]
        self.rng = streams
        self.ids = ids
        self.allowed_dishes = None
        self.tick = 0
        self.next_customer_tick = self.t["first_customer_tick"]
        self.random_customers = scenario.get("random_customers", True)
        self.random_reservations = scenario.get("random_reservations", True)

        fcfg = dict(DEFAULT_FRESHNESS, **tuning.get("freshness", {}))
        self.spoiled_below = _to_fraction(fcfg["spoiled_below"])
        self.decay_per_tick = _to_fraction(fcfg["quan_decay_per_s"]) / Fraction(self.hz)

        rcfg = dict(DEFAULT_RESERVATIONS, **tuning.get("reservations", {}))
        self.res_cfg = rcfg
        self.res_hold_ticks = self._ticks(rcfg["table_hold_s"])
        self.res_price_mult = _to_fraction(rcfg["price_multiplier"])

        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")

        raw_stock = inventory if inventory is not None else scenario.get("stock", [] if self.item_mode else {})
        if self.item_mode:
            self.stock = self._load_item_stock(raw_stock)
        else:
            self.stock = validate_items(raw_stock)

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

        # Dựng đơn đặt trước (nếu bật)
        self.reservations = []
        self._initial_events = []
        if self.reservations_enabled:
            self._init_reservations(scenario, reservations)

        # Dựng khách hàng từ scenario
        self.customers = []
        self._init_customers(scenario)

        if not self.item_mode and any(qty < 0 for qty in self._unreserved_stock().values()):
            raise BadInput("khách giữ chỗ vượt quá kho")
        self._validate_food()
        self.money = self.earned = self.shift_earned = 0
        self.done = False
        self.reason = None

    # --- nạp & kiểm tra v1.2 ---------------------------------------------------
    def _validate_scenario_v12(self, b, tuning):
        if not isinstance(b, dict):
            raise BadInput("khối quan phải là object")
        extra = set(b) - QUAN_V12_KEYS
        if extra:
            raise BadInput(f"trường lạ trong quan: {sorted(extra)}")
        q = tuning["quan"]
        for key in ("random_customers", "random_reservations"):
            if key in b and not isinstance(b[key], bool):
                raise BadInput(f"{key} phải là boolean")
        rep = b.get("reputation", q["reputation_initial"])
        if not _is_num(rep) or not (q["reputation_min"] <= rep <= q["reputation_max"]):
            raise BadInput("reputation ngoài miền")
        if "time_left_ticks" in b:
            t = b["time_left_ticks"]
            dur = int(round(q["duration_s"] * tuning["tick_hz"]))
            if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
                raise BadInput("time_left_ticks ngoài thời lượng ca")
        p = b.get("player", {})
        if not isinstance(p, dict) or set(p) - {"pos", "vel"}:
            raise BadInput("quan.player chỉ có pos và vel")
        qb = q["bounds"]
        if "pos" in p:
            pos = p["pos"]
            if not (isinstance(pos, list) and len(pos) == 2 and all(_is_num(c) for c in pos)):
                raise BadInput("player.pos phải là [x, z]")
            if not (qb["x"][0] <= pos[0] <= qb["x"][1] and qb["z"][0] <= pos[1] <= qb["z"][1]):
                raise BadInput("player.pos ngoài phòng")
        if "vel" in p:
            vel = p["vel"]
            if not (isinstance(vel, list) and len(vel) == 2 and all(_is_num(c) for c in vel)):
                raise BadInput("player.vel phải là [x, z]")
        table_ids = [c.get("table_id") for c in b.get("customers", [])]
        if len(table_ids) != len(set(table_ids)):
            raise BadInput("hai khách cùng bàn")

    def _load_item_stock(self, raw_stock):
        if isinstance(raw_stock, dict):
            raise BadInput("contract v1.2 yêu cầu kho dạng mảng cá thể [{id,kind,fresh}]")
        if not isinstance(raw_stock, list):
            raise BadInput("stock phải là mảng cá thể")
        items = []
        seen_ids = set()
        for entry in raw_stock:
            if not isinstance(entry, dict) or set(entry) != {"id", "kind", "fresh"}:
                raise BadInput("mỗi cá thể kho phải có đúng khóa id, kind, fresh")
            ident, kind, fresh = entry["id"], entry["kind"], entry["fresh"]
            if not isinstance(ident, str) or not ident or ident in seen_ids:
                raise BadInput(f"id cá thể không hợp lệ hoặc trùng: {ident!r}")
            if kind not in KINDS_P1:
                raise BadInput(f"nguyên liệu lạ: {kind!r}")
            if not _is_num(fresh) or not (0 <= fresh <= 100):
                raise BadInput(f"fresh của {ident} phải nằm trong [0, 100]")
            seen_ids.add(ident)
            self.ids.reserve(ident)
            items.append({"id": ident, "kind": kind, "_fresh": _to_fraction(fresh)})
        return items

    def _init_reservations(self, scenario, passed_reservations):
        dur_ticks = self._ticks(self.t["duration_s"])
        known_tables = {tb["id"] for tb in self.tables}
        src = passed_reservations if passed_reservations is not None else scenario.get("reservations")
        if src is not None:
            if not isinstance(src, list) or len(src) > int(self.res_cfg["count"]):
                raise BadInput(f"reservations tối đa {self.res_cfg['count']} đơn")
            seen_ids, seen_tables = set(), set()
            for r in src:
                if not isinstance(r, dict):
                    raise BadInput("reservation phải là object")
                rid = r.get("id")
                tid = r.get("table_id")
                did = r.get("dish_id")
                arr = r.get("arrival_tick")
                state = r.get("state", "scheduled")
                if not isinstance(rid, str) or not rid or rid in seen_ids:
                    raise BadInput(f"reservation id không hợp lệ hoặc trùng: {rid!r}")
                if not isinstance(tid, str) or tid not in known_tables or tid in seen_tables:
                    raise BadInput(f"reservation.{rid}: table_id không hợp lệ hoặc trùng bàn")
                if not isinstance(did, str) or did not in self.menu:
                    raise BadInput(f"reservation.{rid}: dish_id ngoài menu/kế hoạch")
                if isinstance(arr, bool) or not isinstance(arr, int) or not (1 <= arr < dur_ticks):
                    raise BadInput(f"reservation.{rid}: arrival_tick phải nguyên trong [1, {dur_ticks - 1}]")
                if state not in ("scheduled", "holding", "waiting", "served", "failed"):
                    raise BadInput(f"reservation.{rid}: state không hợp lệ")
                seen_ids.add(rid)
                seen_tables.add(tid)
                self.ids.reserve(rid)
                self.reservations.append({
                    "id": rid, "table_id": tid, "dish_id": did,
                    "arrival_tick": arr, "state": state,
                })
        elif self.random_reservations:
            count = min(int(self.res_cfg["count"]), len(self.tables))
            rng = self.rng.get("reservations")
            tables_pool = [tb["id"] for tb in sort_by_id(self.tables)]
            dishes_pool = sorted(self.menu)
            lo_tick = min(1800, dur_ticks - 1)
            for _ in range(count):
                if not tables_pool or not dishes_pool:
                    break
                t_idx = rng.randrange(len(tables_pool))
                table_id = tables_pool.pop(t_idx)
                dish_id = rng.choice(dishes_pool)
                arrival_tick = rng.randrange(lo_tick, dur_ticks)
                rid = self.ids.new("R")
                self.reservations.append({
                    "id": rid, "table_id": table_id, "dish_id": dish_id,
                    "arrival_tick": arrival_tick, "state": "scheduled",
                })

        # Giữ bàn từ max(0, arrival_tick - hold_ticks); nếu giữ từ tick 0 -> thể hiện ngay ở snapshot tick 0
        for r in sort_by_id(self.reservations):
            if r["state"] == "scheduled" and max(0, r["arrival_tick"] - self.res_hold_ticks) == 0:
                r["state"] = "holding"
            if passed_reservations is None:
                self._initial_events.append(("reservation_announced", {
                    "reservation_id": r["id"], "table_id": r["table_id"],
                    "dish_id": r["dish_id"], "arrival_tick": r["arrival_tick"],
                }))

    def initial_events(self):
        return list(self._initial_events)

    def _init_customers(self, scenario):
        known_tables = {tb["id"] for tb in self.tables}
        res_by_id = {r["id"]: r for r in self.reservations}
        used_item_ids = set()
        stock_by_id = {it["id"]: it for it in self.stock} if self.item_mode else {}

        for source in sorted(scenario.get("customers", []), key=self._order_key):
            cid = source.get("id")
            tid = source.get("table_id")
            dish_id = source.get("dish_id")
            if not isinstance(cid, str) or not cid:
                raise BadInput("customer cần id hợp lệ")
            if not isinstance(tid, str) or tid not in known_tables:
                raise BadInput(f"customers.{cid}: table_id không tồn tại")
            if dish_id not in self.menu:
                raise BadInput(f"customers.{cid}: món ngoài kế hoạch ngày")
            state = source.get("state", "waiting")
            status = source.get("order_status", "reserved")
            if state not in ("waiting", "eating") or status not in ("reserved", "assigned", "unfulfillable", "served"):
                raise BadInput(f"customers.{cid}: state/order_status không hợp lệ")
            if (state == "eating") != (status == "served"):
                raise BadInput(f"customers.{cid}: state/order_status mâu thuẫn")
            res_id = source.get("reservation_id")
            if res_id is not None and res_id not in res_by_id:
                raise BadInput(f"customers.{cid}: reservation_id không tồn tại")

            if self.item_mode:
                if status == "reserved":
                    if "reserved" in source:
                        r_ids = source["reserved"]
                        if not isinstance(r_ids, list) or len(r_ids) != len(set(r_ids)):
                            raise BadInput(f"customers.{cid}: reserved phải là mảng id duy nhất")
                        counts = {}
                        for iid in r_ids:
                            if not isinstance(iid, str) or iid not in stock_by_id:
                                raise BadInput(f"customers.{cid}: reserved chứa id không có trong kho ({iid!r})")
                            if iid in used_item_ids:
                                raise BadInput(f"customers.{cid}: cá thể {iid} bị dùng chung giữa hai đơn")
                            it = stock_by_id[iid]
                            if it["_fresh"] < self.spoiled_below:
                                raise BadInput(f"customers.{cid}: cá thể {iid} đã ươn")
                            counts[it["kind"]] = counts.get(it["kind"], 0) + 1
                            used_item_ids.add(iid)
                        if counts != self.menu[dish_id]["recipe"]:
                            raise BadInput(f"customers.{cid}: reserved không khớp công thức món")
                        reserved = sorted(r_ids, key=id_key)
                    else:
                        picked = self._pick_freshest_items(self.menu[dish_id]["recipe"], extra_used=used_item_ids)
                        if picked is None:
                            raise BadInput(f"customers.{cid}: kho không đủ cá thể tươi để giữ chỗ")
                        used_item_ids.update(picked)
                        reserved = picked
                else:
                    if "reserved" in source and source["reserved"]:
                        raise BadInput(f"customers.{cid}: trạng thái {status} không được có reserved")
                    reserved = []
            else:
                expected = self.menu[dish_id]["recipe"] if status == "reserved" else {}
                if "reserved" in source and source["reserved"] != expected:
                    raise BadInput(f"customers.{cid}: reserved không khớp đơn/công thức")
                reserved = dict(expected)

            customer = {
                "id": cid, "table_id": tid, "dish_id": dish_id,
                "order_tick": source.get("order_tick", 0), "state": state, "order_status": status,
                "patience_ticks_left": source.get("patience_ticks_left", self._ticks(self.t["patience_s"])),
                "eat_ticks_left": source.get("eat_ticks_left", 0), "reserved": reserved,
                "base_price": source.get("base_price", 0), "tip": source.get("tip", 0),
            }
            if self.reservations_enabled or res_id is not None:
                customer["reservation_id"] = res_id
            if state == "eating":
                if (customer["eat_ticks_left"] <= 0 or customer["base_price"] <= 0
                        or "base_price" not in source or "tip" not in source):
                    raise BadInput(f"customers.{cid}: eating cần timer dương và base_price/tip")
            elif customer["eat_ticks_left"] != 0 or customer["tip"] != 0:
                raise BadInput(f"customers.{cid}: khách chờ có timer ăn/boa")
            self.customers.append(customer)
            self.ids.reserve(cid)

    # --- tiện ích ---------------------------------------------------------------
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

    def _reserved_item_ids(self):
        ids = set()
        for c in self.customers:
            if isinstance(c["reserved"], list):
                ids.update(c["reserved"])
        return ids

    def _pick_freshest_items(self, recipe, extra_used=()):
        """Chọn cá thể khả dụng (chưa ươn, chưa bị giữ) tươi nhất, hòa theo id nhỏ."""
        used = self._reserved_item_ids() | set(extra_used)
        by_kind = {}
        for it in self.stock:
            if it["id"] in used or it["_fresh"] < self.spoiled_below:
                continue
            by_kind.setdefault(it["kind"], []).append(it)
        picked = []
        for kind, qty in sorted(recipe.items()):
            pool = by_kind.get(kind, [])
            if len(pool) < qty:
                return None
            pool.sort(key=lambda it: (-it["_fresh"], id_key(it["id"])))
            picked.extend(it["id"] for it in pool[:qty])
        return sorted(picked, key=id_key)

    def _unreserved_stock(self):
        if self.item_mode:
            used = self._reserved_item_ids()
            counts = {}
            for it in self.stock:
                if it["id"] not in used and it["_fresh"] >= self.spoiled_below:
                    counts[it["kind"]] = counts.get(it["kind"], 0) + 1
            return counts
        available = dict(self.stock)
        for customer in self.customers:
            for kind, qty in customer["reserved"].items():
                available[kind] = available.get(kind, 0) - qty
        return available

    def available_stock(self):
        return {kind: qty for kind, qty in sorted(self._unreserved_stock().items()) if qty > 0}

    def _can_reserve(self, recipe):
        if self.item_mode:
            return self._pick_freshest_items(recipe) is not None
        avail = self.available_stock()
        return all(avail.get(kind, 0) >= qty for kind, qty in recipe.items())

    def _reserve_for(self, recipe):
        if self.item_mode:
            return self._pick_freshest_items(recipe)
        return dict(recipe) if self._can_reserve(recipe) else None

    def _find_reservation(self, res_id):
        return next((r for r in self.reservations if r["id"] == res_id), None)

    def _export_stock(self):
        if self.item_mode:
            return [{"id": it["id"], "kind": it["kind"], "fresh": float(it["_fresh"])}
                    for it in sort_by_id(self.stock)]
        return {k: qty for k, qty in sorted(self.stock.items()) if qty > 0}

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        table_res = {}
        if self.reservations_enabled:
            for r in self.reservations:
                if r["state"] in ("holding", "waiting"):
                    table_res[r["table_id"]] = r["id"]
        tables_out = []
        for tb in sort_by_id(self.tables):
            entry = {"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])}
            if self.reservations_enabled:
                entry["reservation_id"] = table_res.get(tb["id"])
            tables_out.append(entry)

        customers_out = []
        for c in sort_by_id(self.customers):
            item = deepcopy(c)
            if self.item_mode:
                item["reserved"] = sorted(item["reserved"], key=id_key)
            if self.reservations_enabled and "reservation_id" not in item:
                item["reservation_id"] = None
            customers_out.append(item)

        snap = {
            "player": {"pos": list(self.pos), "vel": list(self.vel)},
            "stock": self._export_stock(),
            "hand": deepcopy(self.hand),
            "stoves": deepcopy(sort_by_id(self.stoves)),
            "tables": tables_out,
            "customers": customers_out,
        }
        if self.reservations_enabled:
            snap["reservations"] = [deepcopy(r) for r in sort_by_id(self.reservations)]
        return snap

    # --- một bước (TICKET-03 §1) -----------------------------------------------
    def step(self, inp):
        if self.done:
            return []
        self.tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        events = []

        # 1. đồng hồ và timer khách
        for customer in self.customers:
            key = "eat_ticks_left" if customer["state"] == "eating" else "patience_ticks_left"
            customer[key] = max(0, customer[key] - 1)

        # 2. hao tươi kho thô -> phát hết spoiled theo id -> xử lý giữ chỗ bị ươn
        if self.item_mode:
            self._decay_and_spoil(events)

        # 3. xét món chín / cháy theo id bếp
        self._step_stoves(events)

        # 4. di chuyển và tối đa một tương tác
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)

        # 5. thanh toán, kiên nhẫn / đóng ca
        self._settle_customers(events)

        # 6. đóng ca hoặc đặt trước (theo id) rồi tới khách thường
        if self.time_left_ticks == 0:
            self.done, self.reason = True, "time"
            events.append(("quan_end", {
                "reason": "time", "money": self.money, "earned": self.earned,
                "shift_earned": self.shift_earned, "reputation": self.reputation,
            }))
        else:
            if self.reservations_enabled:
                self._step_reservations(events)
            if self.random_customers and self.tick == self.next_customer_tick:
                self.next_customer_tick += self._ticks(self.t["customer_interval_s"])
                self._arrive(events)
        return events

    def _decay_and_spoil(self, events):
        newly_spoiled = set()
        for it in sort_by_id(self.stock):
            was_fresh = it["_fresh"] >= self.spoiled_below
            it["_fresh"] = max(Fraction(0), it["_fresh"] - self.decay_per_tick)
            if was_fresh and it["_fresh"] < self.spoiled_below:
                newly_spoiled.add(it["id"])
                events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": "stock"}))

        if not newly_spoiled:
            return

        affected = [
            c for c in self.customers
            if c["order_status"] == "reserved" and any(iid in newly_spoiled for iid in c["reserved"])
        ]
        for customer in sorted(affected, key=self._order_key):
            customer["reserved"] = []
            picked = self._pick_freshest_items(self.menu[customer["dish_id"]]["recipe"])
            if picked is not None:
                customer["reserved"] = picked
            elif customer.get("reservation_id") is not None:
                res = self._find_reservation(customer["reservation_id"])
                if res is not None:
                    self._fail_reservation(res, "stock", events)
            else:
                customer["order_status"] = "unfulfillable"

    def _step_stoves(self, events):
        burn_s = self.t.get("burn_s")
        burn_ticks = self._ticks(burn_s) if burn_s is not None else None
        for stove in sort_by_id(self.stoves):
            if stove["state"] == "ready":
                stove["ready_ticks"] += 1
                if burn_ticks is not None and stove["ready_ticks"] > burn_ticks:
                    dish = stove["dish"]
                    stove_id = stove["id"]
                    self._clear_stove(stove)
                    owner = next((c for c in self.customers if c["id"] == dish["order_id"]), None)
                    if owner is not None and owner.get("reservation_id") is not None:
                        events.append(("dish_burnt", {
                            "stove_id": stove_id, "order_id": dish["order_id"],
                            "dish_id": dish["dish_id"], "order_status": "failed",
                        }))
                        res = self._find_reservation(owner["reservation_id"])
                        if res is not None:
                            self._fail_reservation(res, "burnt", events)
                    elif owner is not None:
                        owner["base_price"] = 0
                        picked = self._reserve_for(self.menu[owner["dish_id"]]["recipe"])
                        if picked is not None:
                            owner["order_status"] = "reserved"
                            owner["reserved"] = picked
                        else:
                            owner["order_status"] = "unfulfillable"
                            owner["reserved"] = [] if self.item_mode else {}
                        events.append(("dish_burnt", {
                            "stove_id": stove_id, "order_id": dish["order_id"],
                            "dish_id": dish["dish_id"], "order_status": owner["order_status"],
                        }))
            elif stove["state"] == "cooking":
                stove["cook_ticks_left"] = max(0, stove["cook_ticks_left"] - 1)
                if stove["cook_ticks_left"] == 0:
                    stove.update(state="ready", ready_ticks=0)
                    events.append(("dish_ready", self._food_event(stove)))

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
                dish_id = customer["dish_id"]
                list_price = self.menu[dish_id]["price"]
                if self.item_mode:
                    consume_ids = set(customer["reserved"])
                    consumed = [it for it in self.stock if it["id"] in consume_ids]
                    self.stock = [it for it in self.stock if it["id"] not in consume_ids]
                    consumed.sort(key=lambda it: (it["kind"], id_key(it["id"])))
                    avg_fresh = sum(it["_fresh"] for it in consumed) / len(consumed)
                    price = math.floor(Fraction(list_price) * avg_fresh / Fraction(100))
                    items = [{"id": it["id"], "kind": it["kind"], "fresh": float(it["_fresh"])} for it in consumed]
                    customer.update(order_status="assigned", reserved=[], base_price=price)
                else:
                    items = []
                    for kind, qty in sorted(customer["reserved"].items()):
                        self.stock[kind] -= qty
                        items.extend([kind] * qty)
                    price = list_price
                    customer.update(order_status="assigned", reserved={}, base_price=price)
                obj.update(
                    state="cooking",
                    dish={"order_id": customer["id"], "dish_id": dish_id, "base_price": price},
                    cook_ticks_left=self._ticks(self.menu[dish_id]["cook_s"]),
                    ready_ticks=0,
                )
                events.append(("cook_started", {**self._food_event(obj), "items": items, "base_price": price}))
        elif self.hand is not None:
            customer = next((c for c in self.customers if c["table_id"] == obj["id"]
                             and c["id"] == self.hand["order_id"] and c["state"] == "waiting"
                             and c["order_status"] == "assigned" and c["dish_id"] == self.hand["dish_id"]), None)
            if customer is None:
                return
            price = self.hand["base_price"]
            res_id = customer.get("reservation_id")
            if res_id is not None:
                price = math.floor(Fraction(price) * self.res_price_mult)
            ratio = Fraction(customer["patience_ticks_left"], self._ticks(self.t["patience_s"]))
            tip = (math.floor(Fraction(price) * Fraction(str(self.t["tip_rate"])))
                   if ratio >= Fraction(str(self.t["tip_min_patience_ratio"])) else 0)
            customer.update(
                state="eating", order_status="served", base_price=price, tip=tip,
                eat_ticks_left=self._ticks(self.t["eat_s"]),
            )
            self.hand = None
            events.append(("served", {
                "order_id": customer["id"], "table_id": customer["table_id"],
                "dish_id": customer["dish_id"], "patience_ticks_left": customer["patience_ticks_left"],
                "base_price": price, "tip": tip,
            }))
            if res_id is not None:
                res = self._find_reservation(res_id)
                if res is not None:
                    res["state"] = "served"
                events.append(("reservation_served", {
                    "reservation_id": res_id, "order_id": customer["id"], "base_price": price,
                }))

    def _change_reputation(self, delta):
        value = float(Decimal(str(self.reputation)) + Decimal(str(delta)))
        self.reputation = min(self.t["reputation_max"], max(self.t["reputation_min"], value))

    def _remove_customer(self, customer):
        for stove in self.stoves:
            if stove["dish"] is not None and stove["dish"]["order_id"] == customer["id"]:
                self._clear_stove(stove)
        if self.hand is not None and self.hand["order_id"] == customer["id"]:
            self.hand = None
        if customer in self.customers:
            self.customers.remove(customer)

    def _fail_reservation(self, res, reason, events):
        if res["state"] in ("served", "failed"):
            return
        res["state"] = "failed"
        owner = next((c for c in self.customers if c.get("reservation_id") == res["id"]), None)
        if owner is not None:
            owner["reserved"] = [] if self.item_mode else {}
            self._remove_customer(owner)
        self._change_reputation(self.res_cfg["failed_reputation_delta"])
        events.append(("reservation_failed", {
            "reservation_id": res["id"], "reason": reason, "reputation": self.reputation,
        }))

    def _settle_customers(self, events):
        closing = self.time_left_ticks == 0
        for customer in sort_by_id(list(self.customers), key=lambda c: c["table_id"]):
            if customer["state"] == "eating":
                if customer["eat_ticks_left"] > 0 and not closing:
                    continue
                amount = customer["base_price"] + customer["tip"]
                self.money += amount
                self.earned += amount
                self.shift_earned += amount
                if customer["tip"] > 0:
                    self._change_reputation(self.t["tip_reputation"])
                events.append(("paid", {
                    "order_id": customer["id"], "table_id": customer["table_id"],
                    "base_price": customer["base_price"], "tip": customer["tip"], "amount": amount,
                    "reason": "finished_eating" if customer["eat_ticks_left"] == 0 else "closing",
                }))
                self._remove_customer(customer)
            elif customer["patience_ticks_left"] == 0 and not closing:
                if customer.get("reservation_id") is not None:
                    res = self._find_reservation(customer["reservation_id"])
                    if res is not None:
                        self._fail_reservation(res, "patience", events)
                else:
                    self._change_reputation(self.t["left_reputation_delta"])
                    events.append(("customer_left", {
                        "order_id": customer["id"], "table_id": customer["table_id"],
                        "reason": "patience", "reputation": self.reputation,
                    }))
                    self._remove_customer(customer)
            elif closing:
                if customer.get("reservation_id") is None:
                    events.append(("customer_left", {
                        "order_id": customer["id"], "table_id": customer["table_id"],
                        "reason": "closing", "reputation": self.reputation,
                    }))
                    self._remove_customer(customer)

        if closing and self.reservations_enabled:
            for res in sort_by_id(self.reservations):
                if res["state"] not in ("served", "failed"):
                    self._fail_reservation(res, "closing", events)

    def _step_reservations(self, events):
        for res in sort_by_id(self.reservations):
            if res["state"] in ("served", "failed", "waiting"):
                continue
            hold_start = max(0, res["arrival_tick"] - self.res_hold_ticks)
            if res["state"] == "scheduled" and hold_start <= self.tick < res["arrival_tick"]:
                res["state"] = "holding"
            if self.tick >= res["arrival_tick"]:
                occupied = any(c["table_id"] == res["table_id"] for c in self.customers)
                if occupied:
                    self._fail_reservation(res, "occupied", events)
                    continue
                picked = self._reserve_for(self.menu[res["dish_id"]]["recipe"])
                if picked is None:
                    self._fail_reservation(res, "stock", events)
                    continue
                res["state"] = "waiting"
                customer = {
                    "id": self.ids.new("C"), "table_id": res["table_id"], "dish_id": res["dish_id"],
                    "order_tick": self.tick, "state": "waiting", "order_status": "reserved",
                    "reserved": picked, "patience_ticks_left": self._ticks(self.t["patience_s"]),
                    "eat_ticks_left": 0, "base_price": 0, "tip": 0, "reservation_id": res["id"],
                }
                self.customers.append(customer)
                events.append(("reservation_arrived", {"reservation_id": res["id"], "order_id": customer["id"]}))
                events.append(("customer_arrived", {
                    "order_id": customer["id"], "table_id": res["table_id"], "dish_id": res["dish_id"],
                }))

    def _arrive(self, events):
        occupied = {c["table_id"] for c in self.customers}
        held = {r["table_id"] for r in self.reservations if r["state"] == "holding"}
        table = next((tb for tb in sort_by_id(self.tables)
                      if tb["id"] not in occupied and tb["id"] not in held), None)
        if table is None:
            return
        menu_dishes = self.allowed_dishes if self.allowed_dishes is not None else self.menu
        dishes = [dish_id for dish_id in sorted(menu_dishes)
                  if self._can_reserve(self.menu[dish_id]["recipe"])]
        if not dishes:
            events.append(("no_dish", {}))
            return
        dish_id = self.rng.get("customer_order").choice(dishes)
        reserved = self._reserve_for(self.menu[dish_id]["recipe"])
        customer = {
            "id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish_id,
            "order_tick": self.tick, "state": "waiting", "order_status": "reserved",
            "reserved": reserved, "patience_ticks_left": self._ticks(self.t["patience_s"]),
            "eat_ticks_left": 0, "base_price": 0, "tip": 0,
        }
        if self.reservations_enabled:
            customer["reservation_id"] = None
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
