// 9x9 Go rules: simple ko, no suicide, Tromp-Taylor area scoring.
// Mirrors trainer/alphago_lite/go.py exactly; Tests/GoEngineTests check parity
// against test vectors written by the Python side.

public enum Go {
    public static let size = 9
    public static let points = 81
    public static let pass = 81
    public static let numMoves = 82
    public static let komi = 7.5
    public static let maxMoves = 162
    public static let numPlanes = 6

    public static let neighbors: [[Int]] = (0..<81).map { p in
        let r = p / 9, c = p % 9
        var out: [Int] = []
        if r > 0 { out.append(p - 9) }
        if r < 8 { out.append(p + 9) }
        if c > 0 { out.append(p - 1) }
        if c < 8 { out.append(p + 1) }
        return out
    }

    static let columns = Array("ABCDEFGHJ")

    public static func moveName(_ m: Int) -> String {
        if m == pass { return "pass" }
        return "\(columns[m % 9])\(9 - m / 9)"
    }
}

public enum Stone: Int8, Sendable {
    case black = 1, white = -1
    public var opponent: Stone { self == .black ? .white : .black }
    public var name: String { self == .black ? "Black" : "White" }
}

public struct Position: Sendable, Hashable {
    /// 1 black, -1 white, 0 empty
    public var board: [Int8]
    public var prevBoard: [Int8]
    public var toPlay: Stone
    public var ko: Int
    public var passes: Int
    public var moveCount: Int

    public init() {
        board = Array(repeating: 0, count: Go.points)
        prevBoard = board
        toPlay = .black
        ko = -1
        passes = 0
        moveCount = 0
    }

    public init(board: [Int8], prevBoard: [Int8], toPlay: Stone, ko: Int, passes: Int, moveCount: Int) {
        self.board = board
        self.prevBoard = prevBoard
        self.toPlay = toPlay
        self.ko = ko
        self.passes = passes
        self.moveCount = moveCount
    }

    public var isOver: Bool { passes >= 2 || moveCount >= Go.maxMoves }

    func group(_ b: [Int8], _ p: Int) -> (stones: [Int], liberties: Set<Int>) {
        let color = b[p]
        var seen = Set([p])
        var stones = [p]
        var libs = Set<Int>()
        var stack = [p]
        while let q = stack.popLast() {
            for n in Go.neighbors[q] {
                let v = b[n]
                if v == 0 { libs.insert(n) }
                else if v == color && !seen.contains(n) {
                    seen.insert(n); stones.append(n); stack.append(n)
                }
            }
        }
        return (stones, libs)
    }

    /// 82 flags; pass is always legal.
    public func legalMask() -> [Bool] {
        let me = toPlay.rawValue
        var gid = Array(repeating: -1, count: Go.points)
        var libCount: [Int] = []
        for p in 0..<Go.points where board[p] != 0 && gid[p] < 0 {
            let color = board[p]
            let g = libCount.count
            gid[p] = g
            var stack = [p]
            var libs = Set<Int>()
            while let q = stack.popLast() {
                for n in Go.neighbors[q] {
                    let v = board[n]
                    if v == 0 { libs.insert(n) }
                    else if v == color && gid[n] < 0 { gid[n] = g; stack.append(n) }
                }
            }
            libCount.append(libs.count)
        }
        var mask = Array(repeating: false, count: Go.numMoves)
        mask[Go.pass] = true
        for p in 0..<Go.points where board[p] == 0 && p != ko {
            for n in Go.neighbors[p] {
                let v = board[n]
                if v == 0 { mask[p] = true; break }
                let lc = libCount[gid[n]]
                if (v == me && lc > 1) || (v == -me && lc == 1) { mask[p] = true; break }
            }
        }
        return mask
    }

    public func isLegal(_ m: Int) -> Bool { m == Go.pass || (m >= 0 && m < Go.points && legalMask()[m]) }

    /// Position after move m. m must be legal.
    public func play(_ m: Int) -> Position {
        let me = toPlay.rawValue
        if m == Go.pass {
            return Position(board: board, prevBoard: board, toPlay: toPlay.opponent, ko: -1,
                            passes: passes + 1, moveCount: moveCount + 1)
        }
        var b = board
        b[m] = me
        var captured: [Int] = []
        for n in Go.neighbors[m] where b[n] == -me {
            let (stones, libs) = group(b, n)
            if libs.isEmpty {
                for s in stones { b[s] = 0 }
                captured.append(contentsOf: stones)
            }
        }
        let (stones, libs) = group(b, m)
        precondition(!libs.isEmpty, "suicide at \(m)")
        let newKo = (captured.count == 1 && stones.count == 1 && libs.count == 1) ? captured[0] : -1
        return Position(board: b, prevBoard: board, toPlay: toPlay.opponent, ko: newKo,
                        passes: 0, moveCount: moveCount + 1)
    }

    /// Black area minus white area minus komi.
    public func areaScore() -> Double {
        var score = 0
        var seen = Array(repeating: false, count: Go.points)
        for p in 0..<Go.points {
            let v = board[p]
            if v != 0 { score += Int(v); continue }
            if seen[p] { continue }
            seen[p] = true
            var region = 1
            var stack = [p]
            var borders = Set<Int8>()
            while let q = stack.popLast() {
                for n in Go.neighbors[q] {
                    let w = board[n]
                    if w == 0 {
                        if !seen[n] { seen[n] = true; region += 1; stack.append(n) }
                    } else { borders.insert(w) }
                }
            }
            if borders.count == 1 { score += region * Int(borders.first!) }
        }
        return Double(score) - Go.komi
    }

    /// Per-point owner under Tromp-Taylor: 1 black, -1 white, 0 neutral.
    public func ownership() -> [Int8] {
        var owner = board
        var seen = Array(repeating: false, count: Go.points)
        for p in 0..<Go.points where board[p] == 0 && !seen[p] {
            seen[p] = true
            var region = [p]
            var stack = [p]
            var borders = Set<Int8>()
            while let q = stack.popLast() {
                for n in Go.neighbors[q] {
                    let w = board[n]
                    if w == 0 {
                        if !seen[n] { seen[n] = true; region.append(n); stack.append(n) }
                    } else { borders.insert(w) }
                }
            }
            if borders.count == 1 { for r in region { owner[r] = borders.first! } }
        }
        return owner
    }

    public func winner() -> Stone { areaScore() > 0 ? .black : .white }

    /// 6x9x9 planes from the point of view of the player to move, flattened.
    public func features() -> [Float] {
        let me = toPlay.rawValue
        var f = Array(repeating: Float(0), count: Go.numPlanes * Go.points)
        let blackToPlay: Float = toPlay == .black ? 1 : 0
        for p in 0..<Go.points {
            let v = board[p], pv = prevBoard[p]
            if v == me { f[p] = 1 } else if v == -me { f[81 + p] = 1 }
            if pv == me { f[162 + p] = 1 } else if pv == -me { f[243 + p] = 1 }
            f[324 + p] = blackToPlay
            f[405 + p] = 1
        }
        return f
    }

    public static func resultString(_ score: Double) -> String {
        (score > 0 ? "B+" : "W+") + String(format: "%g", abs(score))
    }
}
