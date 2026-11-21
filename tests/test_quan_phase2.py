"""Member 3 / TICKET-02: menu, nhiều bếp/bàn và interface kế hoạch ngày.

Chuẩn bị cho người dùng chạy; không phải bằng chứng test đã đạt.
"""

from copy import deepcopy
import unittest

from chonoi.contract import load_contract, validate_tuning
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.inventory import read_inventory, write_inventory
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim
from helpers import Workdir


def action(interact=False):
    return InputState((0, 0), {}, {"interact"} if interact else set())


class QuanPhase2(unittest.TestCase):
    def setUp(self):
        self.tuning = deepcopy(load_contract()["tuning"])

    def sim(self, scenario=None, **kwargs):
        return QuanSim(self.tuning, scenario or {}, Streams(42), IdAllocator(), **kwargs)

    def test_ticket_menu_and_layout(self):
        self.assertEqual(self.tuning["quan"]["stoves"], [
            {"id": "B1", "pos": [2, 8]}, {"id": "B2", "pos": [5, 8]}])
        self.assertEqual(self.tuning["quan"]["tables"], [
            {"id": "T1", "pos": [9, 2]}, {"id": "T2", "pos": [13, 2]},
            {"id": "T3", "pos": [9, 6]}, {"id": "T4", "pos": [13, 6]}])
        self.assertEqual(self.tuning["menu"], {
            "ca_loc_nuong_trui": {"recipe": {"ca_loc": 1}, "cook_s": 6, "price": 60},
            "goi_bong_sung": {"recipe": {"bong_sung": 2}, "cook_s": 4, "price": 40},
            "lau_ca_linh_dien_dien": {"recipe": {"ca_linh": 3, "bong_dien_dien": 1}, "cook_s": 10, "price": 120},
            "canh_chua_ca_loc": {"recipe": {"ca_loc": 1, "bong_dien_dien": 1}, "cook_s": 8, "price": 90},
            "ca_keo_nuong": {"recipe": {"ca_keo": 2}, "cook_s": 6, "price": 70},
            "lau_mam": {"recipe": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}, "cook_s": 12, "price": 200},
        })

    def test_four_seats_fill_on_schedule_and_skip_when_full(self):
        sim = self.sim({"stock": {"ca_loc": 5}})
        arrivals = []
        for tick in range(1, 3721):
            events = sim.step(action())
            arrivals.extend((tick, data["table_id"]) for name, data in events if name == "customer_arrived")
        # T1 rời ở 3720 trước lượt mới, sau khi cả bốn ghế từng được lấp.
        self.assertEqual(arrivals, [(120, "T1"), (1020, "T2"), (1920, "T3"), (2820, "T4"), (3720, "T1")])
        sim = self.sim({"stock": {"ca_loc": 5}, "customers": [
            {"id": f"C{i}", "table_id": f"T{i}", "dish_id": "ca_loc_nuong_trui"}
            for i in range(1, 5)]})
        for _ in range(120):
            events = sim.step(action())
        self.assertEqual(events, [])
        self.assertEqual(len(sim.customers), 4)

    def test_day_filter_ignores_planned_serving_limit_and_reservations(self):
        sim = self.sim({"stock": {"ca_loc": 3, "ca_keo": 2, "bong_dien_dien": 2}},
                       allowed_dishes={"ca_loc_nuong_trui": 1})
        events = []
        for _ in range(2820):
            events.extend(sim.step(action()))
        self.assertEqual([data["dish_id"] for name, data in events if name == "customer_arrived"],
                         ["ca_loc_nuong_trui"] * 3)
        self.assertEqual([name for name, _ in events].count("no_dish"), 1)
        self.assertEqual(sim.stock["ca_loc"], 3)  # Giữ chỗ chưa tiêu kho.
        self.assertEqual(sim.available_stock(), {"ca_keo": 2, "bong_dien_dien": 2})

    def test_standalone_can_order_every_dish(self):
        for dish_id, dish in self.tuning["menu"].items():
            with self.subTest(dish_id=dish_id):
                # Tìm seed cho lượt chọn chính món này trong tập món khả dụng.
                for seed in range(100):
                    sim = QuanSim(self.tuning, {"stock": dish["recipe"]}, Streams(seed), IdAllocator())
                    for _ in range(120):
                        events = sim.step(action())
                    if events[0][1]["dish_id"] == dish_id:
                        break
                self.assertEqual(events[0], ("customer_arrived", {
                    "order_id": "C1", "table_id": "T1", "dish_id": dish_id}))

    def test_plan_order_does_not_change_seeded_choice(self):
        scenario = {"stock": {"ca_loc": 2, "bong_dien_dien": 2, "bong_sung": 4}}
        dishes = {"canh_chua_ca_loc": 1, "ca_loc_nuong_trui": 1, "goi_bong_sung": 1}
        a = self.sim(scenario, allowed_dishes=dishes)
        b = self.sim(scenario, allowed_dishes=dict(reversed(list(dishes.items()))))
        b.rng.get("fish_spawn").random()
        for _ in range(1020):
            self.assertEqual(a.step(action()), b.step(action()))
        self.assertEqual(a.snapshot(), b.snapshot())

    def test_two_stoves_cook_oldest_then_table_id_and_cleanup(self):
        sim = self.sim({"stock": {"ca_loc": 2}, "random_customers": False,
                        "player": {"pos": [2, 8]}, "time_left_ticks": 3,
                        "customers": [
                            {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui"},
                            {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]})
        self.assertEqual(sim.step(action(True))[0][1]["order_id"], "C2")
        sim.pos = [5, 8]
        self.assertEqual(sim.step(action(True))[0][1]["order_id"], "C1")
        self.assertEqual([st["state"] for st in sim.snapshot()["stoves"]], ["cooking", "cooking"])
        self.assertEqual(sim.available_stock(), {})
        self.assertEqual([name for name, _ in sim.step(action())], ["customer_left", "customer_left", "quan_end"])
        self.assertEqual(sim.customers, [])
        self.assertEqual([st["state"] for st in sim.stoves], ["idle", "idle"])
        self.assertEqual(sim.reputation, 3)

    def test_six_ingredient_inventory_roundtrip_and_new_dish(self):
        stock = {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1,
                 "ca_loc": 1, "bong_sung": 2}
        with Workdir() as w:
            path = w.path("inventory.json")
            write_inventory(path, stock)
            sim = self.sim({"player": {"pos": [2, 8]}, "random_customers": False,
                            "customers": [{"id": "C1", "table_id": "T4", "dish_id": "lau_mam"}]},
                           inventory=read_inventory(path), allowed_dishes={"lau_mam": 1})
        self.assertEqual(sim.snapshot()["stock"], stock)
        event = sim.step(action(True))[0]
        self.assertEqual(event[0], "cook_started")
        self.assertEqual(event[1]["base_price"], 200)
        self.assertEqual(sim.stoves[0]["cook_ticks_left"], 720)
        self.assertEqual(sim.available_stock(), {"ca_loc": 1, "bong_sung": 2})

    def test_invalid_filter_and_day_fixture_rejected(self):
        for allowed in ("ca_loc_nuong_trui", ["unknown"], [None]):
            with self.subTest(allowed=allowed), self.assertRaises(BadInput):
                self.sim(allowed_dishes=allowed)
        fixture = {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]}
        with self.assertRaises(BadInput):
            self.sim(fixture, inventory={"ca_loc": 1}, allowed_dishes=["ca_keo_nuong"])
        with self.assertRaises(BadInput):
            self.sim(fixture, inventory={}, allowed_dishes=["ca_loc_nuong_trui"])

    def test_invalid_tuning_rejected(self):
        for recipe in ({}, {"ca_keo": 0}, {"keo_neo": True}, {"unknown": 1}):
            with self.subTest(recipe=recipe), self.assertRaises(BadInput):
                tuning = deepcopy(self.tuning)
                tuning["menu"]["lau_mam"]["recipe"] = recipe
                validate_tuning(tuning)
        tuning = deepcopy(self.tuning)
        tuning["quan"]["stoves"][1]["id"] = "B1"
        with self.assertRaises(BadInput):
            validate_tuning(tuning)
