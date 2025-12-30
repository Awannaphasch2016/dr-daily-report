---
name: impact
description: Assess change scope - understand ripple effects before making changes
accepts_args: true
arg_schema:
  - name: change
    required: true
    description: "Proposed change to assess (what you're planning to modify)"
composition:
  - skill: research
---

# Impact Command

**Purpose**: Before making changes, assess ripple effects

**Core Principle**: "Measure twice, cut once" - understand consequences before acting

**When to use**:
- Branching loop (evaluate path consequences)
- Before architectural changes
- Risk assessment for decisions
- Before refactoring
- Planning breaking changes

---

## Execution Flow

### Phase 1: Understand the Change

1. **Parse change description**: What specifically will change?
2. **Identify scope**: File, function, module, or system-wide?
3. **Classify change type**: Breaking, non-breaking, additive, removal
4. **Determine blast radius**: How far could effects propagate?

---

### Phase 2: Analyze Direct Impact

**What immediately breaks or changes**:

1. **Code dependencies**:
   - Who imports this module?
   - What calls this function?
   - What inherits from this class?

2. **Data dependencies**:
   - What reads this data?
   - What writes this data?
   - What depends on this schema?

3. **API contracts**:
   - What external systems call this?
   - What response format is expected?
   - What parameters are required?

---

### Phase 3: Analyze Indirect Impact

**Cascading effects (second-order dependencies)**:

1. **Conceptual dependencies**:
   - Similar patterns elsewhere
   - Shared assumptions
   - Related workflows

2. **Testing dependencies**:
   - Tests that verify this behavior
   - Mocks that assume this interface
   - Integration tests that use this

3. **Deployment dependencies**:
   - Configuration that references this
   - Infrastructure that depends on this
   - Monitoring/alerts tied to this

---

### Phase 4: Assess Risk Level

For each affected component:

**Risk levels**:
- **🔴 High**: Critical path, no fallback, production impact
- **🟡 Medium**: Important but non-critical, degraded performance
- **🟢 Low**: Minor, has workaround, development only

**Risk factors**:
- How many components affected?
- Are they critical to core functionality?
- Is there test coverage?
- Can changes be rolled back easily?

---

### Phase 5: Generate Mitigation Strategy

For each risk:

1. **How to minimize impact**: Backward compatibility, feature flags, gradual rollout
2. **How to test**: Unit tests, integration tests, manual testing
3. **How to monitor**: Metrics, logs, alerts
4. **How to rollback**: Revert strategy if things break

---

## Output Format

```markdown
## Impact Analysis: {change}

### Change Summary

**What's changing**: {Description of proposed change}

**Change type**: {Breaking | Non-breaking | Additive | Removal}

**Scope**: {File | Module | System-wide}

**Estimated blast radius**: {Small | Medium | Large}

---

## Direct Impact (Immediate Dependencies)

### Component 1: {affected-component}

**How affected**: {Description of impact}

**Location**: `{file-path:line}`

**Risk**: 🔴 High | 🟡 Medium | 🟢 Low

**Why risky**: {Reason for risk level}

**Mitigation**: {How to minimize impact}

---

### Component 2: {affected-component}

[... repeat structure ...]

---

## Indirect Impact (Cascading Effects)

### Similar Patterns

**Pattern**: {Pattern that might be affected}

**Locations**:
- `{file1:line}`
- `{file2:line}`

**Risk**: 🟡 Medium (Conceptual dependency)

**Mitigation**: {Review and update if needed}

---

### Test Coverage

**Tests affected**: {Number} tests

**Locations**:
- `{test-file1:line}` - {Test name}
- `{test-file2:line}` - {Test name}

**Risk**: 🟢 Low (Tests will catch breakage)

**Action needed**: Update test expectations

---

### Deployment Dependencies

**Configuration**: {Config files affected}

**Infrastructure**: {Resources affected}

**Risk**: {Level}

**Mitigation**: {Strategy}

---

## Risk Summary

**Total affected components**: {Number}

**Risk distribution**:
- 🔴 High risk: {Number} components
- 🟡 Medium risk: {Number} components
- 🟢 Low risk: {Number} components

**Overall risk level**: 🔴 High | 🟡 Medium | 🟢 Low

**Risk reasoning**: {Why this overall risk level}

---

## Mitigation Strategy

### Phase 1: Prepare

- [ ] {Preparation step 1}
- [ ] {Preparation step 2}

### Phase 2: Implement with Safety

**Backward compatibility**:
- {How to maintain compatibility during transition}

**Feature flags** (if applicable):
- {How to gate new behavior}

**Gradual rollout**:
- {How to deploy incrementally}

### Phase 3: Validate

**Testing checklist**:
- [ ] Unit tests updated
- [ ] Integration tests pass
- [ ] Manual testing of affected flows
- [ ] Performance testing (if applicable)

**Monitoring**:
- {Metrics to watch}
- {Alerts to set up}

### Phase 4: Rollback Plan

**If things break**:
1. {Rollback step 1}
2. {Rollback step 2}

**Rollback time**: {Estimated time to revert}

---

## Recommended Approach

**Should we proceed?**: {Yes with caution | Yes | Reconsider}

**Recommendation**: {Specific advice based on analysis}

**Why**: {Rationale}

**Next steps**:
```bash
{Suggested commands or actions}
```
```

---

## Examples

### Example 1: API Breaking Change

```bash
/impact "Change ticker parameter from string to array in GET /report endpoint"
```

**Output**:
```markdown
## Impact Analysis: Change ticker parameter from string to array in GET /report endpoint

### Change Summary

**What's changing**: GET /report endpoint currently accepts `ticker=AAPL` (string), changing to `tickers=["AAPL","GOOGL"]` (array)

**Change type**: Breaking (parameter name AND type change)

**Scope**: API endpoint (affects external clients)

**Estimated blast radius**: Large (public API with external consumers)

---

## Direct Impact (Immediate Dependencies)

### Component 1: Telegram Mini App

**How affected**: Frontend calls GET /report?ticker=AAPL - will break

**Location**: `frontend/src/api/reports.ts:42`

**Risk**: 🔴 High

**Why risky**: Production frontend, all users affected, no fallback

**Mitigation**:
- Maintain backward compatibility (accept both formats temporarily)
- Add deprecation warning for old format
- Update frontend before deprecating old format

---

### Component 2: LINE Bot Integration

**How affected**: LINE bot sends single ticker requests

**Location**: `src/telegram/handlers/report_handler.py:67`

**Risk**: 🔴 High

**Why risky**: Production feature, user-facing, LINE bot separate deployment

**Mitigation**:
- Update LINE bot to use array format
- Deploy LINE bot first, then deprecate old format

---

### Component 3: API Documentation

**How affected**: OpenAPI spec shows old parameter format

**Location**: `docs/api/openapi.yaml:145`

**Risk**: 🟡 Medium

**Why risky**: Documentation mismatch confuses integrators

**Mitigation**: Update OpenAPI spec with both formats during transition

---

## Indirect Impact (Cascading Effects)

### Similar Patterns

**Pattern**: Other endpoints with single-ticker parameters

**Locations**:
- `GET /backtest?ticker=AAPL` (might expect same change)
- `GET /analysis?ticker=AAPL` (might expect consistency)

**Risk**: 🟡 Medium (User expectation of consistent API design)

**Mitigation**: Consider updating all ticker parameters for consistency

---

### Test Coverage

**Tests affected**: 15 tests

**Locations**:
- `tests/test_report_api.py:42` - test_get_report_single_ticker
- `tests/test_report_api.py:58` - test_get_report_invalid_ticker
- `tests/integration/test_telegram_flow.py:89` - test_report_request

**Risk**: 🟢 Low (Tests will catch breakage)

**Action needed**: Update test expectations to use array format

---

### Deployment Dependencies

**Configuration**: None (no config changes needed)

**Infrastructure**: API Gateway routes unchanged

**Risk**: 🟢 Low

**Mitigation**: No infrastructure changes needed

---

## Risk Summary

**Total affected components**: 5 components

**Risk distribution**:
- 🔴 High risk: 2 components (Telegram Mini App, LINE Bot)
- 🟡 Medium risk: 2 components (Similar patterns, Documentation)
- 🟢 Low risk: 1 component (Tests)

**Overall risk level**: 🔴 High

**Risk reasoning**: Breaking change to public API with external consumers, requires coordinated deployment across multiple systems

---

## Mitigation Strategy

### Phase 1: Prepare

- [ ] Add support for BOTH formats (backward compatibility)
- [ ] Add deprecation warning for old format
- [ ] Update OpenAPI documentation
- [ ] Create deployment plan

### Phase 2: Implement with Safety

**Backward compatibility**:
```python
# Accept both formats
if "ticker" in request.args:  # Old format
    logger.warning("Deprecated: Use 'tickers' parameter instead")
    tickers = [request.args["ticker"]]
elif "tickers" in request.args:  # New format
    tickers = json.loads(request.args["tickers"])
```

**Feature flags**: Not applicable (use dual-format support instead)

**Gradual rollout**:
1. Deploy backend with dual support (week 1)
2. Update Telegram Mini App to use new format (week 2)
3. Update LINE Bot to use new format (week 3)
4. Remove old format support after 1 month grace period (week 7)

### Phase 3: Validate

**Testing checklist**:
- [ ] Unit tests for both old and new formats
- [ ] Integration tests with both formats
- [ ] Manual testing: Telegram app works with new format
- [ ] Manual testing: LINE bot works with new format
- [ ] Verify deprecation warnings logged

**Monitoring**:
- Track usage of old vs new format (CloudWatch metric)
- Alert if old format usage > 10% after week 4
- Monitor error rates for GET /report

### Phase 4: Rollback Plan

**If things break**:
1. Frontend broken: Rollback frontend to old API calls
2. Backend broken: Revert to old-format-only (remove dual support code)

**Rollback time**: 5-10 minutes (standard deployment rollback)

---

## Recommended Approach

**Should we proceed?**: Yes with caution

**Recommendation**: Implement with backward compatibility and phased rollout

**Why**: Breaking change has high risk but manageable with proper migration strategy. Dual-format support allows graceful transition.

**Next steps**:
```bash
# Step 1: Create implementation plan
EnterPlanMode

# Step 2: Implement dual-format support
# (maintain backward compatibility)

# Step 3: Update clients incrementally
# Telegram Mini App → LINE Bot → Remove old format

# Step 4: Monitor transition
# Track old/new format usage, monitor errors
```
```

---

### Example 2: Refactoring Internal Function

```bash
/impact "Extract database connection logic into shared utility module"
```

**Output**:
```markdown
## Impact Analysis: Extract database connection logic into shared utility module

### Change Summary

**What's changing**: Move `get_db_connection()` from multiple files into `src/utils/db.py`

**Change type**: Non-breaking (internal refactoring, no external API changes)

**Scope**: Module (affects internal code organization)

**Estimated blast radius**: Medium (affects multiple files but isolated change)

---

## Direct Impact

### Component 1: report_handler.py

**How affected**: Must import from new location

**Location**: `src/telegram/report_handler.py:12` (current import location)

**Risk**: 🟢 Low

**Why risky**: Import change only, functionality unchanged, tests will catch

**Mitigation**: Update import statement

---

### Component 2: backtest_handler.py

**How affected**: Must import from new location

**Location**: `src/telegram/backtest_handler.py:15`

**Risk**: 🟢 Low

**Mitigation**: Update import statement

---

### Component 3: scheduler.py

**How affected**: Must import from new location

**Location**: `src/scheduler/ticker_fetcher_handler.py:8`

**Risk**: 🟢 Low

**Mitigation**: Update import statement

---

## Indirect Impact

### Test Coverage

**Tests affected**: 8 tests that import `get_db_connection`

**Risk**: 🟢 Low (Tests will fail if imports not updated, forcing fix)

**Action needed**: Update test imports

---

## Risk Summary

**Total affected components**: 11 files (3 handlers + 8 tests)

**Risk distribution**:
- 🔴 High risk: 0 components
- 🟡 Medium risk: 0 components
- 🟢 Low risk: 11 components

**Overall risk level**: 🟢 Low

**Risk reasoning**: Internal refactoring, no external changes, tests catch import issues

---

## Mitigation Strategy

**Recommended approach**: Proceed (low risk, high benefit for code organization)

**Testing**: Run full test suite before committing

**Rollback**: Simple git revert if issues found

**Next steps**:
```bash
# Safe to proceed with refactoring
# Tests will catch any missed imports
```
```

---

## Relationship to Other Commands

### Workflow Integration

**Before `/impact`**:
- `/what-if` - Explore alternatives before choosing one to assess
- `/explore` - Understand current architecture before changing

**After `/impact`**:
- `/validate` - Validate assumptions about impact
- `/trace` - Forward trace to understand downstream effects
- `EnterPlanMode` - Create detailed implementation plan

**Sequential workflow**:
```bash
/what-if "extract DB connection into utility"
   ↓
/impact "extract database connection logic into shared utility module"
   ↓ (assesses risk: Low, proceed)
EnterPlanMode
   ↓ (creates implementation plan)
Implement refactoring
```

### Loop Relationships

**Branching loop**:
- Use `/impact` to evaluate consequences of different paths
- Compare impact of alternative approaches
- Choose path with acceptable risk level

**Meta-loop**:
- Use `/impact` to assess consequences of changing loop strategy
- Example: Impact of switching from retrying to initial-sensitive loop

---

## Best Practices

### Do
- **Assess before acting** (don't skip impact analysis for "small" changes)
- **Search broadly** (code + tests + docs + config)
- **Consider cascading effects** (not just direct dependencies)
- **Provide specific locations** (file:line references)

### Don't
- **Don't assume no impact** (even internal changes can have ripple effects)
- **Don't skip mitigation** (identify how to minimize risk)
- **Don't ignore test updates** (tests are dependencies too)
- **Don't forget rollback plan** (always have escape hatch)

---

## See Also

- `/locate` - Inverse operation (task → files, range → domain)
- `/trace` - Follow causality forward (what will X cause?)
- `/what-if` - Explore alternatives before choosing
- `/validate` - Validate impact assumptions
- `.claude/diagrams/thinking-process-architecture.md` - Section 5 (Metacognitive Commands)

---

## Prompt Template

You are executing the `/impact` command with arguments: $ARGUMENTS

**Change**: $1

---

### Execution Steps

**Step 1: Understand the Change**

Parse change description:
- What specifically will change?
- What scope? (file, module, system-wide)
- What type? (breaking, non-breaking, additive, removal)

**Step 2: Analyze Direct Impact**

Search codebase for direct dependencies:

```bash
# Code dependencies
grep -r "import {module}" src/ tests/
grep -r "{function_name}(" src/ tests/

# Data dependencies (if applicable)
grep -r "{schema_name}" src/ tests/ docs/

# API contracts (if applicable)
grep -r "{endpoint_path}" src/ tests/ docs/
```

For each dependency found:
- Identify affected component
- Assess risk level (High/Medium/Low)
- Propose mitigation

**Step 3: Analyze Indirect Impact**

Search for:
- Similar patterns (conceptual dependencies)
- Tests that verify related behavior
- Configuration/infrastructure dependencies

**Step 4: Assess Risk**

Calculate overall risk:
- Count affected components
- Categorize by risk level
- Determine if change is safe to proceed

**Step 5: Generate Mitigation Strategy**

For each risk identified:
- How to minimize impact
- How to test
- How to monitor
- How to rollback

**Step 6: Provide Recommendation**

Based on risk analysis:
- Should we proceed? (Yes/Yes with caution/Reconsider)
- Why? (Rationale based on risk/benefit)
- Next steps (specific commands or actions)

---

### Notes

- For breaking changes, always recommend backward compatibility period
- For high-risk changes, suggest gradual rollout
- Include specific file:line references for all affected components
- Prioritize risks by severity and impact
