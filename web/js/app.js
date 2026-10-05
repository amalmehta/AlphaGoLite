// AlphaGo Lite website: Play, AI vs AI and Training tabs plus a feedback tab.
// The engine (network + MCTS) runs in js/worker.js; the rules in js/go.js.
import { Board } from "./board.js";

const REPO = "https://github.com/amalmehta/AlphaGoLite";
const $ = (id) => document.getElementById(id);
const pct = (x) => Math.round(x * 100);

// ---------------------------------------------------------------- engine

class Engine {
  constructor(onStatus) {
    this.worker = new Worker("js/worker.js");
    this.nextId = 1;
    this.handlers = new Map();
    this.worker.onmessage = (e) => {
      const m = e.data;
      if (m.type === "ready") return onStatus && onStatus(m.status);
      const h = this.handlers.get(m.id);
      if (!h) return;
      m.snap.pos = Go.deserialize(m.snap.position);
      if (m.type === "progress") h.progress(m.snap);
      else { this.handlers.delete(m.id); h.done(m.snap); }
    };
  }

  search(pos, sims, progress, done) {
    this.handlers.clear();
    const id = this.nextId++;
    this.handlers.set(id, { progress, done });
    this.worker.postMessage({ type: "search", id, position: Go.serialize(pos), sims });
  }

  cancel() { this.handlers.clear(); this.worker.postMessage({ type: "cancel" }); }
  reset() { this.handlers.clear(); this.worker.postMessage({ type: "reset" }); }
}

// ---------------------------------------------------------------- charts

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function chart(canvas, config) {
  const grid = css("--line"), text = css("--muted");
  Chart.defaults.color = text;
  Chart.defaults.font.family = "-apple-system, system-ui, sans-serif";
  config.options = Object.assign({ responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { display: false } } }, config.options || {});
  for (const axis of Object.values(config.options.scales || {})) {
    axis.grid = Object.assign({ color: grid }, axis.grid || {});
  }
  return new Chart(canvas, config);
}

// ---------------------------------------------------------------- tabs

function showTab(name) {
  for (const b of document.querySelectorAll("nav button")) b.setAttribute("aria-selected", b.dataset.tab === name);
  for (const s of document.querySelectorAll(".tab")) s.hidden = s.id !== name;
  if (name !== "watch") watch.stopPlayback();
  if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
  window.dispatchEvent(new Event("resize"));
}

// ---------------------------------------------------------------- play

class Play {
  constructor() {
    this.engine = new Engine((s) => { $("model-status").textContent = s; });
    this.board = new Board($("play-board"), { onPlay: (m) => this.humanPlay(m) });
    this.wrChart = chart($("wr-chart"), {
      type: "line",
      data: { datasets: [{ data: [], borderColor: css("--accent"), backgroundColor: "rgba(47,111,219,0.15)", fill: true, pointRadius: 0, tension: 0.2 }] },
      options: { scales: { x: { type: "linear", ticks: { precision: 0 } }, y: { min: 0, max: 100 } } },
    });
    $("new-black").onclick = () => this.newGame(Go.BLACK);
    $("new-white").onclick = () => this.newGame(Go.WHITE);
    $("pass").onclick = () => this.humanPlay(Go.PASS);
    $("undo").onclick = () => this.undo();
    $("resign").onclick = () => this.resign();
    $("thinking").onchange = () => { $("thinking").checked ? this.analyze() : this.stopAnalysis(); this.render(); };
    this.newGame(Go.BLACK);
  }

  get sims() { return Number($("strength").value); }
  get isOver() { return Go.isOver(this.pos) || this.resigned !== null; }
  get isHumanTurn() { return !this.isOver && this.pos.toPlay === this.human; }
  get showThinking() { return $("thinking").checked; }

  newGame(color) {
    this.engine.reset();
    this.human = color;
    this.pos = Go.newPosition();
    this.history = [];
    this.moves = [];
    this.snap = null;
    this.resigned = null;
    this.winrates = new Map();
    this.thinking = false;
    if (color === Go.WHITE) this.aiMove(); else this.analyze();
    this.render();
  }

  humanPlay(m) {
    if (!this.isHumanTurn || !Go.isLegal(this.pos, m)) return;
    this.stopAnalysis();
    this.apply(m);
    this.aiMove();
    this.render();
  }

  resign() {
    if (this.isOver) return;
    this.engine.cancel();
    this.thinking = false;
    this.resigned = this.human;
    this.render();
  }

  undo() {
    if (!this.history.length) return;
    this.engine.reset();
    this.thinking = false;
    this.resigned = null;
    do {
      this.pos = this.history.pop();
      this.winrates.delete(this.moves.length);
      this.moves.pop();
    } while (this.pos.toPlay !== this.human && this.history.length);
    this.snap = null;
    if (this.pos.toPlay !== this.human) this.aiMove(); else this.analyze();
    this.render();
  }

  apply(m) {
    this.history.push(this.pos);
    this.moves.push(m);
    this.pos = Go.play(this.pos, m);
    this.snap = null;
  }

  record(snap) {
    this.winrates.set(this.moves.length, snap.pos.toPlay === Go.BLACK ? snap.winrate : 1 - snap.winrate);
  }

  aiMove() {
    if (this.isOver || this.pos.toPlay === this.human) return;
    // If you passed and the engine already wins on the board as it stands, it passes too.
    if (this.moves[this.moves.length - 1] === Go.PASS) {
      const s = Go.areaScore(this.pos);
      if ((s > 0) === (this.pos.toPlay === Go.BLACK)) { this.apply(Go.PASS); return; }
    }
    this.thinking = true;
    this.engine.search(this.pos, this.sims,
      (snap) => { this.snap = snap; this.render(); },
      (snap) => {
        this.thinking = false;
        this.record(snap);
        this.apply(snap.bestMove);
        this.analyze();
        this.render();
      });
  }

  analyze() {
    if (!this.showThinking || !this.isHumanTurn) return;
    this.engine.search(this.pos, this.sims,
      (snap) => { this.snap = snap; this.render(); },
      (snap) => { this.snap = snap; this.record(snap); this.render(); });
  }

  stopAnalysis() { if (!this.thinking) this.engine.cancel(); }

  currentSnap() { return this.snap && Go.sameState(this.snap.pos, this.pos) ? this.snap : null; }

  status() {
    if (this.resigned !== null) return this.resigned === this.human ? "AlphaGo Lite wins by resignation" : "You win by resignation";
    if (Go.isOver(this.pos)) {
      const s = Go.areaScore(this.pos);
      return `${Go.resultString(s)} — ${(s > 0 ? Go.BLACK : Go.WHITE) === this.human ? "you win" : "AlphaGo Lite wins"}`;
    }
    if (this.thinking) return "AlphaGo Lite is thinking…";
    if (this.moves[this.moves.length - 1] === Go.PASS) return `${Go.colorName(-this.pos.toPlay)} passed — your move`;
    return this.isHumanTurn ? `Your move (${Go.colorName(this.human)})` : "";
  }

  render() {
    const snap = this.currentSnap();
    let overlay = {};
    if (this.isOver && this.resigned === null) overlay = { ownership: Go.ownership(this.pos) };
    else if (this.showThinking && snap) {
      const min = Math.max(3, snap.simulations / 50);
      overlay = { visits: snap.visits, bestMove: snap.bestMove,
        winrates: snap.topMoves.slice(0, 5).filter((m) => m.visits >= min).map((m) => [m.move, m.winrate]) };
    }
    this.board.set({ position: this.pos, lastMove: this.moves.length ? this.moves[this.moves.length - 1] : null,
      overlay, interactive: this.isHumanTurn });
    $("play-status").textContent = this.status();
    $("pass").disabled = !this.isHumanTurn;
    $("resign").disabled = this.isOver;
    $("undo").disabled = !this.moves.length;

    const black = snap ? (snap.pos.toPlay === Go.BLACK ? snap.winrate : 1 - snap.winrate)
      : this.winrates.get(this.moves.length) ?? 0.5;
    winbar($("winbar"), black);

    const a = $("analysis");
    if (this.showThinking && snap) {
      const rows = snap.topMoves.slice(0, 6).map((m) =>
        `<tr><td>${Go.moveName(m.move)}</td><td>${m.visits}</td><td>${(m.winrate * 100).toFixed(1)}</td><td>${(m.prior * 100).toFixed(1)}%</td></tr>`).join("");
      a.innerHTML = `
        <div class="stats"><span>${snap.simulations} simulations</span><span title="Value head's estimate before any search, for the player to move">Net alone: ${pct(snap.netWinrate)}%</span></div>
        <h3>Candidate moves (${Go.colorName(snap.pos.toPlay)})</h3>
        <table class="moves"><tr><th>Move</th><th>Visits</th><th>Win %</th><th>Prior</th></tr>${rows}</table>
        ${snap.pv.length ? `<p class="pv">Expected line: ${snap.pv.slice(0, 6).map(Go.moveName).join(" → ")}</p>` : ""}`;
    } else a.innerHTML = "";

    const pts = [...this.winrates.entries()].sort((x, y) => x[0] - y[0]).map(([x, y]) => ({ x, y: y * 100 }));
    $("wr-wrap").hidden = pts.length < 2;
    this.wrChart.data.datasets[0].data = pts;
    this.wrChart.update();
  }
}

function winbar(el, black) {
  el.querySelector(".black-part").style.width = `${black * 100}%`;
  el.querySelector(".b").textContent = `Black ${pct(black)}%`;
  el.querySelector(".w").textContent = `White ${100 - pct(black)}%`;
}

// ---------------------------------------------------------------- AI vs AI

class Watch {
  constructor() {
    this.games = [];
    this.selected = "live";
    this.board = new Board($("watch-board"));
    this.engine = null; // created on first live game
    this.step = 0;
    this.timer = null;
    this.liveRunning = false;
    this.chart = chart($("watch-chart"), {
      type: "line",
      data: { datasets: [
        { data: [], borderColor: css("--accent"), pointRadius: 0, borderWidth: 2 },
        { data: [], borderColor: "#e08a1e", pointRadius: 0, borderWidth: 2 },
      ] },
      options: { scales: { x: { type: "linear", ticks: { precision: 0 } }, y: { min: 0, max: 100, title: { display: true, text: "Black win %" } } } },
    });
    $("w-first").onclick = () => this.goto(0);
    $("w-prev").onclick = () => this.goto(this.step - 1);
    $("w-next").onclick = () => this.goto(this.step + 1);
    $("w-last").onclick = () => this.goto(this.maxStep);
    $("w-play").onclick = () => this.togglePlayback();
    $("w-slider").oninput = (e) => this.goto(Number(e.target.value));
    $("live-toggle").onclick = () => (this.liveRunning ? this.stopLive() : this.startLive());
    document.addEventListener("keydown", (e) => {
      if ($("watch").hidden || e.target.matches("input, textarea, select")) return;
      if (e.key === "ArrowLeft") this.goto(this.step - 1);
      else if (e.key === "ArrowRight") this.goto(this.step + 1);
      else if (e.key === " ") { e.preventDefault(); this.togglePlayback(); } else return;
    });
    fetch("data/games.json").then((r) => r.json()).then((d) => {
      this.games = d.games;
      this.select(this.games.length ? this.games[this.games.length - 1].title : "live");
    }).catch(() => this.select("live"));
  }

  get maxStep() { return this.positions.length - 1; }
  get isLive() { return this.selected === "live"; }

  select(id) {
    this.stopPlayback();
    this.stopLive();
    this.selected = id;
    this.game = this.isLive ? { title: "Live game", result: "", moves: [] } : this.games.find((g) => g.title === id);
    this.positions = [Go.newPosition()];
    for (const m of this.game.moves) this.positions.push(Go.play(this.positions[this.positions.length - 1], m.move));
    this.step = 0;
    this.renderList();
    this.render();
  }

  renderList() {
    const list = $("game-list");
    const item = (id, title, sub) =>
      `<button data-id="${id}" aria-current="${id === this.selected}">${title}${sub ? `<small>${sub}</small>` : ""}</button>`;
    list.innerHTML = `<h4>Live</h4>${item("live", "⚡ Live game", "")}<h4>Self-play games from training</h4>` +
      this.games.map((g) => item(g.title, g.title, `${g.result} · ${g.moves.length} moves`)).join("");
    for (const b of list.querySelectorAll("button")) b.onclick = () => this.select(b.dataset.id);
  }

  goto(s) { this.step = Math.max(0, Math.min(this.maxStep, s)); this.render(); }

  togglePlayback() {
    if (this.timer) return this.stopPlayback();
    if (this.step >= this.maxStep) this.step = 0;
    this.timer = setInterval(() => (this.step < this.maxStep ? this.goto(this.step + 1) : this.stopPlayback()), 600);
    this.render();
  }

  stopPlayback() { clearInterval(this.timer); this.timer = null; if (this.positions) this.render(); }

  startLive() {
    this.select("live");
    this.engine = this.engine || new Engine();
    this.engine.reset();
    this.liveRunning = true;
    this.nextLiveMove();
    this.render();
  }

  stopLive() {
    if (this.engine) this.engine.reset();
    this.liveRunning = false;
    this.liveSnap = null;
  }

  nextLiveMove() {
    const last = this.positions[this.positions.length - 1];
    if (!this.liveRunning || Go.isOver(last)) { this.liveRunning = false; return this.render(); }
    this.engine.search(last, Number($("live-strength").value),
      (snap) => { this.liveSnap = snap; this.render(); },
      (snap) => {
        if (!this.liveRunning) return;
        const black = (snap.pos.toPlay === Go.BLACK ? snap.winrate : 1 - snap.winrate) * 2 - 1;
        this.game.moves.push({ move: snap.bestMove, value: black, visits: snap.visits });
        const following = this.step === this.maxStep;
        this.positions.push(Go.play(last, snap.bestMove));
        if (following) this.step = this.maxStep;
        const end = this.positions[this.positions.length - 1];
        if (Go.isOver(end)) { this.game.result = Go.resultString(Go.areaScore(end)); this.liveRunning = false; }
        else this.nextLiveMove();
        this.render();
      });
  }

  render() {
    const pos = this.positions[this.step], g = this.game;
    let overlay = {};
    if (this.isLive && this.liveRunning && this.liveSnap && Go.sameState(this.liveSnap.pos, pos)) {
      overlay = { visits: this.liveSnap.visits, bestMove: this.liveSnap.bestMove };
    } else if (this.step < g.moves.length) {
      overlay = { visits: g.moves[this.step].visits, bestMove: g.moves[this.step].move };
    } else if (Go.isOver(pos)) overlay = { ownership: Go.ownership(pos) };
    this.board.set({ position: pos, lastMove: this.step > 0 ? g.moves[this.step - 1].move : null, overlay });

    let caption;
    if (this.step < g.moves.length) {
      const m = g.moves[this.step];
      caption = `Move ${this.step + 1}: ${Go.colorName(pos.toPlay)} plays ${Go.moveName(m.move)} — ${m.visits.reduce((a, b) => a + b, 0)} simulations`;
    } else if (Go.isOver(pos)) caption = `Final: ${Go.resultString(Go.areaScore(pos))}`;
    else caption = this.liveRunning ? "Thinking…" : (this.isLive ? "Pick a strength and start a game" : `Move ${this.step}`);
    $("watch-caption").textContent = caption;

    const slider = $("w-slider");
    slider.max = this.maxStep;
    slider.value = this.step;
    $("w-count").textContent = `${this.step}/${this.maxStep}`;
    $("w-play").textContent = this.timer ? "⏸" : "▶";
    $("w-play").setAttribute("aria-label", this.timer ? "Pause" : "Play");
    $("live-controls").hidden = !this.isLive;
    $("live-toggle").textContent = this.liveRunning ? "Stop" : "Start a new game";
    $("live-strength").disabled = this.liveRunning;

    this.chart.data.datasets[0].data = g.moves.map((m, i) => ({ x: i, y: ((m.value + 1) / 2) * 100 }));
    this.chart.data.datasets[1].data = [{ x: this.step, y: 0 }, { x: this.step, y: 100 }];
    this.chart.update();
  }
}

// ---------------------------------------------------------------- training

class Training {
  constructor() {
    this.charts = [];
    fetch("data/metrics.json").then((r) => r.json()).then((m) => this.render(m, "The training run behind the network on this site"))
      .catch(() => { $("tiles").textContent = "No training metrics found."; });
    $("metrics-file").onchange = async (e) => {
      const f = e.target.files[0];
      if (f) this.render(JSON.parse(await f.text()), f.name);
    };
  }

  render(m, source) {
    for (const c of this.charts) c.destroy();
    this.charts = [];
    const gens = m.generations, last = gens[gens.length - 1];
    const checks = (m.strength_checks || []).slice().sort((a, b) => a.vs - b.vs);
    const vs0 = checks.find((c) => c.vs === 0);
    const tile = (t, v) => `<div class="tile"><div class="t">${t}</div><div class="v">${v}</div></div>`;
    $("tiles").innerHTML = tile("Generations", last.gen) + tile("Self-play games", last.total_games.toLocaleString()) +
      tile("Training time", `${(last.elapsed_min / 60).toFixed(1)} h`) +
      (vs0 ? tile("Wins vs. random start", `${Math.floor((vs0.wins / vs0.games) * 100)}%`)
        : tile("Chained Elo", `${last.elo >= 0 ? "+" : ""}${Math.round(last.elo)}`));
    $("tiles").title = source;

    const accent = css("--accent");
    const line = (id, sets, opts = {}) => this.charts.push(chart($(id), {
      type: "line", data: { datasets: sets },
      options: Object.assign({ scales: { x: { type: "linear", ticks: { precision: 0 }, title: { display: true, text: "Generation" } }, y: {} } }, opts),
    }));
    $("h2h-chart").parentElement.parentElement.hidden = !checks.length;
    if (checks.length) {
      this.charts.push(chart($("h2h-chart"), {
        type: "bar",
        data: { labels: checks.map((c) => `vs. generation ${c.vs} (${c.wins}/${c.games} games)`),
          datasets: [{ data: checks.map((c) => (c.wins / c.games) * 100), backgroundColor: accent }] },
        options: { indexAxis: "y", scales: { x: { min: 0, max: 100, title: { display: true, text: "Win %" } }, y: {} } },
      }));
    }
    line("elo-chart", [{ data: gens.map((g) => ({ x: g.gen, y: g.elo })), borderColor: accent, pointRadius: 2 }]);
    const t = gens.filter((g) => g.policy_loss !== undefined);
    line("loss-chart", [
      { label: "Policy loss", data: t.map((g) => ({ x: g.gen, y: g.policy_loss })), borderColor: accent, pointRadius: 2 },
      { label: "Value loss", data: t.map((g) => ({ x: g.gen, y: g.value_loss })), borderColor: "#e08a1e", pointRadius: 2 },
    ], { plugins: { legend: { display: true } } });
    this.charts.push(chart($("prev-chart"), {
      type: "bar",
      data: { labels: t.map((g) => g.gen), datasets: [{ data: t.map((g) => g.winrate_vs_prev * 100), backgroundColor: accent }] },
      options: { scales: { x: { title: { display: true, text: "Generation" } }, y: { min: 0, max: 100 } } },
    }));
    line("len-chart", [{ data: t.map((g) => ({ x: g.gen, y: g.avg_game_length })), borderColor: accent, pointRadius: 2 }]);
    const c = m.config || {};
    $("config-note").textContent = `${source}. Settings: ${c.games_per_gen} games per generation, ${c.sims} simulations per full search, ${c.workers} self-play workers. Chained Elo measures each generation against the one before it; the head-to-head games are the more reliable measure.`;
  }
}

// ---------------------------------------------------------------- feedback

function setupFeedback() {
  const dlg = $("feedback");
  $("feedback-tab").onclick = () => dlg.showModal();
  dlg.addEventListener("close", () => {
    if (dlg.returnValue !== "send") return;
    const text = $("feedback-text").value.trim();
    if (!text) return;
    const kind = dlg.querySelector("input[name=kind]:checked").value;
    const title = `[${kind}] ${text.split("\n")[0].slice(0, 60)}`;
    const body = `${text}\n\n---\nSent from the AlphaGo Lite website (${navigator.userAgent})`;
    window.open(`${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`, "_blank", "noopener");
    $("feedback-text").value = "";
  });
}

// ---------------------------------------------------------------- start

const play = new Play();
const watch = new Watch();
new Training();
setupFeedback();
for (const b of document.querySelectorAll("nav button")) b.onclick = () => showTab(b.dataset.tab);
const tabFromHash = () => showTab(["play", "watch", "training"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "play");
window.addEventListener("hashchange", tabFromHash);
tabFromHash();
window.alphaGoLite = { play, watch };
