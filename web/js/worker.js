// Search worker: owns the network (ONNX Runtime Web) and one MCTS tree, so the
// page stays responsive while the engine thinks.
//
// In:  {type: "search", id, position, sims}   search a position (reuses the tree)
//      {type: "cancel"}                        stop the current search, drop its result
//      {type: "reset"}                         forget the tree
// Out: {type: "ready", status}
//      {type: "progress" | "done", id, snap}
const ORT_VERSION = "1.17.3";
importScripts(`https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/ort.min.js`, "go.js", "mcts.js");

let evaluator = uniformEvaluator;
let mcts = null;
let current = null; // id of the search whose results we still want
let queue = Promise.resolve();

const ready = (async () => {
  try {
    ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
    ort.env.wasm.numThreads = 1; // GitHub Pages can't send the headers threads need
    const session = await ort.InferenceSession.create("../model/alphagolite.onnx", { executionProviders: ["wasm"] });
    evaluator = async (features) => {
      const out = await session.run({ planes: new ort.Tensor("float32", features, [1, 6, 9, 9]) });
      return { logits: out.policy.data, value: out.value.data[0] };
    };
    postMessage({ type: "ready", status: "Trained network loaded" });
  } catch (e) {
    postMessage({ type: "ready", status: "Could not load the network (" + e.message + ") — using a uniform policy" });
  }
})();

async function runSearch({ id, position, sims }) {
  await ready;
  if (id !== current) return;
  const pos = Go.deserialize(position);
  if (!mcts) mcts = new MCTS(evaluator, pos);
  mcts.evaluator = evaluator;
  mcts.advance(pos);
  const remaining = Math.max(1, sims - mcts.root.total);
  await mcts.search(remaining, {
    shouldStop: () => id !== current,
    onProgress: (snap) => { if (id === current) postMessage({ type: "progress", id, snap }); },
  });
  if (id === current) postMessage({ type: "done", id, snap: mcts.snapshot() });
}

onmessage = (e) => {
  const msg = e.data;
  if (msg.type === "search") {
    current = msg.id;
    // Searches run one after another so two never touch the tree at once.
    queue = queue.then(() => runSearch(msg)).catch((err) => console.error(err));
  } else if (msg.type === "cancel") {
    current = null;
  } else if (msg.type === "reset") {
    current = null;
    queue = queue.then(() => { mcts = null; });
  }
};
