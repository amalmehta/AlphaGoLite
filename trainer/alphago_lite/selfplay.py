"""Self-play and evaluation games. Each call plays many games at once so the
network sees large batches."""
import numpy as np
import torch

from .go import NUM_MOVES, PASS, Position
from .mcts import root_value, run_searches
from .net import Evaluator, load_net

TEMP_MOVES = 10  # sample moves proportionally to visits for this many moves
FULL_SEARCH_PROB = 0.25  # playout-cap randomization (KataGo): only full searches
FAST_SIMS_DIVISOR = 4    # become training samples; the rest use sims / 4


class _Game:
    def __init__(self):
        self.pos = Position()
        self.samples = []  # (features, pi, to_play)
        self.record = []  # dicts for the replay viewer


def _pick(visits, move_count, temp_moves, rng):
    if move_count < temp_moves:
        return int(rng.choice(NUM_MOVES, p=visits / visits.sum()))
    best = np.flatnonzero(visits == visits.max())
    return int(rng.choice(best))


def _result_str(pos):
    s = pos.area_score()
    return ("B+" if s > 0 else "W+") + f"{abs(s):g}"


def play_selfplay(weights, n_games, sims, seed, threads=2):
    """Returns (planes int8 [P,6,9,9], pis float32 [P,82], zs float32 [P], records)."""
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    ev = Evaluator(load_net(weights))
    games = [_Game() for _ in range(n_games)]
    active = list(games)
    while active:
        full = rng.random() < FULL_SEARCH_PROB
        n = sims if full else max(8, sims // FAST_SIMS_DIVISOR)
        roots = run_searches([g.pos for g in active], ev, n, rng=rng, noise=full)
        still = []
        for g, root in zip(active, roots):
            visits = root.N
            pi = (visits / visits.sum()).astype(np.float32)
            m = _pick(visits, g.pos.move_count, TEMP_MOVES, rng)
            if full:
                g.samples.append((g.pos.features().astype(np.int8), pi, g.pos.to_play))
            g.record.append({
                "move": m,
                "value": round(root_value(root) * g.pos.to_play, 3),  # black's view
                "visits": [int(v) for v in visits],
                "full": bool(full),
            })
            g.pos = g.pos.play(m)
            if not g.pos.is_over():
                still.append(g)
        active = still

    planes, pis, zs, records = [], [], [], []
    for g in games:
        w = g.pos.winner()
        for f, pi, tp in g.samples:
            planes.append(f)
            pis.append(pi)
            zs.append(float(w * tp))
        records.append({
            "moves": g.record,
            "result": _result_str(g.pos),
            "score": g.pos.area_score(),
            "length": len(g.record),
        })
    if not planes:
        return (np.zeros((0, 6, 9, 9), np.int8), np.zeros((0, NUM_MOVES), np.float32),
                np.zeros(0, np.float32), records)
    return np.stack(planes), np.stack(pis), np.array(zs, dtype=np.float32), records


def play_match(weights_a, weights_b, n_games, sims, seed, threads=2, temp_moves=6):
    """A plays black in the first half of the games. Returns number of A wins."""
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    evs = {0: Evaluator(load_net(weights_a)), 1: Evaluator(load_net(weights_b))}
    games = [(Position(), i < n_games // 2) for i in range(n_games)]  # (pos, a_is_black)
    positions = [g[0] for g in games]
    a_black = [g[1] for g in games]
    active = list(range(n_games))
    while active:
        for who in (0, 1):  # 0 = A to move, 1 = B to move
            idx = [i for i in active
                   if ((positions[i].to_play == 1) == a_black[i]) == (who == 0)]
            if not idx:
                continue
            roots = run_searches([positions[i] for i in idx], evs[who], sims)
            for i, root in zip(idx, roots):
                m = _pick(root.N, positions[i].move_count, temp_moves, rng)
                positions[i] = positions[i].play(m)
        active = [i for i in active if not positions[i].is_over()]
    wins = 0
    for i in range(n_games):
        w = positions[i].winner()
        if (w == 1) == a_black[i]:
            wins += 1
    return wins
