# Intake: AlphaGo Zero on a laptop CPU — training, evaluating and deploying a 9×9 Go engine end to end (working title)

Sources read: `trainer/runs/main/metrics.json` (44 generations), `trainer/runs/main/strength.json`
(11 head-to-head matches), `trainer/runs_main.log`, `trainer/alphago_lite/*.py` (method as implemented),
`MacApp/Tests/GoEngineTests/test_vectors.json`, `web/tests/run_tests.js`, `docs/SYSTEM-DESIGN.md`,
export logs (Core ML / ONNX parity).

## Method as implemented (from code, not notes)

| Item | Value | Source |
|---|---|---|
| Board, rules | 9×9, simple ko, no suicide, Tromp-Taylor area scoring, komi 7.5, game capped at 162 moves | `go.py` |
| Input | 6 planes: own/opp stones, own/opp stones one move ago, side-to-move, ones | `go.py:features` |
| Network | ResNet, 4 blocks × 48 channels, policy head (82 logits) + value head (tanh); 188,173 parameters | `net.py` (counted) |
| Search | PUCT, c_puct = 1.5, first-play urgency = parent value − 0.25·√(visited prior mass) | `mcts.py` |
| Self-play | 160 games/generation, 10 workers × 16 lock-step games; full search 160 sims on 25% of moves (recorded as samples), fast search 40 sims otherwise (playout-cap randomization); Dirichlet α = 0.12, ε = 0.25 on full searches; temperature 1 for first 10 moves | `selfplay.py`, `metrics.json:config` |
| Training | AdamW lr 1e-3, weight decay 1e-4, batch 256, window ≤ 250k samples, 8-fold symmetry augmentation, steps = 16 × new samples / batch; loss = policy CE + value MSE | `train.py` |
| Per-generation eval | new vs previous, 40 games, 32 sims, temperature for first 6 moves; Elo diff = −400·log10(1/w − 1), w clipped to [0.02, 0.98], summed ("chained Elo") | `train.py`, `selfplay.py:play_match` |
| Head-to-head checks | 80 games, 64 sims, colors alternated (40 each), temperature first 6 moves | `strength_check.py` |
| Hardware | Intel Core i9-9980HK, 8 cores / 16 threads, CPU only | `sysctl` |

## Claims

| # | Claim (my draft wording — please edit) | Evidence (file → fields) | Status |
|---|---|---|---|
| C1 | The full AlphaZero loop (self-play MCTS + residual policy/value network + training) learns 9×9 Go from scratch on one 8-core laptop CPU: 44 generations, 7,040 self-play games, 662 min of wall-clock time. | `metrics.json` → generations[44].total_games = 7040, elapsed_min = 662.3 | supported (one run; wall-clock time includes heavy, varying background load — see disagreements) |
| C2 | Playing strength rises across training: the final network (gen 44) wins 79/80 vs gen 0, 78/80 vs gen 19, 59/80 vs gen 34 and 46/80 vs gen 39. | `strength.json` | supported (single training run, single seed per match set) |
| C3 | Chained Elo from small consecutive-generation matches misjudges progress, even in direction: chained Elo ranks gen 34 (74.2) below gen 19 (127.1) and gen 25 (418.4), while gen 34 beats gen 19 79/80 and gen 25 66/80 head-to-head. Final chained Elo is +251.9; the head-to-head result vs gen 0 (79/80) implies ≈ +760 (clipped). | `metrics.json` → elo; `strength.json` | supported by data; the "≈ +760" and any random-walk error analysis are derived numbers I would compute in a script |
| C4 | One rule set is implemented three times (Python trainer, Swift app, JavaScript browser) and the three agree exactly on board, ko point, legal moves, score and input planes for 433 positions from 40 random games. | `test_vectors.json`; `GoEngineTests.swift`; `run_tests.js` | supported (tests pass) |
| C5 | The trained network exports to Core ML and ONNX with max absolute output difference vs PyTorch of 5.48e-6 and 7.63e-6 (20 random inputs). | export logs; `export_app.py:check_parity`, `export_web.py:check_parity` | supported (re-runnable; I'd log it to a file for the paper) |
| C6 | The same search runs on-device in a native Mac app (Core ML) and in the browser (ONNX Runtime Web, WebAssembly, single thread); 400 simulations take about 1 s in the browser; the browser and app produce identical root visit counts for the same position. | one manual browser timing (1,005 ms) and one manual observation (F6, 166 visits) | **partial** — not logged; needs a scripted benchmark if it goes in the paper |
| C7 | Engineering lessons for low-budget AlphaZero: lock-step batched MCTS, playout-cap randomization, first-play urgency, and a self-healing worker pool (a run stalled for 2 h when `multiprocessing.Pool` lost jobs from dead workers). | code; `runs_main.log`; git history | partial (design facts are solid; there are no ablations showing each choice's effect) |
| C8 | The engine plays at the level of a capable beginner. | none | **unsupported** — no games vs humans or an external engine; I would not put this in the paper unless we measure it |

## Facts I still need from you
- **Target venue** (and track: main, workshop, demo, education). This decides page limits, anonymity and how much evidence is expected — see my honest assessment below.
- **Author list and affiliations** (for camera-ready; for anonymous review I'll leave them out).
- **Whether to run more experiments** before writing (options below). Several would make C2/C3/C7 much stronger.
- **Funding / acknowledgements**, if any.
- Whether the public repo and live site may be cited in the paper (they reveal authorship, so they can't appear in an anonymous submission as-is).

## Disagreements between inputs
- `metrics.json:config` records the first sitting only (`hours: 4.0`); later sittings used `--hours 3`, `1.5` and `1.5`, and one sitting stalled for 2 h producing nothing. The paper should report generations and games, and treat wall-clock time as approximate (other software loaded the CPU heavily during generations 32–44: self-play time per generation ranged from 197 s to 2,903 s).
- `docs/SYSTEM-DESIGN.md` says "about 190k parameters"; the code counts 188,173. The paper will use the counted value.
- Per-generation evaluation uses 32 simulations; head-to-head checks use 64. Results from the two are not directly comparable — the paper must say so.
- Only 11 head-to-head pairs exist; there is no evaluation of every generation against a fixed anchor, so a full learning curve of "true" strength isn't available yet.

## Honest assessment of the evidence vs. venues
- **Main track at NeurIPS / ICML / ICLR:** not competitive as is. One training run, no seeds, no ablations, no external benchmark, and the algorithm itself is known. Reviewers would call it a reproduction.
- **Realistic fits:** an education venue (e.g. EAAI, the AAAI symposium on educational advances in AI: an end-to-end, inspectable AlphaZero that trains on a laptop, with a visualizer); a games venue short/demo paper (e.g. IEEE Conference on Games, or Advances in Computer Games); or a workshop paper focused on C3 — evaluating small self-play runs (why chained Elo misleads and what to use instead). The C3 angle gets much stronger with the anchored-evaluation experiment below.
