"""Buổi sáng — Lặn & Hái (`gather`). KHUNG: bơi, chặn mép, đồng hồ, cập bến, xuất kho.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Đã làm sẵn để smoke test chạy được: bơi + tăng/giảm tốc, chặn mép (d không âm), đồng hồ và hết giờ,
cập bến (`interact` trong vùng bến -> `gather_end` reason `docked`), xuất kho, snapshot đầy đủ trường gather.

Nhóm viết tiếp (đúng thứ tự một bước trong PRD mục 13.8, "Gather"):
  TODO(nhóm, lát 1): bơi + oxy + biên + giỏ
      - oxy: dưới nước (d > surface_depth) trừ 1 tick/tick, mặt nước hồi oxygen_refill_per_tick, kẹp [0, max]
      - ngạt: oxy = 0 và đang dưới nước -> đếm zero_oxy_ticks, đủ choke_interval_ticks thì -1 Máu (choke)
      - Máu về 0 -> ngất (faint, gather_end reason `fainted`, mất toàn bộ giỏ, kho rỗng)
      - sự kiện dive / surface / oxygen_empty / choke / faint
      - giỏ: thứ tự nhặt (LIFO), sức chứa hold_capacity
  TODO(nhóm, lát 2): hái + bắt cá + cập bến + kho
      - hái nút ở mặt nước (gather, hold_full), nút mọc lại (node_regrown đã có phần đếm ngược)
      - bắt đàn cá bằng `catch` (fish_caught, hold_full, hồi chiêu catch_cd_ticks, chỉ khi dưới nước)
      - cập bến xét TRƯỚC hái (đã có); ghi kho đúng một lần do runner lo
Các tính năng của phase sau chưa nằm trong khung này.
"""

import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        self.random_fish = scenario.get("random_fish", True)
        self.fish_turn_rng = streams.get("fish_turn")
        self.fish_spawn_rng = streams.get("fish_spawn")
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        if "fish" in scenario:
            src_fish = scenario["fish"]
        elif self.random_fish:
            src_fish = t["fish_initial"]
        else:
            src_fish = []
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": f.get("heading_deg", 0), "age_ticks": f.get("age_ticks", 0)}
                     for f in src_fish]
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"]}
                     for f in sort_by_id(self.fish)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # 2. bơi + chặn mép
        was_at_surface = self._at_surface()
        self._move(inp)
        at_surface = self._at_surface()
        if was_at_surface and not at_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_at_surface and at_surface:
            events.append(("surface", {"pos": list(self.pos)}))

        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
        else:
            previous_oxygen = self.oxygen_ticks
            self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
            if previous_oxygen > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"pos": list(self.pos)}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
                    self.zero_oxy_ticks = 0
                    self.hp = max(0, self.hp - 1)
                    events.append(("choke", {"hp": self.hp, "pos": list(self.pos)}))
            else:
                self.zero_oxy_ticks = 0
        if self.hp <= 0:
            self.hold.clear()
            events.append(("faint", {"pos": list(self.pos)}))
            self._finish("fainted", events)
            return events
        # 3. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if at_surface:
                self._try_gather_node(events)
        # 4. bắt cá
        if inp.pressed("catch"):
            if self.catch_cd_ticks == 0 and not at_surface:
                self._try_catch_fish(events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
        elif self.random_fish:
            self._advance_fish(events)
        return events

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _nearest_ready_node(self):
        radius = self.t["interact_radius"]
        best = None
        best_key = None
        for n in self.nodes:
            if n["regrow_ticks"] > 0:
                continue
            d = math.dist(self.pos, n["pos"])
            if d <= radius:
                k = (d, id_key(n["id"]))
                if best_key is None or k < best_key:
                    best = n
                    best_key = k
        return best

    def _nearest_fish(self):
        radius = self.t["catch_radius"]
        best = None
        best_key = None
        for f in self.fish:
            d = math.dist(self.pos, f["pos"])
            if d <= radius:
                k = (d, id_key(f["id"]))
                if best_key is None or k < best_key:
                    best = f
                    best_key = k
        return best

    def _add_to_hold(self, kind: str, qty: int) -> int:
        cap = int(self.t["hold_capacity"])
        space = max(0, cap - len(self.hold))
        added = min(qty, space)
        if added > 0:
            self.hold.extend([kind] * added)
        return added

    def _try_gather_node(self, events):
        node = self._nearest_ready_node()
        if node is None:
            return
        qty = int(self.t["node_yield"])
        added = self._add_to_hold(node["kind"], qty)
        if added == 0:
            events.append(("hold_full", {
                "kind": node["kind"],
                "hold_count": len(self.hold),
                "hold_capacity": int(self.t["hold_capacity"]),
            }))
            return
        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
        events.append(("gather", {
            "node_id": node["id"],
            "kind": node["kind"],
            "count": added,
            "hold_count": len(self.hold),
        }))
        if added < qty:
            events.append(("hold_full", {
                "kind": node["kind"],
                "hold_count": len(self.hold),
                "hold_capacity": int(self.t["hold_capacity"]),
            }))

    def _try_catch_fish(self, events):
        fish = self._nearest_fish()
        if fish is None:
            return
        qty = int(self.t["fish_yield"][fish["kind"]])
        space = int(self.t["hold_capacity"]) - len(self.hold)
        if space < qty:
            events.append(("hold_full", {
                "kind": fish["kind"],
                "hold_count": len(self.hold),
                "hold_capacity": int(self.t["hold_capacity"]),
            }))
            return
        self.hold.extend([fish["kind"]] * qty)
        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
        self.fish = [f for f in self.fish if f["id"] != fish["id"]]
        events.append(("fish_caught", {
            "fish_id": fish["id"],
            "kind": fish["kind"],
            "count": qty,
            "hold_count": len(self.hold),
        }))

    def _advance_fish(self, events):
        speed = self.t["fish_speed"] / TICK
        for fish in sort_by_id(self.fish):
            fish["age_ticks"] += 1
            if fish["age_ticks"] % self.t["fish_turn_ticks"] == 0:
                fish["heading_deg"] = self.fish_turn_rng.random() * 360.0
            angle = math.radians(fish["heading_deg"])
            vx, vd = math.cos(angle) * speed, math.sin(angle) * speed
            xlo, xhi = self.t["fish_x"]
            dlo, dhi = self.t["fish_depths"][fish["kind"]]
            fish["pos"][0], vx = self._reflect_axis(fish["pos"][0], vx, xlo, xhi)
            fish["pos"][1], vd = self._reflect_axis(fish["pos"][1], vd, dlo, dhi)
            fish["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360.0

        if self.phase_tick % self.t["fish_spawn_ticks"] == 0 and len(self.fish) < self.t["fish_max"]:
            self._spawn_fish(events)

    @staticmethod
    def _reflect_axis(position, delta, lower, upper):
        """Di chuyển một tick và phản xạ phần quãng đường còn lại ở hai đầu dải."""
        position += delta
        if position < lower:
            position = lower + (lower - position)
            delta = abs(delta)
        elif position > upper:
            position = upper - (position - upper)
            delta = -abs(delta)
        return position, delta

    def _spawn_fish(self, events):
        clearance = self.t["fish_spawn_clearance"]
        candidates = {}
        for kind in sorted(self.t["fish_weights"]):
            positions = []
            for x in self.t["fish_spawn_x"]:
                for d in self.t["fish_spawn_depths"][kind]:
                    pos = [float(x), float(d)]
                    if all(math.dist(pos, live["pos"]) > clearance for live in self.fish):
                        positions.append(pos)
            if positions:
                candidates[kind] = positions
        if not candidates:
            return

        total_weight = sum(self.t["fish_weights"][kind] for kind in candidates)
        choice = self.fish_spawn_rng.random() * total_weight
        kind = next(iter(candidates))
        for candidate_kind in candidates:
            choice -= self.t["fish_weights"][candidate_kind]
            if choice < 0:
                kind = candidate_kind
                break
        pos = candidates[kind][self.fish_spawn_rng.randrange(len(candidates[kind]))]
        fish = {"id": self.ids.new("F"), "kind": kind, "pos": pos,
                "heading_deg": self.fish_spawn_rng.random() * 360.0, "age_ticks": 0}
        self.fish.append(fish)
        events.append(("fish_spawned", {"id": fish["id"], "kind": kind, "pos": list(pos)}))

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
