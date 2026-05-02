---
title: Patterns and principles learned while improving /tf-aws (2026-04-27 → 2026-05-01)
date: 2026-05-01
topic_slug: tf-aws-improvement-patterns
generated_by: /consolidate
---

# Consolidated Knowledge: Patterns learned while improving `/tf-aws`

## Information Sources

- **`.claude/commands/tf-aws.md`** — the skill doc (before and after this session's edits)
  - Relevant: contract surface that the patterns either repaired or extended
- **`.claude/replicas/dr-bot.yaml`** — the replica config (`x.files` schema added)
  - Relevant: showed where state-file metadata belongs (config, not algorithm-internal)
- **`.claude/journals/architecture/2026-04-30-legacy-state-cleanup.md`** + addendum — the Plug #2 record before the destructive verb
  - Relevant: demonstrated the "journal-before-rm" pattern in practice; addendum showed the "reality diverges from journal's count" recovery
- **`.claude/evolution/2026-05-01-tf-aws.md`** — drift report this session produced
  - Relevant: explicit before/after of every change; shows which assumptions were wrong
- **`docs/architecture/c4-plantuml/rendered/replica_explorer_dr-bot.html`** — Reconcile-tab tables
  - Relevant: Layer 4 ground truth surface; surfaced the "DIVERGED-IDS" case that pure-string comm misses
- **`/tmp/legacy.tfstate.json` + `/tmp/primary.tfstate.json`** — actual state files at audit time
  - Relevant: dry-run output revealed 18/3/3 (not journal's 14/2/0); the empirical correction
- **`.github/workflows/terraform-test.yml`** (commit `bf00ce4`) — backend-key correction
  - Relevant: institutional-memory artifact for the Phase F.5 sweep pattern
- **Conversation evidence** — user corrections that surfaced framing errors
  - "Edge A is very much needed" → BS-5 first-class promotion
  - "absorb HALT right away" → unmasked over-cautious time-buffer reasoning
  - "approach 2 strictly better" → forced refinement of the verified-orphan claim

---

## Tactical Understanding

### Core concept

Across this session, the work shifted `/tf-aws` from a two-axis audit (Edge B membership + Edge B fingerprint) to a three-axis audit (+ Edge A source-state). The shift surfaced multiple framing errors and added six structural mechanisms (Phase A.5, B3.5, F.5, H self-test; tri-state triage; codebase-aware drift inference). The Stage 1 dry-run and execution revealed a fourth membership category (HALT) and corrected the journal's count baseline.

### Key components added

1. **Phase A.5 (Edge A diff)** — HCL parse + diff produces UNREALIZED-INTENT and UNDECLARED-IMPORT.
2. **Phase B3.5 (reverse-reference walk)** — `incoming_refs` annotation; gates `delete-empty-shell` on closure.
3. **Phase D tri-state** — keep / delete / review families with explicit transitions.
4. **Phase D2 codebase-aware** — Lambda env drift gets per-key verdicts via grep.
5. **Phase F.5 backend-reference sweep** — refuses `--apply` if any CI entry point points at `deprecating` state.
6. **Phase H self-test** — coverage assertions; refuses ✅ if any assertion fails.
7. **`x.files: [{uri, role}]`** — replaces `x.primary` + `x.legacy` flat fields with role-aware list.
8. **HALT category** — fourth membership class beyond ORPHAN/GHOST/DOUBLE.

### Contradictions resolved

- **"Edge A is outside scope, run `terraform plan` separately"** vs. **"the project has shipped silent CI regressions because terraform plan was wrong-keyed for months"**
  - Resolution: bracketing-as-scope was a permission to skip; promoted Edge A to Phase A.5.
- **"DOUBLE means same address in both state files = safe to rm from either"** vs. **"OAI `webapp` binds to `ECE3O34PLCE64` in legacy and `E3TW52UDU2O6GX` in primary"**
  - Resolution: DOUBLE-by-address-only is too coarse; DIVERGED-IDS is a sub-case where the deprecating binding points at a *different* AWS object than the primary binding. State rm is still correct, but the dead AWS object becomes ORPHAN-DELETE, not no-op.
- **"14 DOUBLE / 2 GHOST"** (journal claim) vs. **"18 DOUBLE / 3 GHOST / 3 HALT"** (dry-run reality)
  - Resolution: Plug #2 addendum journal; promoted the journal's "Conditions to re-open" clause from advisory to operational gate.

### Gaps identified

- The skill's improvements are **doc-only** — Phase A.5, B3.5, F.5, H self-test, codebase-aware D2 are described in `tf-aws.md` but no code implements them yet. The 2026-05-01 dry-run was executed manually with `aws-cli` + `jq`. Implementation gap: each phase needs to live in actual executable form before the documented contract is enforceable.
- **Doppler injected-keys list is a comment**, not a structured config. Phase D2's codebase-aware logic depends on this list; it's currently per-Lambda informal knowledge.
- **Approach-2 import block flow not yet exercised** in this project. The pattern is documented; the first concrete use is the pending HALT re-absorb pass.

### Key insights

- ✅ Bracketing-as-scope ("X is outside this audit, do it elsewhere") is empirically a permission to skip. Promoting bracketed concerns to first-class is the structural fix.
- ✅ Every audit number is a *claim*, not a measurement. Treat coverage assertions as part of the audit, not as a separate trust exercise.
- ✅ Forward-walk discovery is for *finding* things; reverse-walk is for *safely deleting* things. Both are required.
- ✅ State is a cache of TF's belief about AWS; source is the contract. Mutating state without source = next plan proposes destroy. The user's intuition that "import tells terraform" is the most common terraform-import gotcha.
- ✅ "Verified orphan" needs unpacking: existence-verified ≠ field-values-verified. Auto-gen captures AWS reality; if AWS reality includes console drift, auto-gen codifies that drift.

### Open questions

- [ ] Should Phase A.5 / B3.5 / F.5 / H be implemented in a real `/tf-aws` executable (Python? Go?), or remain a doc that humans execute manually via aws/jq/terraform CLIs?
- [ ] When a second replica appears, does the `Replica` concept get promoted to a kernel-level type (Rule of Three trigger)?
- [ ] Should `state.role` have a `quarantined` value for state files we want to read (audit) but never write to under any condition?

---

## Strategic Patterns

### Pattern 1: Bracketing-as-scope is a permission to skip

**Intent**: detect when "out of scope, do it separately" framing in a contract becomes a license for the bracketed concern to never be done.

**When to use**:
- Reviewing contracts (skill docs, principles, runbooks) that explicitly bracket part of a problem as "do separately"
- After a silent regression — ask: was the gap that broke us "in scope" or "bracketed"?
- When a tool's contract claims completeness on a slice of the problem space

**Structure**:
```
1. List every "out of scope; use Y separately" sentence in the contract.
2. For each, audit how often Y is actually run alongside the contract.
3. If usage rate < 100%, the bracketing is operationally meaningless —
   either fold it in, or accept that the gap will recur.
```

**Concrete example from this session**:
- `/tf-aws` said: *"Edge A is outside this audit's input scope; its check is `terraform plan`."*
- Empirical check: `terraform plan` was wrong-keyed for months in CI; nobody ran it interactively as a paired check.
- Fix: promoted Edge A to first-class via Phase A.5 (HCL parse + diff).

**Related patterns**:
- "Verify the cheapest evidence first, then promote" — opposite direction; sometimes bracketing is correct because the bracketed check is genuinely independent.

---

### Pattern 2: Audit numbers are claims, assert before claiming ✅

**Intent**: prevent an audit/check from manufacturing false confidence by reporting a measurement that didn't actually happen.

**When to use**:
- Designing or reviewing any audit, scan, or coverage check
- After discovering "we audited X" but "X had a hidden subset that wasn't measured"
- Before relying on a tool's ✅ output as a green light for downstream destructive operations

**Structure**:
```
For every coverage number the tool prints, add an assertion:
  expected = config-derived count of what should have been hit
  actual   = runtime count of what actually was hit
  fail_if  = expected != actual

If any assertion fails, the tool refuses ✅ and exits non-zero.
The user must address the gap before any verdict is rendered.
```

**Concrete example**:
- 2026-04-28 audit reported 1 DRIFTED Lambda; 2026-04-30 reported 6. Delta wasn't new drift — it was newly-measured drift.
- Fix: Phase H self-test in `/tf-aws`. For "<N> TRACKED resources fingerprinted", assert `count(TRACKED of fingerprintable type) == N`. For "<K> state files read", assert `len(x.files) == K`. Etc.

**Related patterns**:
- BS-6 (audit-execution skew) is the named failure mode this pattern plugs.
- Principle #2 (Progressive Evidence Strengthening) operates within layers; this pattern operates *between* claim and measurement.

---

### Pattern 3: Reverse-reference walk before destructive verbs

**Intent**: prevent destructive operations from breaking peers that reference the deletion target.

**When to use**:
- Any tool proposing `delete-empty-shell` style verdicts
- When forward-walk discovery seems "complete" but the operation involves removal
- Before generating delete/destroy commands for resources that other resources may reference

**Structure**:
```
For each candidate-for-deletion resource r:
  1. Forward-walk r's outgoing refs (already done by discovery)
  2. Reverse-walk r's incoming refs:
     - SG: who lists this SG in their ingress/egress?
     - IAM role: who has this in AssumeRole / instance profile?
     - KMS key: who has it in KMSKeyArn / encryption config?
     - S3: who reads/writes this bucket?
  3. If incoming_refs is non-empty AND any entry is live in-scope,
     escalate from delete-empty-shell to review (or emit multi-step
     delete with revoke-then-delete commands)
```

**Concrete example**:
- `aws_security_group.line_bot_ticker_report` had 0 ENIs (forward-walk = empty)
- Reverse-walk: `sg-02530c9c16142e463` has an ingress rule referencing it
- Output upgraded from "delete SG" to two-step "revoke ingress + delete SG"
- Without reverse-walk, AWS would have rejected the delete OR deleted the SG and broken the peer.

**Related patterns**:
- Forward-walk discovery (Phase B3) is the structurally identical pattern in the *find-things* direction.
- `/impact` command in the kernel does this for code changes.

---

### Pattern 4: Plug #2 — journal before the destructive verb

**Intent**: preserve the *reason* a disagreement existed before the destructive verb erases the disagreement itself.

**When to use**:
- Any operation that collapses a contradiction by making one side smaller (state rm, terraform refresh, .tf trim, schema migration that drops a column)
- When the audit/check that surfaced the contradiction will return ✅ after the operation, even though the underlying intent is unrecoverable

**Structure**:
```
Before running the destructive verb:
  1. Write a journal capturing:
     - What the disagreement is right now
     - Which side wins (and why)
     - Conditions that would re-open the decision
     - Reversibility (where the bytes are; what restores them)
  2. The journal lives in .claude/journals/architecture/<date>-<slug>.md
  3. Only after journal is written → run the verb
  4. If reality diverges from the journal's claims (e.g., counts don't match)
     → Plug #2 addendum journal BEFORE proceeding
```

**Concrete example**:
- 2026-04-30 journal claimed 14 DOUBLE / 2 GHOST. Stage 1 dry-run revealed 18 DOUBLE / 3 GHOST / 3 HALT.
- Per the journal's own "Conditions to re-open" clause, halted before any rm.
- 2026-05-01 addendum journal captured the divergence + Option B decision before the 24-rm command fired.

**Related patterns**:
- BS-2 (post-action amnesia) is the named failure mode this pattern plugs.
- Backups (state file → `.terraform-state-backups/`) preserve *bytes*; journals preserve *reasons*. Both are needed.

---

### Pattern 5: State files are roles, not flat lists

**Intent**: encode lifecycle metadata about state files (or any pluggable backend) so audits, sweeps, and apply gates can reason about them.

**When to use**:
- When a system has multiple persistent stores of the same kind (multiple state files, multiple databases, multiple caches) at different lifecycle stages
- When operations need to behave differently per store (e.g., "writeable" vs "read-only-archival")
- After a regression caused by accidentally writing to the wrong store

**Structure**:
```yaml
# Old (flat):
x:
  primary: s3://...
  legacy:
    - s3://...

# New (role-aware):
x:
  type: tfstate
  files:
    - uri: s3://...
      role: primary       # canonical; new bindings land here
    - uri: s3://...
      role: deprecating   # being abandoned; refuse --apply against this
      reason: "..."
    # Future: role: archived (read for audit only; never written)
```

**Concrete example**:
- Pre-2026-05-01: `x.primary` + `x.legacy` was flat; the algorithm hard-coded "keep primary, drop from legacy"
- Post: `state.role` is a config-level concern. Phase F.5 (backend-reference sweep) refuses `--apply` if any CI entry point points at `role: deprecating`.

**Related patterns**:
- Compositional Hierarchy (Principle #28): role taxonomy is a Tier-0 atomic concept that other phases compose with.

---

### Pattern 6: State and source are different kinds of truth

**Intent**: prevent the most common terraform-import mistake (importing without source).

**When to use**:
- Any time you want to bring an existing AWS resource under TF management
- When explaining `terraform import` to someone whose intuition is "import = tell TF about the resource"
- When generating import commands programmatically (`/tf-aws absorb`)

**Structure**:
```
Two sources of truth in TF:
  - Source (.tf):     declarative intent — WHAT SHOULD EXIST
  - State (.tfstate): cache of TF's belief — WHAT TF TRACKS

terraform plan loop:
  for resource in state:
    if NOT in source: → propose DESTROY  ← the gotcha
    else:             → diff and propose update/no-op
  for resource in source:
    if NOT in state:  → propose CREATE

Therefore: importing without source = next plan tries to destroy.

Safe paths:
  Approach 1 (CLI):      write resource block FIRST, then `terraform import`
  Approach 2 (modern):   `import {}` block + `plan -generate-config-out`
                         → terraform writes the resource block from AWS
```

**Concrete example**:
- Stage 1 rm'd 3 HALT resources from deprecating state. They became true ORPHANs (live AWS, no state binding).
- Naïve next step: `terraform import aws_sqs_queue.report_jobs <url>`
- Result: state binding lands; next plan says "queue not configured in source → destroy"
- Catastrophe scope: live telegram queue would be deleted.
- Correct: declare in `.tf` (or auto-gen via `import {}` block), THEN apply/import.

**Related patterns**:
- BS-5 (source-state coverage) and Phase A.5 (UNREALIZED-INTENT / UNDECLARED-IMPORT) are how the audit *detects* mismatches between these two truths.

---

### Pattern 7: Auto-gen for verified orphans, hand-write for redesigns

**Intent**: choose between Approach 1 (hand-write resource block + CLI import) and Approach 2 (`import {}` block + `-generate-config-out`) based on whether AWS-current-state is the desired intent.

**When to use**:
- After membership audit confirms a resource exists in AWS but not in state ("verified orphan")
- When deciding between hand-shaping config vs auto-generating

**Structure**:
```
Approach 2 wins when:
  - Existence-verified AND every-field-aligned-with-intent
  - Resource is load-bearing in production (current AWS state IS the spec)
  - Many similar resources to absorb (auto-gen scales)
  - terraform >= 1.5

Approach 1 wins when:
  - Suspect console drift you want to NOT codify
  - Want to seed a redesign (current AWS state is incidental, not aspirational)
  - Heavy use of variables/locals you want to factor in
  - terraform < 1.5

Both ALWAYS require source; the difference is who writes it (you vs terraform).
```

**Concrete example**:
- 3 HALT-now-ORPHAN resources (active telegram queue + DLQ + alarm)
- Production load-bearing for months → AWS state IS intent
- Approach 2 chosen: `import {}` block + `-generate-config-out` produces 3 resource stubs in one pass

**Related patterns**:
- Pattern 6 (state vs source) is the precondition: both approaches still need a resource block.
- Compositional Hierarchy: Approach 2 is Tier-1 (composes Approach 1's atomic primitives — import command, resource block — into a single declarative operation).

---

### Pattern 8: Backend-reference sweep as institutional memory

**Intent**: turn the latest "wrong state file" regression into a fail-closed gate that prevents the class of bug from recurring.

**When to use**:
- Any time a regression is traced to "wrong endpoint / wrong store / wrong key was used"
- Before any mutating verb against a multi-store system
- When config files reference endpoints by string (path, key, URI)

**Structure**:
```
sweep_paths = [all known entry points that init the backend]
For each path:
  grep for backend-key references
For each reference:
  Cross-check against config (e.g., state.role)
  If reference points to a deprecating/archived/forbidden entry:
    → REFUSE --apply
    → Override available with explicit --allow-X flag (loud, audit-logged)

This phase IS the institutional memory of the failure mode.
Updating the sweep_paths list when a new entry-point class appears
is mandatory after every related incident.
```

**Concrete example**:
- 2026-04-30: `.github/workflows/terraform-test.yml` had `key="dev/terraform.tfstate"` (deprecating) for months.
- Fix: commit `bf00ce4` redirected to primary.
- Pattern: Phase F.5 sweep added to `/tf-aws` to fail-close on this class of bug.

**Related patterns**:
- Pattern 1 (bracketing-as-scope): this pattern is the converse — fold the gate into the tool, don't bracket "developers must check this separately."

---

### Pattern 9: Direction-of-change inference using available context

**Intent**: reduce the size of the human "review queue" produced by an audit by using project-specific context to disambiguate ambiguous verdicts.

**When to use**:
- Any verdict-default-of-`review` that fires often enough to clog the queue
- When the project has structured context (codebase, CloudTrail, Doppler config) that could disambiguate
- When the abstract tool can't tell, but a project-aware heuristic could

**Structure**:
```
Default verdict: review (when intent is ambiguous from a single snapshot)

Refinement layer (project-specific):
  For each `review` candidate:
    Pull project-specific context:
      - Codebase grep (used in code? where?)
      - CloudTrail (who/what/when changed it?)
      - Config sources (Doppler, .env files, ...)
    Apply per-context heuristic:
      Lambda env drift:
        used_in_code AND not_in_doppler_set     → apply-tf
        used_in_code AND in_doppler_set         → trim-spec
        not_used_in_code                        → trim-spec
        in_aws_only AND used_in_code            → refresh-tf
        residual                                → review (genuinely ambiguous)

Effect: the human only sees the residue.
```

**Concrete example**:
- Pre-D2: 16-key Lambda env drift on telegram_api → all `review` → 30 min of manual grep per Lambda
- Post-D2: codebase grep + Doppler injected-keys set produces per-key verdict; ~80% auto-classified

**Related patterns**:
- Pattern 4 (Plug #2): when D2 is wrong, the journal preserves the human's correction for future tuning.

---

### Pattern 10: HALT — a fourth membership category that demands explicit direction

**Intent**: name the "legacy-only with live AWS" case so it doesn't get silently treated as DOUBLE-or-GHOST and processed naively.

**When to use**:
- Any reconciliation between two stores of bindings (state files, indexes, caches)
- When the obvious 2×2 truth table (in-A, in-B, in-both, in-neither) has a hidden subcase

**Structure**:
```
Membership categories on (TFM, LIVE):
  in TFM AND in LIVE        → TRACKED                     (vanilla)
  in TFM AND not in LIVE    → GHOST                       (state-rm safe)
  not in TFM AND in LIVE    → ORPHAN                      (import or delete)
  not in TFM AND not in LIVE → not in scope               (-)

Membership categories on (TFM_primary, TFM_deprecating, LIVE):
  in primary AND in deprecating       → DOUBLE            (state-rm from deprecating)
  in primary only                      → vanilla TRACKED
  in deprecating only AND in LIVE      → HALT  ← named 2026-05-01
  in deprecating only AND not in LIVE  → GHOST (same as before)

Without naming HALT, the dry-run would have processed those entries
as either "DOUBLE" (would've left them un-managed) or "ORPHAN-to-import"
(would've crashed on no source). Naming it forces an explicit choice.
```

**Concrete example**:
- 3 entries in deprecating ONLY, with live AWS counterparts (telegram queue + DLQ + alarm)
- Three options surface explicitly: import-then-rm, rm-then-reabsorb (Option B chosen), defer
- Without HALT as a named category, these 3 would have been mishandled silently.

**Related patterns**:
- Pattern 6 (state vs source): HALT highlights why "state binding == management" is a useful invariant.
- Pattern 5 (state.role): HALT is more meaningful when state files have explicit roles.

---

### Pattern 11: DIVERGED-IDS — same address, different IDs

**Intent**: prevent address-level set comparison from masking instance-level divergence.

**When to use**:
- Any time you compute `set_a ∩ set_b` over addresses
- When two stores of bindings nominally use the same key space
- When deduplication logic ("keep one, drop the other") could pick wrong if the items aren't actually the same

**Structure**:
```
Naïve DOUBLE detection:
  comm -12 (sort addresses_in_a) (sort addresses_in_b)

Refined DOUBLE detection:
  for each address in (set_a ∩ set_b):
    id_a = lookup(a, address)
    id_b = lookup(b, address)
    if id_a == id_b:
      classify as VANILLA-DOUBLE
    else:
      classify as DIVERGED-IDS
      → state-rm from deprecating leaves the deprecating-bound AWS resource
        as a true ORPHAN-DELETE (advisory)
```

**Concrete example**:
- `aws_cloudfront_origin_access_identity.webapp` bound to `ECE3O34PLCE64` (legacy) and `E3TW52UDU2O6GX` (primary)
- Same address, different AWS objects
- `state rm` from deprecating is still correct (the dead OAI loses its sole binding); but the dead OAI then needs an advisory delete in AWS, which a vanilla DOUBLE wouldn't.

**Related patterns**:
- Pattern 10 (HALT): both are sub-categories that pure-string set difference misses.

---

### Pattern 12: Layer 4 invariant assertion AROUND the destructive verb

**Intent**: prove the operation did the thing it claimed to do, AND didn't do anything it shouldn't.

**When to use**:
- Every destructive operation that has a measurable before/after state
- When the operation has invariants (things that must NOT change) alongside changes

**Structure**:
```
BEFORE the verb:
  before_state = capture_measurable_state(all_relevant_subjects)
  log(before_state)

EXECUTE verb

AFTER the verb:
  after_state = capture_measurable_state(all_relevant_subjects)
  assert deltas_intended(before_state, after_state)
  assert invariants_held(before_state, after_state)
  log(after_state, deltas, invariants_status)

Failure of either assertion → operation is in undefined state →
restore from backup or surface for human triage.
```

**Concrete example**:
- Stage 1 mutation:
  - Intended delta: deprecating managed-resource count 24 → 0
  - Invariant: primary managed-resource count 208 → 208 (unchanged)
- Both verified post-rm via re-download + jq count.
- Bonus invariant: 3 HALT AWS resources still alive (Option B requires no AWS-side change) — verified via AWS API checks.

**Related patterns**:
- Principle #2 (Progressive Evidence): this pattern is Layer 4 specifically.
- Principle #25 (Behavioral Invariant Verification): this pattern is the "before claiming done, verify the invariant envelope" rule applied to a single operation.

---

## Metadata

**Generated**: 2026-05-01
**Topic**: Patterns and principles learned while improving /tf-aws
**Slug**: tf-aws-improvement-patterns
**Sources**: 8 files/references
**Patterns Extracted**: 12 reusable patterns
