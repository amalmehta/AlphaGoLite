# Experiment 02 — re-run the training-time evaluation with its original seeds

**Question.** I-01 found the training log's consecutive matches (gens 24→44, 32 sims) gave the newer network 0.492,
while a fresh replay with the same settings gave 0.571 (z = 3.16). Was the log an unlucky draw, or did evaluation during
training differ from evaluation now?

**Design.** For each generation g = 25 … 44, repeat exactly the call `train.py` made after training generation g:
`play_match(gen_g.pt, gen_{g-1}.pt, 4, 32, g*7919 + w, 1)` for w = 0 … 9 (40 games, new network = A), and compare the
summed wins with the log (`metrics.json`: winrate_vs_prev × 40). One job is run twice to confirm that a game is
deterministic given its seed on this machine.

**What would change the conclusion.**
- Every pair reproduces the logged wins exactly → weights and code are unchanged and the log was a rare draw (seeds);
  the paper must attribute the misleading curve to match noise, and drop the "shallow evaluation" story.
- Pairs do not reproduce → something differed between training-time and offline evaluation (code, weights, or
  nondeterminism); the paper must report that as the finding and investigate the cause.

**Compute.** 800 games at 32 sims ≈ 5.1 s each on one worker → ≈ 10–15 min on 10 workers (longer under load).
