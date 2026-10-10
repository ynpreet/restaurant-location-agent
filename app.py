#!/usr/bin/env python3
"""Restaurant Location Agent -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8003
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).

Verdict-first design: both the canned and personalized endpoints return
structured verdict data computed from demo.py's own scoring functions,
so the page renders a prominent "Recommendation" card BEFORE the
step-by-step trace.
"""

import contextlib
import http.server
import io
import json
import mimetypes
import subprocess
import sys
import urllib.parse
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8003
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

sys.path.insert(0, str(HERE))
import demo as DEMO  # the tested artifact: imported, never modified

CUISINES = ["Chinese", "Italian", "Mexican", "Indian", "Thai",
            "American", "Japanese"]


def _capture_canned():
    """Run the canned demo exactly as before (subprocess), capture stdout."""
    proc = subprocess.run(
        [sys.executable, str(DEMO_PY)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout or proc.stderr


def _capture_custom(fn, params):
    """Personalized handlers return a dict; never crash the page."""
    try:
        res = fn(params)
    except Exception:  # never crash the page on a bad input
        return {"output": "[web-ui] The personalized run hit an error and "
                          "stopped safely.",
                "verdict": None, "decision": None}
    if isinstance(res, dict):
        res.setdefault("decision", None)
        return res
    return {"output": res, "verdict": None, "decision": None}


# ---------------------------------------------------------------------------
# Verdict computation -- mirrors LocationAgent.score_location exactly,
# but silent. Same tools, same weights, same rounding, same sort order,
# so the verdict always agrees with what demo.py itself would print.
# ---------------------------------------------------------------------------
def _score_all(avoid):
    areas = {}
    for z in DEMO.ZIPS:
        area = DEMO.Tools.fetch_area_data(z)
        area["quality"] = DEMO.Tools.analyze_review_quality(area)
        area["comps"] = DEMO.Tools.analyze_competitors(area)
        area["econ"] = DEMO.Tools.estimate_economics(area)
        comps = area["comps"]
        aud = DEMO.Tools.assess_audience_and_gap(area, comps)
        area["aud"] = aud
        q = area["quality"]["quality_score"]
        e = area["econ"]["economics_score"]
        a = float(aud["audience_score"])
        if avoid:
            h = max(0.0, 100.0 - comps["n_chinese_competitors"] * 20.0)
        else:
            h = comps["hotelling_score"]
        g = aud["gap_score"]
        w = DEMO.DEFAULT_WEIGHTS
        total = (w["quality"] * q + w["economics"] * e + w["audience"] * a
                 + w["hotelling"] * h + w["gap"] * g)
        area["factors"] = {"quality": q, "economics": e, "audience": a,
                           "hotelling": h, "gap": g}
        area["total"] = round(total, 1)
        areas[z] = area
    return sorted(areas.values(),
                  key=lambda x: (-x["total"], x["postal_code"]))


def _reason_lines(winner, cuisine, avoid):
    f = winner["factors"]
    q_, c_, e_, a_ = (winner["quality"], winner["comps"],
                      winner["econ"], winner["aud"])
    lines = {
        "quality": ("Diners already trust the food here: %.2f weighted stars, "
                    "review sentiment %+.2f."
                    % (q_["weighted_stars"],
                       q_["chinese_review_sentiment"])),
        "economics": ("Cheap to run: rent index %.2f, produce index %.2f "
                      "(blended operating cost %.2f)."
                      % (e_["rent_index"], e_["produce_cost_index"],
                         e_["blended_cost"])),
        "audience": ("Built-in customers: foot-traffic score %d/100."
                     % a_["audience_score"]),
        "gap": ("Real demand gap: only %.1f%% of local restaurants are "
                "%s-style, while the diner demand signal is %d/100."
                % (a_["saturation_pct"], cuisine, a_["demand_signal"])),
    }
    if avoid:
        lines["hotelling"] = ("Only %d existing rival(s) -- the quiet, viable "
                              "spot you asked for."
                              % c_["n_chinese_competitors"])
    else:
        lines["hotelling"] = ("%d existing rival(s) prove the cuisine draws "
                              "crowds here -- you join the draw instead of "
                              "educating a cold market alone."
                              % c_["n_chinese_competitors"])
    top3 = sorted(f, key=lambda k: -f[k])[:3]
    return [lines[k] for k in top3]


def _build_verdict(cuisine, avoid, spotlight_zip):
    ranked = _score_all(avoid)
    best, runner = ranked[0], ranked[1]
    notes = []
    spot = None
    if spotlight_zip and spotlight_zip not in ("all", ""):
        if spotlight_zip in DEMO.ZIPS:
            pos = next(i for i, a in enumerate(ranked, 1)
                       if a["postal_code"] == spotlight_zip)
            sa = next(a for a in ranked
                      if a["postal_code"] == spotlight_zip)
            spot = {"zip": spotlight_zip, "area": sa["area"], "rank": pos,
                    "of": len(ranked), "score": sa["total"]}
        else:
            notes.append("Spotlight ZIP '%s' is not one of the 8 scored "
                         "Phoenix areas -- showing all 8." % spotlight_zip)
    verdict = {
        "cuisine": cuisine,
        "strategy": "avoid" if avoid else "near",
        "winner_zip": best["postal_code"],
        "winner_area": best["area"],
        "score": best["total"],
        "rank": 1,
        "of": len(ranked),
        "runner_up_zip": runner["postal_code"],
        "runner_up_area": runner["area"],
        "runner_up_score": runner["total"],
        "spotlight": spot,
        "reasons": _reason_lines(best, cuisine, avoid),
        "ranking": [{"zip": a["postal_code"], "area": a["area"],
                     "score": a["total"]} for a in ranked],
        "notes": notes,
    }
    if cuisine != "Chinese":
        verdict["notes"].append(
            "Honesty note: the sample dataset's competitor counts track "
            "Chinese restaurants, so for other cuisines the plan, tools and "
            "scoring are fully real while competitor counts stay approximate.")
    return verdict


def _clean_params(params):
    if not isinstance(params, dict):
        params = {}
    cuisine = params.get("cuisine")
    cuisine = cuisine.strip() if isinstance(cuisine, str) else ""
    cuisine = cuisine or "Chinese"
    zipf = params.get("zip")
    zipf = zipf.strip() if isinstance(zipf, str) else "all"
    zipf = zipf or "all"
    strat_raw = params.get("strategy")
    if strat_raw == "avoid":
        avoid, strat_note = True, None
    elif strat_raw in (None, "", "near"):
        avoid, strat_note = False, None
    else:
        avoid = False
        strat_note = ("Unknown strategy '%s' -- used 'near competitors'."
                      % strat_raw)
    return cuisine, zipf, avoid, strat_note


# ---- personalized run: input handling lives in app.py; demo.py untouched ----
def run_custom(params):
    cuisine, zipf, avoid, strat_note = _clean_params(params)
    verdict = _build_verdict(cuisine, avoid,
                             zipf if zipf != "all" else None)
    if strat_note:
        verdict["notes"].append(strat_note)
    zips = DEMO.ZIPS  # engine scores all areas; spotlight ZIP ranked vs rest
    goal = ("I want to open a %s restaurant in Phoenix -- where exactly "
            "should I open it?" % cuisine)
    memory = DEMO.seed_memory()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print("YOUR TURN -- " + goal)
        print("Your ZIP spotlight: %s"
              % ("all 8 areas" if zipf == "all" else zipf))
        print("Strategy: %s"
              % ("avoid competition (blue-ocean)"
                 if avoid else "near competitors (Hotelling rule)"))
        print()
        planner = DEMO.Planner()
        tasks, note = planner.plan(goal, zips, memory, cuisine)
        print("PLANNER -- plan of action (%d steps)" % len(tasks))
        for t in tasks:
            print("  Step %2d. %-44s [tool: %s]"
                  % (t.step, t.description, t.tool))
        print()
        print("MEMORY -- %s" % note)
        print()
        print("EXECUTION -- the agent loop, step by step")
        print("-" * 70)
        agent = DEMO.LocationAgent(DEMO.DEFAULT_WEIGHTS,
                                  avoid_competition=avoid)
        for t in tasks:
            print("Step %2d: %s" % (t.step, t.description))
            agent.run_step(t)
            print()
        memory.record(goal, cuisine, DEMO.DEFAULT_WEIGHTS, agent.best)
        print("YOUR RECOMMENDATION (from the trace above):", agent.best)
    return {"output": out.getvalue(), "verdict": verdict}


def canned_payload():
    """Canned two-turn demo + structured verdicts for both turns."""
    output = _capture_canned()
    v1 = _build_verdict("Chinese", avoid=False, spotlight_zip=None)
    v2 = _build_verdict("Chinese", avoid=True, spotlight_zip=None)
    return {"output": output, "verdicts": [v1, v2]}


PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Restaurant Location Agent &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\n.verdict{background:linear-gradient(135deg,#0e2a4a 0%,#0b3f3a 100%);\n  border:1px solid var(--teal);border-radius:var(--radius);\n  padding:26px 28px;margin:26px 0;box-shadow:0 8px 30px rgba(45,212,191,.12)}\n.v-kicker{font-size:12px;letter-spacing:.12em;color:var(--teal);font-weight:800;\n  text-transform:uppercase;margin-bottom:8px}\n.v-headline{font-size:26px;font-weight:800;margin:0 0 8px;line-height:1.3}\n.v-headline b{color:var(--teal)}\n.v-meta{color:#c8d6ea;font-size:15px}\n.v-spot{color:var(--warn);font-size:14.5px;margin-top:8px}\n.v-reasons{margin:14px 0 6px;padding-left:20px}\n.v-reasons li{margin:8px 0;color:#eaf0f9;font-size:15px}\n.v-rank{width:100%;border-collapse:collapse;margin-top:14px;font-size:13.5px}\n.v-rank th{text-align:left;color:var(--muted);font-size:11px;letter-spacing:.08em;\n  text-transform:uppercase;padding:6px 10px;border-bottom:1px solid var(--line)}\n.v-rank td{padding:6px 10px;border-bottom:1px solid var(--line);color:#d5e0f1}\n.v-rank tr.win td{color:var(--teal);font-weight:800}\n.v-note{margin-top:12px;font-size:13px;color:var(--muted);font-style:italic}\ndetails.trace{margin-top:6px}\ndetails.trace summary{cursor:pointer;color:var(--teal);font-weight:700;\n  font-size:15px;margin:6px 0 12px}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\n/* --- care revamp: why-section + sidebar layout --- */\n.care-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:26px;align-items:start}\n.care-main{min-width:0}\n.care-sidebar{position:sticky;top:20px;min-width:0}\n@media(max-width:960px){.care-layout{grid-template-columns:1fr}.care-sidebar{position:static}}\n.side-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin-bottom:20px}\n.side-card h3{margin:0 0 10px;font-size:15px;color:var(--teal)}\n.side-vid{margin-bottom:18px}\n.side-vid:last-child{margin-bottom:0}\n.side-vid iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;display:block;background:#000}\n.side-vid p{font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.5}\n.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}\n@media(max-width:700px){.why-grid{grid-template-columns:1fr}}\n.why-grid figure{margin:0}\n.why-grid img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:#0a0f1c}\n.why-grid figcaption{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.5}\n.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}\n.chip{background:var(--panel2);border:1px solid var(--teal);color:var(--teal);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;font-family:inherit;line-height:1.4}\n.chip:hover{background:var(--teal-dim)}\n.chal{list-style:none;margin:10px 0 0;padding:0}\n.chal li{position:relative;padding:7px 0 7px 28px;color:#d5e0f1;font-size:15px}\n.chal li::before{content:"!";position:absolute;left:9px;color:var(--warn);font-weight:800}\n\n\n.blog-list{list-style:none;margin:0;padding:0}\n.blog-list li{margin:0 0 14px;padding-bottom:14px;border-bottom:1px dashed var(--line)}\n.blog-list li:last-child{margin-bottom:0;padding-bottom:0;border-bottom:0}\n.blog-list a{color:var(--teal);font-weight:700;font-size:14.5px;text-decoration:none}\n.blog-list a:hover{text-decoration:underline}\n.blog-list span{display:block;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.5}</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>Restaurant Location Agent</h1>\n  <p class="sub">&ldquo;Where exactly should I open my restaurant?&rdquo; &mdash; answered with evidence, not gut feel.</p>\n</div></header>\n<main><div class="wrap care-layout">\n<div class="care-main">\n<section class="card" id="why">\n<h2><span class="n">&#9733;</span>Why this matters in real life</h2>\n<p>&ldquo;Location, location, location&rdquo; is the oldest clich&eacute; in the restaurant business &mdash; because it is true. The wrong corner can sink a brilliant concept, while the right one can carry an average one for years.</p>\n<p>And yet the decision is usually made on gut feel: a few drive-bys, a guess about foot traffic, a landlord\'s promises. A restaurant lease is a 5-to-10-year commitment &mdash; the biggest single bet most restaurateurs ever make, and nearly impossible to undo.</p>\n<p>Data-driven site selection weighs, all at once, what no human can hold in their head together &mdash; foot traffic, competitor density, neighborhood character, review sentiment, rent economics &mdash; and scores every candidate the same fair way. That is what this demo does.</p>\n<div class="why-grid">\n<figure><img src="/assets/img/vibrant-street.svg" alt="A vibrant restaurant street" loading="lazy"><figcaption>Foot traffic is the lifeblood &mdash; the right street markets itself.</figcaption></figure>\n<figure><img src="/assets/img/new-restaurant.svg" alt="A new restaurant opening its doors" loading="lazy"><figcaption>Opening day: the lease was signed months ago. Choose well.</figcaption></figure>\n<figure><img src="/assets/img/dining-room.svg" alt="Diners enjoying a restaurant" loading="lazy"><figcaption>Full tables start with the right address, not the right menu.</figcaption></figure>\n</div>\n<p><b>Why this kind of agent helps:</b></p>\n<ul class="watch">\n<li>Turns a once-a-decade gut decision into a repeatable, explainable scoring process</li>\n<li>Spots patterns humans miss &mdash; like competitors clustering exactly where demand already is</li>\n<li>Lets you test strategies (&ldquo;near competitors&rdquo; vs &ldquo;avoid them&rdquo;) before signing anything</li>\n</ul>\n  <p class="seccap" style="margin-top:14px"><b>Companion project:</b> I also built an end-to-end ML model predicting the ideal location for a new restaurant on the Yelp dataset &mdash; the machine-learning companion to this agent: <a href="https://github.com/ynpreet/Predicting-Ideal-location-for-a-new-reastaurant-using-Yelp-dataset" target="_blank" rel="noopener" style="color:var(--accent);font-weight:700">Predicting Ideal location for a new restaurant using Yelp dataset</a>.</p>\n</section>\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>Opening a restaurant is one of the riskiest small-business bets there is, and location decides most of it. Today that decision runs on gut feel and broker anecdotes.</p>\n<p>In this demo <b>you</b> play the restaurateur. The agent plans a 13-step investigation across 8 Phoenix ZIP codes, calls five evidence-gathering tools (review quality, competitors, economics, scoring, synthesis), scores every area on five factors, and recommends a ZIP with a plain-English explanation. Then the twist: you ask it to <i>avoid</i> competition instead &mdash; and it remembers your first query, inverts the competitor rule, and picks a different ZIP. Same agent, different memory-guided plan.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the planner decompose your question into 13 tool-calling steps <i>before</i> acting &mdash; planning first, tools second.</li>\n<li>The verdict card lands <b>first</b>: the winning ZIP, its score, and the three strongest reasons &mdash; computed from the same scoring engine, not scraped from the text.</li>\n<li>In Turn 2, watch memory in action: the agent finds your first query, inverts the competitor rule, and changes its answer.</li>\n  </ul>\n</section>\n\n<section class="card" id="tryown">\n  <h2><span class="n">&#9998;</span>Try your own</h2>\n  <p>Pick <b>your</b> cuisine, ZIP focus, and strategy &mdash; the planner and scoring engine re-run for you. Note: the sample dataset&rsquo;s competitor counts track Chinese restaurants, so for other cuisines the <i>process</i> is real while competitor counts stay approximate.</p>\n  <div class="row2">\n    <div><label class="f" for="r_cuisine">Your cuisine</label>\n      <select id="r_cuisine">\n        <option>Chinese</option><option>Italian</option><option>Mexican</option>\n        <option>Indian</option><option>Thai</option><option>American</option><option>Japanese</option>\n      </select></div>\n    <div><label class="f" for="r_zip">ZIP to spotlight</label>\n      <select id="r_zip">\n        <option value="all">All 8 Phoenix ZIPs</option>\n        <option>85003</option><option>85004</option><option>85006</option>\n        <option>85012</option><option>85015</option><option>85018</option>\n        <option>85020</option><option>85251</option>\n      </select></div>\n  </div>\n  <p class="hint" style="margin-top:10px">The engine scores all 8 areas so your spotlight ZIP is ranked against the rest.</p>\n  <label class="f" for="r_strat">Strategy</label>\n  <select id="r_strat">\n    <option value="near">Near competitors (Hotelling &mdash; foot traffic follows)</option>\n    <option value="avoid">Avoid heavy competition (blue-ocean ZIPs)</option>\n  </select>\n  <div class="btnrow">\n    <button class="ghost" id="customRun">Score it for me</button>\n    <span class="hint">Same inputs &rarr; same output. Deterministic.</span>\n  </div>\n  <div class="spinner" id="cspin"><div class="dot"></div>Planning and scoring&hellip;</div>\n</section>\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration (two turns: near competitors, then avoid competition). The verdict cards land first; the step-by-step work is below them.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The agent is investigating the 8 ZIP codes&hellip;</span></div>\n  <div id="vwrap"></div>\n  <div id="output">\n    <details class="trace"><summary>Show the agent&rsquo;s step-by-step work</summary>\n      <div class="out" id="outtext"></div>\n    </details>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>The recommendation came with receipts: the verdict card shows the winning ZIP, its score, its rank, and the three strongest reasons &mdash; computed from the scoring engine itself.</li>\n<li>Competitor proximity is a feature, not just a threat &mdash; the Hotelling rule scores being near rivals positively (until you ask otherwise).</li>\n<li>Turn 2 proved memory: same engine, inverted rule, different ZIP &mdash; the agent adapts instead of repeating itself.</li>\n<li>Try your own: pick a cuisine, a ZIP focus, and a strategy in &ldquo;Try your own&rdquo; above.</li>\n    </ul>\n  </div>\n</section>\n\n</div>\n<aside class="care-sidebar">\n<div class="side-card">\n<h3>Learn more</h3>\n<p style="font-size:13.5px;color:var(--muted);margin:0 0 14px">Want to go deeper on site selection? Start with these.</p>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/xHB8IBYaLYc" title="Top 5 Signs Your Restaurant Is in the WRONG Location" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>You cannot train or advertise your way out of a bad location &mdash; how to tell before you sign.</p>\n</div>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/HjfNArT9Ylk" title="How to Choose a Restaurant Location That Drives Foot Traffic" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>Visibility, access, demographics, complementary businesses &mdash; the site-selection checklist.</p>\n</div>\n</div>\n<div class="side-card">\n<h3>Go deeper &mdash; articles</h3>\n<ul class="blog-list">\n<li><a href="https://www.restroworks.com/blog/best-location-for-restaurant-business/" target="_blank" rel="noopener">Restaurant Location Strategy &amp; Site Selection Guide</a><span>RestroWorks &mdash; The full checklist: visibility, access, parking, size, and competition.</span></li>\n<li><a href="https://www.franchising.com/articles/_how_do_you_decide_on_the_locations_for_new_units_what_factors_or_data_point.html" target="_blank" rel="noopener">How Multi-Unit Operators Choose Locations</a><span>Franchising.com &mdash; Real franchisees on the VAST principle: visibility, access, signage, traffic.</span></li>\n<li><a href="https://delivisor.com/blog/how-to-choose-a-restaurant-location-that-drives-maximum-foot-traffic/" target="_blank" rel="noopener">Choosing a Location That Drives Maximum Foot Traffic</a><span>Delivisor &mdash; Location vs foot traffic: why the right corner markets itself.</span></li>\n</ul>\n</div>\n</aside>\n\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/restaurant-location-agent" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["YOUR TURN", "Your question, your cuisine, your ZIP spotlight, your strategy."], ["TURN 1", "Your question: where to open a Chinese restaurant in Phoenix. The agent plans, then executes."], ["PLANNER", "The 13-step plan: fetch data per ZIP, analyze quality, competitors, economics \\u2014 then score and synthesize."], ["MEMORY", "What the agent remembers from past sessions \\u2014 consulted before planning, reused when relevant."], ["EXECUTION", "The agent loop, step by step: each tool call with its evidence, in the open."], ["TURN 2", "The follow-up: avoid heavy competition. Memory is consulted, the competitor rule is inverted, the answer changes."], ["DEMO COMPLETE", "End of run."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction verdictCard(v, kicker){\n  const rows = v.ranking.map(function(r){\n    const win = r.zip === v.winner_zip;\n    return \'<tr class="\'+(win?\'win\':\'\')+\'"><td>\'+esc(r.zip)+\'</td><td>\'+esc(r.area)+\'</td><td>\'+r.score.toFixed(1)+\'</td><td>\'+(win?\'\\u25c0 winner\':\'\')+\'</td></tr>\';\n  }).join(\'\');\n  const spot = v.spotlight\n    ? \'<div class="v-spot">Your spotlight ZIP <b>\'+esc(v.spotlight.zip)+\'</b> (\'+esc(v.spotlight.area)+\') ranked <b>#\'+v.spotlight.rank+\'</b> of \'+v.spotlight.of+\' (score \'+v.spotlight.score.toFixed(1)+\'/100).</div>\'\n    : \'\';\n  const notes = (v.notes||[]).map(function(n){return \'<div class="v-note">\'+esc(n)+\'</div>\';}).join(\'\');\n  const reasons = v.reasons.map(function(r){return \'<li>\'+esc(r)+\'</li>\';}).join(\'\');\n  return \'<div class="verdict">\'\n    +\'<div class="v-kicker">\'+esc(kicker)+\'</div>\'\n    +\'<div class="v-headline">Open in <b>\'+esc(v.winner_zip)+\'</b> &mdash; \'+esc(v.winner_area)+\', Phoenix AZ</div>\'\n    +\'<div class="v-meta">Score <b>\'+v.score.toFixed(1)+\'/100</b> &middot; ranked #1 of \'+v.of+\' &middot; runner-up \'+esc(v.runner_up_zip)+\' (\'+esc(v.runner_up_area)+\') at \'+v.runner_up_score.toFixed(1)+\'</div>\'\n    +spot\n    +\'<ul class="v-reasons">\'+reasons+\'</ul>\'\n    +\'<table class="v-rank"><tr><th>ZIP</th><th>Area</th><th>Score</th><th></th></tr>\'+rows+\'</table>\'\n    +notes+\'</div>\';\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\');btn.disabled=false;\n    document.getElementById(\'vwrap\').innerHTML =\n      verdictCard(j.verdicts[0],\'Turn 1 \\u2014 near competitors (Hotelling)\') +\n      verdictCard(j.verdicts[1],\'Turn 2 \\u2014 avoid heavy competition\');\n    renderOut(j.output);\n    showTakeaways();\n    document.getElementById(\'vwrap\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectCustom(){\n  return {cuisine:document.getElementById(\'r_cuisine\').value,\n          zip:document.getElementById(\'r_zip\').value,\n          strategy:document.getElementById(\'r_strat\').value};\n}\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\');b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      if(!j.verdict){alert(\'Run failed: no verdict returned.\');return;}\n      const v=j.verdict;\n      document.getElementById(\'vwrap\').innerHTML = verdictCard(v,\n        \'Your run \\u00b7 \'+v.cuisine+\' \\u00b7 \'+(v.strategy===\'avoid\'?\'avoid competition\':\'near competitors\'));\n      renderOut(j.output);\n      showTakeaways();\n      document.getElementById(\'vwrap\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n</script>\n</body>\n</html>\n'

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkshopUI/1.0"

    def _send(self, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(json.dumps(obj), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_asset(self, path):
        safe = (HERE / path.lstrip("/")).resolve()
        try:
            safe.relative_to(HERE / "assets")
        except ValueError:
            return self.send_error(403, "forbidden")
        if not safe.is_file():
            return self.send_error(404, "not found")
        ctype, _ = mimetypes.guess_type(str(safe))
        data = safe.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(PAGE)
        elif path == "/api/run":
            self._json(canned_payload())
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json(_capture_custom(run_custom, params))
        else:
            self.send_error(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("ui: " + (fmt % args) + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("Restaurant Location Agent demo UI -> http://localhost:8003")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
