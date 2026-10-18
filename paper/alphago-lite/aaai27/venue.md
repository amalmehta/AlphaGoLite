# AAAI-27 Workshops (AAAI style)

> **Cycle:** AAAI-27 (workshops 22–23 Feb 2027, Montréal) · **Last checked:** 2026-10-08
> **Sources:** [Workshop call](https://aaai.org/conference/aaai/aaai-27/workshops-call/) ·
> [Main technical track call](https://aaai.org/conference/aaai/aaai-27/main-technical-track-call/) ·
> [Author kit](https://aaai.org/authorkit27/)

## Differences from the built-in profiles / open points
- No built-in AAAI profile exists; this one is new.
- **The specific workshop is not chosen yet.** AAAI posts the list of accepted workshops and their calls
  "by October 16, 2026". Each workshop sets its own page limit, anonymity rule and format. Until then this
  draft follows the AAAI-27 main-track format (the usual default for AAAI workshops — **convention**).
- **Compiler:** `aaai2027.sty` aborts unless the engine is pdfTeX ("pdfTeX is required to compile this
  document"), so Tectonic (XeTeX) cannot be used. The paper is built with `pdflatex` + `bibtex` from TinyTeX
  (`~/Library/TinyTeX`, installed 2026-10-08 with the researcher's approval).

## Deadlines
| Item | Date |
|---|---|
| Workshop paper submission (AAAI-wide default) | Friday 20 Nov 2026 (individual workshops may differ) |
| Author notification | Wednesday 2 Dec 2026 |
| Workshops | 22–23 Feb 2027 |

## Length and layout
| Field | Value | Source quote |
|---|---|---|
| Main-text page limit | 7 pages (main track); workshop limit **unknown until its call is out** | "Submissions are limited to 7 pages of main content, with a maximum total length of 9 pages. Any pages beyond page 7 are reserved exclusively for references." |
| Not counted | references (pages 8–9) | same |
| Columns | two | template |
| \textwidth, \columnwidth (measured) | 505.89 pt, 239.39 pt; \textheight 650.43 pt | probe on `AnonymousSubmission2027.tex` |
| Fonts | newtxtext (Times), helvet, courier — loaded by the style; adding font packages is forbidden | template comments |
| Paper size | US Letter | style file |

## Template
| Field | Value |
|---|---|
| Main style file | `aaai2027.sty` (package date 2027/05/04) |
| Anonymous option | `\usepackage[submission]{aaai2027}` |
| Camera-ready | `\usepackage{aaai2027}` (`CameraReady2027.tex`) |
| Citations | natbib (no options allowed), `aaai2027.bst`, author-year (`\citet`, `\citep`) |
| Forbidden packages | authblk, balance, CJK, float, flushend, fullpage, geometry, hyperref, navigator, … (see template) |
| Captions | `caption` package as loaded by the template; figure captions below, table captions above (**convention** in the example) |

## Anonymity
- Main track: double-blind (the anonymous submission template removes authors). Workshops vary — check the chosen call.
- The public repo, live site and app name identify the authors; in an anonymous version they must be replaced by
  "anonymized link" placeholders.

## Required and recommended sections
| Section | Required? | Where | Counts? |
|---|---|---|---|
| Reproducibility checklist | main track: required | separate document from the kit | no |
| Limitations | recommended (**convention**) | before conclusion | yes |
| AI-use disclosure | not required by AAAI wording; we include a short acknowledgement-style note | end of paper | yes (short) |

## LLM / AI-use policy
- "Authors may judiciously use generative AI tools, such as large language models and image generators, in
  preparing their scholarly manuscripts. However, authors remain fully responsible for all submitted material…"
- Prompt injection against the review system is a listed violation.

## Reviewer expectations (convention)
- Workshops reward a clear, well-scoped idea or early result; honest limitations matter more than scale.
- For an evaluation-methodology paper: statistical care (confidence intervals, number of games), a clear
  recommendation practitioners can adopt, and reproducible code.
