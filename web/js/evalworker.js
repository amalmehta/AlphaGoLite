// Network-evaluation helper: one ONNX Runtime session on its own thread.
// The search worker (worker.js) starts a few of these and splits each batch of
// leaf positions between them, so several CPU cores run the network at once.
//
// In:  {id, x: Float32Array(n * 486), n}
// Out: {type: "ready", ok, error?}, then {id, policy: Float32Array(n * 82), value: Float32Array(n)}
const ORT_VERSION = "1.17.3";
importScripts(`https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/ort.min.js`);

const session = (async () => {
  ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
  ort.env.wasm.numThreads = 1;
  return ort.InferenceSession.create("../model/alphagolite.onnx", { executionProviders: ["wasm"] });
})();
session.then(() => postMessage({ type: "ready", ok: true }), (e) => postMessage({ type: "ready", ok: false, error: e.message }));

onmessage = async (e) => {
  const { id, x, n } = e.data;
  const s = await session;
  const out = await s.run({ planes: new ort.Tensor("float32", x, [n, 6, 9, 9]) });
  const policy = Float32Array.from(out.policy.data), value = Float32Array.from(out.value.data);
  postMessage({ id, policy, value }, [policy.buffer, value.buffer]);
};
