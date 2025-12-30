---
name: evolve
description: Detect drift between documented principles and actual practices, propose updates to skills and CLAUDE.md
accepts_args: true
arg_schema:
  - name: focus_area
    required: false
    description: "Optional focus: testing, deployment, error-handling, architecture, docs, cli, or 'all' (default)"
composition:
  - skill: research
---

# Evolve Command

**Purpose**: Meta-learning operation to detect drift between documented principles and actual practices

**Core Principle**: "Principles evolve through practice" - documented principles drift from reality over time. Detect drift, update principles.

**When to use**:
- Monthly review → Full system evolution check
- After major project → Update principles learned
- When principles feel wrong → Investigate drift
- Before formalizing ADR → Ensure aligned with practices

---

## Quick Reference

```bash
/evolve                  # Review all areas (default)
/evolve testing          # Focus on testing patterns
/evolve deployment       # Focus on deployment practices
/evolve error-handling   # Focus on error handling
/evolve architecture     # Focus on architecture patterns
/evolve docs             # Focus on documentation drift
/evolve cli              # Focus on CLI command drift
```

---

## Focus Areas

### `all` (default) - Comprehensive Review
**What it reviews**:
- All journals, observations, abstractions
- All git commits (last 30 days)
- All skills and CLAUDE.md
- Comprehensive drift detection

---

### `testing` - Test Patterns & Practices
**What it reviews**:
- Test files and patterns
- Testing journals and observations
- testing-workflow skill
- CLAUDE.md testing principles

**Drift indicators**:
- Tests written don't match documented patterns
- New test patterns not in skill
- Anti-patterns appearing in code

---

### `deployment` - Deployment Workflows
**What it reviews**:
- Deployment observations
- CI/CD changes
- deployment skill
- CLAUDE.md deployment principles

**Drift indicators**:
- Deployment steps changed
- New deployment patterns emerging
- Infrastructure changes not documented

---

### `error-handling` - Error Investigation
**What it reviews**:
- Failure observations
- Error journals
- error-investigation skill
- CLAUDE.md defensive programming

**Drift indicators**:
- New error patterns
- Changed investigation approach
- Missing error handling patterns

---

### `architecture` - Design Patterns
**What it reviews**:
- Architecture journals
- Code structure changes
- Related skills
- CLAUDE.md architecture principles

**Drift indicators**:
- New design patterns adopted
- Architectural principles violated
- Patterns used don't match docs

---

### `docs` - Documentation Quality & Drift

**What it reviews**:
- Documentation files (`docs/**/*.md`, `README.md`, ADRs)
- Documentation journals (if any doc-specific journals exist)
- Code comments and docstrings
- CLAUDE.md documentation references
- API documentation (if exists)
- Internal links between documentation

**Drift indicators**:
- Documentation describes features that don't exist (false documentation)
- Features exist but not documented (missing documentation)
- Examples in docs are outdated or broken
- API docs don't match actual endpoints/signatures
- README setup instructions don't work
- Broken internal links in documentation
- TODOs/FIXMEs in code not reflected in docs
- Deployment instructions out of sync with actual process

**What to check**:
```bash
# Find all documentation
find docs/ -name "*.md"
find . -maxdepth 1 -name "*.md"

# Check code comments and TODOs
grep -r "TODO\|FIXME\|XXX" src/ tests/

# Find orphaned doc references (referenced but not existing)
grep -r "docs/" **/*.md | grep -v "^docs/"

# Check for broken internal links
grep -r "\[.*\](\./" **/*.md
```

**Example drift detection**:
- README says "Run `dr deploy`" but actual command is `dr deploy dev`
- ADR-008 describes Aurora caching strategy but code uses DynamoDB
- `docs/API.md` lists `/v1/report` endpoint that doesn't exist in code
- Code has new `/v2/backtest` endpoint added 2 weeks ago, not documented anywhere
- Deployment runbook references `just deploy-prod` but recipe doesn't exist

**Proposed updates**:
- Update outdated examples in README and docs
- Document new features added in last 30 days
- Fix broken internal links
- Remove documentation for removed features
- Add missing API endpoint documentation
- Sync deployment instructions with actual process
- Convert recurring TODOs into documentation sections

---

### `cli` - CLI Command Consistency & Usability

**What it reviews**:
- dr CLI commands (`dr_cli/commands/*.py`)
- Justfile recipes (if exists)
- CLI command documentation (`docs/cli.md`, `docs/PROJECT_CONVENTIONS.md`)
- CLI usage patterns in git commits
- Command help text vs actual behavior
- Two-layer design consistency (Justfile intent vs CLI implementation)

**Drift indicators**:
- Justfile recipe exists but no dr CLI equivalent
- dr CLI command exists but no Justfile recipe
- Command help text doesn't match actual behavior
- Commands documented but not implemented (or vice versa)
- New commands added but not documented
- Inconsistent naming between Justfile and CLI
- Missing examples in help text
- Command groups not aligned with functional areas

**What to check**:
```bash
# List all Justfile recipes (if exists)
just --list 2>/dev/null || echo "No Justfile"

# List all dr CLI commands
python3 -c "from dr_cli.main import cli; print(list(cli.commands.keys()))"

# Find CLI command files
ls -la dr_cli/commands/*.py

# Check git usage patterns
git log --since="30 days ago" --all -S "dr " --oneline

# Verify command documentation
grep "dr " docs/PROJECT_CONVENTIONS.md docs/cli.md 2>/dev/null
```

**Example drift detection**:
- Justfile has `just deploy-staging` but `dr deploy staging` doesn't exist
- `dr dev verify` exists (added 2 weeks ago) but no corresponding Justfile recipe
- `dr test tier` command added recently but not in docs or Justfile
- Command help says "Deploy to AWS Lambda" but command name `dr deploy lambda-deploy` is unclear
- PROJECT_CONVENTIONS.md shows old command structure before recent refactor

**Proposed updates**:
- Add missing Justfile recipes for new dr commands
- Implement dr CLI commands for commonly used Justfile recipes
- Update command help text for clarity and consistency
- Document new commands in PROJECT_CONVENTIONS.md and cli.md
- Ensure consistent naming (kebab-case throughout)
- Add usage examples to command help text
- Create mapping table showing Justfile ↔ CLI equivalents

**Two-layer design principle**:
- **Justfile** = Intent (WHEN/WHY) - "When should I use this command?"
- **dr CLI** = Implementation (HOW) - "How does this command work?"

Ensure both layers stay synchronized and complementary.

---

## Execution Flow

### Step 1: Parse Focus Area

```bash
/evolve              # Default: all
/evolve testing      # Focus: testing only
```

---

### Step 2: Collect Recent Work (Last 30 Days)

**Git commits**:
```bash
git log --since="30 days ago" --pretty=format:"%h %s" --all
```

**Journals**:
```bash
find .claude/journals/ -name "*.md" -mtime -30
```

**Observations**:
```bash
find .claude/observations/ -name "*.md" -mtime -30
```

**Abstractions**:
```bash
find .claude/abstractions/ -name "*.md" -mtime -30
```

**Validations**:
```bash
find .claude/validations/ -name "*.md" -mtime -30
```

---

### Step 3: Invoke Research Skill

Use `research` skill methodology to:
- Systematically review collected data
- Identify patterns
- Compare against documented principles
- Avoid confirmation bias

---

### Step 4: Compare Documented vs Actual

**For each focus area**, compare:

#### CLAUDE.md Principles
```
Load: .claude/CLAUDE.md
Extract: Principles for focus area
Store: DOCUMENTED_PRINCIPLES
```

#### Actual Practices
```
Analyze: Git commits, journals, observations
Extract: Patterns actually used
Store: ACTUAL_PRACTICES
```

#### Detect Drift
```
Compare: DOCUMENTED_PRINCIPLES vs ACTUAL_PRACTICES

If different:
  - Classify as: DRIFT_POSITIVE (practice improved)
                 or DRIFT_NEGATIVE (practice degraded)
  - Measure magnitude: MINOR, MODERATE, MAJOR
  - Collect evidence
```

---

### Step 5: Identify Patterns

**New patterns** (not documented):
```
Pattern exists in ACTUAL_PRACTICES
but NOT in DOCUMENTED_PRINCIPLES
  → Candidate for documentation
```

**Abandoned patterns** (documented but not used):
```
Pattern exists in DOCUMENTED_PRINCIPLES
but NOT in ACTUAL_PRACTICES (last 30 days)
  → Candidate for removal or investigation
```

**Evolved patterns** (changed):
```
Pattern exists in both
but IMPLEMENTATION_DIFFERS
  → Candidate for update
```

---

### Step 6: Search for Undocumented Patterns

**In code**:
```bash
# Search for recurring patterns
grep -r "pattern" src/ tests/

# Identify frequent structures
# Extract common idioms
```

**In observations**:
```bash
# Find repeated failure modes
grep "failure" .claude/observations/*/*.md

# Find repeated workflows
grep "execution" .claude/observations/*/*.md
```

**In journals**:
```bash
# Find recurring decisions
# Find repeated solutions
# Identify themes
```

---

### Step 7: Propose Updates

**For each drift detected**, generate proposal:

```markdown
### Proposal: {Title}

**Type**: DRIFT_POSITIVE | DRIFT_NEGATIVE | NEW_PATTERN | ABANDONED_PATTERN

**Evidence**: ({count} instances)
- {Source 1}: {Evidence}
- {Source 2}: {Evidence}
- {Source 3}: {Evidence}

**Current Documentation**:
```
{What CLAUDE.md/skills say now}
```

**Actual Practice**:
```
{What code/journals show actually happens}
```

**Magnitude**: MINOR | MODERATE | MAJOR

**Recommendation**:
```
{Specific change to make to CLAUDE.md or skill}
```

**Priority**: HIGH | MEDIUM | LOW

**Action**:
- [ ] Update CLAUDE.md: {section} → {change}
- [ ] Update skill: {skill_name} → {change}
- [ ] Create ADR: {if significant architectural change}
- [ ] Graduate pattern: {from journal to skill}
```

---

### Step 8: Generate Evolution Report

```markdown
# Knowledge Evolution Report

**Date**: {date}
**Period reviewed**: Last 30 days ({start_date} to {end_date})
**Focus area**: {all | testing | deployment | etc.}

---

## Executive Summary

**Drift detected**: {count} areas
**New patterns**: {count} patterns
**Abandoned patterns**: {count} patterns
**Proposed updates**: {count} proposals

**Overall assessment**: {Healthy | Minor drift | Significant drift | Major divergence}

---

## Drift Analysis

### Positive Drift (Practices Improved)

#### 1. {Pattern name}
**What changed**: {Description}

**Evidence** ({count} instances):
- Git commit {hash}: {description}
- Observation: `.claude/observations/{date}/...`
- Journal: `.claude/journals/{category}/{date}-...`

**Old approach** (documented):
```
{What CLAUDE.md said}
```

**New approach** (actual):
```
{What actually happens now}
```

**Why it's better**:
- {Benefit 1}
- {Benefit 2}

**Recommendation**: Update CLAUDE.md to reflect improvement
**Priority**: HIGH | MEDIUM | LOW

---

#### 2. {Pattern name}
[...]

---

### Negative Drift (Practices Degraded)

#### 1. {Pattern name}
**What changed**: {Description}

**Evidence** ({count} instances):
[...]

**Documented principle**:
```
{What CLAUDE.md says}
```

**Actual practice**:
```
{Violations found}
```

**Why it's concerning**:
- {Risk 1}
- {Risk 2}

**Recommendation**:
- Option A: Revert to documented principle (if principle is correct)
- Option B: Update principle (if practice is better)

**Priority**: HIGH | MEDIUM | LOW

---

#### 2. {Pattern name}
[...]

---

## New Patterns Discovered

### 1. {Pattern name}
**Where found**: {journals, observations, code}

**Frequency**: {count} instances

**Pattern description**:
```
{What the pattern is}
```

**Examples**:
- {Example 1}
- {Example 2}

**Why it's significant**:
- {Reason it should be documented}

**Confidence**: HIGH | MEDIUM | LOW

**Recommendation**:
- If HIGH confidence: Add to CLAUDE.md or skill
- If MEDIUM: Monitor for more instances
- If LOW: Note as potential pattern

**Graduation path**:
- [ ] Add to {skill_name} skill
- [ ] Add to CLAUDE.md: {section}
- [ ] Create abstraction for pattern
- [ ] Create template/example

**Priority**: HIGH | MEDIUM | LOW

---

### 2. {Pattern name}
[...]

---

## Abandoned Patterns

### 1. {Pattern name}
**Documented in**: {CLAUDE.md section or skill}

**Last used**: {date or "Not found in last 30 days"}

**Pattern description**:
```
{What the pattern was}
```

**Why abandoned** (hypothesis):
- {Possible reason 1}
- {Possible reason 2}

**Recommendation**:
- Option A: Remove from documentation (if obsolete)
- Option B: Investigate why not used (if still valuable)
- Option C: Remind team of pattern (if forgotten)

**Priority**: HIGH | MEDIUM | LOW

---

### 2. {Pattern name}
[...]

---

## Skill-Specific Findings

### testing-workflow Skill
**Drift detected**: {YES/NO}

**Findings**:
- {Finding 1}
- {Finding 2}

**Proposed updates**:
```diff
- Old pattern
+ New pattern
```

---

### deployment Skill
[...]

---

### error-investigation Skill
[...]

---

## CLAUDE.md Updates Needed

### Section: {Section name}
**Current principle**:
```
{Current text}
```

**Proposed change**:
```diff
- Old principle
+ Updated principle
```

**Rationale**: {Why this change}

**Evidence**: {Links to journals/observations}

**Impact**: {What changes if principle updated}

---

### Section: {Section name}
[...]

---

## Action Items (Prioritized)

### High Priority (Do This Week)
- [ ] Update CLAUDE.md: {section} → {change}
- [ ] Update skill: {skill_name} → {change}
- [ ] Validate: `/validate "{claim about new pattern}"`
- [ ] Document: `/journal meta "Evolution finding: ..."`

### Medium Priority (Do This Month)
- [ ] Create ADR: {decision to formalize}
- [ ] Graduate pattern: {from abstraction to skill}
- [ ] Investigate: {why pattern abandoned}

### Low Priority (Backlog)
- [ ] Monitor pattern: {potential pattern, need more data}
- [ ] Review similar code: {apply pattern elsewhere}

---

## Recommendations

### Immediate Actions
1. {Most critical update}
2. {Second most critical}
3. {Third most critical}

### Investigation Needed
- {Question 1 to answer}
- {Question 2 to answer}

### Future Monitoring
- Watch for: {pattern to track}
- Measure: {metric to track}

---

## Metrics

**Review scope**:
- Git commits: {count}
- Journals: {count}
- Observations: {count}
- Abstractions: {count}
- Code files: {count}

**Drift indicators**:
- Positive drift: {count} patterns
- Negative drift: {count} patterns
- New patterns: {count}
- Abandoned: {count}

**Update proposals**:
- High priority: {count}
- Medium priority: {count}
- Low priority: {count}

---

## Next Evolution Review

**Recommended**: {date (30 days from now)}

**Focus areas for next time**:
- {Area to watch}
- {Pattern to validate}

---

*Report generated by `/evolve {focus_area}`*
*Generated: {timestamp}*
```

---

### Step 9: Save Report

Create: `.claude/evolution/{date}-{focus_area}.md`

**Example**: `.claude/evolution/2025-12-24-all.md`

Display summary:
```
✅ Evolution review complete

Focus: {all | testing | etc.}
Period: Last 30 days

Findings:
- Positive drift: {count} ✅
- Negative drift: {count} ⚠️
- New patterns: {count} 💡
- Abandoned patterns: {count} 🗑️

Priority actions: {count}

Report: .claude/evolution/2025-12-24-{focus_area}.md

Next review: {date + 30 days}
```

---

## Examples

### Example 1: Full Evolution Review

```bash
/evolve
```

**Output**:
```markdown
# Knowledge Evolution Report

**Date**: 2025-12-24
**Period reviewed**: Last 30 days (2025-11-24 to 2025-12-24)
**Focus area**: all

---

## Executive Summary

**Drift detected**: 4 areas
**New patterns**: 2 patterns
**Abandoned patterns**: 1 pattern
**Proposed updates**: 7 proposals

**Overall assessment**: Minor drift - practices have improved in testing
and error handling, some CLAUDE.md updates needed

---

## Positive Drift (Practices Improved)

### 1. Research Before Iteration (Infrastructure)
**What changed**: Now ALWAYS research first for infrastructure bugs,
not "after 2 failed attempts"

**Evidence** (8 instances):
- Observation: failure-143205-lambda-timeout.md (researched immediately)
- Observation: failure-091234-aurora-connection.md (researched immediately)
- Journal: error-2025-12-10-rds-permissions.md (research-first approach)
- [5 more instances]

**Old approach** (CLAUDE.md):
```
Research Before Iteration Principle:
- After 2 failed attempts, STOP and research
```

**New approach** (actual):
```
Infrastructure bugs: ALWAYS research first
UI bugs: Iterate first
After 2 failed attempts on ANY bug: research
```

**Why it's better**:
- Saved 3+ deployment cycles on infrastructure bugs
- 100% success rate when researching first
- Iteration on infrastructure is expensive (slow feedback)

**Recommendation**: Update CLAUDE.md to distinguish infrastructure vs UI

**Priority**: HIGH

---

### 2. External API Resilience
**What changed**: New pattern emerged - all external APIs now have
timeout + fallback

**Evidence** (5 instances):
- Abstraction: failure_mode-2025-12-15-external-api-timeout.md
- Journal: error-2025-12-15-lambda-timeout-yfinance.md (added timeout)
- Journal: error-2025-12-18-newsapi-slow.md (added timeout)
- Code: 5 API calls updated with timeout parameter

**Pattern description**:
```python
# Before
response = requests.get(url)

# After
try:
    response = requests.get(url, timeout=5)
except Timeout:
    return get_cached_data()
```

**Why it's better**:
- Prevents Lambda timeouts (3 incidents resolved)
- Graceful degradation (stale data > no data)
- Predictable performance

**Recommendation**: Add "External API Resilience Principle" to CLAUDE.md

**Priority**: HIGH

---

## New Patterns Discovered

### 1. Loud Mock Pattern
**Where found**: Code, journals (meta category)

**Frequency**: 3 instances

**Pattern description**:
Mock data in production code must be centralized, explicit, and loud
to prevent silent failures and forgotten mocks

**Examples**:
- src/mocks/__init__.py - Centralized registry
- Startup logging of active mocks
- Environment variable gating

**Why it's significant**:
- Prevents accidental mock data in production
- Makes mock usage transparent
- Easy to audit before deployment

**Confidence**: HIGH (well-documented in code and journal)

**Recommendation**: Add to CLAUDE.md "Code Organization" section

**Priority**: MEDIUM

---

## Abandoned Patterns

### 1. Direct External API Calls
**Documented in**: CLAUDE.md (old pattern from 6 months ago)

**Last used**: Not found in last 30 days

**Pattern description**:
API endpoints directly calling yfinance/NewsAPI during request

**Why abandoned**:
- Migrated to Aurora-First Architecture (ADR-008)
- All data pre-populated nightly
- APIs now read-only from Aurora

**Recommendation**: Remove from CLAUDE.md (obsolete pattern)

**Priority**: MEDIUM

---

## Action Items (Prioritized)

### High Priority (Do This Week)
- [ ] Update CLAUDE.md: "Research Before Iteration" → Distinguish infra vs UI
- [ ] Add CLAUDE.md: "External API Resilience Principle"
- [ ] Update error-investigation skill: Add "External API Timeout" pattern

### Medium Priority (Do This Month)
- [ ] Add CLAUDE.md: "Loud Mock Pattern"
- [ ] Remove CLAUDE.md: Direct API call pattern (obsolete)
- [ ] Graduate pattern: External API resilience → deployment skill

### Low Priority (Backlog)
- [ ] Monitor: Loud Mock pattern adoption in new code

---

✅ Evolution review complete

Focus: all
Period: Last 30 days

Findings:
- Positive drift: 2 ✅
- Negative drift: 0 ⚠️
- New patterns: 1 💡
- Abandoned patterns: 1 🗑️

Priority actions: 5

Report: .claude/evolution/2025-12-24-all.md

Next review: 2026-01-24
```

---

### Example 2: Focused Review (Testing)

```bash
/evolve testing
```

**Output** (condensed):
```markdown
# Knowledge Evolution Report - Testing

**Focus area**: testing

---

## Findings

### Positive Drift: Test Tier Usage
Evidence shows test tiers (0-4) now consistently used.
All PRs include tier classification.

**Recommendation**: CLAUDE.md already documents this - no update needed ✅

---

### New Pattern: Property-Based Testing
Found 3 instances of property-based tests (fast-check).
Not documented in testing-workflow skill.

**Recommendation**: Add to testing-workflow skill

**Priority**: MEDIUM

---

### Negative Drift: Test Sabotage Verification
Documented principle: "After writing test, break code to verify test catches it"
Found: Only 2 out of 12 new tests verified this way

**Recommendation**: Add reminder in testing-workflow skill
Investigate: Why not following this principle?

**Priority**: HIGH

---

Action items: 2 high, 1 medium
```

---

## Integration with Other Commands

### Report → Evolve
```
/report week
    ↓ (shows patterns in recent work)
/evolve
    ↓ (detects if patterns should become principles)
```

### Abstract → Evolve
```
/abstract ".claude/observations/*/failure-*.md"
    ↓ (extracts failure pattern with HIGH confidence)
/evolve error-handling
    ↓ (proposes adding pattern to error-investigation skill)
```

### Journal → Evolve
```
Multiple architecture journals document same trade-off
    ↓
/evolve architecture
    ↓ (detects recurring decision pattern)
Proposes: Create decision heuristic in CLAUDE.md
```

---

## Principles

### 1. Principles Evolve Through Practice

Documented principles should reflect actual practices, not aspirational ideals.

### 2. Detect Drift Early

Monthly evolution reviews prevent large divergences.

### 3. Positive Drift is Good

When practices improve beyond documentation, update documentation.

### 4. Evidence-Based Updates

All proposals must have evidence (journals, observations, code).

### 5. Prioritize Updates

Not all drift needs immediate fixing. Prioritize by impact.

---

## Related Commands

- `/report` - Provides data for evolution analysis
- `/abstract` - Patterns that may need graduation
- `/journal` - Documents that inform evolution
- `/observe` - Evidence of actual practices

---

## See Also

- `.claude/commands/report.md` - Session reporting
- `.claude/commands/abstract.md` - Pattern extraction
- `.claude/CLAUDE.md` - Principles being evolved
- `.claude/skills/` - Skills being updated
