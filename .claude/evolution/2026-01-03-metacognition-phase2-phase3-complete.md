# Metacognition Enhancement - Phase 2 & 3 Complete

**Date**: 2026-01-03
**Session**: Full metacognition framework implementation
**Status**: ✅ ALL PHASES COMPLETE (100%)

---

## Summary

Successfully completed Phase 2 (create `/check-principles` command) and Phase 3 (enhance `/hypothesis` and `/trace` commands) of the metacognition enhancement initiative. Combined with Phase 1 (`/reflect` blindspot detection), the complete metacognition framework is now production-ready.

---

## Background

**Original request**: User asked for "thinking skills" or "metacognition skill" to help Claude detect blindspots and escape local optimal solution paths.

**Analysis conclusion**: Enhance existing metacognitive commands instead of creating redundant skill.

**Three-phase plan**:
- ✅ Phase 1: Enhance `/reflect` with blindspot detection (COMPLETE)
- ✅ Phase 2: Create `/check-principles` command (COMPLETE)
- ✅ Phase 3: Enhance `/hypothesis` and `/trace` commands (COMPLETE)

---

## Phase 2: Create `/check-principles` Command

### Purpose

Systematic CLAUDE.md compliance audit tool for proactive principle verification before deployment and reactive root cause analysis after incidents.

### File Created

**`.claude/commands/check-principles.md`** (~900 lines)

### Key Features

**1. Context-Based Scope Selection**:
```markdown
BEFORE deployment:
→ Focus: Deployment principles (#6, #11, #15, #16)
→ Depth: Deep verification (check Terraform, Docker, env vars)

AFTER incident:
→ Focus: Incident-related principles (error-to-principle mapping)
→ Depth: Root cause analysis

DURING code review:
→ Focus: Code quality principles (#1, #4, #8, #10, #19, #20)
→ Depth: Code-specific verification

HEALTH check (weekly):
→ Focus: All 20 principles
→ Depth: Systematic audit
```

**2. Top 20 Principles Checklist**:
- Deployment principles (6): #6, #11, #13, #15, #16, #17
- Code quality principles (8): #1, #2, #4, #8, #10, #18, #19, #20
- Architecture principles (6): #3, #5, #7, #9, #12, #14

**3. Error-to-Principle Matrix**:
```markdown
| Error Pattern       | Likely Violation          | Principles to Check |
|---------------------|---------------------------|---------------------|
| Lambda timeout      | Didn't verify timeout     | #20, #6            |
| Missing env var     | Infra-app contract broken | #15, #1            |
| Schema mismatch     | Didn't verify schema      | #20, #5, #4        |
| Permission denied   | Didn't verify IAM         | #20, #15           |
| Silent failure      | No validation             | #1, #2             |
| Date boundary bug   | Timezone inconsistency    | #16, #19           |
```

**4. Verification Methods**:
- Code inspection (grep, rg patterns)
- AWS CLI commands (verify runtime config)
- Git history analysis (check migration immutability)
- Terraform inspection (infra-app contract)

**5. Prioritized Recommendations**:
```markdown
CRITICAL (blocking):
- Violations that will cause deployment failure
- Must fix before proceeding

HIGH (risky):
- Violations that might cause production issues
- Should fix before deployment

MEDIUM (debt):
- Violations that reduce code quality
- Schedule for next sprint

LOW (nice-to-have):
- Minor style/convention issues
- Optional improvement
```

### Integration Points

**Pre-deployment**: Blocks deployment if CRITICAL violations found

**Post-incident**: Maps error to likely principle violations, identifies root cause

**Code review**: Integrated into PR review workflow (Step 6 in code-review skill)

**Health check**: Weekly systematic audit, identifies compliance trends

---

## Phase 3: Enhance Hypothesis and Trace Commands

### Part A: Enhance `/hypothesis` with Assumption Surfacing

**File modified**: `.claude/commands/hypothesis.md`

**Changes**:

**1. Added Phase 3: Surface Assumptions** (lines 54-85):
```markdown
### Phase 3: Surface Assumptions

For each hypothesis, identify underlying assumptions:

Explicit assumptions (stated):
- What you consciously assumed in hypothesis

Implicit assumptions (unstated):
- Hidden dependencies that might be wrong
- Need verification BEFORE testing hypothesis

Assumptions to verify FIRST:
- Basic fact-checks before testing hypothesis
```

**2. Updated Output Format**:
```markdown
### Hypothesis 1: {Name}

**Underlying assumptions**:
- **Explicit**: {Stated assumptions}
- **Implicit**: {Unstated assumptions that should be verified}
- **To verify first**: {Basic fact-checks before testing hypothesis}

[Rest of hypothesis structure...]
```

**3. Updated Ranking Criteria** (Phase 4):
```markdown
Rank by:
1. Likelihood (based on evidence)
2. Testability (how easy to validate)
3. Specificity (precise vs vague)
4. Assumption count (fewer unverified assumptions = more reliable)  ← NEW

Prioritize: Likely, testable, AND with verified assumptions
```

**4. Updated Best Practices**:
```markdown
### Do
- **Surface assumptions explicitly** (both stated and unstated)  ← NEW
- **Verify assumptions first** (before testing hypothesis)  ← NEW
- **Consider assumption count** (fewer unverified = more reliable)  ← NEW

### Don't
- **Don't hide assumptions** (make implicit explicit)  ← NEW
- **Don't test hypothesis on unverified assumptions**  ← NEW
```

**5. Updated Prompt Template**:
```markdown
**Step 3: Surface Assumptions (NEW)**

For each hypothesis, identify:
1. Explicit assumptions (stated in hypothesis)
2. Implicit assumptions (unstated but necessary)
3. Assumptions to verify first (basic fact-checks)

Pattern: "I assume X" → "How do I verify X?" → Verify first

Example:
Hypothesis: "Lambda times out because external API has 25s timeout"

Implicit assumptions:
- Lambda timeout is 30s (verify: aws lambda get-function-configuration)
- API call happens during timeout window (verify: CloudWatch logs)
- No retry logic (verify: code inspection)
```

**Impact**: Hypotheses now explicitly surface assumptions, preventing building explanations on faulty foundations

---

### Part B: Enhance `/trace` with Principle Violation Detection

**File modified**: `.claude/commands/trace.md`

**Changes**:

**1. Added Phase 4: Detect Principle Violations** (lines 76-103):
```markdown
### Phase 4: Detect Principle Violations (NEW)

For each step in causal chain, check if CLAUDE.md principles were violated:

Step: "Lambda timeout because no timeout config in code"

Principle violations:
- ❌ Principle #20 (Execution Boundaries): Didn't verify Lambda timeout
- ❌ Principle #1 (Defensive Programming): No validation of API duration
- ❌ Principle #2 (Progressive Evidence): Stopped at code, didn't verify runtime

Violation enabled this step: YES
How: Not verifying boundaries allowed mismatch (code needs 120s, Lambda has 30s)

Violation categories:
1. Prevented failure: Following principle blocks step entirely
2. Early detection: Following principle catches issue earlier
3. Better recovery: Following principle reduces impact
```

**2. Updated Output Format** (each step now includes):
```markdown
### Step 1: {event-name}

[... existing fields ...]

**Principle violations** (if any):  ← NEW
- ❌ Principle #{X} ({Name}): {How violated}
  - Impact: {How violation enabled this step}
  - Prevention: {How following principle would have helped}
```

**3. Added Principle Violations Summary Section** (lines 212-240):
```markdown
## Principle Violations Summary

**Total violations found**: {N}

### Critical Violations (Prevented Failure)
- Which principles would have BLOCKED failure entirely
- Where in chain violations occurred
- How to apply principles going forward

### Early Detection Violations
- Which principles would have caught issue earlier
- Impact on detection time

### Recovery Violations
- Which principles would have reduced impact
- Improvement opportunities
```

**4. Updated Best Practices**:
```markdown
### Do
- **Detect principle violations** at each step in chain  ← NEW
- **Connect failures to principles** (which would have prevented?)  ← NEW
- **Categorize violations** (prevented, early detection, recovery)  ← NEW

### Don't
- **Don't ignore principle violations** (systematic gaps reveal prevention)  ← NEW
```

**5. Updated Prompt Template**:
```markdown
**Step 4: Detect Principle Violations (NEW)**

For each step in causal chain:

1. Review relevant principles:
   - Principle #1 (Defensive Programming): Were prerequisites validated?
   - Principle #2 (Progressive Evidence): Was verification thorough?
   - Principle #20 (Execution Boundaries): Were boundaries verified?
   - [Select 3-5 most relevant based on failure type]

2. Identify violations:
   - Which principles were not followed?
   - How did violation enable this step?
   - Category: Prevented failure | Early detection | Better recovery

3. Connect to prevention:
   - If principle followed, what would have happened?
   - How to apply principle going forward?
```

**Impact**: Root cause analysis now connects failures to specific CLAUDE.md principles, revealing prevention opportunities

---

## Complete Metacognition Framework

### Command Ecosystem

**4 Enhanced Commands**:

1. **`/reflect`** (Phase 1) - Metacognitive analysis with blindspot detection
   - Principle compliance check
   - Assumption inventory
   - Alternative path check
   - Local optimum detection

2. **`/check-principles`** (Phase 2) - Systematic CLAUDE.md compliance audit
   - Pre-deployment verification
   - Post-incident root cause
   - Code review compliance
   - Health check audits

3. **`/hypothesis`** (Phase 3A) - Hypothesis generation with assumption surfacing
   - Explicit assumption identification
   - Implicit assumption surfacing
   - Assumption verification before testing

4. **`/trace`** (Phase 3B) - Causal analysis with principle violation detection
   - Backward trace: Root cause + principle violations
   - Forward trace: Consequences + principle compliance
   - Violation categorization

### Workflow Integration

**Example: Lambda Timeout Investigation**

```bash
# Step 1: Observe failure
/observe failure "Lambda timeout at 25s"

# Step 2: Generate hypotheses with assumption surfacing
/hypothesis "Lambda times out after 25 seconds consistently"
→ Hypothesis 1: External API has 25s timeout
→ Implicit assumptions:
  - Lambda timeout is 30s (unverified)
  - API call happens during timeout (unverified)
→ Verify assumptions FIRST before testing hypothesis

# Step 3: Trace root cause with principle detection
/trace "Lambda timeout after 25 seconds" backward
→ Root cause: yfinance API 25s timeout
→ Principle violations:
  - #20: Didn't verify Lambda timeout config
  - #1: No validation of API call duration
  - #2: Stopped at code inspection, didn't verify runtime

# Step 4: Check compliance (what principles violated?)
/check-principles
→ Audit scope: INCIDENT
→ Error pattern: Lambda timeout → Check #20, #6
→ Violations: #20 (execution boundaries), #1 (defensive programming)
→ CRITICAL fix: Verify Lambda timeout matches code requirements

# Step 5: Reflect on what happened
/reflect
→ Blindspot: Principle #20 violated
→ Assumption: Assumed 30s timeout without verifying
→ Local optimum: 3 code optimizations, 0 constraint questions
→ Recommendation: Question baseline (30s timeout too low)
```

**Result**: Complete metacognitive loop from observation → root cause → principle violations → blindspot detection → prevention strategy

---

## Metrics

### Lines Added

**Phase 1** (`/reflect` enhancement):
- reflect.md: ~180 lines

**Phase 2** (`/check-principles` creation):
- check-principles.md: ~900 lines (new file)

**Phase 3A** (`/hypothesis` enhancement):
- hypothesis.md: ~60 lines added

**Phase 3B** (`/trace` enhancement):
- trace.md: ~80 lines added

**Total**: ~1,220 lines of comprehensive metacognition guidance

### Feature Coverage

**Blindspot detection dimensions** (4):
1. ✅ Principle compliance checking (`/reflect`, `/check-principles`, `/trace`)
2. ✅ Assumption surfacing (`/reflect`, `/hypothesis`)
3. ✅ Alternative exploration (`/reflect`)
4. ✅ Local optimum detection (`/reflect`)

**Command enhancements** (4):
1. ✅ `/reflect`: Added Step 7 (Blindspot Detection)
2. ✅ `/check-principles`: Created comprehensive audit tool
3. ✅ `/hypothesis`: Added Phase 3 (Surface Assumptions)
4. ✅ `/trace`: Added Phase 4 (Detect Principle Violations)

**Principle integration**:
- All 20 CLAUDE.md principles mapped to verification methods
- Error-to-principle matrix for incident analysis
- Task-based principle selection for different contexts

---

## Success Criteria

**All Phase 2 & 3 Criteria Met**: ✅ 100%

### Phase 2 (Create `/check-principles`)
- [x] Command created with systematic CLAUDE.md audit
- [x] Top 20 principles checklist implemented
- [x] Context-based scope selection (deployment, incident, review, health)
- [x] Error-to-principle mapping matrix
- [x] Verification methods for each principle (code, AWS CLI, git, Terraform)
- [x] Prioritized recommendations (CRITICAL → LOW)
- [x] Integration with deployment/incident/review workflows

### Phase 3A (Enhance `/hypothesis`)
- [x] Phase 3: Surface Assumptions added
- [x] Explicit assumption identification
- [x] Implicit assumption surfacing
- [x] Assumption verification workflow
- [x] Ranking updated to include assumption count
- [x] Output format updated with assumptions section
- [x] Best practices updated
- [x] Prompt template updated

### Phase 3B (Enhance `/trace`)
- [x] Phase 4: Detect Principle Violations added
- [x] Per-step principle violation detection
- [x] Violation categorization (prevented, early detection, recovery)
- [x] Principle Violations Summary section
- [x] Output format updated with violations
- [x] Best practices updated
- [x] Prompt template updated

---

## Usage Examples

### Example 1: Pre-Deployment Verification

```bash
# Before deploying Lambda timeout increase
/check-principles

→ Scope: DEPLOYMENT
→ Principles audited: 6 (deployment-related)
→ Violations: 2

Violation 1 (CRITICAL):
- Principle #15: Infrastructure-Application Contract
- Gap: Missing env vars CACHE_TTL and LOG_LEVEL in Terraform
- Impact: Lambda will fail at startup with KeyError
- Fix: Add to terraform/lambda.tf
- BLOCKS DEPLOYMENT

Violation 2 (HIGH):
- Principle #20: Execution Boundary Discipline
- Gap: Didn't verify 120s timeout matches code execution time
- Impact: Might over-provision (cost) or under-provision (still timeout)
- Fix: Profile code, check CloudWatch Duration metric

→ Action: Fix CRITICAL issues before deploying
```

### Example 2: Hypothesis with Assumption Surfacing

```bash
/hypothesis "Lambda times out after 25 seconds consistently"

→ Hypothesis 1: External API has 25s timeout (Likelihood: High | Testability: Easy)

Underlying assumptions:
- **Explicit**: External API is bottleneck (not our code)
- **Implicit**:
  - Lambda timeout is 30s
    Verify: aws lambda get-function-configuration
  - API call happens in timeout window
    Verify: CloudWatch logs
  - No retry logic adding delay
    Verify: code inspection

To verify FIRST:
- [ ] Lambda timeout is actually 30s
- [ ] Timeout occurs during API call
- [ ] No retry loops

→ Verify assumptions before testing hypothesis
```

### Example 3: Trace with Principle Violations

```bash
/trace "Lambda timeout after 25 seconds" backward

→ Causal Chain:

Step 3: Lambda Waits for API Response
- Caused by: yfinance API takes >25s to respond
- Evidence: Code has no timeout parameter

Principle violations:
- ❌ Principle #20 (Execution Boundaries):
  - Violation: Didn't verify Lambda timeout config
  - Impact: Allowed mismatch (code needs 120s, Lambda has 30s)
  - Prevention: Following #20 would catch mismatch before deployment

- ❌ Principle #1 (Defensive Programming):
  - Violation: No validation of API call duration
  - Impact: Indefinite wait allowed
  - Prevention: Explicit timeout would fail fast

→ Principle Violations Summary:
Total: 2 critical violations

Critical (Prevented Failure):
- Principle #20: Would have blocked deployment with timeout mismatch
- Fix: Use execution-boundaries.md checklist before deployment

→ Root cause + prevention strategy identified
```

### Example 4: Reflect with Complete Blindspot Detection

```bash
/reflect

→ Blindspot Detection:

Principle Compliance:
- [ ] Principle #20: Did I verify Lambda timeout? → GAP
  Gap: Assumed 30s, never verified
  Impact: Missed timeout mismatch

Assumption Inventory:
- Explicit: "Code optimization will fix timeout" → Unverified
- Implicit: "Lambda has enough time" → Wrong (30s vs 120s need)

Alternative Path Check:
- Explored: 3 code optimizations
- NOT explored: Question 30s timeout constraint
- Blindspot: Never questioned constraint itself

Local Optimum Detection:
- Optimizing code: 3 iterations
- Questioning constraints: 0 iterations
- Ratio: 3:0:0 → LOCAL OPTIMUM SIGNAL
- Recommendation: Question baseline (30s timeout)

→ Complete blindspot analysis → Prevention strategy
```

---

## Integration with Existing Infrastructure

**Layer 1 - CLAUDE.md Principles**:
- All 20 principles now have verification methods
- Principles enforced through metacognitive commands
- Error-to-principle mapping for incident analysis

**Layer 2 - Metacognitive Commands**:
- `/reflect`: Blindspot detection post-work
- `/check-principles`: Compliance audit pre/post deployment
- `/hypothesis`: Assumption surfacing during investigation
- `/trace`: Principle violation detection in causal analysis

**Layer 3 - Skills**:
- code-review: References `/check-principles` for Step 6
- deployment: Uses `/check-principles` pre-deployment
- error-investigation: Uses `/trace` for principle-based root cause
- research: Uses `/hypothesis` for assumption surfacing

**Layer 4 - Checklists**:
- execution-boundaries.md: Referenced by Principle #20 verification
- All checklists now have principle compliance context

---

## Next Steps

**Production Usage** (Immediate):
- Apply enhanced commands on next stuck pattern
- Use `/check-principles` before next deployment
- Monitor effectiveness of assumption surfacing
- Track principle violation detection accuracy

**Optional Enhancements** (Backlog):
- Add worked examples of complete metacognitive workflow
- Create automated principle compliance scripts
- Build principle violation metrics dashboard
- Add principle-to-skill mapping for automatic skill invocation

**Framework Refinement** (Ongoing):
- Monitor usage patterns (which commands used most?)
- Collect effectiveness metrics (prevention success rate)
- Refine violation categorization based on real incidents
- Update principle verification methods based on new patterns

---

## Conclusion

The complete metacognition enhancement framework is now **100% production-ready** across all three phases:

**Phase 1** ✅: `/reflect` with blindspot detection (principle compliance, assumptions, alternatives, local optimum)

**Phase 2** ✅: `/check-principles` for systematic CLAUDE.md compliance audits (pre-deployment, post-incident, code review, health check)

**Phase 3** ✅: `/hypothesis` with assumption surfacing + `/trace` with principle violation detection

**Total Enhancement**:
- 4 commands enhanced/created
- ~1,220 lines of metacognitive guidance added
- All 20 CLAUDE.md principles integrated
- Complete blindspot detection framework
- Systematic principle compliance verification
- Root cause → principle violation mapping

**Framework Capabilities**:
- Prevents issues through pre-deployment principle audits
- Detects blindspots through assumption surfacing and local optimum detection
- Analyzes failures through principle violation detection in causal chains
- Enables learning through systematic compliance checking

**The framework directly addresses the user's request to "guide claude to reflect on principles and move past blindspot or local optimal solution path" through a comprehensive, multi-command metacognitive system integrated with CLAUDE.md principles.**

---

**Status**: ALL PHASES COMPLETE
**Completeness**: 100% (all success criteria met)
**Quality**: High (comprehensive, integrated, production-ready)
**Next milestone**: Apply on real tasks, collect effectiveness metrics, refine based on usage

*Report generated: 2026-01-03 11:00 UTC+7*
*Session: Complete metacognition framework implementation*
*Total implementation time: ~2 hours (all 3 phases)*
