"""Luật độ tươi và cá thể riêng lẻ trong Gather (TICKET-03)."""

import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputPlayer
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim


def _tuning():
    tuning = load_contract()["tuning"]
    tuning["freshness"] = {
        "initial": 100,
        "gather_decay_per_s": 0.5,
        "quan_decay_per_s": 0.25,
        "spoiled_below": 30,
    }
    tuning["gather"]["current"] = {
        "interval_ticks": 10,
        "duration_ticks": 3,
        "warning_ticks": 2,
        "min_depth": 10,
        "speed": 1.0,
    }
    return tuning


def _sim(scenario, tuning=None):
    return GatherSim(tuning or _tuning(), scenario, Streams(7), IdAllocator())


def _step(sim, ticks=1):
    player = InputPlayer([])
    events = []
    for tick in range(sim.phase_tick, sim.phase_tick + ticks):
        events.extend(sim.step(player.advance(tick)))
        if sim.done:
            break
    return events


def _interact(sim):
    inp = InputPlayer([{"tick": sim.phase_tick, "interact": True}]).advance(sim.phase_tick)
    return sim.step(inp)


class GatherFreshnessTests(unittest.TestCase):
    def test_item_at_30_spoils_on_first_gather_tick(self):
        tuning = _tuning()
        sim = _sim({
            "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}],
            "random_fish": False,
            "monsters": [],
        }, tuning)
        events = _step(sim)
        self.assertEqual([e[0] for e in events], ["spoiled"])
        self.assertEqual(events[0][1], {"item_id": "I1", "kind": "ca_linh", "location": "hold"})
        self.assertEqual(sim.snapshot()["hold"], [])

    def test_gather_degrades_freshness_by_half_percent_per_second(self):
        tuning = _tuning()
        sim = _sim({
            "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}],
            "random_fish": False,
            "monsters": [],
        }, tuning)
        _step(sim, 60)
        self.assertAlmostEqual(sim.snapshot()["hold"][0]["fresh"], 99.5, places=8)

    def test_newly_gathered_item_has_id_and_initial_freshness(self):
        tuning = _tuning()
        tuning["gather"]["dock_pos"] = [2, 0]
        sim = _sim({
            "player": {"pos": [12, 0], "vel": [0, 0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
            "random_fish": False,
            "monsters": [],
        }, tuning)
        events = _interact(sim)
        self.assertEqual([e[0] for e in events], ["gather"])
        self.assertEqual(sim.snapshot()["hold"], [
            {"id": "I1", "kind": "bong_dien_dien", "fresh": 100.0},
        ])

    def test_item_ids_continue_after_loaded_ids_and_preserve_pickup_order(self):
        tuning = _tuning()
        tuning["gather"]["dock_pos"] = [2, 0]
        sim = _sim({
            "player": {"pos": [12, 0], "vel": [0, 0]},
            "hold": [{"id": "I9", "kind": "ca_loc", "fresh": 100}],
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}],
            "random_fish": False,
            "monsters": [],
        }, tuning)
        _interact(sim)
        self.assertEqual([item["id"] for item in sim.inventory_items()], ["I9", "I10"])

    def test_successful_catch_creates_individual_items(self):
        sim = _sim({
            "player": {"pos": [15, 5], "vel": [0, 0]},
            "nodes": [], "random_fish": False,
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}],
        })
        inp = InputPlayer([{"tick": 0, "catch": True}]).advance(0)
        events = sim.step(inp)
        self.assertEqual([name for name, _ in events], ["fish_caught"])
        self.assertEqual(sim.inventory_items(), [
            {"id": "I1", "kind": "ca_linh", "fresh": 100.0},
            {"id": "I2", "kind": "ca_linh", "fresh": 100.0},
            {"id": "I3", "kind": "ca_linh", "fresh": 100.0},
        ])

    def test_monster_loss_and_faint_payloads_use_lifo_item_records(self):
        sim = _sim({
            "hold": [
                {"id": "I1", "kind": "ca_loc", "fresh": 100},
                {"id": "I2", "kind": "bong_sung", "fresh": 100},
                {"id": "I3", "kind": "ca_linh", "fresh": 100},
                {"id": "I4", "kind": "ca_keo", "fresh": 100},
            ],
            "random_fish": False,
            "monsters": [],
        })
        events = []
        sim._faint("monster", events)
        self.assertEqual([item["id"] for item in events[0][1]["lost"]], ["I4", "I3", "I2", "I1"])
        self.assertEqual(events[-1][1]["inventory"], {"items": []})

    def test_random_current_warns_then_activates_for_configured_duration(self):
        sim = _sim({"random_fish": False, "monsters": []})
        warning_events = []
        for _ in range(8):
            warning_events.extend(_step(sim))
        warning = next(event for event in warning_events if event[0] == "current_warning")
        direction = warning[1]["direction"]
        self.assertIn(direction, (-1, 1))
        self.assertEqual(warning[1]["ticks_left"], 2)
        self.assertIsNone(sim.snapshot()["current"])

        # The following 2 ticks reach tick 10; its current is active in the snapshot.
        _step(sim, 2)
        self.assertEqual(sim.snapshot()["current"], {"direction": direction, "ticks_left": 3})
        _step(sim, 3)
        self.assertIsNone(sim.snapshot()["current"])

    def test_current_pushes_only_at_or_below_minimum_depth(self):
        tuning = _tuning()
        tuning["gather"]["current"].update(interval_ticks=1, duration_ticks=1, warning_ticks=0)
        tuning["gather"]["current"]["speed"] = 60
        shallow = _sim({"player": {"pos": [50, 9]}, "random_fish": False, "monsters": []}, tuning)
        _step(shallow)
        self.assertAlmostEqual(shallow.pos[0], 50)

        deep = _sim({"player": {"pos": [50, 10]}, "random_fish": False, "monsters": []}, tuning)
        _step(deep)
        self.assertNotEqual(deep.pos[0], 50)

    def test_random_current_false_disables_warning_activation_and_push(self):
        tuning = _tuning()
        tuning["gather"]["current"].update(interval_ticks=1, duration_ticks=1, warning_ticks=0)
        sim = _sim({
            "player": {"pos": [50, 20]}, "random_current": False,
            "current_direction": 1, "random_fish": False, "monsters": [],
        }, tuning)
        events = _step(sim)
        self.assertFalse(any(event[0] == "current_warning" for event in events))
        self.assertIsNone(sim.snapshot()["current"])
        self.assertAlmostEqual(sim.pos[0], 50)

    def test_fixture_direction_is_used_for_warning_and_current(self):
        tuning = _tuning()
        sim = _sim({
            "current_direction": -1, "random_fish": False, "monsters": [],
        }, tuning)
        events = []
        for _ in range(10):
            events.extend(_step(sim))
        self.assertIn(("current_warning", {"direction": -1, "ticks_left": 2}), events)
        self.assertEqual(sim.snapshot()["current"], {"direction": -1, "ticks_left": 3})


if __name__ == "__main__":
    unittest.main()
