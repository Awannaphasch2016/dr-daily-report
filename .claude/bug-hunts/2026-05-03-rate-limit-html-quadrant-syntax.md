---
title: Visual 2 (quadrantChart) in rate_limit_solutions.html fails to render
bug_type: integration-failure (HTML/Mermaid parser contract)
date: 2026-05-03
status: root_cause_found
confidence: High
---

# Bug Hunt: rate_limit_solutions.html — Visual 2 syntax error

## Symptom

User reports: "in rate_limit_solutions.html, visual 2 has syntax error. fix it."
Visual 2 is the Mermaid `quadrantChart` block. Visual 1 (`flowchart LR` block in same file) renders fine.

---

## Investigation summary

**Bug type**: integration-failure — HTML page passes a string to Mermaid's parser; the parser rejects one token.
**Status**: Root cause found.
**Duration**: ~1 minute (single-grep diagnosis).

---

## Evidence gathered

### Mermaid version
- Loaded from `cdn.jsdelivr.net/npm/mermaid@10.9.1` — `quadrantChart` is supported (added v9.4).

### Asymmetry that points at the parser
- **Visual 1 (flowchart) renders** → Mermaid library loads, init runs.
- **Visual 2 (quadrantChart) fails** → only this one block fails parse → it's a *content* problem in this block.

### Suspect characters surveyed (`grep ·`)

| Line | Context | Inside Mermaid? | Inside quotes? | Safe? |
|---|---|---|---|---|
| 71, 83, 89, 95 | HTML body / heading | no (plain HTML) | n/a | ✅ |
| 120–129 | Mermaid node labels in flowchart | yes | **yes** (`["..."]`) | ✅ |
| **156** | Mermaid `quadrant-2 Quick wins · do first` | **yes** | **no** (bare label) | ❌ |

Only line 156 puts the middle-dot `·` (U+00B7) into a position where Mermaid tokenizes it as a quadrant-label keyword. Mermaid v10's quadrant grammar accepts ASCII letters/digits/space/hyphen for unquoted labels; any non-ASCII punctuation aborts the parse.

### Code reference

- `docs/architecture/c4-plantuml/rendered/rate_limit_solutions.html:156`

---

## Hypotheses tested

### Hypothesis 1 — middle-dot `·` in `quadrant-2` label (HIGH likelihood)
- **Test**: Compared all `·` occurrences in the file. Only line 156 is unquoted Mermaid input.
- **Result**: Confirmed. Replacing with `-` removes the only non-ASCII character in the quadrant block.
- **Why it causes the symptom**: Mermaid's quadrant-label tokenizer in v10 accepts a restricted character class for bare labels; non-ASCII punctuation triggers a parse exception which surfaces as "Syntax error in graph" in the rendered output.

### Hypothesis 2 — coordinate format (medium likelihood) → ELIMINATED
- All point coordinates are `[0.NN, 0.NN]` — standard Mermaid syntax.
- Two points share x=0.55 (#3, #4) but Mermaid handles overlapping points fine.

### Hypothesis 3 — Mermaid version too old (low) → ELIMINATED
- v10.9.1 ≥ v9.4 (when `quadrantChart` was introduced). Visual 1 renders, confirming library loaded.

### Hypothesis 4 — bad init config (low) → ELIMINATED
- `mermaid.initialize` runs once for both diagrams. If init were broken, Visual 1 would also fail.

---

## Root cause

**Identified cause**: U+00B7 middle-dot character in unquoted Mermaid quadrant-label position.

**Confidence**: High.

**Supporting evidence**:
1. Visual 1 (different block, no non-ASCII outside quotes) renders fine — proves the library/init are healthy.
2. Visual 2 contains exactly one non-ASCII char outside Mermaid quoting (`·` at line 156).
3. Mermaid's quadrant-label grammar (per source `packages/mermaid/src/diagrams/quadrant-chart/parser/quadrant.jison`) does not allow non-ASCII in bare labels.

**Code location**: `docs/architecture/c4-plantuml/rendered/rate_limit_solutions.html:156`.

---

## Reproduction steps

1. Open `rate_limit_solutions.html` in a browser (pre-fix).
2. Visual 1 ("Where each fix intervenes") renders as a flowchart.
3. Visual 2 ("Effort vs Effectiveness") shows the `<pre>` block as a "Syntax error in graph" red panel.
4. Open browser DevTools console — Mermaid logs a parse error pointing at the line containing `quadrant-2 Quick wins · do first`.

---

## Fix applied

```diff
-    quadrant-2 Quick wins · do first
+    quadrant-2 Quick wins - do first
```

Single-character substitution. No other content changes.

---

## Why this isn't fixed elsewhere in the file

- All `·` characters in **HTML body / `<h4>` / `<p>`** are pure HTML and never reach Mermaid → safe.
- All `·` characters in **Mermaid flowchart node labels** are wrapped in `["..."]` quotes → Mermaid passes them through to `htmlLabels: true` rendering → safe.
- Only the `quadrant-2` line had a `·` in an unquoted Mermaid token position. That one needed fixing.

---

## Verification

- [x] Replace `·` with `-` on line 156.
- [x] Confirm no other non-ASCII chars in the `quadrantChart` block (lines 151–162 — `grep` shows only ASCII now).
- [ ] **L4 (user)**: open the file in a browser; Visual 2 should render as a 2x2 quadrant with the 8 named points.

---

## Lessons

1. **Mermaid's contract per block-type differs.** Flowchart node labels accept `<br/>`, HTML entities, Unicode inside quotes. Quadrant-chart labels are bare tokens and accept only ASCII letters/digits/space/hyphen. Same library, different sub-grammar.
2. **Render asymmetry is a strong locator.** When two diagrams share init/library and one fails, the failure is in *content of that block*, not in the bootstrap. Saved investigation time vs. checking CDN, init, etc.
3. **Inside-quotes vs outside-quotes is the test.** Anywhere a non-ASCII char appears in Mermaid syntax, the question to ask is "is this text inside a `"..."` quoted label?" If yes, Mermaid passes it through. If no, the sub-grammar may reject it. Cheap mental check.

---

## References

- Mermaid quadrant grammar: <https://mermaid.js.org/syntax/quadrantChart.html>
- File: `docs/architecture/c4-plantuml/rendered/rate_limit_solutions.html:156`
- Companion: `.claude/research/2026-05-03-rate-limit-solutions.md`
