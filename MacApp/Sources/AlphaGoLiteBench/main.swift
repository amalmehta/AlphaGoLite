// Cross-platform benchmark, Swift/Core ML side (used by paper/alphago-lite/bench).
//   swift run -c release AlphaGoLiteBench <positions.json> <model.mlmodelc> <out.json>
// Searches each position from an empty tree, timing the best of 3 runs.
import Foundation
import GoEngine

struct Input: Decodable {
    struct Case: Decodable { let moves: [Int] }
    let sims: Int
    let cases: [Case]
}

let args = CommandLine.arguments
guard args.count == 4 else {
    print("usage: AlphaGoLiteBench <positions.json> <model.mlmodelc> <out.json>")
    exit(2)
}
let input = try JSONDecoder().decode(Input.self, from: Data(contentsOf: URL(fileURLWithPath: args[1])))
let evaluator = try CoreMLEvaluator(compiledModelURL: URL(fileURLWithPath: args[2]))
var results: [[String: Any]] = []
for c in input.cases {
    var pos = Position()
    for m in c.moves { pos = pos.play(m) }
    var best = Double.infinity
    var mcts = MCTS(evaluator: evaluator, position: pos)
    for _ in 0..<3 {
        mcts = MCTS(evaluator: evaluator, position: pos)
        let t = Date()
        try mcts.search(input.sims)
        best = min(best, Date().timeIntervalSince(t))
    }
    let visits = mcts.root.visits.map { Int($0) }
    results.append(["visits": visits, "best": mcts.bestMove(), "ms": best * 1000])
}
let out: [String: Any] = ["platform": "Swift / Core ML (CPU only)", "sims": input.sims, "repeats": 3, "cases": results]
try JSONSerialization.data(withJSONObject: out).write(to: URL(fileURLWithPath: args[3]))
let ms = results.map { $0["ms"] as! Double }.sorted()
print(String(format: "swift: median %.0f ms per %d-sim search (%d positions)", ms[ms.count / 2], input.sims, ms.count))
