"""Draw the README's training chart from a run's metrics.json.

    python -m alphago_lite.plot_training --run runs/main --out ../docs/images/training.png
"""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="runs/main")
    ap.add_argument("--out", default="../docs/images/training.png")
    args = ap.parse_args()
    gens = json.loads((Path(args.run) / "metrics.json").read_text())["generations"]
    g = [x["gen"] for x in gens]
    hours = gens[-1]["elapsed_min"] / 60
    games = gens[-1]["total_games"]

    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.6), dpi=150)
    checks = Path(args.run) / "strength.json"
    final = sorted((c for c in (json.loads(checks.read_text()) if checks.exists() else []) if c["gen"] == g[-1]),
                   key=lambda c: c["vs"])
    labels = [f"vs. generation {c['vs']}" for c in final]
    rates = [100 * c["wins"] / c["games"] for c in final]
    a.barh(labels, rates, color="#2f6fdb")
    for i, c in enumerate(final):
        a.text(rates[i] - 2, i, f"{c['wins']}/{c['games']} games", va="center", ha="right", color="white", fontsize=9)
    a.axvline(50, color="#999", lw=1, ls="--")
    a.set_xlim(0, 100)
    a.invert_yaxis()
    a.set_xlabel("Win %")
    a.set_title(f"Generation {g[-1]} vs. earlier generations (head-to-head)")
    t = [x for x in gens if "policy_loss" in x]
    b.plot([x["gen"] for x in t], [x["policy_loss"] for x in t], label="Policy loss", color="#2f6fdb", lw=2)
    b.plot([x["gen"] for x in t], [x["value_loss"] for x in t], label="Value loss", color="#e08a1e", lw=2)
    b.set_title("Training loss")
    b.set_xlabel("Generation")
    b.legend(frameon=False)
    b.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=0.25)
    fig.suptitle(f"AlphaGo Lite learning 9×9 Go from scratch — {games:,} self-play games, {hours:.1f} hours on one laptop CPU",
                 fontsize=11)
    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
