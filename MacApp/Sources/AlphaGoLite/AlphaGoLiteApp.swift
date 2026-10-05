import AppKit
import SwiftUI

@main
struct AlphaGoLiteApp: App {
    @AppStorage("section") private var section: AppSection = .play

    init() {
        // Needed when launched as a bare executable (swift run) rather than an .app.
        NSApplication.shared.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup("AlphaGo Lite") {
            ContentView(section: $section)
                .frame(minWidth: 900, minHeight: 640)
        }
        .defaultSize(width: 1180, height: 780)
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandGroup(before: .sidebar) {
                ForEach(Array(AppSection.allCases.enumerated()), id: \.element) { i, s in
                    Button(s.rawValue) { section = s }
                        .keyboardShortcut(KeyEquivalent(Character("\(i + 1)")), modifiers: .command)
                }
                Divider()
            }
        }
    }
}

enum AppSection: String, CaseIterable, Identifiable {
    case play = "Play", watch = "AI vs AI", training = "Training"
    var id: String { rawValue }
    var icon: String {
        switch self {
        case .play: return "circle.grid.3x3.fill"
        case .watch: return "play.rectangle"
        case .training: return "chart.xyaxis.line"
        }
    }
}

struct ContentView: View {
    @Binding var section: AppSection
    @State private var showFeedback = false

    var body: some View {
        NavigationSplitView {
            List(AppSection.allCases, selection: Binding<AppSection?>(get: { section }, set: { if let s = $0 { section = s } })) { s in
                Label(s.rawValue, systemImage: s.icon).tag(s)
            }
            .navigationSplitViewColumnWidth(170)
            .safeAreaInset(edge: .bottom) {
                Button { showFeedback = true } label: {
                    Label("Feedback", systemImage: "bubble.left")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .help("Send feedback about AlphaGo Lite")
            }
        } detail: {
            switch section {
            case .play: PlayView()
            case .watch: WatchView()
            case .training: TrainingView()
            }
        }
        .sheet(isPresented: $showFeedback) { FeedbackView() }
    }
}
