---
name: restore-plan
description: Restore plan from /tmp/ backup (created by /copy-plan)
accepts_args: false
---

# Restore-Plan Command

**Purpose**: Restore plan from `/tmp/` backup after exploration

**Core Principle**: "Easy revert enables fearless exploration" - explore alternatives knowing you can always go back

**When to use**:
- After exploration (want to revert to original plan)
- Made plan changes that didn't work out (need to undo)
- Comparing multiple plan iterations (restore specific version)
- Accidentally overwrote plan (recover from backup)

**When NOT to use**:
- No backups in /tmp/ (nothing to restore)
- Current plan is what you want (no need to restore)
- Plan already in git (use git checkout instead)

---

## Quick Reference

```bash
# Explored alternative, want to restore original plan
/restore-plan
→ Available backups:
  1. /tmp/plan-backup-2026-01-03-110000.md (15 KB, 30 minutes ago)
  2. /tmp/plan-backup-2026-01-03-113000.md (18 KB, 5 minutes ago)
→ Select: 1
→ Plan restored from /tmp/plan-backup-2026-01-03-110000.md
```

---

## Execution Flow

### Step 1: List Available Backups

**Find backup files** in `/tmp/`:
```bash
ls -t /tmp/plan-backup-*.md 2>/dev/null
```

**Display with metadata**:
```
Available backups:

1. /tmp/plan-backup-2026-01-03-110000.md
   Size: 15 KB
   Created: 30 minutes ago (2026-01-03 11:00:00)

2. /tmp/plan-backup-2026-01-03-113000.md
   Size: 18 KB
   Created: 5 minutes ago (2026-01-03 11:30:00)

3. /tmp/plan-backup-2026-01-03-114500.md
   Size: 12 KB
   Created: 1 minute ago (2026-01-03 11:45:00)
```

**If no backups found**:
```
No plan backups found in /tmp/

Checked: /tmp/plan-backup-*.md

To create backups:
→ Use /copy-plan before exploration
→ Backups are created in /tmp/ with timestamps

If you have git commits:
→ Use git log .claude/plans/ to see history
→ Use git checkout <commit> -- .claude/plans/current-plan.md
```

---

### Step 2: Show Backup Previews

**For each backup, show preview** (first 10 lines):
```
Preview of backup 1:
─────────────────────────────────────────────────
# Implementation Plan: Lambda Timeout Increase

## Context
Current Lambda timeout: 30s
Target timeout: 120s
Reason: External API calls take 60-90s

## Steps
1. Update Terraform configuration
─────────────────────────────────────────────────

Preview of backup 2:
─────────────────────────────────────────────────
# Implementation Plan: Parallel Lambda Processing

## Context
Current: Sequential processing (46 tickers)
Target: Parallel processing (46 concurrent Lambdas)
─────────────────────────────────────────────────
```

**Allow user to compare**:
- Show preview of each backup
- Show current plan preview
- Help user identify which backup to restore

---

### Step 3: Prompt User Selection

**Ask which backup to restore**:
```
Select backup to restore:

1. /tmp/plan-backup-2026-01-03-110000.md (Lambda timeout approach)
2. /tmp/plan-backup-2026-01-03-113000.md (Parallel processing approach)
3. /tmp/plan-backup-2026-01-03-114500.md (Hybrid approach)

[Or type 'cancel' to abort]

Enter selection (1-3):
```

**User inputs**: Number (1, 2, 3) or 'cancel'

---

### Step 4: Confirm Overwrite

**Current plan will be overwritten**:
```
⚠️ Warning: This will overwrite current plan

Current plan: .claude/plans/current-plan.md (20 KB)
Will be replaced with: /tmp/plan-backup-2026-01-03-110000.md (15 KB)

Proceed? [yes/no]
```

**Safety check**:
- Show current plan size (so user knows what's being lost)
- Require explicit confirmation
- Allow abort without changes

---

### Step 5: Backup Current Plan (Before Restore)

**Create safety backup** before overwriting:
```bash
# Backup current plan before restore
SAFETY_BACKUP="/tmp/plan-before-restore-$(date +%Y-%m-%d-%H%M%S).md"
cp .claude/plans/current-plan.md "$SAFETY_BACKUP"
```

**Why safety backup**:
- If user restores wrong backup, can undo
- Prevents loss of current work
- Allows comparison after restore

**Confirm safety backup created**:
```
Safety backup created: /tmp/plan-before-restore-2026-01-03-115000.md

This allows undo if you restore the wrong backup.
```

---

### Step 6: Restore Selected Backup

**Execute restore**:
```bash
cp /tmp/plan-backup-2026-01-03-110000.md .claude/plans/current-plan.md
```

**Verify restore success**:
```bash
# Check file exists
ls -lh .claude/plans/current-plan.md

# Compare checksums (ensure identical to backup)
md5sum /tmp/plan-backup-2026-01-03-110000.md .claude/plans/current-plan.md
```

**If restore fails**:
```
Error: Failed to restore plan

Reason: {error message}

Current plan unchanged.
Safety backup preserved at: {path}

Manual restore:
cp /tmp/plan-backup-2026-01-03-110000.md .claude/plans/current-plan.md
```

---

### Step 7: Confirm to User

**Success message**:
```
✅ Plan restored successfully

Restored from: /tmp/plan-backup-2026-01-03-110000.md
To: .claude/plans/current-plan.md
Size: 15 KB

Safety backup (current plan before restore):
→ /tmp/plan-before-restore-2026-01-03-115000.md

You can now:
- Continue with restored plan
- Compare restored vs pre-restore: diff {paths}
- Undo restore: cp /tmp/plan-before-restore-*.md .claude/plans/current-plan.md
```

**Include undo instructions**:
- If user realizes they restored wrong backup
- How to compare restored vs previous
- Where safety backup is located

---

## Output Format

```markdown
# Plan Restore

**Date**: {YYYY-MM-DD HH:MM:SS}
**Action**: Restore plan from /tmp/ backup

---

## Available Backups

### Backup 1
**Path**: {/tmp/plan-backup-YYYY-MM-DD-HHmmss.md}
**Size**: {size in KB}
**Created**: {X minutes ago}

**Preview**:
```
{First 10 lines of backup}
```

[Repeat for each backup]

---

## Current Plan

**Path**: {.claude/plans/current-plan.md}
**Size**: {size in KB}

**Preview**:
```
{First 10 lines of current plan}
```

---

## Restore Confirmation

**Selected backup**: {backup number/path}
**Current plan will be overwritten**

**Safety backup created**: {/tmp/plan-before-restore-*.md}

Proceed? [Requires user confirmation]

---

## Restore Result

✅ **Status**: Success | Failed

**Restored from**: {backup path}
**To**: {.claude/plans/current-plan.md}
**Size**: {size in KB}

**Safety backup** (undo restore):
→ {/tmp/plan-before-restore-*.md}

---

## What's Next

**Continue with restored plan**:
```
Plan is now restored. You can:
- Review: cat .claude/plans/current-plan.md
- Edit: Continue modifying plan
- Commit: git add .claude/plans/current-plan.md
```

**Compare restored vs pre-restore**:
```bash
diff /tmp/plan-before-restore-*.md .claude/plans/current-plan.md
```

**Undo restore** (if wrong backup selected):
```bash
cp /tmp/plan-before-restore-*.md .claude/plans/current-plan.md
```
```

---

## Examples

### Example 1: Simple Restore

```bash
# Explored alternative, want original back
/restore-plan

Output:
Available backups:
1. /tmp/plan-backup-2026-01-03-110000.md (15 KB, 45 minutes ago)

Select: 1

⚠️ Warning: This will overwrite current plan
Proceed? yes

Safety backup created: /tmp/plan-before-restore-2026-01-03-115000.md

✅ Plan restored successfully

You can now continue with restored plan.
```

---

### Example 2: Multiple Backups, Need Preview

```bash
/restore-plan

Output:
Available backups:

1. /tmp/plan-backup-2026-01-03-110000.md (15 KB, 1 hour ago)
   Preview: # Implementation Plan: Lambda Timeout Increase

2. /tmp/plan-backup-2026-01-03-113000.md (18 KB, 30 minutes ago)
   Preview: # Implementation Plan: Parallel Lambda Processing

3. /tmp/plan-backup-2026-01-03-114500.md (12 KB, 15 minutes ago)
   Preview: # Implementation Plan: Hybrid Approach

Current plan:
   Preview: # Implementation Plan: Event-Driven Architecture

Select: 2  (Parallel processing approach)

⚠️ Warning: Current plan (Event-Driven Architecture) will be replaced
Proceed? yes

✅ Plan restored to Parallel Lambda Processing approach
```

---

### Example 3: Wrong Restore, Undo

```bash
/restore-plan

Select: 1
Proceed? yes

✅ Plan restored from backup 1

# Wait, I wanted backup 2!

# Undo using safety backup
cp /tmp/plan-before-restore-2026-01-03-115000.md .claude/plans/current-plan.md

# Try again
/restore-plan

Select: 2  (Correct backup this time)
Proceed? yes

✅ Plan restored successfully
```

---

### Example 4: No Backups Available

```bash
/restore-plan

Output:
No plan backups found in /tmp/

To create backups:
→ Use /copy-plan before exploration

If you have git commits:
→ git log .claude/plans/
→ git checkout <commit> -- .claude/plans/current-plan.md
```

---

## Workflow Integration

**Exploration workflow**:
```
Original plan → /copy-plan → Backup created
              ↓
         Explore alternatives
              ↓
         /restore-plan → Back to original

         OR

         Keep new plan → git commit
```

**Comparison workflow**:
```
Backup 1 (approach A) ← /restore-plan ← Compare
Backup 2 (approach B) ← /restore-plan ← Compare
Backup 3 (approach C) ← /restore-plan ← Compare
                                        ↓
                               Choose best approach
                                        ↓
                                   git commit
```

**Git integration**:
```bash
# Backups in /tmp/ (temporary exploration)
/copy-plan
/restore-plan

# Git commits (permanent versions)
git log .claude/plans/
git checkout <commit> -- .claude/plans/current-plan.md
```

---

## Best Practices

### Do
- **Review backup previews** before selecting (ensure correct backup)
- **Confirm overwrite** (current plan will be lost)
- **Use safety backup** if you realize wrong restore (undo capability)
- **Clean up old backups** after committing chosen approach

### Don't
- **Don't skip confirmation** (easy to select wrong backup)
- **Don't delete safety backup immediately** (might need undo)
- **Don't restore without previewing** (might overwrite with wrong backup)
- **Don't rely on /tmp/ long-term** (use git for permanent versions)

---

## Integration with Other Commands

**`/copy-plan` → `/restore-plan`**:
- Create backup before exploration
- Explore alternatives
- Restore original if exploration didn't work out

**`/restore-plan` → git**:
- Restore chosen backup
- Review restored plan
- Commit to git for permanent version

**EnterPlanMode → `/copy-plan` → `/restore-plan`**:
- Create initial plan (EnterPlanMode)
- Backup before changes (/copy-plan)
- Restore if changes didn't work out (/restore-plan)

---

## See Also

- **`/copy-plan`** - Create backup in /tmp/ before exploration
- **EnterPlanMode** - Create implementation plan
- **ExitPlanMode** - Complete planning phase
- **git** - Permanent version control for plans

---

## Prompt Template

You are executing the `/restore-plan` command.

---

### Execution Steps

**Step 1: List Available Backups**

Find backups:
```bash
ls -t /tmp/plan-backup-*.md 2>/dev/null
```

If no backups: Show error, suggest /copy-plan or git

**Step 2: Show Backup Previews**

For each backup:
- Show path, size, creation time
- Show first 10 lines (preview)
- Number each backup (1, 2, 3, ...)

**Step 3: Prompt User Selection**

Ask user to select backup:
- Show numbered list
- Allow 'cancel' to abort
- Validate input (1-N or cancel)

**Step 4: Confirm Overwrite**

⚠️ Warning:
- Show current plan will be overwritten
- Show sizes (current vs backup)
- Require explicit confirmation (yes/no)

**Step 5: Create Safety Backup**

Before restore:
```bash
SAFETY="/tmp/plan-before-restore-$(date +%Y-%m-%d-%H%M%S).md"
cp .claude/plans/current-plan.md "$SAFETY"
```

Confirm safety backup created

**Step 6: Restore Selected Backup**

Execute restore:
```bash
cp {selected_backup} .claude/plans/current-plan.md
```

Verify restore:
```bash
md5sum {selected_backup} .claude/plans/current-plan.md
```

**Step 7: Confirm to User**

Show:
- ✅ Success message
- Restored from (backup path)
- Safety backup location (for undo)
- Next steps (continue, compare, undo)

---

### Output

Use the output format above, including:
- Available backups (with previews)
- Current plan (preview)
- Restore confirmation
- Restore result (success/failure)
- What's next (continue, compare, undo)
