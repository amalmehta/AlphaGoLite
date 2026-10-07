# System Design

AlphaGo Lite is the AlphaGo Zero / AlphaZero algorithm scaled down to 9×9 Go so it
can train on one laptop CPU. It has three parts:

- **Trainer** (Python, PyTorch): learns to play Go from nothing by self-play.
- **Mac app** (Swift, SwiftUI, Core ML): plays against you, shows what the engine is
  thinking, replays its self-play games and charts how training went.
- **Website** (`web/`, plain JavaScript, ONNX Runtime Web): the same features in the
  browser, deployed to GitHub Pages. The engine runs entirely on the visitor's machine.

## Architecture

```mermaid
flowchart LR
    subgraph Trainer["Trainer (trainer/alphago_lite)"]
        GO[go.py<br/>rules + features] --> MCTS[mcts.py<br/>batched PUCT search]
        NET[net.py<br/>policy/value ResNet] --> MCTS
        MCTS --> SP[selfplay.py<br/>self-play + eval matches]
        SP -->|positions, visit counts, results| DATA[(runs/main/data<br/>gen_NNNN.npz)]
        DATA --> TR[train.py<br/>training loop]
        TR -->|new weights| W[(runs/main/weights)]
        W --> SP
        TR --> MET[(metrics.json<br/>games/*.json)]
        W --> EXP[export_app.py]
        MET --> EXP
    end
    EXP -->|AlphaGoLite.mlpackage<br/>metrics.json, games.json| RES[(MacApp/Resources)]
    subgraph App["Mac app (MacApp/)"]
        RES --> BUILD[scripts/build_app.sh<br/>compiles model into .app]
        ENG[GoEngine library<br/>Go.swift, MCTS.swift,<br/>CoreMLEvaluator.swift] --> UI
        BUILD --> UI[AlphaGo Lite.app<br/>Play · AI vs AI · Training · Feedback]
    end
    GO -. test_vectors.json<br/>rule parity .-> ENG
    W --> EXW[export_web.py]
    MET --> EXW
    EXW -->|alphagolite.onnx<br/>metrics.json, games.json| WEB
    subgraph Web["Website (web/)"]
        WEB[(model/, data/)] --> WK[js/worker.js<br/>ONNX Runtime Web + mcts.js]
        GOJS[js/go.js<br/>rules] --> WK
        WK --> PAGE[index.html + js/app.js<br/>Play · AI vs AI · Training · Feedback]
    end
    GO -. test_vectors.json .-> GOJS
    PAGE -->|GitHub Actions| PAGES[GitHub Pages]
```

## Components

| Component | Job |
|---|---|
| `trainer/alphago_lite/go.py` | 9×9 rules: captures, simple ko, no suicide, Tromp-Taylor area scoring with komi 7.5, the 6 input planes, the 8 board symmetries. |
| `trainer/alphago_lite/net.py` | Residual network (4 blocks × 48 channels, ~190k parameters) with a policy head (82 move logits) and a value head (tanh, −1…1). |
| `trainer/alphago_lite/mcts.py` | PUCT tree search. Searches many trees in lock-step so every simulation evaluates one leaf per tree in a single network batch. |
| `trainer/alphago_lite/selfplay.py` | Self-play games (with Dirichlet noise, temperature for the first 10 moves, playout-cap randomization) and head-to-head evaluation matches. |
| `trainer/alphago_lite/train.py` | The loop: self-play → train → evaluate, one generation at a time, across a pool of worker processes. Resumable. If a self-play or evaluation step returns nothing within `--job-timeout` (40 min), it restarts the workers and retries, up to 3 times. |
| `trainer/alphago_lite/export_app.py` | Converts the latest weights to Core ML (and checks it matches PyTorch), copies the metrics and a selection of games for the app. |
| `trainer/alphago_lite/strength_check.py` | Plays one generation against earlier ones (80 games each) for an honest strength number. |
| `trainer/alphago_lite/plot_training.py` | Draws the README's training chart. |
| `trainer/alphago_lite/make_test_vectors.py` | Writes positions from random games so the Swift rules can be checked against the Python rules. |
| `MacApp/Sources/GoEngine` | Swift port of the rules and search, plus the Core ML evaluator. A separate library so it can be unit-tested. |
| `MacApp/Sources/AlphaGoLite` | The SwiftUI app: Play, AI vs AI, Training, Feedback. |
| `trainer/alphago_lite/export_web.py` | Exports the network to ONNX (checking it against PyTorch) plus the metrics and games for the website. |
| `web/js/go.js`, `web/js/mcts.js` | JavaScript ports of the rules and the search. Classic scripts, so they run in the page, in the worker and in Node (for tests). |
| `web/js/worker.js` | Web Worker that loads the ONNX network (ONNX Runtime Web, WebAssembly, from jsDelivr) and runs searches off the main thread. It keeps the search tree between moves. |
| `web/js/board.js` | Canvas board: the same drawing and overlays as the Mac app. |
| `web/js/app.js` | The page: Play, AI vs AI, Training (Chart.js) and the feedback tab. |
| `.github/workflows/pages.yml` | On a push that touches `web/`: runs the JS tests, then deploys `web/` to GitHub Pages. |
| `MacApp/scripts/build_app.sh` | Builds the release binary and assembles `AlphaGo Lite.app` (compiles the model, copies resources, writes Info.plist, ad-hoc signs). |

## Main flows

**Training a generation** (`train.py`)
1. Ten worker processes each play 16 self-play games with the previous generation's
   network. Only a quarter of moves get a full search (160 simulations); those become
   training samples. The rest get a fast search (40 simulations) and just move the game on.
2. The samples are saved to `data/gen_NNNN.npz`. The network trains on a sliding window of
   the most recent 250k samples, with random symmetries. Loss = cross-entropy against the
   search's visit distribution + squared error against the game result.
3. The new network plays 40 games against the previous one (32 simulations a move). The
   win rate becomes an Elo difference, added to a running total in `metrics.json`.

**Playing a move in the app** (`PlayModel` → `SearchWorker` → `MCTS`)
1. You click a point. The board accepts it only if it's legal and your turn.
2. `SearchWorker` runs MCTS on a background queue. It reuses the subtree from earlier
   searches, and each leaf is evaluated by the Core ML network.
3. Every 40 simulations a snapshot goes to the UI: the visit heat map, the top moves with
   their win rates and priors, the expected line, and the win bar.
4. When the search finishes, the most-visited move is played. If "Show the engine's
   thinking" is on, it then starts analysing your turn.
5. If you pass and the engine is already winning on the board as it stands, the engine
   passes too and the game is scored.

**Playing a move on the website** works the same way. `app.js` sends the position to
`worker.js` with `postMessage`. The worker searches using the ONNX network and posts
progress snapshots and the final result back. A new request cancels the old one, and
searches run one at a time so two never touch the tree together.

**AI vs AI**: replays games recorded during training, with the visit counts recorded for
each move, or plays a new game live with the trained network.

**Training view**: reads `metrics.json`, either the copy bundled in the app or a live
`runs/<name>` folder, which it re-reads every 20 s.

## Results of the bundled run

- 34 generations, 5,440 self-play games, 7.2 hours on an 8-core Intel i9, in two sittings:
  generations 1–19 (4.1 h, sharing the CPU with other apps), then generations 20–34
  (3 h, with the machine mostly free).
- Policy loss fell from 4.09 to 2.97. Value loss fell from 0.69 to about 0.55, then crept up to about 0.57.
- Head-to-head games with the network in the apps (generation 34), at 64 simulations a
  move, 80 games each:

  | Opponent | Generation 34 won |
  |---|---|
  | Generation 0 (random network + search) | 78/80 (97%) |
  | Generation 10 | 76/80 (95%) |
  | Generation 19 (the first release) | 79/80 (99%) |
  | Generation 25 (peak chained Elo) | 66/80 (82%) |
  | Generation 30 | 58/80 (72%) |

- Chained Elo peaked at generation 25 and then fell, but generation 34 beats 25 and 30
  head-to-head, so it is the best generation and the one shipped. Chained Elo adds up the noise from each 40-game match, so
  the dashboards lead with the head-to-head numbers, and the README chart shows only those.

## Where data lives

| Data | Location |
|---|---|
| Network weights per generation | `trainer/runs/main/weights/gen_NNNN.pt` (+ `optimizer.pt`) |
| Training samples | `trainer/runs/main/data/gen_NNNN.npz` (int8 planes, float policy, float result) |
| Metrics, sample games, head-to-head results | `trainer/runs/main/metrics.json`, `trainer/runs/main/games/gen_NNNN.json`, `trainer/runs/main/strength.json` |
| What the app ships with | `MacApp/Resources/` → copied into `AlphaGo Lite.app/Contents/Resources/` (model compiled to `.mlmodelc`) |
| Feedback (Mac app) | `~/Library/Application Support/AlphaGo Lite/feedback.jsonl` (local only) |
| Feedback (website) | GitHub issues on the AlphaGoLite repo (the feedback tab opens a pre-filled issue) |
| What the website ships with | `web/model/alphagolite.onnx`, `web/data/metrics.json`, `web/data/games.json` |

`trainer/runs/` is not committed (too large). `MacApp/Resources/` is committed, so the app
builds without retraining.

## Key decisions and trade-offs

- **9×9 instead of 19×19.** The real AlphaGo Zero used about 5,000 TPUs. A 9×9 board is
  small enough to learn on one CPU in hours, and the algorithm is the same.
- **Small network (4×48).** On this Intel CPU, a 6×64 network took about 1.8 ms per
  position and a 4×48 one about 0.85 ms. That halves self-play time and costs some
  strength. The app could carry a bigger network, but it would need training time we
  don't have.
- **Batched lock-step MCTS in Python.** Running 16 games per worker gives the network
  useful batch sizes without the complexity of virtual loss or threads. The rule and
  tree code stays in readable Python; the cost is Python overhead (~20–30% of self-play
  time).
- **Playout-cap randomization (from KataGo).** Fast searches on most moves give roughly
  2× more games per hour for value training, and the policy targets still come from full
  searches.
- **Chained Elo plus separate head-to-head checks.** Measuring each generation against
  the one before it is cheap, but 40 games per step is noisy and the errors add up. The
  larger 80-game head-to-head checks against older generations give the trustworthy
  number.
- **Tromp-Taylor scoring.** Simple and unambiguous, so it's easy to make the Python and
  Swift rules agree exactly. But every stone on the board counts as alive, so players
  must capture dead stones before passing. The app says so.
- **Simple ko only** (no superko). Long cycles like triple ko are possible but very
  rare; the 162-move cap ends any such game.
- **Core ML on the CPU in the app.** For a network this small, one inference on the CPU
  is well under a millisecond, faster than a round trip to the GPU. The search runs one
  leaf at a time, which keeps the Swift MCTS simple.
- **ONNX Runtime Web for the website**, rather than a hand-written JavaScript network:
  WebAssembly is several times faster, at the cost of one CDN dependency (~10 MB of
  WebAssembly on first load). It runs single-threaded, because GitHub Pages can't send
  the cross-origin isolation headers that threads need. 400 simulations take about a
  second on this Intel Mac.
- **Plain JavaScript, no build step.** The site is static files that Pages serves
  directly. The rules and search are classic scripts so Node can test them unchanged.
- **Website feedback goes to GitHub issues**, since a static site has nowhere to store
  it. The visitor reviews and submits the pre-filled issue themselves, which needs a
  GitHub account.
- **A worker pool that heals itself.** `multiprocessing.Pool` replaces a worker that
  dies but silently loses its job, so the trainer could wait forever. This happened once,
  on an overloaded machine, and wasted 2 hours. Each pool call now has a timeout and is
  retried on fresh workers. The cost: a genuinely hung step wastes up to one timeout.
- **Swift Package + build script instead of an Xcode project.** Plain text, easy to
  diff, builds with `swift build`; the script assembles a real `.app`.

## Testing

- `trainer/tests/test_go.py` (pytest): captures, suicide, ko, scoring, two-pass ending,
  symmetry round-trip, and search finding a capture.
- `MacApp/Tests/GoEngineTests` (`swift test`):
  - **Rule parity**: replays 433 positions from random Python games and checks the
    board, ko point, legal moves, score and input planes match exactly.
  - Ko and capture, search finding a capture, pass and game end.
- `web/tests/run_tests.js` (`node web/tests/run_tests.js`, also run by the deploy workflow):
  the same 433-position rule parity check, ko, the winning-pass search, and tree reuse.
- `export_web.py` compares ONNX and PyTorch outputs (max difference about 6e-6). Checked
  in the browser: the website's search gives the same candidate moves, visit counts and
  replies as the Mac app for the same position.
- `export_app.py` compares Core ML and PyTorch outputs on random boards every time it
  exports. The max difference was about 1e-7.
- Training health is in the dashboard: loss curves, win rate against the previous
  generation, game length, and head-to-head checks.
- The website was checked in a browser:
  - Play: moves, engine replies and the thinking overlay.
  - AI vs AI: replay with the arrow keys, and a live game (43 moves in 8 s at Quick).
  - Training charts.
  - Feedback: the issue URL is built correctly.
  - Phone width (375 px): no sideways scrolling.
- The app was checked by hand with the final network:
  - Play: moves, engine replies, and the thinking overlay. The engine found a capture in a real game.
  - AI vs AI: replays and a live game.
  - Training charts.
  - Feedback: saved to the local file.

## Known limits

- Strength is that of a few hours of CPU training: it plays reasonable shapes and
  captures, but is far below a strong 9×9 engine (KataGo) or a dan player.
- Elo is chained and noisy; use the head-to-head checks instead.
- Training time was short (7 hours on one CPU). The network is clearly better than its
  earlier generations, but its strength against people is unmeasured. Expect a capable
  beginner, not a strong player.
- No superko, no handicap, no time controls, no SGF import or export.
- The app's search is single-threaded with batch size 1.
- Tromp-Taylor scoring doesn't remove dead stones.
- The website needs internet access for ONNX Runtime Web (jsDelivr) and Chart.js (cdnjs).
  Search is single-threaded and evaluates one position at a time.
- Website feedback needs a GitHub account.
