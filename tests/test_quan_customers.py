"""PRD-0 D–F boundary and customer reservation regressions."""
import copy
import unittest
from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inputs import InputState
from chonoi.runner import Session


def action(interact=False):
    return InputState((0, 0), {}, {"interact"} if interact else set())


class QuanCustomers(unittest.TestCase):
    def setUp(self):
        self.tuning = copy.deepcopy(load_contract()["tuning"])
        self.tuning["quan"].update(first_customer_tick=2, customer_interval_s=2/60, patience_s=4/60, eat_s=2/60)
        self.tuning["menu"]["ca_loc_nuong_trui"]["cook_s"] = 2/60

    def session(self, scenario=None):
        return Session("quan", self.tuning, scenario or {}, 1)

    def customer(self, **updates):
        return {"id":"C9", "table_id":"T1", "dish_id":"ca_loc_nuong_trui", **updates}

    def food(self, **updates):
        return {"order_id":"C9", "dish_id":"ca_loc_nuong_trui", "base_price":60, **updates}

    def test_arrival_schedule_payload_defaults_and_stock(self):
        s = self.session({"stock":{"ca_loc":1}, "player":{"pos":[2,8]}})
        self.assertEqual(s.step(action()), [])
        self.assertEqual([(e["name"],e["data"]) for e in s.step(action(True))], [("customer_arrived",{"order_id":"C1","table_id":"T1","dish_id":"ca_loc_nuong_trui"})])
        c = s.sim.customers[0]
        self.assertEqual((c["order_tick"],c["order_status"],c["patience_ticks_left"],c["reserved"]),(2,"reserved",4,{"ca_loc":1}))
        self.assertEqual(s.sim.stock, {"ca_loc":1})
        self.assertEqual(s.sim.stock["ca_loc"] - c["reserved"]["ca_loc"], 0)
        self.assertEqual(s.sim.stoves[0]["state"], "idle")

    def test_no_dish_empty_event_and_disabled_arrivals(self):
        s=self.session()
        s.step(action())
        self.assertEqual([(e["name"],e["data"]) for e in s.step(action())],[("no_dish",{})])
        self.assertEqual(s.sim.reputation,3)
        s=self.session({"random_customers":False})
        for _ in range(5):
            self.assertEqual(s.step(action()),[])

    def test_timeout_releases_before_arrival_and_continues_ids(self):
        s=self.session({"stock":{"ca_loc":1},"customers":[self.customer(patience_ticks_left=2)]})
        s.step(action())
        events=s.step(action())
        self.assertEqual([e["name"] for e in events],["customer_left","customer_arrived"])
        self.assertEqual(events[0]["data"],{"order_id":"C9","table_id":"T1","reason":"patience","reputation":2.5})
        self.assertEqual(s.sim.customers[0]["id"],"C10")

    def test_reservations_and_numeric_table_order_prevent_overbooking(self):
        self.tuning["quan"]["tables"]=[{"id":"T10","pos":[12,2]},{"id":"T2","pos":[9,2]}]
        s=self.session({"stock":{"ca_loc":1}})
        for _ in range(3): s.step(action())
        self.assertEqual(s.step(action())[0]["name"],"no_dish")
        self.assertEqual(s.sim.customers[0]["table_id"],"T2")

    def test_full_table_skips_without_consuming_id(self):
        # Fixture cố ý một bàn; preset Phase 2 có bốn bàn nên không còn đầy.
        self.tuning["quan"]["tables"] = self.tuning["quan"]["tables"][:1]
        s=self.session({"stock":{"ca_loc":2},"customers":[self.customer()]})
        s.step(action())
        self.assertEqual(s.step(action()),[])
        s.step(action());s.step(action())
        self.assertEqual(s.sim.customers[0]["id"],"C10")

    def test_fixture_not_mutated_and_reservation_inferred(self):
        scenario={"stock":{"ca_loc":1},"customers":[self.customer()]}
        original=copy.deepcopy(scenario)
        s=self.session(scenario)
        self.assertEqual(s.sim.customers[0]["reserved"],{"ca_loc":1})
        s.step(action())
        self.assertEqual(scenario,original)

    def test_bad_reservation_state_and_links(self):
        for c in (self.customer(reserved={}),self.customer(order_status="assigned"),self.customer(state="assigned"),
                  self.customer(order_tick=True),self.customer(state="eating",order_status="served",eat_ticks_left=1)):
            with self.subTest(c=c),self.assertRaises(BadInput):
                self.session({"stock":{"ca_loc":1},"customers":[c]})

    def test_unfulfillable_cannot_reserve_or_cook(self):
        s=self.session({"customers":[self.customer(order_status="unfulfillable")],"player":{"pos":[2,8]},"random_customers":False})
        self.assertEqual(s.sim.customers[0]["reserved"],{})
        self.assertEqual(s.step(action(True)),[])

    def test_seeded_choice_ignores_dict_order_and_other_streams(self):
        stock={"ca_loc":2,"bong_sung":4,"ca_linh":6,"bong_dien_dien":2}
        a=self.session({"stock":stock})
        self.tuning["menu"]=dict(reversed(list(self.tuning["menu"].items())))
        b=self.session({"stock":stock});b.sim.rng.get("fish_spawn").random()
        for _ in range(2): a.step(action());b.step(action())
        self.assertEqual(a.sim.customers,b.sim.customers)
        self.assertEqual(len(a.sim.customers),1)

    def test_service_payloads_timer_and_single_inventory_deduction(self):
        self.tuning["quan"]["patience_s"]=100/60
        s=self.session({"stock":{"ca_loc":1},"customers":[self.customer()],"player":{"pos":[2,8]},"random_customers":False})
        event=s.step(action(True))[0]
        self.assertEqual(event["data"],{"stove_id":"B1","order_id":"C9","dish_id":"ca_loc_nuong_trui","items":["ca_loc"],"base_price":60})
        self.assertEqual(s.sim.stock.get("ca_loc",0),0)
        self.assertEqual(s.sim.customers[0]["order_status"],"assigned")
        s.step(action())
        self.assertEqual([e["name"] for e in s.step(action(True))],["dish_ready","dish_picked"])
        self.assertEqual(s.sim.hand,self.food())
        s.sim.pos=[9,2]
        self.assertEqual(s.step(action(True))[0]["data"],{"order_id":"C9","table_id":"T1","dish_id":"ca_loc_nuong_trui","patience_ticks_left":96,"base_price":60,"tip":12})
        s.step(action());self.assertEqual(s.sim.money,0)
        self.assertEqual(s.step(action())[0]["data"],{"order_id":"C9","table_id":"T1","base_price":60,"tip":12,"amount":72,"reason":"finished_eating"})
        self.assertEqual((s.sim.money,s.sim.earned,s.sim.shift_earned,s.sim.reputation),(72,72,72,3.2))

    def test_assigned_timeout_discards_stove_and_hand_without_refund(self):
        for place in ("hand","ready","cooking"):
            scenario={"customers":[self.customer(order_status="assigned",patience_ticks_left=1)],"random_customers":False,"reputation":.1}
            if place=="hand":scenario["hand"]=self.food()
            else:scenario["stoves"]=[{"id":"B1","state":place,"dish":self.food(),"cook_ticks_left":2 if place=="cooking" else 0}]
            s=self.session(scenario)
            self.assertEqual(s.step(action())[0]["name"],"customer_left")
            self.assertEqual((s.sim.hand,s.sim.customers,s.sim.stock,s.sim.reputation),(None,[],{},0))
            self.assertEqual(s.sim.stoves[0]["state"],"idle")

    def test_service_at_last_patience_or_closing_tick(self):
        for closing in (False,True):
            scenario={"customers":[self.customer(order_status="assigned",patience_ticks_left=1)],"hand":self.food(),"player":{"pos":[9,2]},"random_customers":False}
            if closing:scenario["time_left_ticks"]=1
            s=self.session(scenario);events=s.step(action(True))
            self.assertEqual([e["name"] for e in events],["served","paid","quan_end"] if closing else ["served"])
            if closing:self.assertEqual(events[1]["data"]["reason"],"closing")
            else:s.step(action());s.step(action())
            self.assertEqual((s.sim.money,s.sim.reputation),(60,3))

    def test_tip_floor_uses_post_decrement_patience_and_locked_price(self):
        for patience,want in ((3,14),(2,0)):
            s=self.session({"customers":[self.customer(order_status="assigned",patience_ticks_left=patience)],"hand":self.food(base_price=73),"player":{"pos":[9,2]},"random_customers":False})
            data=s.step(action(True))[0]["data"]
            self.assertEqual((data["base_price"],data["tip"]),(73,want))

    def test_cooking_uses_order_age_then_table_id(self):
        self.tuning["quan"]["tables"]=[{"id":"T10","pos":[12,2]},{"id":"T2","pos":[9,2]}]
        for age,want in ((0,"C10"),(1,"C1")):
            s=self.session({"stock":{"ca_loc":2},"player":{"pos":[2,8]},"random_customers":False,"customers":[
                self.customer(id="C1",table_id="T10",order_tick=0),self.customer(id="C10",table_id="T2",order_tick=age)]})
            self.assertEqual(s.step(action(True))[0]["data"]["order_id"],want)

    def test_radius_edge_and_unusable_target_does_not_fall_through(self):
        s=self.session({"stock":{"ca_loc":1},"customers":[self.customer()],"player":{"pos":[3.5,8]},"random_customers":False})
        self.assertEqual(s.step(action(True))[0]["name"],"cook_started")
        self.tuning["quan"]["tables"][0]["pos"]=[2,8]
        s=self.session({"customers":[self.customer(order_status="assigned")],"hand":self.food(),"player":{"pos":[2,8]},"random_customers":False})
        self.assertEqual(s.step(action(True)),[])

    def test_ready_age_and_same_tick_pickup(self):
        scenario={"customers":[self.customer(order_status="assigned")],"player":{"pos":[2,8]},"random_customers":False,"stoves":[{"id":"B1","state":"cooking","dish":self.food(),"cook_ticks_left":1}]}
        s=self.session(scenario)
        self.assertEqual([e["name"] for e in s.step(action(True))],["dish_ready","dish_picked"])
        s=self.session(scenario);s.step(action())
        self.assertEqual(s.sim.stoves[0]["ready_ticks"],0)
        s.step(action());self.assertEqual(s.sim.stoves[0]["ready_ticks"],1)

    def test_closing_waiter_has_no_penalty_and_one_end(self):
        s=self.session({"customers":[self.customer(order_status="assigned",patience_ticks_left=1)],"hand":self.food(),"time_left_ticks":1})
        events=s.step(action())
        self.assertEqual(events[0]["data"],{"order_id":"C9","table_id":"T1","reason":"closing","reputation":3})
        self.assertEqual([e["name"] for e in events],["customer_left","quan_end"])
        self.assertEqual((s.sim.hand,s.sim.customers),(None,[]))
        self.assertEqual(s.step(action()),[])

    def test_departures_by_table_and_repeated_tip_score(self):
        self.tuning["quan"]["tables"]=[{"id":f"T{i}","pos":[9,2]} for i in range(1,6)]
        s=self.session({"reputation":1,"random_customers":False,"customers":[self.customer(id=f"C{6-i}",table_id=f"T{i}",state="eating",order_status="served",eat_ticks_left=1,base_price=60,tip=12) for i in range(1,6)]})
        self.assertEqual([e["data"]["order_id"] for e in s.step(action())],["C5","C4","C3","C2","C1"])
        self.assertEqual((s.snapshot()["score"],s.sim.reputation),(560,2))

    def test_ascii_suffix_only_and_shortened_shift(self):
        s=self.session({"stock":{"ca_loc":1},"customers":[self.customer(id="C١",patience_ticks_left=1)]})
        s.step(action());s.step(action());self.assertEqual(s.sim.customers[0]["id"],"C1")
        s=self.session({"stock":{"ca_loc":1},"time_left_ticks":2})
        s.step(action());self.assertEqual([e["name"] for e in s.step(action())],["quan_end"])
        self.assertEqual(s.sim.customers,[])
