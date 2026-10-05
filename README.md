# AlphaGo Lite

A Mac app that plays 9×9 Go using the AlphaGo Zero algorithm. It taught itself from scratch through self-play on one laptop, and it shows you what it's thinking as it plays.

![Playing against AlphaGo Lite, with its search shown on the board](docs/images/play.png)

| Watch it play itself | See how it learned |
|---|---|
| ![AI vs AI replay](docs/images/watch.png) | ![Training dashboard](docs/images/training-view.png) |

![Training progress](docs/images/training.png)

```mermaid
flowchart LR
    A[Self-play<br/>MCTS + network] -->|games| B[Train<br/>policy + value]
    B -->|new network| C[Evaluate<br/>vs previous]
    C --> A
    B -->|Core ML| D[AlphaGo Lite.app<br/>Play · AI vs AI · Training]
```

## Links

- [Instructions](docs/INSTRUCTIONS.md): build and run the app, how to play, how to retrain
- [System design](docs/SYSTEM-DESIGN.md): architecture, flows, decisions, limits
- [File structure](docs/FILE-STRUCTURE.md): what's where
- [Project brief](algha_go_lite.md)
