import Charts
import SwiftUI
import UniformTypeIdentifiers

/// Charts of a training run. Shows the run bundled with the app, or a live run
/// folder (re-read every 20 seconds while training is in progress).
@MainActor
final class TrainingModel: ObservableObject {
    @Published private(set) var metrics: TrainingMetrics?
    @Published private(set) var source = "The training run bundled with this app"
    @Published private(set) var error: String?
    private var liveURL: URL?
    private var timer: Timer?

    init() {
        if let url = AppResources.url("metrics", "json") { load(url) } else { error = "No bundled training metrics" }
    }

    func load(_ url: URL) {
        do { metrics = try TrainingMetrics.load(url); error = nil } catch { self.error = error.localizedDescription }
    }

    func openRun(_ url: URL) {
        let file = url.hasDirectoryPath ? url.appendingPathComponent("metrics.json") : url
        _ = url.startAccessingSecurityScopedResource()
        liveURL = file
        source = "Live run: " + file.deletingLastPathComponent().path
        load(file)
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in
            Task { @MainActor in if let self, let u = self.liveURL { self.load(u) } }
        }
    }
}

struct TrainingView: View {
    @StateObject private var model = TrainingModel()
    @State private var importing = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                if let m = model.metrics {
                    content(m)
                } else {
                    Text(model.error ?? "Loading…").foregroundStyle(.secondary)
                }
            }
            .padding(20)
        }
        .navigationTitle("Training")
        .toolbar {
            Button { importing = true } label: { Label("Open Training Run…", systemImage: "folder") }
                .help("Open a run folder (trainer/runs/…) to watch training live")
        }
        .fileImporter(isPresented: $importing, allowedContentTypes: [.folder, .json]) { result in
            if case .success(let url) = result { model.openRun(url) }
        }
    }

    @ViewBuilder
    func content(_ m: TrainingMetrics) -> some View {
        let gens = m.generations
        let last = gens.last
        Text("How AlphaGo Lite taught itself 9×9 Go").font(.title2.bold())
        Text(model.source).font(.caption).foregroundStyle(.secondary)
        Text("Each generation: the current network plays itself with tree search, the network trains on those games, then the new network plays the previous one to measure progress.")
            .foregroundStyle(.secondary)

        HStack(spacing: 12) {
            Tile(title: "Generations", value: "\(last?.gen ?? 0)")
            Tile(title: "Self-play games", value: (last?.totalGames ?? 0).formatted())
            Tile(title: "Training time", value: String(format: "%.1f h", (last?.elapsedMin ?? 0) / 60))
            if let c = m.strengthChecks?.first(where: { $0.vs == 0 }) {
                Tile(title: "Wins vs. random start", value: "\(c.wins * 100 / max(1, c.games))%")
            } else {
                Tile(title: "Chained Elo", value: String(format: "%+.0f", last?.elo ?? 0))
            }
        }

        if let checks = m.strengthChecks, !checks.isEmpty {
            ChartCard(title: "Head-to-head: the network in the app vs. earlier generations") {
                Chart(checks.sorted { $0.vs < $1.vs }) { c in
                    BarMark(x: .value("Win %", Double(c.wins) / Double(max(1, c.games)) * 100),
                            y: .value("Opponent", "vs. generation \(c.vs)"))
                        .annotation(position: .trailing) {
                            Text("\(c.wins)/\(c.games) games").font(.caption)
                        }
                    RuleMark(x: .value("Even", 50)).foregroundStyle(.secondary)
                }
                .chartXScale(domain: 0...100)
            }
        }

        ChartCard(title: "Chained Elo by generation (each step from 40 games, so noisy: roughly ±100)") {
            Chart(gens) { g in
                LineMark(x: .value("Generation", g.gen), y: .value("Elo", g.elo))
                if g.gen == m.exportedGen {
                    PointMark(x: .value("Generation", g.gen), y: .value("Elo", g.elo))
                        .annotation(position: .top) { Text("in app").font(.caption2) }
                }
            }
        }

        let losses = gens.flatMap { g -> [LossPoint] in
            var out: [LossPoint] = []
            if let p = g.policyLoss { out.append(LossPoint(gen: g.gen, kind: "Policy loss", value: p)) }
            if let v = g.valueLoss { out.append(LossPoint(gen: g.gen, kind: "Value loss", value: v)) }
            return out
        }
        ChartCard(title: "Training loss") {
            Chart(losses) { item in
                LineMark(x: .value("Generation", item.gen), y: .value("Loss", item.value))
                    .foregroundStyle(by: .value("Loss", item.kind))
                PointMark(x: .value("Generation", item.gen), y: .value("Loss", item.value))
                    .foregroundStyle(by: .value("Loss", item.kind))
                    .symbolSize(18)
            }
        }

        HStack(spacing: 12) {
            ChartCard(title: "Win rate vs previous generation") {
                Chart(gens.filter { $0.winrateVsPrev != nil }) { g in
                    BarMark(x: .value("Generation", g.gen), y: .value("Win %", (g.winrateVsPrev ?? 0) * 100))
                    RuleMark(y: .value("Even", 50)).foregroundStyle(.secondary)
                }
                .chartYScale(domain: 0...100)
            }
            ChartCard(title: "Average game length (moves)") {
                Chart(gens.filter { $0.avgGameLength != nil }) { g in
                    LineMark(x: .value("Generation", g.gen), y: .value("Moves", g.avgGameLength ?? 0))
                }
            }
        }

        if let c = m.config {
            Text("Settings: \(c.gamesPerGen ?? 0) games per generation, \(c.sims ?? 0) simulations per full search, \(c.workers ?? 0) self-play workers. Elo is chained from head-to-head matches between consecutive generations, so it measures progress, not strength against humans.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}

struct LossPoint: Identifiable {
    var id: String { "\(gen)-\(kind)" }
    let gen: Int
    let kind: String
    let value: Double
}

struct Tile: View {
    let title: String
    let value: String
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.title.bold().monospacedDigit())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 10))
    }
}

struct ChartCard<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline)
            content.frame(height: 180)
        }
        .padding(12)
        .background(.quaternary.opacity(0.3), in: RoundedRectangle(cornerRadius: 10))
    }
}
