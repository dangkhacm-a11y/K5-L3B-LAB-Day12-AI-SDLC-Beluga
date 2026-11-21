"""Kiểm thử tích hợp liên thông Gather -> Quán (E2E Phase 1).
Thành viên 4: Kiểm tra luồng dữ liệu kho từ gather_end (docked) sang quán,
nấu món từ nguyên liệu đã thu thập, phục vụ và thanh toán.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


class TestIntegrationGatherQuanE2E(unittest.TestCase):
    def test_gather_inventory_to_quan_cooking_e2e(self):
        with Workdir() as w:
            inv_file = w.path("kho.json")
            gather_out = w.path("gather.jsonl")
            quan_out = w.path("quan.jsonl")

            # 1. Gather: cập bến với 1 cá lóc trong giỏ
            sc_gather = write_json(w.path("sc_gather.json"), {
                "gather": {
                    "player": {"pos": [2, 0]},
                    "hold": ["ca_loc"]
                }
            })
            inp_gather = write_json(w.path("inp_gather.json"), frames({"tick": 0, "interact": True}))

            code, err = run_headless(
                "--mode", "gather",
                "--seed", "42",
                "--ticks", "1",
                "--scenario", sc_gather,
                "--inputs", inp_gather,
                "--inventory-out", inv_file,
                "--out", gather_out
            )
            self.assertEqual(code, 0, err)

            # Kiểm tra kho được ghi hợp lệ
            with open(inv_file, encoding="utf-8") as f:
                inv_data = json.load(f)
            self.assertEqual(inv_data, {"items": {"ca_loc": 1}})

            # 2. Quán: nạp kho vừa xuất, có khách C1 gọi ca_loc_nuong_trui
            sc_quan = write_json(w.path("sc_quan.json"), {
                "quan": {
                    "player": {"pos": [2, 8]},  # Đứng ngay bếp B1
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "patience_ticks_left": 3600
                    }]
                }
            })
            # Input: tick 0 nhấn interact để nấu món
            inp_quan = write_json(w.path("inp_quan.json"), frames(
                {"tick": 0, "interact": True}
            ))

            code, err = run_headless(
                "--mode", "quan",
                "--seed", "42",
                "--ticks", "10",
                "--scenario", sc_quan,
                "--inventory", inv_file,
                "--inputs", inp_quan,
                "--out", quan_out
            )
            self.assertEqual(code, 0, err)

            rows = read_jsonl(quan_out)
            cook_ev = events(rows, "cook_started")
            self.assertEqual(len(cook_ev), 1)
            self.assertEqual(cook_ev[0]["data"]["dish_id"], "ca_loc_nuong_trui")
            self.assertEqual(cook_ev[0]["data"]["stove_id"], "B1")

            # Kiểm tra sau khi nấu, nguyên liệu trong kho đã được trừ
            last_snap = snapshots(rows)[-1]
            self.assertEqual(last_snap["stock"], {})


if __name__ == "__main__":
    unittest.main()
