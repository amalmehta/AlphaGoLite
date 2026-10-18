# Improvement ideas: Chained Elo Can Point the Wrong Way (AAAI-27-format draft)

> Mode: own draft · Generated 2026-10-18 · Budget: CPU, ≤ 30 min per experiment, ≤ 2 h per round
> Pilot timing (2026-10-18, load ≈ 8): one evaluation game takes 5.1 s at 32 simulations, 10.3 s at 64 and 21.9 s
> at 128 on one worker; 10 workers run in parallel (≈ 8× speed-up on this machine).

## Ranked ideas
| # | Idea | Type | Impact | Effort | Compute | Literature | Status |
|---|---|---|---|---|---|---|---|
| I-01 | Re-run the log's 32-sim consecutive matches with fresh seeds | evidence | High | 1 h | ≈ 10 min | no close match in searched sources (not proof of novelty) | done — undercuts claim |
| I-02 | Search-depth sweep: measured gap vs. simulations per move | evidence | High | 1.5 h | ≈ 20 min | related work: wu2019strength, liu2020strength | proposed |
| I-03 | Disclose that the code was also written with an AI assistant | writing | High | 15 min | none | related work: sherwood2026agents | applied |
| I-04 | Position against recent limited-compute and anchored evaluations | reviewer | High | 1 h | none | related work: braun2026efficient, sherwood2026agents, lanctot2023vase | applied |
| I-05 | Scope the claim as a case study (title, abstract) | reviewer | Medium | 20 min | none | not applicable (presentation) | proposed |
| I-06 | Put the replay's key numbers in the abstract | writing | Medium | 15 min | none | not applicable (presentation) | proposed |
| I-07 | Rating fit with an upset floor | evidence | Medium | 1.5 h | < 1 min | related work: coulom2008whr | proposed |
| I-08 | How many anchor games are enough? Subsample the anchored data | evidence | Medium | 1 h | < 1 min | no close match in searched sources (not proof of novelty) | proposed |
| I-09 | A boxed, copy-paste evaluation protocol | writing | Low | 30 min | none | not applicable (presentation) | proposed |
| I-10 | Evaluation compression as a general effect across games | direction | Medium | days | hours | related work: wu2019strength | proposed |
| I-11 | Sequential testing for per-generation decisions | direction | Low | 1 day | ≈ 1 h | no close match in searched sources (not proof of novelty) | proposed |

## Details

### I-01 · Re-run the log's 32-sim consecutive matches with fresh seeds
- **Type:** evidence · **Impact:** High · **Effort:** 1 h · **Compute:** ≈ 10 min (800 games × 5.1 s / 8 workers, from the pilot)
- **Motivated by:** §5 "On any one pair the difference between the log and the replay is within noise, so we cannot
  fully separate the effect of search depth from the play of chance with one run." The log gave \valConsWrLog{} = 0.493,
  the 64-sim replay 0.537 (`data/consecutive.json`).
- **Idea:** replay the same consecutive pairs (generations 24→44) at **32** simulations with new random seeds, exactly as
  the training log did (40 games, temperature for 6 moves). This separates "32-sim matches compress the gap" from
  "the log was an unlucky draw".
- **Why it matters:** it is the cleanest control for the paper's central causal claim (Contribution 2).
- **What would change the conclusion:** a fresh 32-sim win rate near 0.49–0.51 supports "shallow evaluation compresses
  differences"; a rate near 0.54 (like the 64-sim replay) means the log was mostly bad luck, and the paper must say that
  noise, not search depth, explains the failure.
- **Literature:** no close match in searched sources (not proof of novelty) — searches on chained/relative Elo in
  self-play found no study of this failure (see Literature searched).
- **Status:** done — see [findings](experiments/01_fresh_32sim_replay/findings.md). Fresh 32-sim replay: 0.571
  (457/800), higher than the log's 0.492 on the same pairs (z = 3.16) and not lower than the 64-sim replay (0.537).
  The "too-shallow matches" explanation is not supported; paper text not yet changed (awaiting the author).

### I-02 · Search-depth sweep: measured gap vs. simulations per move
- **Type:** evidence · **Impact:** High · **Effort:** 1.5 h · **Compute:** ≈ 20 min (5 pairs four apart × 40 games at 16/32/64/128 sims)
- **Motivated by:** §6 lesson 1 "Matches that are too shallow compress real differences toward a draw" — currently
  supported by two sim counts only (32 in the log, 64 in the replay).
- **Idea:** for the five pairs four generations apart in gens 24–44 (24/28 … 40/44), play 40 games each at 16, 32, 64
  and 128 simulations, and plot the newer network's win rate against simulations (a new figure).
- **Why it matters:** turns lesson 1 from an inference into a measured curve, and tells practitioners how deep is deep
  enough at this scale.
- **What would change the conclusion:** a win rate that rises with simulations supports compression; a flat curve would
  undercut it and point back to noise (I-01).
- **Literature:** related work: wu2019strength, liu2020strength — these vary an MCTS program's strength through its
  move-selection policy and relate it to Elo; they do not study how evaluation depth changes measured gaps between
  training generations.
- **Status:** proposed

### I-03 · Disclose that the code was also written with an AI assistant
- **Type:** writing · **Impact:** High · **Effort:** 15 min · **Compute:** none
- **Motivated by:** §7 "Use of AI tools" lists only drafting text, figure scripts and references. The training
  pipeline, apps, evaluation scripts and benchmarks in this repository were also written with an AI coding assistant.
- **Idea:** state that the implementation was written with an AI coding assistant under the author's direction and
  checked by the tests and parity checks described in §5.
- **Why it matters:** honesty and venue policy; reviewers who find the repository history would otherwise see an
  undisclosed fact. It is also mildly interesting context (see the related record).
- **Literature:** related work: sherwood2026agents — coding agents implementing an AlphaZero pipeline on consumer
  hardware, evaluated against a solver-anchored round robin; directly related context for an AI-built pipeline.
- **Status:** applied — §7 "Use of AI tools" now states the implementation was written with an AI coding assistant.

### I-04 · Position against recent limited-compute and anchored evaluations
- **Type:** reviewer · **Impact:** High · **Effort:** 1 h · **Compute:** none
- **Motivated by:** §2 cites only 2016–2021 work on AlphaZero reimplementations and evaluation.
- **Idea:** *A reviewer may say "anchored evaluation is standard; what is new?"* → add a paragraph: recent
  limited-compute AlphaZero work rates engines against fixed external ladders (braun2026efficient) or a solver-anchored
  round robin (sherwood2026agents); evaluation via social choice is another alternative to Elo (lanctot2023vase). Our
  contribution is the documented failure of the cheap internal signal, its cause, and a protocol for runs too weak for
  an external ladder (our network lost 40/40 to GNU Go level 1, so an external anchor could not separate generations).
- **Why it matters:** it answers the most likely novelty objection with verified records.
- **Literature:** related work: braun2026efficient, sherwood2026agents, lanctot2023vase — fixed-ladder evaluation under
  limited compute; anchored round robin on consumer hardware; voting-based agent evaluation.
- **Status:** applied — new paragraph in §2; three references added to refs.bib and verified against arXiv.

### I-05 · Scope the claim as a case study (title, abstract)
- **Type:** reviewer · **Impact:** Medium · **Effort:** 20 min · **Compute:** none
- **Motivated by:** title "Chained Elo Can Point the Wrong Way" and §7 "This is one training run with one seed".
- **Idea:** *A reviewer may say "one run cannot support a general claim"* → add "A Case Study" to the subtitle and say
  "in one run" in the abstract's first result sentence.
- **Why it matters:** matches the wording to the evidence (one run, one seed).
- **Literature:** not applicable (presentation)
- **Status:** proposed

### I-06 · Put the replay's key numbers in the abstract
- **Type:** writing · **Impact:** Medium · **Effort:** 15 min · **Compute:** none
- **Motivated by:** abstract "Replaying the same consecutive matches with more search per move recovers the correct
  direction" — no numbers, while the evidence is crisp (+159 vs −344 Elo from gen 25 to 34).
- **Idea:** add the numbers via the existing `\valReplayChain`, `\valInversion` macros.
- **Why it matters:** reviewers skim abstracts; the headline result should be quantitative.
- **Literature:** not applicable (presentation)
- **Status:** proposed

### I-07 · Rating fit with an upset floor
- **Type:** evidence · **Impact:** Medium · **Effort:** 1.5 h · **Compute:** < 1 min
- **Motivated by:** §5 "Its Pearson χ² is 323 over 41 matches … in very lopsided pairs the weaker network still wins a
  few games … We therefore do not quote a total Elo gain".
- **Idea:** fit Bradley–Terry with a mixture term — with probability ε the result is a coin flip (opening randomness) —
  fit ε by maximum likelihood, and report whether χ² drops to a plausible level and what total gain it implies.
- **Why it matters:** a well-fitting model would let the paper quote a total gain with an interval, which reviewers will ask for.
- **What would change the conclusion:** if the floor model fits, Fig. 3c becomes a scale and a total gain can be quoted;
  if not, the current "read as a ranking" caveat stands, now justified.
- **Literature:** related work: coulom2008whr — a Bayesian rating model for time-varying strength; it does not add an
  upset floor, but is the natural alternative model to mention.
- **Status:** proposed

### I-08 · How many anchor games are enough? Subsample the anchored data
- **Type:** evidence · **Impact:** Medium · **Effort:** 1 h · **Compute:** < 1 min
- **Motivated by:** §6 "It cost 40 games per sampled generation" — the cost claim of the protocol rests on one design.
- **Idea:** subsample the anchored games (10, 20, 30, 40 per sampled generation, bootstrap) and report how often the
  score-vs-anchor curve shows the true upward trend (e.g. a positive rank correlation with generation).
- **Why it matters:** gives practitioners a budget for the recommended protocol, using data already collected.
- **What would change the conclusion:** if 10–20 games already recover the trend reliably, the protocol is even cheaper
  than stated; if 40 is marginal, the recommendation must raise the budget.
- **Literature:** no close match in searched sources (not proof of novelty)
- **Status:** proposed

### I-09 · A boxed, copy-paste evaluation protocol
- **Type:** writing · **Impact:** Low · **Effort:** 30 min · **Compute:** none
- **Motivated by:** §6's three-item list sits in running text; 3 of 7 pages are unused.
- **Idea:** turn the protocol into a small algorithm box with concrete defaults taken from this run (anchors, games,
  simulations), referencing I-02's result if run.
- **Why it matters:** practitioners adopt what they can copy; workshop reviewers value a clear takeaway.
- **Literature:** not applicable (presentation)
- **Status:** proposed

### I-10 · Evaluation compression as a general effect across games
- **Type:** direction · **Impact:** Medium · **Effort:** days · **Compute:** hours
- **Motivated by:** §7 "We do not know how often chained Elo misleads in other runs, games or network sizes".
- **Idea:** train a second small run (e.g. Connect Four or a 7×7 board, a few hours) and measure the gap between two
  checkpoints across simulation counts; first experiment = I-02's sweep on the new run.
- **Why it matters:** generality is the main thing a single case study lacks.
- **Literature:** related work: wu2019strength — strength–simulation relations for one MCTS program, not across games or
  training generations.
- **Status:** proposed

### I-11 · Sequential testing for per-generation decisions
- **Type:** direction · **Impact:** Low · **Effort:** 1 day · **Compute:** ≈ 1 h
- **Motivated by:** §6 "promote a network only when it beats the current release head to head" — no stopping rule given.
- **Idea:** replace fixed 40-game gating matches with a sequential test that stops early when the result is clear, and
  measure games saved on this run's pairs.
- **Why it matters:** could cut evaluation cost further for small runs.
- **Literature:** no close match in searched sources (not proof of novelty) — sequential testing is common practice in
  chess-engine development, but our searches found no citable record of it.
- **Status:** proposed

## Records cited

| Key | Record | ID |
|---|---|---|
| wu2019strength | On Strength Adjustment for MCTS-Based Programs (AAAI 2019) | doi:10.1609/AAAI.V33I01.33011222 |
| liu2020strength | Strength Adjustment and Assessment for MCTS-Based Programs (IEEE CIM 2020) | doi:10.1109/MCI.2020.2998315 |
| braun2026efficient | Engineering Efficient Self-Play Chess: Search, Replay, and Throughput Under Limited Compute (2026) | doi:10.48550/arxiv.2609.37447 |
| sherwood2026agents | Frontier Coding Agents Can Now Implement an AlphaZero Self-Play ML Pipeline for Connect Four … (2026) | doi:10.48550/arxiv.2604.25067 |
| lanctot2023vase | Evaluating Agents using Social Choice Theory (2023) | doi:10.48550/arxiv.2312.03121 |
| coulom2008whr | Whole-History Rating (Computers and Games 2008) — already in the paper | doi:10.1007/978-3-540-87608-3_11 |

## Literature searched

| Group | Queries | Services that answered | Results |
|---|---|---|---|
| Chained / relative Elo in self-play | "self-play Elo relative previous checkpoint inflation"; "AlphaZero training progress evaluation Elo"; "Elo rating drift self-play generations" | arXiv, OpenAlex, Crossref, Semantic Scholar | [chained_elo.md](literature/chained_elo.md) |
| Search depth and strength | "MCTS simulations playing strength scaling AlphaZero"; "search depth evaluation strength difference game agents" | all four | [search_depth.md](literature/search_depth.md) |
| Small-compute AlphaZero | "AlphaZero reproduction limited compute small board"; "efficient AlphaZero training single machine Go" | all four | [small_alphazero.md](literature/small_alphazero.md) |
| Rating and evaluating agents | "evaluating agents Elo nontransitivity rating"; "statistical comparison game playing agents confidence intervals" | all four | [rating_eval.md](literature/rating_eval.md) |
| Elo inflation and gating | "self-play Elo inflation Leela Zero"; "gating evaluation new network self-play win rate threshold"; "Elo difference playouts per move evaluation games" | arXiv, OpenAlex, Crossref (Semantic Scholar: rate-limited, 429) | [elo_inflation.md](literature/elo_inflation.md) |
| Sequential testing | "sequential probability ratio test engine testing games"; "statistical testing playing strength computer chess" | arXiv, OpenAlex, Crossref (Semantic Scholar: rate-limited, 429) | [sequential_testing.md](literature/sequential_testing.md) |

All queries were topic keywords run with `--guard-text aaai27/sections`; no draft text was sent.

## Log
- 2026-10-18 — ideas generated; pilot timing recorded above.
- 2026-10-18 — I-03, I-04 applied (§7 disclosure, §2 positioning, 3 verified references).
- 2026-10-18 — I-01 run (695 s): fresh 32-sim replay 457/800 = 0.571 vs log 0.492 (z = 3.16) and 64-sim replay 0.537.
  **Undercuts** the paper's "too-shallow matches" explanation; reported to the author before any claim edit.
