PROJECT NAME: algha_go_lite

META-INSTRUCTIONS:

<Read it all before acting. Ask about anything unclear, contradictory or
 underspecified — before starting and mid-build. Ask in the question widget
 (AskUserQuestion): related questions batched, concrete options, your
 recommendation first. Plain text only if the widget isn't available.>

<Don't expand scope. Anything not listed here is a proposal, including changes
 to this file — propose it, don't do it.>

<Prefer doing over describing: run the code, write the files, test it.>

<Always in scope, no proposal needed: when it goes on GitHub, a README that is
 easy to read at a glance — a line on what it is, then clear visuals
 (screenshots, a diagram or a chart), then links. Everything else goes in
 linked files: docs/INSTRUCTIONS.md (setup, run, use),
 docs/SYSTEM-DESIGN.md (see below) and docs/FILE-STRUCTURE.md (what's where). Also a small unobtrusive feedback tab
 if what you're building is an application rather than a script.>

<If what you're building is an application, build it as a Mac app first; the
 website comes after, as its own step.>

<Name things the way a person would say them — "Goal Tracker", not
 goal_tracker — for the app, its windows, titles, files people open, repo
 descriptions and README headings. When you create the GitHub repo, name it
 with no "_" or "-": one word or joined words, e.g. GoalTracker.>

<Always in scope: a system design doc in the codebase, docs/SYSTEM-DESIGN.md,
 kept current as the build changes. Cover the architecture (with a Mermaid
 diagram), each component's job, the main flows, where data lives, the key
 design decisions and their trade-offs, how it's tested, and known limits.>

<Finish by listing every deliverable: path, what it is, how to check it works.>

<Git rules (no Claude attribution, never commit .claude/) are in
 ~/.claude/CLAUDE.md and apply on their own — nothing to repeat here.>

<Keep the changelog at the bottom current.>

CONTEXT:

create alpha_go_lite

DELIVERABLES:

full scale demo with alpha_go

OPEN QUESTIONS / ASSUMPTIONS:

Asked and answered (2026-10-04):
- "alpha_go_lite" = AlphaGo Zero / AlphaZero algorithm scaled down to 9×9 Go
  (self-play + MCTS + policy/value network), trained on this laptop's CPU.
- "Full scale demo" = Mac app with: play vs the AI, show its thinking (visit
  heat map, win rates, expected line), training dashboard, AI vs AI replays.
- Stack: Python/PyTorch trainer → Core ML → native SwiftUI Mac app.
- GitHub: create repo AlphaGoLite and push; website is a later, separate step.

Decided without asking:
- Read "algha" in the folder name as a typo for "alpha"; the app is "AlphaGo Lite".
  The folder name was left alone.
- Rules: simple ko (no superko), no suicide, Tromp-Taylor area scoring,
  komi 7.5, game scored after 162 moves.
- Network 4 residual blocks × 48 channels (a 6×64 net was 2× slower on this
  Intel CPU); about 4 hours of training (19 generations, 3,040 games).
- Added a head-to-head strength check (final network vs generations 0 and 10)
  because chained Elo was too noisy to show progress.
- Added View-menu shortcuts (⌘1/⌘2/⌘3) for switching sections.
- Training tricks beyond the original paper: playout-cap randomization
  (KataGo) and Leela-style first-play urgency, both for speed on one CPU.
- Elo is chained generation-vs-previous-generation, relative to the random
  starting network.
- The engine passes after you pass only when it's already ahead on the board.
- Feedback is saved locally (Application Support/AlphaGo Lite/feedback.jsonl),
  not sent anywhere.
- Built as a Swift Package + build script rather than an .xcodeproj.
- GitHub repo created private.

Website (asked and answered 2026-10-04):
- Hosted on GitHub Pages. That needed the repo to be public on this plan, so
  AlphaGoLite was made public.
- Same features as the Mac app. Network runs with ONNX Runtime Web; feedback opens a
  pre-filled GitHub issue.

Website, decided without asking:
- Plain JavaScript with no build step; search runs in a Web Worker; charts use Chart.js.
- Strength levels match the Mac app (100 / 400 / 1200 / 3000 simulations).

CHANGELOG:

- 2026-10-04 — created
- 2026-10-05 — website built (web/), deployed to GitHub Pages; repo made public
- 2026-10-04 — built: 9×9 AlphaZero trainer + AlphaGo Lite Mac app (Play, AI vs AI, Training, Feedback); trained 19 generations; docs and README added
- 2026-09-15 — added meta-instruction: built-out applications include a small feedback tab
- 2026-09-15 — added meta-instruction: no "Claude" attribution in commits, PRs, or branches
- 2026-09-16 — added meta-instruction: always include a README when adding to GitHub
- 2026-09-16 — changed meta-instruction: ask clarifying questions in the question widget
- 2026-09-17 — added meta-instructions: Claude never a contributor; never commit .claude/
- 2026-09-26 — compressed the meta-instructions and every field prompt; git rules moved to the global instruction file
- 2026-09-27 — added meta-instruction: applications are built as a Mac app first, then a website
- 2026-09-28 — folded inputs, instructions, constraints, deliverables and done criteria into one free-form CONTEXT
- 2026-09-28 — changed meta-instruction: a README on GitHub always includes a visual
- 2026-09-28 — added meta-instruction: name things like a person would, never snake_case
- 2026-09-28 — changed meta-instruction: README leads with visuals; instructions live in a linked guide
- 2026-09-28 — changed meta-instruction: README is visuals and links; details in docs/INSTRUCTIONS.md and docs/FILE-STRUCTURE.md
- 2026-09-29 — changed meta-instruction: GitHub repo names have no "_" or "-"
- 2026-10-02 — added a DELIVERABLES field after CONTEXT
- 2026-10-02 — added meta-instruction: every project has a system design doc at docs/SYSTEM-DESIGN.md
