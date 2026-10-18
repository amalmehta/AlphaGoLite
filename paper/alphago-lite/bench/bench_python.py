"""Cross-platform benchmark, Python/PyTorch side. Also writes positions.json,
the shared input for the Swift and browser benchmarks.

    ../../../trainer/.venv/bin/python bench_python.py

Positions: every 5th move (0..95) of the last recorded self-play game.
Each position is searched from an empty tree for SIMS simulations, one leaf at a
time (batch size 1), as in the apps.
"""
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "trainer"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from alphago_lite.go import Position  # noqa: E402
from alphago_lite.mcts import run_searches  # noqa: E402
from alphago_lite.net import Evaluator, load_net  # noqa: E402

SIMS = 400
REPEATS = 3


def main():
    games = json.loads((ROOT / "web/data/games.json").read_text())["games"]
    game = games[-1]
    moves = [m["move"] for m in game["moves"]]
    cases = [{"moves": moves[:k]} for k in range(0, min(len(moves), 96), 5)]
    (HERE / "positions.json").write_text(json.dumps({"source": game["title"], "sims": SIMS, "cases": cases}))

    torch.set_num_threads(1)
    gen = json.loads((ROOT / "web/data/metrics.json").read_text())["exported_gen"]
    ev = Evaluator(load_net(ROOT / f"trainer/runs/main/weights/gen_{gen:04d}.pt"))
    out = []
    for c in cases:
        pos = Position()
        for m in c["moves"]:
            pos = pos.play(m)
        times = []
        for _ in range(REPEATS):
            t = time.perf_counter()
            root = run_searches([pos], ev, SIMS)[0]
            times.append(time.perf_counter() - t)
        out.append({"visits": [int(v) for v in root.N], "best": int(root.N.argmax()), "ms": 1000 * min(times)})
    load = subprocess.run(["sysctl", "-n", "vm.loadavg"], capture_output=True, text=True).stdout.strip()
    (HERE / "result_python.json").write_text(json.dumps({
        "platform": "Python 3.11 / PyTorch %s (CPU, 1 thread)" % torch.__version__, "gen": gen, "sims": SIMS,
        "repeats": REPEATS, "machine": platform.processor() or platform.machine(), "loadavg": load, "cases": out}))
    ms = [c["ms"] for c in out]
    print(f"python: median {np.median(ms):.0f} ms per {SIMS}-sim search ({len(out)} positions), load {load}")


if __name__ == "__main__":
    main()
