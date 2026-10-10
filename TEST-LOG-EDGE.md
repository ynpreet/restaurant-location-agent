# Edge-Case Test Log — Restaurant Location Agent (web UI)

Date: 2026-10-10. Deterministic: same inputs -> same outputs.

## Data
- No data changes (8-ZIP set is load-bearing for the canned narrative; per instructions).
- Verdict-first UI from the prior wave left intact; no regressions introduced.

## 13-case adversarial battery (function level) — ALL PASS
- Unicode/emoji cuisine ("寿司 🍣"), unknown cuisine ("Klingon"), 10,000-char cuisine string,
  ZIP "00000" (honest "not one of the 8" note), empty/None/non-string params,
  dict/list params, "not a dict"/None top-level, padded "  italian  " / " 85251 ",
  lowercase "mexican", invalid strategy "xyz" (falls back to "near" + note),
  control characters in cuisine: every case returns a valid verdict
  (winner in the 8-ZIP set, score 0-100, spotlight rank 1-8) or an honest note. No crashes.

## Matrix regression — 18/18 PASS
- 3 cuisines x 2 strategies x 3 spotlight ZIPs: winner valid, score in range,
  ranking sorted, spotlight rank correct, deterministic.

## HTTP battery (live server, port 8003) — ALL PASS
- Malformed JSON / empty body / 10KB junk / wrong types / JSON array / JSON null
  -> HTTP 200, valid JSON, no traceback.
- 24 concurrent requests -> all 200.
