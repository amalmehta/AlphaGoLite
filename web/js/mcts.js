// PUCT tree search; same constants and first-play-urgency rule as
// trainer/alphago_lite/mcts.py and MacApp/Sources/GoEngine/MCTS.swift.
// evaluator(features) must return a Promise of { logits: Float32Array(82), value }.
(function (root) {
  "use strict";
  const Go = root.Go || require("./go.js");
  const C_PUCT = 1.5, FPU_REDUCTION = 0.25, N = 82;

  class Node {
    constructor(pos) {
      this.pos = pos;
      this.children = new Map();
      this.expanded = false;
      this.total = 0;
      this.netValue = 0;
    }

    expand(logits, value) {
      const legal = Go.legalMask(this.pos);
      let max = -Infinity;
      for (let i = 0; i < N; i++) if (legal[i]) max = Math.max(max, logits[i]);
      const prior = new Float64Array(N);
      let sum = 0;
      for (let i = 0; i < N; i++) if (legal[i]) { prior[i] = Math.exp(logits[i] - max); sum += prior[i]; }
      for (let i = 0; i < N; i++) prior[i] /= sum;
      this.legal = legal;
      this.prior = prior;
      this.visits = new Float64Array(N);
      this.valueSum = new Float64Array(N);
      this.netValue = value;
      this.expanded = true;
    }

    select() {
      let visitedPrior = 0;
      for (let i = 0; i < N; i++) if (this.visits[i] > 0) visitedPrior += this.prior[i];
      const fpu = this.netValue - FPU_REDUCTION * Math.sqrt(visitedPrior);
      const scale = C_PUCT * Math.sqrt(this.total + 1);
      let best = -1, bestScore = -Infinity;
      for (let i = 0; i < N; i++) {
        if (!this.legal[i]) continue;
        const n = this.visits[i];
        const q = n > 0 ? this.valueSum[i] / n : fpu;
        const s = q + this.prior[i] * scale / (1 + n);
        if (s > bestScore) { bestScore = s; best = i; }
      }
      return best;
    }

    q(m) { return this.visits[m] > 0 ? this.valueSum[m] / this.visits[m] : this.netValue; }

    meanValue() {
      let n = 0, w = 0;
      for (let i = 0; i < N; i++) { n += this.visits[i]; w += this.valueSum[i]; }
      return n > 0 ? w / n : this.netValue;
    }
  }

  class MCTS {
    constructor(evaluator, pos) {
      this.evaluator = evaluator;
      this.root = new Node(pos || Go.newPosition());
    }

    // Move the root to pos, keeping the subtree if pos is a direct child.
    advance(pos) {
      if (Go.sameState(this.root.pos, pos)) return;
      for (const child of this.root.children.values()) {
        if (Go.sameState(child.pos, pos)) { this.root = child; return; }
      }
      this.root = new Node(pos);
    }

    static terminalValue(pos) { return Go.winner(pos) === pos.toPlay ? 1 : -1; }

    // Runs `count` simulations. onProgress(snapshot) every `every` sims;
    // shouldStop() is checked between simulations.
    async search(count, { every = 40, shouldStop = () => false, onProgress = null } = {}) {
      const root = this.root;
      if (!root.expanded) {
        const out = await this.evaluator(Go.features(root.pos));
        root.expand(out.logits, out.value);
      }
      if (Go.isOver(root.pos)) return;
      for (let i = 0; i < count; i++) {
        if (shouldStop()) break;
        await this.simulate();
        if (onProgress && ((i + 1) % every === 0 || i === count - 1)) onProgress(this.snapshot());
      }
    }

    async simulate() {
      let node = this.root, value;
      const path = [];
      for (;;) {
        const a = node.select();
        path.push([node, a]);
        let child = node.children.get(a);
        if (!child) { child = new Node(Go.play(node.pos, a)); node.children.set(a, child); }
        if (Go.isOver(child.pos)) { value = MCTS.terminalValue(child.pos); break; }
        if (!child.expanded) {
          const out = await this.evaluator(Go.features(child.pos));
          child.expand(out.logits, out.value);
          value = out.value;
          break;
        }
        node = child;
      }
      for (let i = path.length - 1; i >= 0; i--) {
        const [n, a] = path[i];
        value = -value;
        n.visits[a] += 1;
        n.valueSum[a] += value;
        n.total += 1;
      }
    }

    snapshot(top = 8) {
      const r = this.root;
      const empty = new Array(N).fill(0);
      if (!r.expanded) {
        return { position: Go.serialize(r.pos), simulations: 0, visits: empty, prior: empty, winrate: 0.5, netWinrate: 0.5, topMoves: [], pv: [], bestMove: Go.PASS };
      }
      const order = [];
      for (let i = 0; i < N; i++) if (r.visits[i] > 0) order.push(i);
      order.sort((a, b) => r.visits[b] - r.visits[a]);
      const topMoves = order.slice(0, top).map(m => ({ move: m, visits: r.visits[m], prior: r.prior[m], winrate: (r.q(m) + 1) / 2 }));
      const pv = [];
      let node = r;
      while (node && node.expanded && pv.length < 10) {
        let best = -1;
        for (let i = 0; i < N; i++) if (node.visits[i] > 0 && (best < 0 || node.visits[i] > node.visits[best])) best = i;
        if (best < 0) break;
        pv.push(best);
        node = node.children.get(best);
      }
      return {
        position: Go.serialize(r.pos), simulations: r.total,
        visits: Array.from(r.visits), prior: Array.from(r.prior),
        winrate: (r.meanValue() + 1) / 2, netWinrate: (r.netValue + 1) / 2,
        topMoves, pv, bestMove: this.bestMove(),
      };
    }

    // Most-visited move, ties broken by prior.
    bestMove() {
      const r = this.root;
      if (!r.expanded) return Go.PASS;
      let best = Go.PASS;
      for (let i = 0; i < N; i++) {
        if (r.visits[i] > r.visits[best] || (r.visits[i] === r.visits[best] && r.prior[i] > r.prior[best])) best = i;
      }
      return best;
    }
  }

  // Uniform policy, zero value: used when the network can't load, and in tests.
  async function uniformEvaluator() { return { logits: new Float32Array(N), value: 0 }; }

  root.MCTS = MCTS;
  root.uniformEvaluator = uniformEvaluator;
  if (typeof module !== "undefined" && module.exports) module.exports = { MCTS, uniformEvaluator };
})(typeof self !== "undefined" ? self : globalThis);
