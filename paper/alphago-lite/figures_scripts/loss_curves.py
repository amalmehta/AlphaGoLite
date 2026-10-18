"""Fig. 2: training losses per generation."""
import common as c
import figure_style as fs

gens = [g for g in c.generations() if "policy_loss" in g]
x = [g["gen"] for g in gens]
fig, (a, b) = fs.figure(c.VENUE, width="column", aspect=0.42, ncols=2)
a.plot(x, [g["policy_loss"] for g in gens], color=fs.PALETTE[0], marker=fs.MARKERS[0], markevery=4)
a.set_xlabel("Generation")
a.set_ylabel("Policy loss (nats)")
b.plot(x, [g["value_loss"] for g in gens], color=fs.PALETTE[1], marker=fs.MARKERS[1], markevery=4)
b.set_xlabel("Generation")
b.set_ylabel("Value loss (MSE)")
fs.save(fig, c.VENUE_DIR / "figures/loss_curves.pdf")
