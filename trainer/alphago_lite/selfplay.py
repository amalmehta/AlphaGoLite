"""Self-play and evaluation games. Each call plays many games at once so the
network sees large batches."""
import numpy as np
import torch

from .go import MAX_MOVES, NUM_MOVES, PASS, Position
from .mcts import root_value, run_searches
from .net import Evaluator, load_net

TEMP_MOVES = 10  # sample moves proportionally to visits for this many moves
FULL_SEARCH_PROB = 0.25  # playout-cap randomization (KataGo): only full searches
FAST_SIMS_DIVISOR = 4    # become training samples; the rest use sims / 4


class _Game:
    def __init__(self, max_moves):
        self.pos = Position(max_moves=max_moves)
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


def play_selfplay(weights, n_games, sims, seed, threads=2, pass_rule=False, max_moves=MAX_MOVES):
    """Returns (planes int8 [P,6,9,9], pis float32 [P,82], zs float32 [P],
    owns int8 [P,81], records). owns is the final Tromp-Taylor owner of each
    point from the point of view of the player to move in that position."""
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    ev = Evaluator(load_net(weights))
    games = [_Game(max_moves) for _ in range(n_games)]
    active = list(games)
    while active:
        full = rng.random() < FULL_SEARCH_PROB
        n = sims if full else max(8, sims // FAST_SIMS_DIVISOR)
        roots = run_searches([g.pos for g in active], ev, n, rng=rng, noise=full, pass_rule=pass_rule)
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

    planes, pis, zs, owns, records = [], [], [], [], []
    for g in games:
        w = g.pos.winner()
        own = np.asarray(g.pos.ownership(), dtype=np.int8)
        for f, pi, tp in g.samples:
            planes.append(f)
            pis.append(pi)
            zs.append(float(w * tp))
            owns.append(own * np.int8(tp))
        records.append({
            "moves": g.record,
            "result": _result_str(g.pos),
            "score": g.pos.area_score(),
            "length": len(g.record),
        })
    if not planes:
        return (np.zeros((0, 6, 9, 9), np.int8), np.zeros((0, NUM_MOVES), np.float32),
                np.zeros(0, np.float32), np.zeros((0, 81), np.int8), records)
    return np.stack(planes), np.stack(pis), np.array(zs, dtype=np.float32), np.stack(owns), records


def play_match(weights_a, weights_b, n_games, sims, seed, threads=2, temp_moves=6,
               pass_rule_a=False, pass_rule_b=False, max_moves=MAX_MOVES):
    """A plays black in the first half of the games. Returns number of A wins.
    pass_rule_a/b turn on Position.search_mask for that side's search."""
    torch.set_num_threads(threads)
    rng = np.random.default_rng(seed)
    evs = {0: Evaluator(load_net(weights_a)), 1: Evaluator(load_net(weights_b))}
    rules = {0: pass_rule_a, 1: pass_rule_b}
    games = [(Position(max_moves=max_moves), i < n_games // 2) for i in range(n_games)]  # (pos, a_is_black)
    positions = [g[0] for g in games]
    a_black = [g[1] for g in games]
    active = list(range(n_games))
    while active:
        for who in (0, 1):  # 0 = A to move, 1 = B to move
            idx = [i for i in active
                   if ((positions[i].to_play == 1) == a_black[i]) == (who == 0)]
            if not idx:
                continue
            roots = run_searches([positions[i] for i in idx], evs[who], sims, pass_rule=rules[who])
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
