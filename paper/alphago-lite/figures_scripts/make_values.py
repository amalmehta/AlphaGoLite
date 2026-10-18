"""Write <venue>/generated/values.tex (one \\newcommand per number used in the text) and the
generated block of <venue>/sources.md (one row per macro: value, meaning, file, computation)."""
import json
import math
import re

import numpy as np

import common as c

rows = []


def val(name, value, meaning, source):
    rows.append((name, value, meaning, source))


gens = c.generations()
last = gens[-1]
chained = {g["gen"]: g["elo"] for g in gens}
with_loss = [g for g in gens if "policy_loss" in g]
config = c.load("metrics.json")["config"]

val("NGens", str(last["gen"]), "generations trained", "metrics.json: generations[-1].gen")
val("TotalGames", f"{last['total_games']:,}", "self-play games", "metrics.json: generations[-1].total_games")
val("WallHours", f"{last['elapsed_min'] / 60:.1f}", "wall-clock hours of training", "metrics.json: generations[-1].elapsed_min / 60")
val("GamesPerGen", str(config["games_per_gen"]), "self-play games per generation", "metrics.json: config.games_per_gen")
val("PolicyLossFirst", f"{with_loss[0]['policy_loss']:.2f}", "policy loss, generation 1", "metrics.json: generations[1].policy_loss")
val("PolicyLossLast", f"{with_loss[-1]['policy_loss']:.2f}", "policy loss, last generation", "metrics.json: generations[-1].policy_loss")
val("ValueLossFirst", f"{with_loss[0]['value_loss']:.2f}", "value loss, generation 1", "metrics.json: generations[1].value_loss")
val("ValueLossLast", f"{with_loss[-1]['value_loss']:.2f}", "value loss, last generation", "metrics.json: generations[-1].value_loss")
sp = [g["selfplay_sec"] for g in with_loss]
val("SelfplayMin", f"{min(sp):,.0f}", "fastest self-play phase of a generation (s)", "metrics.json: min selfplay_sec")
val("SelfplayMax", f"{max(sp):,.0f}", "slowest self-play phase of a generation (s)", "metrics.json: max selfplay_sec")

peak_gen = max(chained, key=chained.get)
val("ChainedFinal", f"{chained[last['gen']]:+.0f}", "chained Elo of the last generation", "metrics.json: generations[-1].elo")
val("ChainedPeak", f"{chained[peak_gen]:+.0f}", "highest chained Elo", "metrics.json: max elo")
val("ChainedPeakGen", str(peak_gen), "generation with the highest chained Elo", "metrics.json: argmax elo")
for g in (19, 25, 34):
    val(f"Chained{['Nineteen','TwentyFive','ThirtyFour'][[19,25,34].index(g)]}", f"{chained[g]:+.0f}",
        f"chained Elo of generation {g}", f"metrics.json: generations[{g}].elo")
val("Inversion", f"{chained[25] - chained[34]:.0f}", "chained Elo of generation 25 minus generation 34",
    "metrics.json: elo[25] - elo[34]")
wr = [g["winrate_vs_prev"] for g in with_loss]
val("MeanWrPrev", f"{np.mean(wr):.3f}", "mean win rate vs previous generation (32 sims, 40 games)", "metrics.json: mean winrate_vs_prev")
val("MeanWrPrevSE", f"{np.std(wr) / math.sqrt(len(wr)):.3f}", "standard error of that mean", "metrics.json: std(winrate_vs_prev)/sqrt(n)")
val("EvalGames", str(config["eval_games"]), "games per chained step", "metrics.json: config.eval_games")
val("EvalSims", str(config["eval_sims"]), "simulations per move in chained steps", "metrics.json: config.eval_sims")
val("StepSE", f"{c.chained_step_se(config['eval_games']):.0f}", "SE (Elo) of one 40-game step at p = 0.5", "common.chained_step_se(40)")
val("WalkSD", f"{c.chained_step_se(config['eval_games']) * math.sqrt(last['gen']):.0f}",
    "SD (Elo) of a chained sum after all generations from noise alone", "chained_step_se(40) * sqrt(44)")

checks = {(m["gen"], m["vs"]): m for m in c.load("strength.json")}
for (a, b), name in {(34, 25): "TtfVsTf", (34, 19): "TtfVsNt", (44, 34): "FfVsTtf", (44, 39): "FfVsTn",
                     (44, 0): "FfVsZero", (44, 19): "FfVsNt"}.items():
    m = checks[(a, b)]
    val(f"H{name}", f"{m['wins']}/{m['games']}", f"generation {a} wins vs generation {b} (64 sims)", f"strength.json: gen={a}, vs={b}")

anc = c.anchored()
val("AnchoredPairs", str(len(anc)), "anchored pairs played", "anchored.json: len(results)")
val("AnchoredGames", f"{sum(r['games'] for r in anc):,}", "games in anchored pairs", "anchored.json: sum games")
val("AnchoredSims", str(c.load("anchored.json")["sims"]), "simulations per move in anchored games", "anchored.json: sims")
m_all = c.h2h_matches()
val("HtoHGames", f"{sum(x[3] for x in m_all):,}", "all 64-sim head-to-head games", "anchored.json + strength.json")
vs_last = sorted((r["a"], r["wins_a"], r["games"]) for r in anc if r["b"] == last["gen"])
val("AnchorScores", ", ".join(str(w) for _, w, _ in vs_last), "wins vs the last generation, every 4th generation in order",
    "anchored.json: b=44, wins_a by a")
w4, n4, step_elo = c.per_step_elo_from_step4()
val("StepFourWr", f"{w4 / n4:.3f}", "pooled win rate of the later generation over pairs 4 apart", "anchored.json: b-a=4")
val("StepElo", f"{step_elo:.0f}", "implied Elo gain per generation from pairs 4 apart", "common.per_step_elo_from_step4")
val("StepWr", f"{1 / (1 + 10 ** (-step_elo / 400)):.3f}", "implied per-generation win rate", "from StepElo")
lo4, hi4 = c.wilson(w4, n4)
val("StepWrLo", f"{c.to_step(lo4, 4):.3f}", "95% lower bound of that per-generation rate", "Wilson bound on pooled 4-apart rate, converted with common.to_step")
val("StepWrHi", f"{c.to_step(hi4, 4):.3f}", "95% upper bound", "same")
def sci(x):
    """LaTeX-ready scientific notation, e.g. 3\\times10^{-5}."""
    m, e = f"{x:.0e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


val("PMisorderOne", f"{c.p_misorder(1, step_elo, config['eval_games']):.2f}",
    "chance a 40-game chained step shows a decline, if each generation gains StepElo", "common.p_misorder(1, StepElo, 40)")
val("PMisorderNine", sci(c.p_misorder(9, step_elo, config['eval_games'])),
    "chance noise alone makes chained Elo rank g+9 below g (40-game steps)", "common.p_misorder(9, StepElo, 40)")

ratings = c.fit_bt(m_all)
dev = sum(((w - n / (1 + math.exp(-c.K * (ratings[a] - ratings[b])))) ** 2) /
          (n * (p := 1 / (1 + math.exp(-c.K * (ratings[a] - ratings[b])))) * (1 - p) + 1e-9) for a, b, w, n in m_all)
val("BTChiSq", f"{dev:.0f}", "Pearson chi-square of the Bradley-Terry fit", "common.fit_bt on all 64-sim matches")
val("BTMatches", str(len(m_all)), "matches in the Bradley-Terry fit", "anchored.json + strength.json")
val("BTFree", str(len(ratings) - 1), "free ratings in the fit", "common.fit_bt")

cons = c.anchored("consecutive")
if cons:
    wcons = sum(r["games"] - r["wins_a"] for r in cons)
    ncons = sum(r["games"] for r in cons)
    log32 = [g["winrate_vs_prev"] for g in gens if g["gen"] in {r["b"] for r in cons}]
    val("ConsPairs", str(len(cons)), "consecutive pairs replayed at 64 sims", "consecutive.json")
    val("ConsFrom", str(min(r["a"] for r in cons)), "first generation of the replay", "consecutive.json")
    val("ConsWr", f"{wcons / ncons:.3f}", "pooled win rate of the newer generation, 64 sims", "consecutive.json")
    val("ConsWrLo", f"{c.wilson(wcons, ncons)[0]:.3f}", "95% Wilson lower bound", "consecutive.json")
    val("ConsWrHi", f"{c.wilson(wcons, ncons)[1]:.3f}", "95% Wilson upper bound", "consecutive.json")
    val("ConsWrLog", f"{np.mean(log32):.3f}", "same pairs in the training log (32 sims)", "metrics.json: winrate_vs_prev for those generations")
    first = min(r["a"] for r in cons)
    late = [q for q in c.step4_pairs() if q[0] >= first]
    wl, nl = sum(q[2] for q in late), sum(q[3] for q in late)
    late_elo = -400 * math.log10(nl / wl - 1) / 4
    val("LateStepWr", f"{c.to_step(wl / nl, 4):.3f}", f"per-generation rate from 4-apart pairs within gens {first}-{last['gen']}",
        "anchored.json: b-a=4, a>=first replayed generation; common.to_step")
    val("LateStepWrLo", f"{c.to_step(c.wilson(wl, nl)[0], 4):.3f}", "95% lower bound", "Wilson, common.to_step")
    val("LateStepWrHi", f"{c.to_step(c.wilson(wl, nl)[1], 4):.3f}", "95% upper bound", "Wilson, common.to_step")
    val("LateStepElo", f"{late_elo:.0f}", "implied Elo per generation in that range", "from LateStepWr")
    byp = {(r["a"], r["b"]): r for r in cons}
    rep = sum(c.elo_from_winrate((byp[(g, g + 1)]["games"] - byp[(g, g + 1)]["wins_a"]) / byp[(g, g + 1)]["games"])
              for g in range(25, 34))
    val("ReplayChain", f"{rep:+.0f}", "chained Elo from gen 25 to 34 using the 64-sim replay", "consecutive.json, train.py Elo formula")
    val("HtoHEloTtfTf", f"{c.elo_from_winrate(checks[(34, 25)]['wins'] / checks[(34, 25)]['games']):+.0f}",
        "Elo difference implied by gen 34 vs gen 25 head-to-head", "strength.json: 66/80 -> Elo")
    expect = 9 * late_elo
    sd = c.chained_step_se(config["eval_games"]) * 3
    val("DropZ", f"{(-(chained[25] - chained[34]) - expect) / sd:.1f}",
        "log's 25->34 chained change, in SDs below what LateStepElo predicts", "(elo[34]-elo[25] - 9*LateStepElo) / (StepSE*sqrt(9))")
    val("DropExpect", f"{expect:+.0f}", "expected chained change from 25 to 34 under LateStepElo", "9 * LateStepElo")
    replay_all = sum(c.elo_from_winrate((r["games"] - r["wins_a"]) / r["games"]) for r in cons)
    val("ReplayChainAll", f"{replay_all:+.0f}", f"replay chained Elo over gens {first}-{last['gen']}", "consecutive.json")
    val("LogChainAll", f"{chained[last['gen']] - chained[first]:+.0f}", "log chained Elo over the same gens", "metrics.json")
else:
    for name in ("ConsPairs", "ConsFrom", "ConsWr", "ConsWrLo", "ConsWrHi", "ConsWrLog"):
        val(name, "\\TODO{consecutive replay still running}", "pending: consecutive.json not in data/ yet", "consecutive.json")

gg = c.load("gnugo.json")["matches"][0]
val("GnuWins", f"{gg['wins']}/{gg['decided']}", "wins vs GNU Go", "gnugo.json")
val("GnuSims", str(gg["sims"]), "our simulations per move vs GNU Go", "gnugo.json")
val("GnuLevel", str(gg["level"]), "GNU Go level", "gnugo.json")
margins = [abs(g["our_score_black"]) for g in gg["games"]]
val("GnuMedianMargin", f"{np.median(margins):.1f}", "median losing margin vs GNU Go (points)", "gnugo.json: median |our_score_black|")
agree = sum(g["gnugo_final_score"].startswith("W+" if g["our_score_black"] < 0 else "B+") for g in gg["games"])
val("GnuScoreAgree", f"{agree}/{len(gg['games'])}", "games where GNU Go's own final_score names the same winner as ours",
    "gnugo.json: gnugo_final_score prefix vs sign of our_score_black")

par = json.loads((c.BENCH / "export_parity.json").read_text())
val("RuleCases", str(par["rule_parity_cases"]), "rule-parity positions", "bench/export_parity.json")
val("RuleGames", str(par["rule_parity_games"]), "random games the positions come from", "bench/export_parity.json")
val("CoreMLDiff", f"{par['coreml_max_abs_diff'] * 1e6:.1f}", "max |Core ML - PyTorch| (x1e-6)", "bench/export_parity.json")
val("OnnxDiff", f"{par['onnx_max_abs_diff'] * 1e6:.1f}", "max |ONNX - PyTorch| (x1e-6)", "bench/export_parity.json")

import torch  # noqa: E402  (parameter count from the real network)
import sys  # noqa: E402
sys.path.insert(0, str(c.HERE.parents[2] / "trainer"))
from alphago_lite.net import PolicyValueNet  # noqa: E402
val("NParams", f"{sum(p.numel() for p in PolicyValueNet().parameters()):,}", "network parameters", "trainer/alphago_lite/net.py (counted)")

bench = {k: json.loads((c.BENCH / f"result_{k}.json").read_text()) for k in ("python", "swift", "browser")}
val("BenchPositions", str(len(bench["python"]["cases"])), "benchmark positions", "bench/result_python.json")
val("BenchSims", str(bench["python"]["sims"]), "simulations per benchmark search", "bench/result_python.json")
same = all(bench[k]["cases"][i]["visits"] == bench["python"]["cases"][i]["visits"]
           for k in ("swift", "browser") for i in range(len(bench["python"]["cases"])))
val("BenchIdentical", "all" if same else "\\TODO{not all}", "positions with identical root visits on all platforms", "bench/result_*.json")

tex = ["% generated by figures_scripts/make_values.py — do not edit"]
# typeset leading minus signs as a true minus (math mode), not a hyphen
rows = [(n, re.sub(r"^-(?=\d)", "$-$", v) if isinstance(v, str) else v, m, s_) for n, v, m, s_ in rows]
for name, value, _, _ in rows:
    tex.append(f"\\newcommand{{\\val{name}}}{{{value}}}")
c.write("generated/values.tex", "\n".join(tex) + "\n")

src = c.VENUE_DIR / "sources.md"
table = ["<!-- BEGIN GENERATED (make_values.py) -->", "| Macro | Value | Meaning | Source / computation |", "|---|---|---|---|"]
table += [f"| `\\val{n}` | {v} | {m} | {s} |" for n, v, m, s in rows]
table.append("<!-- END GENERATED -->")
old = src.read_text() if src.exists() else "# Sources\n\n<!-- BEGIN GENERATED (make_values.py) -->\n<!-- END GENERATED -->\n"
new = re.sub(r"<!-- BEGIN GENERATED.*?<!-- END GENERATED -->", lambda _: "\n".join(table), old, flags=re.S)
src.write_text(new)
print(f"wrote {len(rows)} values")
