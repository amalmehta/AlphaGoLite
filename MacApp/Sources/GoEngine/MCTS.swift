import Foundation

/// Anything that maps a position's feature planes to policy logits and a value.
public protocol Evaluator: AnyObject {
    /// features: 6*81 floats. Returns 82 logits and a value in [-1, 1] for the player to move.
    func evaluate(_ features: [Float]) throws -> (logits: [Float], value: Float)
}

/// PUCT search, same constants and first-play-urgency rule as trainer/alphago_lite/mcts.py.
public final class MCTSNode {
    public let position: Position
    var legal: [Bool] = []
    public internal(set) var prior: [Double] = []
    public internal(set) var visits: [Double] = []
    var valueSum: [Double] = []
    public internal(set) var netValue: Double = 0
    var total: Double = 0
    var children: [Int: MCTSNode] = [:]
    public internal(set) var expanded = false

    init(_ position: Position) { self.position = position }

    func expand(logits: [Float], value: Float) {
        legal = position.legalMask()
        var maxL = -Double.infinity
        for i in 0..<Go.numMoves where legal[i] { maxL = max(maxL, Double(logits[i])) }
        var p = Array(repeating: 0.0, count: Go.numMoves)
        var sum = 0.0
        for i in 0..<Go.numMoves where legal[i] { p[i] = exp(Double(logits[i]) - maxL); sum += p[i] }
        prior = p.map { $0 / sum }
        visits = Array(repeating: 0, count: Go.numMoves)
        valueSum = visits
        netValue = Double(value)
        expanded = true
    }

    func select() -> Int {
        var visitedPrior = 0.0
        for i in 0..<Go.numMoves where visits[i] > 0 { visitedPrior += prior[i] }
        let fpu = netValue - MCTS.fpuReduction * visitedPrior.squareRoot()
        let scale = MCTS.cPuct * (total + 1).squareRoot()
        var best = -1, bestScore = -Double.infinity
        for i in 0..<Go.numMoves where legal[i] {
            let q = visits[i] > 0 ? valueSum[i] / visits[i] : fpu
            let s = q + prior[i] * scale / (1 + visits[i])
            if s > bestScore { bestScore = s; best = i }
        }
        return best
    }

    /// Mean value of move m for the player to move here.
    public func q(_ m: Int) -> Double { visits[m] > 0 ? valueSum[m] / visits[m] : netValue }
    public var totalVisits: Double { total }
    public var meanValue: Double {
        let n = visits.reduce(0, +)
        return n > 0 ? valueSum.reduce(0, +) / n : netValue
    }
}

public struct MoveStat: Identifiable, Sendable {
    public var id: Int { move }
    public let move: Int
    public let visits: Int
    public let prior: Double
    /// Win probability (0...1) for the player to move at the root.
    public let winrate: Double
}

/// A snapshot of the search, cheap to hand to the UI.
public struct SearchSnapshot: Sendable {
    public let position: Position
    public let simulations: Int
    public let visits: [Double]
    public let prior: [Double]
    /// Root win probability for the player to move.
    public let winrate: Double
    public let netWinrate: Double
    public let topMoves: [MoveStat]
    public let principalVariation: [Int]

    public var bestMove: Int { topMoves.first?.move ?? Go.pass }
}

public final class MCTS {
    public static let cPuct = 1.5
    public static let fpuReduction = 0.25

    public let evaluator: Evaluator
    public private(set) var root: MCTSNode

    public init(evaluator: Evaluator, position: Position = Position()) {
        self.evaluator = evaluator
        self.root = MCTSNode(position)
    }

    /// Move the root to `position`, reusing the subtree if it is a direct child.
    public func advance(to position: Position) {
        if let child = root.children.values.first(where: { $0.position == position }) {
            root = child
        } else if root.position != position {
            root = MCTSNode(position)
        }
    }

    static func terminalValue(_ p: Position) -> Double {
        p.winner() == p.toPlay ? 1 : -1
    }

    /// Run `count` simulations, calling `progress` every `every` simulations.
    public func search(_ count: Int, every: Int = 50, shouldStop: () -> Bool = { false },
                       progress: ((SearchSnapshot) -> Void)? = nil) throws {
        if !root.expanded {
            let out = try evaluator.evaluate(root.position.features())
            root.expand(logits: out.logits, value: out.value)
        }
        if root.position.isOver { return }
        for i in 0..<count {
            if shouldStop() { break }
            try simulate()
            if let progress, (i + 1) % every == 0 || i == count - 1 { progress(snapshot()) }
        }
    }

    func simulate() throws {
        var node = root
        var path: [(MCTSNode, Int)] = []
        var value: Double
        while true {
            let a = node.select()
            path.append((node, a))
            let child: MCTSNode
            if let c = node.children[a] { child = c } else {
                child = MCTSNode(node.position.play(a))
                node.children[a] = child
            }
            if child.position.isOver { value = Self.terminalValue(child.position); break }
            if !child.expanded {
                let out = try evaluator.evaluate(child.position.features())
                child.expand(logits: out.logits, value: out.value)
                value = Double(out.value)
                break
            }
            node = child
        }
        for (n, a) in path.reversed() {
            value = -value
            n.visits[a] += 1
            n.valueSum[a] += value
            n.total += 1
        }
    }

    public func snapshot(top: Int = 8) -> SearchSnapshot {
        let r = root
        let order = (0..<Go.numMoves).filter { r.expanded && r.visits[$0] > 0 }
            .sorted { r.visits[$0] > r.visits[$1] }
        let stats = order.prefix(top).map {
            MoveStat(move: $0, visits: Int(r.visits[$0]), prior: r.prior[$0], winrate: (r.q($0) + 1) / 2)
        }
        var pv: [Int] = []
        var node = r
        while node.expanded, pv.count < 10,
              let best = (0..<Go.numMoves).max(by: { node.visits[$0] < node.visits[$1] }),
              node.visits[best] > 0 {
            pv.append(best)
            guard let next = node.children[best] else { break }
            node = next
        }
        return SearchSnapshot(
            position: r.position, simulations: Int(r.total),
            visits: r.expanded ? r.visits : Array(repeating: 0, count: Go.numMoves),
            prior: r.expanded ? r.prior : Array(repeating: 0, count: Go.numMoves),
            winrate: (r.meanValue + 1) / 2, netWinrate: (r.netValue + 1) / 2,
            topMoves: stats, principalVariation: pv)
    }

    /// Most-visited move (ties broken by prior).
    public func bestMove() -> Int {
        let r = root
        guard r.expanded else { return Go.pass }
        return (0..<Go.numMoves).max {
            (r.visits[$0], r.prior[$0]) < (r.visits[$1], r.prior[$1])
        } ?? Go.pass
    }
}
