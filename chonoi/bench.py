"""Measure deterministic simulation tick throughput (not rendered FPS)."""

import argparse
import json
import os
import sys
import time

from .contract import load_contract
from .errors import BadInput
from .live import LiveGame, LiveServer


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"error: {message}\n")
        raise SystemExit(2)


def _percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))]


def run_benchmark(seed: int, duration: int, out_path: str) -> dict:
    if duration < 1:
        raise BadInput("--duration must be >= 1")
    start_load = time.perf_counter()
    contract = load_contract()
    tuning = contract["tuning"]
    game = LiveGame("gather", tuning, {}, seed)
    server = LiveServer(game, port=0)
    load_ms = (time.perf_counter() - start_load) * 1000
    frames = 0
    window_frames = 0
    window_started = time.perf_counter()
    window_fps = []
    measured_start = time.perf_counter()
    deadline = measured_start + duration
    while time.perf_counter() < deadline:
        game._tick_once()
        frames += 1
        window_frames += 1
        now = time.perf_counter()
        if now - window_started >= 1.0:
            window_fps.append(window_frames / (now - window_started))
            window_frames = 0
            window_started = now
    server.httpd.server_close()
    measured_s = time.perf_counter() - measured_start
    if window_frames:
        window_fps.append(window_frames / max(time.perf_counter() - window_started, 1e-9))
    if not frames:
        raise BadInput("benchmark produced no frames")
    report = {
        "avg_fps": round(frames / measured_s, 3),
        "p1_low_fps": round(_percentile(window_fps, 0.01), 3),
        "frames": frames,
        "measured_s": round(measured_s, 3),
        "load_ms": round(load_ms, 3),
    }
    directory = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return report


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.bench")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        report = run_benchmark(a.seed, a.duration, a.out)
    except BadInput as e:
        sys.stderr.write(f"invalid input: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"benchmark error: {e}\n")
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
