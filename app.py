#!/usr/bin/env python3
"""Restaurant Location Agent -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8003
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).
"""

import contextlib
import http.server
import io
import json
import mimetypes
import re
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

COND_RE = re.compile(
    r"(type 2 diabetes|type 1 diabetes|diabetes|hypertension|high blood pressure|"
    r"kidney disease|ckd|heart disease|depression|asthma|arthritis|copd|hyperlipidemia)"
)

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

def _capture_fn(fn, params):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return "[web-ui] The personalized run hit an error and stopped safely.\n%s: %s" % (type(exc).__name__, exc)

# ---- personalized run: input handling lives in app.py; demo.py untouched ----

def run_custom(params):
    cuisine = (params.get("cuisine") or "Chinese").strip() or "Chinese"
    zipf = (params.get("zip") or "all").strip()
    avoid = (params.get("strategy") or "near") == "avoid"
    zips = DEMO.ZIPS  # the engine scores all areas so any spotlight ZIP is ranked against the rest
    goal = f"I want to open a {cuisine} restaurant in Phoenix -- where exactly should I open it?"
    memory = DEMO.seed_memory()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print("YOUR TURN -- " + goal)
        print("Your ZIP spotlight: %s" % ("all 8 areas" if zipf in ("all", "") else zipf))
        print("Strategy: %s" % ("avoid competition (blue-ocean)" if avoid else "near competitors (Hotelling rule)"))
        print("Honesty notes: (1) the sample dataset's competitor counts track Chinese restaurants;")
        print("for other cuisines the plan, tools, scoring and memory are fully real while competitor")
        print("counts stay approximate. (2) The engine scores all 8 areas so your spotlight ZIP can")
        print("be ranked against the rest.")
        planner = DEMO.Planner()
        tasks, note = planner.plan(goal, zips, memory, cuisine)
        print()
        print("PLANNER -- plan of action (%d steps)" % len(tasks))
        for t in tasks:
            print("  Step %2d. %-44s [tool: %s]" % (t.step, t.description, t.tool))
        print()
        print("MEMORY -- %s" % note)
        print()
        print("EXECUTION -- the agent loop, step by step")
        print("-" * 70)
        agent = DEMO.LocationAgent(DEMO.DEFAULT_WEIGHTS, avoid_competition=avoid)
        for t in tasks:
            print("Step %2d: %s" % (t.step, t.description))
            agent.run_step(t)
            print()
        memory.record(goal, cuisine, DEMO.DEFAULT_WEIGHTS, agent.best)
        print("YOUR RECOMMENDATION:", agent.best)
        if zipf not in ("all", "") and zipf in agent.areas:
            ranked = sorted(agent.areas.values(), key=lambda x: (-x["total"], x["postal_code"]))
            pos = next(i for i, a in enumerate(ranked, 1) if a["postal_code"] == zipf)
            a = agent.areas[zipf]
            print("YOUR SPOTLIGHT: %s ranked #%d of %d with total %.1f/100" % (zipf, pos, len(ranked), a["total"]))
    return out.getvalue()

PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Restaurant Location Agent &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>Restaurant Location Agent</h1>\n  <p class="sub">“Where exactly should I open my restaurant?” — answered with evidence, not gut feel.</p>\n</div></header>\n<main><div class="wrap">\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>Opening a restaurant is one of the riskiest small-business bets there is, and location decides most of it. Today that decision runs on gut feel and broker anecdotes.</p>\n<p>In this demo <b>you</b> play the restaurateur. The agent plans a 13-step investigation across 8 Phoenix ZIP codes, calls five evidence-gathering tools (review quality, competitors, economics, scoring, synthesis), scores every area on five factors, and recommends a ZIP with a plain-English explanation. Then the twist: you ask it to <i>avoid</i> competition instead — and it remembers your first query, inverts the competitor rule, and picks a different ZIP. Same agent, different memory-guided plan.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the planner decompose your question into 13 tool-calling steps <i>before</i> acting — planning first, tools second.</li>\n<li>Watch the per-factor scores: quality, economics, audience, competitor proximity, demand gap. No black box.</li>\n<li>In Turn 2, watch memory in action: the agent finds your first query, inverts the competitor rule, and changes its answer.</li>\n  </ul>\n</section>\n\n\n\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own</h2>\n  <p>Pick <b>your</b> cuisine, ZIP focus, and strategy — the planner and scoring engine re-run for you. Note: the sample dataset\'s competitor counts track Chinese restaurants, so for other cuisines the <i>process</i> is real while competitor counts stay approximate.</p>\n  <div class="row2">\n    <div><label class="f" for="r_cuisine">Your cuisine</label>\n      <select id="r_cuisine">\n        <option>Chinese</option><option>Italian</option><option>Mexican</option>\n        <option>Indian</option><option>Thai</option><option>American</option><option>Japanese</option>\n      </select></div>\n    <div><label class="f" for="r_zip">ZIP to spotlight</label>\n      <select id="r_zip">\n        <option value="all">All 8 Phoenix ZIPs</option>\n        <option>85003</option><option>85004</option><option>85006</option><option>85012</option>\n        <option>85015</option><option>85018</option><option>85020</option><option>85251</option>\n      </select></div>\n  </div>\n  <p class="hint" style="margin-top:10px">The engine scores all 8 areas so your spotlight ZIP is ranked against the rest.</p>\n  <label class="f" for="r_strat">Strategy</label>\n  <select id="r_strat">\n    <option value="near">Near competitors (Hotelling — foot traffic follows)</option>\n    <option value="avoid">Avoid heavy competition (blue-ocean ZIPs)</option>\n  </select>\n  <div class="btnrow">\n    <button class="ghost" id="customRun">Score it for me</button>\n    <span class="hint">Same inputs → same output. Deterministic.</span>\n  </div>\n  <div class="spinner" id="cspin"><div class="dot"></div>Planning and scoring…</div>\n</section>\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The agent is investigating the 8 ZIP codes…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>The recommendation came with receipts: five per-factor scores per ZIP, not a mysterious number.</li>\n<li>Competitor proximity is a feature, not just a threat — the Hotelling rule scores being near rivals positively (until you ask otherwise).</li>\n<li>Turn 2 proved memory: same engine, inverted rule, different ZIP — the agent adapts instead of repeating itself.</li>\n<li>Try your own: pick a cuisine, a ZIP focus, and a strategy in “Try your own” above.</li>\n    </ul>\n  </div>\n</section>\n\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/restaurant-location-agent" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["TURN 1", "Your question: where to open a Chinese restaurant in Phoenix. The agent plans, then executes."], ["PLANNER", "The 13-step plan: fetch data per ZIP, analyze quality, competitors, economics \\u2014 then score and synthesize."], ["MEMORY", "What the agent remembers from past sessions \\u2014 consulted before planning, reused when relevant."], ["EXECUTION", "The agent loop, step by step: each tool call with its evidence, in the open."], ["TURN 2", "The follow-up: avoid heavy competition. Memory is consulted, the competitor rule is inverted, the answer changes."], ["DEMO COMPLETE", "End of run."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\n\nfunction collectCustom(){\n  return {cuisine:document.getElementById(\'r_cuisine\').value,\n          zip:document.getElementById(\'r_zip\').value,\n          strategy:document.getElementById(\'r_strat\').value};\n}\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n</script>\n</body>\n</html>\n'

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
        return json.loads(raw.decode("utf-8") or "{}")

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
            self._json({"output": _capture_canned()})
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json({"output": _capture_fn(run_custom, params)})
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
