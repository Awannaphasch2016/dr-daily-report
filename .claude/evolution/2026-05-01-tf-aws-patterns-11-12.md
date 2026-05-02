---
title: /tf-aws — patterns 11 & 12 landed (closes 12-pattern catalog)
date: 2026-05-01
focus_area: tf-aws
generated_by: /evolve
related:
  - .claude/evolution/2026-05-01-tf-aws.md
  - .claude/evolution/2026-05-01-tf-aws-patterns-3-6-7.md
  - .claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md
---

# Knowledge Evolution Report — `/tf-aws` patterns 11 & 12

**Period reviewed**: 2026-05-01 session, post-/understand on pattern 12
**Focus**: implement the two remaining patterns deferred from the 3/6/7 pass; close out the 12-pattern catalog

## Executive summary

Patterns 11 and 12 landed in `tf-aws.md`. The 12-pattern catalog from `.claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md` is now fully resolved.

| Pattern | Final status |
|---|---|
| 1. Bracketing-as-scope is permission to skip | ❌ skipped (meta-skill-design lesson; lives in consolidation, not skill) |
| 2. Audit numbers are claims | ✅ in (Phase H self-test + BS-6) — pre-existing |
| 3. State and source are different kinds of truth | ✅ in (head pedagogical block) — landed earlier today |
| 4. Reverse-reference walk before destructive verbs | ✅ in (Phase B3.5) — pre-existing |
| 5. Plug #2 — journal before destructive verb | ✅ in (BS-2) — pre-existing |
| 6. HALT as fourth membership category | ✅ in (Phase C/D) — landed earlier today |
| 7. DIVERGED-IDS sub-case of DOUBLE | ✅ in (Phase C/D) — landed earlier today |
| 8. State files are roles, not flat lists | ✅ in (`state.role` schema) — pre-existing |
| 9. Backend-reference sweep as institutional memory | ✅ in (Phase F.5) — pre-existing |
| 10. Direction-of-change inference using available context | ✅ in (Phase D2) — pre-existing |
| **11. Auto-gen vs hand-write decision criteria** | **✅ in (Phase E absorb fork)** |
| **12. Layer 4 invariant assertion AROUND destructive verb** | **✅ in (Phase G bracket + Phase H self-test)** |

## What landed

### Pattern 11 — Auto-gen vs hand-write decision (Phase E)

**Edit location**: Phase E "Verb dispatch" — added new sub-section "Absorb output: hand-write vs auto-generate (per-ORPHAN fork)".

**What's new**:
- Comparison table contrasting Approach 1 (CLI `terraform import` + hand-written stub) and Approach 2 (`import {}` block + `terraform plan -generate-config-out=...`)
- Decision rule: pick Approach 2 only when ALL of (verdict came from `triage.always_import_classes` or `observer_class`) AND (resource type's fingerprint fields are not sensitive) AND (TF ≥ 1.5)
- Otherwise Approach 1
- Per-ORPHAN, not global: an absorb run typically emits a mix; output groups them into two sections
- Annotation in `diff` output naming which approach each ORPHAN would get

**Why this level of abstraction**: the decision is captured as 3 conjunctive criteria — that's the smallest size that distinguishes the cases without becoming a tutorial on terraform import semantics. The "Why the fork exists" paragraph gives the reasoning (Approach 2's two failure modes) so the next reader can extend the criteria when an unanticipated case shows up, instead of just adding flags.

**Behavioral effect**: ORPHANs admitted via `had_recent_activity` heuristic — i.e., those where the operator may have intent the team hasn't expressed yet — are kept on Approach 1, which forces explicit field declarations rather than codifying console drift as if it were canonical. ORPHANs admitted via `always_import_classes` (log groups, default IAM artifacts, observer alarms) — where AWS reality *is* the intent — flow to Approach 2, which avoids stub-vs-AWS drift on first apply.

### Pattern 12 — Pre/post invariant assertion wrapping Phase G

**Edit locations**:
- Phase G fully restructured into 8 numbered steps (G.1 through G.8) wrapping the destructive verb
- Phase H self-test gained `invariant_bracket_executed` coverage assertion
- Tuple Effects Strategy row mentions the bracket explicitly

**What's new**:
- **G.2 (pre-capture)**: per-state-file managed-resource count + expected delta (`+N`, `-N`, or `0`)
- **G.4 (re-fetch)**: re-download every in-scope state file from S3 after the verb (`/tmp/tf_state_*.json` from Phase A is stale)
- **G.5 (post-capture)**: same counts after the verb
- **G.6 (assert)**: actual == pre + expected_delta, per file; auto-restore from `.terraform-state-backups/<ts>/` on violation
- The crucial invariant: state files **not** in the verb's address-list partition get `expected_delta=0`. That's what catches misdirection (verb hits the wrong backend).

**Why this level of abstraction**: the invariant is computed from the verb's own address list. The skill doesn't need a separate spec language — the partition is automatically derivable from `terraform state rm <addrs>` / `terraform import <addr> <id>`. One concrete example (Stage 1's `primary expected_delta=0, deprecating expected_delta=-24`) anchors the pattern; the rest is mechanical.

**Behavioral effect**: a Stage-1-style operation now becomes safe even if the working directory is mis-initialized. Phase F.5 (backend-reference sweep) catches *external* misdirection (CI workflows pointing at deprecating); Pattern 12 catches *internal* misdirection (the working directory itself). Together they close the misdirection class.

**Phase H coverage assertion `invariant_bracket_executed`** prevents BS-6 leakage: the audit refuses to claim ✅ if the bracket didn't run on a `--apply`. So a future operator can't quietly skip G.2/G.5/G.6 and have the audit declare PASS based on "residual δ = 0 right now."

## Why the two patterns compose

Pattern 11 controls *what the verb writes*. Pattern 12 controls *what the verb is allowed to touch*. They're orthogonal but reinforce each other:

- Without 11: absorb runs with one rigid approach, sometimes writing wrong source, requiring follow-up edits
- Without 12: the verb's blast radius is whatever the address list says — and the address list isn't checked against the working directory it's run in
- With both: the absorb verb chooses its output strategy per-ORPHAN, AND the resulting state mutation is bounded by a computed invariant that fires before any byte is written outside the declared partition

The Tuple Effects Strategy line now reflects this: `Verb dispatch (per-ORPHAN absorb fork: hand-write vs auto-generate) → (optional Apply, bracketed by pre/post invariant assertion that auto-restores on scope violation)`.

## Skill-level findings

**No CLAUDE.md update needed.** Principle #27 row already says `verbs: audit/diff/absorb/prune/sync` and lists Phase F.5 explicitly. Phase G's restructure into 8 steps is a body-of-skill change that doesn't surface to the kernel row. The Strategy line in Tuple Effects (which the kernel row points to) is updated; the kernel row itself stays high-level.

## Action items

### Done this pass
- [x] Phase E absorb fork (Approach 1 vs 2 with criteria)
- [x] Phase G restructured into 8 bracket steps
- [x] Phase H self-test `invariant_bracket_executed` assertion
- [x] Tuple Effects Strategy line updated
- [x] Step 10 compliance check (below)

### Optional follow-ups (not actioning)
- Replicate the bracket pattern in other destructive skills (e.g., `/reconcile`, `/move`) — Rule of Three: not yet earned promotion to a CLAUDE.md principle. Watch for the third instance.

## Step 10 — Agent Kernel compliance check

| Artifact | Tuple Effects section | CLAUDE.md entry | Tier | Status |
|---|---|---|---|---|
| `.claude/commands/tf-aws.md` | ✅ present, Strategy row updated | ✅ Principle #27 row present, no row-level change needed | 1 (unchanged) | ✅ |

CLAUDE.md row spot-check: the row mentions Phase A.5, Phase H self-test, Phase F.5, but not Phase E or Phase G by name. Decision: no row update — the row's mandate is "what kernel-level properties does this skill maintain," and pattern 11/12 are *implementation details of how* the skill enforces the existing kernel-level properties (membership convergence + audit-execution non-skew). They strengthen the implementation without changing the kernel contract.

**Final delta = 0**.

## Catalog closed

The 2026-05-01 consolidation `.claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md` is now fully resolved. Of the 12 patterns: 10 in skill, 1 explicitly skipped (pattern 1, meta-skill-design lesson), 0 deferred.

## Next evolution review

Recommended trigger: when a third skill exhibits the bracket-around-destructive-verb pattern (Pattern 12). At that point promote it from `/tf-aws`-internal to a Tier-1 principle. Until then, it's specialized.

---

*Generated by `/evolve "implement pattern 11 and 12 to improve /tf-aws"`*
