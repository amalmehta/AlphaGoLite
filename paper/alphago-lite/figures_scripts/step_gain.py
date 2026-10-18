"""Fig. 4: per-generation improvement measured three ways, as the newer generation's win rate
over one generation step, with 95% intervals."""
import math

import numpy as np

import common as c
import figure_style as fs



rows = []
gens = c.generations()
cons = c.anchored("consecutive")
lo_gen = min((r["a"] for r in cons), default=None)

# 1. training log: 40 games, 32 simulations, every consecutive pair
log = [g for g in gens if "winrate_vs_prev" in g]
w = sum(round(g["winrate_vs_prev"] * 40) for g in log)
n = 40 * len(log)
rows.append((f"Log, gens 1–{log[-1]['gen']}\n(32 sims)", w, n, 1))
if cons:
    sub = [g for g in log if g["gen"] > lo_gen]
    w = sum(round(g["winrate_vs_prev"] * 40) for g in sub)
    rows.append((f"Log, gens {lo_gen + 1}–{sub[-1]['gen']}\n(32 sims)", w, 40 * len(sub), 1))
    wc = sum(r["games"] - r["wins_a"] for r in cons)
    nc = sum(r["games"] for r in cons)
    rows.append((f"Replay, gens {lo_gen + 1}–{cons[-1]['b']}\n(64 sims)", wc, nc, 1))
if cons:
    late = [p for p in c.step4_pairs() if p[0] >= lo_gen]
    rows.append((f"Pairs 4 apart, gens {lo_gen}–{late[-1][1]}\n(64 sims), per gen.",
                 sum(p[2] for p in late), sum(p[3] for p in late), 4))
w4 = sum(p[2] for p in c.step4_pairs())
n4 = sum(p[3] for p in c.step4_pairs())
rows.append(("Pairs 4 apart, gens 0–44\n(64 sims), per gen.", w4, n4, 4))


to_step = c.to_step


fig, ax = fs.figure(c.VENUE, width="column", aspect=0.62)
for i, (label, w, n, k) in enumerate(rows):
    p = w / n
    lo, hi = c.wilson(w, n)
    y = 100 * to_step(p, k)
    ax.errorbar(y, i, xerr=[[y - 100 * to_step(lo, k)], [100 * to_step(hi, k) - y]],
                color=fs.PALETTE[i], marker=fs.MARKERS[i], capsize=2)
ax.axvline(50, color="0.6", lw=0.6, ls="--")
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows])
ax.invert_yaxis()
ax.set_xlabel("Newer generation's win % per generation step")
fs.save(fig, c.VENUE_DIR / "figures/step_gain.pdf")
