"""I-01: replay consecutive pairs 24->44 at 32 simulations with fresh seeds.
Imports the trainer read-only; writes only to results/."""
import json
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "trainer"))

from alphago_lite.selfplay import play_match  # noqa: E402
from alphago_lite.train import Workers  # noqa: E402

SIMS, GAMES, CHUNK, FIRST, LAST, SEED = 32, 40, 4, 24, 44, 777000


def main():
    weights = ROOT / "trainer/runs/main/weights"
    w = lambda g: str(weights / f"gen_{g:04d}.pt")
    jobs, owners = [], []
    for a in range(FIRST, LAST):
        for c in range(GAMES // CHUNK):
            jobs.append((w(a), w(a + 1), CHUNK, SIMS, SEED + 1000 * a + c, 1))
            owners.append(a)
    t = time.time()
    with Workers(10, 3600) as pool:
        wins = pool.starmap(play_match, jobs)
    results = []
    for a in range(FIRST, LAST):
        won = sum(x for x, o in zip(wins, owners) if o == a)
        results.append({"a": a, "b": a + 1, "wins_a": won, "games": GAMES})
    out = {"design": "consecutive, fresh seeds", "sims": SIMS, "seed_base": SEED, "results": results,
           "wall_seconds": round(time.time() - t, 1), "python": platform.python_version(),
           "loadavg_start": os.getloadavg()}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "replay32.json").write_text(json.dumps(out, indent=1))
    newer = sum(r["games"] - r["wins_a"] for r in results)
    print(f"newer wins {newer}/{GAMES * len(results)} = {newer / (GAMES * len(results)):.3f} in {out['wall_seconds']} s")


if __name__ == "__main__":
    main()
