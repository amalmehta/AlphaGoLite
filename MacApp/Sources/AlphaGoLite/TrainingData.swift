import Foundation

/// metrics.json written by trainer/alphago_lite/train.py (one entry per generation).
struct TrainingMetrics: Decodable {
    struct Generation: Decodable, Identifiable {
        var id: Int { gen }
        let gen: Int
        let elo: Double
        let winrateVsPrev: Double?
        let policyLoss: Double?
        let valueLoss: Double?
        let games: Int?
        let totalGames: Int
        let positions: Int?
        let avgGameLength: Double?
        let blackWinrate: Double?
        let selfplaySec: Double?
        let trainSec: Double?
        let evalSec: Double?
        let elapsedMin: Double
    }

    struct Config: Decodable {
        let gamesPerGen: Int?
        let sims: Int?
        let workers: Int?
    }

    struct StrengthCheck: Decodable, Identifiable {
        var id: String { "\(gen)-\(vs)" }
        let gen: Int
        let vs: Int
        let wins: Int
        let games: Int
        let sims: Int
    }

    let generations: [Generation]
    let exportedGen: Int?
    let strengthChecks: [StrengthCheck]?
    let config: Config?

    static func load(_ url: URL) throws -> TrainingMetrics {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return try d.decode(TrainingMetrics.self, from: Data(contentsOf: url))
    }
}

/// games.json written by trainer/alphago_lite/export_app.py.
struct ReplayGame: Decodable, Identifiable {
    struct Move: Decodable {
        let move: Int
        /// Search's value for Black, -1...1.
        let value: Double
        let visits: [Int]
        let full: Bool?
    }

    var id: String { title }
    var title: String
    var generation: Int?
    var result: String
    var moves: [Move]

    static func loadAll(_ url: URL) throws -> [ReplayGame] {
        struct File: Decodable { let games: [ReplayGame] }
        return try JSONDecoder().decode(File.self, from: Data(contentsOf: url)).games
    }
}
