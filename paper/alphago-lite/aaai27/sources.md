# Sources

<!-- BEGIN GENERATED (make_values.py) -->
| Macro | Value | Meaning | Source / computation |
|---|---|---|---|
| `\valNGens` | 44 | generations trained | metrics.json: generations[-1].gen |
| `\valTotalGames` | 7,040 | self-play games | metrics.json: generations[-1].total_games |
| `\valWallHours` | 11.0 | wall-clock hours of training | metrics.json: generations[-1].elapsed_min / 60 |
| `\valGamesPerGen` | 160 | self-play games per generation | metrics.json: config.games_per_gen |
| `\valPolicyLossFirst` | 4.09 | policy loss, generation 1 | metrics.json: generations[1].policy_loss |
| `\valPolicyLossLast` | 2.90 | policy loss, last generation | metrics.json: generations[-1].policy_loss |
| `\valValueLossFirst` | 0.69 | value loss, generation 1 | metrics.json: generations[1].value_loss |
| `\valValueLossLast` | 0.57 | value loss, last generation | metrics.json: generations[-1].value_loss |
| `\valSelfplayMin` | 197 | fastest self-play phase of a generation (s) | metrics.json: min selfplay_sec |
| `\valSelfplayMax` | 2,903 | slowest self-play phase of a generation (s) | metrics.json: max selfplay_sec |
| `\valChainedFinal` | +252 | chained Elo of the last generation | metrics.json: generations[-1].elo |
| `\valChainedPeak` | +418 | highest chained Elo | metrics.json: max elo |
| `\valChainedPeakGen` | 25 | generation with the highest chained Elo | metrics.json: argmax elo |
| `\valChainedNineteen` | +127 | chained Elo of generation 19 | metrics.json: generations[19].elo |
| `\valChainedTwentyFive` | +418 | chained Elo of generation 25 | metrics.json: generations[25].elo |
| `\valChainedThirtyFour` | +74 | chained Elo of generation 34 | metrics.json: generations[34].elo |
| `\valInversion` | 344 | chained Elo of generation 25 minus generation 34 | metrics.json: elo[25] - elo[34] |
| `\valMeanWrPrev` | 0.508 | mean win rate vs previous generation (32 sims, 40 games) | metrics.json: mean winrate_vs_prev |
| `\valMeanWrPrevSE` | 0.018 | standard error of that mean | metrics.json: std(winrate_vs_prev)/sqrt(n) |
| `\valEvalGames` | 40 | games per chained step | metrics.json: config.eval_games |
| `\valEvalSims` | 32 | simulations per move in chained steps | metrics.json: config.eval_sims |
| `\valStepSE` | 55 | SE (Elo) of one 40-game step at p = 0.5 | common.chained_step_se(40) |
| `\valWalkSD` | 364 | SD (Elo) of a chained sum after all generations from noise alone | chained_step_se(40) * sqrt(44) |
| `\valHTtfVsTf` | 66/80 | generation 34 wins vs generation 25 (64 sims) | strength.json: gen=34, vs=25 |
| `\valHTtfVsNt` | 79/80 | generation 34 wins vs generation 19 (64 sims) | strength.json: gen=34, vs=19 |
| `\valHFfVsTtf` | 59/80 | generation 44 wins vs generation 34 (64 sims) | strength.json: gen=44, vs=34 |
| `\valHFfVsTn` | 46/80 | generation 44 wins vs generation 39 (64 sims) | strength.json: gen=44, vs=39 |
| `\valHFfVsZero` | 79/80 | generation 44 wins vs generation 0 (64 sims) | strength.json: gen=44, vs=0 |
| `\valHFfVsNt` | 78/80 | generation 44 wins vs generation 19 (64 sims) | strength.json: gen=44, vs=19 |
| `\valAnchoredPairs` | 30 | anchored pairs played | anchored.json: len(results) |
| `\valAnchoredGames` | 1,200 | games in anchored pairs | anchored.json: sum games |
| `\valAnchoredSims` | 64 | simulations per move in anchored games | anchored.json: sims |
| `\valHtoHGames` | 2,080 | all 64-sim head-to-head games | anchored.json + strength.json |
| `\valAnchorScores` | 0, 0, 1, 0, 0, 0, 2, 6, 6, 8, 16 | wins vs the last generation, every 4th generation in order | anchored.json: b=44, wins_a by a |
| `\valStepFourWr` | 0.786 | pooled win rate of the later generation over pairs 4 apart | anchored.json: b-a=4 |
| `\valStepElo` | 57 | implied Elo gain per generation from pairs 4 apart | common.per_step_elo_from_step4 |
| `\valStepWr` | 0.581 | implied per-generation win rate | from StepElo |
| `\valStepWrLo` | 0.567 | 95% lower bound of that per-generation rate | Wilson bound on pooled 4-apart rate, converted with common.to_step |
| `\valStepWrHi` | 0.595 | 95% upper bound | same |
| `\valPMisorderOne` | 0.15 | chance a 40-game chained step shows a decline, if each generation gains StepElo | common.p_misorder(1, StepElo, 40) |
| `\valPMisorderNine` | $1\times10^{-3}$ | chance noise alone makes chained Elo rank g+9 below g (40-game steps) | common.p_misorder(9, StepElo, 40) |
| `\valBTChiSq` | 323 | Pearson chi-square of the Bradley-Terry fit | common.fit_bt on all 64-sim matches |
| `\valBTMatches` | 41 | matches in the Bradley-Terry fit | anchored.json + strength.json |
| `\valBTFree` | 17 | free ratings in the fit | common.fit_bt |
| `\valConsPairs` | 20 | consecutive pairs replayed at 64 sims | consecutive.json |
| `\valConsFrom` | 24 | first generation of the replay | consecutive.json |
| `\valConsWr` | 0.537 | pooled win rate of the newer generation, 64 sims | consecutive.json |
| `\valConsWrLo` | 0.503 | 95% Wilson lower bound | consecutive.json |
| `\valConsWrHi` | 0.572 | 95% Wilson upper bound | consecutive.json |
| `\valConsWrLog` | 0.493 | same pairs in the training log (32 sims) | metrics.json: winrate_vs_prev for those generations |
| `\valLateStepWr` | 0.547 | per-generation rate from 4-apart pairs within gens 24-44 | anchored.json: b-a=4, a>=first replayed generation; common.to_step |
| `\valLateStepWrLo` | 0.529 | 95% lower bound | Wilson, common.to_step |
| `\valLateStepWrHi` | 0.565 | 95% upper bound | Wilson, common.to_step |
| `\valLateStepElo` | 33 | implied Elo per generation in that range | from LateStepWr |
| `\valReplayChain` | +159 | chained Elo from gen 25 to 34 using the 64-sim replay | consecutive.json, train.py Elo formula |
| `\valHtoHEloTtfTf` | +269 | Elo difference implied by gen 34 vs gen 25 head-to-head | strength.json: 66/80 -> Elo |
| `\valDropZ` | $-$3.9 | log's 25->34 chained change, in SDs below what LateStepElo predicts | (elo[34]-elo[25] - 9*LateStepElo) / (StepSE*sqrt(9)) |
| `\valDropExpect` | +295 | expected chained change from 25 to 34 under LateStepElo | 9 * LateStepElo |
| `\valReplayChainAll` | +551 | replay chained Elo over gens 24-44 | consecutive.json |
| `\valLogChainAll` | $-$114 | log chained Elo over the same gens | metrics.json |
| `\valGnuWins` | 0/40 | wins vs GNU Go | gnugo.json |
| `\valGnuSims` | 400 | our simulations per move vs GNU Go | gnugo.json |
| `\valGnuLevel` | 1 | GNU Go level | gnugo.json |
| `\valGnuMedianMargin` | 81.0 | median losing margin vs GNU Go (points) | gnugo.json: median |our_score_black| |
| `\valGnuScoreAgree` | 40/40 | games where GNU Go's own final_score names the same winner as ours | gnugo.json: gnugo_final_score prefix vs sign of our_score_black |
| `\valRuleCases` | 433 | rule-parity positions | bench/export_parity.json |
| `\valRuleGames` | 40 | random games the positions come from | bench/export_parity.json |
| `\valCoreMLDiff` | 5.5 | max |Core ML - PyTorch| (x1e-6) | bench/export_parity.json |
| `\valOnnxDiff` | 7.6 | max |ONNX - PyTorch| (x1e-6) | bench/export_parity.json |
| `\valNParams` | 188,173 | network parameters | trainer/alphago_lite/net.py (counted) |
| `\valBenchPositions` | 15 | benchmark positions | bench/result_python.json |
| `\valBenchSims` | 400 | simulations per benchmark search | bench/result_python.json |
| `\valBenchIdentical` | all | positions with identical root visits on all platforms | bench/result_*.json |
<!-- END GENERATED -->

## Hand-typed settings and facts in the prose

| Text | Meaning | Source |
|---|---|---|
| 9$\times$9, simple ko, no suicide, Tromp--Taylor, komi 7.5, 162 moves | rules | `trainer/alphago_lite/go.py` (`N`, `KOMI`, `MAX_MOVES`, `legal_mask`, `area_score`) |
| six planes; 81 points and pass | network input/output | `go.py:features` (`NUM_PLANES = 6`), `NUM_MOVES = 82` |
| first-play urgency = parent value − reduction·√(visited prior) | search | `trainer/alphago_lite/mcts.py:Node.select` |
| Ten workers × 16 games, lock step | self-play | `metrics.json:config.workers = 10`, `games_per_gen = 160`; `selfplay.py:play_selfplay` |
| a quarter of moves get a full search; others a quarter of the simulations | playout-cap randomization | `selfplay.py: FULL_SEARCH_PROB = 0.25, FAST_SIMS_DIVISOR = 4` |
| eight board symmetries; AdamW; CE + MSE | training | `train.py:train_steps`, `go.py:apply_symmetry` |
| clipped to [0.02, 0.98] | chained Elo formula | `train.py:elo_from_winrate` |
| Intel Core i9-9980HK, 8 cores, 16 threads, no GPU | hardware | `sysctl machdep.cpu.brand_string hw.physicalcpu hw.logicalcpu` (2026-10-04) |
| every fourth generation (0,4,…,44); next two sampled generations and the final one | anchored design | `trainer/alphago_lite/anchored_eval.py` (`--step 4`) |
| first six moves sampled in proportion to visits | evaluation games | `selfplay.py:play_match(temp_moves=6)` |
| eleven 80-game checks | release checks | `data/strength.json` (11 entries, 80 games, 64 sims) |
| 95% Wilson intervals; 95% bootstrap intervals (1000 resamples) | statistics | `figures_scripts/common.py: wilson, bootstrap_bt(reps=1000)` |
| prior s.d. 1000 | Bradley–Terry prior | `figures_scripts/common.py: fit_bt(prior_sd=1000.0)` |
| generation 24 (first sampled generation scoring above zero after 8) | reading of Fig. 3b | `data/anchored.json` (a=24, b=44, wins_a=2) |
| GNU Go 3.8, Chinese rules, komi 7.5, --capture-all-dead | external engine | `gnugo --version`; `trainer/alphago_lite/gnugo_match.py:GTP` |
| best of three runs, one leaf per network call, one CPU thread | benchmark protocol | `bench/bench_python.py` (REPEATS = 3, torch threads 1), `MacApp/Sources/AlphaGoLiteBench/main.swift`, `bench/bench_browser.html` (numThreads = 1) |
| 64 simulations (evaluation), 32 (training log) | evaluation settings | `data/anchored.json:sims`, `metrics.json:config.eval_sims` |
| two hours stalled | engineering note | `trainer/runs_main.log` (no generation between 22:05 and 00:06, 2026-10-05/06); `algha_go_lite.md` changelog |
| AI-use statement | disclosure | this paper was drafted with Claude Code + paper-writer skill (author to confirm) |
