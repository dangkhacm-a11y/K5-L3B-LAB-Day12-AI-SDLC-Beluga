"""Deterministic multi-day headless soak runner for Test Contract 1.3."""

import argparse
import json
import math
import os
import sys
import time

from .contract import load_contract
from .errors import BadInput
from .inputs import InputPlayer
from .runner import Session


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"error: {message}\n")
        raise SystemExit(2)


def run_soak(seed: int, days: int, out_path: str) -> dict:
    if days < 1:
        raise BadInput("--days must be >= 1")
    start = time.perf_counter()
    contract = load_contract()
    session = Session("day", contract["tuning"], {}, seed, days=days)
    # An empty fixed input stream makes this a reproducible lifecycle soak.
    player = InputPlayer([])
    results = []
    crashes = 0
    tick = 0
    while not session.done:
        shop_day = session.sim.day
        try:
            rows = session.step(player.advance(tick))
        except Exception:
            crashes += 1
            break
        tick += 1
        for row in rows:
            if row["name"] == "shop_end":
                results.append({
                    "day": shop_day,
                    "earned": session.sim.earned,
                    "reputation": session.sim.reputation,
                    "score": session.sim.earned + math.floor(session.sim.reputation) * contract["tuning"].get("score", {}).get("reputation_multiplier", 100),
                })
        if session.sim.reason == "error":
            crashes += 1
            break

    elapsed = time.perf_counter() - start
    report = {
        "days": days,
        "days_completed": session.sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": round(elapsed, 6),
    }
    directory = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return report


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        report = run_soak(a.seed, a.days, a.out)
    except BadInput as e:
        sys.stderr.write(f"invalid input: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"write error: {e}\n")
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["days_completed"] == report["days"] and report["crashes"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
