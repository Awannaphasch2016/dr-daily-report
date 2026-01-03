# Checklist: Monthly CLI/Justfile Drift Review

**Purpose**: Scheduled monthly review to detect and fix CLI/Justfile drift

**When to use**: First Monday of each month

**Estimated time**: 30-60 minutes

---

## Preparation (5 minutes)

- [ ] **Schedule review**
  - Date: First Monday of month
  - Time: 30-60 minutes
  - Calendar invite: "Monthly CLI/Justfile Drift Review"

- [ ] **Notify team**
  - Post in team chat: "Running monthly CLI sync review today"
  - Request: "Hold off on CLI changes until review complete"

- [ ] **Prepare environment**
  - Pull latest from `dev` branch
  - Ensure clean working directory
  - Doppler configured for dev environment

---

## Execution (20-40 minutes)

### Step 1: Run Drift Detection

- [ ] **Execute drift detection**
  ```bash
  /evolve cli
  ```

- [ ] **Review output**
  - Report saved to: `.claude/evolution/YYYY-MM-DD-cli.md`
  - Open and read full report

- [ ] **Note drift statistics**
  - Commands without recipes: ____ (count)
  - Recipes without commands: ____ (count)
  - Documentation mismatches: ____ (count)
  - New commands added this month: ____ (count)

---

### Step 2: Triage Findings

For each drift instance, assign priority:

#### High Priority (Fix Today)

Mark as high priority if:
- [ ] Production deployment command affected
- [ ] Security-critical command missing docs
- [ ] Breaking change not reflected in docs
- [ ] Commonly-used command (>5x/week) affected

**High priority drift**:
1. _______________________________ (command/recipe name)
2. _______________________________ (command/recipe name)
3. _______________________________ (command/recipe name)

---

#### Medium Priority (Fix This Week)

Mark as medium priority if:
- [ ] Developer-facing command not documented
- [ ] New command added 2+ weeks ago without docs
- [ ] Moderate inconsistency in naming/help text

**Medium priority drift**:
1. _______________________________ (command/recipe name)
2. _______________________________ (command/recipe name)
3. _______________________________ (command/recipe name)

---

#### Low Priority (Backlog)

Mark as low priority if:
- [ ] Rarely-used command (<1x/month)
- [ ] Minor documentation wording issue
- [ ] Cosmetic inconsistency

**Low priority drift**:
1. _______________________________ (command/recipe name)
2. _______________________________ (command/recipe name)
3. _______________________________ (command/recipe name)

---

### Step 3: Fix High Priority Drift

For each high priority drift:

- [ ] **Understand the issue**
  - What's missing/wrong?
  - When was it introduced?
  - Why wasn't it caught earlier?

- [ ] **Apply fix**
  - Follow: [CLI Sync Verification Checklist](./cli-sync-verification.md)
  - Update both layers (dr CLI + Justfile)
  - Update documentation

- [ ] **Verify fix**
  ```bash
  # Test command/recipe
  dr <group> <command> --help
  just <recipe-name>

  # Re-run drift detection
  /evolve cli
  ```

- [ ] **Document fix**
  - Note what was fixed
  - Note root cause
  - Update this review checklist if needed

---

### Step 4: Create Tickets for Medium/Low Priority

- [ ] **Create tickets**
  - One ticket per drift instance
  - Title: "CLI Drift: <command/recipe name>"
  - Description: Link to evolution report
  - Priority: Medium or Low
  - Assign: To appropriate developer

**Tickets created**:
1. #____ - ______________________________
2. #____ - ______________________________
3. #____ - ______________________________

---

### Step 5: Analyze Patterns

Look for recurring patterns in this month's drift:

- [ ] **Same developer missing steps?**
  - Developer name: ______________________________
  - Action: Remind about pre-commit checklist

- [ ] **Same command group affected?**
  - Command group: ______________________________
  - Action: Review group-specific documentation

- [ ] **Same type of drift recurring?**
  - Drift type: ______________________________
  - Action: Add to automated detection

- [ ] **New pattern discovered?**
  - Pattern: ______________________________
  - Action: Update maintenance process docs

---

## Analysis (10-15 minutes)

### Drift Metrics

Record metrics for tracking health over time:

- [ ] **This month's metrics**
  - Drift instances: ____ (total count)
  - High priority: ____
  - Medium priority: ____
  - Low priority: ____
  - Fix time (avg): ____ hours

- [ ] **Compare to last month**
  - Drift trend: Increasing / Decreasing / Stable
  - Fix time trend: Faster / Slower / Same

- [ ] **Root cause analysis**
  - Most common cause: ______________________________
  - Contributing factors:
    1. ______________________________
    2. ______________________________

---

### Process Health

Evaluate synchronization process health:

- [ ] **Detection effectiveness**
  - Was all drift detected? YES / NO
  - False positives? ____ (count)
  - False negatives? ____ (count)

- [ ] **Prevention effectiveness**
  - Pre-commit checklist used? YES / NO / SOMETIMES
  - CI/CD validation working? YES / NO / N/A
  - Developer awareness: High / Medium / Low

- [ ] **Fix efficiency**
  - High priority fixed same day? YES / NO
  - Medium priority fixed within week? YES / NO
  - Average fix time: ____ hours

---

## Recommendations (5 minutes)

Based on this month's review:

### Process Improvements

- [ ] **Recommendation 1**
  - Issue: ______________________________
  - Proposal: ______________________________
  - Owner: ______________________________
  - Priority: High / Medium / Low

- [ ] **Recommendation 2**
  - Issue: ______________________________
  - Proposal: ______________________________
  - Owner: ______________________________
  - Priority: High / Medium / Low

### Documentation Updates

- [ ] **Update needed in**:
  - [ ] .claude/processes/cli-justfile-maintenance.md
  - [ ] .claude/checklists/adding-cli-command.md
  - [ ] .claude/checklists/cli-sync-verification.md
  - [ ] docs/PROJECT_CONVENTIONS.md
  - [ ] Other: ______________________________

### Automation Opportunities

- [ ] **Can automate**:
  - [ ] Drift detection in CI/CD
  - [ ] Pre-commit hook for verification
  - [ ] Monthly drift report generation
  - [ ] Command/recipe mapping generation
  - [ ] Other: ______________________________

---

## Communication (5 minutes)

### Share Findings

- [ ] **Post summary to team**
  - Platform: Slack / Email / GitHub Discussion
  - Include: Drift count, priority breakdown, actions taken
  - Thank team for cooperation

**Example message**:
```
🔍 Monthly CLI/Justfile Drift Review (January 2026)

Total drift: 5 instances
- High priority: 1 (fixed today ✅)
- Medium priority: 3 (tickets created)
- Low priority: 1 (backlog)

Pattern: Noticed developers forgetting Justfile recipes when adding dr commands
Action: Updated pre-commit checklist with reminder

Next review: February 3, 2026
```

### Update Logs

- [ ] **Log in journal**
  ```bash
  /journal process "Monthly CLI sync review - Jan 2026: <summary>"
  ```

- [ ] **Update evolution report** (if needed)
  - Add any additional findings
  - Document lessons learned

---

## Follow-Up (Ongoing)

### Track Ticket Progress

- [ ] **Monday + 3 days**: Check medium priority tickets
  - Any blockers? ______________________________
  - Need help? ______________________________

- [ ] **Monday + 7 days**: Verify medium priority complete
  - All fixed? YES / NO
  - Re-run `/evolve cli` if needed

### Schedule Next Review

- [ ] **Next review date**: ______________ (First Monday of next month)

- [ ] **Calendar invite sent**: YES / NO

- [ ] **Checklist ready**: Print/bookmark this checklist

---

## Completion Criteria

Before marking review complete:

- [ ] **Drift detection run**: ✅
- [ ] **High priority fixed**: ✅
- [ ] **Tickets created for medium/low**: ✅
- [ ] **Patterns analyzed**: ✅
- [ ] **Metrics recorded**: ✅
- [ ] **Recommendations documented**: ✅
- [ ] **Team notified**: ✅
- [ ] **Next review scheduled**: ✅

---

## Review History

Track completion over time:

| Date | Drift Count | High Pri Fixed | Tickets Created | Notes |
|------|-------------|----------------|-----------------|-------|
| YYYY-MM-DD | X | X | X | Pattern: ... |
| YYYY-MM-DD | X | X | X | Pattern: ... |
| YYYY-MM-DD | X | X | X | Pattern: ... |

---

## Related Documentation

- [CLI/Justfile Maintenance Process](./../processes/cli-justfile-maintenance.md)
- [Adding CLI Command Checklist](./adding-cli-command.md)
- [CLI Sync Verification Checklist](./cli-sync-verification.md)
- [Evolve Command - CLI Focus](./../commands/evolve.md)

---

**Created**: 2025-12-31
**Checklist Type**: Monthly review
**Review Frequency**: First Monday of each month
**Estimated Time**: 30-60 minutes
