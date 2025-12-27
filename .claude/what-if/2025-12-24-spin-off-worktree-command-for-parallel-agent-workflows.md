---
title: /spin-off-worktree command for parallel agent workflows
date: 2025-12-24
assumption_type: addition
status: analyzed
recommendation: conditional
---

# What-If Analysis: /spin-off-worktree Command

## Assumption

**What if we had a `/spin-off-worktree` command that deterministically spins off current branch into new branch and creates worktree for parallel agent work?**

**Context**: Planning to run many agents doing different tasks for different workflows in the same repo

**Proposed command**:
```bash
/spin-off-worktree "feature description"
# → Creates new branch from current
# → Creates git worktree in separate directory
# → Each agent works in isolated worktree
# → No file conflicts between parallel agents
```

---

## Current Reality

**Current workflow**: Single working directory
- **Branch**: `dev` (primary development branch)
- **Working directory**: `/home/anak/dev/dr-daily-report_telegram`
- **Agent model**: One agent at a time in same directory
- **Parallelism**: None (sequential agent execution)

**Current limitations**:
- Cannot run multiple agents simultaneously (file conflicts)
- Switching tasks requires committing or stashing changes
- Context switching overhead (mental + git operations)
- No isolation between parallel workstreams

**Sources**:
- Git status shows single working tree
- No worktree infrastructure currently exists
- Agent execution is sequential by design

---

## Under New Assumption: /spin-off-worktree Command

### What Changes Immediately

**Git structure**:
```
/home/anak/dev/dr-daily-report_telegram/           # Main worktree (dev branch)
/home/anak/dev/dr-daily-report_telegram-wt-1/      # Worktree 1 (feature-A branch)
/home/anak/dev/dr-daily-report_telegram-wt-2/      # Worktree 2 (feature-B branch)
/home/anak/dev/dr-daily-report_telegram-wt-3/      # Worktree 3 (bug-fix-C branch)
```

**Agent workflow**:
```bash
# Terminal 1: Agent working on feature A
cd /home/.../dr-daily-report_telegram-wt-1
/bug-hunt "Lambda timeout"

# Terminal 2: Agent working on feature B (parallel)
cd /home/.../dr-daily-report_telegram-wt-2
/specify "REST API for backtester"

# Terminal 3: Agent working on bug fix C (parallel)
cd /home/.../dr-daily-report_telegram-wt-3
/refactor src/workflow/
```

**Command behavior**:
```bash
/spin-off-worktree "investigate lambda timeout"
# 1. Generate deterministic branch name: wt-2025-12-24-143052-investigate-lambda-timeout
# 2. Create branch from current HEAD
# 3. Create worktree: git worktree add ../dr-daily-report_telegram-wt-investigate-lambda-timeout wt-...
# 4. Output path to worktree
# 5. Agent continues work in new worktree
```

---

### Cascading Effects

**Level 1 (Direct)**:
- ✅ **Parallel agent execution**: Multiple agents work simultaneously
- ✅ **File isolation**: No conflicts between concurrent edits
- ✅ **Independent Claude Code sessions**: Each worktree has own .claude/ state
- ⚠️ **Disk usage**: N worktrees = N copies of working directory (~500MB each)

**Level 2 (Workflow)**:
- ✅ **Task parallelism**: `/bug-hunt` + `/specify` + `/refactor` run concurrently
- ✅ **Context preservation**: Each worktree maintains its own uncommitted changes
- ⚠️ **Branch proliferation**: Many short-lived branches (cleanup needed)
- ⚠️ **Worktree lifecycle**: Need to remove worktrees when done

**Level 3 (Mental model)**:
- ✅ **Spatial organization**: Different tasks = different directories (clear boundaries)
- ⚠️ **Cognitive overhead**: Track which worktree has which task
- ⚠️ **Merge coordination**: Multiple branches need merging back to dev

---

### Components Affected

**Git operations**:
- `git worktree add` - Creates worktree
- `git worktree list` - Shows all worktrees
- `git worktree remove` - Cleans up when done
- `.git/worktrees/` - Stores worktree metadata

**File system**:
- Parent directory (`/home/anak/dev/`) - Holds multiple worktree directories
- Each worktree - Independent working directory (~500MB)
- Shared `.git` - All worktrees point to same Git database

**Claude Code**:
- Each worktree has independent `.claude/` state
- Observations, journals, specifications isolated per worktree
- Commands execute in worktree-specific context

**CI/CD**:
- GitHub Actions triggered per branch (parallel CI runs)
- Each worktree branch can deploy independently
- Potential for resource contention (parallel deploys)

---

## What Breaks

### Critical Issues

**1. Shared State Confusion**
- **Problem**: `.claude/` directories are independent per worktree
- **Impact**: Observations in worktree-1 invisible to worktree-2
- **Example**: `/observe failure` in wt-1, `/bug-hunt` in wt-2 can't see it
- **Severity**: Medium (worktrees should be independent anyway)
- **Workaround**: Share observations via git (commit and pull)

**2. Branch Naming Collisions**
- **Problem**: If two agents run `/spin-off-worktree` simultaneously with same description
- **Impact**: Git refuses duplicate branch names
- **Example**: Two agents both try to create `wt-2025-12-24-fix-timeout`
- **Severity**: Low (timestamp in name prevents most collisions)
- **Workaround**: Add random suffix or agent ID

**3. Disk Space**
- **Problem**: Each worktree ~500MB, 10 worktrees = 5GB
- **Impact**: Disk space exhaustion on constrained systems
- **Example**: Laptop with limited SSD space
- **Severity**: Medium (depends on number of parallel agents)
- **Workaround**: Limit concurrent worktrees, cleanup policy

### Degraded Functionality

**1. Navigation Overhead**
- **Before**: All work in one directory
- **After**: Must navigate between worktree directories
- **Impact**: Acceptable (spatial separation is the goal)

**2. Cleanup Complexity**
- **Before**: Just switch branches
- **After**: Must remove worktrees, delete branches
- **Impact**: Acceptable (can automate cleanup)

---

## What Improves

### Performance Gains

**1. True Parallelism**
- **Metric**: Agent throughput
- **Magnitude**: N agents = N× tasks completed simultaneously
- **Value**: **High** (main benefit)
- **Example**: `/bug-hunt` + `/specify` + `/refactor` run in parallel

**2. No Context Switching**
- **Metric**: Time wasted on git stash/commit/checkout
- **Magnitude**: Eliminates ~2-5 min per task switch
- **Value**: **Medium** (saves time, reduces friction)

**3. Independent Failure Domains**
- **Metric**: Blast radius of broken code
- **Magnitude**: Bug in worktree-1 doesn't affect worktree-2
- **Value**: **High** (safety for experiments)

### Workflow Improvements

**1. Spatial Task Organization**
- **Before**: Mental tracking of "what's uncommitted"
- **After**: Task A = directory-A, Task B = directory-B
- **Benefit**: Clear physical boundaries for different workstreams

**2. Experiment Safety**
- **Before**: Risky to try radical changes (might break main work)
- **After**: Spin off worktree, experiment freely, discard if failed
- **Benefit**: Encourages exploration without fear

**3. Agent Specialization**
- **Before**: One agent does everything sequentially
- **After**: Agent-1 = bug hunting, Agent-2 = design, Agent-3 = refactoring
- **Benefit**: Parallel execution of different command types

---

## Insights Revealed

### Assumptions Exposed

**1. Single-threaded development assumption**
- **Hidden assumption**: "One task at a time in one directory"
- **Evidence**: Current workflow is sequential
- **Criticality**: High (limits throughput with multiple agents)
- **Revealed**: Git worktrees enable true parallelism

**2. Shared .claude/ state assumption**
- **Hidden assumption**: "All agents share observations/journals"
- **Reality**: Worktrees have independent `.claude/` directories
- **Criticality**: Medium (design decision: share vs isolate)
- **Implication**: Need strategy for cross-worktree knowledge sharing

### Trade-offs Clarified

**1. Parallelism vs Coordination**
- **Original choice**: Sequential execution (simple coordination)
- **Alternative**: Parallel execution (complex coordination)
- **Trade-off**: Speed vs Complexity
- **Validated**: Depends on use case (many small tasks → parallel wins)

**2. Disk Space vs Throughput**
- **Original choice**: One worktree (minimal disk usage)
- **Alternative**: N worktrees (N× disk usage)
- **Trade-off**: Resources vs Speed
- **Validated**: Acceptable on modern systems (disk is cheap, time is not)

### Boundary Conditions

**1. Maximum Concurrent Worktrees**
- **Threshold**: Disk space / 500MB per worktree
- **Example**: 50GB available → max 100 worktrees (absurd, but possible)
- **Practical limit**: 3-10 concurrent worktrees (diminishing returns)
- **Current margin**: Infinite (not using worktrees yet)

**2. Agent Coordination Overhead**
- **Threshold**: N agents = O(N²) merge conflicts if uncoordinated
- **Example**: 10 agents editing same file → merge hell
- **Mitigation**: Assign non-overlapping file sets per agent
- **Safety factor**: High (different workflows touch different files)

### Design Rationale

**Why `/spin-off-worktree` makes sense**:
1. **Use case**: Multiple agents working on different tasks simultaneously
2. **Git feature**: Worktrees are designed for exactly this (parallel work on different branches)
3. **Isolation**: Each agent needs independent workspace
4. **Determinism**: Branch naming must be predictable (timestamp + description)

**Why it might NOT be needed**:
1. **Sequential is simpler**: If tasks are quick, sequential may suffice
2. **Coordination cost**: Merging N branches back to dev has overhead
3. **Overkill for small repo**: If only 1-2 tasks at a time, not worth complexity

---

## Recommendation

### Should We Add This Command?

**Decision**: ⚠️ **CONDITIONALLY YES**

**Rationale**:
- ✅ **Strong use case**: Multiple agents doing different tasks in parallel
- ✅ **Git worktrees are mature**: Well-supported, designed for this
- ✅ **Enables true parallelism**: N agents = N× throughput
- ⚠️ **Adds complexity**: Branch proliferation, cleanup overhead
- ⚠️ **Needs lifecycle management**: Automatic worktree cleanup required

**Conditions for YES**:
1. **Cleanup automation**: Must auto-remove worktrees after task completion
2. **Branch naming convention**: Deterministic, collision-resistant
3. **Disk space check**: Warn if insufficient space for new worktree
4. **Documentation**: Clear guide on when to use vs sequential workflow

---

### Action Items

**Implement if conditions met**:
- [ ] Design cleanup mechanism (`/cleanup-worktree` or auto-detect when done)
- [ ] Implement deterministic branch naming (timestamp + slug + random suffix)
- [ ] Add disk space check before creating worktree
- [ ] Document use cases (when to use worktrees vs sequential)
- [ ] Test with 3-5 concurrent agents
- [ ] Measure actual throughput improvement

**Command design**:
```bash
# Create worktree
/spin-off-worktree "investigate lambda timeout"
# → Branch: wt-2025-12-24-143052-investigate-lambda-timeout-a3f2
# → Worktree: /home/anak/dev/dr-daily-report_telegram-wt-investigate-lambda-timeout
# → Output: "Created worktree at {path}, branch {name}"

# List active worktrees
/list-worktrees
# → Shows all worktrees with branch names, paths, last activity

# Cleanup worktree (when done)
/cleanup-worktree "investigate-lambda-timeout"
# → Merges branch to dev (if requested)
# → Removes worktree directory
# → Deletes branch (if merged)
```

---

### Follow-Up

**Specify the command**:
```bash
/specify "/spin-off-worktree command for parallel agent workflows"
```

**Questions to answer**:
- How to handle `.claude/` state across worktrees? (Share via git? Independent?)
- When to auto-cleanup? (After merge? After N days? Manual?)
- How to prevent branch name collisions? (Timestamp sufficient? Add UUID?)
- How to coordinate merges? (Sequential merge queue? YOLO merge?)

**Validate assumptions**:
```bash
/validate "Git worktrees work well with 5+ concurrent instances"
/validate "Disk space is not a bottleneck for 10 worktrees"
```

**Journal the decision**:
```bash
/journal architecture "/spin-off-worktree for parallel agent execution"
```

---

## Alternative Approaches Considered

### Alternative 1: Docker Containers Per Agent
**Idea**: Each agent runs in separate container with own repo clone

**Pros**:
- Complete isolation (filesystem, network, processes)
- Easy cleanup (just remove container)

**Cons**:
- Heavier than worktrees (full OS overhead)
- Slower setup (image pull, container start)
- More complex infrastructure

**Verdict**: Worktrees are lighter, faster, simpler

---

### Alternative 2: Separate Repo Clones
**Idea**: Clone repo N times, each agent works in separate clone

**Pros**:
- Complete independence (no shared .git)
- Simple mental model (just separate directories)

**Cons**:
- Massive disk usage (N full clones)
- Fetch overhead (N separate fetches from remote)
- Not using Git's built-in worktree feature

**Verdict**: Worktrees use shared .git (efficient), designed for this

---

### Alternative 3: Branch Switching (Current)
**Idea**: Stay with current sequential workflow, switch branches as needed

**Pros**:
- Simple (no new infrastructure)
- Minimal disk usage (one worktree)

**Cons**:
- No parallelism (defeats purpose of multiple agents)
- Context switching overhead (stash/commit/checkout)

**Verdict**: Doesn't solve parallel execution problem

---

## Conclusion

**The `/spin-off-worktree` command is a good idea IF**:
1. You actually plan to run multiple agents in parallel (3+ concurrent)
2. Tasks are independent (different files, different workflows)
3. You implement lifecycle management (automatic cleanup)
4. Disk space is not constrained (500MB × N worktrees)

**Recommend**:
- ✅ Implement `/spin-off-worktree` with cleanup automation
- ✅ Add `/list-worktrees` to track active worktrees
- ✅ Add `/cleanup-worktree` or auto-detect completion
- ✅ Document when to use (parallel work) vs not (sequential work)
- ⚠️ Start with 3-5 concurrent agents, measure benefits
- ⚠️ Add disk space check (warn if < 2GB available)

**Next step**: Create specification with `/specify "/spin-off-worktree command"`
