"""Test cửa sổ chơi trực tiếp (chonoi.live). Chỉ dành cho starter Python: nhóm đổi ngôn ngữ thì xóa file này."""

import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.inventory import read_inventory
from chonoi.live import LiveGame, LiveServer


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        e.close()
        return e.code


class LiveServerTest(unittest.TestCase):
    def test_http_gather_transitions_to_playable_quan_with_saved_stock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "kho.json")
            game = LiveGame("gather", load_contract()["tuning"],
                            {"hold": ["ca_loc", "bong_sung", "bong_sung"]}, 1,
                            inventory_out=path)
            server = LiveServer(game, port=0)
            server.start()
            try:
                self.assertEqual(_post(server.url + "input", {"interact": True}), 200)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    state = json.loads(_get(server.url + "state")[1])
                    if state["mode"] == "quan":
                        break
                    time.sleep(0.01)
                self.assertEqual(state["mode"], "quan")
                self.assertFalse(state["finished"])
                self.assertEqual(state["stock"], {"ca_loc": 1, "bong_sung": 2})
                self.assertEqual(read_inventory(path), {"ca_loc": 1, "bong_sung": 2})
                self.assertIsNone(state["error"])
                code, html = _get(server.url)
                self.assertEqual(code, 200)
                self.assertIn(b"<canvas", html)
            finally:
                server.stop()

    def test_quan_page_is_served(self):
        server = LiveServer(LiveGame("quan", load_contract()["tuning"], {}, 1), port=0)
        server.start()
        try:
            code, html = _get(server.url)
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
        finally:
            server.stop()

    def test_state_input_and_clean_stop(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)  # cổng ngẫu nhiên
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertIn("tick", st)
            self.assertEqual(st["mode"], "gather")
            self.assertEqual(st["player"]["pos"], [2, 0])
            self.assertEqual(_post(base + "/input", {"move": [1, 0], "interact": False, "catch": False}), 200)
            self.assertEqual(_post(base + "/input", {"move": [5, 0]}), 400)
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
            code, png = _get(base + "/assets/kenney_fish/fish_blue_outline.png")
            self.assertEqual(code, 200)
            self.assertTrue(png.startswith(b"\x89PNG"))
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                _get(base + "/assets/../index.html")
            self.assertEqual(ctx.exception.code, 404)
            deadline = time.time() + 3
            while time.time() < deadline:
                st2 = json.loads(_get(base + "/state")[1])
                if st2["tick"] > st["tick"] + 3 and st2["player"]["pos"][0] > st["player"]["pos"][0]:
                    break
                time.sleep(0.05)
            self.assertGreater(st2["tick"], st["tick"], "mô phỏng phải chạy nền")
            self.assertGreater(st2["player"]["pos"][0], st["player"]["pos"][0], "input phải tác động tới sim")
        finally:
            server.stop()
        self.assertFalse(server.game._thread.is_alive())
        self.assertFalse(server._thread.is_alive())


class LiveGatherTransitionTest(unittest.TestCase):
    def test_fresh_items_transfer_with_ids_and_available_counts(self):
        tuning = load_contract()["tuning"]
        tuning["freshness"] = {
            "initial": 100, "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25, "spoiled_below": 30,
        }
        cases = [
            ({}, True, "docked", 1),
            ({"time_left_ticks": 1}, False, "time", 1),
            ({"player": {"hp": 0}}, False, "fainted", 0),
        ]
        for extra, interact, reason, count in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "inventory.json")
                scenario = {"hold": [{"id": "I9", "kind": "ca_loc", "fresh": 75}], **extra}
                game = LiveGame("gather", tuning, scenario, 1, inventory_out=path)
                game.set_input({"interact": interact})
                game._tick_once()
                state = json.loads(game.state_json())
                self.assertEqual(state["mode"], "quan")
                self.assertIsNone(state["error"])
                self.assertEqual(state["available_stock"], {"ca_loc": 1} if count else {})
                self.assertEqual(read_inventory(path), state["stock"])
                if count:
                    self.assertEqual(state["stock"][0]["id"], "I9")
                    self.assertAlmostEqual(state["stock"][0]["fresh"], 75 - 0.5 / 60)
                    # Arrival reserves the only fish by ID; the live HUD must still serialize.
                    game.session.sim.random_reservations = False
                    for _ in range(tuning["quan"]["first_customer_tick"]):
                        game._tick_once()
                    state = json.loads(game.state_json())
                    self.assertEqual(len(state["customers"]), 1)
                    self.assertEqual(state["customers"][0]["reserved"], ["I9"])
                    self.assertEqual(state["available_stock"], {})
                else:
                    self.assertEqual(state["stock"], [])

    def test_gather_end_saves_and_transfers_stock_for_every_end_reason(self):
        cases = [
            ({"hold": ["ca_loc", "ca_loc", "ca_keo", "keo_neo"]}, True,
             "docked", {"ca_loc": 2, "ca_keo": 1, "keo_neo": 1}),
            ({"hold": ["bong_sung"], "time_left_ticks": 1}, False,
             "time", {"bong_sung": 1}),
            ({"hold": ["ca_loc"], "player": {"hp": 0}}, False,
             "fainted", {}),
        ]
        for scenario, interact, reason, expected in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "kho.json")
                with open(path, "w", encoding="utf-8") as f:
                    f.write('{"items":{"ca_linh":9}}')
                game = LiveGame("gather", load_contract()["tuning"], scenario, 1,
                                inventory_out=path)
                self.assertEqual(read_inventory(path), {"ca_linh": 9})
                game.set_input({"interact": interact})
                game._tick_once()
                self.assertEqual(game.mode, "quan")
                state = json.loads(game.state_json())
                self.assertEqual(state["mode"], "quan")
                self.assertEqual(state["tick"], 0)
                self.assertFalse(state["finished"])
                self.assertEqual(state["stock"], expected)
                self.assertEqual(state["available_stock"], expected)
                self.assertIn("menu", state["meta"])
                end = next(e for e in state["events"] if e["name"] == "gather_end")
                self.assertEqual(end["data"], {"reason": reason, "inventory": {"items": expected}})
                self.assertEqual(read_inventory(path), expected)
                # Cooking must not overwrite the saved gather inventory on later ticks.
                game.session.sim.stock.clear()
                game._tick_once()
                self.assertEqual(read_inventory(path), expected)
                game.restart()
                self.assertEqual(json.loads(game.state_json())["mode"], "gather")

    def test_default_inventory_file_is_written_without_cli_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                game = LiveGame("gather", load_contract()["tuning"], {"hold": ["ca_loc"]}, 1)
                game._tick_once()
                self.assertFalse(os.path.exists("inventory.json"))
                self.assertEqual(game.mode, "gather")
                game.set_input({"interact": True})
                game._tick_once()
                self.assertEqual(read_inventory("inventory.json"), {"ca_loc": 1})
                self.assertEqual(json.loads(game.state_json())["stock"], {"ca_loc": 1})
            finally:
                os.chdir(previous)

    def test_failed_save_keeps_gather_inventory_and_retries_before_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "missing")
            path = os.path.join(folder, "kho.json")
            game = LiveGame("gather", load_contract()["tuning"], {"hold": ["ca_loc"]}, 1,
                            inventory_out=path)
            game.set_input({"interact": True})
            game._tick_once()
            state = json.loads(game.state_json())
            self.assertEqual(state["mode"], "gather")
            self.assertEqual(state["hold"], ["ca_loc"])
            self.assertTrue(state["error"])
            os.mkdir(folder)
            game._tick_once()
            state = json.loads(game.state_json())
            self.assertEqual(state["mode"], "quan")
            self.assertIsNone(state["error"])
            self.assertEqual(state["stock"], {"ca_loc": 1})
            self.assertEqual(read_inventory(path), {"ca_loc": 1})


if __name__ == "__main__":
    unittest.main()
