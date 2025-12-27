---
title: /wt-list command - list active worktrees
focus: workflow
date: 2025-12-24
status: approved
---

# Specification: /wt-list Command

## Purpose

List all active git worktrees with their branch names, paths, and activity metadata. Provides visibility into parallel agent workflows and helps identify stale worktrees for cleanup.

## Use Case

**Problem**: When running multiple parallel agents across different worktrees, hard to track:
- Which worktrees exist
- What task each worktree is for
- Which worktrees are actively being worked on
- Which worktrees are stale and can be cleaned up

**Solution**: Single command that shows all worktrees with meaningful metadata

**Workflow**:
```bash
# Check what worktrees exist
/wt-list

# Output:
✅ Active Worktrees (3)

Main Worktree:
  Path:      /home/anak/dev/dr-daily-report_telegram
  Branch:    dev
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:25:00 (5 minutes ago)

Worktree: investigate-lambda-timeout
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout
  Branch:    wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:30:52 (just now)
  Status:    🟢 Active (working on bug investigation)

Worktree: rest-api-for-backtester
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-rest-api-for-backtester
  Branch:    wt-2025-12-24-143117-rest-api-for-backtester-b8d1
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 13:45:00 (45 minutes ago)
  Status:    🟡 Idle (no activity in last 30 min)

Worktree: refactor-workflow-layer
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-refactor-workflow-layer
  Branch:    wt-2025-12-24-120000-refactor-workflow-layer-c9e3
  Commit:    1dd1923 (fix(ci): Fix Lambda smoke test payload format)
  Modified:  2025-12-23 18:00:00 (20 hours ago)
  Status:    🔴 Stale (no activity in > 12 hours)

Cleanup Suggestions:
  - Stale worktree detected: refactor-workflow-layer
    → Review: cd /home/anak/dev/dr-daily-report_telegram-wt-refactor-workflow-layer
    → Merge:  /wt-merge "refactor-workflow-layer"
    → Remove: /wt-remove "refactor-workflow-layer"
```

---

## Command Interface

### Signature
```bash
/wt-list
```

### Arguments
None (shows all worktrees)

### Optional Flags (Future Enhancement)
```bash
/wt-list --stale          # Only show stale worktrees (> 12 hours)
/wt-list --active         # Only show active worktrees (< 30 min)
/wt-list --sort=modified  # Sort by last modified (default: creation time)
```

*Note: Initial implementation has no flags, shows all worktrees*

---

## Behavior

### 1. Git Worktree Query

**Command**: `git worktree list --porcelain`

**Output Format**:
```
worktree /home/anak/dev/dr-daily-report_telegram
HEAD 6630d4c1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
branch refs/heads/dev

worktree /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout
HEAD 6630d4c1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
branch refs/heads/wt-2025-12-24-143052-investigate-lambda-timeout-a3f2

worktree /home/anak/dev/dr-daily-report_telegram-wt-rest-api-for-backtester
HEAD 6630d4c1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
branch refs/heads/wt-2025-12-24-143117-rest-api-for-backtester-b8d1
```

**Parsing Algorithm**:
```bash
git worktree list --porcelain | awk '
  /^worktree / { path = $2 }
  /^HEAD / { commit = $2 }
  /^branch / { branch = $2; sub("refs/heads/", "", branch) }
  /^$/ {
    if (path != "") {
      print path "|" branch "|" commit
      path = ""; branch = ""; commit = ""
    }
  }
  END {
    if (path != "") {
      print path "|" branch "|" commit
    }
  }
'
```

---

### 2. Last Modified Time Detection

**Strategy**: Check last git operation timestamp in each worktree

**Implementation**:
```bash
# For each worktree path
LAST_MODIFIED=$(git -C "$WORKTREE_PATH" log -1 --format="%at" 2>/dev/null)

# If no commits in this worktree, fall back to directory mtime
if [[ -z "$LAST_MODIFIED" ]]; then
  LAST_MODIFIED=$(stat -c %Y "$WORKTREE_PATH" 2>/dev/null || stat -f %m "$WORKTREE_PATH")
fi

# Convert to human-readable
LAST_MODIFIED_DATE=$(date -d "@$LAST_MODIFIED" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -r "$LAST_MODIFIED" "+%Y-%m-%d %H:%M:%S")

# Calculate relative time
NOW=$(date +%s)
DIFF=$((NOW - LAST_MODIFIED))
MINUTES=$((DIFF / 60))
HOURS=$((DIFF / 3600))
DAYS=$((DIFF / 86400))

if [[ $MINUTES -lt 1 ]]; then
  RELATIVE="just now"
elif [[ $MINUTES -lt 60 ]]; then
  RELATIVE="$MINUTES minutes ago"
elif [[ $HOURS -lt 24 ]]; then
  RELATIVE="$HOURS hours ago"
else
  RELATIVE="$DAYS days ago"
fi
```

---

### 3. Activity Status Classification

**Thresholds**:
- 🟢 **Active**: Last modified < 30 minutes ago
- 🟡 **Idle**: Last modified 30 min - 12 hours ago
- 🔴 **Stale**: Last modified > 12 hours ago

**Logic**:
```bash
MINUTES=$((DIFF / 60))
HOURS=$((DIFF / 3600))

if [[ $MINUTES -lt 30 ]]; then
  STATUS="🟢 Active"
  STATUS_MSG="working on task"
elif [[ $HOURS -lt 12 ]]; then
  STATUS="🟡 Idle"
  STATUS_MSG="no activity in last ${MINUTES} min"
else
  STATUS="🔴 Stale"
  STATUS_MSG="no activity in > 12 hours"
fi
```

**Rationale**:
- **30 min**: Typical agent task duration (bug hunt, spec creation, refactoring)
- **12 hours**: Work day boundary (overnight = likely abandoned)

---

### 4. Slug Extraction from Branch Name

**Pattern**: `wt-{date}-{time}-{slug}-{random}` → extract `{slug}`

**Algorithm**:
```bash
# Branch: wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
# Want:   investigate-lambda-timeout

# Remove prefix (wt-YYYY-MM-DD-HHMMSS-)
BRANCH_TAIL=$(echo "$BRANCH" | sed 's/^wt-[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-[0-9]\{6\}-//')

# Remove suffix (-XXXX random)
SLUG=$(echo "$BRANCH_TAIL" | sed 's/-[a-f0-9]\{4\}$//')

# Result: investigate-lambda-timeout
```

**Edge Case - Main Worktree**:
```bash
# Main worktree has no wt- prefix
if [[ "$BRANCH" != wt-* ]]; then
  SLUG="main-worktree"
fi
```

---

### 5. Commit Message Truncation

**Implementation**:
```bash
# Get commit message (first line only)
COMMIT_MSG=$(git -C "$WORKTREE_PATH" log -1 --format="%s" "$COMMIT_SHA" 2>/dev/null)

# Truncate to 60 characters
if [[ ${#COMMIT_MSG} -gt 60 ]]; then
  COMMIT_MSG="${COMMIT_MSG:0:57}..."
fi

# Output: 6630d4c (fix(ci): Use fileb:// instead of file://)
```

---

## Output Format

### Standard Output (3 Worktrees)

```
✅ Active Worktrees (3)

Main Worktree:
  Path:      /home/anak/dev/dr-daily-report_telegram
  Branch:    dev
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:25:00 (5 minutes ago)

Worktree: investigate-lambda-timeout
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout
  Branch:    wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:30:52 (just now)
  Status:    🟢 Active (working on task)

Worktree: rest-api-for-backtester
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-rest-api-for-backtester
  Branch:    wt-2025-12-24-143117-rest-api-for-backtester-b8d1
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 13:45:00 (45 minutes ago)
  Status:    🟡 Idle (no activity in last 30 min)

Cleanup Suggestions:
  None (all worktrees recently active)
```

### Output with Stale Worktrees

```
✅ Active Worktrees (2)

Main Worktree:
  Path:      /home/anak/dev/dr-daily-report_telegram
  Branch:    dev
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:25:00 (5 minutes ago)

Worktree: refactor-workflow-layer
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-refactor-workflow-layer
  Branch:    wt-2025-12-24-120000-refactor-workflow-layer-c9e3
  Commit:    1dd1923 (fix(ci): Fix Lambda smoke test payload format)
  Modified:  2025-12-23 18:00:00 (20 hours ago)
  Status:    🔴 Stale (no activity in > 12 hours)

Cleanup Suggestions:
  ⚠️  Stale worktree detected: refactor-workflow-layer
      → Review work:  cd /home/anak/dev/dr-daily-report_telegram-wt-refactor-workflow-layer
      → Merge:        /wt-merge "refactor-workflow-layer"
      → Remove:       /wt-remove "refactor-workflow-layer"
      → Discard work: /wt-remove "refactor-workflow-layer" (without merge)
```

### Output (Only Main Worktree)

```
✅ Active Worktrees (1)

Main Worktree:
  Path:      /home/anak/dev/dr-daily-report_telegram
  Branch:    dev
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Modified:  2025-12-24 14:25:00 (5 minutes ago)

No additional worktrees.

Hint: Create a new worktree for parallel work:
  /wt-spin-off "task description"
```

### Output (No Worktrees - Error State)

```
❌ No worktrees found

This should never happen (main worktree always exists).
Possible causes:
  - Not in a git repository
  - Git worktree metadata corrupted

Debug:
  git worktree list
```

---

## Edge Cases

### 1. Detached HEAD Worktree
**Scenario**: Worktree is in detached HEAD state (not on a branch)

**Git Output**:
```
worktree /home/anak/dev/dr-daily-report_telegram-wt-test
HEAD 6630d4c1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
detached
```

**Handling**:
```bash
if [[ "$BRANCH" == "detached" ]] || [[ -z "$BRANCH" ]]; then
  BRANCH="(detached HEAD)"
  SLUG="detached-head"
  STATUS="⚠️ Detached HEAD (unusual state)"
fi
```

**Output**:
```
Worktree: detached-head
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-test
  Branch:    (detached HEAD)
  Commit:    6630d4c (fix(ci): Use fileb:// instead of file://)
  Status:    ⚠️ Detached HEAD (unusual state)
```

---

### 2. Worktree Directory Deleted (Broken Reference)
**Scenario**: Worktree directory was deleted manually (not via `git worktree remove`)

**Git Behavior**: `git worktree list` still shows it, but path doesn't exist

**Detection**:
```bash
if [[ ! -d "$WORKTREE_PATH" ]]; then
  STATUS="❌ Missing directory (broken reference)"
  MODIFIED="N/A"
  RELATIVE="directory deleted"
fi
```

**Output**:
```
Worktree: broken-worktree
  Path:      /home/anak/dev/dr-daily-report_telegram-wt-deleted (MISSING)
  Branch:    wt-2025-12-24-100000-broken-worktree-x1y2
  Commit:    abc1234 (old commit)
  Status:    ❌ Missing directory (broken reference)

Cleanup Suggestions:
  ⚠️  Broken worktree reference: broken-worktree
      → Remove stale reference: git worktree prune
```

---

### 3. Very Long Worktree Path
**Scenario**: Path exceeds terminal width

**Handling**: Truncate with ellipsis
```bash
MAX_PATH_LEN=70

if [[ ${#WORKTREE_PATH} -gt $MAX_PATH_LEN ]]; then
  # Keep start and end
  START="${WORKTREE_PATH:0:30}"
  END="${WORKTREE_PATH: -37}"
  DISPLAY_PATH="${START}...${END}"
else
  DISPLAY_PATH="$WORKTREE_PATH"
fi
```

**Output**:
```
Worktree: very-long-task-name
  Path:      /home/anak/dev/dr-daily-r.../telegram-wt-very-long-task-name
  Branch:    wt-2025-12-24-143052-very-long-task-name-a3f2
```

---

### 4. Non-wt Branch in Worktree
**Scenario**: User manually created worktree with non-standard branch name

**Example**:
```bash
git worktree add ../custom-feature feature-X
# Branch: feature-X (not wt-* pattern)
```

**Handling**: Show as-is, don't try to extract slug
```bash
if [[ "$BRANCH" != wt-* ]]; then
  # Use branch name as slug
  SLUG="$BRANCH"
fi
```

**Output**:
```
Worktree: feature-X
  Path:      /home/anak/dev/custom-feature
  Branch:    feature-X
  Commit:    abc1234 (Some custom commit)
  Modified:  2025-12-24 10:00:00 (4 hours ago)
  Status:    🟡 Idle (no activity in last 240 min)
```

---

## Cleanup Suggestions Logic

### When to Suggest Cleanup

**Criteria**: Any worktree with 🔴 Stale status (> 12 hours)

**Suggestion Format**:
```bash
# For each stale worktree
echo "  ⚠️  Stale worktree detected: $SLUG"
echo "      → Review work:  cd $WORKTREE_PATH"
echo "      → Merge:        /wt-merge \"$SLUG\""
echo "      → Remove:       /wt-remove \"$SLUG\""
echo "      → Discard work: /wt-remove \"$SLUG\" (without merge)"
echo ""
```

**No Stale Worktrees**:
```
Cleanup Suggestions:
  None (all worktrees recently active)
```

---

## Performance Considerations

### Scalability

**Assumption**: Typically 1-10 worktrees (not 100+)

**Performance**:
- `git worktree list --porcelain`: O(N) where N = number of worktrees
- Per-worktree `git log -1`: O(1) per worktree
- Total: O(N), acceptable for N < 20

**If N > 20** (unlikely):
```bash
# Warning if many worktrees
WORKTREE_COUNT=$(git worktree list | wc -l)

if [[ $WORKTREE_COUNT -gt 20 ]]; then
  echo "⚠️  Warning: $WORKTREE_COUNT worktrees detected (unusual)"
  echo "   Consider cleaning up stale worktrees to improve performance"
  echo ""
fi
```

---

## Implementation Checklist

- [ ] Command file: `.claude/commands/wt-list.md`
- [ ] Parse `git worktree list --porcelain` output
- [ ] Extract branch names and commit SHAs
- [ ] Detect last modified timestamp (git log or directory mtime)
- [ ] Calculate relative time (minutes/hours/days ago)
- [ ] Classify activity status (Active/Idle/Stale)
- [ ] Extract slug from branch name (handle main worktree)
- [ ] Truncate commit messages to 60 chars
- [ ] Format output with aligned columns
- [ ] Generate cleanup suggestions for stale worktrees
- [ ] Handle edge cases: detached HEAD, missing directories, non-wt branches
- [ ] Performance warning if > 20 worktrees

---

## Success Criteria

**Command succeeds when**:
1. ✅ Lists all worktrees (main + additional)
2. ✅ Shows accurate last modified times
3. ✅ Correctly classifies activity status
4. ✅ Extracts readable slugs from branch names
5. ✅ Provides actionable cleanup suggestions
6. ✅ Handles edge cases gracefully (detached HEAD, missing dirs)

**User can answer these questions**:
- How many worktrees do I have?
- Which worktree is for which task?
- Which worktrees are actively being worked on?
- Which worktrees should I clean up?
- What commands do I run to merge/remove a worktree?

---

## Related Commands

- `/wt-spin-off "description"` - Create new worktree
- `/wt-merge "slug"` - Merge worktree branch back to dev
- `/wt-remove "slug"` - Remove worktree directory

---

## See Also

- [What-If: /spin-off-worktree for parallel workflows](../what-if/2025-12-24-spin-off-worktree-command-for-parallel-agent-workflows.md)
- [What-If: wt-* prefix naming convention](../what-if/2025-12-24-worktree-command-naming-wt-prefix-vs-worktree-suffix.md)
- [Specification: /wt-spin-off command](2025-12-24-wt-spin-off-command-create-branch-and-worktree.md)
- Git worktree documentation: `git help worktree`
