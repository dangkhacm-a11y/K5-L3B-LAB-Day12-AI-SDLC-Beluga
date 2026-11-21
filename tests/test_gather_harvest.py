"""Unit & headless tests cho Gather lát 2: hái nút, mọc lại, bắt cá, giỏ đầy, ưu tiên cập bến và xuất kho."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.runner import Session

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def _step_frames(scenario, frame_list, ticks, seed=1):
    tuning = load_contract()["tuning"]
    sess = Session("gather", tuning, scenario, seed)
    player = InputPlayer(frame_list)
    all_events = []
    while sess.tick < ticks and not sess.done:
        inp = player.advance(sess.tick)
        all_events.extend(sess.step(inp))
    return sess, all_events


class GatherNodeTests(unittest.TestCase):
    def test_gather_ready_node_at_surface_and_regrow(self):
        tuning = load_contract()["tuning"]["gather"]
        regrow_ticks = int(round(tuning["regrow_s"] * 60))
        sc = {
            "player": {"pos": [12, 0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
            "random_fish": False,
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "interact": True}], ticks=1)
        gather_evs = [e for e in evs if e["name"] == "gather"]
        self.assertEqual(len(gather_evs), 1)
        self.assertEqual(gather_evs[0]["tick"], 1)
        self.assertEqual(gather_evs[0]["data"]["node_id"], "N1")
        self.assertEqual(gather_evs[0]["data"]["kind"], "bong_dien_dien")
        self.assertEqual(gather_evs[0]["data"]["count"], tuning["node_yield"])
        snap = sess.snapshot()
        self.assertEqual(snap["hold"], ["bong_dien_dien"])
        self.assertFalse(snap["nodes"][0]["ready"])
        self.assertEqual(snap["nodes"][0]["regrow_ticks"], regrow_ticks)

        # Chạy đủ regrow_ticks để nút mọc lại
        player = InputPlayer([])
        regrow_evs = []
        for _ in range(regrow_ticks):
            regrow_evs.extend(sess.step(player.advance(sess.tick)))
        regrown = [e for e in regrow_evs if e["name"] == "node_regrown"]
        self.assertEqual(len(regrown), 1)
        self.assertEqual(regrown[0]["data"], {"node_id": "N1"})
        self.assertTrue(sess.snapshot()["nodes"][0]["ready"])

    def test_cannot_gather_when_underwater(self):
        sc = {
            "player": {"pos": [12, 1.0]},  # > surface_depth (0.5), trong interact_radius (2.0)
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
            "random_fish": False,
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "interact": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], [])
        self.assertEqual(sess.snapshot()["hold"], [])
        self.assertTrue(sess.snapshot()["nodes"][0]["ready"])

    def test_gather_tie_break_nearest_then_smallest_id(self):
        sc = {
            "player": {"pos": [20, 0]},
            "nodes": [
                {"id": "N10", "kind": "bong_sung", "pos": [19, 0]},
                {"id": "N2", "kind": "bong_dien_dien", "pos": [21, 0]},
            ],
            "random_fish": False,
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "interact": True}], ticks=1)
        gather_evs = [e for e in evs if e["name"] == "gather"]
        self.assertEqual(len(gather_evs), 1)
        self.assertEqual(gather_evs[0]["data"]["node_id"], "N2")
        self.assertEqual(sess.snapshot()["hold"], ["bong_dien_dien"])

    def test_gather_hold_full_does_not_consume_node(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        sc = {
            "player": {"pos": [12, 0]},
            "hold": ["ca_loc"] * cap,
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
            "random_fish": False,
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "interact": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], ["hold_full"])
        self.assertEqual(sess.snapshot()["hold_count"], cap)
        self.assertTrue(sess.snapshot()["nodes"][0]["ready"])

    def test_dock_has_priority_over_gather(self):
        sc = {
            "player": {"pos": [2, 0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [2, 0]}],
            "random_fish": False,
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "interact": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], ["gather_end"])
        self.assertEqual(evs[0]["data"]["reason"], "docked")
        self.assertTrue(sess.done)
        self.assertEqual(sess.snapshot()["hold"], [])
        self.assertTrue(sess.snapshot()["nodes"][0]["ready"])


class CatchFishTests(unittest.TestCase):
    def test_catch_ca_linh_underwater_and_cooldown(self):
        tuning = load_contract()["tuning"]["gather"]
        cd_ticks = int(round(tuning["catch_cooldown_s"] * 60))
        sc = {
            "player": {"pos": [15, 5]},
            "nodes": [],
            "random_fish": False,
            "fish": [
                {"id": "F1", "kind": "ca_linh", "pos": [15, 5]},
                {"id": "F2", "kind": "ca_loc", "pos": [15.5, 5]},
            ],
        }
        # Tick 0: bắt F1 -> nhận 3 ca_linh, vào hồi chiêu 30 tick.
        # Tick 2: vẫn đang hồi chiêu -> bấm catch không bắt được F2.
        # Tick cd_ticks: hồi chiêu vừa về 0 ở đầu bước -> bắt được F2.
        inp_frames = [
            {"tick": 0, "catch": True},
            {"tick": 1, "catch": False},
            {"tick": 2, "catch": True},
            {"tick": 3, "catch": False},
            {"tick": cd_ticks, "catch": True},
        ]
        sess, evs = _step_frames(sc, inp_frames, ticks=cd_ticks + 1)
        caught = [e for e in evs if e["name"] == "fish_caught"]
        self.assertEqual(len(caught), 2)
        self.assertEqual(caught[0]["tick"], 1)
        self.assertEqual(caught[0]["data"]["fish_id"], "F1")
        self.assertEqual(caught[0]["data"]["count"], tuning["fish_yield"]["ca_linh"])
        self.assertEqual(caught[1]["tick"], cd_ticks + 1)
        self.assertEqual(caught[1]["data"]["fish_id"], "F2")
        self.assertEqual(caught[1]["data"]["count"], tuning["fish_yield"]["ca_loc"])
        self.assertEqual(sess.snapshot()["hold"], ["ca_linh", "ca_linh", "ca_linh", "ca_loc"])
        self.assertEqual(sess.snapshot()["fish"], [])

    def test_cannot_catch_at_surface(self):
        sc = {
            "player": {"pos": [15, 0.5]},  # <= surface_depth (0.5)
            "nodes": [],
            "random_fish": False,
            "fish": [{"id": "F1", "kind": "ca_loc", "pos": [15, 1.5]}],
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "catch": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], [])
        self.assertEqual(sess.snapshot()["player"]["catch_cd_ticks"], 0)
        self.assertEqual(len(sess.snapshot()["fish"]), 1)

    def test_catch_without_fish_does_not_start_cooldown(self):
        sc = {"player": {"pos": [15, 5]}, "nodes": [], "fish": [], "random_fish": False}
        sess, evs = _step_frames(sc, [{"tick": 0, "catch": True}], ticks=1)
        self.assertEqual(evs, [])
        self.assertEqual(sess.snapshot()["player"]["catch_cd_ticks"], 0)

    def test_catch_tie_break_nearest_then_smallest_id(self):
        sc = {
            "player": {"pos": [20, 5]},
            "nodes": [],
            "random_fish": False,
            "fish": [
                {"id": "F10", "kind": "ca_loc", "pos": [19, 5]},
                {"id": "F2", "kind": "ca_linh", "pos": [21, 5]},
            ],
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "catch": True}], ticks=1)
        caught = [e for e in evs if e["name"] == "fish_caught"]
        self.assertEqual(len(caught), 1)
        self.assertEqual(caught[0]["data"]["fish_id"], "F2")
        self.assertEqual([f["id"] for f in sess.snapshot()["fish"]], ["F10"])

    def test_catch_hold_full_keeps_fish(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        sc = {
            "player": {"pos": [15, 5]},
            "hold": ["bong_sung"] * cap,
            "nodes": [],
            "random_fish": False,
            "fish": [{"id": "F1", "kind": "ca_loc", "pos": [15, 5]}],
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "catch": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], ["hold_full"])
        self.assertEqual(len(sess.snapshot()["fish"]), 1)
        self.assertEqual(sess.snapshot()["hold_count"], cap)

    def test_catch_requires_room_for_whole_school_and_does_not_start_cooldown(self):
        cap = load_contract()["tuning"]["gather"]["hold_capacity"]
        sc = {
            "player": {"pos": [15, 5]},
            "hold": ["bong_sung"] * (cap - 2),
            "nodes": [],
            "random_fish": False,
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}],  # yield 3, chỉ còn 2 chỗ
        }
        sess, evs = _step_frames(sc, [{"tick": 0, "catch": True}], ticks=1)
        self.assertEqual([e["name"] for e in evs], ["hold_full"])
        self.assertEqual(sess.snapshot()["hold_count"], cap - 2)
        self.assertEqual(sess.snapshot()["hold"][-2:], ["bong_sung", "bong_sung"])
        self.assertEqual(len(sess.snapshot()["fish"]), 1)
        self.assertEqual(sess.snapshot()["player"]["catch_cd_ticks"], 0)


class FishMovementTests(unittest.TestCase):
    def test_fish_swims_at_contract_speed(self):
        sc = {"nodes": [], "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 7]}]}
        sess, _ = _step_frames(sc, [], ticks=60)
        fish = sess.snapshot()["fish"][0]
        self.assertAlmostEqual(fish["pos"][0], 51.5, places=6)
        self.assertAlmostEqual(fish["pos"][1], 7, places=6)

    def test_fish_turns_on_120th_swim_step_and_seed_is_deterministic(self):
        sc = {"nodes": [], "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 7]}]}
        one, _ = _step_frames(sc, [], ticks=120, seed=31)
        two, _ = _step_frames(sc, [], ticks=120, seed=31)
        fish_one = one.snapshot()["fish"][0]
        fish_two = two.snapshot()["fish"][0]
        self.assertEqual(fish_one, fish_two)
        self.assertNotEqual(fish_one["heading_deg"], 0)

    def test_spawn_happens_after_swim_at_tick_360(self):
        sc = {"nodes": [], "fish": []}
        sess, evs = _step_frames(sc, [], ticks=360, seed=9)
        spawned = [e for e in evs if e["name"] == "fish_spawned"]
        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0]["tick"], 360)
        self.assertEqual(len(sess.snapshot()["fish"]), 1)
        self.assertEqual(sess.snapshot()["fish"][0]["id"], spawned[0]["data"]["id"])

    def test_spawning_stops_at_contract_maximum(self):
        tuning = load_contract()["tuning"]
        sess = Session("gather", tuning, {}, seed=9)
        player = InputPlayer([])
        spawned = []
        for _ in range(1440):
            spawned.extend(e for e in sess.step(player.advance(sess.tick)) if e["name"] == "fish_spawned")
        self.assertEqual(len(spawned), 4)
        self.assertEqual(len(sess.snapshot()["fish"]), tuning["gather"]["fish_max"])

    def test_spawn_skips_when_all_points_are_blocked(self):
        tuning = load_contract()["tuning"]
        g = tuning["gather"]
        g["fish_speed"] = 0
        g["fish_max"] = 40
        points = {(x, d, kind)
                  for kind, depths in g["fish_spawn_depths"].items()
                  for x in g["fish_spawn_x"] for d in depths}
        fish = []
        positions = set()
        for x, d, kind in points:
            pos = (x, d)
            if pos in positions:
                continue
            positions.add(pos)
            fish.append({"id": f"F{len(fish) + 1}", "kind": kind, "pos": [x, d]})
        sess = Session("gather", tuning, {"fish": fish}, seed=9)
        player = InputPlayer([])
        spawned = []
        for _ in range(g["fish_spawn_ticks"]):
            spawned.extend(e for e in sess.step(player.advance(sess.tick)) if e["name"] == "fish_spawned")
        self.assertEqual(spawned, [])
        self.assertEqual(len(sess.snapshot()["fish"]), len(positions))

    def test_fish_reflects_at_x_boundary(self):
        sc = {"nodes": [], "fish": [{"id": "F1", "kind": "ca_linh", "pos": [95.99, 7]}]}
        sess, _ = _step_frames(sc, [], ticks=1)
        fish = sess.snapshot()["fish"][0]
        self.assertAlmostEqual(fish["pos"][0], 95.985, places=6)
        self.assertAlmostEqual(fish["heading_deg"], 180, places=6)

    def test_random_fish_false_keeps_fixture_static_and_disables_spawn(self):
        sc = {"nodes": [], "random_fish": False,
              "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 7]}]}
        sess, evs = _step_frames(sc, [], ticks=360)
        self.assertEqual(sess.snapshot()["fish"][0]["pos"], [50.0, 7.0])
        self.assertFalse(any(e["name"] == "fish_spawned" for e in evs))


class GatherHeadlessInventoryTests(unittest.TestCase):
    def test_headless_gather_fish_and_dock_writes_inventory(self):
        """Chạy headless đầy đủ: bắt cá -> hái rau -> cập bến xuất kho đúng."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [4, 1.0]},
                    "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [6, 0]}],
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [4, 1.0]}],
                }
            })
            # Tick 0: bắt F1 tại [4, 1.0], đồng thời bơi lên mặt nước sang phải tới [6, 0]
            # Tick 60: tới mặt nước gần N1 -> hái N1; bơi trái về bến [2, 0]
            # Tick 160: trong vùng bến -> cập bến
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "catch": True, "move": [1, -1]},
                {"tick": 45, "move": [0, 0]},
                {"tick": 50, "interact": True},
                {"tick": 51, "interact": False, "move": [-1, 0]},
                {"tick": 140, "move": [0, 0]},
                {"tick": 145, "interact": True},
            ))
            out = w.path("out.jsonl")
            inv = w.path("inv.json")
            code, err = run_headless(
                "--mode", "gather", "--seed", "1", "--ticks", "200",
                "--scenario", sc, "--inputs", inp, "--inventory-out", inv, "--out", out,
            )
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            self.assertEqual(len(events(rows, "fish_caught")), 1)
            self.assertEqual(len(events(rows, "gather")), 1)
            end_evs = events(rows, "gather_end")
            self.assertEqual(len(end_evs), 1)
            self.assertEqual(end_evs[0]["data"]["reason"], "docked")
            want = {"items": {"bong_dien_dien": 1, "ca_loc": 1}}
            self.assertEqual(end_evs[0]["data"]["inventory"], want)
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), want)


if __name__ == "__main__":
    unittest.main()
