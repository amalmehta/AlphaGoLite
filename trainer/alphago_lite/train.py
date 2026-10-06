"""AlphaZero training loop: self-play -> train -> evaluate, one generation at a time.

    python -m alphago_lite.train --run runs/main --hours 3

Everything the Mac app's Training dashboard reads is written to the run folder:
metrics.json (one entry per generation) and games/gen_NNNN.json (sample games).
"""
import argparse
import json
import math
import multiprocessing as mp
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from .go import apply_symmetry
from .net import PolicyValueNet
from .selfplay import play_match, play_selfplay


def elo_from_winrate(w):
    w = min(max(w, 0.02), 0.98)
    return -400 * math.log10(1 / w - 1)


def write_json(path, obj):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


class Workers:
    """Process pool that survives a dead worker. multiprocessing.Pool replaces a
    worker that dies but loses its job, so starmap would wait forever; here a
    call that doesn't finish within `timeout` seconds is retried on a new pool."""

    def __init__(self, n, timeout, retries=3):
        self.n, self.timeout, self.retries = n, timeout, retries
        self.ctx = mp.get_context("spawn")
        self.pool = self.ctx.Pool(n)

    def starmap(self, fn, jobs):
        for attempt in range(1, self.retries + 1):
            try:
                return self.pool.starmap_async(fn, jobs).get(self.timeout)
            except mp.TimeoutError:
                print(f"{fn.__name__}: no result after {self.timeout}s (attempt {attempt}); restarting workers",
                      flush=True)
                self.pool.terminate()
                self.pool = self.ctx.Pool(self.n)
        raise RuntimeError(f"{fn.__name__} failed {self.retries} times")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.pool.terminate()


def load_window(data_dir, max_positions):
    files = sorted(data_dir.glob("gen_*.npz"), reverse=True)
    planes, pis, zs, total = [], [], [], 0
    for fp in files:
        d = np.load(fp)
        planes.append(d["planes"])
        pis.append(d["pis"])
        zs.append(d["zs"])
        total += len(d["zs"])
        if total >= max_positions:
            break
    return np.concatenate(planes), np.concatenate(pis), np.concatenate(zs)


def train_steps(net, opt, planes, pis, zs, steps, batch, rng):
    net.train()
    pl_sum = vl_sum = 0.0
    for _ in range(steps):
        idx = rng.integers(0, len(zs), batch)
        xb, pb = [], []
        for i in idx:
            x, p = apply_symmetry(planes[i], pis[i], int(rng.integers(8)))
            xb.append(x)
            pb.append(p)
        x = torch.from_numpy(np.stack(xb).astype(np.float32))
        p = torch.from_numpy(np.stack(pb))
        z = torch.from_numpy(zs[idx])
        logits, v = net(x)
        pl = -(p * F.log_softmax(logits, dim=1)).sum(1).mean()
        vl = F.mse_loss(v[:, 0], z)
        loss = pl + vl
        opt.zero_grad()
        loss.backward()
        opt.step()
        pl_sum += pl.item()
        vl_sum += vl.item()
    net.eval()
    return pl_sum / steps, vl_sum / steps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--max-gens", type=int, default=10_000)
    ap.add_argument("--games-per-gen", type=int, default=160)
    ap.add_argument("--sims", type=int, default=160)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--eval-games", type=int, default=40)
    ap.add_argument("--eval-sims", type=int, default=32)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--window", type=int, default=250_000)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--train-threads", type=int, default=12)
    ap.add_argument("--job-timeout", type=int, default=2400,
                    help="seconds before a self-play/eval step is retried on fresh workers")
    args = ap.parse_args()

    run = Path(args.run)
    (run / "weights").mkdir(parents=True, exist_ok=True)
    (run / "data").mkdir(exist_ok=True)
    (run / "games").mkdir(exist_ok=True)
    metrics_path = run / "metrics.json"

    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    net = PolicyValueNet()
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=1e-4)

    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {
        "config": vars(args), "generations": []}
    gens = metrics["generations"]
    if gens:  # resume
        g0 = gens[-1]["gen"]
        net.load_state_dict(torch.load(run / "weights" / f"gen_{g0:04d}.pt"))
        state = run / "weights" / "optimizer.pt"
        if state.exists():
            opt.load_state_dict(torch.load(state))
    else:
        g0 = 0
        torch.save(net.state_dict(), run / "weights" / "gen_0000.pt")
        gens.append({"gen": 0, "elo": 0.0, "elapsed_min": 0.0, "total_games": 0})
        write_json(metrics_path, metrics)

    start = time.time() - gens[-1]["elapsed_min"] * 60
    deadline = time.time() + args.hours * 3600
    threads = 1
    with Workers(args.workers, args.job_timeout) as pool:
        for gen in range(g0 + 1, args.max_gens + 1):
            if time.time() > deadline:
                break
            prev = run / "weights" / f"gen_{gen - 1:04d}.pt"
            t0 = time.time()

            per = args.games_per_gen // args.workers
            jobs = [(str(prev), per, args.sims, gen * 1000 + w, threads) for w in range(args.workers)]
            results = pool.starmap(play_selfplay, jobs)
            planes = np.concatenate([r[0] for r in results])
            pis = np.concatenate([r[1] for r in results])
            zs = np.concatenate([r[2] for r in results])
            records = [rec for r in results for rec in r[3]]
            np.savez_compressed(run / "data" / f"gen_{gen:04d}.npz", planes=planes, pis=pis, zs=zs)
            write_json(run / "games" / f"gen_{gen:04d}.json",
                       {"generation": gen - 1, "games": records[:4]})
            t_self = time.time() - t0

            t1 = time.time()
            torch.set_num_threads(args.train_threads)
            wp, wpi, wz = load_window(run / "data", args.window)
            steps = max(100, len(zs) * 16 // args.batch)
            pl, vl = train_steps(net, opt, wp, wpi, wz, steps, args.batch, rng)
            cur = run / "weights" / f"gen_{gen:04d}.pt"
            torch.save(net.state_dict(), cur)
            torch.save(opt.state_dict(), run / "weights" / "optimizer.pt")
            t_train = time.time() - t1

            t2 = time.time()
            per_eval = max(2, args.eval_games // args.workers)
            ejobs = [(str(cur), str(prev), per_eval, args.eval_sims, gen * 7919 + w, threads)
                     for w in range(args.workers)]
            wins = sum(pool.starmap(play_match, ejobs))
            n_eval = per_eval * args.workers
            winrate = wins / n_eval
            t_eval = time.time() - t2

            lengths = [r["length"] for r in records]
            gens.append({
                "gen": gen,
                "elo": round(gens[-1]["elo"] + elo_from_winrate(winrate), 1),
                "winrate_vs_prev": round(winrate, 3),
                "policy_loss": round(pl, 4),
                "value_loss": round(vl, 4),
                "games": len(records),
                "total_games": gens[-1]["total_games"] + len(records),
                "positions": int(len(zs)),
                "window": int(len(wz)),
                "train_steps": steps,
                "avg_game_length": round(float(np.mean(lengths)), 1),
                "black_winrate": round(float(np.mean([r["score"] > 0 for r in records])), 3),
                "selfplay_sec": round(t_self, 1),
                "train_sec": round(t_train, 1),
                "eval_sec": round(t_eval, 1),
                "elapsed_min": round((time.time() - start) / 60, 1),
            })
            write_json(metrics_path, metrics)
            g = gens[-1]
            print(f"gen {gen}: elo {g['elo']} (vs prev {winrate:.2f}) "
                  f"pl {pl:.3f} vl {vl:.3f} len {g['avg_game_length']} "
                  f"[self {t_self:.0f}s train {t_train:.0f}s eval {t_eval:.0f}s]", flush=True)


if __name__ == "__main__":
    main()
