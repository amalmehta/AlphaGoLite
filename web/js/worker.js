// Search worker: owns one MCTS tree and the network (ONNX Runtime Web), so the
// page stays responsive while the engine thinks. The tree collects a batch of
// leaf positions at a time (MCTS.simulateBatch) and splits it between a few
// helper workers (evalworker.js), each running the network on its own core.
// Without helpers (or if they fail to load) it evaluates in this worker.
//
// In:  {type: "search", id, position, sims}   search a position (reuses the tree)
//      {type: "cancel"}                        stop the current search, drop its result
//      {type: "reset"}                         forget the tree
// Out: {type: "ready", status}
//      {type: "progress" | "done", id, snap}
const ORT_VERSION = "1.17.3";
const CODE_VERSION = 4; // bump when go.js or mcts.js change, so browsers don't mix cached copies
importScripts(`https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/ort.min.js`,
  `go.js?v=${CODE_VERSION}`, `mcts.js?v=${CODE_VERSION}`);

const HELPERS = Math.max(1, Math.min(4, Math.floor((self.navigator?.hardwareConcurrency || 2) / 2)));
// Leaves per batch: bigger batches keep more helpers busy but make each batch
// a little less informed (virtual loss), so small searches use small batches.
const batchFor = (sims) => Math.max(1, Math.min(4 * HELPERS, Math.round(sims / 50)));
let evaluator = uniformEvaluator, batchEvaluator = uniformBatchEvaluator;
let mcts = null;
let current = null; // id of the search whose results we still want
let queue = Promise.resolve();

const ready = (async () => {
  try {
    ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
    ort.env.wasm.numThreads = 1; // GitHub Pages can't send the headers threads need
    const session = await ort.InferenceSession.create(`../model/alphagolite.onnx?v=${CODE_VERSION}`, { executionProviders: ["wasm"] });
    evaluator = async (features) => {
      const out = await session.run({ planes: new ort.Tensor("float32", features, [1, 6, 9, 9]) });
      return { logits: out.policy.data, value: out.value.data[0] };
    };
    batchEvaluator = async (list) => {
      const x = new Float32Array(list.length * 486);
      list.forEach((f, i) => x.set(f, i * 486));
      const out = await session.run({ planes: new ort.Tensor("float32", x, [list.length, 6, 9, 9]) });
      return list.map((_, i) => ({ logits: out.policy.data.subarray(i * 82, (i + 1) * 82), value: out.value.data[i] }));
    };
    postMessage({ type: "ready", status: "Trained network loaded" });
    // Helpers start in the background; searches switch to them once they load.
    startHelpers().then((helpers) => {
      if (helpers.length < 2) return;
      batchEvaluator = splitBetween(helpers);
      postMessage({ type: "ready", status: `Trained network loaded (searching on ${helpers.length} threads)` });
    });
  } catch (e) {
    postMessage({ type: "ready", status: "Could not load the network (" + e.message + ") — using a uniform policy" });
  }
})();

// Starts the helper workers; resolves to the ones that loaded the network.
async function startHelpers() {
  if (HELPERS < 2 || typeof Worker === "undefined") return [];
  const started = [];
  for (let i = 0; i < HELPERS; i++) {
    try { started.push(new Worker(`evalworker.js?v=${CODE_VERSION}`)); } catch { break; }
  }
  const ok = await Promise.all(started.map((w) => new Promise((resolve) => {
    const timer = setTimeout(() => resolve(false), 20000);
    w.onmessage = (e) => { if (e.data.type === "ready") { clearTimeout(timer); resolve(e.data.ok); } };
    w.onerror = () => { clearTimeout(timer); resolve(false); };
  })));
  const good = started.filter((w, i) => ok[i]);
  started.forEach((w, i) => { if (!ok[i]) w.terminate(); });
  let nextId = 1;
  for (const w of good) {
    w.pending = new Map();
    w.onmessage = (e) => { const r = w.pending.get(e.data.id); w.pending.delete(e.data.id); r(e.data); };
    w.run = (x, n) => new Promise((resolve) => { const id = nextId++; w.pending.set(id, resolve); w.postMessage({ id, x, n }, [x.buffer]); });
  }
  return good;
}

// A batch evaluator that splits each batch evenly between the helpers.
function splitBetween(helpers) {
  return async (list) => {
    const per = Math.ceil(list.length / helpers.length), jobs = [];
    for (let h = 0, start = 0; start < list.length; h++, start += per) {
      const part = list.slice(start, start + per), x = new Float32Array(part.length * 486);
      part.forEach((f, i) => x.set(f, i * 486));
      jobs.push(helpers[h].run(x, part.length));
    }
    const outs = await Promise.all(jobs), res = [];
    for (const o of outs) {
      for (let i = 0; i < o.value.length; i++) res.push({ logits: o.policy.subarray(i * 82, (i + 1) * 82), value: o.value[i] });
    }
    return res;
  };
}

async function runSearch({ id, position, sims }) {
  await ready;
  if (id !== current) return;
  const pos = Go.deserialize(position);
  if (!mcts) mcts = new MCTS(evaluator, pos, { passRule: true });
  mcts.evaluator = evaluator;
  mcts.batchEvaluator = batchEvaluator;
  mcts.batch = batchFor(sims);
  // (a search that started before the helpers loaded keeps the evaluator it began with)
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
