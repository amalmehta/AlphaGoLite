# File Structure

```
AlphaGoLite/
├── README.md                     what it is, screenshots, links
├── algha_go_lite.md              the project brief
├── docs/
│   ├── INSTRUCTIONS.md           setup, run, use, retrain, test
│   ├── SYSTEM-DESIGN.md          architecture, flows, decisions, limits
│   ├── FILE-STRUCTURE.md         this file
│   └── images/                   screenshots and the training chart used in the README
├── .github/workflows/pages.yml   tests + deploys web/ to GitHub Pages
├── web/                          the website (static, no build step)
│   ├── index.html                page layout: Play, AI vs AI, Training, feedback dialog
│   ├── style.css                 light/dark theme, phone layout
│   ├── icon.png
│   ├── js/
│   │   ├── go.js                 rules (port of go.py / Go.swift)
│   │   ├── mcts.js               tree search (port of mcts.py / MCTS.swift)
│   │   ├── worker.js             Web Worker: ONNX network + search
│   │   ├── board.js              canvas board drawing
│   │   └── app.js                the three tabs and the feedback tab
│   ├── model/alphagolite.onnx    the trained network
│   ├── data/                     metrics.json, games.json
│   └── tests/run_tests.js        Node tests (rule parity, search)
├── trainer/                      Python: learns Go by self-play
│   ├── requirements.txt
│   ├── alphago_lite/
│   │   ├── go.py                 rules, scoring, input planes, symmetries
│   │   ├── net.py                policy/value residual network
│   │   ├── mcts.py               batched PUCT tree search
│   │   ├── selfplay.py           self-play games and evaluation matches
│   │   ├── train.py              the training loop (entry point)
│   │   ├── export_app.py         Core ML export + metrics/games for the app
│   │   ├── export_web.py         ONNX export + metrics/games for the website
│   │   ├── strength_check.py     head-to-head games: one generation vs earlier ones
│   │   ├── make_test_vectors.py  rule-parity vectors for the Swift tests
│   │   └── plot_training.py      draws docs/images/training.png from metrics.json
│   ├── tests/test_go.py          pytest suite
│   └── runs/                     (not committed) weights, samples, metrics per run
└── MacApp/                       Swift: the AlphaGo Lite Mac app
    ├── Package.swift
    ├── VERSION
    ├── Resources/                what the app ships with
    │   ├── AlphaGoLite.mlpackage the trained network
    │   ├── metrics.json          training history (Training view)
    │   ├── games.json            recorded self-play games (AI vs AI view)
    │   └── AppIcon.icns
    ├── Sources/
    │   ├── GoEngine/             library: rules, MCTS, Core ML evaluator
    │   │   ├── Go.swift
    │   │   ├── MCTS.swift
    │   │   └── CoreMLEvaluator.swift
    │   └── AlphaGoLite/          the SwiftUI app
    │       ├── AlphaGoLiteApp.swift   window, sidebar, feedback link
    │       ├── Engine.swift           resource lookup, background search worker
    │       ├── BoardView.swift        board drawing, overlays, win bar
    │       ├── PlayView.swift         play against the engine + thinking panel
    │       ├── WatchView.swift        AI vs AI replays and live games
    │       ├── TrainingView.swift     training charts
    │       ├── TrainingData.swift     metrics.json / games.json models
    │       └── FeedbackView.swift     feedback form
    ├── Tests/GoEngineTests/      parity + engine tests (swift test)
    ├── scripts/
    │   ├── build_app.sh          builds build/AlphaGo Lite.app
    │   └── make_icon.swift       draws Resources/AppIcon.icns
    └── build/                    (not committed) the built .app
```
