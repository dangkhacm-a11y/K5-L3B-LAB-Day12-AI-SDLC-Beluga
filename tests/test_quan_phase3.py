"""Tests Phase 3 Thành viên 2 (TICKET-03): Quán độ tươi cá thể, giữ chỗ theo ID, chốt giá và đơn đặt trước."""

from copy import deepcopy
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim


def act(interact=False):
    return InputState((0, 0), {}, {"interact"} if interact else set())


def v12_tuning(*, with_reservations=False, burn_s=None):
    t = deepcopy(load_contract()["tuning"])
    t["freshness"] = {
        "initial": 100,
        "gather_decay_per_s": 0.5,
        "quan_decay_per_s": 0.25,
        "spoiled_below": 30,
    }
    if with_reservations:
        t["reservations"] = {
            "count": 2,
            "table_hold_s": 30,
            "price_multiplier": 1.5,
            "failed_reputation_delta": -1,
        }
    if burn_s is not None:
        t["quan"]["burn_s"] = burn_s
    return t


class QuanFreshnessAndPricingTests(unittest.TestCase):
    def test_spoiled_exact_threshold_30_and_id_order(self):
        # 30.0 giảm 1/240 ở tick 1 -> < 30 (ươn đúng tick 1); 30.25 cần 61 tick mới < 30
        t = v12_tuning()
        sc = {
            "random_customers": False,
            "stock": [
                {"id": "I10", "kind": "ca_loc", "fresh": 30},
                {"id": "I2", "kind": "ca_linh", "fresh": 30},
                {"id": "I3", "kind": "ca_loc", "fresh": 30.25},
            ],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        evs1 = sim.step(act())
        self.assertEqual(evs1, [
            ("spoiled", {"item_id": "I2", "kind": "ca_linh", "location": "stock"}),
            ("spoiled", {"item_id": "I10", "kind": "ca_loc", "location": "stock"}),
        ])
        # Tick 2..60: I3 chạm đúng 30.0 ở tick 60 (chưa ươn!), không phát spoiled lặp cho I2/I10
        for _ in range(59):
            self.assertEqual(sim.step(act()), [])
        # Tick 61: I3 đi từ 30 xuống 7199/240 < 30 -> phát spoiled đúng tick 61
        evs61 = sim.step(act())
        self.assertEqual(evs61, [("spoiled", {"item_id": "I3", "kind": "ca_loc", "location": "stock"})])

    def test_freshest_tie_break_by_id_and_freshness_base_price_floor(self):
        # 3 cá lóc: I1(80), I10(90), I2(90) -> chọn I2 (tươi nhất 90, hòa chọn id nhỏ I2 < I10)
        # Bắt đầu nấu ở tick 1 -> I2 hao 1/240 -> 89 + 239/240 -> floor(60 * (89 + 239/240) / 100) = 53
        t = v12_tuning()
        sc = {
            "random_customers": False,
            "player": {"pos": [2, 8]},
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 80},
                {"id": "I10", "kind": "ca_loc", "fresh": 90},
                {"id": "I2", "kind": "ca_loc", "fresh": 90},
            ],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        self.assertEqual(sim.snapshot()["customers"][0]["reserved"], ["I2"])
        evs = sim.step(act(interact=True))
        self.assertEqual(evs[0][0], "cook_started")
        data = evs[0][1]
        self.assertEqual([it["id"] for it in data["items"]], ["I2"])
        self.assertEqual(data["base_price"], 53)
        # I2 đã bị tiêu khỏi kho, I1 và I10 còn nguyên
        self.assertEqual([it["id"] for it in sim.snapshot()["stock"]], ["I1", "I10"])

    def test_cook_started_items_sorted_by_kind_then_id_and_exact_avg_floor(self):
        # lau_ca_linh_dien_dien (price=120): ca_linh x3 + bong_dien_dien x1
        # Sau 1 tick: mỗi cá thể giảm 1/240. Dùng fresh=80 + 1/240 không biểu diễn thập phân; dùng 100 -> 99.995833 -> floor(120 * avg / 100) = 119
        t = v12_tuning()
        sc = {
            "random_customers": False,
            "player": {"pos": [2, 8]},
            "stock": [
                {"id": "I10", "kind": "ca_linh", "fresh": 100},
                {"id": "I2", "kind": "ca_linh", "fresh": 100},
                {"id": "I3", "kind": "ca_linh", "fresh": 100},
                {"id": "I5", "kind": "bong_dien_dien", "fresh": 100},
            ],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien"}],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        evs = sim.step(act(interact=True))
        items = evs[0][1]["items"]
        self.assertEqual([(it["kind"], it["id"]) for it in items], [
            ("bong_dien_dien", "I5"), ("ca_linh", "I2"), ("ca_linh", "I3"), ("ca_linh", "I10"),
        ])
        self.assertEqual(evs[0][1]["base_price"], 119)

    def test_spoil_rereserve_order_by_order_tick_then_table_id(self):
        # Hai đơn cùng bị ươn ở tick 1, nhưng kho chỉ còn 1 cá lóc tươi I5:
        # C_early (order_tick=1, T2) và C_late (order_tick=2, T1) -> C_early được giữ I5, C_late -> unfulfillable
        t = v12_tuning()
        sc = {
            "random_customers": False,
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 30},
                {"id": "I2", "kind": "ca_loc", "fresh": 30},
                {"id": "I5", "kind": "ca_loc", "fresh": 90},
            ],
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 1, "reserved": ["I1"]},
                {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 2, "reserved": ["I2"]},
            ],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        evs = sim.step(act())
        self.assertEqual([e[0] for e in evs], ["spoiled", "spoiled"])
        by_id = {c["id"]: c for c in sim.snapshot()["customers"]}
        self.assertEqual(by_id["C1"]["order_status"], "reserved")
        self.assertEqual(by_id["C1"]["reserved"], ["I5"])
        self.assertEqual(by_id["C2"]["order_status"], "unfulfillable")
        self.assertEqual(by_id["C2"]["reserved"], [])

    def test_invalid_v12_stock_and_reserved_conflicts_rejected(self):
        t = v12_tuning()
        # Kho đếm v1.1 bị từ chối khi freshness bật
        with self.assertRaises(BadInput):
            QuanSim(t, {"stock": {"ca_loc": 1}}, Streams(1), IdAllocator())
        # Cá thể đã ươn không được dùng trong reserved
        with self.assertRaises(BadInput):
            QuanSim(t, {
                "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 29}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}],
            }, Streams(1), IdAllocator())
        # Dùng chung cùng 1 ID giữa hai đơn -> BadInput
        with self.assertRaises(BadInput):
            QuanSim(t, {
                "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                    {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                ],
            }, Streams(1), IdAllocator())


class QuanReservationsTests(unittest.TestCase):
    def test_holding_at_tick_0_blocks_new_regular_customer_and_serves_with_multiplier_and_tip(self):
        # R1 đến ở tick 100 -> max(0, 100-1800) = 0 -> holding ngay từ snapshot tick 0
        t = v12_tuning(with_reservations=True)
        sc = {
            "random_customers": False,
            "player": {"pos": [2, 8]},
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 100},
                {"id": "I2", "kind": "ca_loc", "fresh": 100},
            ],
            "reservations": [{"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 10}],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        snap0 = sim.snapshot()
        self.assertEqual(snap0["reservations"][0]["state"], "holding")
        self.assertEqual(snap0["tables"][0]["reservation_id"], "R1")

        # Khách thường thử đến ở tick 5 -> không được ngồi T1 đang holding, phải ngồi T2!
        sim.random_customers = True
        sim.next_customer_tick = 5
        evs = []
        for _ in range(10):
            evs.extend(sim.step(act()))
        arr_regular = [d for n, d in evs if n == "customer_arrived" and d["order_id"] == "C1"]
        self.assertEqual(arr_regular[0]["table_id"], "T2")
        # Tick 10: R1 đến -> reservation_arrived rồi customer_arrived tại T1
        res_arr = [(n, d) for n, d in evs if n in ("reservation_arrived", "customer_arrived") and d.get("order_id") == "C2"]
        self.assertEqual([n for n, _ in res_arr], ["reservation_arrived", "customer_arrived"])
        self.assertEqual(sim.snapshot()["reservations"][0]["state"], "waiting")

        # Nấu món cho R1 (lấy đơn cũ nhất C1 trước hay chỉ để R1 nấu: bỏ C1 đi cho nhanh để test giá R1)
        sim.customers = [c for c in sim.customers if c.get("reservation_id") == "R1"]
        cook_evs = sim.step(act(interact=True))
        self.assertEqual(cook_evs[0][0], "cook_started")
        fresh_base = cook_evs[0][1]["base_price"]  # floor(60 * ~99.95 / 100) = 59
        # Đợi nấu xong (360 tick)
        for _ in range(360):
            sim.step(act())
        # Nhặt món tại B1 [2,8]
        self.assertEqual(sim.step(act(interact=True))[0][0], "dish_picked")
        # Di chuyển tới T1 [9,2] và phục vụ
        sim.pos = [9.0, 2.0]
        serve_evs = sim.step(act(interact=True))
        self.assertEqual([n for n, _ in serve_evs], ["served", "reservation_served"])
        expected_final = int(fresh_base * 1.5)  # floor(59 * 1.5) = 88
        expected_tip = int(expected_final * 0.2)  # floor(88 * 0.2) = 17
        self.assertEqual(serve_evs[0][1]["base_price"], expected_final)
        self.assertEqual(serve_evs[0][1]["tip"], expected_tip)
        self.assertEqual(serve_evs[1][1], {"reservation_id": "R1", "order_id": "C2", "base_price": expected_final})
        self.assertEqual(sim.snapshot()["reservations"][0]["state"], "served")

    def test_reservation_fail_occupied_and_stock_and_no_double_penalty(self):
        t = v12_tuning(with_reservations=True)
        # R1 đến T1 nhưng T1 đang có khách thường ngồi -> fail occupied (-1 rep)
        # R2 đến T2 trống nhưng kho rỗng -> fail stock (-1 rep)
        sc = {
            "random_customers": False,
            "stock": [],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "unfulfillable"}],
            "reservations": [
                {"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 2},
                {"id": "R2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 2},
            ],
            "time_left_ticks": 3,
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        sim.step(act())
        evs2 = sim.step(act())
        self.assertEqual(evs2, [
            ("reservation_failed", {"reservation_id": "R1", "reason": "occupied", "reputation": 2.0}),
            ("reservation_failed", {"reservation_id": "R2", "reason": "stock", "reputation": 1.0}),
        ])
        # Tick 3 đóng ca: R1, R2 đã failed nên KHÔNG bị phạt lặp khi closing!
        evs3 = sim.step(act())
        self.assertFalse(any(n == "reservation_failed" for n, _ in evs3))
        self.assertEqual(sim.reputation, 1.0)

    def test_reservation_fail_spoil_stock_and_patience_and_closing(self):
        t = v12_tuning(with_reservations=True)
        # Case 1: phần giữ của reservation vừa ươn, kho không còn đồ thay -> fail stock đúng 1 lần
        sc = {
            "random_customers": False,
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 30}],
            "reservations": [{"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 1, "state": "waiting"}],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                           "order_status": "reserved", "reserved": ["I1"], "reservation_id": "R1"}],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        evs = sim.step(act())
        self.assertEqual([n for n, _ in evs], ["spoiled", "reservation_failed"])
        self.assertEqual(evs[1][1], {"reservation_id": "R1", "reason": "stock", "reputation": 2.0})
        self.assertEqual(sim.customers, [])

        # Case 2: reservation hết kiên nhẫn -> reservation_failed("patience"), KHÔNG phát customer_left (-0.5)
        sc_pat = {
            "random_customers": False,
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
            "reservations": [{"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 1, "state": "waiting"}],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                           "order_status": "reserved", "reserved": ["I1"], "patience_ticks_left": 1, "reservation_id": "R1"}],
        }
        sim_p = QuanSim(t, sc_pat, Streams(1), IdAllocator())
        evs_p = sim_p.step(act())
        self.assertEqual(evs_p, [("reservation_failed", {"reservation_id": "R1", "reason": "patience", "reputation": 2.0})])
        self.assertEqual(sim_p.reputation, 2.0)

        # Case 3: đóng ca khi R1 (holding) và R2 (scheduled) chưa phục vụ -> fail theo id đặt
        sc_close = {
            "random_customers": False,
            "stock": [],
            "time_left_ticks": 1,
            "reservations": [
                {"id": "R2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 5000},
                {"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 100},
            ],
        }
        sim_c = QuanSim(t, sc_close, Streams(1), IdAllocator())
        evs_c = sim_c.step(act())
        self.assertEqual([(n, d.get("reservation_id"), d.get("reason")) for n, d in evs_c], [
            ("reservation_failed", "R1", "closing"),
            ("reservation_failed", "R2", "closing"),
            ("quan_end", None, "time"),
        ])
        self.assertEqual(sim_c.reputation, 1.0)

    def test_reservation_dish_burnt_emits_failed_before_reservation_failed(self):
        t = v12_tuning(with_reservations=True, burn_s=20)
        sc = {
            "random_customers": False,
            "stock": [],
            "reservations": [{"id": "R1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "arrival_tick": 1, "state": "waiting"}],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                           "order_status": "assigned", "base_price": 60, "reservation_id": "R1"}],
            "stoves": [{"id": "B1", "state": "ready", "ready_ticks": 1200,
                        "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}}],
        }
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        evs = sim.step(act())
        self.assertEqual(evs, [
            ("dish_burnt", {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui", "order_status": "failed"}),
            ("reservation_failed", {"reservation_id": "R1", "reason": "burnt", "reputation": 2.0}),
        ])
        self.assertEqual(sim.snapshot()["stoves"][0]["state"], "idle")
        self.assertEqual(sim.customers, [])


if __name__ == "__main__":
    unittest.main()
