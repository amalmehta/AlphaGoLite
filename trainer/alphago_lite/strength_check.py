"""Head-to-head check of one generation against earlier ones. Results are
saved to <run>/strength.json and shown in the app's Training view.

    python -m alphago_lite.strength_check --run runs/main --gen 19 --vs 0 10
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

from .selfplay import play_match


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--gen", type=int, required=True)
    ap.add_argument("--vs", type=int, nargs="+", default=[0])
    ap.add_argument("--games", type=int, default=80)
    ap.add_argument("--sims", type=int, default=64)
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()
    w = Path(args.run) / "weights"
    per = args.games // args.workers
    out_path = Path(args.run) / "strength.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else []
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for old in args.vs:
            jobs = [(str(w / f"gen_{args.gen:04d}.pt"), str(w / f"gen_{old:04d}.pt"), per, args.sims, 99 + i, 1)
                    for i in range(args.workers)]
            wins = sum(pool.starmap(play_match, jobs))
            n = per * args.workers
            print(f"gen {args.gen} vs gen {old}: won {wins}/{n} ({wins / n:.0%}) at {args.sims} sims/move", flush=True)
            results = [r for r in results if (r["gen"], r["vs"]) != (args.gen, old)]
            results.append({"gen": args.gen, "vs": old, "wins": wins, "games": n, "sims": args.sims})
    out_path.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
