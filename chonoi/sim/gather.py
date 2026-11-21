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
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, weapon_level=0):
        t = tuning["gather"]
        self.t = t
        self.freshness = tuning.get("freshness", {
            "initial": 100.0, "gather_decay_per_s": 0.0, "spoiled_below": 30.0,
        })
        self.rng = streams
        self.ids = ids
        self.day = int(day)
        self.weapon_tiers = {
            int(tier["level"]): tier
            for tier in tuning.get("shop", {}).get("upgrades", {}).get("weapon", [])
        }
        self.weapon_enabled = "weapon_cooldown_s" in t and bool(self.weapon_tiers)
        self.weapon_level = int(weapon_level)
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
        self.attack_cd_ticks = p.get("attack_cd_ticks", 0)
        self.hold = []
        for entry in scenario.get("hold", []):
            if isinstance(entry, dict):
                item = dict(entry)
            else:  # Compatibility with v1.0/1.1 in-process count fixtures until adapter v1.2 lands.
                item = self._new_item(str(entry))
            self.hold.append(item)
        for item in self.hold:
            ids.reserve(item["id"])
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        self.current_cfg = t.get("current", {
            "interval_ticks": 600, "duration_ticks": 120, "warning_ticks": 60,
            "min_depth": 10.0, "speed": 1.0,
        })
        self.random_current = scenario.get("random_current", True)
        self.current_override = scenario.get("current_direction")
        self._validate_current_config()
        self.current_direction = None
        self.current_ticks_left = 0
        self.current_warning_direction = None
        self.current_rng = streams.get("river_current")
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
        mcfg = t.get("monsters", {})
        self.monster_species = mcfg.get("species", {})
        if "monsters" in scenario:
            src_monsters = scenario["monsters"]
        else:
            src_monsters = [s for s in mcfg.get("spawns", []) if s.get("from_day", 1) <= self.day]
        self.monsters = [self._build_monster(m) for m in src_monsters]
        for coll in (self.nodes, self.fish, self.monsters):
            for e in coll:
                ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> list:
        return [dict(item) for item in self.hold]

    def snapshot(self) -> dict:
        player = {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                  "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                  "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                  "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                  "at_surface": self._at_surface()}
        if self.weapon_enabled:
            player["attack_cd_ticks"] = self.attack_cd_ticks
        return {
            "player": player,
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "current": (None if self.current_direction is None else {
                "direction": self.current_direction, "ticks_left": self.current_ticks_left,
            }),
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"]}
                     for f in sort_by_id(self.fish)],
            "monsters": [{"id": m["id"], "kind": m["kind"], "pos": m["pos"], "waypoints": m["waypoints"],
                          "target_idx": m["target_idx"], "state": m["state"],
                          "state_ticks_left": m["state_ticks_left"], "recoil_dir": m["recoil_dir"]}
                         for m in sort_by_id(self.monsters)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        self.attack_cd_ticks = max(0, self.attack_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        self._decay_hold(events)
        self._update_current(events)
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
            self._faint("choke", events)
            return events
        # 2.4. Lao xua nếu bật mở rộng weapon (TICKET-02 §3, §4.5)
        if inp.pressed("attack"):
            self._try_weapon_attack(events)
        # 2.5. cập nhật quái theo id rồi xét tối đa một hit (TICKET-02 §4.5)
        if self._update_monsters(events):
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
            self.hold.extend(self._new_item(kind) for _ in range(added))
        return added

    def _validate_current_config(self):
        """Reject schedules that cannot fit into one current cycle."""
        interval = int(self.current_cfg["interval_ticks"])
        duration = int(self.current_cfg["duration_ticks"])
        warning = int(self.current_cfg["warning_ticks"])
        if interval <= 0 or duration <= 0 or duration > interval or warning < 0 or warning > interval:
            raise ValueError("gather.current requires 0 < duration_ticks <= interval_ticks and 0 <= warning_ticks <= interval_ticks")
        override = self.current_override
        if override is not None and override not in (-1, 1):
            raise ValueError("scenario.current_direction must be -1, 1, or null")

    def _new_item(self, kind: str) -> dict:
        return {
            "id": self.ids.new("I"),
            "kind": kind,
            "fresh": float(self.freshness["initial"]),
        }

    def _decay_hold(self, events):
        decay = float(self.freshness["gather_decay_per_s"]) / TICK
        spoiled, kept = [], []
        for item in self.hold:
            item["fresh"] = max(0.0, round(float(item["fresh"]) - decay, 12))
            if item["fresh"] < self.freshness["spoiled_below"]:
                spoiled.append(item)
            else:
                kept.append(item)
        self.hold = kept
        for item in sort_by_id(spoiled):
            events.append(("spoiled", {
                "item_id": item["id"], "kind": item["kind"], "location": "hold",
            }))

    def _update_current(self, events):
        if self.current_direction is not None:
            self.current_ticks_left -= 1
            if self.current_ticks_left <= 0:
                self.current_direction = None
                self.current_ticks_left = 0

        if not self.random_current:
            return

        interval = int(self.current_cfg["interval_ticks"])
        warning = int(self.current_cfg["warning_ticks"])
        cycle_tick = self.phase_tick % interval
        if warning > 0 and cycle_tick == interval - warning:
            direction = self.current_override
            if direction is None:
                direction = self.current_rng.choice((-1, 1))
            self.current_warning_direction = direction
            events.append(("current_warning", {"direction": direction, "ticks_left": warning}))

        if cycle_tick == 0:
            direction = self.current_warning_direction
            if direction is None:
                direction = self.current_override
            if direction is None:
                direction = self.current_rng.choice((-1, 1))
            self.current_direction = direction
            self.current_ticks_left = int(self.current_cfg["duration_ticks"])
            self.current_warning_direction = None

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
        self.hold.extend(self._new_item(fish["kind"]) for _ in range(qty))
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

    @staticmethod
    def _build_monster(m: dict) -> dict:
        rdir = m.get("recoil_dir")
        if rdir is not None:
            dx, dd = float(rdir[0]), float(rdir[1])
            norm = math.hypot(dx, dd)
            rdir = [dx / norm, dd / norm] if norm > 0.0 else [1.0, 0.0]
        return {
            "id": m["id"],
            "kind": m["kind"],
            "pos": [float(c) for c in m["pos"]],
            "waypoints": [[float(c) for c in wp] for wp in m["waypoints"]],
            "target_idx": int(m.get("target_idx", 1)),
            "state": m.get("state", "patrol"),
            "state_ticks_left": int(m.get("state_ticks_left", 0)),
            "recoil_dir": rdir,
        }

    def _clamp_monster(self, m: dict, sp: dict):
        xlo, xhi = self.t["bounds"]["x"]
        dlo, dhi = sp["depths"]
        m["pos"][0] = min(xhi, max(xlo, m["pos"][0]))
        m["pos"][1] = min(dhi, max(dlo, m["pos"][1]))

    def _faint(self, cause: str, events):
        remaining = [self.hold.pop() for _ in range(len(self.hold))]
        events.append(("faint", {"cause": cause, "hp": 0, "lost": remaining, "pos": list(self.pos)}))
        self._finish("fainted", events)

    def _try_weapon_attack(self, events):
        """Mở rộng Lao xua (weapon): cần cấp >= 1, hồi 180 tick kể cả trượt, đẩy 3m và choáng 120/180 bước."""
        if not self.weapon_enabled or self.weapon_level < 1 or self.attack_cd_ticks > 0:
            return
        tier = self.weapon_tiers.get(self.weapon_level)
        if tier is None:
            return
        self.attack_cd_ticks = int(round(self.t["weapon_cooldown_s"] * TICK))
        radius = float(tier["weapon_radius"])
        stun_ticks = int(round(float(tier["stun_s"]) * TICK))
        push_dist = float(self.t.get("weapon_push_dist", 3.0))
        hit_ids = []
        stun_events = []
        for m in sort_by_id(self.monsters):
            d = math.dist(self.pos, m["pos"])
            if d > radius:
                continue
            sp = self.monster_species[m["kind"]]
            dx = m["pos"][0] - self.pos[0]
            dd = m["pos"][1] - self.pos[1]
            if d == 0.0:
                ux, ud = 1.0, 0.0
            else:
                ux, ud = dx / d, dd / d
            m["pos"][0] += ux * push_dist
            m["pos"][1] += ud * push_dist
            self._clamp_monster(m, sp)
            m["state"] = "stunned"
            m["state_ticks_left"] = stun_ticks
            m["recoil_dir"] = None
            hit_ids.append(m["id"])
            stun_events.append(("monster_stunned", {
                "monster_id": m["id"],
                "pos": list(m["pos"]),
                "stun_ticks": stun_ticks,
            }))
        events.append(("attack", {"pos": list(self.pos), "monster_ids": hit_ids}))
        events.extend(stun_events)

    def _update_monsters(self, events) -> bool:
        """Cập nhật quái theo id rồi xét tối đa một hit. Trả True nếu người chơi ngất."""
        if not self.monsters:
            return False
        eligible = []
        for m in sort_by_id(self.monsters):
            sp = self.monster_species[m["kind"]]
            state = m["state"]
            if state == "stunned":
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"] = "patrol"
                    m["state_ticks_left"] = 0
                    m["recoil_dir"] = None
                continue
            if state == "recoil":
                step_dist = sp["recoil_dist"] / sp["recoil_ticks"]
                m["pos"][0] += m["recoil_dir"][0] * step_dist
                m["pos"][1] += m["recoil_dir"][1] * step_dist
                self._clamp_monster(m, sp)
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"] = "patrol"
                    m["state_ticks_left"] = 0
                    m["recoil_dir"] = None
                continue

            # patrol / chase: xét chuyển trạng thái rồi di chuyển
            dlo = sp["depths"][0]
            player_in_zone = self.pos[1] >= dlo
            dist_to_player = math.dist(m["pos"], self.pos)
            if state == "patrol":
                if player_in_zone and dist_to_player <= sp["detect_radius"]:
                    m["state"] = "chase"
            elif state == "chase":
                if (not player_in_zone) or dist_to_player > sp["exit_radius"]:
                    m["state"] = "patrol"

            if m["state"] == "chase":
                step_dist = sp["chase_speed"] / TICK
                dx = self.pos[0] - m["pos"][0]
                dd = self.pos[1] - m["pos"][1]
                d = math.hypot(dx, dd)
                if d > 0.0:
                    move = min(step_dist, d)
                    m["pos"][0] += (dx / d) * move
                    m["pos"][1] += (dd / d) * move
            else:
                step_dist = sp["patrol_speed"] / TICK
                wp = m["waypoints"][m["target_idx"]]
                dx = wp[0] - m["pos"][0]
                dd = wp[1] - m["pos"][1]
                d = math.hypot(dx, dd)
                if d <= step_dist + 1e-9:
                    m["pos"][0] = wp[0]
                    m["pos"][1] = wp[1]
                    m["target_idx"] = 1 - m["target_idx"]
                else:
                    m["pos"][0] += (dx / d) * step_dist
                    m["pos"][1] += (dd / d) * step_dist
            self._clamp_monster(m, sp)
            eligible.append((m, sp))

        if self.invuln_ticks > 0:
            return False

        best = None
        best_key = None
        for m, sp in eligible:
            if self.pos[1] < sp["depths"][0]:
                continue
            d = math.dist(m["pos"], self.pos)
            if d <= sp["hit_radius"]:
                k = (d, id_key(m["id"]))
                if best_key is None or k < best_key:
                    best = (m, sp)
                    best_key = k
        if best is None:
            return False

        m, sp = best
        mcfg = self.t["monsters"]
        self.hp = max(0, self.hp - 1)
        drop_count = int(math.floor(len(self.hold) * mcfg["loss_ratio"]))
        lost = [self.hold.pop() for _ in range(drop_count)]
        self.invuln_ticks = int(mcfg["invuln_ticks"])

        dx = m["pos"][0] - self.pos[0]
        dd = m["pos"][1] - self.pos[1]
        d_vec = math.hypot(dx, dd)
        m["state"] = "recoil"
        m["state_ticks_left"] = int(sp["recoil_ticks"])
        m["recoil_dir"] = [1.0, 0.0] if d_vec == 0.0 else [dx / d_vec, dd / d_vec]

        events.append(("monster_hit", {
            "monster_id": m["id"],
            "hp": self.hp,
            "lost": lost,
            "pos": list(self.pos),
        }))
        if self.hp <= 0:
            self._faint("monster", events)
            return True
        return False

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if self.current_direction is not None and self.pos[1] >= self.current_cfg["min_depth"]:
            self.vel[0] += self.current_direction * self.current_cfg["speed"]
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
