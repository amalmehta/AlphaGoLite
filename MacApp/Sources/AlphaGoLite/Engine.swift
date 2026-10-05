import Foundation
import GoEngine

/// Finds bundled resources: inside the .app they live in Contents/Resources;
/// during development (`swift run`) set ALPHAGO_LITE_RESOURCES or run from MacApp/.
enum AppResources {
    static func url(_ name: String, _ ext: String) -> URL? {
        if let u = Bundle.main.url(forResource: name, withExtension: ext) { return u }
        let dirs = [ProcessInfo.processInfo.environment["ALPHAGO_LITE_RESOURCES"],
                    FileManager.default.currentDirectoryPath + "/build/Resources"].compactMap { $0 }
        for d in dirs {
            let u = URL(fileURLWithPath: d).appendingPathComponent("\(name).\(ext)")
            if FileManager.default.fileExists(atPath: u.path) { return u }
        }
        return nil
    }
}

/// Runs MCTS off the main thread. One worker owns one search tree; calls are
/// serialised on its queue so the tree is never touched concurrently.
final class SearchWorker: @unchecked Sendable {
    static let modelStatus: String = {
        _ = sharedEvaluator
        return modelError ?? "Trained network loaded"
    }()
    private static var modelError: String?
    private static let sharedEvaluator: Evaluator = {
        guard let url = AppResources.url("AlphaGoLite", "mlmodelc") else {
            modelError = "No trained network found — using a uniform policy"
            return UniformEvaluator()
        }
        do { return try CoreMLEvaluator(compiledModelURL: url) } catch {
            modelError = "Could not load network: \(error.localizedDescription)"
            return UniformEvaluator()
        }
    }()

    private let queue = DispatchQueue(label: "AlphaGoLite.search", qos: .userInitiated)
    private let lock = NSLock()
    private var stopFlag = false
    private var generation = 0
    private var mcts: MCTS?

    var stopRequested: Bool { lock.lock(); defer { lock.unlock() }; return stopFlag }

    /// Stops any running search; its completion is not delivered.
    func cancel() {
        lock.lock(); stopFlag = true; generation += 1; lock.unlock()
    }

    /// Search `position` for `simulations`. Callbacks run on the main queue and are
    /// dropped if `cancel()` is called (or a newer search starts) in the meantime.
    func search(_ position: Position, simulations: Int,
                progress: @escaping (SearchSnapshot) -> Void,
                completion: @escaping (SearchSnapshot) -> Void) {
        lock.lock(); generation += 1; let gen = generation; stopFlag = false; lock.unlock()
        queue.async { [self] in
            let isCurrent = { [self] in self.lock.lock(); defer { self.lock.unlock() }; return self.generation == gen }
            let mcts = self.mcts ?? MCTS(evaluator: Self.sharedEvaluator, position: position)
            self.mcts = mcts
            mcts.advance(to: position)
            let start = Int(mcts.snapshot().simulations)
            let remaining = max(1, simulations - start)
            do {
                try mcts.search(remaining, every: 40, shouldStop: { [self] in self.stopRequested || !isCurrent() }) { snap in
                    DispatchQueue.main.async { if isCurrent() { progress(snap) } }
                }
            } catch {
                NSLog("search failed: \(error)")
            }
            let final = mcts.snapshot()
            DispatchQueue.main.async { if isCurrent() { completion(final) } }
        }
    }

    /// Forget the tree (e.g. after undo or a new game).
    func reset() {
        cancel()
        queue.async { [self] in self.mcts = nil }
    }
}

enum Strength: String, CaseIterable, Identifiable {
    case quick = "Quick", normal = "Normal", strong = "Strong", maximum = "Maximum"
    var id: String { rawValue }
    var simulations: Int {
        switch self {
        case .quick: return 100
        case .normal: return 400
        case .strong: return 1200
        case .maximum: return 3000
        }
    }
}
