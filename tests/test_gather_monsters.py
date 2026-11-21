"""Unit & headless tests cho Phase 2 Thành viên 2: Cá Sấu Năm Chèo, va chạm, recoil, bất tử và ngất."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.gather import GatherSim

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def _step_gather(scenario, frame_list=(), ticks=1, seed=1):
    tuning = load_contract()["tuning"]
    sess = Session("gather", tuning, scenario, seed)
    player = InputPlayer(list(frame_list))
    all_events = []
    while sess.tick < ticks and not sess.done:
        inp = player.advance(sess.tick)
        all_events.extend(sess.step(inp))
    return sess, all_events


class CrocodileSpawnAndPatrolTests(unittest.TestCase):
    def test_default_spawns_by_day_and_standalone_gather(self):
        tuning = load_contract()["tuning"]
        # gather độc lập dùng bố trí Ngày 1: chỉ có M1
        sess = Session("gather", tuning, {}, seed=1)
        monsters = sess.snapshot()["monsters"]
        self.assertEqual([m["id"] for m in monsters], ["M1"])
        self.assertEqual(monsters[0]["pos"], [60.0, 24.0])
        self.assertEqual(monsters[0]["waypoints"], [[60.0, 24.0], [64.0, 24.0]])
        self.assertEqual(monsters[0]["state"], "patrol")
        self.assertEqual(monsters[0]["target_idx"], 1)

        # Ngày 3 có thêm M2 ở [85, 18] <-> [89, 18]
        sim_d3 = GatherSim(tuning, {}, Streams(1), IdAllocator(), day=3)
        m_d3 = sim_d3.snapshot()["monsters"]
        self.assertEqual([m["id"] for m in m_d3], ["M1", "M2"])
        self.assertEqual(m_d3[1]["pos"], [85.0, 18.0])
        self.assertEqual(m_d3[1]["waypoints"], [[85.0, 18.0], [89.0, 18.0]])

    def test_patrol_speed_and_waypoint_flip(self):
        sc = {"player": {"pos": [2, 0]}, "random_fish": False}
        # M1 đi từ [60, 24] đến [64, 24] ở 1.0 m/s -> mất 240 tick
        sess, _ = _step_gather(sc, ticks=60)
        m1 = sess.snapshot()["monsters"][0]
        self.assertEqual(m1["state"], "patrol")
        self.assertAlmostEqual(m1["pos"][0], 61.0, places=5)
        self.assertAlmostEqual(m1["pos"][1], 24.0, places=5)
        self.assertEqual(m1["target_idx"], 1)

        # Chạy tiếp 180 tick (tổng 240): chạm [64, 24] và đảo sang target_idx=0 cho bước sau
        player = InputPlayer([])
        for _ in range(180):
            sess.step(player.advance(sess.tick))
        m1 = sess.snapshot()["monsters"][0]
        self.assertAlmostEqual(m1["pos"][0], 64.0, places=5)
        self.assertEqual(m1["target_idx"], 0)

        # Bước 241 bắt đầu đi ngược về [60, 24]
        sess.step(player.advance(sess.tick))
        m1 = sess.snapshot()["monsters"][0]
        self.assertLess(m1["pos"][0], 64.0)

    def test_chase_detection_and_exit_by_distance_and_depth(self):
        # Người chơi ở d >= 10 và cách <= 10m -> chuyển chase, bơi 3.0 m/s
        sc = {
            "player": {"pos": [50, 24]},  # cách M1 [60, 24] đúng 10.0 m
            "random_fish": False,
        }
        sess, _ = _step_gather(sc, ticks=1)
        m1 = sess.snapshot()["monsters"][0]
        self.assertEqual(m1["state"], "chase")
        self.assertAlmostEqual(m1["pos"][0], 60.0 - 3.0 / 60.0, places=5)

        # Nếu đang chase nhưng người chơi lên d < 10 -> lập tức về patrol
        sc_shallow = {
            "player": {"pos": [60, 9.9]},
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [60, 12],
                "waypoints": [[60, 24], [64, 24]], "target_idx": 1, "state": "chase",
            }],
        }
        sess_sh, _ = _step_gather(sc_shallow, ticks=1)
        self.assertEqual(sess_sh.snapshot()["monsters"][0]["state"], "patrol")

        # Nếu đang chase và cách > 16m -> về patrol
        sc_far = {
            "player": {"pos": [43.5, 24]},  # cách 16.5 m > 16 m
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [60, 24],
                "waypoints": [[60, 24], [64, 24]], "target_idx": 1, "state": "chase",
            }],
        }
        sess_far, _ = _step_gather(sc_far, ticks=1)
        self.assertEqual(sess_far.snapshot()["monsters"][0]["state"], "patrol")

    def test_monster_clamped_to_species_depth_and_map_bounds(self):
        sc = {
            "player": {"pos": [100, 10]},
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [99.99, 10.01],
                "waypoints": [[90, 12], [95, 12]], "target_idx": 1,
                "state": "recoil", "state_ticks_left": 10, "recoil_dir": [0.70710678, -0.70710678],
            }],
        }
        sess, _ = _step_gather(sc, ticks=5)
        m1 = sess.snapshot()["monsters"][0]
        self.assertLessEqual(m1["pos"][0], 100.0)
        self.assertGreaterEqual(m1["pos"][1], 10.0)


class CrocodileHitRecoilInvulnFaintTests(unittest.TestCase):
    def test_hit_drops_lifo_half_sets_invuln_and_recoil_60_steps(self):
        sc = {
            "player": {"pos": [60, 24], "hp": 3},
            "hold": ["ca_loc", "bong_sung", "ca_linh", "bong_dien_dien", "ca_keo"],  # 5 -> floor(5/2) = 2
            "random_fish": False,
        }
        # Tick 1: chạm trùng tâm -> mất 1 HP, rơi LIFO ["ca_keo", "bong_dien_dien"], invuln=90, recoil=60 hướng +x
        sess, evs = _step_gather(sc, ticks=1)
        hits = [e for e in evs if e["name"] == "monster_hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"]["monster_id"], "M1")
        self.assertEqual(hits[0]["data"]["hp"], 2)
        self.assertEqual(hits[0]["data"]["lost"], ["ca_keo", "bong_dien_dien"])
        self.assertEqual(hits[0]["data"]["pos"], [60.0, 24.0])

        snap = sess.snapshot()
        self.assertEqual(snap["player"]["hp"], 2)
        self.assertEqual(snap["player"]["invuln_ticks"], 90)
        self.assertEqual(snap["hold"], ["ca_loc", "bong_sung", "ca_linh"])
        m1 = snap["monsters"][0]
        self.assertEqual(m1["state"], "recoil")
        self.assertEqual(m1["state_ticks_left"], 60)
        self.assertEqual(m1["recoil_dir"], [1.0, 0.0])
        self.assertEqual(m1["pos"], [60.0, 24.0])  # recoil bắt đầu từ bước sau

        # Chạy đúng 60 bước recoil: di chuyển đúng +2.0m theo +x, không gây hit thêm, hết tick 60 về patrol
        player = InputPlayer([])
        recoil_evs = []
        for _ in range(60):
            recoil_evs.extend(sess.step(player.advance(sess.tick)))
        self.assertFalse(any(e["name"] == "monster_hit" for e in recoil_evs))
        m1_after = sess.snapshot()["monsters"][0]
        self.assertEqual(m1_after["state"], "patrol")
        self.assertEqual(m1_after["state_ticks_left"], 0)
        self.assertIsNone(m1_after["recoil_dir"])
        self.assertAlmostEqual(m1_after["pos"][0], 62.0, places=5)
        self.assertAlmostEqual(m1_after["pos"][1], 24.0, places=5)

    def test_invuln_blocks_monster_hit_and_recoil_for_90_ticks(self):
        # Đứng sát M1 với invuln_ticks=5: 4 bước đầu bất tử (4,3,2,1), bước 5 giảm về 0 -> bị hit
        sc = {
            "player": {"pos": [60, 24], "hp": 3, "invuln_ticks": 5},
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [60, 24],
                "waypoints": [[60, 24], [64, 24]], "target_idx": 1, "state": "chase",
            }],
        }
        sess, evs = _step_gather(sc, ticks=4)
        self.assertEqual([e["name"] for e in evs], [])
        self.assertEqual(sess.snapshot()["player"]["hp"], 3)
        self.assertEqual(sess.snapshot()["monsters"][0]["state"], "chase")  # không bị đẩy vào recoil

        # Bước thứ 5: invuln 1 -> 0 -> ăn hit
        evs5 = sess.step(InputPlayer([]).advance(sess.tick))
        self.assertEqual([e["name"] for e in evs5], ["monster_hit"])
        self.assertEqual(sess.snapshot()["player"]["hp"], 2)
        self.assertEqual(sess.snapshot()["monsters"][0]["state"], "recoil")

    def test_max_one_hit_per_tick_nearest_then_smallest_id(self):
        sc = {
            "player": {"pos": [60, 20], "hp": 3},
            "random_fish": False,
            "monsters": [
                {"id": "M10", "kind": "ca_sau", "pos": [59, 20],
                 "waypoints": [[58, 20], [62, 20]], "target_idx": 1, "state": "chase"},
                {"id": "M2", "kind": "ca_sau", "pos": [61, 20],
                 "waypoints": [[58, 20], [62, 20]], "target_idx": 1, "state": "chase"},
            ],
        }
        sess, evs = _step_gather(sc, ticks=1)
        hits = [e for e in evs if e["name"] == "monster_hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"]["monster_id"], "M2")
        by_id = {m["id"]: m for m in sess.snapshot()["monsters"]}
        self.assertEqual(by_id["M2"]["state"], "recoil")
        self.assertEqual(by_id["M10"]["state"], "chase")

    def test_fatal_monster_hit_emits_faint_and_ends_with_empty_inventory(self):
        sc = {
            "player": {"pos": [60, 24], "hp": 1},
            "hold": ["ca_loc", "bong_sung", "ca_linh", "ca_keo"],  # hit rơi 2 LIFO -> còn 2 -> faint mất nốt
            "random_fish": False,
        }
        sess, evs = _step_gather(sc, ticks=5)
        self.assertEqual([e["name"] for e in evs], ["monster_hit", "faint", "gather_end"])
        self.assertEqual(evs[0]["data"]["hp"], 0)
        self.assertEqual(evs[0]["data"]["lost"], ["ca_keo", "ca_linh"])
        self.assertEqual(evs[1]["data"]["cause"], "monster")
        self.assertEqual(evs[1]["data"]["hp"], 0)
        self.assertEqual(evs[1]["data"]["lost"], ["ca_loc", "bong_sung"])
        self.assertEqual(evs[2]["data"]["reason"], "fainted")
        self.assertEqual(evs[2]["data"]["inventory"], {"items": {}})
        self.assertTrue(sess.done)
        self.assertEqual(sess.snapshot()["hold"], [])

    def test_choke_pierces_invuln_and_keeps_hold_when_alive(self):
        sc = {
            "player": {"pos": [60, 24], "hp": 2, "oxygen_ticks": 0, "zero_oxy_ticks": 59, "invuln_ticks": 50},
            "hold": ["ca_loc", "bong_sung"],
            "monsters": [],
            "random_fish": False,
        }
        sess, evs = _step_gather(sc, ticks=1)
        self.assertEqual([e["name"] for e in evs], ["choke"])
        self.assertEqual(sess.snapshot()["player"]["hp"], 1)
        self.assertEqual(sess.snapshot()["hold"], ["ca_loc", "bong_sung"])
        self.assertFalse(sess.done)

    def test_choke_fatal_precedes_monster_hit_same_tick(self):
        sc = {
            "player": {"pos": [60, 24], "hp": 1, "oxygen_ticks": 0, "zero_oxy_ticks": 59},
            "hold": ["ca_loc"],
            "random_fish": False,
        }
        sess, evs = _step_gather(sc, ticks=1)
        self.assertEqual([e["name"] for e in evs], ["choke", "faint", "gather_end"])
        self.assertEqual(evs[1]["data"]["cause"], "choke")
        self.assertEqual(evs[1]["data"]["lost"], ["ca_loc"])
        self.assertEqual(evs[1]["data"]["hp"], 0)
        self.assertTrue(sess.done)

    def test_recoil_finished_tick_does_not_hit_until_next_tick(self):
        sc = {
            "player": {"pos": [60, 24], "hp": 3},
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [60.2, 24],
                "waypoints": [[60, 24], [64, 24]], "target_idx": 1,
                "state": "recoil", "state_ticks_left": 1, "recoil_dir": [1.0, 0.0],
            }],
        }
        # Tick 1: hoàn tất bước recoil cuối -> chuyển về patrol, KHÔNG gây hit ở tick này
        sess, evs = _step_gather(sc, ticks=1)
        self.assertEqual(evs, [])
        self.assertEqual(sess.snapshot()["monsters"][0]["state"], "patrol")
        self.assertEqual(sess.snapshot()["player"]["hp"], 3)
        # Tick 2: đã về patrol và xét phát hiện/chạm từ bước kế -> trúng hit
        evs2 = sess.step(InputPlayer([]).advance(sess.tick))
        self.assertEqual([e["name"] for e in evs2], ["monster_hit"])
        self.assertEqual(sess.snapshot()["player"]["hp"], 2)


class MonsterScenarioValidationTests(unittest.TestCase):
    def test_invalid_monster_scenarios_exit_2(self):
        bad_blocks = [
            # thiếu waypoints
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24]}]},
            # độ sâu ngoài [10, 30]
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 5], "waypoints": [[60, 24], [64, 24]]}]},
            # recoil nhưng state_ticks_left == 0
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                           "waypoints": [[60, 24], [64, 24]], "state": "recoil",
                           "state_ticks_left": 0, "recoil_dir": [1, 0]}]},
            # recoil nhưng recoil_dir không phải vector đơn vị
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                           "waypoints": [[60, 24], [64, 24]], "state": "recoil",
                           "state_ticks_left": 10, "recoil_dir": [2, 0]}]},
            # patrol nhưng recoil_dir != null
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                           "waypoints": [[60, 24], [64, 24]], "state": "patrol", "recoil_dir": [1, 0]}]},
            # target_idx ngoài {0, 1}
            {"monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                           "waypoints": [[60, 24], [64, 24]], "target_idx": 2}]},
        ]
        with Workdir() as w:
            for idx, block in enumerate(bad_blocks):
                sc = write_json(w.path(f"bad_{idx}.json"), {"gather": block})
                out = w.path(f"out_{idx}.jsonl")
                code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, block)

    def test_headless_monster_faint_writes_empty_inventory(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [60, 24], "hp": 1},
                    "hold": ["ca_loc", "bong_sung"],
                    "random_fish": False,
                }
            })
            out = w.path("out.jsonl")
            inv = w.path("inv.json")
            code, err = run_headless(
                "--mode", "gather", "--seed", "1", "--ticks", "10",
                "--scenario", sc, "--inventory-out", inv, "--out", out,
            )
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            self.assertEqual(len(events(rows, "monster_hit")), 1)
            faints = events(rows, "faint")
            self.assertEqual(len(faints), 1)
            self.assertEqual(faints[0]["data"]["cause"], "monster")
            self.assertEqual(rows[-1]["reason"], "fainted")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {}})


class WeaponExtensionTests(unittest.TestCase):
    def _step_weapon(self, scenario, frame_list, ticks, weapon_level=1, seed=1):
        tuning = load_contract()["tuning"]
        sess = Session("gather", tuning, scenario, seed, active_upgrades={"weapon": weapon_level})
        player = InputPlayer(list(frame_list), buttons=("interact", "catch", "attack"))
        all_events = []
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)
            all_events.extend(sess.step(inp))
        return sess, all_events

    def test_weapon_requires_level_1(self):
        sc = {"player": {"pos": [60, 24]}, "random_fish": False}
        sess, evs = self._step_weapon(sc, [{"tick": 0, "attack": True}], ticks=1, weapon_level=0)
        # Chưa mua cấp 1 -> không phát attack, không đặt cooldown, và vẫn ăn hit từ M1
        self.assertFalse(any(e["name"] == "attack" for e in evs))
        self.assertEqual(sess.snapshot()["player"]["attack_cd_ticks"], 0)
        self.assertEqual(sess.snapshot()["player"]["hp"], 2)

    def test_weapon_level_1_pushes_3m_stuns_120_ticks_including_attack_tick(self):
        # Người chơi ở [58, 24], M1 ở [60, 24] (cách 2m <= 4m)
        sc = {"player": {"pos": [58, 24], "hp": 3}, "random_fish": False}
        sess, evs = self._step_weapon(sc, [{"tick": 0, "attack": True}], ticks=1, weapon_level=1)
        self.assertEqual([e["name"] for e in evs], ["attack", "monster_stunned"])
        self.assertEqual(evs[0]["data"], {"pos": [58.0, 24.0], "monster_ids": ["M1"]})
        self.assertEqual(evs[1]["data"], {"monster_id": "M1", "pos": [63.0, 24.0], "stun_ticks": 120})
        snap = sess.snapshot()
        self.assertEqual(snap["player"]["attack_cd_ticks"], 180)
        self.assertEqual(snap["player"]["hp"], 3)
        m1 = snap["monsters"][0]
        self.assertEqual(m1["pos"], [63.0, 24.0])
        self.assertEqual(m1["state"], "stunned")
        self.assertEqual(m1["state_ticks_left"], 119)  # đã tính luôn bước bị Lao

        # Chạy tiếp 119 bước nữa (tổng 120 bước kể cả bước bị Lao): đứng yên, hết bước 120 về patrol
        player = InputPlayer([], buttons=("interact", "catch", "attack"))
        for _ in range(119):
            step_evs = sess.step(player.advance(sess.tick))
            self.assertFalse(any(e["name"] == "monster_hit" for e in step_evs))
        m1_done = sess.snapshot()["monsters"][0]
        self.assertEqual(m1_done["pos"], [63.0, 24.0])
        self.assertEqual(m1_done["state"], "patrol")
        self.assertEqual(m1_done["state_ticks_left"], 0)

        # Bước thứ 121: bắt đầu di chuyển trở lại từ vị trí sau đẩy
        sess.step(player.advance(sess.tick))
        self.assertNotEqual(sess.snapshot()["monsters"][0]["pos"], [63.0, 24.0])

    def test_weapon_same_center_pushes_plus_x_overrides_recoil_and_clamps(self):
        sc = {
            "player": {"pos": [98.5, 24], "hp": 3},
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [98.5, 24],
                "waypoints": [[90, 24], [95, 24]], "target_idx": 1,
                "state": "recoil", "state_ticks_left": 40, "recoil_dir": [-1.0, 0.0],
            }],
        }
        sess, evs = self._step_weapon(sc, [{"tick": 0, "attack": True}], ticks=1, weapon_level=1)
        self.assertEqual([e["name"] for e in evs], ["attack", "monster_stunned"])
        # Trùng tâm đẩy +x 3m -> 101.5 -> kẹp biên map x=100.0; ghi đè recoil
        self.assertEqual(evs[1]["data"]["pos"], [100.0, 24.0])
        m1 = sess.snapshot()["monsters"][0]
        self.assertEqual(m1["state"], "stunned")
        self.assertIsNone(m1["recoil_dir"])
        self.assertEqual(m1["pos"], [100.0, 24.0])

    def test_weapon_level_2_radius_6m_stun_180_id_order_and_miss_cooldown(self):
        # Test trúng nhiều con duyệt theo id (M2 trước M10) với cấp 2 (r=6m, stun=180)
        sc = {
            "player": {"pos": [60, 20], "hp": 3},
            "random_fish": False,
            "monsters": [
                {"id": "M10", "kind": "ca_sau", "pos": [65.5, 20],
                 "waypoints": [[60, 20], [66, 20]], "target_idx": 1},
                {"id": "M2", "kind": "ca_sau", "pos": [55.0, 20],
                 "waypoints": [[54, 20], [58, 20]], "target_idx": 1},
            ],
        }
        sess, evs = self._step_weapon(sc, [{"tick": 0, "attack": True}], ticks=1, weapon_level=2)
        self.assertEqual([e["name"] for e in evs], ["attack", "monster_stunned", "monster_stunned"])
        self.assertEqual(evs[0]["data"]["monster_ids"], ["M2", "M10"])
        self.assertEqual(evs[1]["data"]["monster_id"], "M2")
        self.assertEqual(evs[1]["data"]["stun_ticks"], 180)
        self.assertEqual(evs[2]["data"]["monster_id"], "M10")
        self.assertEqual(evs[2]["data"]["stun_ticks"], 180)

        # Bấm trượt vẫn hồi 180 tick
        sc_miss = {"player": {"pos": [10, 5]}, "monsters": [], "random_fish": False}
        sess_m, evs_m = self._step_weapon(sc_miss, [{"tick": 0, "attack": True}], ticks=1, weapon_level=1)
        self.assertEqual([e["name"] for e in evs_m], ["attack"])
        self.assertEqual(evs_m[0]["data"]["monster_ids"], [])
        self.assertEqual(sess_m.snapshot()["player"]["attack_cd_ticks"], 180)

    def test_headless_accepts_attack_input_and_exposes_attack_cd_ticks(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [10, 5], "attack_cd_ticks": 10}, "random_fish": False}})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "attack": True}))
            out = w.path("out.jsonl")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2", "--scenario", sc, "--inputs", inp, "--out", out)
            self.assertEqual(code, 0, err)
            snaps = snapshots(read_jsonl(out))
            self.assertEqual(snaps[0]["player"]["attack_cd_ticks"], 10)
            self.assertEqual(snaps[-1]["player"]["attack_cd_ticks"], 8)


if __name__ == "__main__":
    unittest.main()
