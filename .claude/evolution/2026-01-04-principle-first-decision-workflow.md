# Evolution: Principle-First Decision Workflow Analysis

**Date**: 2026-01-04
**Type**: Workflow Evolution Proposal
**Status**: 🔍 Analysis Complete - Recommendation: SELECTIVE ENFORCEMENT

---

## User Proposal

> "I think /check-principles are required before any decision making to make sure that decisions are aligned with our believe. do you think we should adjust .claude/*, skills, slash command to follow reflect on principles → think → make decision → execute"

**Proposed workflow**:
```
Step 1: Reflect on Principles (/check-principles)
Step 2: Think (analysis, exploration)
Step 3: Make Decision (choose path)
Step 4: Execute (implement decision)
```

---

## Executive Summary

**Recommendation**: **SELECTIVE ENFORCEMENT** - Not all decisions need `/check-principles`, but critical decision types should enforce it.

**Rationale**:
- ✅ **Deploy decisions**: Already enforces `/check-principles` (correct pattern)
- ⚠️ **Architecture decisions**: Should add `/check-principles` gate
- ⚠️ **Problem-statement decisions**: Should reference principles in decision framework
- ❌ **Tactical decisions**: Over-engineering to enforce (file naming, refactoring scope)
- ❌ **Research/exploration**: Premature optimization (still gathering information)

**Classification**: 3 decision tiers with different principle-checking requirements

---

## Current State Analysis

### Commands That Make Decisions

| Command | Decision Type | Current Workflow | Principle Check? |
|---------|---------------|------------------|------------------|
| `/deploy` | **STRATEGIC** - Infrastructure/deployment | `/check-principles` → plan → approve → execute | ✅ YES (enforced) |
| `/architect` | **STRATEGIC** - Architecture patterns | research → components → boundaries → trade-offs | ❌ NO |
| `/problem-statement` | **STRATEGIC** - Technology/approach | identify → trace → gather → restate → framework | ❌ NO |
| `/what-if` | ANALYTICAL - Alternative evaluation | scenario → outcomes → comparison → recommendation | ❌ NO |
| `/explore` | RESEARCH - Multi-angle exploration | perspectives → alternatives → synthesis | ❌ NO |
| `/abstract` | PATTERN - Pattern extraction | detect → classify → template | ❌ NO |
| `/restructure` | TACTICAL - Code refactoring | analyze → hotspots → recommendations | ❌ NO |

### Skills That Make Decisions

| Skill | Decision Type | Current Workflow | Principle Check? |
|-------|---------------|------------------|------------------|
| `deployment` | **STRATEGIC** - Deployment execution | validate → plan → execute → verify | ✅ YES (via /deploy) |
| `research` | RESEARCH - Investigation | observe → hypothesize → research → validate | ❌ NO |
| `code-review` | QUALITY - Code assessment | security → performance → patterns → testing | 🟡 IMPLICIT (checks against principles) |
| `error-investigation` | DEBUGGING - Root cause analysis | observe → trace → validate → fix | ❌ NO |
| `frontend-design` | CREATIVE - UI/UX design | requirements → design → implement | ❌ NO |

---

## Analysis: Where Principle-Checking Adds Value

### Tier 1: STRATEGIC Decisions (MUST check principles)

**Characteristics**:
- High impact (affects system architecture, infrastructure, or operations)
- Long-term consequences (difficult/expensive to reverse)
- Multi-stakeholder (affects team, users, or infrastructure)
- Risk of principle violation causes major issues

**Examples**:
- Deployment changes (Lambda config, Terraform changes, Docker images)
- Architecture decisions (microservices vs monolith, sync vs async, caching strategy)
- Technology selection (database choice, queue system, CDN provider)
- Process changes (deployment workflow, testing strategy, error handling)

**Current coverage**:
- ✅ `/deploy` - Enforces `/check-principles` (scope: DEPLOYMENT)
- ❌ `/architect` - Missing principle check
- ❌ `/problem-statement` - Missing principle reference

**Why principle-checking helps**:
- Prevents deployment failures (Principle #15: Infrastructure-Application Contract)
- Ensures monitoring discipline (Principle #6: Deployment Monitoring Discipline)
- Validates boundary testing (Principle #19: Cross-Boundary Contract Testing)
- Checks artifact promotion (Principle #11: Artifact Promotion Principle)

**Recommendation**: ✅ **ENFORCE** `/check-principles` before strategic decisions

---

### Tier 2: ANALYTICAL Decisions (SHOULD reference principles)

**Characteristics**:
- Medium impact (affects code quality, performance, or maintainability)
- Reversible (can change approach without major cost)
- Developer-facing (affects how we write code, not what system does)
- Principle violations create technical debt, not system failures

**Examples**:
- Refactoring approach (extract function vs class, naming conventions)
- Test strategy (unit vs integration, mocking approach)
- Code organization (file structure, module boundaries)
- Error handling patterns (exceptions vs error codes)

**Current coverage**:
- 🟡 `/what-if` - Implicit (compares alternatives, but doesn't cite principles)
- 🟡 `code-review` - Implicit (checks patterns, but doesn't enumerate principles)
- ❌ `/restructure` - No principle reference

**Why principle-checking helps**:
- Ensures defensive programming (Principle #1: Fail fast and visible)
- Validates error handling (Principle #8: Error Handling Duality)
- Checks logging patterns (Principle #18: Logging Discipline)
- Verifies test quality (Principle #10: Testing Anti-Patterns Awareness)

**Recommendation**: 🟡 **REFERENCE** principles in decision framework (not enforced gate, but included in analysis)

---

### Tier 3: TACTICAL/RESEARCH Decisions (NO principle check needed)

**Characteristics**:
- Low impact (local changes, exploratory work)
- Highly reversible (git revert, quick iteration)
- Learning/discovery phase (don't know what the decision is yet)
- Principle violations would be caught in code review or testing

**Examples**:
- File naming (use snake_case or kebab-case for this file?)
- Variable naming (call it `result` or `output`?)
- Exploration (which files handle authentication?)
- Research (how does this library work?)
- Debugging (what's causing this error?)

**Current coverage**:
- ✅ `/explore` - Correctly omits principle check (research phase)
- ✅ `/research` skill - Correctly omits principle check (investigation)
- ✅ `/trace` - Correctly omits principle check (debugging)
- ✅ `/hypothesis` - Correctly omits principle check (hypothesis generation)

**Why principle-checking doesn't help**:
- Decision scope too small to violate principles
- Enforcement adds friction without benefit
- Code review catches issues later
- Slows iteration during learning/debugging

**Recommendation**: ❌ **NO ENFORCEMENT** - Principle checks add overhead without value

---

## Detailed Recommendations

### Recommendation 1: Enforce `/check-principles` for Strategic Decisions

**Commands to modify**:

#### `/architect` - Add Phase 0: Principle Compliance Check

**Before**:
```markdown
### Phase 1: Component Identification
Identify all system components...
```

**After**:
```markdown
### Phase 0: Principle Compliance Check (Pre-Analysis)

**Run compliance audit** (for architecture decisions):

/check-principles
  Scope: ARCHITECTURE
  Principles audited: #3, #5, #19, #20

**Architecture-specific principles**:
- ✅ Principle #3: Aurora-First Data Architecture
- ✅ Principle #5: Database Migrations Immutability
- ✅ Principle #19: Cross-Boundary Contract Testing
- ✅ Principle #20: Execution Boundary Discipline

**Output**: Compliance status before architectural analysis begins

If CRITICAL violations found: Address before proceeding with architecture analysis

---

### Phase 1: Component Identification
Identify all system components...
```

**Integration**:
```yaml
# .claude/commands/architect.md frontmatter
composition:
  - command: check-principles
    args: "architecture"
  - skill: research
```

#### `/problem-statement` - Add Principle Reference in Decision Framework

**Before**:
```markdown
### Phase 5: Present Decision Framework

## Option 1: {Option name}
**Pros**: ...
**Cons**: ...
**Best for**: ...
**Not good for**: ...
```

**After**:
```markdown
### Phase 5: Present Decision Framework

**Relevant principles** (from CLAUDE.md):
- Principle #{N} ({Name}): {How it applies to this decision}
- Principle #{M} ({Name}): {How it applies to this decision}

## Option 1: {Option name}
**Pros**: ...
**Cons**: ...
**Principle alignment**:
- ✅ Aligns with Principle #{N} ({reason})
- ⚠️ Tension with Principle #{M} ({trade-off})
**Best for**: ...
**Not good for**: ...
```

**New section in comparison matrix**:
```markdown
## Principle Compliance Matrix

| Principle | Option 1 | Option 2 | Notes |
|-----------|----------|----------|-------|
| #{N} ({Name}) | ✅ Aligned | ⚠️ Partial | {Explanation} |
| #{M} ({Name}) | ⚠️ Tension | ✅ Aligned | {Explanation} |
```

---

### Recommendation 2: Add `/check-principles` Scopes

**Current scopes** (in `/check-principles` command):
- DEPLOYMENT - Pre-deployment verification
- INCIDENT - Post-incident analysis
- CODE_REVIEW - Before PR merge
- HEALTH_CHECK - Monthly system health

**New scopes to add**:

#### ARCHITECTURE Scope

**Principles to audit**:
- Principle #3: Aurora-First Data Architecture
- Principle #5: Database Migrations Immutability
- Principle #15: Infrastructure-Application Contract
- Principle #19: Cross-Boundary Contract Testing
- Principle #20: Execution Boundary Discipline

**Use cases**:
- Before architectural decisions (/architect)
- Before technology selection
- Before major refactoring

**Example**:
```bash
/check-principles architecture

Output:
✅ Principle #3 (Aurora-First): Compliant
  - All data queries use Aurora precomputed data
  - No direct external API calls in request path

⚠️ Principle #19 (Cross-Boundary Testing): Partial
  - Lambda→Aurora boundary tested
  - Missing: Lambda→S3 boundary tests
  - Recommendation: Add S3 upload/download boundary tests

✅ Principle #20 (Execution Boundaries): Compliant
  - All Lambdas have startup validation
  - Terraform env vars match code requirements
```

#### DECISION Scope

**Principles to audit**:
- Principle #12: OWL-Based Relationship Analysis
- Principle #21: Deployment Blocker Resolution

**Use cases**:
- Before making technology choices
- Before architectural decisions
- Before process changes

**Example**:
```bash
/check-principles decision "Choose between Redis and DynamoDB"

Output:
✅ Principle #12 (OWL-Based Analysis): Applied
  - Relationship type: Substitution (can replace each other)
  - Trade-off dimensions: Performance vs Cost vs Ops Complexity
  - Concrete examples provided

N/A Principle #21 (Deployment Blocker): Not applicable
  - No deployment blockers in this decision context
```

---

### Recommendation 3: Update Command Workflow Templates

**Create standard workflow template** for strategic decision commands:

```markdown
## Standard Strategic Decision Workflow

### Phase 0: Principle Compliance Check (/check-principles)
- Scope: {DEPLOYMENT | ARCHITECTURE | DECISION}
- Audit relevant principles
- Block on CRITICAL violations

### Phase 1: Context Gathering
- Understand current state
- Identify constraints and requirements

### Phase 2: Alternative Generation
- Explore options
- Consider trade-offs

### Phase 3: Principle Alignment Check
- For each option, check alignment with audited principles
- Document tensions or trade-offs

### Phase 4: Decision Framework Presentation
- Present options with principle compliance matrix
- Provide recommendation based on principle alignment

### Phase 5: User Approval
- Present to user
- Get explicit decision

### Phase 6: Execution
- Implement chosen option
- Validate against principles (post-execution check)
```

**Commands that should use this template**:
- `/deploy` - Already follows this pattern ✅
- `/architect` - Should adopt this pattern
- `/problem-statement` - Should adopt this pattern (variant for clarification, not just decisions)

---

## Implementation Plan

### Phase 1: Immediate (High Priority)

**1.1 Update `/check-principles` command**:
- [ ] Add ARCHITECTURE scope
- [ ] Add DECISION scope
- [ ] Update principle-to-scope mapping

**1.2 Update `/deploy` command**:
- [ ] Document existing `/check-principles` enforcement as best practice
- [ ] No changes needed (already correct pattern)

### Phase 2: Near-term (Medium Priority)

**2.1 Update `/architect` command**:
- [ ] Add Phase 0: Principle Compliance Check
- [ ] Update frontmatter composition to include `/check-principles architecture`
- [ ] Update examples to show principle compliance output

**2.2 Update `/problem-statement` command**:
- [ ] Add principle reference in Phase 5 (Decision Framework)
- [ ] Add Principle Compliance Matrix section
- [ ] Update examples to show principle alignment

### Phase 3: Future (Low Priority)

**3.1 Update analytical commands** (optional enhancement):
- [ ] `/what-if` - Add principle reference in alternative comparison
- [ ] `/compare` - Add principle alignment dimension
- [ ] `code-review` skill - Explicitly enumerate principles being checked

**3.2 Create decision workflow template**:
- [ ] Document standard strategic decision workflow
- [ ] Add to `.claude/processes/strategic-decision-workflow.md`
- [ ] Reference from relevant commands

---

## Trade-offs Analysis

### Benefits of Selective Enforcement

✅ **Prevents critical principle violations**:
- Deployment failures (missing env vars, wrong timeouts)
- Architecture anti-patterns (bypassing Aurora, violating boundaries)
- Process regressions (skipping waiters, ignoring evidence strengthening)

✅ **Improves decision quality**:
- Explicit principle alignment check
- Documented trade-offs against principles
- Clear rationale for chosen approach

✅ **Creates audit trail**:
- Principle compliance documented in decision process
- Easy to review why decision was made
- Helps onboarding (shows principle application)

✅ **Balances rigor and speed**:
- Strategic decisions get principle checks (high impact)
- Tactical decisions skip checks (low friction)
- Research/exploration unencumbered (fast iteration)

### Costs of Selective Enforcement

⚠️ **Added workflow steps**:
- `/architect` gets longer (Phase 0 added)
- `/problem-statement` output more verbose (principle matrix)
- Potential friction if principle checks are slow

⚠️ **Maintenance burden**:
- Must keep principle-to-scope mapping updated
- Need to classify new commands as strategic/analytical/tactical
- Principle list in `/check-principles` must stay current

⚠️ **Risk of over-enforcement**:
- Developers might run `/check-principles` for every decision "to be safe"
- Slows iteration if enforced unnecessarily
- Creates compliance theater without value

### Mitigations

**For workflow friction**:
- Make `/check-principles` fast (<5 seconds)
- Cache principle audit results (valid for session)
- Allow "quick mode" for re-checks

**For maintenance burden**:
- Auto-detect scope from command context (reduce manual classification)
- Pull principle list from CLAUDE.md programmatically (single source of truth)
- Monthly review of principle-to-scope mapping

**For over-enforcement**:
- Clear documentation of when to use each scope
- Examples showing tactical decisions that DON'T need checks
- Training/onboarding materials

---

## Comparison: Proposed vs Current Workflow

### Before (Current - Inconsistent)

```
/deploy "Lambda timeout increase"
  → /check-principles (enforced)
  → plan → approve → execute ✅

/architect "report generation pipeline"
  → research → analyze → recommend ❌ (no principle check)

/problem-statement "Redis vs DynamoDB"
  → identify → trace → framework ❌ (no principle reference)
```

**Issue**: Inconsistent application of principle-checking

### After (Proposed - Selective Enforcement)

```
/deploy "Lambda timeout increase"
  → /check-principles DEPLOYMENT (enforced)
  → plan → approve → execute ✅

/architect "report generation pipeline"
  → /check-principles ARCHITECTURE (enforced)
  → research → analyze → recommend ✅

/problem-statement "Redis vs DynamoDB"
  → identify → trace → framework (with principle matrix) 🟡

/explore "authentication patterns"
  → research → perspectives → synthesis ✅ (no check needed)
```

**Benefit**: Strategic decisions get principle checks, research/exploration stays fast

---

## User Proposal Evaluation

### Original Proposal

> "reflect on principles → think → make decision → execute"

**Evaluation**:
- ✅ **Correct for strategic decisions** (deploy, architecture, technology)
- ⚠️ **Over-engineered for analytical decisions** (refactoring, code review)
- ❌ **Premature for research/exploration** (still gathering information)

### Modified Proposal (This Document)

**For STRATEGIC decisions**:
```
1. Reflect on Principles (/check-principles {scope})
2. Think (analysis with principle context)
3. Make Decision (with principle alignment matrix)
4. Execute (with post-execution validation)
```

**For ANALYTICAL decisions**:
```
1. Think (analysis)
2. Reference Principles (in decision framework, not enforced gate)
3. Make Decision (with principle considerations)
4. Execute
```

**For TACTICAL/RESEARCH decisions**:
```
1. Think (exploration, research)
2. Make Decision (quick iteration)
3. Execute
4. (Principle violations caught in code review)
```

---

## Rejected Alternatives

### Alternative 1: Enforce `/check-principles` for ALL Decisions

**Why rejected**:
- Over-engineering for tactical decisions
- Slows research and exploration
- Creates compliance theater (checking principles for file naming)
- High friction, low value

### Alternative 2: No Enforcement, Only Documentation

**Why rejected**:
- Evidence shows `/deploy` enforcement prevents failures
- Voluntary compliance leads to inconsistency
- Strategic decisions are high-impact (worth enforcing)

### Alternative 3: AI-Driven Scope Detection

**Why rejected**:
- Complexity doesn't justify benefit
- Manual scope classification is clear and explicit
- Risk of AI misclassifying decision importance
- Can add later if manual classification proves burdensome

---

## Success Metrics

**How to measure if this change is successful**:

### Leading Indicators (Immediate)

- [ ] `/check-principles` executed before `/architect` decisions (target: 100%)
- [ ] `/problem-statement` includes principle compliance matrix (target: 100%)
- [ ] `/deploy` continues to enforce `/check-principles` (target: 100%)

### Lagging Indicators (3-month review)

- [ ] Deployment failures due to principle violations: Decrease by 50%
- [ ] Architecture decisions violating principles: Decrease by 75%
- [ ] Developer feedback: "Principle checks help decision quality" (target: >80% agree)
- [ ] Workflow friction: "Principle checks slow me down unnecessarily" (target: <20% agree)

### Health Metrics (6-month review)

- [ ] Principle compliance in code reviews: Increase from baseline
- [ ] Documented principle trade-offs in decisions: Increase from baseline
- [ ] Time to make strategic decisions: No significant increase (maintain <2 hours)

---

## Next Steps

### Immediate (This Week)

1. **Get user approval** on selective enforcement approach
   - Confirm: Strategic decisions enforce, analytical reference, tactical skip
   - Confirm: Add ARCHITECTURE and DECISION scopes to `/check-principles`

2. **Prioritize implementation phases**
   - Which phase to start with? (Recommend Phase 1: Update `/check-principles`)

### Near-term (This Month)

3. **Implement Phase 1**:
   - Update `/check-principles` with new scopes
   - Test with real decisions

4. **Implement Phase 2**:
   - Update `/architect` command
   - Update `/problem-statement` command

### Future (Ongoing)

5. **Monitor and iterate**:
   - Collect feedback on workflow friction
   - Adjust scope boundaries if needed
   - Add Phase 3 enhancements based on usage patterns

---

## Conclusion

**Recommendation**: ✅ **ADOPT SELECTIVE ENFORCEMENT**

**Key points**:
1. **Not all decisions are equal** - Strategic, analytical, and tactical decisions have different principle-checking needs
2. **Current state has gaps** - `/deploy` correctly enforces, but `/architect` and `/problem-statement` don't check principles
3. **Proposed workflow is sound** - "Reflect on principles → think → decide → execute" makes sense for strategic decisions
4. **Implementation is incremental** - Can add enforcement in phases, starting with highest-impact commands

**Next decision point**: User approval to proceed with Phase 1 implementation

---

*Analysis generated: 2026-01-04*
*Analyst: Claude Sonnet 4.5*
*Status: Ready for user review*
