"""Vòng tick (Contract B, mô hình tick). KHUNG — thường không cần sửa.

Thứ tự ghi: snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi snapshot (nếu tới lượt
hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`):
cả hai chạy CÙNG một lớp sim, không nhân đôi logic.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    elif mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    elif mode == "day":
        return DaySim(tuning, scenario, streams, ids, days=days)
    from .errors import BadInput
    raise BadInput(f"mode không hợp lệ: {mode}")


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning.get("score", {}).get("reputation_multiplier", 100)
    if sim.mode == "day":
        return {
            "type": "snapshot", "tick": tick, "sim_tick": getattr(sim, "sim_tick", tick), "mode": sim.mode,
            "state": "paused" if getattr(sim, "paused", False) else (state or ("finished" if sim.done else "playing")),
        }
    return {
        "type": "snapshot", "tick": tick, "sim_tick": sim_tick, "mode": sim.mode, "phase": sim.phase,
        "phase_tick": phase_tick, "state": state, "time_left_ticks": sim.time_left_ticks,
        "money": sim.money, "earned": sim.earned, "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick, lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days=days)

    @property
    def done(self) -> bool:
        return self.sim.done

    def initial_events(self) -> list:
        if hasattr(self.sim, "initial_events"):
            return self.sim.initial_events()
        return []

    def snapshot(self) -> dict:
        s = _common(self.sim, self.tick, self.tick, self.tick, self.tuning, "finished" if self.sim.done else "playing")
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        events = self.sim.step(inp)
        self.tick += 1
        out = []
        for ev in events:
            name, data = ev[0], ev[1]
            phase = ev[2] if len(ev) > 2 else self.sim.phase
            row = {"type": "event", "tick": self.tick, "phase": phase, "name": name, "data": data}
            if self.mode == "day":
                row["day"] = self.sim.day
            out.append(row)
        return out

    def end_row(self) -> dict:
        sim = self.sim
        score = sim.earned + self.tuning.get("score", {}).get("reputation_multiplier", 100) * math.floor(sim.reputation)
        row = {"type": "end", "ticks": self.tick, "sim_tick": getattr(sim, "sim_tick", self.tick), "mode": sim.mode,
               "state": "finished" if sim.done else "playing",
               "reason": sim.reason if sim.done else "tick_limit",
               "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": score}
        if self.mode == "day":
            row["days_completed"] = getattr(sim, "days_completed", 0)
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days)
    from .inputs import BUTTONS_V10, BUTTONS_V11
    player = InputPlayer(frames, buttons=BUTTONS_V11 if mode == "day" else BUTTONS_V10)
    w = JsonlWriter(out_path)
    try:
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        for row in sess.initial_events():
            w.write(row)
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
