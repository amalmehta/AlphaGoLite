# Instructions

## Requirements

- macOS 14 or later, with Xcode (or the Command Line Tools) for `swift` and `xcrun coremlcompiler`.
- For the website: any modern browser. Node 18+ for its tests.
- To retrain: [uv](https://docs.astral.sh/uv/) (or any Python 3.11) and about 3–4 hours of CPU time.

## Run the Mac app

The repo ships with a trained network, so you can build and play straight away:

```bash
MacApp/scripts/build_app.sh --open
```

This builds `MacApp/build/AlphaGo Lite.app` and opens it. Copy it to `/Applications` if you want to keep it.

## Use the website

Open https://amalmehta.github.io/AlphaGoLite/. It has the same Play, AI vs AI and Training tabs as the Mac app, and the engine runs in your browser. The first load downloads about 10 MB of engine code.

To run it locally:

```bash
python3 -m http.server 8765 --directory web
```

Then open http://localhost:8765. Opening the file directly doesn't work, because the Web Worker and `fetch` need a server.

The **Feedback** button (bottom right) opens a pre-filled GitHub issue; you submit it yourself.

## Using the app

**Play**
- Click an empty point to play. You're Black by default. To play White, use **New Game › Play as White**.
- **Pass**, **Undo** (⌘Z) and **Resign** are in the toolbar.
- **Strength** sets how many simulations the engine runs per move: Quick 100, Normal 400, Strong 1,200, Maximum 3,000.
- **Show the engine's thinking** controls the overlay:
  - Blue circles: how much the search looked at each point. The brightest is the engine's choice.
  - White numbers: the engine's win % for that move.
  - Faint numbered stones: the line the engine expects next.
  - Side panel: candidate moves with visits, win % and prior (the network's first guess), the win bar, and a win-probability chart for the whole game.
- Scoring is by area (Tromp-Taylor), with komi 7.5. Every stone on the board counts as alive, so capture dead stones before you pass. At the end, small squares mark each side's territory.

**AI vs AI**
- Pick a self-play game recorded during training to see how play changed from early generations to late ones. Use ←/→ to step, Space to play or pause, or drag the slider. The blue heat map shows the search that chose each move.
- **Live game**: choose a strength and click **Start a new game** to watch the trained network play itself.

**Training**
- Charts for the bundled run: head-to-head results of the network in the app against earlier generations, chained Elo, policy and value loss, win rate against the previous generation, and game length.
- **Open Training Run…** (toolbar): choose a `trainer/runs/<name>` folder to watch a run that's still training. It refreshes every 20 seconds.

**Feedback**: click the small **Feedback** link at the bottom of the sidebar. Entries are saved only on this Mac, in `~/Library/Application Support/AlphaGo Lite/feedback.jsonl`.

## Train your own network

```bash
cd trainer
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m alphago_lite.train --run runs/main --hours 4
```

- Progress is printed one line per generation and written to `runs/main/metrics.json`. Watch it live in the app with **Training › Open Training Run…**.
- Training resumes from the last finished generation if you run the same command again.
- Useful flags: `--games-per-gen`, `--sims`, `--workers` (default 10, one process per core), `--eval-games`, `--max-gens`.

Measure real strength with head-to-head games (results go to `runs/main/strength.json` and appear in the app's Training view):

```bash
cd trainer
.venv/bin/python -m alphago_lite.strength_check --run runs/main --gen 19 --vs 0 10
```

Export the result into the app, then rebuild:

```bash
cd trainer
.venv/bin/python -m alphago_lite.export_app --run runs/main --out ../MacApp/Resources
../MacApp/scripts/build_app.sh --open
```

To export a specific generation, add `--gen N`.

Export the same run for the website. A push to `main` that touches `web/` redeploys the site.

```bash
cd trainer
.venv/bin/python -m alphago_lite.export_web --run runs/main --out ../web
```

## Tests

```bash
cd trainer
.venv/bin/python -m pytest -q tests
```

```bash
cd MacApp
swift test
```

```bash
node web/tests/run_tests.js
```

If you change the rules, regenerate the parity vectors that keep Python and Swift in step:

```bash
cd trainer
.venv/bin/python -m alphago_lite.make_test_vectors --out ../MacApp/Tests/GoEngineTests/test_vectors.json
```

## Regenerate the app icon

```bash
cd MacApp
swift scripts/make_icon.swift
```
