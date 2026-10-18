"""Shared data loading and analysis for the paper's figures, tables and values.

Data lives in paper/alphago-lite/data/ (copied from trainer/runs/main/):
  metrics.json   per-generation training log, including chained Elo
  strength.json  80-game head-to-head checks (64 simulations a move)
  anchored.json  40-game anchored pairs (64 simulations a move)
  gnugo.json     games against GNU Go 3.8
"""
import json
import math
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
BENCH = HERE.parent / "bench"
VENUE = os.environ.get("VENUE", "aaai27")
VENUE_DIR = Path(os.environ.get("VENUE_DIR", HERE.parent / VENUE))

K = math.log(10) / 400  # Elo scale: P(win) = 1 / (1 + exp(-K * diff))
SEED = 20261018


def load(name):
    return json.loads((DATA / name).read_text())


def generations():
    return load("metrics.json")["generations"]


def h2h_matches():
    """All head-to-head results played at 64 simulations: list of (a, b, wins_a, games)."""
    out = [(r["a"], r["b"], r["wins_a"], r["games"]) for r in load("anchored.json")["results"]]
    out += [(c["gen"], c["vs"], c["wins"], c["games"]) for c in load("strength.json") if c["sims"] == 64]
    return out


def fit_bt(matches, prior_sd=1000.0, iters=100):
    """Bradley-Terry (Elo-scale) ratings by Newton's method, generation 0 fixed at 0.
    A weak Gaussian prior (sd `prior_sd` Elo) keeps ratings finite after one-sided matches.
    Returns {generation: rating}."""
    gens = sorted({g for a, b, _, _ in matches for g in (a, b)})
    free = [g for g in gens if g != 0]
    idx = {g: i for i, g in enumerate(free)}
    r = np.zeros(len(free))
    for _ in range(iters):
        grad = -r / prior_sd ** 2
        hess = -np.eye(len(free)) / prior_sd ** 2
        for a, b, w, n in matches:
            ra = r[idx[a]] if a in idx else 0.0
            rb = r[idx[b]] if b in idx else 0.0
            p = 1 / (1 + math.exp(-K * (ra - rb)))
            g1 = K * (w - n * p)
            h1 = -K * K * n * p * (1 - p)
            for x, s in ((a, 1), (b, -1)):
                if x in idx:
                    grad[idx[x]] += s * g1
                    for y, t in ((a, 1), (b, -1)):
                        if y in idx:
                            hess[idx[x], idx[y]] += s * t * h1
        step = np.linalg.solve(hess, grad)
        r -= step
        if np.abs(step).max() < 1e-9:
            break
    out = {0: 0.0}
    out.update({g: float(r[idx[g]]) for g in free})
    return out


def bootstrap_bt(matches, reps=1000, seed=SEED):
    """Resample the games inside each match (binomial with the observed win rate) and refit.
    Returns {generation: (low, high)} 95% percentile intervals."""
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(reps):
        resampled = [(a, b, int(rng.binomial(n, w / n)), n) for a, b, w, n in matches]
        samples.append(fit_bt(resampled))
    gens = samples[0].keys()
    return {g: (float(np.percentile([s[g] for s in samples], 2.5)),
                float(np.percentile([s[g] for s in samples], 97.5))) for g in gens}


def elo_from_winrate(w):
    """Same formula as train.py (win rate clipped to [0.02, 0.98])."""
    w = min(max(w, 0.02), 0.98)
    return -400 * math.log10(1 / w - 1)


def chained_step_se(games):
    """Standard error (Elo) of one chained step between equal players: delta method at p = 0.5."""
    se_p = math.sqrt(0.25 / games)
    return 400 / math.log(10) / 0.25 * se_p


def interpolate(ratings, upto):
    """Linear interpolation of fitted ratings to every generation 0..upto."""
    xs = sorted(ratings)
    return np.interp(np.arange(upto + 1), xs, [ratings[x] for x in xs])


def simulate_chained(true, games, reps=10000, seed=SEED):
    """Chained Elo trajectories from consecutive-generation matches of `games` games under `true` ratings.
    Returns array (reps, len(true)) starting at 0."""
    rng = np.random.default_rng(seed)
    diffs = np.diff(true)
    p = 1 / (1 + np.exp(-K * diffs))
    wins = rng.binomial(games, p, size=(reps, len(diffs)))
    w = np.clip(wins / games, 0.02, 0.98)
    steps = -400 * np.log10(1 / w - 1)
    return np.concatenate([np.zeros((reps, 1)), np.cumsum(steps, axis=1)], axis=1)


def wilson(w, n, z=1.96):
    """95% Wilson score interval for a win rate."""
    if n == 0:
        return (0.0, 1.0)
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def anchored(design="anchored"):
    path = DATA / f"{design}.json"
    return json.loads(path.read_text())["results"] if path.exists() else []


def step4_pairs():
    """Anchored pairs four generations apart: (a, a+4, wins of the later generation, games)."""
    return [(r["a"], r["b"], r["games"] - r["wins_a"], r["games"]) for r in anchored() if r["b"] - r["a"] == 4]


def per_step_elo_from_step4():
    """Pooled win rate of the later generation over all 4-apart pairs, as Elo per generation."""
    pairs = step4_pairs()
    w = sum(p[2] for p in pairs)
    n = sum(p[3] for p in pairs)
    return w, n, -400 * math.log10(n / w - 1) / 4


def p_misorder(k, step_elo, games):
    """Chance that chained Elo ranks generation g+k below g, when each generation truly gains
    `step_elo` and each chained step is a `games`-game match (normal approximation)."""
    se = chained_step_se(games)
    z = math.sqrt(k) * step_elo / se
    return 0.5 * math.erfc(z / math.sqrt(2))


def write(rel, text):
    path = VENUE_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def to_step(p, k):
    """Win rate over k generations -> equivalent win rate over one generation (Elo divided by k)."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    elo = -400 * math.log10(1 / p - 1) / k
    return 1 / (1 + 10 ** (-elo / 400))
