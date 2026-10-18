# Venue report — AAAI-27 workshop draft (updated 2026-10-18, after the consecutive replay)

## Checks (`check_paper.py`, run with `--regenerate`)
See `checks.md` for the latest table. Status at this draft:

| | Check | Detail |
|---|---|---|
| ✅ | LaTeX errors, references, missing files, fonts | none |
| ✅ | overfull lines | none (platform table shortened) |
| ✅ | page limit | main text ends on page 4 of a 7-page limit |
| ✅ | anonymity | no author name, handle, repo name or app name in the PDF |
| ✅ | numbers in prose are sourced | every number is a generated `\val` macro or a row in `sources.md` |
| ✅ | figures have scripts; figures and values reproduce exactly from the data | 7 generated files |
| ❌ | citations verified | `elo1978rating` (a 1978 book, no DOI; Crossref matched an unrelated title). The entry is correct to my knowledge — **please confirm** |
| ⚠️ | open TODOs | artifact link; AI-use statement confirmation |

## Rule changes found at P2
- No built-in AAAI profile existed; built from aaai.org on 2026-10-08.
- `aaai2027.sty` requires pdfTeX, so the paper builds with `pdflatex` + `bibtex` (TinyTeX), not Tectonic.
- AAAI requires the final source as **one** `.tex` file with the bibliography included.
  `figures_scripts/flatten_tex.py ../aaai27` writes `submission/main.tex` (all `\input`s and `main.bbl` inlined,
  plus the figure PDFs and style files); it compiles standalone to the same 5 pages.

## Venue choice — needs a decision
The AAAI-27 workshop list (published by 16 Oct) has **no workshop on games, game-playing RL or RL evaluation**.
The closest, "Effective and Efficient Evaluation for AI Scientists", is about research agents and states game
agents are out of scope. Options that fit the paper better:
- **ICLR 2027 workshops** (calls expected ~Dec 2026–Jan 2027; deadlines ~Feb 2027).
- **IEEE Conference on Games (CoG) 2027** short paper (deadline usually spring).
- **Advances in Computer Games / ICGA Journal** (games-specific; journal has no fixed deadline).
- Keep the AAAI format and submit to an AAAI-27 workshop only if one announces games/RL scope late.
Retargeting is mechanical (P9): the scripts regenerate figures at any venue's widths.

## Open TODOs and facts still needed
1. ~~Consecutive replay~~ — done (20 pairs, 800 games). Result changed the explanation: at 64 sims the
   consecutive matches agree with pairs 4 apart over the same generations (0.537 vs 0.547 per generation),
   while the log's 32-sim matches gave 0.493; chaining the replay from gen 25 to 34 gives +159 (log: −344).
   The paper now attributes the failure mainly to too-shallow per-generation matches plus noise — not to
   comparing adjacent generations. Please check you agree with this reading (§5, "Why").
2. Artifact link for review (anonymized) and public repo URL for camera-ready.
3. Author block for camera-ready (name, affiliation, email).
4. Confirm the `elo1978rating` reference.
5. Confirm or edit the AI-use statement (end of §7).

## Statements
- **AI use** (end of the paper): drafted from facts — the assistant drafted text, wrote the figure/table/value
  scripts and formatted/verified references; the author reviewed everything. AAAI allows generative-AI use
  with full author responsibility. If the chosen venue's submission form asks about AI use, the answer must
  match this statement.
- **Reproducibility checklist**: required for the AAAI main track, probably not for workshops; can be filled
  from `sources.md` if needed.

## Only a human can judge
- Whether the framing ("chained Elo can point the wrong way") is novel enough for the chosen venue; the related
  work covers evaluation pitfalls in general (Balduzzi et al.; Agarwal et al.) but I found no paper on this
  exact failure in small self-play runs — a literature check before submission is advised.
- Figure 1 is a simple TikZ diagram; polish as you like.
- Tone and title.
