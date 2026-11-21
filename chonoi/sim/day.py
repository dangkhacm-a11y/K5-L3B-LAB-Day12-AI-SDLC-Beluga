import copy
import math
from ..ids import IdAllocator
from ..rng import Streams
from .gather import GatherSim
from .quan import QuanSim

DEFAULT_DAY_PLANS = [
    {"day": 1, "dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3}, "ingredients": {"ca_loc": 3, "bong_sung": 6}},
    {"day": 2, "dishes": {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2}, "ingredients": {"ca_loc": 2, "ca_linh": 6, "bong_dien_dien": 2}},
    {"day": 3, "dishes": {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2}, "ingredients": {"bong_sung": 4, "ca_loc": 2, "bong_dien_dien": 2, "ca_keo": 4}},
    {"day": 4, "dishes": {"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1}, "ingredients": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1, "ca_loc": 2, "bong_sung": 2}},
    {"day": 5, "dishes": {"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1}, "ingredients": {"ca_linh": 5, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 2, "ca_loc": 1}},
]

DEFAULT_SHOP_UPGRADES = {
    "oxygen": [
        {"level": 1, "price": 200, "oxygen_max_s": 45},
        {"level": 2, "price": 400, "oxygen_max_s": 60}
    ],
    "hp": [
        {"level": 1, "price": 250, "hp_max": 4},
        {"level": 2, "price": 500, "hp_max": 5}
    ]
}


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.scenario = scenario
        self.rng = streams
        self.ids = ids
        self.target_days = max(1, int(days))
        self.day = 1
        self.days_completed = 0

        sc_day = scenario.get("day", {})
        self.money = sc_day.get("money", 0)
        self.earned = sc_day.get("earned", 0)
        self.reputation = float(sc_day.get("reputation", tuning.get("quan", {}).get("reputation_initial", 3.0)))
        self.upgrades = dict(sc_day.get("upgrades", {}))
        self.active_upgrades = dict(self.upgrades)

        # Kế hoạch ngày
        self.day_plans = self._load_day_plans(sc_day)
        # Nâng cấp Shop
        self.shop_upgrades = tuning.get("shop", {}).get("upgrades", DEFAULT_SHOP_UPGRADES)

        self.stock = {}
        self.sim_tick = 0
        self.phase_tick = 0
        self.paused = False
        self.done = False
        self.reason = None
        self.phase = "gather"
        self.shop_time_left = 600

        self.gather_sim = None
        self.quan_sim = None

        self._init_current_day(initial=True)

    def _load_day_plans(self, sc_day):
        plans = copy.deepcopy(DEFAULT_DAY_PLANS)
        overrides = sc_day.get("day_plan")
        if overrides:
            by_day = {p["day"]: p for p in plans}
            for op in overrides:
                d = op["day"]
                if d in by_day:
                    by_day[d] = copy.deepcopy(op)
                    if "ingredients" not in by_day[d]:
                        by_day[d]["ingredients"] = self._compute_ingredients(by_day[d].get("dishes", {}))
            plans = [by_day[i] for i in range(1, 6) if i in by_day]
        return plans

    def _compute_ingredients(self, dishes):
        menu = self.tuning.get("menu", {})
        ing_total = {}
        for dish_id, count in dishes.items():
            recipe = menu.get(dish_id, {}).get("recipe", {})
            for ing, qty in recipe.items():
                ing_total[ing] = ing_total.get(ing, 0) + qty * count
        return {k: ing_total[k] for k in sorted(ing_total)}

    def get_plan_for_day(self, day_num):
        # Contract 1.3 soak replays the five-day plan after day five.
        plan_day = ((day_num - 1) % 5) + 1
        for p in self.day_plans:
            if p["day"] == plan_day:
                return p
        return {"day": plan_day, "dishes": {}, "ingredients": {}}

    def _init_current_day(self, initial=False):
        # 1. Cấu hình gather tuning theo active_upgrades
        g_tuning = copy.deepcopy(self.tuning)
        oxy_lvl = self.active_upgrades.get("oxygen", 0)
        if oxy_lvl > 0 and "oxygen" in self.shop_upgrades:
            oxy_s = self.shop_upgrades["oxygen"][oxy_lvl - 1]["oxygen_max_s"]
            g_tuning["gather"]["oxygen_max_s"] = oxy_s
        hp_lvl = self.active_upgrades.get("hp", 0)
        if hp_lvl > 0 and "hp" in self.shop_upgrades:
            hp_m = self.shop_upgrades["hp"][hp_lvl - 1]["hp_max"]
            g_tuning["gather"]["hp_max"] = hp_m

        # 2. Khởi tạo GatherSim
        sc_gather = copy.deepcopy(self.scenario.get("gather", {}))
        sc_gather["hold"] = []  # Giỏ làm mới đầu ngày
        weapon_lvl = self.active_upgrades.get("weapon", 0)
        self.gather_sim = GatherSim(g_tuning, sc_gather, self.rng, self.ids, day=self.day, weapon_level=weapon_lvl)
        self.phase = "gather"
        self.phase_tick = 0

    def initial_events(self):
        plan = self.get_plan_for_day(self.day)
        return [
            {"type": "event", "tick": 0, "phase": "gather", "day": self.day, "name": "day_start", "data": {}},
            {"type": "event", "tick": 0, "phase": "gather", "day": self.day, "name": "day_plan",
             "data": {"dishes": plan["dishes"], "ingredients": plan["ingredients"]}},
            {"type": "event", "tick": 0, "phase": "gather", "day": self.day, "name": "phase_start", "data": {}}
        ]

    def snapshot(self) -> dict:
        mult = self.tuning.get("score", {}).get("reputation_multiplier", 100)
        score = self.earned + mult * math.floor(self.reputation)
        cur_plan = self.get_plan_for_day(self.day)
        s = {
            "day": self.day,
            "day_plan": {"dishes": cur_plan["dishes"], "ingredients": cur_plan["ingredients"]},
            "upgrades": dict(self.upgrades),
            "active_upgrades": dict(self.active_upgrades),
            "money": self.money,
            "earned": self.earned,
            "reputation": self.reputation,
            "score": score,
            "state": "paused" if self.paused else ("finished" if self.done else "playing"),
            "phase": self.phase,
            "phase_tick": self.phase_tick,
            "time_left_ticks": 0,
        }
        if self.phase == "gather" and self.gather_sim:
            gsnap = self.gather_sim.snapshot()
            s.update(gsnap)
            s["time_left_ticks"] = self.gather_sim.time_left_ticks
        elif self.phase == "quan" and self.quan_sim:
            qsnap = self.quan_sim.snapshot()
            s.update(qsnap)
            s["time_left_ticks"] = self.quan_sim.time_left_ticks
        elif self.phase == "shop":
            if isinstance(self.stock, list):
                s["stock"] = list(self.stock)
            else:
                s["stock"] = {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}
            s["time_left_ticks"] = self.shop_time_left
        return s

    def step(self, inp):
        events = []

        # 1. Xét cạnh pause trước
        if inp.pressed("pause"):
            if self.paused:
                self.paused = False
                events.append(("resumed", {}, self.phase))
            else:
                self.paused = True
                events.append(("paused", {}, self.phase))
                return events

        if self.paused:
            return []

        self.sim_tick += 1

        # 2. Xử lý gameplay theo phase
        if self.phase == "gather":
            sub_ev = self.gather_sim.step(inp)
            for ev in sub_ev:
                events.append((ev[0], ev[1], "gather"))
            self.phase_tick += 1

            if self.gather_sim.done:
                if self.gather_sim.reason == "fainted":
                    self.stock = [] if isinstance(getattr(self.gather_sim, "hold", None), list) and any(isinstance(x, dict) for x in self.gather_sim.hold) else {}
                else:
                    self.stock = self.gather_sim.inventory_items()

                # Dựng QuanSim và chuyển phase cùng tick
                cur_plan = self.get_plan_for_day(self.day)
                sc_quan = copy.deepcopy(self.scenario.get("quan", {}))
                sc_quan["reputation"] = self.reputation
                self.quan_sim = QuanSim(self.tuning, sc_quan, self.rng, self.ids, inventory=self.stock)
                self.quan_sim.money = self.money
                self.quan_sim.earned = self.earned
                self.quan_sim.reputation = self.reputation
                self.quan_sim.allowed_dishes = set(cur_plan["dishes"].keys())

                self.phase = "quan"
                self.phase_tick = 0
                events.append(("phase_start", {}, "quan"))

        elif self.phase == "quan":
            sub_ev = self.quan_sim.step(inp)
            for ev in sub_ev:
                events.append((ev[0], ev[1], "quan"))
            self.phase_tick += 1

            if self.quan_sim.done:
                self.money = self.quan_sim.money
                self.earned = self.quan_sim.earned
                self.reputation = self.quan_sim.reputation
                self.stock = list(self.quan_sim.stock) if isinstance(self.quan_sim.stock, list) else dict(self.quan_sim.stock)

                # Dựng Shop cùng tick
                self.phase = "shop"
                self.phase_tick = 0
                self.shop_time_left = 600
                events.append(("phase_start", {}, "shop"))

        elif self.phase == "shop":
            # Xử lý buy trước cạnh shop_done
            buy_cmd = getattr(inp, "buy", None)
            if buy_cmd:
                if buy_cmd not in self.shop_upgrades:
                    events.append(("buy_failed", {"action": "buy", "reason": "unknown"}, "shop"))
                else:
                    curr_lvl = self.upgrades.get(buy_cmd, 0)
                    tiers = self.shop_upgrades.get(buy_cmd, [])
                    if curr_lvl >= len(tiers):
                        events.append(("buy_failed", {"action": "buy", "reason": "max_level"}, "shop"))
                    else:
                        tier = tiers[curr_lvl]
                        price = tier["price"]
                        if self.money < price:
                            events.append(("buy_failed", {"action": "buy", "reason": "funds"}, "shop"))
                        else:
                            self.money -= price
                            self.upgrades[buy_cmd] = curr_lvl + 1
                            events.append(("bought", {"upgrade": buy_cmd, "level": curr_lvl + 1, "price": price, "money": self.money}, "shop"))

            # Đóng shop bằng shop_done hoặc hết giờ
            shop_closed = False
            if inp.pressed("shop_done"):
                events.append(("shop_end", {"reason": "done"}, "shop"))
                shop_closed = True
            else:
                self.shop_time_left -= 1
                self.phase_tick += 1
                if self.shop_time_left <= 0:
                    events.append(("shop_end", {"reason": "time"}, "shop"))
                    shop_closed = True

            if shop_closed:
                self.days_completed += 1
                self.stock = {}
                if self.days_completed >= self.target_days:
                    self.done = True
                    self.reason = "days_complete"
                else:
                    # Chuyển sang Ngày mới ngay trong tick đó
                    self.day += 1
                    self.active_upgrades = dict(self.upgrades)
                    self._init_current_day(initial=False)
                    plan = self.get_plan_for_day(self.day)
                    events.append(("day_start", {}, "gather"))
                    events.append(("day_plan", {"dishes": plan["dishes"], "ingredients": plan["ingredients"]}, "gather"))
                    events.append(("phase_start", {}, "gather"))

        return events
