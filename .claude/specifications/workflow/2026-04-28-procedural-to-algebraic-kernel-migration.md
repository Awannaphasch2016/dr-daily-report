---
title: Procedural → Algebraic Kernel Migration
focus: workflow
date: 2026-04-28
status: draft (planning only — DO NOT IMPLEMENT YET)
tags: [agent-kernel, type-system, principles, meta-architecture]
prior_art:
  - .claude/CLAUDE.md (Principles #25, #26, #27, #28)
  - .claude/abstractions/architecture-2026-04-27-nl-slash-command-interface.md (if written)
  - Conversation 2026-04-27 → 2026-04-28 deriving the typed-kernel proposal
---

# Specification: Procedural → Algebraic Kernel Migration

## TL;DR

Today the Agent Kernel exposes ~40 slash commands as a flat list of verbs that take loosely-typed prose. Underneath, every operation is some flavor of *"compute or apply δ between two representations under a policy."* That implicit structure is **already typed** — but the types are not named, not declared, and not used in command signatures.

This spec captures a **5-phase plan** to make those types explicit, lift the kernel from a procedural collection of commands to an algebra of typed primitives + typed combinators.

**Status**: planning artifact only. Do not begin implementation without a separate go-ahead.

---

## Goal

Promote the kernel's implicit type structure to explicit first-class primitive types, give every command a typed signature, and refactor existing commands to be specializations within a small algebra. After migration:

- The kernel exposes ~10 named primitive types (nouns) and a smaller set of typed verbs over them
- New commands have a *determined place* in the taxonomy, not an invented one
- Documentation density improves — types are documented once, commands become brief signatures
- Composition rules become checkable (statically or via review)
- Principles #25–#28 stop *gesturing* at this structure and start *being* it

---

## Why now (and why "later," not "now")

### Why now (eventually)

1. **The implicit types have stabilized.** Throughout 2026-04 we used `Replica`, `Delta`, `Policy`, `Projection`, `Source`, `Invariant`, `Tuple` consistently as English nouns across many discussions. The vocabulary is converged.
2. **Tier-0 principles haven't churned in months.** The kernel is past experimentation; cost of formalization is low.
3. **New commands are getting hard to place.** When `/replica`, `/diff`, `/converge` were proposed, the question "do these duplicate `/merge`, `/adapt`, `/reconcile`?" took a long discussion to resolve. A type system would answer it in one line.
4. **Principles #25–#28 are already type-shaped.** They define `δ`, `Members`, `Invariant`, `Tuple` informally. The lift is small.

### Why **later**, not now

1. **Concurrent work in flight.** `report_pipeline.tf` migration is unfinished; orphan-import is queued; multiple validations are pending. Kernel-level changes during active feature work amplify risk.
2. **Type system is reversible if delayed but not if rushed.** Taking another week to land it costs nothing; landing it half-baked locks in wrong choices.
3. **One real-world driver should land first.** Adding `/replica` as the first typed command (under the proposed system) is a more honest test than retrofitting the type system to existing commands.

---

## Current state vs target state

### Current state (procedural kernel)

```
┌──────────────────────────────────────────────────────────┐
│  Tier-0 Principles (#1, #2, #18, #20, #23, #25–#28)      │
├──────────────────────────────────────────────────────────┤
│  Slash commands (flat list, ~40)                         │
│  - Each has prose description                            │
│  - Each takes a free-form NL string                      │
│  - "Tuple Effects" tables describe state changes         │
│  - No signatures, no static composition checks           │
├──────────────────────────────────────────────────────────┤
│  Skills, observations, journals, validations, etc.       │
└──────────────────────────────────────────────────────────┘

Implicit (un-named) types in use:
  Source, Replica, Delta, Policy, Projection,
  Invariant, Tuple, Strategy, Mode
```

### Target state (algebraic kernel)

```
┌──────────────────────────────────────────────────────────┐
│  Tier-0 Principles (#1, #2, #18, #20, #23, #25–#29)      │
│    NEW: #29 — Kernel Operates on Typed Primitives        │
├──────────────────────────────────────────────────────────┤
│  PRIMITIVE TYPE LAYER (NEW)                              │
│  - Source, Replica, Delta, Policy, Projection,           │
│    Invariant, Tuple, Strategy, Mode                      │
│  - Each has its own .claude/types/<name>.md              │
│  - Total: ≤10 types (hard cap to prevent sprawl)         │
├──────────────────────────────────────────────────────────┤
│  Slash commands (same surface, typed underneath)         │
│  - /diff   : Replica → Delta                             │
│  - /converge : Replica × Apply? → Replica                │
│  - /merge  : Source × Source × Strategy → Source         │
│  - /reconcile : Source × Invariant → Source              │
│                  ≡ /converge with policy=conform         │
│  - /move, /adapt, /provision-env: Source → Source family │
│  - /replica : Source × Source × Projection × Policy →    │
│               Replica (constructor for the new noun)     │
├──────────────────────────────────────────────────────────┤
│  Skills, observations, journals, validations, etc.       │
└──────────────────────────────────────────────────────────┘
```

---

## Migration plan (5 phases)

Each phase is independently valuable and independently revertible. Stop at any phase if value/cost balance changes.

### Phase 1 — NAME (~1 day)

**What**: Write `.claude/types/<type>.md` for each primitive — one paragraph each, no enforcement.

**Files to create** (10 files, ~1 paragraph each):

| File | Type purpose |
|---|---|
| `.claude/types/source.md` | A representation: file path, URL, AWS account scope, Doppler config, etc. |
| `.claude/types/replica.md` | Pair of `Source`s + `Projection` + `Policy`; the unit of paired-state reconciliation |
| `.claude/types/delta.md` | Result of comparing two `Source`s under a `Projection` |
| `.claude/types/policy.md` | Reconciliation rule: `conform`, `absorb-reality`, `LWW`, `merge`, `tombstone-aware`, ... |
| `.claude/types/projection.md` | `Source → CompactForm` mapping; defines what "same" means for δ |
| `.claude/types/invariant.md` | Predicate over a `Source` or `Replica`; the spec side of Principle #25 |
| `.claude/types/tuple.md` | `(Constraints, Invariant, Principles, Strategy, Check)` — Principle #26 |
| `.claude/types/strategy.md` | `list[Mode]` — pipeline of typed commands |
| `.claude/types/mode.md` | A typed slash command (`/explore`, `/converge`, etc.) |
| `.claude/types/README.md` | Index + composition rules + cross-references |

**Acceptance criteria**:
- [ ] All 10 files exist
- [ ] Each names: definition, examples, what it composes with
- [ ] README cross-references which command operates on which type
- [ ] Phase 1 alone returns most of the value — clearer thinking, no kernel changes

**Reversal**: delete `.claude/types/`. Zero impact on running commands.

---

### Phase 2 — ANNOTATE (~2 days)

**What**: Add a `## Signature` section to each existing command file. Type-signature only, not enforced.

**Files to edit** (top priority — Tier-0 + most-used):

| Command | Proposed signature |
|---|---|
| `/merge` | `Source × Source × Strategy → Source` |
| `/move` | `Source → Source` (preserve identity) |
| `/adapt` | `Source × Shape → Source` (preserve information, change form) |
| `/provision-env` | `Source × Env → Source` (copy with env-specific substitution) |
| `/reconcile` | `Source × Invariant → Source` (≡ converge with conform) |
| `/invariant` | `Goal → Invariant` |
| `/validate` | `Claim → Verdict` |
| `/step` | `Tuple → Tuple` |
| `/explore` | `Constraints → list[Alternative]` |
| `/consolidate` | `list[Alternative] → Decision` |
| `/what-if` | `Scenario → ImpactAnalysis` |
| `/decompose` | `Goal → list[SubGoal]` |
| `/observe` | `Event → Observation` |
| `/abstract` | `list[Observation] → Pattern` |

**Acceptance criteria**:
- [ ] Every command in the table above has a `## Signature` section
- [ ] Signatures use only Phase-1 primitive types (forces them to be sufficient)
- [ ] If a command can't be expressed cleanly, that's a flag — note it in `.claude/types/_open_questions.md`
- [ ] No runtime behavior change

**Reversal**: revert the per-command edits; types still stand from Phase 1.

---

### Phase 3 — ADOPT (~2 days)

**What**: Implement the three new commands (`/replica`, `/diff`, `/converge`) **natively** against the typed system from Phase 1. They should *be* the first commands designed type-first.

**Files to create**:

| File | Type signature |
|---|---|
| `.claude/commands/replica.md` | Constructor: `Source × Source × Projection × Policy → Replica` |
| `.claude/commands/diff.md` | `Replica → Delta`  *(also accepts `Source × Source × Projection`)* |
| `.claude/commands/converge.md` | `Replica × Apply? → Replica` |
| `.claude/replicas/README.md` | Replica registry directory; declared replicas live here |

**Each command file must include**:
- `## Signature` section (using Phase-1 types)
- `## NL Surface` (natural-language input examples that resolve to the typed form — see `.claude/abstractions/architecture-2026-04-27-nl-slash-command-interface.md`)
- `## Tuple Effects` (what changes in the Thinking Tuple)
- `## Local Check` (mode completion criteria)
- Worked examples showing the NL→typed→executor pipeline

**Acceptance criteria**:
- [ ] `/replica declare` writes to `.claude/replicas/<name>.md`
- [ ] `/diff <name>` reads the declaration and computes δ
- [ ] `/converge <name> --apply` reads, computes, applies the policy
- [ ] All three commands accept NL surface AND structured-flag form
- [ ] First demonstrable replica: `dr-bot-tf-vs-aws` (the TF-state ↔ AWS reality pair we discussed)

**Reversal**: delete the three command files + `.claude/replicas/`. No impact on existing commands.

---

### Phase 4 — REFACTOR (~3 days)

**What**: Re-express existing commands as specializations within the type algebra. Make the algebra real, not just declared.

**Concrete refactors**:

| Existing command | Becomes |
|---|---|
| `/reconcile X` | Syntactic sugar for `/converge (replica.from(spec, reality, π, conform))` |
| `/invariant goal` | Returns an `Invariant` (typed object), not just prose |
| `/move src dst` | Specialization of `/merge` with `strategy=preserve` (already documented; now enforced via signature) |
| `/adapt src shape` | Specialization of `/merge` with `strategy=adapt` |
| `/provision-env src env` | Specialization of `/merge` with `strategy=copy-with-env-substitution` |

**Update Principle #25 (Behavioral Invariant Verification)**:
- Today it's specialized to one twin: `spec ↔ reality`
- After: it becomes a special case of the general `Replica` type with `policy=conform`
- The math (`δ(member, Invariant) = 0`) is unchanged; only the framing widens

**Update Principle #26 (Thinking Tuple)**:
- Today the `Check` slot uses `δ(state, invariant)` (one twin)
- After: `Check` is polymorphic over any `Replica`'s `Delta`

**Update Principle #28 (Compositional Hierarchy)**:
- Add the type layer between Tier-0 (atomic) and Tier-1 (specialized)
- Document the `composes / depends / invokes / grounds` relationships using the type system

**Acceptance criteria**:
- [ ] `/reconcile` documented as alias for `/converge --policy=conform`
- [ ] Principle #25 generalized to any Replica (not just spec↔reality)
- [ ] Principle #26 Check slot documented as polymorphic over Replicas
- [ ] No runtime behavior change for existing commands (compatibility preserved)
- [ ] At least one cross-domain Replica declared and exercised:
  - Required: `terraform-vs-aws-{dev}`
  - Stretch: `spec-vs-implementation`, `migration-vs-schema`, `cache-vs-source`

**Reversal**: hardest to reverse. By Phase 4 the type system is load-bearing. Plan accordingly.

---

### Phase 5 — ENFORCE *(optional, far later)* (weeks)

**What**: Build a static checker that validates command pipelines against types. Reject ill-typed compositions before runtime.

**Skip unless** pipelines actually grow complex enough to warrant it. Likely overkill for current usage; documented for completeness.

**If pursued**:
- Build a Python script `scripts/typecheck_kernel.py` that parses command files for `## Signature` blocks and validates pipelines in `## Strategy` chains
- Integrate into pre-commit hook
- Generate visual type-flow diagrams for documentation

**Acceptance criteria**: deferred indefinitely.

---

## New Tier-0 principle to add

### Principle #29 — Kernel Operates on Typed Primitives

```
The Agent Kernel exposes a fixed set of named primitive types
(Source, Replica, Delta, Policy, Projection, Invariant, Tuple,
Strategy, Mode). All commands have signatures expressed in these
types. New commands SHOULD compose from existing types, NOT
introduce new ones. The hard cap is 10 primitive types.

Rationale: when type set is small and stable, command placement
becomes a determined question (what's the signature?) rather
than an invented one (where does this fit?). Composition
becomes checkable. Documentation density improves.

Enforcement: review-time. New types require a Tier-0 principle
update; new commands without signatures are rejected.
```

**Where it fits**: alongside #28 (Compositional Hierarchy) — they reinforce each other.

---

## Boundary conditions (hard constraints)

| Constraint | Why |
|---|---|
| **≤10 primitive types** | Beyond 10, the type system collapses under its own weight. If a new domain needs 3 new types, redesign — don't just add. |
| **No runtime behavior change in Phases 1–4** | Migration must be invisible to existing users. Only docs, signatures, and new commands change. |
| **NL surface preserved** | Every command keeps its English-prose interface (per the NL-Slash-Command pattern). Type signatures are *internal calling convention*, never the surface. |
| **Reversibility per phase** | Each phase must be independently revertible. No phase locks in the next. |
| **Dogfood with `/replica`** | `/replica` (Phase 3) is the test that the type system can support a real, novel command. If `/replica` is awkward to express, the type system needs revision before Phase 4. |

---

## Open questions

- [ ] **Q1 — Substrate vs Source**: Should `Source` be split into `(Identity, Substrate, Representation)`? Cleaner taxonomically, but pushes total count past 10. Resolve before Phase 1.
- [ ] **Q2 — Policy registry**: Should `Policy` be a closed set (`conform`, `absorb-reality`, `LWW`, `merge`, `tombstone-aware`) or open? Open is more flexible; closed is more checkable. Lean closed at start, open later if needed.
- [ ] **Q3 — Tuple as type or sui generis**: `Tuple` is described as `(C, I, P, S, Check)`. Is it a primitive type or a derived struct? Argument for primitive: every reasoning episode runs through it. Argument for derived: it's a record of the others.
- [ ] **Q4 — Mode signature self-reference**: `/step : Tuple → Tuple` is fine, but a `Mode` operates on a Tuple AND is part of a `Strategy` AND a `Strategy` is part of a Tuple. Circular but well-founded. Document the recursion explicitly to avoid confusion.
- [ ] **Q5 — Migration of in-flight specs**: existing specifications in `.claude/specifications/` reference commands by name. Will their meaning shift after Phase 4? Spot-check a sample before committing.
- [ ] **Q6 — Audience friction**: Type signatures may alienate users who don't think in types. Should we hide signatures behind a `## Advanced` collapse? Decide during Phase 2 based on reviewer feedback.
- [ ] **Q7 — Tooling vs prose**: Phase 5 (enforcement) is optional. Does Phase 4 acceptance require ANY automated check, or is review-time enforcement sufficient? Default: review-time, escalate to tooling only if drift accumulates.

---

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Type set explodes past 10 | Medium | High — defeats the whole purpose | Hard cap. Force consolidation. Reject new types in review. |
| Phase 4 breaks existing commands | Low | High | Phase 4 is doc-only refactor. Signatures don't change runtime. |
| Users find typed signatures alienating | Medium | Medium | Keep NL surface; signatures are internal. Hide behind collapse if needed. |
| Phases drift apart in time | High | Medium | Each phase is independently valuable. Acceptable to stop at any phase. |
| Concurrent feature work conflicts | High | Medium | Run during a quiet feature week. Don't interleave with active Tier-0 churn. |
| Future kernel evolutions don't fit the type system | Medium | High | Treat type set as living. Allow Tier-0 principle update to add a type — but require evidence of recurring need. |

---

## Dependencies / prerequisites

Before starting Phase 1:
- [ ] No active Tier-0 principle changes in flight
- [ ] No major command additions in flight
- [ ] At least one real-world driver for `/replica` exists (we have one: `dr-bot-tf-vs-aws`)
- [ ] Verbal commitment from human reviewer that "yes, the type-set is stable enough to formalize"
- [ ] (Optional) Prior conversation notes from 2026-04-27/28 archived for context

---

## Acceptance criteria (overall migration)

The migration is complete (Phase 1–4) when ALL of the following hold:

- [ ] `.claude/types/` directory exists with ≤10 type files + README
- [ ] Every command in the priority list has a `## Signature` section
- [ ] `/replica`, `/diff`, `/converge` are implemented and exercised against `dr-bot-tf-vs-aws`
- [ ] `/reconcile` is documented as syntactic sugar over `/converge --policy=conform`
- [ ] Principles #25, #26, #28 are updated to reference the type system
- [ ] Principle #29 is added to Tier-0
- [ ] At least one cross-domain Replica beyond TF↔AWS is declared (e.g., `spec-vs-code`)
- [ ] No runtime regressions in existing commands
- [ ] `.claude/CLAUDE.md` Quick Principle Reference table updated to include #29

---

## Next steps (when ready to start)

1. **Re-read this spec** — confirm rationale still holds
2. **Resolve open questions Q1–Q3** (the structural ones) before any file is written
3. **Execute Phase 1** — name the types, write the 10 files, ship as one PR
4. **Pause and review** — does naming alone return value? If yes, continue. If no, stop.
5. **Execute Phase 2** — annotate signatures, ship as one PR
6. **Execute Phase 3** — implement `/replica`/`/diff`/`/converge`, ship as one PR
7. **Execute Phase 4** — refactor existing commands + update principles, ship as one PR
8. **Skip Phase 5** unless complexity demands it

---

## References

- **Conversation that derived this**: 2026-04-27 → 2026-04-28 session, focusing on TF state vs AWS reality reconciliation, generalized to a typed paired-state abstraction
- **Principles to evolve**: #25 (Behavioral Invariant Verification), #26 (Thinking Tuple Protocol), #27 (Commands as Strategy Modes), #28 (Compositional Hierarchy)
- **Related abstractions**:
  - NL-Slash-Command Interface pattern (deferred — write under `.claude/abstractions/architecture-2026-04-27-nl-slash-command-interface.md`)
  - Untracked-Resource Discovery via Push/Observer Duality (deferred — write under `.claude/abstractions/workflow-2026-04-27-untracked-resource-discovery.md`)
- **First real driver**: `dr-bot-tf-vs-aws` Replica — absorb deployed AWS resources into Terraform state for the dr daily report bot
- **Related validation**: `.claude/validations/2026-04-27-terraform-state-vs-deployed-infra.md` — drift evidence motivating the `/replica` use case

---

## Status note

**This spec is planning artifact only.** Do not begin implementation without explicit user approval. The Phase-1 step alone (~1 day, naming types, no behavior change) is the natural starting point when you're ready.

When ready to start: re-read this file, resolve Q1–Q3, then proceed to Phase 1.
