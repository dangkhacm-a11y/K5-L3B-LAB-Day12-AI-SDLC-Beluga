import json
import os
import tempfile
import unittest

from chonoi.bench import run_benchmark
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.day import DaySim
from chonoi.soak import run_soak


class Phase4CommandTests(unittest.TestCase):
    def test_soak_repeats_five_day_schedule_to_ten_days(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "soak.json")
            result = run_soak(7, 10, path)
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
        self.assertEqual(result, saved)
        self.assertEqual(saved["days"], 10)
        self.assertEqual(saved["days_completed"], 10)
        self.assertEqual(saved["crashes"], 0)
        self.assertEqual([r["day"] for r in saved["results"]], list(range(1, 11)))
        self.assertTrue(all(set(r) == {"day", "earned", "reputation", "score"} for r in saved["results"]))
        self.assertTrue(all(result["reputation"] >= 0 for result in saved["results"]))

    def test_day_plan_repeats_after_fifth_day(self):
        tuning = load_contract()["tuning"]
        sim = DaySim(tuning, {}, Streams(7), IdAllocator(), days=10)
        for day in range(1, 6):
            self.assertEqual(sim.get_plan_for_day(day + 5), sim.get_plan_for_day(day))

    def test_benchmark_writes_contract_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "bench.json")
            report = run_benchmark(42, 1, path)
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
        self.assertEqual(report, saved)
        self.assertEqual(set(saved), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertGreater(saved["frames"], 0)
        self.assertGreater(saved["measured_s"], 0)
        self.assertGreaterEqual(saved["load_ms"], 0)


if __name__ == "__main__":
    unittest.main()
