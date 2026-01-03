---
name: copy-plan
description: Copy current plan to /tmp/ for safe exploration without interfering with working plan
accepts_args: false
---

# Copy-Plan Command

**Purpose**: Backup current plan to `/tmp/` before exploration

**Core Principle**: "Explore freely without losing work" - isolate exploration from working plan

**When to use**:
- Before exploring alternative approaches (don't want to overwrite current plan)
- Before major plan changes (want to preserve original)
- When uncertain about direction (easy to revert)
- Testing plan modifications (keep backup)

**When NOT to use**:
- No active plan file (nothing to copy)
- Plan already committed to git (version control is backup)
- Simple plan edits (no risk of loss)

---

## Quick Reference

```bash
# Working on implementation plan, want to explore alternative
/copy-plan
→ Plan copied to: /tmp/plan-backup-2026-01-03-110000.md
→ You can now explore alternatives
→ Original plan preserved in /tmp/

# After exploration: Keep or restore?
# Option A: Keep exploration (current plan file is new approach)
git add .claude/plans/current-plan.md
git commit -m "Use alternative approach"

# Option B: Restore original
/restore-plan
→ Select backup to restore
→ Original plan restored
```

---

## Execution Flow

### Step 1: Identify Current Plan

**Find most recent plan file**:
```bash
# Search .claude/plans/ for plan files
ls -t .claude/plans/*.md 2>/dev/null | head -1
```

**Possible locations**:
- `.claude/plans/current-plan.md` (standard location)
- `.claude/plans/YYYY-MM-DD-*.md` (dated plans)
- Plan mode working file (if in plan mode)

**If no plan found**:
```
No active plan file found.

Checked:
- .claude/plans/current-plan.md
- .claude/plans/*.md

Create a plan first:
→ Use EnterPlanMode to start planning
→ Then use /copy-plan to backup
```

---

### Step 2: Generate Backup Filename

**Format**: `/tmp/plan-backup-YYYY-MM-DD-HHmmss.md`

```bash
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP="/tmp/plan-backup-${TIMESTAMP}.md"
```

**Example**: `/tmp/plan-backup-2026-01-03-110000.md`

**Why timestamped**:
- Multiple backups don't overwrite each other
- Can restore from specific point in time
- Clear chronological order

---

### Step 3: Copy Plan File

**Execute copy**:
```bash
cp .claude/plans/current-plan.md "$BACKUP"
```

**Verify copy success**:
```bash
# Check file exists
ls -lh "$BACKUP"

# Compare checksums (ensure identical)
md5sum .claude/plans/current-plan.md "$BACKUP"
```

**If copy fails**:
```
Error: Failed to copy plan file

Reason: {error message}

Manual backup:
cp .claude/plans/current-plan.md /tmp/plan-backup-manual.md
```

---

### Step 4: Confirm to User

**Success message**:
```
✅ Plan copied successfully

Original: .claude/plans/current-plan.md
Backup: /tmp/plan-backup-2026-01-03-110000.md
Size: 15 KB

You can now:
- Explore alternative approaches (EnterPlanMode)
- Modify current plan without losing original
- Restore backup with /restore-plan if needed

Backup location: /tmp/plan-backup-2026-01-03-110000.md
```

**Include instructions**:
- How to explore (EnterPlanMode will overwrite current plan)
- How to restore (use `/restore-plan`)
- Where backup is located (for manual operations)

---

## Output Format

```markdown
# Plan Backup

**Date**: {YYYY-MM-DD HH:MM:SS}
**Action**: Copy plan to /tmp/

---

## Backup Details

**Original plan**: {path to original}
**Backup location**: {path to backup}
**File size**: {size in KB/MB}
**Checksum**: {MD5 hash for verification}

---

## What's Next

You can now:

**Option 1: Explore alternative approach**
```bash
EnterPlanMode
# This will create new plan, original preserved in backup
```

**Option 2: Modify current plan**
```
# Edit .claude/plans/current-plan.md
# Original preserved in backup if you need to revert
```

**Option 3: Restore from backup** (if needed later)
```bash
/restore-plan
# Select backup to restore
```

---

## Backup Location

**Path**: {/tmp/plan-backup-YYYY-MM-DD-HHmmss.md}

**Manual operations**:
```bash
# View backup
cat /tmp/plan-backup-2026-01-03-110000.md

# Compare with current
diff /tmp/plan-backup-2026-01-03-110000.md .claude/plans/current-plan.md

# Manual restore (if /restore-plan not available)
cp /tmp/plan-backup-2026-01-03-110000.md .claude/plans/current-plan.md
```
```

---

## Examples

### Example 1: Before Exploring Alternative

```bash
# Working on implementation plan
EnterPlanMode  # Created .claude/plans/current-plan.md

# Want to explore alternative approach without losing current work
/copy-plan

Output:
✅ Plan copied successfully

Backup: /tmp/plan-backup-2026-01-03-110000.md

You can now explore alternatives. Original plan preserved.

# Explore alternative
EnterPlanMode
# ... creates new plan ...

# Decision: Keep alternative (current plan is new approach)
git add .claude/plans/current-plan.md
git commit -m "Use alternative approach"

# Or: Restore original
/restore-plan
→ Select: /tmp/plan-backup-2026-01-03-110000.md
→ Restored original plan
```

---

### Example 2: Before Major Plan Changes

```bash
# Have detailed implementation plan, want to try different organization
/copy-plan

Output:
✅ Plan copied to /tmp/plan-backup-2026-01-03-111500.md

# Make major changes to .claude/plans/current-plan.md
# ... edit, reorganize ...

# Compare changes
diff /tmp/plan-backup-2026-01-03-111500.md .claude/plans/current-plan.md

# Decision: Revert changes (didn't work out)
/restore-plan
→ Restored original structure
```

---

### Example 3: Multiple Backups

```bash
# Iteration 1: Backup before first exploration
/copy-plan
→ /tmp/plan-backup-2026-01-03-110000.md

# Explore approach 1
# ...

# Iteration 2: Backup before second exploration
/copy-plan
→ /tmp/plan-backup-2026-01-03-113000.md

# Explore approach 2
# ...

# Decision: Want approach from first iteration
/restore-plan
→ Select: /tmp/plan-backup-2026-01-03-110000.md
→ Restored first iteration
```

---

## Workflow Integration

**Before exploration**:
```
Working plan → /copy-plan → Backup in /tmp/
```

**During exploration**:
```
EnterPlanMode → New plan (overwrites current)
```

**After exploration**:
```
Option 1: Keep new plan (git commit)
Option 2: Restore backup (/restore-plan)
```

**Git workflow**:
```bash
# Backup before exploration
/copy-plan

# Explore
EnterPlanMode

# Compare approaches
diff /tmp/plan-backup-*.md .claude/plans/current-plan.md

# Commit chosen approach
git add .claude/plans/current-plan.md
git commit -m "Choose [new/original] approach"
```

---

## Best Practices

### Do
- **Backup before major changes** (easy to revert)
- **Use timestamped backups** (don't overwrite previous)
- **Compare before deciding** (diff backup vs current)
- **Clean up old backups** (rm /tmp/plan-backup-*.md when done)

### Don't
- **Don't skip backup when exploring** (prevents loss of work)
- **Don't use /tmp/ for long-term storage** (/tmp/ may be cleared)
- **Don't forget backup location** (write down if needed)
- **Don't delete backup until committed** (might need to restore)

---

## Integration with Other Commands

**`/copy-plan` → EnterPlanMode**:
- Backup current plan
- Explore alternative approach
- EnterPlanMode creates new plan (safe because backup exists)

**`/copy-plan` → `/restore-plan`**:
- Create backup
- Make changes
- Restore if changes didn't work out

**`/copy-plan` → git**:
- Backup before exploration
- Explore alternatives
- Commit chosen approach (backup no longer needed)

---

## See Also

- **`/restore-plan`** - Restore plan from /tmp/ backup
- **EnterPlanMode** - Create implementation plan (may overwrite current)
- **ExitPlanMode** - Complete planning phase

---

## Prompt Template

You are executing the `/copy-plan` command.

---

### Execution Steps

**Step 1: Identify Current Plan**

Find most recent plan file:
```bash
ls -t .claude/plans/*.md 2>/dev/null | head -1
```

If no plan found: Show error, suggest creating plan first

**Step 2: Generate Backup Filename**

Create timestamped filename:
```bash
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP="/tmp/plan-backup-${TIMESTAMP}.md"
```

**Step 3: Copy Plan File**

Execute copy:
```bash
cp {plan_file} "$BACKUP"
```

Verify copy success:
```bash
md5sum {plan_file} "$BACKUP"
```

**Step 4: Confirm to User**

Show:
- ✅ Success message
- Original plan location
- Backup location
- File size
- Next steps (explore, modify, restore)

---

### Output

Use the output format above, including:
- Backup details (location, size, checksum)
- What's next (exploration options)
- Backup location (for manual operations)
