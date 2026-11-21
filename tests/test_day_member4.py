import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.day import DaySim


def make_input(move=(0.0, 0.0), **kwargs):
    edges = set()
    held = {}
    for k, v in kwargs.items():
        if k == "buy":
            continue
        if v:
            edges.add(k)
            held[k] = True
    return InputState(list(move), held, edges, buy=kwargs.get("buy"))


class DaySimTests(unittest.TestCase):
    def setUp(self):
        contract = load_contract()
        self.tuning = contract["tuning"]
        self.streams = Streams(1)
        self.ids = IdAllocator()

    def test_day_initial_events_and_plan(self):
        sim = DaySim(self.tuning, {}, self.streams, self.ids, days=1)
        init_ev = sim.initial_events()
        self.assertEqual(len(init_ev), 3)
        self.assertEqual(init_ev[0]["name"], "day_start")
        self.assertEqual(init_ev[1]["name"], "day_plan")
        self.assertEqual(init_ev[1]["data"]["dishes"], {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3})
        self.assertEqual(init_ev[1]["data"]["ingredients"], {"ca_loc": 3, "bong_sung": 6})
        self.assertEqual(init_ev[2]["name"], "phase_start")
        self.assertEqual(init_ev[2]["phase"], "gather")

    def test_day_pause_and_resume(self):
        sim = DaySim(self.tuning, {}, self.streams, self.ids, days=1)
        # Bấm pause
        ev = sim.step(make_input(pause=True))
        self.assertTrue(sim.paused)
        self.assertEqual(ev[0][0], "paused")
        self.assertEqual(sim.snapshot()["state"], "paused")

        # Đang pause mà không bấm -> không chạy gameplay
        ev_idle = sim.step(make_input())
        self.assertEqual(ev_idle, [])
        self.assertTrue(sim.paused)

        # Bấm pause lần nữa -> resume
        ev_res = sim.step(make_input(pause=True))
        self.assertFalse(sim.paused)
        self.assertEqual(ev_res[0][0], "resumed")

    def test_shop_buy_oxygen_and_hp(self):
        # Scenario có sẵn 500k tiền trong ngày
        scenario = {"day": {"money": 500, "earned": 500}}
        sim = DaySim(self.tuning, scenario, self.streams, self.ids, days=1)
        sim.phase = "shop"
        sim.phase_tick = 0

        # Mua oxygen cấp 1 (giá 200)
        ev = sim.step(make_input(buy="oxygen"))
        bought = [e for e in ev if e[0] == "bought"]
        self.assertEqual(len(bought), 1)
        self.assertEqual(bought[0][1]["upgrade"], "oxygen")
        self.assertEqual(bought[0][1]["level"], 1)
        self.assertEqual(bought[0][1]["price"], 200)
        self.assertEqual(bought[0][1]["money"], 300)
        self.assertEqual(sim.upgrades["oxygen"], 1)
        # Nhưng active_upgrades vẫn là cấp cũ (0) cho tới khi sang ngày mới
        self.assertEqual(sim.active_upgrades.get("oxygen", 0), 0)

        # Mua tiếp oxygen cấp 2 (giá 400, trong khi còn 300) -> buy_failed (funds)
        ev2 = sim.step(make_input(buy="oxygen"))
        failed = [e for e in ev2 if e[0] == "buy_failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0][1]["reason"], "funds")

        # Mua lệnh lạ -> buy_failed (unknown)
        ev3 = sim.step(make_input(buy="sung_laser"))
        failed_unk = [e for e in ev3 if e[0] == "buy_failed"]
        self.assertEqual(len(failed_unk), 1)
        self.assertEqual(failed_unk[0][1]["reason"], "unknown")

    def test_shop_done_and_day_completion(self):
        scenario = {"day": {"money": 200, "earned": 200}}
        sim = DaySim(self.tuning, scenario, self.streams, self.ids, days=1)
        sim.phase = "shop"
        sim.phase_tick = 0

        # Bấm shop_done để kết thúc ngày 1
        ev = sim.step(make_input(shop_done=True))
        shop_end = [e for e in ev if e[0] == "shop_end"]
        self.assertEqual(len(shop_end), 1)
        self.assertEqual(shop_end[0][1]["reason"], "done")
        self.assertEqual(sim.days_completed, 1)
        self.assertTrue(sim.done)
        self.assertEqual(sim.reason, "days_complete")

    def test_day_to_day_progression_and_active_upgrades(self):
        scenario = {"day": {"money": 500, "earned": 500}}
        sim = DaySim(self.tuning, scenario, self.streams, self.ids, days=2)
        sim.phase = "shop"
        sim.phase_tick = 0

        # Mua oxy trong shop ngày 1
        sim.step(make_input(buy="oxygen"))
        self.assertEqual(sim.upgrades["oxygen"], 1)
        self.assertEqual(sim.active_upgrades.get("oxygen", 0), 0)

        # Đóng shop ngày 1 -> chuyển sang Ngày 2 ngay tick đó
        ev = sim.step(make_input(shop_done=True))
        self.assertEqual(sim.day, 2)
        self.assertEqual(sim.active_upgrades.get("oxygen"), 1)
        self.assertEqual(sim.phase, "gather")
        day_starts = [e for e in ev if e[0] == "day_start"]
        self.assertEqual(len(day_starts), 1)
        plans = [e for e in ev if e[0] == "day_plan"]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0][1]["dishes"], {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2})

    def test_headless_day_mode_run(self):
        with Workdir() as w:
            out = w.path("day.jsonl")
            # Chạy headless mode day --days 1 với ticks 10
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "10", "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            self.assertEqual(rows[0]["type"], "snapshot")
            self.assertEqual(rows[0]["mode"], "day")
            self.assertEqual(rows[0]["day"], 1)
            # Kiểm tra event initial ở tick 0
            plan_ev = events(rows, "day_plan")
            self.assertEqual(len(plan_ev), 1)
            self.assertEqual(plan_ev[0]["day"], 1)
            self.assertEqual(rows[-1]["type"], "end")
            self.assertEqual(rows[-1]["mode"], "day")


    def test_day_full_cycle_gather_quan_shop_e2e(self):
        # Scenario ngày 1 với mục tiêu kiểm tra trọn vẹn luồng gather -> quan -> shop -> kết thúc
        sim = DaySim(self.tuning, {}, self.streams, self.ids, days=1)
        self.assertEqual(sim.phase, "gather")
        self.assertEqual(sim.day, 1)

        # Mô phỏng ép kết thúc gather bằng cập bến (docked)
        sim.gather_sim.done = True
        sim.gather_sim.reason = "docked"
        sim.gather_sim.hold = [
            {"id": "I1", "kind": "ca_loc", "fresh": 100.0},
            {"id": "I2", "kind": "ca_loc", "fresh": 100.0},
            {"id": "I3", "kind": "bong_sung", "fresh": 100.0},
            {"id": "I4", "kind": "bong_sung", "fresh": 100.0},
        ]

        # Bước tiếp theo: DaySim nhận thấy gather_sim kết thúc, chuyển sang quan
        ev = sim.step(make_input())
        self.assertEqual(sim.phase, "quan")
        phase_starts = [e for e in ev if e[0] == "phase_start"]
        self.assertEqual(phase_starts[0][2], "quan")
        # Kho bàn giao cho quan nhận đúng stock
        self.assertEqual(len(sim.quan_sim.stock), 4)

        # Mô phỏng ép kết thúc quan khi hết giờ
        sim.quan_sim.done = True
        sim.quan_sim.reason = "time"
        sim.quan_sim.money = 150
        sim.quan_sim.earned = 150
        sim.quan_sim.reputation = 3.5

        # Bước tiếp theo: chuyển từ quan sang shop
        ev2 = sim.step(make_input())
        self.assertEqual(sim.phase, "shop")
        self.assertEqual(sim.money, 150)
        self.assertEqual(sim.earned, 150)
        self.assertEqual(sim.reputation, 3.5)

        # Trong shop bấm shop_done
        ev3 = sim.step(make_input(shop_done=True))
        self.assertTrue(sim.done)
        self.assertEqual(sim.reason, "days_complete")
        self.assertEqual(sim.days_completed, 1)
        shop_ends = [e for e in ev3 if e[0] == "shop_end"]
        self.assertEqual(len(shop_ends), 1)


if __name__ == "__main__":
    unittest.main()
