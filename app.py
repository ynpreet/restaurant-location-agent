#!/usr/bin/env python3
"""
Restaurant Location Agent — localhost web UI (Demo 2 of 4, Agentic AI Workshop).

Starts a small, stdlib-only web server (http.server, no frameworks, no pip)
so the demo can be shown live in Google Chrome:

    python3 app.py
    -> Open in Chrome: http://localhost:8003

Endpoints:
    GET /         the single-page UI (header + story, Run live demo button,
                  agent-trace panel, results panel)
    GET /api/run  runs `python3 demo.py` via subprocess and returns
                  {"ok": true, "output": "<demo stdout>"} as JSON

Fully offline, no API keys, stdlib only. Bind address is 127.0.0.1 so the
server is reachable only from this machine.

Port 8003 is the fixed port for this demo in the workshop series. If the
port is already in use the server exits with a clear error instead of a
bare traceback.
"""

import errno
import http.server
import json
import os
import subprocess
import sys

HOST = "127.0.0.1"
PORT = 8003

# demo.py lives next to this file; run it from there so the UI works no
# matter which directory app.py is started from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_demo():
    """Run `python3 demo.py` in a subprocess; return a JSON-able dict."""
    try:
        proc = subprocess.run(
            [sys.executable, "demo.py"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "demo.py timed out after 60 seconds."}
    except Exception as exc:  # e.g. demo.py missing
        return {"ok": False, "error": "Could not launch demo.py: %s" % exc}
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": "demo.py exited with code %d." % proc.returncode,
            "output": proc.stdout,
            "stderr": proc.stderr[-2000:],
        }
    return {"ok": True, "output": proc.stdout}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "RestaurantLocationDemo/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  [http] %s\n" % (fmt % args))

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            body = PAGE.encode("utf-8")
            self._send(200, "text/html; charset=utf-8", body)
        elif path == "/api/run":
            body = json.dumps(run_demo()).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)
        else:
            body = b'{"ok": false, "error": "not found"}'
            self._send(404, "application/json; charset=utf-8", body)

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Single-page UI: inline CSS + JS, no external assets.
# (raw string so the JavaScript backslashes pass through untouched)
# ---------------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Restaurant Location Agent — Live Demo</title>
<style>
  :root {
    --bg: #0f1420; --panel: #182031; --panel2: #1f2a42;
    --ink: #eef2fa; --muted: #9aa7c2; --gold: #e8b44a;
    --red: #d64541; --green: #4cc38a; --blue: #5aa2f0;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.55;
  }
  .wrap { max-width: 1020px; margin: 0 auto; padding: 32px 20px 60px; }
  header.hero {
    background: linear-gradient(135deg, #23130f 0%, #4a1512 55%, #7a1f16 100%);
    border: 1px solid #8a3a28; border-radius: 14px;
    padding: 30px 32px; margin-bottom: 22px;
  }
  header.hero h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: 0.2px; }
  header.hero h1 .badge {
    display: inline-block; background: var(--gold); color: #23130f;
    font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
    vertical-align: middle; margin-right: 10px;
  }
  header.hero p.sub { margin: 0; color: #f3d9c6; font-size: 16px; }
  .story {
    background: var(--panel); border: 1px solid #2a3854; border-radius: 14px;
    padding: 22px 26px; margin-bottom: 22px;
  }
  .story h2 { margin: 0 0 10px; font-size: 19px; color: var(--gold); }
  .story p { margin: 8px 0; color: var(--ink); }
  .story .rules { margin: 10px 0 0; padding-left: 20px; color: var(--muted); }
  .story .rules li { margin: 4px 0; }
  .story .rules b { color: var(--ink); }
  .story .note {
    margin-top: 12px; font-size: 13px; color: var(--muted);
    border-top: 1px solid #2a3854; padding-top: 10px;
  }
  .controls { text-align: center; margin: 26px 0; }
  button#runBtn {
    background: var(--gold); color: #23130f; border: 0; border-radius: 10px;
    font-size: 18px; font-weight: 700; padding: 14px 44px; cursor: pointer;
    box-shadow: 0 4px 18px rgba(232,180,74,0.25);
  }
  button#runBtn:hover:not(:disabled) { background: #f3c46a; }
  button#runBtn:disabled { opacity: 0.55; cursor: wait; }
  .spinner {
    display: inline-block; width: 18px; height: 18px; margin-right: 10px;
    border: 3px solid rgba(35,19,15,0.25); border-top-color: #23130f;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    vertical-align: -3px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status { text-align: center; color: var(--muted); font-size: 14px; min-height: 22px; }
  .panel {
    background: var(--panel); border: 1px solid #2a3854; border-radius: 14px;
    padding: 22px 26px; margin-bottom: 22px;
  }
  .panel h2 { margin: 0 0 14px; font-size: 19px; }
  .panel h2 .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
  #tracePanel h2 .dot { background: var(--blue); }
  #resultsPanel h2 .dot { background: var(--green); }
  .turn-label {
    font-size: 15px; font-weight: 700; color: var(--ink);
    margin: 18px 0 8px; padding-bottom: 6px; border-bottom: 1px solid #2a3854;
  }
  .turn-label:first-child { margin-top: 0; }
  .plan-box {
    background: #fff8e8; color: #3a2c12; border-left: 5px solid var(--gold);
    border-radius: 8px; padding: 14px 18px; margin: 10px 0 16px;
  }
  .plan-box h3 { margin: 0 0 8px; font-size: 15px; color: #7a5b14; }
  .plan-box ol { margin: 0; padding-left: 22px; font-size: 14px; }
  .plan-box li { margin: 3px 0; }
  .plan-box .tool { font-family: var(--mono); font-size: 12px; background: #efe3c2;
    border-radius: 4px; padding: 1px 6px; white-space: nowrap; }
  .step-title { font-weight: 700; font-size: 14px; color: var(--ink); margin: 14px 0 6px; }
  .toolcall {
    font-family: var(--mono); font-size: 13px; background: var(--panel2);
    border: 1px solid #33415e; border-left: 4px solid var(--blue);
    border-radius: 6px; padding: 7px 12px; margin: 5px 0; color: #dbe5f5;
    overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  }
  .toolcall .tname { color: var(--gold); font-weight: 700; }
  .mem {
    font-size: 13px; color: var(--muted); background: #141b2c;
    border-radius: 6px; padding: 8px 12px; margin: 8px 0;
  }
  .mem b { color: var(--blue); }
  .rec-card {
    background: linear-gradient(135deg, #123524 0%, #1a4a33 100%);
    border: 1px solid #2e7d4f; border-radius: 10px;
    padding: 18px 22px; margin: 12px 0 16px;
  }
  .rec-card .zip { font-size: 30px; font-weight: 800; color: #7ce3a8; }
  .rec-card .area { font-size: 16px; color: var(--ink); }
  .rec-card .score { font-size: 15px; color: var(--muted); margin-top: 4px; }
  .rec-card .score b { color: var(--ink); }
  .factors { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
  .factors td { padding: 7px 10px; border-bottom: 1px solid #2a3854; }
  .factors td:last-child { text-align: right; font-family: var(--mono); color: var(--gold); font-weight: 700; }
  .why { font-size: 14px; color: #cdd7ec; margin: 12px 0; }
  .why p { margin: 8px 0; }
  .why p::before { content: "\2713  "; color: var(--green); font-weight: 700; }
  .complete {
    background: #123524; border: 1px solid #2e7d4f; border-radius: 10px;
    padding: 14px 20px; margin-top: 18px; font-size: 14px; color: #bde8cd;
  }
  .error {
    background: #3a1414; border: 1px solid var(--red); border-radius: 10px;
    padding: 14px 20px; color: #f5c9c9; font-size: 14px;
  }
  .empty { color: var(--muted); font-size: 14px; }
  footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 30px; }
  code { font-family: var(--mono); background: #141b2c; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <h1><span class="badge">DEMO 2 OF 4</span>Restaurant Location Agent</h1>
    <p class="sub">&ldquo;Where should I open a Chinese restaurant?&rdquo; — an agentic
    site-selection system that <b>plans</b>, calls <b>tools</b>, <b>scores</b> every
    candidate zip, and <b>synthesizes</b> a recommendation.</p>
  </header>

  <section class="story">
    <h2>The story</h2>
    <p>Opening a restaurant is one of the riskiest small-business bets there is —
    location decides most of it. Instead of gut feel, we hand the problem to an
    agent armed with <b>five business rules</b> a real restaurateur would use:</p>
    <ol class="rules">
      <li><b>Review-quality signals</b> — areas whose restaurants earn high stars and
        whose Chinese-spot reviews mention &ldquo;fresh&rdquo; and &ldquo;authentic&rdquo;.</li>
      <li><b>Produce/rent economics</b> — cheaper inputs and rent mean a good
        restaurant costs less to run.</li>
      <li><b>Customer/audience presence</b> — the cheapest lease means nothing with
        no foot traffic.</li>
      <li><b>Hotelling competitor-proximity</b> — a stall <i>beside</i> a competitor
        usually outperforms an isolated one; the agent models a curve that peaks at
        2&ndash;4 nearby Chinese restaurants and falls off with saturation.</li>
      <li><b>Cuisine saturation vs. demand gap</b> — low Chinese share + strong demand
        means an underserved gap.</li>
    </ol>
    <p>Watch the loop below: the agent prints its <b>PLAN</b> (13 steps), its
    <b>tool calls</b> with real outputs, and the <b>Synthesizer&rsquo;s</b> ranked
    recommendation. Turn 2 shows <b>memory</b>: asked to avoid competition, the
    agent reuses the turn-1 scoring profile and replans with the inverted rule.</p>
    <div class="note">Educational demo — all 60 businesses and reviews are synthetic
    SAMPLE data in the Yelp schema (clearly labeled in the output). Offline, no API
    keys, deterministic: identical output on every run.</div>
  </section>

  <div class="controls">
    <button id="runBtn" type="button">Run live demo</button>
  </div>
  <div class="status" id="status"></div>

  <section class="panel" id="tracePanel">
    <h2><span class="dot"></span>Agent trace — plan &amp; execution</h2>
    <div id="trace"><p class="empty">Press <b>Run live demo</b> to watch the agent
    plan, call its tools, and score all 8 Phoenix-area zips.</p></div>
  </section>

  <section class="panel" id="resultsPanel">
    <h2><span class="dot"></span>Results — recommendations</h2>
    <div id="results"><p class="empty">The Synthesizer&rsquo;s ranked
    recommendations will appear here.</p></div>
  </section>

  <footer>
    Runs <code>python3 demo.py</code> live on this machine (localhost:8003) &middot;
    stdlib only &middot; fully offline
  </footer>

</div>

<script>
(function () {
  "use strict";
  var btn = document.getElementById("runBtn");
  var status = document.getElementById("status");
  var traceEl = document.getElementById("trace");
  var resultsEl = document.getElementById("results");

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  btn.addEventListener("click", function () {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Running the agent…';
    status.textContent = "Running demo.py on the server — planning, tool calls, scoring…";
    traceEl.innerHTML = "";
    resultsEl.innerHTML = "";
    fetch("/api/run")
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        btn.disabled = false;
        btn.textContent = "Run live demo";
        if (!data.ok) {
          status.textContent = "The demo failed.";
          traceEl.innerHTML = '<div class="error">' + esc(data.error || "unknown error") + "</div>";
          return;
        }
        status.textContent = "Demo complete — trace and results rendered below.";
        render(data.output);
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.textContent = "Run live demo";
        status.textContent = "Request failed.";
        traceEl.innerHTML = '<div class="error">Could not reach /api/run: ' + esc(String(err)) + "</div>";
      });
  });

  function render(output) {
    var lines = output.split("\n");
    var traceHtml = [], resultsHtml = [];
    var mode = "pre";            // pre | plan | exec | synth
    var inPlanList = false;
    var inWhy = false;
    var whyLines = [];
    var i, line;

    function flushWhy() {
      if (whyLines.length) {
        resultsHtml.push('<div class="why">' +
          whyLines.map(function (w) { return "<p>" + esc(w) + "</p>"; }).join("") +
          "</div>");
        whyLines = [];
      }
    }

    for (i = 0; i < lines.length; i++) {
      line = lines[i];
      var t = line.trim();

      if (/^=+\s*$/.test(t) || /^-{10,}\s*$/.test(t) || t === "") { continue; }

      // ---- completion banner (check before synth mode swallows it) ----
      if (/^DEMO COMPLETE/.test(t)) {
        flushWhy();
        var extra = ((lines[i + 1] || "") + " " + (lines[i + 2] || "")).trim();
        resultsHtml.push('<div class="complete"><b>' + esc(t) + "</b><br>" + esc(extra) + "</div>");
        i += 2;
        continue;
      }
      if (/^agent used a plan/.test(t) || /^synthesizer across/.test(t)) { continue; }

      // ---- turn header ----
      var mTurn = line.match(/^TURN (.*?) — USER: (.*)$/);
      if (mTurn) {
        flushWhy(); mode = "pre"; inPlanList = false; inWhy = false;
        traceHtml.push('<div class="turn-label">Turn: ' + esc(mTurn[1] + " — " + mTurn[2]) + "</div>");
        resultsHtml.push('<div class="turn-label">' + esc(mTurn[1]) + "</div>");
        continue;
      }

      // ---- plan section ----
      if (/^PLANNER — plan of action/.test(t)) {
        mode = "plan"; inPlanList = true;
        var n = (t.match(/\((\d+) steps\)/) || [])[1] || "";
        traceHtml.push('<div class="plan-box"><h3>PLAN — plan of action' +
          (n ? " (" + n + " steps)" : "") + "</h3><ol>");
        continue;
      }
      if (inPlanList) {
        var mPlan = line.match(/^\s*Step\s+(\d+)\.\s+(.*?)\s+\[tool:\s*(.*?)\]\s*$/);
        if (mPlan) {
          traceHtml.push("<li><b>Step " + mPlan[1] + ".</b> " + esc(mPlan[2]) +
            ' <span class="tool">' + esc(mPlan[3]) + "</span></li>");
          continue;
        }
        traceHtml.push("</ol></div>");
        inPlanList = false;
      }

      // ---- memory notes ----
      if (/^MEMORY — /.test(t)) {
        traceHtml.push('<div class="mem"><b>MEMORY</b> — ' + esc(t.replace(/^MEMORY — /, "")) + "</div>");
        continue;
      }
      if (/\(cuisine:.*winner:/.test(t)) {
        traceHtml.push('<div class="mem" style="margin-top:-4px">' + esc(t) + "</div>");
        continue;
      }

      // ---- execution section ----
      if (/^EXECUTION —/.test(t)) { mode = "exec"; continue; }
      if (mode === "exec") {
        var mStep = line.match(/^Step\s+(\d+):\s+(.*)$/);
        if (mStep) {
          traceHtml.push('<div class="step-title">Step ' + mStep[1] + ": " + esc(mStep[2]) + "</div>");
          continue;
        }
        var mTool = line.match(/^\s*\[tool\]\s+(\w+)\((.*)\)\s*->\s*(.*)$/);
        if (mTool) {
          traceHtml.push('<div class="toolcall"><span class="tname">' + esc(mTool[1]) +
            "</span>(" + esc(mTool[2]) + ") &rarr; " + esc(mTool[3]) + "</div>");
          continue;
        }
      }

      // ---- synthesizer ----
      if (/^SYNTHESIZER —/.test(t)) { mode = "synth"; continue; }
      if (mode === "synth") {
        var mRec = t.match(/^RECOMMENDED:\s*(.*)$/);
        if (mRec) {
          var zip = mRec[1].split(" ")[0];
          var area = mRec[1].slice(zip.length).trim();
          resultsHtml.push('<div class="rec-card"><div class="zip">' + esc(zip) +
            '</div><div class="area">' + esc(area) + "</div>");
          continue;
        }
        var mScore = t.match(/^Score:\s*(.*)$/);
        if (mScore) {
          resultsHtml.push('<div class="score">Score: <b>' + esc(mScore[1]) + "</b></div></div>");
          continue;
        }
        if (/^Per-factor scores for/.test(t)) {
          resultsHtml.push('<table class="factors">');
          continue;
        }
        var mFactor = t.match(/^(\d\.\s+.*?)\s{2,}(\d+\.\d+)\/100$/);
        if (mFactor) {
          resultsHtml.push("<tr><td>" + esc(mFactor[1]) + "</td><td>" +
            esc(mFactor[2]) + "/100</td></tr>");
          continue;
        }
        if (/^Why, in plain English:/.test(t)) { resultsHtml.push("</table>"); inWhy = true; continue; }
        if (inWhy) {
          if (/^(You asked to avoid|Review-quality signal|Economics|Customers|Hotelling|Saturation vs demand|Runner-up)/.test(t)) {
            whyLines.push(t);
          } else if (whyLines.length) {
            whyLines[whyLines.length - 1] += " " + t;   // wrapped continuation line
          }
          continue;
        }
        continue;
      }

      // ---- skip demo banner / disclaimers (already on the page) ----
      if (/^RESTAURANT LOCATION AGENT/.test(t) || /^NOTE: All business data/.test(t)) { continue; }
    }
    flushWhy();
    traceEl.innerHTML = traceHtml.join("") || '<p class="empty">No trace captured.</p>';
    resultsEl.innerHTML = resultsHtml.join("") || '<p class="empty">No results captured.</p>';
  }
})();
</script>
</body>
</html>
"""


def main():
    try:
        server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            sys.stderr.write("\n")
            sys.stderr.write("ERROR: port %d is already in use.\n" % PORT)
            sys.stderr.write(
                "Something is already listening on http://localhost:%d "
                "(maybe another copy of this demo).\n" % PORT)
            sys.stderr.write(
                "Fix: stop the other process (e.g. `pkill -f 'app.py'`), "
                "then run `python3 app.py` again.\n\n")
            sys.exit(1)
        raise
    print("=" * 60)
    print("Restaurant Location Agent — live demo UI")
    print()
    print("Open in Chrome: http://localhost:8003")
    print()
    print("Serving on 127.0.0.1:%d — press Ctrl-C to stop." % PORT)
    print("=" * 60)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
