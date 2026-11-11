// Canvas Go board: grid, coordinates, stones, last-move marker, optional move
// numbers, search heat map, win rates, territory, dead stones and a ghost stone
// (on hover with a mouse; on phones the first tap shows it and a second tap on
// the same point plays). Mirrors MacApp/Sources/AlphaGoLite/BoardView.swift.
const WOOD = "#dbb373";
const STARS = [20, 24, 40, 56, 60];
const COLS = "ABCDEFGHJ";

export class Board {
  // onPreview(point|null) fires when a tap shows or clears the ghost stone.
  constructor(canvas, { onPlay = null, onPreview = null } = {}) {
    this.onPreview = onPreview;
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onPlay = onPlay;
    this.position = Go.newPosition();
    this.lastMove = null;
    this.overlay = {};
    this.interactive = false;
    this.hover = null;
    this.numbers = null;
    new ResizeObserver(() => this.draw()).observe(canvas);
    canvas.addEventListener("pointermove", (e) => {
      if (e.pointerType !== "mouse") return;
      const p = this.pointAt(e);
      this.touchPreview = false;
      if (p !== this.hover) { this.hover = p; this.draw(); }
    });
    canvas.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") { this.hover = null; this.draw(); } });
    canvas.addEventListener("pointerup", (e) => {
      const p = this.pointAt(e);
      if (!this.interactive || p === null || !Go.isLegal(this.position, p) || !this.onPlay) return;
      if (e.pointerType !== "mouse" && this.hover !== p) { // preview first, play on a second tap
        this.hover = p; this.touchPreview = true; this.draw();
        if (this.onPreview) this.onPreview(p);
        return;
      }
      this.hover = null;
      if (this.touchPreview && this.onPreview) this.onPreview(null);
      this.onPlay(p);
    });
  }

  // numbers: optional Map point -> move number, drawn on the stones.
  set({ position, lastMove = null, overlay = {}, interactive = false, numbers = null }) {
    if (position !== this.position && this.touchPreview && this.hover !== null) { // a tap preview is for one position
      this.hover = null;
      if (this.onPreview) this.onPreview(null);
    }
    this.position = position;
    this.lastMove = lastMove;
    this.overlay = overlay;
    this.interactive = interactive;
    this.numbers = numbers;
    this.canvas.style.cursor = interactive ? "pointer" : "default";
    this.draw();
  }

  geometry() {
    const side = this.canvas.clientWidth;
    return { side, cell: side / 10, origin: side / 10 };
  }

  pointAt(e) {
    const r = this.canvas.getBoundingClientRect();
    const { cell, origin } = this.geometry();
    const c = Math.round((e.clientX - r.left - origin) / cell), row = Math.round((e.clientY - r.top - origin) / cell);
    return c >= 0 && c < 9 && row >= 0 && row < 9 ? row * 9 + c : null;
  }

  draw() {
    const dpr = window.devicePixelRatio || 1;
    const { side, cell, origin } = this.geometry();
    if (!side) return;
    if (this.canvas.width !== Math.round(side * dpr)) {
      this.canvas.width = Math.round(side * dpr);
      this.canvas.height = Math.round(side * dpr);
    }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const xy = (m) => [origin + (m % 9) * cell, origin + Math.floor(m / 9) * cell];
    const pos = this.position, ov = this.overlay;

    ctx.clearRect(0, 0, side, side);
    ctx.fillStyle = WOOD;
    roundRect(ctx, 0, 0, side, side, side * 0.015);
    ctx.fill();

    ctx.strokeStyle = "rgba(0,0,0,0.75)";
    ctx.lineWidth = Math.max(1, cell * 0.02);
    ctx.beginPath();
    for (let i = 0; i < 9; i++) {
      const d = origin + i * cell;
      ctx.moveTo(origin, d); ctx.lineTo(origin + 8 * cell, d);
      ctx.moveTo(d, origin); ctx.lineTo(d, origin + 8 * cell);
    }
    ctx.stroke();
    ctx.fillStyle = "rgba(0,0,0,0.8)";
    for (const s of STARS) { const [x, y] = xy(s); disc(ctx, x, y, cell * 0.08); }

    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.font = `500 ${cell * 0.26}px -apple-system, system-ui, sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (let i = 0; i < 9; i++) {
      const d = origin + i * cell;
      ctx.fillText(COLS[i], d, origin - cell * 0.62);
      ctx.fillText(COLS[i], d, origin + 8 * cell + cell * 0.62);
      ctx.fillText(String(9 - i), origin - cell * 0.62, d);
      ctx.fillText(String(9 - i), origin + 8 * cell + cell * 0.62, d);
    }

    if (ov.ownership) {
      for (let p = 0; p < 81; p++) {
        if (pos.board[p] !== 0 || ov.ownership[p] === 0) continue;
        const [x, y] = xy(p);
        ctx.fillStyle = ov.ownership[p] === 1 ? "rgba(0,0,0,0.8)" : "rgba(255,255,255,0.9)";
        ctx.fillRect(x - cell * 0.15, y - cell * 0.15, cell * 0.3, cell * 0.3);
      }
    }

    if (ov.visits) {
      let max = 0;
      for (let p = 0; p < 81; p++) max = Math.max(max, ov.visits[p]);
      if (max > 0) {
        for (let p = 0; p < 81; p++) {
          if (ov.visits[p] <= 0 || pos.board[p] !== 0) continue;
          const f = ov.visits[p] / max, [x, y] = xy(p);
          const rgb = p === ov.bestMove ? "26,140,242" : "51,115,230";
          ctx.fillStyle = `rgba(${rgb},${0.25 + 0.6 * f})`;
          disc(ctx, x, y, cell * (0.18 + 0.27 * Math.sqrt(f)));
        }
      }
    }

    const dead = new Set(ov.dead || []);
    for (let p = 0; p < 81; p++) {
      if (pos.board[p] === 0) continue;
      const [x, y] = xy(p);
      stone(ctx, x, y, cell, pos.board[p] === 1, dead.has(p) ? 0.45 : 1);
      if (dead.has(p)) { // a cross in the owner's colour marks it as dead
        ctx.strokeStyle = pos.board[p] === 1 ? "rgba(255,255,255,0.95)" : "rgba(0,0,0,0.85)";
        ctx.lineWidth = Math.max(1.5, cell * 0.06);
        const d = cell * 0.17;
        ctx.beginPath(); ctx.moveTo(x - d, y - d); ctx.lineTo(x + d, y + d); ctx.moveTo(x + d, y - d); ctx.lineTo(x - d, y + d); ctx.stroke();
      }
    }
    if (this.numbers) {
      ctx.font = `600 ${cell * 0.32}px -apple-system, system-ui, sans-serif`;
      for (const [p, n] of this.numbers) {
        if (pos.board[p] === 0 || dead.has(p)) continue;
        const last = p === this.lastMove;
        ctx.fillStyle = last ? "#e5484d" : pos.board[p] === 1 ? "#fff" : "#000";
        ctx.fillText(String(n), ...xy(p));
      }
    }
    if (!this.numbers && this.lastMove !== null && this.lastMove < 81 && pos.board[this.lastMove] !== 0) {
      const [x, y] = xy(this.lastMove);
      ctx.strokeStyle = pos.board[this.lastMove] === 1 ? "#fff" : "#000";
      ctx.lineWidth = Math.max(1.5, cell * 0.05);
      ctx.beginPath(); ctx.arc(x, y, cell * 0.2, 0, Math.PI * 2); ctx.stroke();
    }

    if (ov.winrates) {
      ctx.fillStyle = "#fff";
      ctx.font = `700 ${cell * 0.26}px -apple-system, system-ui, sans-serif`;
      for (const [m, w] of ov.winrates) {
        if (m < 81 && pos.board[m] === 0) ctx.fillText(String(Math.round(w * 100)), ...xy(m));
      }
    }

    if (this.interactive && this.hover !== null && pos.board[this.hover] === 0 && Go.isLegal(pos, this.hover)) {
      stone(ctx, ...xy(this.hover), cell, pos.toPlay === 1, 0.4);
    }
  }
}

function disc(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); }

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

function stone(ctx, x, y, cell, black, alpha) {
  const r = cell * 0.47;
  ctx.save();
  ctx.globalAlpha = alpha;
  if (alpha === 1) {
    ctx.shadowColor = "rgba(0,0,0,0.35)"; ctx.shadowBlur = cell * 0.1;
    ctx.shadowOffsetX = cell * 0.03; ctx.shadowOffsetY = cell * 0.04;
  }
  const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.35, 0, x - r * 0.35, y - r * 0.35, r * 1.6);
  if (black) { g.addColorStop(0, "#737373"); g.addColorStop(1, "#0d0d0d"); }
  else { g.addColorStop(0, "#ffffff"); g.addColorStop(1, "#c7c7c7"); }
  ctx.fillStyle = g;
  disc(ctx, x, y, r);
  ctx.restore();
}
