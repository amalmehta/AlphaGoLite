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
    ap.add_argument("--vs-run", default=None, help="take the --vs generations from this run (default: --run)")
    ap.add_argument("--pass-rule", action="store_true", help="pass rule on for --gen's side")
    ap.add_argument("--vs-pass-rule", action="store_true", help="pass rule on for the --vs side")
    args = ap.parse_args()
    w = Path(args.run) / "weights"
    wv = Path(args.vs_run) / "weights" if args.vs_run else w
    per = args.games // args.workers
    out_path = Path(args.run) / "strength.json"
    results = json.loads(out_path.read_text()) if out_path.exists() else []
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for old in args.vs:
            jobs = [(str(w / f"gen_{args.gen:04d}.pt"), str(wv / f"gen_{old:04d}.pt"), per, args.sims, 99 + i, 1,
                     6, args.pass_rule, args.vs_pass_rule) for i in range(args.workers)]
            wins = sum(pool.starmap(play_match, jobs))
            n = per * args.workers
            print(f"gen {args.gen} vs {args.vs_run or ''} gen {old}: won {wins}/{n} ({wins / n:.0%}) at {args.sims} sims/move", flush=True)
            entry = {"gen": args.gen, "vs": old, "wins": wins, "games": n, "sims": args.sims}
            if args.vs_run or args.pass_rule or args.vs_pass_rule:
                entry.update(vs_run=args.vs_run, pass_rule=args.pass_rule, vs_pass_rule=args.vs_pass_rule)
            ident = lambda r: (r["gen"], r["vs"], r.get("vs_run"), r.get("pass_rule", False), r.get("vs_pass_rule", False))
            results = [r for r in results if ident(r) != ident(entry)]
            results.append(entry)
    out_path.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
