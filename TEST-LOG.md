# TEST-LOG.md — Determinism verification

**Date:** 2026-10-10
**Command:** `python3 demo.py` (10 consecutive runs, same machine, same session)
**Method:** each run's stdout+stderr captured to a file; recorded exit code and SHA-256 of full output.

| Run | Exit code | SHA-256 of output | Result |
|-----|-----------|-------------------|--------|
| 1 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 2 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 3 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 4 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 5 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 6 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 7 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 8 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 9 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |
| 10 | 0 | `91ddddb99e3d9dd06ee899e9f71fc52af0552242caac1a75f1d6cf8fe65e2c1f` | PASS |

**Result: 10/10 PASS** — exit code 0 and byte-identical output on every run.

Determinism sources: no timestamps, no `random`, no network, no unordered iteration
(all loops iterate `sorted()` keys; scorecard tie-breaks on postal code).

---

## Web UI test log (app.py)

**Date:** 2026-10-10
**What:** `app.py` — stdlib-only (`http.server`) localhost web UI on port 8003 (bound to 127.0.0.1). Endpoints: `GET /` serves the single-page UI (header + story, "Run live demo" button, agent-trace panel, results panel); `GET /api/run` runs `python3 demo.py` via subprocess and returns `{"ok": true, "output": "..."}` as JSON. No frameworks, no pip, no external assets, no network calls, no API keys.
**Method:** 12 rounds. Each round: (a) `python3 demo.py` must exit 0; (b) start `python3 app.py` on port 8003, wait for readiness, `curl /` must return HTTP 200 with UI markers, `curl /api/run` must return HTTP 200 with stable output markers from demo.py (`"ok": true`, `85012`, `85003`, `RECOMMENDED`, `score_location`, `DEMO COMPLETE`, `Hotelling`); then kill the server by PID.

| Round | demo.py exit | GET / | GET /api/run | Output markers | Result |
|-------|--------------|-------|--------------|----------------|--------|
| 1 | 0 | 200 | 200 | all present | PASS |
| 2 | 0 | 200 | 200 | all present | PASS |
| 3 | 0 | 200 | 200 | all present | PASS |
| 4 | 0 | 200 | 200 | all present | PASS |
| 5 | 0 | 200 | 200 | all present | PASS |
| 6 | 0 | 200 | 200 | all present | PASS |
| 7 | 0 | 200 | 200 | all present | PASS |
| 8 | 0 | 200 | 200 | all present | PASS |
| 9 | 0 | 200 | 200 | all present | PASS |
| 10 | 0 | 200 | 200 | all present | PASS |
| 11 | 0 | 200 | 200 | all present | PASS |
| 12 | 0 | 200 | 200 | all present | PASS |

**Result: 12/12 PASS** — no flakiness found.

One-off checks (not part of the 12 rounds):
- **Port in use:** with 8003 already bound, `python3 app.py` exits 1 with a clear error (`ERROR: port 8003 is already in use.` plus what's listening and the `pkill -f 'app.py'` fix) instead of a bare traceback.
- **Startup banner:** prints `Open in Chrome: http://localhost:8003` clearly on startup.
- **In-page render:** the page's JS parser was executed in Node against real `demo.py` output with a DOM stub (14 assertions): 2 plan boxes × 13 steps with the PLAN highlighted, 80 tool-call rows, 5 memory notes, 2 recommendation cards (85012 turn 1, 85003 turn 2), 2 five-row per-factor score tables, 2 "why" explanation blocks, DEMO COMPLETE banner — all rendered, no fallbacks. **Bug found and fixed:** the renderer's regex for seeded-memory list lines (`- '...' (cuisine: ...)`) expected the line to start with a quote and dropped both seeded entries; fixed before the 12 rounds.
- **Cleanup:** no `app.py` processes left running after the test run; port 8003 free.
