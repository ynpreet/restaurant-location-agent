# Restaurant Location Agent

**Demo 2 of 4 · Agentic AI Workshop**

> **▶ Open in Chrome (fastest way to demo):** run `python3 app.py`, then open **http://localhost:8003** in Google Chrome and click **Run live demo**. Stdlib only — no installs, no API keys, fully offline (binds 127.0.0.1, port 8003).

> **Educational demo.** All 60 businesses and reviews are synthetic SAMPLE
> data in the Yelp schema — clearly labeled in code and output. See section
> 10 ("Point this at your real dataset") to run it against real Yelp data.

---

## Real-world problem, target users, market need, and differentiation

**The problem.** *"I want to open a Chinese restaurant — where exactly
should I open it?"* Opening a restaurant is one of the riskiest
small-business bets there is, and location decides most of it. Today that
decision runs on gut feel, broker anecdotes, and spreadsheets that never
weigh the factors against each other.

**Target users.** First-time restaurateurs and small-business owners
scouting a site — people with deep food expertise and zero data-science
support.

**Market need.** A site decision blends five things a restaurateur actually
reasons about: review-quality signals, produce/rent economics,
customer/audience presence, competitor proximity, and cuisine
saturation-vs-demand. Nobody evaluates those five consistently across
every candidate area by hand.

**Differentiation.** This demo is the classroom-friendly, fully offline,
60-seconds-to-run version of a real analysis — Preet's repo
*[Predicting Ideal location for a new restaurant using Yelp
dataset](https://github.com/ynpreet/Predicting-Ideal-location-for-a-new-reastaurant-using-Yelp-dataset)*,
which ran the same class of analysis on the real Yelp dataset for Phoenix,
AZ. The agent doesn't give a one-shot answer: it **plans** the
investigation, **calls tools** to gather evidence per area, **scores** every
candidate zip, **synthesizes** a recommendation with per-factor scores and a
plain-English explanation — and on a follow-up turn, **remembers** the
scoring profile and replans with an inverted competitor rule. A second turn
shows memory in action: the user asks for a re-run that avoids competition,
the agent finds the turn-1 profile in memory, inverts the competitor rule,
and picks a different zip. Same agent, different memory-guided plan,
different answer.

---

## Meaningful Agentic AI functionality

**Why an agent, not a chatbot?** Ask the room: *"Could a plain chatbot do
this?"* No. This system:

- **Plans before acting** — the printed PLAN decomposes the goal into 13
  steps (fetch per zip → analyze → score → synthesize). This is the
  "planning" judges look for.
- **Uses tools rather than answering from memory** — five evidence-gathering
  tools (`fetch_area_data`, `analyze_review_quality`, `analyze_competitors`,
  `estimate_economics`, `score_location`) whose outputs you watch on screen.
- **Reasons across multiple evidence sources** — quality, economics,
  audience, Hotelling, demand gap — combined in a transparent weighted
  scoring model.
- **Remembers past sessions** — the seeded memory holds prior queries; turn
  2 consults it and reuses the scoring profile for the same cuisine.
- **Changes behavior on the follow-up goal** — "avoid heavy competition"
  inverts the Hotelling rule (`100 − 20·n`) and re-ranks, with no human in
  the loop for the analysis.

A chatbot produces text; this agent runs an investigation and revises its
plan when the goal changes.

---

## Project scope, inputs, outputs, constraints, success criteria, and definition of done

**Scope.** A deterministic, offline site-selection agent: two turns — the
ask ("where should I open a Chinese restaurant in Phoenix?"), then a
follow-up ("avoid heavy competition") that reuses memory and inverts one
rule.

**Inputs.**

- ~60 synthetic businesses across 8 Phoenix-area zips (Yelp-schema:
  business_id, name, city, state, postal_code, lat/lon, stars,
  review_count, categories) + 24 synthetic reviews attached to Chinese
  competitors.
- `ZIP_PROFILES`: per-zip area profile (produce-cost index, rent index,
  foot-traffic score).
- Scoring weights: quality 0.25, economics 0.20, audience 0.20, Hotelling
  0.15, gap 0.20.
- Seeded memory: two past sessions (bubble-tea/Tempe, taco-truck/ASU).

**Outputs.**

- Turn 1: recommended zip (**85012, Uptown Phoenix**) with per-factor
  scorecard and plain-English "why."
- Turn 2: re-ranked recommendation (**85003, Downtown Phoenix** — 1
  competitor, foot-traffic 92, big demand gap) with the inverted-competitor
  explanation.
- Full printed trace: PLAN, memory note, every tool call, synthesizer
  ranking.

**Constraints.** Stdlib only, fully offline, no API keys, no network.
Byte-identical output across runs (no randomness anywhere). Synthetic data
is labeled SAMPLE throughout.

**Success criteria.** Turn 1 recommends 85012 with Hotelling 100 (3 strong
Chinese competitors proving the cuisine's draw); turn 2 consults memory,
inverts the competitor rule, and recommends 85003; the scoring formula
matches the documented weights; `TEST-LOG.md` records 10/10 identical runs.

**Definition of done.** Both turns run in well under a second and exit 0;
README carries all 10 checklist sections; `TEST-LOG.md` shows the 10/10
determinism gate passing.

---

## Documented single-agent or multi-agent workflow

**Single-agent workflow** — one `LocationAgent` with a `Planner` and a
`Synthesizer`, calling five tools. (Multi-component, single decision-maker.)

```
                    ┌─────────────┐
                    │   USER GOAL │  "Where should I open a Chinese restaurant?"
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐   seeded with past sessions,
                    │   MEMORY    │──▶ consults scoring profile per cuisine
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐   decomposes goal → 13-step task list
                    │   PLANNER   │   (fetch per zip → analyze → score → synth)
                    └──────┬──────┘
                           ▼
        ┌──────────────────────────────────────────────┐
        │            EXECUTION LOOP (prints each step)  │
        │  fetch_area_data        → businesses + profile│
        │  analyze_review_quality → stars + review text │
        │  analyze_competitors    → Hotelling curve     │
        │  estimate_economics     → produce + rent      │
        │  score_location         → weighted total      │
        └──────────────────┬───────────────────────────┘
                           ▼
                    ┌─────────────┐   ranks zips, writes per-factor
                    │ SYNTHESIZER │──▶ scorecard + plain-English "why"
                    └─────────────┘
```

**Scoring model (transparent, deterministic):**

```
total = 0.25·quality + 0.20·economics + 0.20·audience
      + 0.15·hotelling + 0.20·gap
```

- `quality`: review-count-weighted average stars → 0–100 scale, blended
  with review-text sentiment ("fresh"/"authentic" vs "greasy"/"stale").
- `economics`: `100 · (1.6 − (0.6·rent + 0.4·produce)) / 0.9` — lower cost →
  higher score.
- `audience`: foot-traffic score per area.
- `hotelling`: peaks at 100 for 2–4 Chinese competitors, drops to 40 when
  ≥6 (saturated); inverted to `100 − 20·n` on the "avoid competition"
  follow-up.
- `gap`: demand (competitor review volume) minus cuisine saturation share.

All weights are fixed constants; no randomness anywhere — output is
byte-identical across runs (verified: 10/10 in `TEST-LOG.md`).

---

## Working prototype evidence, source code, and setup instructions

### Setup (MacBook, step by step)

You need nothing but Python 3, which ships with macOS. Any Python 3.8+
works. Zero installs — stdlib only (see `requirements.txt`). Two ways to
run it — the browser way (best for a live audience) and the terminal way.

**Option A — in Google Chrome (recommended for demos)**

**1. Open Terminal.** (Spotlight → type "Terminal" → Enter.)

**2. Start the web app:**

```bash
cd ~/workspace/agentic-ai-workshop/restaurant-location-agent
python3 app.py
```

You'll see:

```
Open in Chrome: http://localhost:8003
```

**3. Open that URL in Google Chrome and click "Run live demo."**

The page runs `demo.py` live on your machine and renders the agent trace
— the highlighted **PLAN**, every **tool call** with its output, and the
**results** panel with the ranked recommendation, per-factor scorecard,
and plain-English explanation. Run it as many times as you like: the
output is deterministic, so the story never drifts mid-demo.

(If port 8003 is already in use, `app.py` says so and exits — stop the
other copy with `pkill -f 'app.py'` and start again.)

**Option B — in the terminal**

```bash
cd ~/workspace/agentic-ai-workshop/restaurant-location-agent
python3 demo.py
```

Same demo as plain text — handy for piping, diffing, or reading the raw
output. It completes in well under a second, fully offline — no API keys,
no network, no downloads.

### Files

| File | What |
|---|---|
| `app.py` | Localhost web UI — `python3 app.py`, then open http://localhost:8003 in Chrome. Runs `demo.py` live and renders the agent trace + results. |
| `demo.py` | The whole demo — data, agent, tools, planner, synthesizer. `python3 demo.py` is the entry point. |
| `requirements.txt` | Empty by design — stdlib only, nothing to install. |
| `TEST-LOG.md` | 10 consecutive runs: exit code + SHA-256 of output, all passing. |
| `RUBRIC.md` | Self-score against the hackathon judging rubric, with evidence per criterion. |

### The story to tell (speaker notes)

**Setup (30 sec):** "Opening a restaurant is one of the riskiest
small-business bets there is, and location decides most of it. Today,
instead of gut feel, we hand the problem to an agent with five business
rules a real restaurateur would use."

**The five rules (1 min)** — walk through them on the slide or whiteboard:

1. **Review-quality signals** — areas whose restaurants earn high stars and
   whose Chinese-spot reviews mention "fresh" and "authentic" signal diners
   who reward quality.
2. **Produce/rent economics** — cheaper inputs and rent mean a good
   restaurant costs less to run (Preet's California-produce example: grow it
   nearby, serve it cheaper).
3. **Customer/audience presence** — the cheapest lease on earth means
   nothing with no foot traffic.
4. **Hotelling competitor-proximity** — Hotelling's law: a stall *beside* a
   competitor usually outperforms an isolated one, because rivals already
   proved the demand and draw crowds. The agent models this as a curve that
   peaks at 2–4 nearby Chinese restaurants and falls off when the area is
   saturated.
5. **Cuisine saturation vs. demand gap** — low Chinese share of restaurants
   + strong demand (review counts) = an underserved gap.

**Watch the loop (1–2 min):** In Chrome, click **Run live demo** (or run
`python3 demo.py` in the terminal). Point out each phase as it renders:
the **PLAN** (the agent decomposes the goal into 13 steps —
this is the "planning" judges look for), the **tool calls** with real
outputs (`fetch_area_data`, `analyze_review_quality`,
`analyze_competitors`, `estimate_economics`, `score_location`), and the
**Synthesizer** that ranks and explains. Ask the room: *"Could a plain
chatbot do this? No — it takes a multi-step plan, five different
evidence-gathering tools, and a scoring model."*

**The payoff:** Turn 1 recommends **85012 (Uptown Phoenix)** — quality 85,
Hotelling 100 (3 strong Chinese competitors proving the cuisine's draw),
audience 84. Turn 2 shows **memory**: the user asks for the *quietest
viable* spot, the agent finds the turn-1 profile in memory, inverts the
competitor rule, and picks **85003 (Downtown Phoenix)** — 1 competitor,
foot-traffic 92, big demand gap. Same agent, different memory-guided plan,
different answer.

**Bridge to the real repo (30 sec):** "This runs on 60 synthetic businesses
so it works on a plane. Preet's actual repo ran the same class of analysis
on the real Yelp dataset for Phoenix — link's in the README, and there's a
section showing exactly how to point this agent at the real JSON."

**Honesty beat (say it out loud):** "Everything here is sample data and a
heuristic curve, not a market study. A real site decision would layer in
rent listings, demographics, and foot-traffic sensors — and a human still
signs the lease. The agent *advises*; it doesn't decide."

---

## Functional and end-to-end testing, realistic scenarios, failure cases, reliability, and human oversight

**Realistic scenarios (end to end).** Turn 1 is the full investigation:
plan → 13 tool-calling steps across 8 zips → ranked recommendation with
explanation. Turn 2 is the realistic follow-up every user actually asks:
"interesting — now avoid heavy competition," exercising memory consult,
rule inversion, and re-ranking.

**Failure cases the demo handles** (all from `demo.py` behavior):

- **Zip with no businesses.** `analyze_review_quality` guards
  `total_rc == 0` (weighted stars → 0.0) instead of dividing by zero — an
  empty area scores, never crashes.
- **Zip with no Chinese competitors.** `analyze_competitors` returns
  `avg_competitor_stars = 0.0`, `avg_competitor_reviews = 0.0`, and the
  Hotelling lookup handles `n = 0` (score 30) explicitly.
- **Saturated area.** Six or more Chinese competitors collapses the
  Hotelling score to 40 — the curve encodes "crowded is bad," not just
  "competitors are good."
- **Memory miss.** `memory.consult(cuisine)` returns `None` for an unseen
  cuisine; the planner falls back to the default scoring profile with an
  explicit "No past queries" note — never a silent default.
- **Ambiguous cuisine memory.** `consult` matches on cuisine, scanning
  past queries newest-first, so a stale profile can't shadow a newer one.

**Reliability gate.** `TEST-LOG.md` records 10 consecutive runs of
`python3 demo.py` — exit codes + SHA-256 of full output — with the result
**10/10 PASSED, byte-identical output on every run**.

**Human oversight.** The agent *advises*; a human signs the lease. The
README's honesty beat is said out loud on stage: a real site decision
layers in rent listings, demographics, and foot-traffic sensors — and no
financial decision should rest on a demo.

---

## Focus, feasibility, and avoidance of unnecessary complexity

One file, stdlib only, 60 synthetic businesses, a fixed weight vector. The
complexity that was *not* added:

- **No ML framework, no LLM.** The "intelligence" is a transparent scoring
  formula with fixed weights — students can audit every number instead of
  trusting a black box.
- **No database.** The dataset is in-code dicts; the real-data swap path
  (section 10) is a small loader, not a migration.
- **No frontend.** The printed trace *is* the UI: PLAN, tool calls,
  synthesizer output — everything the audience needs to see the loop.
- **Heuristics labeled as heuristics.** The Hotelling curve and weights are
  stated as teaching approximations, not calibrated market research.

Feasibility is the design: a student can read `demo.py` end to end in one
sitting and understand exactly why 85012 beat 85003 — then extend it with
real data without changing the agent's shape.

---

## Interdisciplinary team roles and division of labor

| Role | Owns in this demo | Concrete component |
|---|---|---|
| **Domain researcher** | The five business rules and their economics | Hotelling's law curve (peak 2–4, collapse ≥6), quality/economics/audience/gap factor definitions, the avoid-competition inversion rule, the "human signs the lease" honesty framing |
| **Agent engineer** | Plan → execute → synthesize loop | `Planner` (13-step decomposition), `LocationAgent.run_step` execution loop, `Synthesizer.explain` plain-English reasons, `Memory.consult` profile reuse |
| **Data engineer** | Synthetic Yelp-schema dataset and the real-data swap path | `_RAW_BUSINESSES` / `_RAW_REVIEWS` in Yelp schema, `ZIP_PROFILES`, `_build_dataset`, the `jq` + loader recipe in section 10 |
| **UX / storyteller** | The two-turn narrative and the honesty beat | Speaker notes (five rules → watch the loop → payoff → honesty beat), the 85012-vs-85003 payoff, sample-data disclaimers in output |
| **QA** | Determinism gate and turn-2 behavior checks | `TEST-LOG.md` 10/10 byte-identical gate, verified turn-1/turn-2 winners, memory-hit vs memory-miss path coverage |

---

## Limitations, risks, and responsible AI (ethics, privacy, security, safety)

- **All data is synthetic; the Hotelling curve and weights are heuristics,
  not calibrated market research.** Say this out loud.
- **Foot-traffic, produce, and rent numbers are illustrative constants** —
  a real deployment needs live sources (rent listings, demographics,
  foot-traffic sensors).
- **The agent advises; a human signs the lease.** No financial decisions
  should rest on a demo.
- **No privacy exposure by design.** The dataset is invented; no real
  business or reviewer is represented. The same shape works on the real
  Yelp Open Dataset without changing the agent.
- **Bias caution for real use.** Heuristic weights encode the builder's
  judgment; applied to real neighborhoods, they would need calibration and
  fairness review so the scoring doesn't redline areas by proxy.

---

## Practical value, adoption path, and measurable outcomes

**Practical value.** A restaurateur's site decision, compressed from weeks
of gut feel into a 60-second, fully explainable investigation — every
factor scored, every recommendation justified in plain English, and the
follow-up question ("avoid competition") answered by replanning instead of
restarting.

**Adoption path — point this at your real dataset.** The demo ships with
~60 synthetic businesses across 8 Phoenix-area zips so it runs anywhere.
To run the same agent on **real Yelp data** (the [Yelp Open
Dataset](https://business.yelp.com/data/resources/open-dataset/)):

**1. Get the data.** Download `yelp_academic_dataset_business.json` and
`yelp_academic_dataset_review.json` from the Yelp Open Dataset page.

**2. Filter to your market.** The real repo's scope was Phoenix, AZ. A
one-liner per file with `jq`:

```bash
jq -c 'select(.state=="AZ" and (.city=="Phoenix" or .city=="Scottsdale" or .city=="Tempe"))' \
  yelp_academic_dataset_business.json > phoenix_business.json

jq -c 'select(.business_id as $b | $b)' yelp_academic_dataset_review.json > /dev/null  # reviews: filter by business_id set in step 3
```

**3. Drop it in.** In `demo.py`, replace `_RAW_BUSINESSES` / `_RAW_REVIEWS`
(or better: add a small loader) with code that reads your JSON:

```python
import json
# businesses: business_id, name, city, state, postal_code,
#             latitude, longitude, stars, review_count, categories
businesses = [json.loads(l) for l in open("phoenix_business.json")]
# reviews: business_id, stars, text
reviews = [json.loads(l) for l in open("phoenix_reviews.json")]
```

No code changes needed downstream: `is_chinese()` matches on the
`categories` string, `Tools.fetch_area_data` groups by `postal_code`, and
the review-text sentiment scan reads `reviews.text`. `ZIP_PROFILES`
(produce/rent/foot-traffic) would be replaced with real inputs — e.g., USDA
produce price data, rent listings, and foot-traffic estimates — but the
scoring model consumes them in the same shape.

**4. Run.** `python3 demo.py` — same loop, same output format, now on real
evidence.

**Measurable outcomes.** Today: byte-identical determinism (10/10) and
correct turn-1/turn-2 recommendations. On real data: rank stability across
data refreshes, agreement with broker shortlists, and — the honest metric —
whether recommended zips outperform on actual restaurant survival rates.

---

*Built for the Agentic AI Workshop · Demo 2 of 4*
