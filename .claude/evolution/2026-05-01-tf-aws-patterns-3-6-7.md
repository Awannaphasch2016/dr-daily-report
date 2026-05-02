---
title: /tf-aws — patterns 3, 6, 7 landed; 11, 12 deferred
date: 2026-05-01
focus_area: tf-aws
generated_by: /evolve
related: [.claude/evolution/2026-05-01-tf-aws.md, .claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md]
---

# Knowledge Evolution Report — `/tf-aws` patterns 3, 6, 7

**Period reviewed**: 2026-05-01 session (post Stage-1 cleanup)
**Focus**: improve `/tf-aws` skill so the patterns surfaced today have a textual home in the skill itself, not only in journals/explorer/consolidations
**Source pattern catalog**: `.claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md` (12 patterns)

## Executive summary

Three patterns landed in `tf-aws.md`. Two deferred pending more deliberate evaluation. One explicitly skipped as a meta-skill-design lesson that doesn't belong inside the skill itself.

| Pattern | Status before | Status now |
|---|---|---|
| 1. Bracketing-as-scope is permission to skip | ⚠️ partial | ❌ skip (meta-lesson, not skill content) |
| 3. State and source are different kinds of truth | ⚠️ mechanism only | ✅ pedagogical block + asymmetry table added |
| 6. HALT as fourth membership category | ❌ not in | ✅ Phase C set definition + Phase D triage rules |
| 7. DIVERGED-IDS sub-case of DOUBLE | ❌ not in | ✅ Phase C definition + Phase D DOUBLE triage |
| 11. Auto-gen vs hand-write decision criteria | ❌ not in | ⏸ deferred (pending /understand) |
| 12. Layer 4 invariant assertion AROUND destructive verb | ⚠️ partial | ⏸ deferred (pending /understand) |

Patterns 2, 4, 5, 8, 9, 10 are unchanged — already in the skill from the 2026-05-01 evolve pass earlier today.

## What landed (drift type: NEW_PATTERN, magnitude: MODERATE, evidence: in-session)

### Pattern 3 — State and source are different kinds of truth

**Edit location**: head of `tf-aws.md`, immediately after the three-edges diagram.

**What's new**: a 7-line block + 3-row table naming each view's *kind of truth* (contract / cache / ground truth) and the operational consequence — `terraform import` writes the cache without writing the contract, so importing alone leaves Edge A broken; the next `terraform plan` proposes destroy. This is the *why* behind Phase A.5's existence; before this edit, Phase A.5's mechanism was documented but the framing wasn't.

**Why this level of abstraction**: the table is the smallest representation that names the asymmetry without re-deriving the three-edges diagram. The consequence sentence is the smallest unit that connects the framing to a Phase that already exists.

### Pattern 6 — HALT as fourth membership category

**Edit locations**:
- Phase C set definitions (formal partition rule)
- Phase D triage rules (new "For each HALT" block with three verdict families)
- Audit / diff / Phase H output formats (HALT counts surface alongside ORPHAN/GHOST/DOUBLE)
- Phase H self-test triage_completeness assertion (HALT entries must have a verdict)
- Tuple-effects table Check row (HALT must be 0 for PASS)

**What's new**: HALT is defined as "bound in deprecating-role state ONLY, AWS resource is live." Triage default is `halt-defer` (state-rm now, accept temporary un-management, re-absorb on next audit as ORPHAN). Override to `import-to-primary-then-rm-from-deprecating` if the resource is in `triage.always_import_classes` / observer-class / had recent activity. New config knob `x.halt_defer_grace_days` (default 7) — audit flags HALT entries whose source hasn't landed in primary inside the grace window.

**Why this level of abstraction**: the partition rule is one line; the verdict logic mirrors the existing ORPHAN/GHOST verdict layout (keep / delete / review families); the rationale paragraph after the verdict block names the operational reason for the default (`halt-defer`) — that paragraph is what prevents the next reader from second-guessing the default and proposing "always import" as a simpler rule.

### Pattern 7 — DIVERGED-IDS sub-case of DOUBLE

**Edit locations**:
- Phase C set definition (sub-case named with detection rule: compare `instances[].attributes.id`, not just address)
- Phase D DOUBLE triage rules (split into same-ID and different-ID branches)

**What's new**: the existing DOUBLE triage assumed both bindings reference the same AWS ID. The DIVERGED-IDS branch surfaces when they don't — primary's binding stays canonical; rm of deprecating's binding leaves the deprecating AWS ID as a true ORPHAN that the next audit will surface and either import or delete-empty-shell.

**Why this level of abstraction**: one line in Phase C names the sub-case. Phase D's triage gets a 3-line addition that branches on equality of AWS IDs. The downstream consequence ("freed AWS ID becomes ORPHAN on next audit") is one sentence. No new Phase needed; no new verb needed.

## What was explicitly skipped

### Pattern 1 — Bracketing-as-scope is permission to skip

**Why skip**: this is a meta-lesson about how skills get designed (the act of bracketing a class of disagreements as "out of scope" is itself a behavior to scrutinize). It's about *me* designing skills, not about how `/tf-aws` operates. Putting it inside `/tf-aws` would be category confusion — the skill would carry advice for its own future maintainers, not advice for its operators.

**Where it lives**: stays in `.claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md` as a learning-from-this-session note. If it earns a third instance in another skill's evolution, it graduates to a CLAUDE.md principle then.

## What was deferred

### Pattern 11 — Auto-gen vs hand-write decision criteria (Approach 1 vs 2)

**Why defer**: today the skill emits Approach 1 (CLI `terraform import` + hand-written `.tf` stub) unconditionally for ORPHAN absorption. Approach 2 (`import {}` block + `-generate-config-out`) is mostly better for verified ORPHANs but has caveats (codifies console drift into source, locks defaults, sensitive-field redaction). User asked for clearer pre-write before committing the rule. Awaiting follow-up `/understand` request.

**Where the rule would land if accepted**: Phase E verb dispatch — the absorb verb gets a per-resource fork. The fork criterion is "verified ORPHAN with stable AWS config" → Approach 2; otherwise Approach 1.

### Pattern 12 — Layer 4 invariant assertion AROUND destructive verb

**Why defer**: today Phase H verifies *after* mutation. Pattern 12 captures an invariant snapshot *before* the verb (e.g., "primary has 208 managed resources"), executes the verb, then asserts the same invariant *after*. Phase G's backup is byte-level reversibility; pattern 12 is *semantic* — "did we touch only what we said we'd touch?"

**Where the rule would land if accepted**: Phase G as a wrapper — pre-verb snapshot, verb, post-verb re-assertion. The snapshot fields would be drawn from the audit's reported counts (TFM cardinality of in-scope state files, plus per-role counts).

## Skill-level findings

**No principle-level updates needed in CLAUDE.md.** The Principle #27 row for `/tf-aws` already lists the membership categories generically as "Edge B: ORPHAN/GHOST/DOUBLE." The audit-output and Phase descriptions inside the skill itself are the right level for HALT and DIVERGED-IDS to live; CLAUDE.md doesn't need to enumerate every sub-category. (See Step 10 below for the verification.)

## Action items

### Done this pass
- [x] Add pattern 3 framing to `tf-aws.md` head
- [x] Add HALT to Phase C/D + audit outputs + Phase H self-test
- [x] Add DIVERGED-IDS sub-case to Phase C/D
- [x] Step 10 compliance check (below)

### Deferred (pending user signal)
- [ ] Pattern 11: Approach 1 vs 2 decision criteria in Phase E
- [ ] Pattern 12: pre/post invariant snapshots wrapping Phase G

### Not actioning
- [ ] Pattern 1: meta-lesson stays in consolidation, not skill

## Step 10 — Agent Kernel compliance check

Artifacts modified this pass:

| Artifact | Tuple Effects section | CLAUDE.md entry | Tier | Status |
|---|---|---|---|---|
| `.claude/commands/tf-aws.md` | ✅ present (unchanged) | ✅ Principle #27 row present | 1 (unchanged) | ✅ |

CLAUDE.md Principle #27 row inspection:

> `/tf-aws` | reconcile | … reconciles TF source ↔ TF state ↔ AWS reality for the dr-bot replica on **three axes** — `δ_source` (Edge A: UNREALIZED-INTENT / UNDECLARED-IMPORT via Phase A.5 HCL parse + diff), `δ_membership` (Edge B: ORPHAN/GHOST/DOUBLE), `δ_config` (Edge B: TRACKED-but-DRIFTED, …)

**Drift check**: the Edge B membership enumeration in the row says `ORPHAN/GHOST/DOUBLE` — does it now need `HALT` too?

Decision: **no row update needed**. The row is a *one-line summary* of what the skill does; HALT is a fourth membership category that surfaces only in multi-state-file replicas. Listing it in the row would imply HALT is always relevant, when it's not. The skill body is the right home for the full enumeration. Compliance delta = 0.

## Reading order verification

Walked the skill linearly. Order of mention:
1. Header (line 3): "ORPHAN / GHOST / DOUBLE / HALT" — naming
2. Three-axis δ block: HALT mentioned in δ_membership criterion
3. Tuple Effects Check row: HALT must be 0 for PASS
4. Verb dispatch table: audit summary mentions HALT
5. Phase C: formal definitions of all four categories + DIVERGED-IDS sub-case
6. Phase D: triage rules for ORPHAN, GHOST, DOUBLE (incl. DIVERGED-IDS branch), HALT
7. Phase E verb-dispatch reminder: audit table includes HALT
8. Phase H output: residual δ for membership includes HALT
9. Phase H self-test: triage completeness assertion mentions HALT
10. End-to-end success line: `HALT=0` assertion

No forward references. HALT is named in the header before it is defined in Phase C; that's the standard pattern in the file (ORPHAN/GHOST/DOUBLE follow the same convention). Reading order is consistent.

## Next evolution review

**Recommended**: when patterns 11 or 12 earn an actionable trigger (e.g., a specific Stage 2 absorb that would benefit from auto-gen), or 30 days from now, whichever comes first.

---

*Generated by `/evolve "improve /tf-aws. keep info at the right level of abstraction."`*
