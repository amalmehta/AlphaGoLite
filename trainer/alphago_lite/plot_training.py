"""Draw the README's training chart from a run's metrics.json.

    python -m alphago_lite.plot_training --run runs/main --out ../docs/images/training.png

Whole history (gens 0-44 from runs/main, 45 on from runs/v2, as on the website),
with the GNU Go result as an extra bar, at the portfolio's 1200x392:

    python -m alphago_lite.plot_training --metrics ../web/data/metrics.json \
        --gnugo runs/v2/gnugo.json --mark 44 --px 1200x392 --out ../docs/images/training-107.png
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
    ap.add_argument("--metrics", help="metrics.json with its own strength_checks (e.g. web/data/metrics.json)")
    ap.add_argument("--gnugo", help="gnugo.json; adds the final generation's GNU Go result as a bar")
    ap.add_argument("--mark", type=int, help="draw a line after this generation (where training settings changed)")
    ap.add_argument("--px", help="output size in pixels, e.g. 1200x392 (same layout, scaled)")
    args = ap.parse_args()
    metrics = json.loads((Path(args.metrics) if args.metrics else Path(args.run) / "metrics.json").read_text())
    gens = metrics["generations"]
    g = [x["gen"] for x in gens]
    hours = gens[-1]["elapsed_min"] / 60
    games = gens[-1]["total_games"]

    if args.px:
        w, h = (int(v) for v in args.px.split("x"))
        fig, (a, b) = plt.subplots(1, 2, figsize=(11, 11 * h / w), dpi=w / 11)
    else:
        fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.6), dpi=150)
    if args.metrics:
        checks = metrics.get("strength_checks", [])
    else:
        path = Path(args.run) / "strength.json"
        checks = json.loads(path.read_text()) if path.exists() else []
    final = sorted((c for c in checks if c["gen"] == g[-1]), key=lambda c: c["vs"])
    labels = [f"vs. generation {c['vs']}" for c in final]
    if args.gnugo:
        for m in json.loads(Path(args.gnugo).read_text())["matches"]:
            if m["gen"] == g[-1]:
                won = sum(x["ours_won"] for x in m["games"])
                final.append({"wins": won, "games": len(m["games"])})
                labels.append(f"vs. GNU Go level {m['level']}")
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
    if args.mark is not None:
        b.axvline(args.mark + 0.5, color="#999", lw=1, ls="--")
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
