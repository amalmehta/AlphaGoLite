"""Anchored head-to-head evaluation: many generation pairs, for fitting one
Bradley-Terry (Elo) rating per generation.

    python -m alphago_lite.anchored_eval --run runs/main --step 4 --games 40

Pairs (--design anchored, the default): every `step`-th generation g plays
g+step, g+2*step and the last generation. --design consecutive plays each
generation g in [--from, last) against g+1, to compare with the training log's
32-simulation chained matches. Results are appended to <run>/<design>.json after
each batch, so the command can be stopped and resumed.
"""
import argparse
import json
from pathlib import Path

from .selfplay import play_match
from .train import Workers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--step", type=int, default=4)
    ap.add_argument("--games", type=int, default=40, help="games per pair (even)")
    ap.add_argument("--sims", type=int, default=64)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--chunk", type=int, default=4, help="games per job (even)")
    ap.add_argument("--pairs-per-batch", type=int, default=5)
    ap.add_argument("--job-timeout", type=int, default=3600)
    ap.add_argument("--design", choices=["anchored", "consecutive"], default="anchored")
    ap.add_argument("--from", dest="first", type=int, default=0, help="first generation (consecutive design)")
    args = ap.parse_args()

    run = Path(args.run)
    weights = run / "weights"
    last = max(int(p.stem.split("_")[1]) for p in weights.glob("gen_*.pt"))
    gens = list(range(0, last + 1, args.step))
    if gens[-1] != last:
        gens.append(last)
    pairs = []
    if args.design == "consecutive":
        pairs = [(g, g + 1) for g in range(args.first, last)]
    else:
        for i, g in enumerate(gens):
            for h in gens[i + 1:i + 3] + [last]:
                if h != g and (g, h) not in pairs:
                    pairs.append((g, h))

    out = run / f"{args.design}.json"
    data = json.loads(out.read_text()) if out.exists() else {"sims": args.sims, "results": []}
    done = {(r["a"], r["b"]) for r in data["results"]}
    todo = [p for p in pairs if p not in done]
    print(f"{len(pairs)} pairs, {len(todo)} to play, {args.games} games each at {args.sims} sims", flush=True)

    w = lambda g: str(weights / f"gen_{g:04d}.pt")
    with Workers(args.workers, args.job_timeout) as pool:
        for i in range(0, len(todo), args.pairs_per_batch):
            batch = todo[i:i + args.pairs_per_batch]
            jobs, owners = [], []
            for a, b in batch:
                for c in range(args.games // args.chunk):
                    # each chunk plays chunk/2 games with A as black, chunk/2 with A as white
                    jobs.append((w(a), w(b), args.chunk, args.sims, 1_000_003 * a + 1009 * b + c, 1))
                    owners.append((a, b))
            wins = pool.starmap(play_match, jobs)
            for a, b in batch:
                n = sum(1 for o in owners if o == (a, b)) * args.chunk
                won = sum(x for x, o in zip(wins, owners) if o == (a, b))
                data["results"].append({"a": a, "b": b, "wins_a": won, "games": n})
                print(f"gen {a} vs gen {b}: {won}/{n}", flush=True)
            out.write_text(json.dumps(data, indent=1))


if __name__ == "__main__":
    main()
