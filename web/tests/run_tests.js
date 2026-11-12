// Node tests for the browser engine:  node web/tests/run_tests.js
// Replays the Python-generated parity vectors (shared with the Swift tests) and
// checks the search finds a game-winning pass. searchMask (the pass rule) was\n// also cross-checked against Python's search_mask on 3,000 random positions.
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const Go = require("../js/go.js");
const { MCTS, uniformEvaluator, uniformBatchEvaluator } = require("../js/mcts.js");

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

  await test("batched search finds the winning pass and undoes its virtual losses", async () => {
    const pos = Go.newPosition();
    for (let r = 0; r < 9; r++) pos.board[r * 9 + 4] = 1;
    pos.passes = 1;
    const mcts = new MCTS(uniformEvaluator, pos, { batchEvaluator: uniformBatchEvaluator, batch: 8 });
    await mcts.search(300);
    assert.strictEqual(mcts.bestMove(), Go.PASS);
    assert.strictEqual(mcts.snapshot().simulations, 300);
    const check = (node) => {
      if (!node.expanded) return;
      const v = node.visits.reduce((a, b) => a + b, 0);
      assert.strictEqual(v, node.total, "visits add up to the node total");
      for (let i = 0; i < 82; i++) assert(node.visits[i] >= 0 && Math.abs(node.valueSum[i]) <= node.visits[i] + 1e-9);
      for (const c of node.children.values()) { assert(!c.pending); check(c); }
    };
    check(mcts.root);
  });

  await test("batched search spreads a batch over different leaves", async () => {
    let calls = 0, sizes = 0;
    const be = async (list) => { calls++; sizes += list.length; return uniformBatchEvaluator(list); };
    const mcts = new MCTS(uniformEvaluator, Go.newPosition(), { batchEvaluator: be, batch: 8 });
    await mcts.search(400);
    assert.strictEqual(mcts.root.total, 400);
    assert(sizes / calls > 6, `average batch ${sizes / calls}`);
  });

  const fromRows = (rows, toPlay = Go.BLACK) => {
    const pos = Go.newPosition();
    rows.forEach((r, i) => [...r].forEach((ch, j) => { pos.board[i * 9 + j] = ch === "X" ? 1 : ch === "O" ? -1 : 0; }));
    pos.toPlay = toPlay;
    return pos;
  };
  const names = (ps) => ps.map(Go.moveName).sort().join(",");

  await test("scoring removes lone dead stones in the opponent's area", () => {
    // Black owns A-E (wall on E), White owns G-J (wall on G); column F is neutral.
    // C7 (white) and J2 (black) sit alone in the other side's area.
    const pos = fromRows(["....X.O..", "....X.O..", "..O.X.O..", "....X.O..", "....X.O..",
                          "....X.O..", "....X.O..", "....X.O.X", "....X.O.."]);
    assert.strictEqual(Go.areaScore(pos), -7.5); // Tromp-Taylor counts both as alive
    const r = Go.scoreWithDeadRemoved(pos);
    assert.strictEqual(names(r.dead), "C7,J2");
    assert.strictEqual(r.score, 45 - 27 - 7.5); // black A-E, white G-J, komi
    assert.strictEqual(r.board[20], 0);
  });

  await test("scoring removes a dead corner group but keeps the stone that kills it", () => {
    const pos = fromRows(["OO..X.O..", "OX..X.O..", "....X.O..", "....X.O..", "....X.O..",
                          "....X.O..", "....X.O..", "....X.O..", "....X.O.."]);
    const r = Go.scoreWithDeadRemoved(pos);
    assert.strictEqual(names(r.dead), "A8,A9,B9");
    assert.strictEqual(r.score, 10.5);
  });

  await test("scoring leaves a settled board unchanged and is repeatable", () => {
    const pos = fromRows(Array(9).fill("...XO...."));
    const r = Go.scoreWithDeadRemoved(pos);
    assert.deepStrictEqual(r.dead, []);
    assert.strictEqual(r.score, Go.areaScore(pos));
    const again = Go.scoreWithDeadRemoved(pos);
    assert.deepStrictEqual(Array.from(again.ownership), Array.from(r.ownership));
  });

  await test("scoring keeps a two-eyed group in the opponent's area alive", () => {
    // white has two separate eyes (H9, J8) in the top-right corner, inside black's side
    const pos = fromRows(["XXXXXXO.O", "XXXXXXOO.", "XXXXXXXOO", "XXXXXXXXX", "XXXXXXXXX",
                          "XXXXXXXXX", "XXXXXXXXX", "XXXXXXXX.", "XXXXXXX.X"]);
    const r = Go.scoreWithDeadRemoved(pos);
    assert.deepStrictEqual(r.dead, []);
  });

  await test("an empty board has nothing dead", () => {
    const r = Go.scoreWithDeadRemoved(Go.newPosition(), { playouts: 50 });
    assert.deepStrictEqual(r.dead, []);
  });

  await test("pass rule: no pass while there are moves worth playing", () => {
    const m = Go.searchMask(Go.newPosition());
    assert.strictEqual(m[Go.PASS], 0);
    assert.strictEqual(m.reduce((a, v) => a + v, 0), 81);
  });

  await test("pass rule: pass allowed once only own-eye fills are left", () => {
    // Black owns the left, white the right, each with two real eyes; the only
    // empty points are those eyes, so neither side has a worthwhile move.
    const rows = ["X.XXOO.OO", "XXXXOOOOO", "XXXXOOOOO", "XXXXOOOOO", "XXXXOOOOO",
                  "XXXXOOOOO", "XXXXOOOOO", "XXXXOOOOO", "X.XXOO.OO"];
    assert.strictEqual(Go.searchMask(fromRows(rows, Go.BLACK))[Go.PASS], 1);
    assert.strictEqual(Go.searchMask(fromRows(rows, Go.WHITE))[Go.PASS], 1);
  });

  await test("pass rule: pass back allowed only when ahead on the board", () => {
    const pos = fromRows(Array(9).fill("...XO...."));
    pos.passes = 1;
    pos.toPlay = Go.BLACK;  // the board is even, so black loses by komi: keep playing
    assert.strictEqual(Go.searchMask(pos)[Go.PASS], 0);
    pos.toPlay = Go.WHITE;  // white wins by komi: may pass back
    assert.strictEqual(Go.searchMask(pos)[Go.PASS], 1);
  });

  await test("search with the pass rule never passes on an open board", async () => {
    const pos = Go.newPosition();
    pos.passes = 1;  // black to play, behind by komi
    const mcts = new MCTS(uniformEvaluator, pos, { passRule: true, batchEvaluator: uniformBatchEvaluator, batch: 8 });
    await mcts.search(200);
    assert.strictEqual(mcts.root.visits[Go.PASS], 0);
    assert.notStrictEqual(mcts.bestMove(), Go.PASS);
  });

  console.log(`${passed} tests passed`);
})().catch(e => { console.error(e); process.exit(1); });
