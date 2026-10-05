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
    newPosition, isOver, legalMask, isLegal, play, areaScore, ownership, winner, features,
    sameState, moveName, resultString, colorName, serialize, deserialize,
  };
  root.Go = Go;
  if (typeof module !== "undefined" && module.exports) module.exports = Go;
})(typeof self !== "undefined" ? self : globalThis);
