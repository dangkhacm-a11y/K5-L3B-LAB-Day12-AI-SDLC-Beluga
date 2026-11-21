"""Tests Phase 4 Thành viên 2: HUD 3 cảnh báo (thủy quái gần, oxy sắp hết, khách sắp giận), tương phản cao và phụ đề SFX khi tắt tiếng."""

import json
import math
import unittest
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


class Phase4AlertsAndAccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_html_contains_three_alerts_high_contrast_mute_and_sfx_subtitles(self):
        server = LiveServer(LiveGame("gather", self.tuning, {}, 1), port=0)
        server.start()
        try:
            code, raw = _get(f"http://127.0.0.1:{server.port}/")
            self.assertEqual(code, 200)
            html = raw.decode("utf-8")
            # 3 cảnh báo chữ + biểu tượng
            self.assertIn("THỦY QUÁI GẦN!", html)
            self.assertIn("OXY SẮP HẾT!", html)
            self.assertIn("HẾT HƠI! NGẠT!", html)
            self.assertIn("KHÁCH SẮP GIẬN!", html)
            # Nút & CSS chế độ tương phản cao, tắt âm thanh, phụ đề SFX
            for token in ("btn-hc", "btn-mute", "btn-sub", "subtitle-box", "alert-bar", "body.hc", "SFX_LABELS"):
                self.assertIn(token, html)
        finally:
            server.stop()

    def test_gather_state_exposes_monster_near_and_low_oxygen_alerts(self):
        # Đặt Út Sen ở [58, 24] (cách M1 [60, 24] chỉ 2m <= 10m) và oxy còn 300/1800 (< 25%)
        sc = {"player": {"pos": [58, 24], "oxygen_ticks": 300}, "random_fish": False}
        game = LiveGame("gather", self.tuning, sc, 1)
        state = json.loads(game.state_json())
        p = state["player"]
        self.assertLess(p["oxygen_ticks"] / p["oxygen_max_ticks"], 0.25)
        m1 = state["monsters"][0]
        dist = math.dist(p["pos"], m1["pos"])
        self.assertLessEqual(dist, state["meta"]["monsters"]["species"]["ca_sau"]["detect_radius"])

    def test_quan_state_exposes_angry_customer_alert(self):
        # Khách ở T1 còn 400/3600 tick kiên nhẫn (< 25%) -> kích hoạt cảnh báo KHÁCH SẮP GIẬN!
        sc = {
            "random_customers": False,
            "stock": {"ca_loc": 1},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_status": "reserved", "patience_ticks_left": 400,
            }],
        }
        game = LiveGame("quan", self.tuning, sc, 1)
        state = json.loads(game.state_json())
        pat_max = state["meta"]["patience_s"] * 60
        c = state["customers"][0]
        self.assertEqual(c["state"], "waiting")
        self.assertLess(c["patience_ticks_left"] / pat_max, 0.25)


if __name__ == "__main__":
    unittest.main()
