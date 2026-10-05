import Charts
import GoEngine
import SwiftUI

@MainActor
final class PlayModel: ObservableObject {
    @Published private(set) var position = Position()
    @Published private(set) var moves: [Int] = []
    @Published var humanColor: Stone = .black
    @Published var strength: Strength = .normal
    @Published var showThinking = true { didSet { showThinking ? analyze() : stopAnalysis() } }
    @Published private(set) var snapshot: SearchSnapshot?
    @Published private(set) var aiThinking = false
    @Published private(set) var resigned: Stone?
    /// Black's win probability after each move, as estimated by the engine's searches.
    @Published private(set) var winrates: [Int: Double] = [:]

    private var history: [Position] = []
    private let worker = SearchWorker()

    var isOver: Bool { position.isOver || resigned != nil }
    var isHumanTurn: Bool { !isOver && position.toPlay == humanColor }
    var lastMove: Int? { moves.last }

    var blackWinrate: Double? {
        guard let s = snapshot, s.position == position else { return winrates[moves.count] }
        return s.position.toPlay == .black ? s.winrate : 1 - s.winrate
    }

    var status: String {
        if let line = resultLine { return line }
        if aiThinking { return "AlphaGo Lite is thinking…" }
        if moves.last == Go.pass { return "\(position.toPlay.opponent.name) passed — your move" }
        return isHumanTurn ? "Your move (\(humanColor.name))" : ""
    }

    var resultLine: String? {
        if let r = resigned { return r == humanColor ? "AlphaGo Lite wins by resignation" : "You win by resignation" }
        guard position.isOver else { return nil }
        let s = position.areaScore()
        let winner: Stone = s > 0 ? .black : .white
        return "\(Position.resultString(s)) — " + (winner == humanColor ? "you win" : "AlphaGo Lite wins")
    }

    func newGame(as color: Stone) {
        worker.reset()
        humanColor = color
        position = Position()
        history = []
        moves = []
        snapshot = nil
        resigned = nil
        winrates = [:]
        aiThinking = false
        if color == .white { aiMove() } else { analyze() }
    }

    func humanPlay(_ m: Int) {
        guard isHumanTurn, position.isLegal(m) else { return }
        stopAnalysis()
        apply(m)
        aiMove()
    }

    func resign() {
        guard !isOver else { return }
        worker.cancel()
        aiThinking = false
        resigned = humanColor
    }

    func undo() {
        guard !history.isEmpty else { return }
        worker.reset()
        aiThinking = false
        resigned = nil
        repeat {
            position = history.removeLast()
            winrates[moves.count] = nil
            moves.removeLast()
        } while position.toPlay != humanColor && !history.isEmpty
        snapshot = nil
        if position.toPlay != humanColor { aiMove() } else { analyze() }
    }

    private func apply(_ m: Int) {
        history.append(position)
        moves.append(m)
        position = position.play(m)
        snapshot = nil
    }

    private func record(_ snap: SearchSnapshot) {
        let black = snap.position.toPlay == .black ? snap.winrate : 1 - snap.winrate
        winrates[moves.count] = black
    }

    private func aiMove() {
        guard !isOver, position.toPlay != humanColor else { return }
        // If you passed and the engine already wins on the board as it stands, it passes too.
        if moves.last == Go.pass {
            let s = position.areaScore()
            if (s > 0) == (position.toPlay == .black) { apply(Go.pass); return }
        }
        aiThinking = true
        worker.search(position, simulations: strength.simulations, progress: { [weak self] snap in
            self?.snapshot = snap
        }, completion: { [weak self] snap in
            guard let self else { return }
            self.aiThinking = false
            self.record(snap)
            self.apply(snap.bestMove)
            self.analyze()
        })
    }

    /// Background analysis of your turn, so the overlay shows what the engine would play.
    private func analyze() {
        guard showThinking, isHumanTurn else { return }
        worker.search(position, simulations: strength.simulations, progress: { [weak self] snap in
            self?.snapshot = snap
        }, completion: { [weak self] snap in
            self?.snapshot = snap
            self?.record(snap)
        })
    }

    private func stopAnalysis() {
        if !aiThinking { worker.cancel() }
    }

    func overlay() -> BoardOverlay {
        if isOver, resigned == nil { return BoardOverlay(ownership: position.ownership()) }
        guard showThinking, let s = snapshot, s.position == position else { return BoardOverlay() }
        var wr: [Int: Double] = [:]
        for m in s.topMoves.prefix(5) where m.visits >= max(3, s.simulations / 50) { wr[m.move] = m.winrate }
        return BoardOverlay(visits: s.visits, winrates: wr, bestMove: s.bestMove)
    }
}

struct PlayView: View {
    @StateObject private var model = PlayModel()
    @State private var started = false

    var body: some View {
        HStack(spacing: 0) {
            VStack(spacing: 10) {
                BoardView(position: model.position, lastMove: model.lastMove, overlay: model.overlay(),
                          interactive: model.isHumanTurn, onPlay: model.humanPlay)
                    .padding(.horizontal)
                Text(model.status)
                    .font(.headline)
                    .frame(height: 22)
            }
            .padding(.vertical)
            .frame(minWidth: 440, maxWidth: .infinity)

            Divider()
            ThinkingPanel(model: model)
                .frame(width: 290)
        }
        .toolbar {
            ToolbarItemGroup {
                Menu {
                    Button("Play as Black") { model.newGame(as: .black) }
                    Button("Play as White") { model.newGame(as: .white) }
                } label: { Label("New Game", systemImage: "plus.circle") }
                Button { model.humanPlay(Go.pass) } label: { Label("Pass", systemImage: "hand.raised") }
                    .disabled(!model.isHumanTurn)
                Button { model.undo() } label: { Label("Undo", systemImage: "arrow.uturn.backward") }
                    .disabled(model.moves.isEmpty)
                    .keyboardShortcut("z")
                Button { model.resign() } label: { Label("Resign", systemImage: "flag") }
                    .disabled(model.isOver)
            }
        }
        .navigationTitle("Play")
        .onAppear { if !started { started = true; model.newGame(as: .black) } }
    }
}

struct ThinkingPanel: View {
    @ObservedObject var model: PlayModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Picker("Strength", selection: $model.strength) {
                    ForEach(Strength.allCases) { s in Text("\(s.rawValue) (\(s.simulations))").tag(s) }
                }
                Toggle("Show the engine's thinking", isOn: $model.showThinking)

                Divider()
                Text("Win probability").font(.subheadline.bold())
                WinBar(black: model.blackWinrate ?? 0.5)

                if model.showThinking, let s = model.snapshot, s.position == model.position {
                    HStack {
                        Text("\(s.simulations) simulations")
                        Spacer()
                        Text("Net alone: \(Int((s.netWinrate * 100).rounded()))%").help("Value head's estimate before any search, for the player to move")
                    }
                    .font(.caption).foregroundStyle(.secondary)

                    Text("Candidate moves (\(s.position.toPlay.name))").font(.subheadline.bold())
                    Grid(alignment: .leading, horizontalSpacing: 10, verticalSpacing: 4) {
                        GridRow {
                            Text("Move"); Text("Visits"); Text("Win %"); Text("Prior")
                        }
                        .font(.caption.bold()).foregroundStyle(.secondary)
                        ForEach(s.topMoves.prefix(6)) { m in
                            GridRow {
                                Text(Go.moveName(m.move)).bold()
                                Text("\(m.visits)")
                                Text(String(format: "%.1f", m.winrate * 100))
                                Text(String(format: "%.1f%%", m.prior * 100))
                            }
                            .font(.callout.monospacedDigit())
                        }
                    }
                    if !s.principalVariation.isEmpty {
                        Text("Expected line: " + s.principalVariation.prefix(6).map(Go.moveName).joined(separator: " → "))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }

                if model.winrates.count > 1 {
                    Divider()
                    Text("Black's win probability over the game").font(.subheadline.bold())
                    Chart(model.winrates.sorted { $0.key < $1.key }, id: \.key) { item in
                        LineMark(x: .value("Move", item.key), y: .value("Black win %", item.value * 100))
                        AreaMark(x: .value("Move", item.key), y: .value("Black win %", item.value * 100))
                            .opacity(0.15)
                    }
                    .chartYScale(domain: 0...100)
                    .frame(height: 120)
                }

                Divider()
                Text("Scoring is by area (Tromp-Taylor), komi 7.5: every stone on the board counts as alive, so capture dead stones before passing.")
                    .font(.caption).foregroundStyle(.secondary)
                Text(SearchWorker.modelStatus).font(.caption2).foregroundStyle(.tertiary)
            }
            .padding()
        }
    }
}
