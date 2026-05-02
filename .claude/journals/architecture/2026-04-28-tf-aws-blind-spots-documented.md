---
title: Document `/tf-aws audit` blind spots — calibrating agent trust in `δ = 0`
category: architecture
date: 2026-04-28
status: adopted
related_adrs: []
tags: [tf-aws, replica, audit, agent-calibration, plug-2, blind-spots]
---

# Document `/tf-aws audit` blind spots — calibrating agent trust in `δ = 0`

## Context

**What problem are we solving?**

During the absorb-reality reconciliation walkthrough on 2026-04-28, three "risk callouts before green-light" surfaced for the dr-bot replica:

1. **trim-spec irreversibility** for the telegram-api Lambda env vars (`OPENROUTER_API_KEY`, `PDF_STORAGE_BUCKET`) — once removed from `terraform/telegram_api.tf:149,152` and from the validator at `src/telegram_lambda_handler.py:80`, the Mini App fix becomes a code-level re-addition rather than "set Doppler" or "set TF var".
2. **GHOST removal** for Aurora SG rules (`aurora_from_codebuild`, `aurora_from_proxy`) flagged in validation 2026-04-27 — `state rm` is consistent with `policy.default: absorb-reality` but **erases the original validation finding** from TF state. Future audits will not flag what is now absent on both sides.
3. **"LINE bot working" is not config-level proof of correctness for all tracked Lambdas** — the reconciliation imports webhook-health, model-catalog-sync, quant-agent. None are exercised by the LINE smoke test. They could be silently broken before and after.

A `/validate` run against the claim *"information about audit blind spots is documented in `.claude/commands/tf-aws.md`"* returned **PARTIALLY TRUE** with a strong skew: the doc covers safety properties (lines 5, 64, 537, 552, 648 — what the command will not do TO AWS) thoroughly, but only one paragraph (line 341) addresses what the audit's verdict cannot prove. The asymmetry was load-bearing: an AI agent reading `tf-aws.md` to calibrate its trust in `δ = 0` would conclude the spec is complete, then overtrust ✅ as "system healthy" when ✅ only proves "TF and AWS agree on the scoped, enumerated fields right now."

**Why this decision matters now**

The reconciliation plan is queued. Two destructive verbs (`state rm` + `trim-spec`) will execute next. After they run, the disagreements they resolve become invisible to all future audits — the TF state file is a snapshot of what TF *thinks AWS looks like*, not a record of *intent*. If the doc didn't tell agents (and humans) to journal those decisions before running the verbs, the reconciliation would silently consume its own provenance.

## Options Considered

### Option 1: Leave doc as-is, rely on session memory
**Pros**:
- Zero immediate work
- Three risk callouts already surfaced in this session

**Cons**:
- Session memory is not persisted; the next agent loading `tf-aws.md` cold has no signal that ✅ is narrow
- Doesn't generalize beyond the dr-bot replica (a future replica YAML inherits the same four blind spots structurally)
- Demonstrably failed: a `/validate` against "blind spots documented?" returned PARTIALLY TRUE

**Trade-off**: zero cost now, recurring cost on every future cold read. Wrong direction for a doc that AI agents are expected to consume.

### Option 2: Inline disclaimer in "Safety checklist"
**Pros**:
- Smallest possible change
- Co-located with existing safety language

**Cons**:
- "Safety checklist" is operational ("things to verify when running"); blind spots are epistemic ("things the verdict cannot prove"). Mixing them dilutes both.
- Single-paragraph disclaimers don't scale; new blind-spot categories couldn't grow the section without warping it.
- An agent skimming for "what does ✅ mean?" wouldn't think to look under "Safety checklist".

**Trade-off**: discoverability suffers; the disclaimer hides under a section heading that doesn't match the question being asked.

### Option 3: Dedicated "Blind spots and limits" section with 4 categories + plugs (CHOSEN)
**Pros**:
- Discoverable section heading matches the question agents actually ask ("what does `δ = 0` not prove?")
- Each blind-spot category is named, defined, and paired with a concrete mitigation (the "plug")
- Structure is open-ended: new blind-spot categories fit as new subsections without warping existing content
- Composes cleanly with Principle #25 (Behavioral Invariant Verification) — the section explicitly says `/tf-aws audit` covers Levels 4 + part of 3, leaving 0/1/2 out-of-band

**Cons**:
- Adds ~110 lines to a doc that was already long
- Section needs to stay current as `projection.fingerprint_fields` evolves (field-coverage subsection references it)
- Risk of becoming a "warnings museum" if it's not actively curated

**Trade-off**: pay one-time documentation cost in exchange for permanent calibration improvement for every agent reading the doc.

## Decision

**What did we choose?**

Option 3. The new section was added to `.claude/commands/tf-aws.md` between "## DRIFTED reconciliation" (operational) and "## Safety checklist" (operational), positioning the epistemic discussion at the boundary between detection guidance and operational guidance.

The section names four structural blind spots and pairs each with a one-line mitigation:

| # | Blind spot | Plug |
|---|---|---|
| 1 | Layer-coverage — runtime/behavioral correctness invisible | CloudWatch errors + Level-1 smoke + Level-0 e2e |
| 2 | Post-action amnesia — verbs that collapse spec onto reality erase intent | Journal the decision **before** running the destructive verb |
| 3 | Field-coverage — drift on undeclared fields invisible | Extend `projection.fingerprint_fields` after every incident |
| 4 | Scope-coverage — out-of-filter resources don't exist to the audit | Periodic unscoped sweep against `y.filter` complement |

It also includes a "Reading order for a passing audit" code block that explicitly tells the reader what *additional* checks compose with `δ = 0` to claim "system healthy."

**Why this option?**

Three reasons converged:

1. **AI-agent calibration is now a first-class concern.** This project's `.claude/commands/*.md` files are read by agents to decide how to act. A doc that under-documents its limits will be overtrusted. The cost of one section is small; the cost of agents misreading ✅ is silent and recurring.
2. **The four categories are stable.** Layer / post-action / field / scope is an exhaustive partition of the failure modes — every blind spot we surface in the future fits into one of the four. New entries become additions to existing subsections, not new subsections.
3. **This entry itself is Plug #2 in action.** Documenting the rationale before context fades is exactly what the new section recommends for destructive verbs. Practicing what we preach on a doc decision establishes the pattern before the higher-stakes runs (state rm + trim-spec) occur.

## Consequences

**Positive**:
- AI agents reading `tf-aws.md` learn that ✅ has a narrow technical meaning, not a broad colloquial one
- The four-plug pairing turns each warning into an actionable mitigation rather than free-floating anxiety
- The section composes with Principle #25 — Levels 4 + part of 3 are claimed; Levels 2/1/0 are explicitly out-of-band, requiring outside-the-audit evidence
- Future replicas (e.g., a hypothetical `webapp-vs-deployed`) inherit a stable taxonomy of blind spots to think against

**Negative**:
- Adds ~110 lines; one more section that needs to stay current as `projection.fingerprint_fields` evolves
- Field-coverage subsection references the YAML by name; if the YAML structure changes, the section needs an update
- Risk of becoming a "warnings museum" without active curation

**Mitigation strategy**:
- Treat the section as a living artifact: every time a blind spot bites in practice, add a one-line example to the relevant subsection
- During monthly `/evolve`, scan the section against current `projection.fingerprint_fields` for staleness

**Risks**:
- *Risk 1*: Section grows stale if `projection.fingerprint_fields` changes underneath it. **Likelihood**: medium. **Impact**: low (the named example becomes wrong, but the principle stays right). **Mitigation**: include in monthly doc-drift `/evolve` review.
- *Risk 2*: Agents read the section but don't operationalize the plugs. **Likelihood**: medium-high (knowing isn't doing). **Impact**: medium. **Mitigation**: the "Reading order for a passing audit" block names each plug as a precondition for "system healthy"; treats them as mandatory rather than aspirational.
- *Risk 3*: A new structural blind spot emerges that doesn't fit the four-category taxonomy. **Likelihood**: low (the four are exhaustive over the audit's epistemic surface). **Impact**: low. **Mitigation**: add a fifth category if/when this happens; the section's structure permits it.

## Next Steps

- [x] Add "Blind spots and limits" section to `.claude/commands/tf-aws.md` between "DRIFTED reconciliation" and "Safety checklist" (done 2026-04-28 in this evolution)
- [x] Update `CLAUDE.md` `/tf-aws` row to mention two-axis δ (done earlier this session)
- [ ] **Plug #2 entry — Aurora SG rule prune**: write `.claude/journals/architecture/2026-04-28-aurora-sg-rules-state-rm.md` BEFORE running `terraform state rm aws_security_group_rule.aurora_from_codebuild aws_security_group_rule.aurora_from_proxy`. Capture: original validation 2026-04-27 finding, why we accept reality (no CodeBuild→Aurora traffic in CloudTrail last 30d), conditions that would re-open the decision (CodeBuild starts failing on Aurora connection)
- [ ] **Plug #2 entry — telegram-api Lambda env-var trim-spec**: write `.claude/journals/architecture/2026-04-28-telegram-api-trim-spec.md` BEFORE editing `terraform/telegram_api.tf:149` (remove `OPENROUTER_API_KEY`) and `src/telegram_lambda_handler.py:80` (remove from `required_vars`). Capture: grep evidence that no FastAPI route consumes OpenRouter, why we don't trim PDF_STORAGE_BUCKET (real consumer at `src/api/transformer.py`), conditions to re-open (a Mini App endpoint that introduces LLM calls)
- [ ] Optional: mirror in `.claude/replicas/README.md` — one-paragraph "limits of replica-based audits" pointing back to the new section, so a future replica author inherits the taxonomy. Backlog priority.
- [ ] During monthly `/evolve docs`, audit the new section against current `projection.fingerprint_fields` in `.claude/replicas/dr-bot.yaml` for staleness in the field-coverage example.
- [ ] If a fifth blind-spot category emerges in practice, add it as a subsection rather than warping an existing one.

---

**References from this session**:

- `/validate` run that confirmed the doc gap — verdict: PARTIALLY TRUE (safety properties documented; epistemic limits poorly documented)
- `/evolve` docs that applied the change
- **Visual framework added 2026-04-29** — `.claude/commands/tf-aws.md` § "Visual framework — where each blind spot lives in the replica" — 4 ASCII visuals (replica 5-tuple, spatial picture, temporal picture for BS-2, decision tree). Driven by clarification that BS-3 is **narrower than first listed** (IAM policy attachments / SG rules / event source mappings are separate TF resource types and are caught by δ_membership, not BS-3). HTML's BS-3 cell tightened in the same pass.
- The three risk callouts from the absorb-reality reconciliation invariant verification
- Principle #25 (Behavioral Invariant Verification) — the framing this section composes with
- `.claude/replicas/dr-bot.yaml` `projection.fingerprint_fields` — referenced by the field-coverage subsection
- `.claude/replicas/README.md` Rule-of-Three deferral — context for why blind spots live in the command file, not yet in a kernel-level abstraction
