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
    a.plot(g, [x["elo"] for x in gens], color="#2f6fdb", lw=2)
    a.set_title("Chained Elo (each point from 40 games: noisy)")
    a.set_xlabel("Generation")
    t = [x for x in gens if "policy_loss" in x]
    b.plot([x["gen"] for x in t], [x["policy_loss"] for x in t], label="Policy loss", color="#2f6fdb", lw=2)
    b.plot([x["gen"] for x in t], [x["value_loss"] for x in t], label="Value loss", color="#e08a1e", lw=2)
    b.set_title("Training loss")
    b.set_xlabel("Generation")
    b.legend(frameon=False)
    for ax in (a, b):
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=0.25)
    checks = Path(args.run) / "strength.json"
    for c in (json.loads(checks.read_text()) if checks.exists() else []):
        a.annotate(f"gen {c['gen']} beats gen {c['vs']}: {c['wins']}/{c['games']}",
                   xy=(0.02, 0.92 - 0.08 * c["vs"] / 10), xycoords="axes fraction", fontsize=8, color="#444")
    fig.suptitle(f"AlphaGo Lite learning 9×9 Go from scratch — {games:,} self-play games, {hours:.1f} hours on one laptop CPU",
                 fontsize=11)
    fig.tight_layout()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
