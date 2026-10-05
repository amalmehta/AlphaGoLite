import Charts
import GoEngine
import SwiftUI

/// AI vs AI: replays of recorded self-play games from training, or a fresh game
/// played live by the trained engine against itself.
@MainActor
final class WatchModel: ObservableObject {
    @Published private(set) var games: [ReplayGame] = []
    @Published var selection: String? { didSet { if selection != oldValue { select() } } }
    @Published private(set) var game: ReplayGame?
    @Published private(set) var positions: [Position] = [Position()]
    @Published var step = 0
    @Published private(set) var playing = false
    @Published private(set) var liveRunning = false
    @Published private(set) var liveSnapshot: SearchSnapshot?
    @Published var liveStrength: Strength = .quick

    static let liveID = "Live game"
    private let worker = SearchWorker()
    private var timer: Timer?

    init() {
        if let url = AppResources.url("games", "json"), let g = try? ReplayGame.loadAll(url) { games = g }
        selection = games.last?.id ?? Self.liveID
        select()
    }

    var isLive: Bool { selection == Self.liveID }
    var maxStep: Int { positions.count - 1 }
    var position: Position { positions[min(step, maxStep)] }

    private func select() {
        stopPlayback()
        stopLive()
        if isLive {
            game = ReplayGame(title: Self.liveID, generation: nil, result: "", moves: [])
        } else {
            game = games.first { $0.id == selection }
        }
        var ps = [Position()]
        for m in game?.moves ?? [] { ps.append(ps.last!.play(m.move)) }
        positions = ps
        step = 0
    }

    /// Black win probability per move (from the recorded search values).
    var curve: [(Int, Double)] {
        (game?.moves ?? []).enumerated().map { ($0.offset, ($0.element.value + 1) / 2) }
    }

    func overlay() -> BoardOverlay {
        if isLive, liveRunning, let s = liveSnapshot, s.position == position {
            return BoardOverlay(visits: s.visits, bestMove: s.bestMove)
        }
        guard let g = game, step < g.moves.count else {
            return position.isOver ? BoardOverlay(ownership: position.ownership()) : BoardOverlay()
        }
        let v = g.moves[step].visits.map(Double.init)
        return BoardOverlay(visits: v, bestMove: g.moves[step].move)
    }

    var lastMove: Int? { step > 0 ? game?.moves[step - 1].move : nil }

    var caption: String {
        guard let g = game else { return "" }
        if step < g.moves.count {
            let m = g.moves[step]
            let who = position.toPlay.name
            return "Move \(step + 1): \(who) plays \(Go.moveName(m.move)) — \(m.visits.reduce(0, +)) simulations"
        }
        if position.isOver { return "Final: \(Position.resultString(position.areaScore()))" }
        return liveRunning ? "Thinking…" : "Move \(step)"
    }

    // MARK: playback

    func togglePlayback() {
        if playing { stopPlayback(); return }
        if step >= maxStep { step = 0 }
        playing = true
        timer = Timer.scheduledTimer(withTimeInterval: 0.6, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                if self.step < self.maxStep { self.step += 1 } else { self.stopPlayback() }
            }
        }
    }

    func stopPlayback() {
        timer?.invalidate()
        timer = nil
        playing = false
    }

    // MARK: live game

    func startLive() {
        selection = Self.liveID
        select()
        liveRunning = true
        nextLiveMove()
    }

    func stopLive() {
        worker.reset()
        liveRunning = false
        liveSnapshot = nil
    }

    private func nextLiveMove() {
        guard liveRunning, let last = positions.last, !last.isOver else { liveRunning = false; return }
        worker.search(last, simulations: liveStrength.simulations, progress: { [weak self] s in
            self?.liveSnapshot = s
        }, completion: { [weak self] s in
            guard let self, self.liveRunning else { return }
            let blackValue = (s.position.toPlay == .black ? s.winrate : 1 - s.winrate) * 2 - 1
            let mv = ReplayGame.Move(move: s.bestMove, value: blackValue, visits: s.visits.map { Int($0) }, full: true)
            self.game?.moves.append(mv)
            let following = self.step == self.maxStep
            self.positions.append(last.play(s.bestMove))
            if following { self.step = self.maxStep }
            if let p = self.positions.last, p.isOver {
                self.game?.result = Position.resultString(p.areaScore())
                self.liveRunning = false
            } else {
                self.nextLiveMove()
            }
        })
    }
}

struct WatchView: View {
    @StateObject private var model = WatchModel()

    var body: some View {
        HStack(spacing: 0) {
            List(selection: $model.selection) {
                Section("Live") {
                    Label(WatchModel.liveID, systemImage: "bolt.fill").tag(WatchModel.liveID)
                }
                Section("Self-play games from training") {
                    ForEach(model.games) { g in
                        VStack(alignment: .leading) {
                            Text(g.title)
                            Text("\(g.result) · \(g.moves.count) moves").font(.caption).foregroundStyle(.secondary)
                        }
                        .tag(g.id)
                    }
                    if model.games.isEmpty {
                        Text("No recorded games bundled").foregroundStyle(.secondary)
                    }
                }
            }
            .listStyle(.sidebar)
            .frame(width: 230)

            Divider()

            VStack(spacing: 10) {
                BoardView(position: model.position, lastMove: model.lastMove, overlay: model.overlay())
                    .padding(.horizontal)
                Text(model.caption).font(.callout.monospacedDigit()).frame(height: 20)
                HStack {
                    Button { model.step = 0 } label: { Image(systemName: "backward.end.fill").accessibilityLabel("First move") }
                    Button { model.step = max(0, model.step - 1) } label: { Image(systemName: "backward.fill").accessibilityLabel("Previous move") }
                        .keyboardShortcut(.leftArrow, modifiers: [])
                    Button { model.togglePlayback() } label: { Image(systemName: model.playing ? "pause.fill" : "play.fill").accessibilityLabel(model.playing ? "Pause" : "Play") }
                        .keyboardShortcut(.space, modifiers: [])
                    Button { model.step = min(model.maxStep, model.step + 1) } label: { Image(systemName: "forward.fill").accessibilityLabel("Next move") }
                        .keyboardShortcut(.rightArrow, modifiers: [])
                    Button { model.step = model.maxStep } label: { Image(systemName: "forward.end.fill").accessibilityLabel("Last move") }
                    Slider(value: Binding(get: { Double(model.step) }, set: { model.step = Int($0.rounded()) }),
                           in: 0...Double(max(1, model.maxStep)))
                        .disabled(model.maxStep == 0)
                    Text("\(model.step)/\(model.maxStep)").monospacedDigit().frame(width: 60)
                }
                .buttonStyle(.borderless)
                .padding(.horizontal)

                if model.isLive {
                    HStack {
                        Picker("Strength", selection: $model.liveStrength) {
                            ForEach(Strength.allCases) { s in Text("\(s.rawValue) (\(s.simulations))").tag(s) }
                        }
                        .frame(width: 240)
                        .disabled(model.liveRunning)
                        Button(model.liveRunning ? "Stop" : "Start a new game") {
                            model.liveRunning ? model.stopLive() : model.startLive()
                        }
                    }
                }

                Chart {
                    ForEach(model.curve, id: \.0) { item in
                        LineMark(x: .value("Move", item.0), y: .value("Black win %", item.1 * 100))
                    }
                    RuleMark(x: .value("Current", model.step)).foregroundStyle(.orange)
                    RuleMark(y: .value("Even", 50)).foregroundStyle(.secondary.opacity(0.4))
                }
                .chartYScale(domain: 0...100)
                .chartYAxisLabel("Black win %")
                .frame(height: 110)
                .padding(.horizontal)
            }
            .padding(.vertical)
            .frame(minWidth: 460, maxWidth: .infinity)
        }
        .navigationTitle("AI vs AI")
        .onDisappear { model.stopPlayback() }
    }
}
