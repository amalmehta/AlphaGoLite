# Outline — AAAI-27 workshop paper (AAAI two-column, 7 content pages + references)

**Working title:** *Chained Elo Can Point the Wrong Way: Evaluating a Laptop-Scale AlphaZero for 9×9 Go*

**One-sentence pitch:** We train an AlphaZero-style 9×9 Go engine end to end on one laptop CPU and deploy it
natively and in the browser; tracking progress the usual cheap way — summing Elo from small matches between
consecutive generations — told us training had stalled or regressed, while anchored head-to-head games show
steady improvement. We quantify why, and recommend an evaluation protocol that fits a small budget.

## Page budget (7.0 pages)
| Section | Pages | Carries claims |
|---|---|---|
| Abstract | 0.25 | C1–C3, C8 headline |
| 1 Introduction (+ contributions) | 0.85 | all |
| 2 Related work | 0.55 | — |
| 3 System: training on a laptop | 1.35 (incl. Fig. 1, Table 1) | C1, C7 |
| 4 Evaluating small self-play runs | 0.75 | C3 (method) |
| 5 Results | 2.4 (incl. Figs. 2–4, Tables 2–3) | C1–C6, C8 |
| 6 Lessons for low-budget AlphaZero | 0.35 | C7 |
| 7 Limitations and conclusion | 0.4 | — |
| AI-use note | 0.1 | — |

## Section plan
1. **Introduction.** Small self-play runs (teaching, hobby engines, research prototypes) can't afford big
   evaluations, so progress is often tracked by matching each new network against its predecessor and summing
   the Elo differences. Our run is a case where that signal was wrong in direction (gen 34 rated below gens 19
   and 25, yet beating both head-to-head). Contributions (as confirmed): (i) an open, laptop-trainable
   AlphaZero pipeline with identical rules in Python, Swift and JavaScript and on-device deployment (§3, §5.5);
   (ii) an anchored evaluation of the whole run, showing steady gains that chained Elo misses (§5.2);
   (iii) a simulation explaining the error — chained Elo is a random walk whose spread grows with the number
   of generations (§5.3) — and a cheap protocol to use instead (§4, §6); (iv) an external calibration against
   GNU Go that bounds what such a run actually achieves (§5.4).
2. **Related work.** AlphaGo/AlphaGo Zero/AlphaZero; efficient reimplementations (Leela Zero, MiniGo,
   KataGo — playout-cap randomization); rating systems (Elo, Bradley–Terry, BayesElo/Ordo-style fits);
   evaluation practice in self-play (gating, chained Elo). Each group ends with how we differ.
3. **System.** Rules (9×9, Tromp-Taylor, komi 7.5, simple ko); input planes; network (4×48 ResNet, 188k params);
   PUCT with Leela-style first-play urgency; lock-step batched self-play; playout-cap randomization; training
   loop; hardware. Fig. 1 pipeline + deployment; Table 1 hyperparameters (from code).
4. **Evaluating small self-play runs.** Define chained Elo; show its variance grows linearly with generations
   (each 40-game step has a standard error of ≈ X Elo at p = 0.5 — computed in a script). Anchored design:
   which generation pairs we play, 40 games each, colors balanced; Bradley–Terry fit with bootstrap CIs.
5. **Results.**
   - 5.1 The run (C1): generations, games, wall time with its caveat; loss curves (Fig. 2, maybe merged).
   - 5.2 Chained vs anchored (C2, C3): Fig. 3 — both rating curves on one axis, CIs on the anchored one.
   - 5.3 Why chained Elo drifts (C3): Fig. 4 — simulated chained-Elo trajectories from the fitted ratings,
     with 40-game steps; how often they show a false decline.
   - 5.4 External calibration (C8): Table 2 — gen 44 vs GNU Go 3.8 (level 1; level 10 if informative).
     Wording follows the result; no "capable beginner" unless the data says so.
   - 5.5 One rule set, three platforms (C4–C6): Table 3 — parity tests, export error, sims/s and root
     visit-count agreement for Python/PyTorch, Swift/Core ML, browser/ONNX.
6. **Lessons (C7).** Lock-step batching, playout caps, FPU, self-healing worker pool; CPU contention effects
   (self-play time per generation ranged 197–2,903 s).
7. **Limitations, conclusion.** One run, one seed; 9×9 only; small network; evaluation at 64 simulations;
   wall-clock under uncontrolled load; no human games.

## Figure and table plan
| ID | Takeaway (first caption sentence) | Data | Script | Width |
|---|---|---|---|---|
| Fig. 1 | One loop trains on a laptop; the same rules and network run in three runtimes. | — (diagram) | `figures/pipeline.tex` (TikZ) | full |
| Fig. 2 | Losses fall steadily over 44 generations. | `metrics.json` | `loss_curves.py` | column |
| Fig. 3 | Chained Elo says training stalled after gen 25; anchored ratings say it kept improving. | `metrics.json`, `anchored.json`, `strength.json` | `elo_comparison.py` | full (or column) |
| Fig. 4 | With 40-game steps, chained Elo wanders by ±N Elo after 44 generations. | fitted ratings | `chained_sim.py` | column |
| Table 1 | Hyperparameters | code constants + `metrics.json:config` | `hyperparams_table.py` | column |
| Table 2 | Gen 44 vs GNU Go | `gnugo.json` | `gnugo_table.py` | column |
| Table 3 | Cross-platform parity and speed | `parity.json`, `bench.json` | `platform_table.py` | column |

## Required statements / checklist
- Reproducibility checklist (main-track requirement; workshop likely not) — draft from facts if required.
- AI-use note: the paper text, figure/table scripts and citation formatting were drafted with an AI assistant
  (Claude Code with the paper-writer skill); the author reviewed all content.

## Experiment status (results drive §5.2–5.5)
- Done: anchored evaluation, 30 pairs × 40 games, 64 sims → `paper/alphago-lite/data/anchored.json`.
- Done: gen 44 (400 sims) vs GNU Go 3.8 level 1, 40 games → won 0/40 (`data/gnugo.json`). C8 ("capable
  beginner") is not supported; §5.4 reports the loss as an external calibration.
- To do: cross-platform benchmark (needs a quiet machine); chained-Elo simulation (after the anchored fit).

## Changelog
- 2026-10-08 — first outline.
- 2026-10-18 — anchored evaluation and GNU Go match finished; data copied to `paper/alphago-lite/data/`.
- 2026-10-18 — consecutive replay finished; explanation changed from "adjacency" to "shallow (32-sim) per-generation matches + noise"; abstract, intro, §5, §6, §7 and Fig. 4 updated; flatten script for the single-file submission.
