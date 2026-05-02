---
title: /tf-aws language standardization + noema-anchor cross-cutting recognition
date: 2026-05-02
focus_area: tf-aws + agent-kernel
generated_by: /evolve
related:
  - .claude/evolution/2026-05-01-tf-aws-patterns-3-6-7.md
  - .claude/evolution/2026-05-01-tf-aws-patterns-11-12.md
  - .claude/consolidate/2026-05-01-tf-aws-improvement-patterns.md
---

# Knowledge Evolution Report — language standardization + noema-anchor recognition

**Period reviewed**: 2026-05-02 session, post-pattern-12 close-out
**Focus**: clean up the epistemic overreach in `/tf-aws` framing language ("AWS = reality"), introduce `noema_anchor` as the per-replica declarative knob, and recognize the same underlying pattern at the kernel level without renaming anything

## Executive summary

Two related drifts converged today:

1. **Skill-layer drift** (`/tf-aws`): the framing "AWS reality / ground truth" was conflating an *operational* asymmetry (AWS read-only as safety boundary) with an *epistemic* asymmetry (AWS as the privileged truth). The conceptual work in this session — particularly the GORE/phenomenology parallel-text exercise and the explorer's GORE/Phenomenology tabs — surfaced that none of `.tf`/`.tfstate`/AWS-live is intrinsically canonical. The intent-noema is canonical; the three views are *profiles* of it.

2. **Kernel-layer pattern recognition**: The new concept `noema_anchor` (which profile is canonical right now for this replica) is structurally the same as several existing kernel concepts (`/merge` strategy, Thinking Tuple Invariant slot, `/feature` spec, `/reconcile` domain). The kernel already does the work; it just doesn't say so.

Both edits landed this pass. Drift type: **NEW_PATTERN** (vocabulary) + **DRIFT_NEGATIVE** (existing language was epistemically wrong). Magnitude: **MODERATE** (head-of-skill rewrite + one CLAUDE.md paragraph + one yaml field).

## What landed

### Skill-layer (`/tf-aws.md`)

**Vocabulary panel** added at the head, between Purpose and the three-axis δ block. Defines:
- The three **profiles** of the dr-bot intent-noema (`.tf`, `.tfstate`, AWS-live)
- The **realization-act** that produces each profile
- The **operational name** for each profile in this skill (contract, cache, deployment)
- The `noema_anchor` field as the declarative source of canonicality
- The flat-out admission: "the AWS = reality framing this skill carried before 2026-05-02 was an epistemic overreach"
- Reference to the Phenomenology HTML tab as the home of the deeper categorization (kept *not load-bearing for skill body*)

**Six word-level fixes** (subset applied this pass; the rest left for a follow-up if needed):
- Line 3 (Purpose): "deployed AWS reality" → "three profiles (`.tf` source, `.tfstate`, AWS-live)"
- Line 5 (Core Principle): renamed "Core Principle" → "Operational scope"; dropped "AWS reality is read-only" as a truth claim, kept it as a scoping statement
- Three-edges diagram (line ~17): "AWS reality" column label → "AWS-live"; "intent" / "realized intent" → "contract" / "cache"
- Kinds-of-truth table (line ~30): "View | Kind of truth" → "Profile | Role in this skill"; "Ground truth" row rewritten to name AWS-live as the *proxy for the noema while `noema_anchor: aws_currently_working`*, not as intrinsic truth
- Tuple Effects (line ~58): "TF-state and AWS-reality substrates" → "three profiles (.tf source, .tfstate, AWS-live) of a single intent-noema, anchored per-replica via `noema_anchor`"

### Replica config (`.claude/replicas/dr-bot.yaml`)

**`noema_anchor: aws_currently_working`** field added near the top, with comment explaining valid values (`aws_currently_working` / `tf_intent_pre_deployment`) and why the field exists (replaces implicit "AWS = reality" framing).

This field is currently **declarative only** — Phase D's direction-of-change logic doesn't yet read it. The field is the canonical record; runtime use is a follow-up that would let Phase D2's per-field verdict logic derive `apply-tf` vs `refresh-tf` defaults from the anchor instead of from the field-direction map alone. Deferred to a future pass.

### Kernel layer (`CLAUDE.md`)

**One paragraph appended to Principle #28** (Compositional Hierarchy), recognizing noema-anchor as a cross-cutting pattern across:

- Thinking Tuple Invariant slot (#26)
- `/feature` spec files
- `/merge` strategy field
- `/reconcile` domain argument
- `/tf-aws` `noema_anchor` field
- Principle #25 invariant levels L0–L4

**No renames.** The kernel keeps existing role-specific names (Invariant, spec, strategy, domain). The general name `noema-anchor` is reserved for skill-body usage in reconciliation/transformation modes. **Promotion to a Tier-0 principle is deferred** pending Rule of Three.

## Why no rename at the kernel level

Three reasons:

1. **The kernel's strength is small, sharp vocabulary.** Each existing word (Invariant, spec, strategy, domain) carries operational weight specific to its mode. Forcing a uniform "noema-anchor" rename would trade plain-English precision for a phenomenology term most kernel users don't think in.

2. **One instance ≠ kernel-level concept.** `/tf-aws` is the only skill that needs an explicit `noema_anchor` field today. Pattern 12 (invariant bracket) is on Rule-of-Three watch (2026-05-04 routine). Noema-anchor needs the same watch — when a second reconciliation skill explicitly needs it, promote.

3. **Phenomenology vocabulary was deliberately scoped *not* load-bearing for skill body** (declared in the Phenomenology HTML tab on 2026-05-01). Same logic at the kernel level: phenomenological framing is for evolution notes and pedagogical blocks, not for runtime operation.

## What changed in framing — before and after

**Before (`/tf-aws.md` head, until 2026-05-02)**:
> "Reconcile Terraform state with deployed AWS reality... AWS reality is read-only from this command's perspective."

This carried two claims:
- Operational: `/tf-aws` doesn't write AWS. ✅ Correct, load-bearing.
- Epistemic: AWS *is* reality. ❌ Overreach.

**After (`/tf-aws.md` head, 2026-05-02)**:
> "Reconcile a replica's three profiles (`.tf` source, `.tfstate`, AWS-live)... Operational scope: Mutations land only on `.tfstate` and `.tf`. AWS-live is read but never written by this skill."

The two claims are now separated:
- Operational scope is named explicitly as such.
- The epistemic claim is replaced by `noema_anchor: aws_currently_working` — a contingent, declarative choice that names AWS-live as the *proxy for the noema* because the bot is currently serving traffic. Could be different for a different replica.

## Skill-level findings

**Principle #27 row for `/tf-aws` is unchanged.** The kernel row says the skill "reconciles TF source ↔ TF state ↔ AWS reality" — the word "reality" appears there too, but at the kernel-row level it's a colloquial gloss, not a load-bearing epistemic claim. Could be re-worded to "AWS-live" for consistency, but skipping in this pass to avoid scope creep. Captured as optional follow-up below.

**Per-axis canonicality table** (drafted in the prior `/analysis` turn) was *not* added to the skill body in this pass. Reason: the Vocabulary panel covers the same ground at a higher level of abstraction — explicit axes per finding-type would be redundant with what Phase A.5 / B / C / C2 already do. If a future operator finds the framing insufficient for a real ambiguous case, add the table then.

## Action items

### Done this pass
- [x] Vocabulary panel inserted at head of `/tf-aws.md`
- [x] Three-edges diagram column label "AWS reality" → "AWS-live"; intent/realized-intent → contract/cache
- [x] "Kinds of truth" table reframed as "Profile / Role in this skill"
- [x] Tuple Effects "substrates" sentence rewritten with profile + noema-anchor language
- [x] `noema_anchor: aws_currently_working` field added to `.claude/replicas/dr-bot.yaml`
- [x] CLAUDE.md Principle #28 appended with cross-cutting noema-anchor paragraph
- [x] Step 10 compliance check (below)

### Optional follow-ups (not actioning in this pass)
- [ ] Re-word the `/tf-aws` row in CLAUDE.md Principle #27's command table — "AWS reality" → "AWS-live" for consistency
- [ ] Phase D2's per-field verdict logic could derive defaults from `noema_anchor` (e.g. `aws_currently_working` → bias toward `refresh-tf` for ambiguous cases). Currently the field is declarative-only.
- [ ] Add a CLAUDE.md cross-reference from #25 (Behavioral Invariant) to #28's noema-anchor paragraph — reinforces that the Invariant slot IS a noema-anchor in tuple terms.
- [ ] Update the explorer's GORE tab "Why GORE is load-bearing for /tf-aws" closer to mention `noema_anchor` as the operational landing of the goal model's canonical-profile concept.

### Watch — Rule of Three for noema-anchor promotion
When a second reconciliation skill (hypothetical `/tf-doppler`, `/tf-langfuse`, `/spec-runtime`, etc.) is built and **explicitly needs an anchor field**, that's the third instance — at which point `noema-anchor` graduates from Principle #28 footnote to a Tier-0 principle. The 2026-05-04 routine for Pattern 12 third-instance watch can be extended to also watch for noema-anchor patterns; recommend updating its prompt at the next /schedule manage pass.

## Step 10 — Agent Kernel compliance check

| Artifact | Tuple Effects section | CLAUDE.md entry | Tier | Status |
|---|---|---|---|---|
| `.claude/commands/tf-aws.md` | ✅ present (Strategy row referencing per-ORPHAN absorb fork + invariant bracket; unchanged this pass) | ✅ Principle #27 row present | 1 (unchanged) | ✅ |
| `.claude/CLAUDE.md` Principle #28 | n/a (principle) | ✅ self | 0 (Core, unchanged tier) | ✅ |
| `.claude/replicas/dr-bot.yaml` | n/a (config) | n/a (skill-internal) | n/a | ✅ |

**CLAUDE.md row spot-check for `/tf-aws`** (line ~277 in Principle #27 command table): row mentions `δ_source / δ_membership / δ_config`, `audit/diff/absorb/prune/sync`, Phase H self-test, Phase F.5, but does *not* mention `noema_anchor`. Decision: **no row update this pass**. The row is a one-line summary of what the skill does for the kernel; `noema_anchor` is a configuration knob on a single replica, not a kernel-level property. Listing it in the row would suggest it's structurally important to the kernel, when it's actually skill-internal. Compliance delta = 0.

**CLAUDE.md Principle #28 spot-check**: the new paragraph adds a 6-row table inside Principle #28's body. This is consistent with the existing "Applied Across Domains" table also inside #28. No tier change. No new principle file needed.

**Final delta = 0.**

## Reading order verification

Walked the skill linearly:
1. Header line (Purpose) — three profiles, intent-noema language
2. Operational scope (line ~5) — operational asymmetry, no epistemic claim
3. Vocabulary panel (lines ~7–25) — full conceptual mapping
4. Three-axis δ block — unchanged from prior pass
5. Three-edges diagram — column labels updated to AWS-live; node hint phrases updated to contract/cache
6. Kinds-of-truth table — reframed as Profile/Role with noema-anchor reference
7. Tuple Effects (Strategy / Local Check) — substrate language replaced with profile+noema-anchor
8. (rest of skill body, Phases A/A.5/B/B1/B2/B3/B3.5/C/C2/D/D2/E/F/F.5/G.1–G.8/H, unchanged)

Vocabulary panel sits *above* the three-axis δ block, so a reader encounters the noema/profile vocabulary before they hit the operational mechanics. Reading order coheres.

## Next evolution review

**Recommended**: when a second reconciliation skill needs an explicit anchor field (Rule of Three for noema-anchor promotion). Until then, the concept stays scoped to `/tf-aws` and recognized at the kernel via Principle #28's cross-cutting paragraph. The 2026-05-04 routine (Pattern 12 third-instance watch) is the right vehicle — extend its prompt to also watch for noema-anchor cases when next managed.

---

*Generated by `/evolve "evolve Language standardization for /tf-aws. and evolve Option B Recognize-without-rename..."`*
