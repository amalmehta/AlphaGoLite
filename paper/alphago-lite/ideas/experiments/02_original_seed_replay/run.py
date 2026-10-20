"""Experiment 02: repeat train.py's evaluation calls with their original seeds.
Imports the trainer read-only; writes only to results/."""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "trainer"))

from alphago_lite.selfplay import play_match  # noqa: E402
from alphago_lite.train import Workers  # noqa: E402

FIRST, LAST, WORKERS, PER, SIMS = 25, 44, 10, 4, 32


def main():
    run = ROOT / "trainer/runs/main"
    log = {g["gen"]: g for g in json.loads((run / "metrics.json").read_text())["generations"]}
    w = lambda g: str(run / "weights" / f"gen_{g:04d}.pt")
    jobs, owners = [], []
    for g in range(FIRST, LAST + 1):
        for k in range(WORKERS):
            jobs.append((w(g), w(g - 1), PER, SIMS, g * 7919 + k, 1))
            owners.append(g)
    # determinism probe: the first job once more, at the end
    jobs.append(jobs[0])
    owners.append("repeat")
    t = time.time()
    with Workers(WORKERS, 3600) as pool:
        wins = pool.starmap(play_match, jobs)
    out = {"pairs": [], "determinism": {"job": "gen %d seed %d" % (FIRST, FIRST * 7919), "first": wins[0], "repeat": wins[-1]},
           "wall_seconds": round(time.time() - t, 1), "loadavg_start": os.getloadavg()}
    for g in range(FIRST, LAST + 1):
        replay = sum(x for x, o in zip(wins, owners) if o == g)
        logged = round(log[g]["winrate_vs_prev"] * WORKERS * PER)
        out["pairs"].append({"gen": g, "logged_wins": logged, "replayed_wins": replay, "games": WORKERS * PER,
                             "match": replay == logged})
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "original_seed.json").write_text(json.dumps(out, indent=1))
    same = sum(p["match"] for p in out["pairs"])
    print(f"reproduced {same}/{len(out['pairs'])} pairs exactly; determinism probe {wins[0]} vs {wins[-1]}; "
          f"{out['wall_seconds']} s")


if __name__ == "__main__":
    main()
