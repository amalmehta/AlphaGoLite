"""Play a trained generation against GNU Go 3.8 over GTP.

    python -m alphago_lite.gnugo_match --run runs/main --gen 44 --games 40 --sims 400 --level 10

GNU Go runs with Chinese rules, komi 7.5 and --capture-all-dead, so it removes
dead stones before passing and Tromp-Taylor area scoring (ours) is fair to it.
Games end after two passes or 162 moves and are scored by our rules; GNU Go's
own `final_score` is recorded alongside as a cross-check. Results go to
<run>/gnugo.json (resumable).
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import torch

from .go import PASS, Position, move_to_str
from .mcts import run_searches
from .net import Evaluator, load_net
from .train import Workers

COLS = "ABCDEFGHJ"


class GTP:
    def __init__(self, level, seed):
        self.p = subprocess.Popen(
            ["gnugo", "--mode", "gtp", "--boardsize", "9", "--komi", "7.5", "--chinese-rules",
             "--capture-all-dead", "--level", str(level), "--seed", str(seed)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def cmd(self, c):
        self.p.stdin.write(c + "\n")
        self.p.stdin.flush()
        lines = []
        while True:
            line = self.p.stdout.readline()
            if line.strip() == "" and lines:
                break
            if line.strip():
                lines.append(line.strip())
        resp = " ".join(lines)
        if not resp.startswith("="):
            raise RuntimeError(f"GTP error for {c!r}: {resp}")
        return resp[1:].strip()

    def close(self):
        try:
            self.cmd("quit")
        except Exception:
            pass
        self.p.kill()


def to_gtp(m):
    return "pass" if m == PASS else move_to_str(m)


def from_gtp(s):
    s = s.upper()
    if s == "PASS":
        return PASS
    if s == "RESIGN":
        return None
    return (9 - int(s[1:])) * 9 + COLS.index(s[0])


def play_games(weights, n_games, sims, level, seed, ours_black_first):
    """Play n_games sequentially; colors alternate starting from ours_black_first."""
    torch.set_num_threads(1)
    ev = Evaluator(load_net(weights))
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n_games):
        ours_black = (i % 2 == 0) == ours_black_first
        gtp = GTP(level, seed * 100 + i)
        gtp.cmd("clear_board")
        pos, moves, note = Position(), [], ""
        ours = 1 if ours_black else -1
        while not pos.is_over():
            if pos.to_play == ours:
                # after an opponent pass, pass too if already winning on the board
                if moves and moves[-1] == PASS and pos.area_score() * ours > 0:
                    m = PASS
                else:
                    root = run_searches([pos], ev, sims, rng=rng)[0]
                    m = int(root.N.argmax())
                gtp.cmd(f"play {'B' if ours == 1 else 'W'} {to_gtp(m)}")
            else:
                reply = gtp.cmd(f"genmove {'B' if ours == -1 else 'W'}")
                m = from_gtp(reply)
                if m is None:  # GNU Go resigned
                    note = "gnugo resigned"
                    break
                if not pos.legal_mask()[m]:
                    note = f"gnugo played {reply}, illegal under our rules"
                    break
            moves.append(m)
            pos = pos.play(m)
        gnugo_score = gtp.cmd("final_score")
        gtp.close()
        score = pos.area_score()
        if note == "gnugo resigned":
            ours_won = True
        elif note:
            ours_won = None  # void game
        else:
            ours_won = (score > 0) == ours_black
        out.append({"ours_black": ours_black, "moves": [to_gtp(m) for m in moves], "our_score_black": score,
                    "gnugo_final_score": gnugo_score, "ours_won": ours_won, "note": note})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--gen", type=int, required=True)
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--sims", type=int, default=400)
    ap.add_argument("--level", type=int, default=10)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--job-timeout", type=int, default=7200)
    args = ap.parse_args()
    run = Path(args.run)
    out = run / "gnugo.json"
    data = json.loads(out.read_text()) if out.exists() else {"matches": []}
    key = {"gen": args.gen, "sims": args.sims, "level": args.level}
    if any({k: m[k] for k in key} == key for m in data["matches"]):
        print("already played", key)
        return
    per = args.games // args.workers
    weights = str(run / "weights" / f"gen_{args.gen:04d}.pt")
    jobs = [(weights, per, args.sims, args.level, 7777 + w, w % 2 == 0) for w in range(args.workers)]
    with Workers(args.workers, args.job_timeout) as pool:
        games = [g for r in pool.starmap(play_games, jobs) for g in r]
    decided = [g for g in games if g["ours_won"] is not None]
    wins = sum(g["ours_won"] for g in decided)
    data["matches"].append(dict(key, games=games, wins=wins, decided=len(decided)))
    out.write_text(json.dumps(data, indent=1))
    print(f"gen {args.gen} ({args.sims} sims) vs GNU Go level {args.level}: won {wins}/{len(decided)} "
          f"({len(games) - len(decided)} void)", flush=True)


if __name__ == "__main__":
    main()
