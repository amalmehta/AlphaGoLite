// 9x9 Go rules: simple ko, no suicide, Tromp-Taylor area scoring.
// Mirrors trainer/alphago_lite/go.py and MacApp/Sources/GoEngine/Go.swift;
// web/tests/run_tests.js checks parity against the Python test vectors.
// Classic script: works in the page, in the search worker and in Node.
(function (root) {
  "use strict";
  const SIZE = 9, POINTS = 81, PASS = 81, NUM_MOVES = 82, KOMI = 7.5, MAX_MOVES = 162, PLANES = 6;
  const BLACK = 1, WHITE = -1;
  const COLUMNS = "ABCDEFGHJ";

  const NEIGHBORS = [];
  for (let p = 0; p < POINTS; p++) {
    const r = Math.floor(p / 9), c = p % 9, n = [];
    if (r > 0) n.push(p - 9);
    if (r < 8) n.push(p + 9);
    if (c > 0) n.push(p - 1);
    if (c < 8) n.push(p + 1);
    NEIGHBORS.push(n);
  }

  function newPosition() {
    return { board: new Int8Array(POINTS), prev: new Int8Array(POINTS), toPlay: BLACK, ko: -1, passes: 0, moveCount: 0 };
  }

  function isOver(pos) { return pos.passes >= 2 || pos.moveCount >= MAX_MOVES; }

  function group(b, p) {
    const color = b[p], seen = new Set([p]), stones = [p], libs = new Set(), stack = [p];
    while (stack.length) {
      const q = stack.pop();
      for (const n of NEIGHBORS[q]) {
        const v = b[n];
        if (v === 0) libs.add(n);
        else if (v === color && !seen.has(n)) { seen.add(n); stones.push(n); stack.push(n); }
      }
    }
    return { stones, libs };
  }

  function legalMask(pos) {
    const b = pos.board, me = pos.toPlay;
    const gid = new Int16Array(POINTS).fill(-1), libCount = [];
    for (let p = 0; p < POINTS; p++) {
      if (b[p] === 0 || gid[p] >= 0) continue;
      const color = b[p], g = libCount.length, stack = [p], libs = new Set();
      gid[p] = g;
      while (stack.length) {
        const q = stack.pop();
        for (const n of NEIGHBORS[q]) {
          const v = b[n];
          if (v === 0) libs.add(n);
          else if (v === color && gid[n] < 0) { gid[n] = g; stack.push(n); }
        }
      }
      libCount.push(libs.size);
    }
    const mask = new Uint8Array(NUM_MOVES);
    mask[PASS] = 1;
    for (let p = 0; p < POINTS; p++) {
      if (b[p] !== 0 || p === pos.ko) continue;
      for (const n of NEIGHBORS[p]) {
        const v = b[n];
        if (v === 0) { mask[p] = 1; break; }
        const lc = libCount[gid[n]];
        if ((v === me && lc > 1) || (v === -me && lc === 1)) { mask[p] = 1; break; }
      }
    }
    return mask;
  }

  const DIAGONALS = [];
  for (let p = 0; p < POINTS; p++) {
    const r = Math.floor(p / 9), c = p % 9, d = [];
    for (const dr of [-1, 1]) for (const dc of [-1, 1]) {
      if (r + dr >= 0 && r + dr < 9 && c + dc >= 0 && c + dc < 9) d.push((r + dr) * 9 + c + dc);
    }
    DIAGONALS.push(d);
  }

  // legalMask, except that passing is only allowed when every legal move would
  // fill one of our own real eyes or put our own stones in atari, or when the
  // opponent just passed and we already win on the board. The network was
  // trained with this rule (trainer/alphago_lite/go.py Position.search_mask),
  // so the search plays games out until dead stones are captured.
  function searchMask(pos) {
    const b = pos.board, me = pos.toPlay;
    const gid = new Int16Array(POINTS).fill(-1), libsets = [];
    for (let p = 0; p < POINTS; p++) {
      if (b[p] === 0 || gid[p] >= 0) continue;
      const color = b[p], g = libsets.length, stack = [p], libs = new Set();
      gid[p] = g;
      while (stack.length) {
        const q = stack.pop();
        for (const n of NEIGHBORS[q]) {
          const v = b[n];
          if (v === 0) libs.add(n);
          else if (v === color && gid[n] < 0) { gid[n] = g; stack.push(n); }
        }
      }
      libsets.push(libs);
    }
    const mask = new Uint8Array(NUM_MOVES);
    mask[PASS] = 1;
    let worthwhile = false;
    for (let p = 0; p < POINTS; p++) {
      if (b[p] !== 0 || p === pos.ko) continue;
      let legal = false, captures = false, ownEye = true;
      const libs = new Set();
      for (const n of NEIGHBORS[p]) {
        const v = b[n];
        if (v === 0) { legal = true; ownEye = false; libs.add(n); }
        else if (v === me) {
          const ls = libsets[gid[n]];
          if (ls.size > 1) legal = true;
          for (const l of ls) libs.add(l);
        } else {
          ownEye = false;
          if (libsets[gid[n]].size === 1) legal = captures = true;
        }
      }
      if (!legal) continue;
      mask[p] = 1;
      if (worthwhile) continue;
      if (ownEye) {
        const diag = DIAGONALS[p];
        let bad = 0;
        for (const d of diag) if (b[d] === -me) bad++;
        if (bad === 0 || (diag.length === 4 && bad === 1)) continue; // filling a real eye
      }
      libs.delete(p);
      if (captures || libs.size >= 2) worthwhile = true;
    }
    if (worthwhile && !(pos.passes === 1 && areaScore(pos) * me > 0)) mask[PASS] = 0;
    return mask;
  }

  function isLegal(pos, m) { return m === PASS || (m >= 0 && m < POINTS && legalMask(pos)[m] === 1); }

  function play(pos, m) {
    const me = pos.toPlay;
    if (m === PASS) {
      return { board: pos.board, prev: pos.board, toPlay: -me, ko: -1, passes: pos.passes + 1, moveCount: pos.moveCount + 1 };
    }
    const b = pos.board.slice();
    b[m] = me;
    const captured = [];
    for (const n of NEIGHBORS[m]) {
      if (b[n] !== -me) continue;
      const g = group(b, n);
      if (g.libs.size === 0) { for (const s of g.stones) b[s] = 0; captured.push(...g.stones); }
    }
    const own = group(b, m);
    if (own.libs.size === 0) throw new Error("suicide at " + m);
    const ko = captured.length === 1 && own.stones.length === 1 && own.libs.size === 1 ? captured[0] : -1;
    return { board: b, prev: pos.board, toPlay: -me, ko, passes: 0, moveCount: pos.moveCount + 1 };
  }

  // Empty regions bordered by one color only; calls fn(region, color).
  function regions(b, fn) {
    const seen = new Uint8Array(POINTS);
    for (let p = 0; p < POINTS; p++) {
      if (b[p] !== 0 || seen[p]) continue;
      seen[p] = 1;
      const region = [p], stack = [p], borders = new Set();
      while (stack.length) {
        const q = stack.pop();
        for (const n of NEIGHBORS[q]) {
          const w = b[n];
          if (w === 0) { if (!seen[n]) { seen[n] = 1; region.push(n); stack.push(n); } }
          else borders.add(w);
        }
      }
      if (borders.size === 1) fn(region, borders.values().next().value);
    }
  }

  function areaScore(pos) {
    let score = 0;
    for (let p = 0; p < POINTS; p++) score += pos.board[p];
    regions(pos.board, (region, color) => { score += region.length * color; });
    return score - KOMI;
  }

  function ownership(pos) {
    const own = Int8Array.from(pos.board);
    regions(pos.board, (region, color) => { for (const r of region) own[r] = color; });
    return own;
  }

  function winner(pos) { return areaScore(pos) > 0 ? BLACK : WHITE; }

  // ---- dead-stone estimate for the final count (Play tab only; the engine,
  // trainer and Mac app still score by Tromp-Taylor) -------------------------

  function rng32(seed) { // mulberry32: small seeded generator, so results are repeatable
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Can `me` play at empty point p? Also false for filling a point whose four
  // neighbours are all `me` (an eye), which random playouts never do.
  function playoutMoveOk(b, p, me, ko, mark) {
    if (p === ko) return false;
    let eye = true;
    for (const n of NEIGHBORS[p]) if (b[n] !== me) { eye = false; break; }
    if (eye) return false;
    for (const n of NEIGHBORS[p]) {
      const v = b[n];
      if (v === 0) return true;
      const many = libsAtLeast2(b, n, mark);
      if ((v === me && many) || (v === -me && !many)) return true;
    }
    return false;
  }

  function libsAtLeast1(b, p, mark) {
    const stamp = ++mark[POINTS], color = b[p], stack = [p];
    mark[p] = stamp;
    while (stack.length) {
      const q = stack.pop();
      for (const n of NEIGHBORS[q]) {
        const v = b[n];
        if (v === 0) return true;
        if (v === color && mark[n] !== stamp) { mark[n] = stamp; stack.push(n); }
      }
    }
    return false;
  }

  // Does the group at p have two or more liberties? Stops at the second one.
  // `mark` is scratch space (Int32Array(POINTS + 1)); mark[POINTS] is the stamp.
  function libsAtLeast2(b, p, mark) {
    const stamp = ++mark[POINTS], color = b[p], stack = [p];
    mark[p] = stamp;
    let lib = -1;
    while (stack.length) {
      const q = stack.pop();
      for (const n of NEIGHBORS[q]) {
        if (mark[n] === stamp) continue;
        const v = b[n];
        if (v === 0) { if (lib >= 0 && lib !== n) return true; lib = n; }
        else if (v === color) { mark[n] = stamp; stack.push(n); }
      }
    }
    return false;
  }

  // Plays `playouts` random games to the end from pos and returns, per point,
  // the average final owner (+1 black ... -1 white).
  function playoutOwnership(pos, playouts, rand) {
    const sum = new Float64Array(POINTS), mark = new Int32Array(POINTS + 1);
    const cand = new Int16Array(POINTS), stack = [];
    for (let k = 0; k < playouts; k++) {
      const b = pos.board.slice();
      let me = pos.toPlay, ko = pos.ko, passes = 0;
      for (let moves = 0; moves < 3 * POINTS && passes < 2; moves++) {
        // uniform over the allowed moves: draw empty points at random, dropping bad ones
        let n = 0;
        for (let p = 0; p < POINTS; p++) if (b[p] === 0) cand[n++] = p;
        let m = PASS;
        while (n > 0) {
          const i = Math.floor(rand() * n), p = cand[i];
          if (playoutMoveOk(b, p, me, ko, mark)) { m = p; break; }
          cand[i] = cand[--n];
        }
        if (m === PASS) { passes++; ko = -1; me = -me; continue; }
        passes = 0;
        b[m] = me;
        let captured = 0, capturedAt = -1;
        for (const nb of NEIGHBORS[m]) {
          if (b[nb] !== -me || libsAtLeast1(b, nb, mark)) continue;
          // remove the captured group
          stack.push(nb); b[nb] = 0;
          while (stack.length) {
            const q = stack.pop();
            captured++; capturedAt = q;
            for (const r of NEIGHBORS[q]) if (b[r] === -me) { b[r] = 0; stack.push(r); }
          }
        }
        ko = -1;
        if (captured === 1) {
          let lonely = true, libs = 0;
          for (const nb of NEIGHBORS[m]) { if (b[nb] === me) lonely = false; else if (b[nb] === 0) libs++; }
          if (lonely && libs === 1) ko = capturedAt;
        }
        me = -me;
      }
      regions(b, (region, color) => { for (const r of region) b[r] = color; });
      for (let i = 0; i < POINTS; i++) sum[i] += b[i];
    }
    for (let i = 0; i < POINTS; i++) sum[i] /= playouts;
    return sum;
  }

  // Estimates which stones are dead at the end of a game and scores the board
  // with them removed. A group counts as dead when the opponent owns its points
  // in at least `threshold` of the random playouts (default 60%), which leaves
  // seki and unclear fights on the board. An estimate, not an agreement between
  // players: it can misjudge unsettled positions.
  function scoreWithDeadRemoved(pos, { playouts = 300, seed = 1, threshold = 0.6 } = {}) {
    const avg = playoutOwnership(pos, playouts, rng32(seed));
    const dead = [], seen = new Uint8Array(POINTS);
    for (let p = 0; p < POINTS; p++) {
      const c = pos.board[p];
      if (c === 0 || seen[p]) continue;
      const { stones } = group(pos.board, p);
      let s = 0;
      for (const q of stones) { seen[q] = 1; s += avg[q] * c; }
      // mean of own*color is 1 - 2 * (share of playouts the opponent owns it)
      if (s / stones.length <= 1 - 2 * threshold) dead.push(...stones);
    }
    const board = pos.board.slice();
    for (const p of dead) board[p] = 0;
    const cleaned = { board, prev: board, toPlay: pos.toPlay, ko: -1, passes: 0, moveCount: pos.moveCount };
    return { score: areaScore(cleaned), dead, ownership: ownership(cleaned), board };
  }

  // 6x9x9 planes from the point of view of the player to move.
  function features(pos) {
    const me = pos.toPlay, f = new Float32Array(PLANES * POINTS);
    const bt = me === BLACK ? 1 : 0;
    for (let p = 0; p < POINTS; p++) {
      const v = pos.board[p], pv = pos.prev[p];
      if (v === me) f[p] = 1; else if (v === -me) f[81 + p] = 1;
      if (pv === me) f[162 + p] = 1; else if (pv === -me) f[243 + p] = 1;
      f[324 + p] = bt;
      f[405 + p] = 1;
    }
    return f;
  }

  function sameState(a, b) {
    if (a.toPlay !== b.toPlay || a.ko !== b.ko || a.passes !== b.passes || a.moveCount !== b.moveCount) return false;
    for (let i = 0; i < POINTS; i++) if (a.board[i] !== b.board[i] || a.prev[i] !== b.prev[i]) return false;
    return true;
  }

  function moveName(m) { return m === PASS ? "pass" : COLUMNS[m % 9] + (9 - Math.floor(m / 9)); }
  function resultString(score) { return (score > 0 ? "B+" : "W+") + Math.abs(score); }
  function colorName(c) { return c === BLACK ? "Black" : "White"; }

  // Plain-array form for postMessage.
  function serialize(pos) {
    return { board: Array.from(pos.board), prev: Array.from(pos.prev), toPlay: pos.toPlay, ko: pos.ko, passes: pos.passes, moveCount: pos.moveCount };
  }
  function deserialize(o) {
    return { board: Int8Array.from(o.board), prev: Int8Array.from(o.prev), toPlay: o.toPlay, ko: o.ko, passes: o.passes, moveCount: o.moveCount };
  }

  const Go = {
    SIZE, POINTS, PASS, NUM_MOVES, KOMI, MAX_MOVES, PLANES, BLACK, WHITE, NEIGHBORS,
    newPosition, isOver, legalMask, searchMask, isLegal, play, areaScore, ownership, winner, features, scoreWithDeadRemoved,
    sameState, moveName, resultString, colorName, serialize, deserialize,
  };
  root.Go = Go;
  if (typeof module !== "undefined" && module.exports) module.exports = Go;
})(typeof self !== "undefined" ? self : globalThis);
