---
name: diff-explain
description: Explain what changed and why in git diffs
accepts_args: true
arg_schema:
  - name: target
    required: false
    description: "Optional: commit hash, branch name, or 'staged' (default: HEAD)"
composition:
  - skill: research
---

# /diff-explain - Git Diff Analysis

**Purpose**: Analyze git diffs and explain what changed, why it changed, and impact

**Category**: Code Review Tool

**When to use**:
- Code review (understand changes quickly)
- Understanding unfamiliar commits
- Before merging PR (impact analysis)
- Post-deployment verification (what actually changed)
- Learning from past changes (historical analysis)

**Core Principle**: "Code review should understand intent, not just syntax"

---

## Usage

```bash
# Uncommitted changes (working directory)
/diff-explain

# Staged changes only (what's ready to commit)
/diff-explain staged

# Last commit
/diff-explain HEAD~1

# Specific commit
/diff-explain abc123f

# Specific commit vs HEAD
/diff-explain abc123f

# Commit range
/diff-explain main..dev
/diff-explain HEAD~5..HEAD

# Compare branches
/diff-explain main..feature/new-api
```

---

## What it Analyzes

### 1. What Changed
- File-by-file breakdown
- Added/modified/deleted lines
- Structural changes (new classes, functions, endpoints)

### 2. Why Changed
- Inferred from commit messages
- Inferred from code context (comments, naming)
- Inferred from related changes (tests, docs)

### 3. Impact
- Affected components (frontend, backend, database)
- Breaking changes (API signature changes, schema changes)
- Performance implications (new queries, loops, network calls)

### 4. Principle Adherence
- Defensive Programming checks
- Multi-Layer Verification usage
- Error Handling Duality
- Testing Anti-Patterns

---

## Output Structure

```markdown
# Diff Explanation: {Target}

**Comparing**: {base} → {target}
**Generated**: 2025-12-28
**Author**: {commit author if single commit}
**Files Changed**: {count}
**Insertions**: +{count} lines
**Deletions**: -{count} lines

---

## Summary

**Overall Intent**: {Inferred from commit message + code changes}

**Change Type**: {Feature/Bugfix/Refactor/Docs/Infrastructure}

**Risk Level**: {Low/Medium/High}
- Low: Documentation, tests, internal refactor
- Medium: New feature, API changes (backward compatible)
- High: Breaking changes, database migrations, security fixes

---

## Changes by File

### File 1: `{path}` (+{lines}, -{lines})

**Change Type**: {Added/Modified/Deleted}

**What changed**:
- {Change 1: Added new function `foo()`}
- {Change 2: Modified validation in `bar()`}
- {Change 3: Removed deprecated `baz()`}

**Why changed** (inferred):
- {Reason 1: Support new feature X}
- {Reason 2: Fix edge case Y}
- {Reason 3: Clean up unused code}

**Code Snippet** (key changes):
```python
# Added: Input validation (Defensive Programming)
@app.post("/backtest/cancel")
async def cancel_backtest(backtest_id: str):
    if not backtest_id:
        raise HTTPException(400, "backtest_id required")  # Fail fast

    # Multi-layer verification
    result = db.execute("UPDATE backtests SET status='cancelled' WHERE id=?", backtest_id)
    if result.rowcount == 0:
        raise HTTPException(404, f"Backtest {backtest_id} not found")

    return {"status": "cancelled"}
```

**Impact**:
- **Frontend**: Needs "Cancel" button added
- **API**: New endpoint (backward compatible)
- **Database**: Needs "cancelled" status in enum
- **Tests**: New test coverage required

**Risk**: {Low/Medium/High} - {Explanation}

---

[Repeat for each file]

---

## Principles Adherence

### ✅ Followed

**Defensive Programming**:
- ✅ Line 45: Validates `backtest_id` is not empty (fail fast)
- ✅ Line 50: Checks rowcount after UPDATE (explicit failure detection)
- ✅ Line 51: Raises 404 if backtest not found (no silent failure)

**Multi-Layer Verification**:
- ✅ Line 50: Checks database rowcount (layer 2: payload verification)
- ⚠️ Missing: CloudWatch log verification (layer 3)

**Testing Anti-Patterns Awareness**:
- ✅ Tests verify actual cancellation (`assert status == 'cancelled'`)
- ✅ Tests cover edge case (backtest not found → 404)

---

### ⚠️ Potential Issues

**Missing Multi-Layer Verification**:
- Issue: Only checks database rowcount
- Recommendation: Add CloudWatch log entry for audit trail
- Example:
```python
logger.info(f"Backtest {backtest_id} cancelled by user {user_id}")
```

**Error Handling**:
- Issue: Generic HTTPException, no custom error code
- Recommendation: Use structured error responses
- Example:
```python
raise HTTPException(404, detail={
    "error_code": "BACKTEST_NOT_FOUND",
    "message": f"Backtest {backtest_id} not found"
})
```

---

## Impact Analysis

### Affected Components

**Backend**:
- New endpoint: `POST /backtest/cancel`
- Database: Needs "cancelled" status added to enum
- Tests: `tests/integration/test_backtest_cancel.py` (new file)

**Frontend**:
- Needs: "Cancel" button in backtest UI
- API integration: Call `POST /backtest/cancel`

**Infrastructure**:
- No changes required (Lambda permissions already sufficient)

**Documentation**:
- Update: `spec/API_CONTRACT.md` (new endpoint)
- Update: Database migration (add cancelled status)

---

### Breaking Changes

**API Changes**:
- None (backward compatible addition)

**Database Changes**:
- ⚠️ Migration required: Add "cancelled" to backtest status enum
- Migration file: `migrations/002_add_cancelled_status.sql`

**Deprecations**:
- ❌ Removed: `GET /backtest/legacy` (breaking change!)
- Migration path: Use `POST /backtest/run` instead
- Client impact: LINE Bot needs update

---

### Performance Implications

**Database**:
- New query: `UPDATE backtests SET status='cancelled'`
- Impact: Low (single row update, indexed on id)

**API**:
- New endpoint: Expected 10-20 requests/day
- Impact: Negligible

**No Concerns**: Change is lightweight, no performance risk

---

## Related Changes

### Similar Past Changes

**2025-12-10**: Added cancel endpoint to scheduler
- Commit: `abc123f`
- Pattern: Same cancel pattern (validate → update → verify)
- Learning: Remember to add rollback capability

**2025-11-05**: Added pause endpoint to reports
- Commit: `def456g`
- Pattern: Similar lifecycle management

**Consistency**: ✅ Follows established cancel pattern

---

### Follow-Up Work Needed

**Required** (blocking merge):
- [ ] Update `spec/API_CONTRACT.md` with new endpoint
- [ ] Create database migration `migrations/002_add_cancelled_status.sql`
- [ ] Add tests for cancel functionality

**Recommended** (non-blocking):
- [ ] Add "Cancel" button to Telegram Mini App
- [ ] Add CloudWatch logging for audit trail
- [ ] Update LINE Bot to remove legacy endpoint usage

---

## Commit Message Analysis

**Original Commit Message**:
```
feat(api): Add cancel endpoint for backtester

- Add POST /backtest/cancel endpoint
- Remove deprecated GET /backtest/legacy
- Update tests for cancel functionality

Breaking change: Removed GET /backtest/legacy
Migration: Use POST /backtest/run instead
```

**Quality**: ✅ **Excellent**

**Why excellent**:
- Clear type prefix (`feat:`) indicates new feature
- Scope indicated (`api`)
- Breaking change called out explicitly
- Migration path provided
- Follows Conventional Commits standard

**Suggestions**:
- None (message is well-structured)

---

### Commit Message Anti-Patterns

**If message was poor**:

❌ **Bad Example**:
```
fixed stuff
```

**Issues**:
- No context (what stuff?)
- No type (feat/fix/refactor?)
- No scope (what area?)
- No details (why? impact?)

✅ **Good Template**:
```
<type>(<scope>): <subject>

<body explaining why and what>

<footer with breaking changes, references>
```

---

## Review Checklist

**Based on this diff, reviewer should check**:

### Functionality
- [ ] Cancel validation covers all edge cases (empty id, invalid id, already cancelled)
- [ ] Tests verify actual cancellation (not just that function was called)
- [ ] Error messages are clear and actionable

### Code Quality
- [ ] Follows Defensive Programming (validates inputs, explicit failures)
- [ ] Error handling uses exceptions (not state-based for utility function)
- [ ] Code is readable (clear variable names, comments where needed)

### Testing
- [ ] Unit tests cover happy path
- [ ] Unit tests cover edge cases (not found, already cancelled)
- [ ] Integration tests verify end-to-end flow

### Documentation
- [ ] `API_CONTRACT.md` updated
- [ ] Database migration created
- [ ] Breaking changes documented

### Infrastructure
- [ ] No new AWS resources needed (verified)
- [ ] Existing Lambda permissions sufficient (verified)

---

## Principle Violations (if any)

### None Found ✅

**This change follows all core principles**:
- Defensive Programming: ✅ Validates inputs, fails fast
- Multi-Layer Verification: ⚠️ Partial (could add CloudWatch logging)
- Error Handling Duality: ✅ Uses exceptions (utility function)
- Testing Anti-Patterns Awareness: ✅ Tests outcomes, not execution

---

## Risk Assessment

### Overall Risk: **Low-Medium**

**Low Risk Factors**:
- Backward compatible (new endpoint, no changes to existing)
- Simple logic (validate → update → verify)
- Well-tested (unit + integration tests)

**Medium Risk Factors**:
- Breaking change (removed legacy endpoint)
- Database migration required
- Client impact (LINE Bot needs update)

**Mitigation**:
- Deploy migration before deploying code
- Update clients before removing legacy endpoint
- Monitor error rates for 24h post-deployment

---

## Rollback Plan

**If issues arise**:

1. **Revert code deployment** (~5 min):
```bash
ENV=prod doppler run -- aws lambda update-function-code \
  --function-name telegram-api \
  --image-uri {previous-digest}
```

2. **No database rollback needed**:
- Migration added status, didn't remove anything
- Safe to keep "cancelled" status even if code reverted

3. **Re-enable legacy endpoint** (if clients break):
```python
@app.get("/backtest/legacy")  # Temporarily re-add
async def legacy_endpoint():
    return {"deprecated": true, "use": "/backtest/run"}
```

---

## Timeline

**Commit History** (if range):
- 2025-12-20: Added cancel endpoint
- 2025-12-21: Added tests
- 2025-12-22: Updated docs

**Estimated Development Time**: 3 hours
- Design: 30 min
- Implementation: 1.5 hours
- Testing: 45 min
- Documentation: 15 min

---

## See Also

- Similar changes: `git log --grep="cancel" --oneline`
- Related PRs: GitHub PR #123
- Database migrations: `migrations/README.md`
- API docs: `spec/API_CONTRACT.md`

---

```

---

## Examples

### Example 1: Uncommitted Changes

```bash
/diff-explain
```

**Output**: Analysis of working directory changes (not yet committed)

**Use case**: Before committing, understand what you're about to commit

**Duration**: ~1 minute

---

### Example 2: Staged Changes

```bash
/diff-explain staged
```

**Output**: Analysis of staged changes only (ready to commit)

**Use case**: Review what's staged, ensure no unintended changes

**Duration**: ~1 minute

---

### Example 3: Specific Commit

```bash
/diff-explain HEAD~1
```

**Output**: Analysis of last commit with:
- Commit message quality assessment
- Code changes explanation
- Impact analysis
- Principle adherence check

**Use case**: Understand recent commit (yours or teammate's)

**Duration**: ~2 minutes

---

### Example 4: Commit Range (PR Review)

```bash
/diff-explain main..feature/new-api
```

**Output**: Analysis of all commits in PR:
- Summary of overall changes
- File-by-file breakdown
- Breaking changes identified
- Review checklist generated

**Use case**: Code review before merging PR

**Duration**: ~5 minutes (for 10-file PR)

---

## Decision Tree

```
Want to understand changes?
  │
  ├─ Before committing?
  │  └─ /diff-explain (or /diff-explain staged)
  │
  ├─ Code review (PR)?
  │  └─ /diff-explain main..{branch}
  │
  ├─ Understanding past commit?
  │  └─ /diff-explain {commit-hash}
  │
  ├─ Post-deployment verification?
  │  └─ /diff-explain {prev-commit}..{current-commit}
  │
  └─ Learning from history?
     └─ /diff-explain {date-range or commits}
```

---

## vs Related Commands

### vs `git diff`
- **`git diff`**: Raw diff (syntax)
- **`/diff-explain`**: Explained diff (intent + impact)

**When to use git diff**: Quick syntax check
**When to use /diff-explain**: Understanding intent and impact

---

### vs Code Review Tools (GitHub PR)
- **GitHub PR**: UI-based review, comments, approvals
- **`/diff-explain`**: Automated analysis, principle checks, impact assessment

**Relationship**: Complementary (use both)
**Workflow**: `/diff-explain` → read analysis → GitHub PR review → approve

---

## Anti-Patterns

### ❌ Using for Trivial Changes

```bash
# Bad
/diff-explain  # Changed: one comment typo
```

**Why bad**: Overhead for trivial change
**Better**: Just commit (or use `git diff` for quick check)

---

### ❌ Using for Non-Code Changes

```bash
# Bad
/diff-explain  # Changed: README formatting
```

**Why bad**: Principle checks not applicable to docs
**Better**: Quick visual review sufficient

---

### ❌ Replacing Actual Code Review

```bash
# Bad
/diff-explain → Auto-approve PR (skipped reading code)
```

**Why bad**: Automated analysis complements, doesn't replace human review
**Better**: Use /diff-explain as first pass, then manual review

---

## Integration with Workflow

### Pre-Commit Workflow

```bash
# 1. Check what you're about to commit
/diff-explain

# 2. Review explanation (ensure matches intent)

# 3. Commit if explanation looks good
git commit -m "feat(api): Add cancel endpoint"

# 4. Push
git push
```

---

### Code Review Workflow

```bash
# 1. Analyze PR changes
/diff-explain main..feature/new-api

# 2. Read generated review checklist

# 3. Manually review critical sections

# 4. Comment on GitHub PR

# 5. Approve or request changes
```

---

### Post-Deployment Workflow

```bash
# 1. Compare deployed vs previous
/diff-explain {prev-tag}..{current-tag}

# 2. Verify changes match deployment notes

# 3. Check for unintended changes

# 4. Monitor CloudWatch for principle violations
```

---

## Success Metrics

**Diff explanation is valuable when**:
- [ ] Reviewer understands intent without asking author
- [ ] Breaking changes identified automatically
- [ ] Principle violations caught before merge
- [ ] Impact analysis is accurate (matches actual impact)
- [ ] Review checklist covers what reviewer manually checks

---

## Maintenance

### Update Triggers
- New principles added to CLAUDE.md (update adherence checks)
- New patterns emerge (update what to look for)
- False positives in analysis (refine detection logic)

### Quality Checks
- [ ] Intent inference is accurate (matches commit message)
- [ ] Impact analysis covers all components
- [ ] Principle checks are relevant (not generic)
- [ ] Review checklist is actionable

---

## See Also

- `/observe execution` - Capture what you did (input for understanding changes)
- `/journal` - Document why you made changes
- `.claude/CLAUDE.md` - Principles checked in analysis
- `docs/CODE_STYLE.md` - Code style guidelines
- `git log` - Command-line git history
