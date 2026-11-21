"""PRD D–F black-box checks: schemas, deadlines, replay, pre-output rejection."""
import os
import unittest
from helpers import Workdir, events, frames, read_jsonl, run_headless, write_json


class QuanContract(unittest.TestCase):
    def test_no_dish_on_exact_schedule(self):
        with Workdir() as w:
            out=w.path("empty.jsonl")
            code,err=run_headless("--mode","quan","--seed","1","--ticks","1020","--out",out)
            self.assertEqual(code,0,err)
            self.assertEqual([(e["tick"],e["name"],e["data"]) for e in events(read_jsonl(out))],[(120,"no_dish",{}),(1020,"no_dish",{})])

    def test_real_timer_service_replay_is_byte_identical(self):
        with Workdir() as w:
            scenario=write_json(w.path("sc.json"),{"quan":{"stock":{"ca_loc":1},"random_customers":False,"player":{"pos":[2,8]},
                "customers":[{"id":"C1","table_id":"T1","dish_id":"ca_loc_nuong_trui"}]}})
            inputs=write_json(w.path("in.json"),frames({"tick":0,"interact":True},{"tick":1,"interact":False},
                {"tick":360,"interact":True},{"tick":361,"interact":False,"move":[1,-6/7]},
                {"tick":500,"move":[0,0]},{"tick":506,"interact":True},{"tick":507,"interact":False}))
            for i in range(2):
                code,err=run_headless("--mode","quan","--seed","42","--ticks","1200","--scenario",scenario,"--inputs",inputs,"--out",w.path(f"out{i}.jsonl"))
                self.assertEqual(code,0,err)
            rows=read_jsonl(w.path("out0.jsonl"))
            self.assertEqual([(e["tick"],e["name"]) for e in events(rows)],[(1,"cook_started"),(361,"dish_ready"),(361,"dish_picked"),(507,"served"),(1107,"paid")])
            self.assertEqual((rows[-1]["money"],rows[-1]["reputation"]),(72,3.2))
            with open(w.path("out0.jsonl"),"rb") as a,open(w.path("out1.jsonl"),"rb") as b:
                self.assertEqual(a.read(),b.read())

    def test_invalid_fixtures_exit_two_before_output(self):
        c={"id":"C1","table_id":"T1","dish_id":"ca_loc_nuong_trui"}
        food={"order_id":"C1","dish_id":"ca_loc_nuong_trui","base_price":60}
        assigned={**c,"order_status":"assigned"}
        cases=[{"customers":[{**c,"extra":1}],"stock":{"ca_loc":1}},
            {"tables":[{"id":"T1","extra":1}]},{"tables":[{"id":"T1","pos":[99,2]}]},
            {"stoves":[{"id":"B1","state":"broken"}]},{"stoves":[{"id":"B1","pos":[2,-1]}]},
            {"random_customers":1},{"reputation":float("nan")},{"reputation":6},
            {"customers":[{**c,"dish_id":[]}]},{"customers":[c]},
            {"customers":[{**c,"reserved":{"ca_loc":True}}],"stock":{"ca_loc":1}},
            {"customers":[assigned]},{"customers":[assigned],"hand":{**food,"base_price":-1}},
            {"customers":[assigned],"hand":{**food,"dish_id":"goi_bong_sung"}},
            {"customers":[assigned],"hand":food,"stoves":[{"id":"B1","state":"ready","dish":food}]},
            {"customers":[assigned],"stoves":[{"id":"B1","state":"cooking","dish":food,"cook_ticks_left":0}]},
            {"customers":[{**c,"state":"eating","order_status":"served","eat_ticks_left":1}]}]
        with Workdir() as w:
            for i,block in enumerate(cases):
                with self.subTest(block=block):
                    sc=write_json(w.path(f"bad{i}.json"),{"quan":block});out=w.path(f"bad{i}.jsonl")
                    code,err=run_headless("--mode","quan","--seed","1","--ticks","0","--scenario",sc,"--out",out)
                    self.assertEqual(code,2,err)
                    self.assertNotIn("Traceback",err)
                    self.assertFalse(os.path.exists(out))
