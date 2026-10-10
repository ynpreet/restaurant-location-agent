# RUBRIC.md — Self-score vs. the PEAAII Hackathon Judging Rubric

Scored 1–5 per criterion against `~/workspace/peaii-hackathon/judging-rubric.md`, with concrete evidence, one honest gap per criterion, and how a student could close it.

| # | Criterion (weight) | Score | Points |
|---|---|---|---|
| 1 | Problem Definition & Real-World Impact (25) | 4/5 | 20 |
| 2 | Meaningful Agentic AI Behavior (20) | 5/5 | 20 |
| 3 | Working Prototype (15) | 5/5 | 15 |
| 4 | Innovation & Creativity (15) | 3/5 | 9 |
| 5 | Presentation & Communication (15) | 5/5 | 15 |
| 6 | Responsible AI & Feasibility (10) | 4/5 | 8 |
| | **TOTAL** | | **87/100** |

---

## 1. Problem Definition & Real-World Impact — 4/5 (20 pts)

**Evidence:** A specific user (an aspiring Chinese-restaurant owner in Phoenix) with a concrete, high-stakes question ("where exactly should I open it?"); the demo answers with a named zip, per-factor scores, and a plain-English rationale tied to five real business rules (review quality, produce/rent economics, audience, Hotelling clustering, saturation-vs-demand gap). Grounded in Preet's real Yelp-dataset repo for Phoenix, AZ — a genuine problem people solve with spreadsheets and gut feel today.

**Honest gap:** The demo frames the user well but never *names* who loses if the agent is wrong (the founder's savings). It also doesn't show the "today" workflow it's replacing.

**Close it:** Add one README line with the founder's stakes and a 30-second "before" beat in the talk — "today this is a broker's hunch and a spreadsheet; here's the agent's evidence trail instead."

## 2. Meaningful Agentic AI Behavior — 5/5 (20 pts)

**Evidence:** The loop is the centerpiece and it's *printed*: the Planner decomposes the goal into a 13-step plan (visible in output), five distinct tools are called with visible inputs/outputs (`fetch_area_data`, `analyze_review_quality`, `analyze_competitors`, `estimate_economics`, `score_location`), a Synthesizer ranks and explains, and Memory is genuinely used — turn 2 consults the turn-1 scoring profile and replans with an inverted competitor rule, producing a *different* recommendation (85003 vs 85012). A chatbot could not do this: it requires multi-step planning, tool use, and stateful memory.

**Honest gap:** The "memory" is seeded and in-process rather than persistent across sessions; a judge probing hard could call it scripted.

**Close it:** Persist memory to a small JSON file so a second `python3 demo.py` run shows recall of the previous real session — same stdlib, no new deps.

## 3. Working Prototype — 5/5 (15 pts)

**Evidence:** `python3 demo.py` is the entire demo — stdlib only, fully offline, completes in <1 second, and TEST-LOG.md proves 10/10 byte-identical runs with exit code 0. The scoring model is transparent and every factor traceable to tool output printed on screen.

**Honest gap:** Only one entry point and no interactive mode (unlike demo #1's `--interactive` flag); a student demoing live can't ask follow-up questions of their own.

**Close it:** Add an optional `--query` flag that re-runs scoring with a user-supplied cuisine or zip list — still deterministic given the same args.

## 4. Innovation & Creativity — 3/5 (9 pts)

**Evidence:** The Hotelling competitor-proximity curve modeled *explicitly* as a scored factor (peaks at 2–4 competitors, penalizes saturation, invertible on request) is a genuinely creative, economics-grounded design choice, and the "avoid competition" replan that flips the curve is a nice twist. But site-selection agents and location-scoring dashboards exist; the core idea is an execution of a known repo, not a novel invention.

**Honest gap:** It's a faithful classroom port of the existing Yelp-location repo, not a new concept.

**Close it:** Add one novel factor the repo didn't have — e.g., review-text "authenticity gap" (areas where reviews complain "nothing authentic here" = unmet demand), which the demo's sentiment scanner is already halfway to computing.

## 5. Presentation & Communication — 5/5 (15 pts)

**Evidence:** README carries the full non-technical story: a 30-second setup, a 1-minute walkthrough of the five rules, speaker notes for narrating the printed loop, an ASCII architecture diagram, a "say the honesty beat out loud" prompt, and MacBook run steps assuming zero setup. The demo's own output explains its recommendation in plain English a non-technical judge can follow, with per-factor scores a technical judge can audit.

**Honest gap:** No visuals — it's a terminal demo, and a live room responds to at least one picture.

**Close it:** Add a one-slide diagram (the ASCII architecture as a real slide) and, if time, a bar-chart of the eight zips' total scores rendered with plain matplotlib-free SVG in the browser.

## 6. Responsible AI & Feasibility — 4/5 (8 pts)

**Evidence:** The README's Limitations section and the "honesty beat" speaker note explicitly state the data is synthetic, the curve is a heuristic not market research, real deployments need live rent/demographic/foot-traffic sources, and "the agent advises; a human signs the lease." The "Point this at your real dataset" section gives the concrete jq + loader path from sample to real Yelp JSON. No personal data, no sensitive domain.

**Honest gap:** No discussion of what happens when the agent is *wrong* in the real-data version (a bad lease = real money lost) — no confidence intervals or "ask a broker" escalation.

**Close it:** Have the Synthesizer print a confidence caveat with close calls (e.g., 85012 at 76.1 vs runner-up 69.4 — "decisive") versus near-ties ("within 3 points — treat as a shortlist, visit both"), and add a one-line "verify with a local broker" nudge in the explanation.
