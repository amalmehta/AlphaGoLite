# I-01 findings — fresh 32-simulation replay (run 2026-10-18, 695 s wall time)

All numbers from `results/replay32.json` (20 pairs, 800 games), compared with `data/consecutive.json` (64-sim replay)
and `data/metrics.json` (training log, 32 sims), same pairs (generations 24→44).

| Measurement (same 20 pairs) | Newer generation won | Rate | 95% Wilson |
|---|---|---|---|
| Training log, 32 sims | 394/800 | 0.492 | — |
| **Fresh replay, 32 sims (I-01)** | **457/800** | **0.571** | 0.537–0.605 |
| Replay, 64 sims | 430/800 | 0.537 | 0.503–0.572 |

- Fresh 32-sim vs. training log (same settings, different seeds): z = 3.16 (two-proportion test).
- Fresh 32-sim vs. 64-sim replay: z = 1.36 — no evidence that deeper search measures a larger gap.
- Chained Elo from generation 25 to 34: fresh 32-sim +675, 64-sim replay +159, training log −344.
- The log is lower than the fresh 32-sim replay on 15 of the 20 pairs.

## What this means for the paper

**It undercuts the current explanation.** The draft says the log misled "mainly because the per-generation matches
were too cheap" (32 simulations). Replaying the same pairs at the same 32 simulations with fresh seeds reproduces the
anchored gains (0.571, if anything higher than at 64 simulations). So search depth does not explain the log.

What remains: the training-time evaluation matches came out systematically lower than offline replays of the same
pairs with the same protocol. Either (a) the log is an unlucky draw (z = 3.16 pooled over 20 pairs, p ≈ 0.002 if the
pairs are independent), or (b) something differed between evaluation during training and evaluation afterwards (a
bug, or weights files that changed after the log was written).

## Suggested next diagnostic (not run — needs approval)
Re-run the exact training-time call for a few pairs with the **original seeds** (`play_match(cur, prev, 4, 32,
gen*7919 + w, 1)` for w = 0…9). Self-play evaluation is deterministic given the seed on this CPU, so:
- if it reproduces the logged wins exactly, the weights and code are unchanged and the log was a (rare) draw;
- if it does not, evaluation during training differed from evaluation now — a reproducibility problem the paper
  must report (and which is itself a strong lesson for small runs).
Estimated cost: ~1 min per pair (40 games at 32 sims on 10 workers).
