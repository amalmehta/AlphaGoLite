"""Fig. 3: what chained Elo says vs. what anchored games say."""
import common as c
import figure_style as fs

gens = c.generations()
last = gens[-1]["gen"]
fig, (a, b, d) = fs.figure(c.VENUE, width="text", aspect=0.27, ncols=3)

# (a) chained Elo from the training log
a.plot([g["gen"] for g in gens], [g["elo"] for g in gens], color=fs.PALETTE[0], marker=".", markersize=3)
chained = {g["gen"]: g["elo"] for g in gens}
for g, off in ((19, (0, -16)), (25, (11, -3)), (34, (0, -16))):
    a.annotate(f"gen {g}", (g, chained[g]), xytext=off, textcoords="offset points", ha="center",
               va="center", arrowprops=dict(arrowstyle="-", lw=0.5, color="0.4", shrinkA=0, shrinkB=2), fontsize=6.5)
a.set_ylim(top=max(chained.values()) + 80)
a.set_xlabel("Generation")
a.set_ylabel("Chained Elo")
a.set_title("(a) Chained Elo (training log)", loc="left")

# (b) score of every 4th generation against the last one, with 95% Wilson intervals
pts = sorted((r["a"], r["wins_a"], r["games"]) for r in c.anchored() if r["b"] == last)
xs = [p[0] for p in pts]
ps = [p[1] / p[2] for p in pts]
lo = [p - c.wilson(w, n)[0] for p, (_, w, n) in zip(ps, pts)]
hi = [c.wilson(w, n)[1] - p for p, (_, w, n) in zip(ps, pts)]
b.errorbar(xs, [100 * p for p in ps], yerr=[[100 * v for v in lo], [100 * v for v in hi]],
           color=fs.PALETTE[2], marker=fs.MARKERS[2], capsize=1.5, lw=1)
b.set_xlabel("Generation")
b.set_ylabel(f"Win % vs. generation {last}")
b.set_ylim(-3, 60)
b.set_title(f"(b) Score against generation {last}", loc="left")

# (c) Bradley-Terry ratings from all 64-simulation games, 95% bootstrap intervals
m = c.h2h_matches()
r = c.fit_bt(m)
ci = c.bootstrap_bt(m)
gs = sorted(r)
d.errorbar(gs, [r[g] for g in gs], yerr=[[r[g] - ci[g][0] for g in gs], [ci[g][1] - r[g] for g in gs]],
           color=fs.PALETTE[3], marker=fs.MARKERS[3], ls="none", capsize=1.5, lw=1)
d.set_xlabel("Generation")
d.set_ylabel("Fitted Elo (gen. 0 = 0)")
d.set_title("(c) Bradley–Terry fit", loc="left")
fs.save(fig, c.VENUE_DIR / "figures/elo_comparison.pdf")
