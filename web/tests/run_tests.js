// Node tests for the browser engine:  node web/tests/run_tests.js
// Replays the Python-generated parity vectors (shared with the Swift tests) and
// checks the search finds a game-winning pass.
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const Go = require("../js/go.js");
const { MCTS, uniformEvaluator } = require("../js/mcts.js");

let passed = 0;
async function test(name, fn) {
  await fn();
  passed++;
  console.log("ok -", name);
}

(async () => {
  await test("parity with Python rules", () => {
    const file = path.join(__dirname, "../../MacApp/Tests/GoEngineTests/test_vectors.json");
    const { cases } = JSON.parse(fs.readFileSync(file, "utf8"));
    assert(cases.length > 100);
    cases.forEach((c, i) => {
      let pos = Go.newPosition();
      for (const m of c.moves) {
        assert(Go.isLegal(pos, m), `case ${i}: illegal ${m}`);
        pos = Go.play(pos, m);
      }
      assert.deepStrictEqual(Array.from(pos.board), c.board, `case ${i} board`);
      assert.strictEqual(pos.ko, c.ko, `case ${i} ko`);
      assert.strictEqual(pos.toPlay, c.to_play, `case ${i} to play`);
      assert.deepStrictEqual(Array.from(Go.legalMask(pos)), c.legal, `case ${i} legal`);
      assert.strictEqual(Go.areaScore(pos), c.score, `case ${i} score`);
      const f = Go.features(pos);
      const sums = [0, 1, 2, 3, 4, 5].map(k => f.slice(k * 81, (k + 1) * 81).reduce((a, b) => a + b, 0));
      assert.deepStrictEqual(sums, c.features_sum, `case ${i} feature sums`);
      assert.strictEqual(f.reduce((a, v, j) => a + v * j, 0), c.features_hash, `case ${i} feature layout`);
    });
  });

  await test("ko and capture", () => {
    const pos = Go.newPosition();
    for (const p of [0, 10, 2]) pos.board[p] = 1;
    for (const p of [11, 3]) pos.board[p] = -1;
    pos.toPlay = Go.WHITE;
    const after = Go.play(pos, 1);
    assert.strictEqual(after.board[2], 0);
    assert.strictEqual(after.ko, 2);
    assert(!Go.isLegal(after, 2));
  });

  await test("search finds the winning pass", async () => {
    const pos = Go.newPosition();
    for (let r = 0; r < 9; r++) pos.board[r * 9 + 4] = 1;
    pos.passes = 1;
    const mcts = new MCTS(uniformEvaluator, pos);
    await mcts.search(300);
    assert.strictEqual(mcts.bestMove(), Go.PASS);
    assert.strictEqual(mcts.snapshot().simulations, 300);
  });

  await test("tree reuse keeps the subtree", async () => {
    const mcts = new MCTS(uniformEvaluator, Go.newPosition());
    await mcts.search(200);
    const m = mcts.bestMove();
    const next = Go.play(Go.newPosition(), m);
    const before = mcts.root.children.get(m).total;
    mcts.advance(next);
    assert.strictEqual(mcts.root.total, before);
  });

  console.log(`${passed} tests passed`);
})().catch(e => { console.error(e); process.exit(1); });
