"""Unit test cho phần việc của Thành viên 4:
- Tương tác bếp (cook_started, dish_ready, dish_picked)
- Tương tác bàn (served)
- Vòng đời ăn uống và thanh toán (paid, tip, reputation)
- Thứ tự ưu tiên interact (khoảng cách, bếp trước bàn, id)
- Kết thúc ca (quan_end)
"""

import unittest
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim


def make_input(move=(0.0, 0.0), interact=False):
    return InputState(
        move=list(move),
        held={"interact": interact} if interact else {},
        edges={"interact"} if interact else set()
    )


class TestQuanMember4(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]
        self.streams = Streams(1)
        self.ids = IdAllocator()

    def test_cook_started_and_dish_ready(self):
        """Bếp idle + đủ nguyên liệu -> cook_started -> sau cook_s -> dish_ready."""
        stove_pos = self.tuning["quan"]["stoves"][0]["pos"]  # [2, 8]
        scenario = {
            "player": {"pos": stove_pos},
            "stock": {"ca_loc": 2},
            "customers": [{"id": "C1", "table_id": "T1", "dish": "ca_loc_nuong_trui"}],
            "stoves": [{"id": "B1", "pos": stove_pos, "state": "idle"}]
        }
        sim = QuanSim(self.tuning, scenario, self.streams, self.ids)

        # Tick 1: nhấn interact tại bếp
        events = sim.step(make_input(interact=True))
        cook_ev = [ev for ev in events if ev[0] == "cook_started"]
        self.assertEqual(len(cook_ev), 1)
        self.assertEqual(cook_ev[0][1]["stove_id"], "B1")
        self.assertEqual(cook_ev[0][1]["dish"], "ca_loc_nuong_trui")
        self.assertEqual(sim.stock.get("ca_loc", 0), 1)  # Đã trừ 1 ca_loc
        self.assertEqual(sim.stoves[0]["state"], "cooking")

        # Chạy tiếp cho đến khi nấu xong (cook_s = 6s = 360 ticks)
        ready_events = []
        for _ in range(360):
            ready_events.extend([ev for ev in sim.step(make_input()) if ev[0] == "dish_ready"])

        self.assertEqual(len(ready_events), 1)
        self.assertEqual(ready_events[0][1]["stove_id"], "B1")
        self.assertEqual(ready_events[0][1]["dish"], "ca_loc_nuong_trui")
        self.assertEqual(sim.stoves[0]["state"], "ready")

    def test_dish_picked(self):
        """Bếp ready + tay trống -> dish_picked, món lên tay, bếp về idle."""
        stove_pos = self.tuning["quan"]["stoves"][0]["pos"]
        scenario = {
            "player": {"pos": stove_pos},
            "hand": None,
            "stoves": [{"id": "B1", "pos": stove_pos, "state": "ready", "dish": "ca_loc_nuong_trui", "cook_ticks_left": 0}]
        }
        sim = QuanSim(self.tuning, scenario, self.streams, self.ids)

        events = sim.step(make_input(interact=True))
        pick_ev = [ev for ev in events if ev[0] == "dish_picked"]
        self.assertEqual(len(pick_ev), 1)
        self.assertEqual(pick_ev[0][1]["dish"], "ca_loc_nuong_trui")
        self.assertEqual(sim.hand, "ca_loc_nuong_trui")
        self.assertEqual(sim.stoves[0]["state"], "idle")
        self.assertIsNone(sim.stoves[0]["dish"])

    def test_served_and_paid_with_tip(self):
        """Tay cầm món đúng -> served -> ăn xong -> paid có tip và tăng uy tín."""
        table_pos = self.tuning["quan"]["tables"][0]["pos"]  # [9, 2]
        scenario = {
            "player": {"pos": table_pos},
            "hand": "ca_loc_nuong_trui",
            "customers": [{
                "id": "C1",
                "table_id": "T1",
                "dish": "ca_loc_nuong_trui",
                "state": "waiting",
                "patience_ticks": 3600,
                "patience_max_ticks": 3600
            }]
        }
        sim = QuanSim(self.tuning, scenario, self.streams, self.ids)
        init_rep = sim.reputation

        # Phục vụ
        events = sim.step(make_input(interact=True))
        served_ev = [ev for ev in events if ev[0] == "served"]
        self.assertEqual(len(served_ev), 1)
        self.assertEqual(served_ev[0][1]["customer_id"], "C1")
        self.assertIsNone(sim.hand)  # Món đã trao cho khách

        # Khách ăn eat_s = 10s = 600 ticks
        paid_events = []
        for _ in range(600):
            paid_events.extend([ev for ev in sim.step(make_input()) if ev[0] == "paid"])

        self.assertEqual(len(paid_events), 1)
        p = paid_events[0][1]
        self.assertEqual(p["customer_id"], "C1")
        self.assertEqual(p["price"], 60)
        self.assertEqual(p["tip"], 12)  # 20% của 60 là 12
        self.assertEqual(p["total"], 72)
        self.assertAlmostEqual(sim.reputation, init_rep + 0.2)
        self.assertEqual(sim.money, 72)
        self.assertEqual(sim.earned, 72)
        # Bàn đã trống
        self.assertEqual(len(sim.customers), 0)

    def test_paid_without_tip_when_patience_low(self):
        """Phục vụ khi patience < 50% -> paid không có tip, uy tín không đổi."""
        table_pos = self.tuning["quan"]["tables"][0]["pos"]
        scenario = {
            "player": {"pos": table_pos},
            "hand": "ca_loc_nuong_trui",
            "customers": [{
                "id": "C1",
                "table_id": "T1",
                "dish": "ca_loc_nuong_trui",
                "state": "waiting",
                "patience_ticks": 1000,
                "patience_max_ticks": 3600  # < 50%
            }]
        }
        sim = QuanSim(self.tuning, scenario, self.streams, self.ids)
        init_rep = sim.reputation

        sim.step(make_input(interact=True))

        paid_events = []
        for _ in range(600):
            paid_events.extend([ev for ev in sim.step(make_input()) if ev[0] == "paid"])

        self.assertEqual(len(paid_events), 1)
        p = paid_events[0][1]
        self.assertEqual(p["tip"], 0)
        self.assertEqual(p["total"], 60)
        self.assertEqual(sim.reputation, init_rep)

    def test_interact_priority_distance_and_stove_first(self):
        """Nếu cùng khoảng cách trong interact_radius, bếp được chọn trước bàn."""
        pos = [5.0, 5.0]
        scenario = {
            "player": {"pos": pos},
            "stoves": [{"id": "B1", "pos": [5.0, 6.0], "state": "idle"}],
            "tables": [{"id": "T1", "pos": [5.0, 6.0]}],
            "stock": {"ca_loc": 1},
            "customers": [{"id": "C1", "table_id": "T1", "dish": "ca_loc_nuong_trui"}]
        }
        sim = QuanSim(self.tuning, scenario, self.streams, self.ids)
        events = sim.step(make_input(interact=True))
        # Chọn bếp trước bàn -> phát cook_started thay vì tương tác bàn
        self.assertTrue(any(ev[0] == "cook_started" for ev in events))


if __name__ == "__main__":
    unittest.main()
