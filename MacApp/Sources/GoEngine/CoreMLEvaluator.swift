import CoreML
import Foundation

/// Runs the trained policy/value network (exported by trainer/export_coreml.py).
/// Input "planes" [1,6,9,9]; outputs "policy" [1,82] logits and "value" [1,1].
public final class CoreMLEvaluator: Evaluator {
    let model: MLModel
    let input: MLMultiArray

    public init(compiledModelURL url: URL) throws {
        let config = MLModelConfiguration()
        config.computeUnits = .cpuOnly  // tiny net: CPU beats the round trip to GPU/ANE
        model = try MLModel(contentsOf: url, configuration: config)
        input = try MLMultiArray(shape: [1, 6, 9, 9], dataType: .float32)
    }

    public func evaluate(_ features: [Float]) throws -> (logits: [Float], value: Float) {
        let ptr = input.dataPointer.bindMemory(to: Float.self, capacity: features.count)
        features.withUnsafeBufferPointer { ptr.update(from: $0.baseAddress!, count: features.count) }
        let out = try model.prediction(from: MLDictionaryFeatureProvider(dictionary: ["planes": input]))
        guard let p = out.featureValue(for: "policy")?.multiArrayValue,
              let v = out.featureValue(for: "value")?.multiArrayValue else {
            throw NSError(domain: "AlphaGoLite", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Model outputs missing"])
        }
        var logits = [Float](repeating: 0, count: Go.numMoves)
        for i in 0..<Go.numMoves { logits[i] = p[i].floatValue }
        return (logits, v[0].floatValue)
    }
}

/// Uniform policy, zero value: pure search with no knowledge. Used in tests and
/// as a fallback when no model is bundled.
public final class UniformEvaluator: Evaluator {
    public init() {}
    public func evaluate(_ features: [Float]) throws -> (logits: [Float], value: Float) {
        ([Float](repeating: 0, count: Go.numMoves), 0)
    }
}
