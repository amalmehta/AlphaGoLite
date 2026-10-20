# I-01 plan — fresh 32-simulation replay of consecutive pairs

**Hypothesis.** Matches at 32 simulations a move compress the gap between consecutive generations. If so, a fresh
replay at 32 simulations (new seeds) reproduces the training log's low win rate for the newer network (≈ 0.49–0.51),
below the 64-simulation replay (0.537).

**Claim tested.** Contribution 2 / §5 "Why": the training log misled mainly because its per-generation matches were too
shallow, not only because of noise.

**What would change the conclusion.**
- Fresh 32-sim rate near 0.49–0.51 (clearly below 0.537): supports "shallow evaluation compresses differences".
- Fresh 32-sim rate near 0.537: the log's result was mostly an unlucky draw; the paper must attribute the failure to
  noise rather than search depth, and lesson 1 must be weakened.

**Design.** Pairs (g, g+1) for g = 24 … 43 (20 pairs), 40 games each (colors balanced), 32 simulations a move,
temperature for the first 6 moves — identical to the training log's matches (`train.py`: eval_games 40, eval_sims 32,
`play_match(temp_moves=6)`) except for new random seeds (base 777000, disjoint from the log's `gen*7919+w` and the
64-sim replay's seeds). Same weights files (`trainer/runs/main/weights/gen_*.pt`), read-only.

**Metrics.** Pooled win rate of the newer network with a 95% Wilson interval; per-pair wins; chained Elo over 25→34 and
24→44 with the training formula.

**Compute estimate (pilot, 2026-10-18).** 5.1 s per game at 32 sims on one worker; 800 games on 10 workers (≈ 8×
effective) ≈ 9 min. Within the 30-minute budget.
