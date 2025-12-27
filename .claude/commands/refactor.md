---
name: refactor
description: Analyze code complexity and hotspots with actionable refactoring recommendations (auto-detects analysis mode)
accepts_args: true
arg_schema:
  - name: target
    required: true
    description: "Path to analyze (file or directory) - mode auto-detected"
  - name: mode_or_output
    required: false
    description: "Analysis mode (complexity/hotspots/all) OR output filename"
composition:
  - skill: refactor
---

# Refactor Command

**Purpose**: Analyze code complexity and hotspots to identify high-priority refactoring opportunities

**Core Principle**: "Measure first, refactor second" - use data to prioritize refactoring efforts where they have maximum impact

**When to use**:
- Before adding new features to complex code
- During code reviews to identify technical debt
- When preparing for major refactoring
- To find hotspots (high churn + high complexity)
- Monthly health checks of codebase quality
- When velocity slows due to code complexity
- To validate that refactoring reduced complexity

---

## Quick Reference

```bash
# Analyze single file (complexity mode)
/refactor src/workflow/workflow_nodes.py

# Analyze directory (all mode: complexity + hotspots)
/refactor src/workflow/

# Explicit hotspots analysis
/refactor src/ hotspots

# Explicit complexity analysis
/refactor src/workflow/ complexity

# Save report to file
/refactor src/workflow/ report.md

# Explicit mode + save
/refactor src/ complexity refactor-report.md
```

---

## Analysis Modes

### Mode 1: Complexity
**Analyzes**: Cyclomatic complexity, cognitive complexity, LOC, parameters

**Best for**: Single file or focused module analysis

**Metrics**:
- Cyclomatic Complexity (CC): Number of independent code paths
- Cognitive Complexity: How difficult code is to understand
- Lines of Code (LOC): Function size
- Parameters: Number of function arguments

**Thresholds** (defaults):
- CC ≤ 10 (Functions with > 10 are complex)
- Cognitive ≤ 15 (Higher = harder to understand)
- LOC ≤ 50 (Longer = should be split)
- Parameters ≤ 4 (More = consider parameter object)

---

### Mode 2: Hotspots
**Analyzes**: High churn (git commits) + high complexity

**Best for**: Finding files that change often AND are complex (highest risk)

**Metrics**:
- Commits: Number of changes (last 6 months)
- Max Complexity: Worst function in file
- Avg Complexity: Overall file complexity

**Thresholds**:
- Churn: > 15 commits in 6 months = high churn
- Complexity: CC > 10 = complex

**Priority Matrix**:
| Churn | Complexity | Priority | Label |
|-------|-----------|----------|-------|
| High (> 15) | High (> 10) | **P0** | 🔥 CRITICAL |
| High (> 15) | Low (≤ 10) | P1 | ⚠️ MONITOR |
| Low (≤ 15) | High (> 10) | P2 | 📝 TECH DEBT |
| Low (≤ 15) | Low (≤ 10) | P3 | ✅ HEALTHY |

---

### Mode 3: All (Complexity + Hotspots)
**Analyzes**: Both complexity and hotspots

**Best for**: Comprehensive codebase health check

**Output**: Complete analysis with priority-sorted findings

---

## Smart Detection

**Auto-detection logic**:
```
Input: /refactor $TARGET [$MODE_OR_OUTPUT]

If $TARGET ends with .py:
  → complexity mode (single file)

Else if $MODE_OR_OUTPUT in [complexity, hotspots, all]:
  → Use explicit mode

Else if $MODE_OR_OUTPUT ends with .md:
  → all mode, save to file

Else if "hotspot" or "churn" in $TARGET:
  → hotspots mode

Else:
  → all mode (directory analysis)
```

**Examples**:
```bash
/refactor src/file.py                    # complexity (single file)
/refactor src/workflow/                  # all (directory)
/refactor src/ hotspots                  # hotspots (explicit)
/refactor src/ report.md                 # all, save to file
/refactor src/workflow/ complexity       # complexity (explicit)
```

---

## Execution Flow

### Step 1: Parse Arguments and Detect Mode

**Input parsing**:
```bash
TARGET="$1"
MODE_OR_OUTPUT="${2:-}"
OUTPUT_FILE=""

# Detect mode
if [[ "$TARGET" == *.py ]]; then
  MODE="complexity"
elif [[ "$MODE_OR_OUTPUT" =~ ^(complexity|hotspots|all)$ ]]; then
  MODE="$MODE_OR_OUTPUT"
elif [[ "$MODE_OR_OUTPUT" == *.md ]]; then
  MODE="all"
  OUTPUT_FILE="$MODE_OR_OUTPUT"
elif [[ "$TARGET" =~ (hotspot|churn) ]]; then
  MODE="hotspots"
else
  MODE="all"  # Default for directories
fi

echo "Mode: $MODE"
echo "Target: $TARGET"
[[ -n "$OUTPUT_FILE" ]] && echo "Output: $OUTPUT_FILE"
```

---

### Step 2: Run Analysis Scripts

**Complexity mode**:
```bash
python .claude/skills/refactor/scripts/analyze_complexity.py "$TARGET" \
  --max-cc 10 \
  --max-cognitive 15 \
  --max-loc 50 \
  --max-params 4 \
  --json > /tmp/complexity.json
```

**Hotspots mode**:
```bash
python .claude/skills/refactor/scripts/analyze_hotspots.py "$TARGET" \
  --since "6 months ago" \
  --top 20 \
  --min-commits 15 \
  --json > /tmp/hotspots.json
```

**All mode**: Run both scripts

---

### Step 3: Parse JSON Results

**Complexity output format**:
```json
{
  "src/file.py": [
    {
      "name": "function_name",
      "lineno": 42,
      "complexity": 15,
      "cognitive": 18,
      "loc": 68,
      "params": 5,
      "rank": "C"
    }
  ]
}
```

**Hotspots output format**:
```json
[
  {
    "file": "src/workflow/nodes.py",
    "commits": 45,
    "max_complexity": 18,
    "avg_complexity": 12.3,
    "priority": "P0",
    "complex_functions": [
      {"name": "score_report", "cc": 18, "line": 248}
    ]
  }
]
```

---

### Step 4: Apply Priority Matrix

**Priority calculation**:
```python
def calculate_priority(commits: int, max_cc: int) -> str:
    if commits > 15 and max_cc > 10:
        return "P0"  # CRITICAL
    elif commits > 15:
        return "P1"  # MONITOR
    elif max_cc > 10:
        return "P2"  # TECH DEBT
    else:
        return "P3"  # HEALTHY
```

**Group files by priority**: P0 → P1 → P2 → P3

---

### Step 5: Generate Recommendations

**For each priority level**:
1. List files in that priority
2. Show metrics (commits, max CC, avg CC)
3. List top 3-5 complex functions with line numbers
4. **Recommend patterns** (link to REFACTORING-PATTERNS.md)

**Pattern selection logic**:
```python
def select_pattern(cc: int, cognitive: int, loc: int, params: int, nesting: int):
    patterns = []

    if cc > 10 and loc > 50:
        patterns.append("Extract Method")

    if cognitive > 15 or nesting > 3:
        patterns.append("Guard Clauses (early returns)")

    if params > 4:
        patterns.append("Introduce Parameter Object")

    if loc > 100:
        patterns.append("Split into smaller functions")

    if cc > 15:
        patterns.append("Simplify Conditionals")

    return patterns
```

---

### Step 6: Generate Example Refactoring (Top P0 Function)

**For the MOST critical function** (highest CC in P0 files):

1. **Show current code structure** (before)
2. **Identify pattern to apply** (Extract Method, Guard Clauses, etc.)
3. **Show refactored structure** (after)
4. **Calculate expected improvement** (CC 18 → 4, LOC 68 → 8+helpers)

**Example format**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE REFACTORING: {function_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: {file_path}:{line_number}
Current Metrics: CC {cc}, Cognitive {cognitive}, LOC {loc}
Pattern: {pattern_name}

BEFORE (current structure):
```python
{current_code_structure}
```

AFTER (refactored):
```python
{refactored_code_structure}
```

EXPECTED IMPROVEMENT:
• {function_name}: CC {before_cc} → {after_cc} ({percent}% reduction)
• New functions: CC 2-3 each (simple, testable)
• LOC: {before_loc} → {after_loc} (main) + {helper_count} helpers
• Cognitive: {before_cog} → {after_cog} (no deep nesting)

Pattern reference:
  .claude/skills/refactor/REFACTORING-PATTERNS.md#{pattern_id}
```

---

### Step 7: Format Output

**Verbose terminal output** (default):
```
====================================================
REFACTORING ANALYSIS: {target_path}
====================================================

Mode: {mode}
Analyzed: {file_count} files
Thresholds: CC ≤ 10, Cognitive ≤ 15, LOC ≤ 50, Params ≤ 4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 - CRITICAL HOTSPOTS ({count} files)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 {file_path}
   Commits: {commits} (last 6 months)
   Max CC: {max_cc} | Avg CC: {avg_cc}

   Complex functions:
   • {function_name} (line {lineno}) - CC: {cc}, Cognitive: {cognitive}, LOC: {loc}
     Patterns: {pattern1}, {pattern2}
     See: .claude/skills/refactor/REFACTORING-PATTERNS.md#{pattern_id}

   🚨 Action: URGENT - Refactor before next feature

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE REFACTORING: {top_p0_function}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{Full example as shown in Step 6}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P1 - MONITOR ({count} files)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  {file_path}
   Commits: {commits}
   Max CC: {max_cc} | Avg CC: {avg_cc}

   Complex functions:
   • {function_name} (line {lineno}) - CC: {cc}
     Patterns: {patterns}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P2 - TECH DEBT ({count} files)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 {file_path}
   Commits: {commits}
   Max CC: {max_cc} | Avg CC: {avg_cc}

   Complex functions:
   • {function_name} (line {lineno}) - CC: {cc}
     Patterns: {patterns}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P3 - HEALTHY ({count} files)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ {file_path}
   Commits: {commits}
   Max CC: {max_cc} | Avg CC: {avg_cc}
   Status: No action needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total files analyzed: {total_files}
  • P0 (Critical): {p0_count} files 🔥
  • P1 (Monitor): {p1_count} files ⚠️
  • P2 (Tech debt): {p2_count} files 📝
  • P3 (Healthy): {p3_count} files ✅

Recommended actions:
  1. Refactor P0 files immediately (block new features)
  2. Monitor P1 files (review quarterly)
  3. Schedule P2 files (next refactoring sprint)
  4. Maintain P3 files (keep healthy)

====================================================
```

---

### Step 8: Save to File (if requested)

**If output filename provided**:
```bash
if [[ -n "$OUTPUT_FILE" ]]; then
  # Write report to file
  cat > "$OUTPUT_FILE" << 'EOF'
{Full analysis output in markdown format}
EOF

  echo "✅ Refactoring report saved: $OUTPUT_FILE"
  echo ""
  echo "Next steps:"
  echo "  - Review P0 files (critical hotspots)"
  echo "  - Apply recommended patterns"
  echo "  - Re-run analysis after refactoring to verify improvement"
fi
```

**Report location**: Saved in current directory (user-specified filename)

---

## Priority Matrix

| Priority | Churn | Complexity | Label | Action |
|----------|-------|-----------|-------|--------|
| **P0** | > 15 commits | CC > 10 | 🔥 CRITICAL | Refactor immediately |
| **P1** | > 15 commits | CC ≤ 10 | ⚠️ MONITOR | Review quarterly |
| **P2** | ≤ 15 commits | CC > 10 | 📝 TECH DEBT | Schedule in sprint |
| **P3** | ≤ 15 commits | CC ≤ 10 | ✅ HEALTHY | Maintain quality |

**Why this matrix works**:
- **P0**: High churn + high complexity = highest risk (changes break complex code)
- **P1**: High churn + low complexity = watch for degradation
- **P2**: Low churn + high complexity = technical debt (hard to change when needed)
- **P3**: Low churn + low complexity = healthy (no action needed)

---

## Examples

### Example 1: Single File Analysis

```bash
/refactor src/workflow/workflow_nodes.py
```

**Output**:
```
====================================================
REFACTORING ANALYSIS: src/workflow/workflow_nodes.py
====================================================

Mode: complexity
Analyzed: 1 file
Thresholds: CC ≤ 10, Cognitive ≤ 15, LOC ≤ 50

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLEX FUNCTIONS (3 functions above threshold)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 score_report (line 248)
   CC: 18, Cognitive: 22, LOC: 68, Params: 1
   Patterns: Extract Method, Simplify Conditionals, Guard Clauses
   See: .claude/skills/refactor/REFACTORING-PATTERNS.md#extract-method

⚠️  validate_ticker_data (line 156)
   CC: 14, Cognitive: 16, LOC: 52, Params: 1
   Patterns: Guard Clauses
   See: .claude/skills/refactor/REFACTORING-PATTERNS.md#guard-clauses

⚠️  process_news_feed (line 324)
   CC: 12, Cognitive: 14, LOC: 45, Params: 2
   Patterns: Extract Method
   See: .claude/skills/refactor/REFACTORING-PATTERNS.md#extract-method

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE REFACTORING: score_report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: src/workflow/workflow_nodes.py:248
Current Metrics: CC 18, Cognitive 22, LOC 68
Pattern: Extract Method

BEFORE:
```python
def score_report(state: AgentState) -> AgentState:
    # Mixed concerns: validation, calculation, thresholds, updates
    if not state.get("report"):
        state["error"] = "No report"
        return state
    # ... 60+ more lines ...
```

AFTER:
```python
def score_report(state: AgentState) -> AgentState:
    if not _has_valid_report(state):
        return _set_error(state, "No report")
    scores = _calculate_scores(state)
    passed = _check_thresholds(scores)
    return _update_state(state, scores, passed)
```

EXPECTED IMPROVEMENT:
• score_report: CC 18 → 4 (78% reduction)
• New helpers: CC 2-3 each (simple, testable)
• LOC: 68 → 8 (main) + 4 helpers (~15 lines each)

====================================================
```

---

### Example 2: Directory Analysis (All Mode)

```bash
/refactor src/workflow/
```

**Output**:
```
====================================================
REFACTORING ANALYSIS: src/workflow/
====================================================

Mode: all (complexity + hotspots)
Analyzed: 12 files
Thresholds: CC ≤ 10, Cognitive ≤ 15, LOC ≤ 50

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P0 - CRITICAL HOTSPOTS (1 file)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 src/workflow/workflow_nodes.py
   Commits: 45 (last 6 months)
   Max CC: 18 | Avg CC: 12.3

   🚨 Action: URGENT - Refactor before next feature

[... full P0/P1/P2/P3 breakdown ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total files: 12
  • P0: 1 file 🔥
  • P1: 2 files ⚠️
  • P2: 3 files 📝
  • P3: 6 files ✅

====================================================
```

---

### Example 3: Hotspots Only

```bash
/refactor src/ hotspots
```

**Output**: Only shows hotspot analysis (churn + complexity), no detailed complexity metrics

---

### Example 4: Save Report to File

```bash
/refactor src/ refactor-report-2025-12-24.md
```

**Output**:
```
[... full analysis ...]

✅ Refactoring report saved: refactor-report-2025-12-24.md

Next steps:
  - Review P0 files (critical hotspots)
  - Apply recommended patterns
  - Re-run analysis after refactoring to verify improvement
```

---

## Error Handling

### Error 1: Invalid Path

```bash
/refactor nonexistent/path/
```

**Response**:
```
❌ Error: Path not found

Path: nonexistent/path/
Expected: Valid file (*.py) or directory

Usage: /refactor <path> [mode|filename]

Examples:
  /refactor src/file.py
  /refactor src/workflow/
  /refactor src/ hotspots
```

---

### Error 2: No Python Files Found

```bash
/refactor docs/
```

**Response**:
```
⚠️  Warning: No Python files found

Path: docs/
Found: 0 *.py files

Suggestion: Check path or use directory with Python code

```

---

### Error 3: Git Not Available (Hotspots Mode)

```bash
/refactor src/ hotspots
```

**Response** (if not a git repo):
```
❌ Error: Git repository required for hotspot analysis

Hotspot mode analyzes git commit history.

Options:
  1. Use complexity mode: /refactor src/ complexity
  2. Initialize git repo: git init
  3. Analyze from git repository root

```

---

## Directory Structure

**Reports saved to** (when filename provided):
```
{current_directory}/
└── {user-specified-filename}.md
```

**Example**:
```bash
/refactor src/ refactor-report.md
# Creates: ./refactor-report.md (in current directory)
```

**No automatic directory creation** - reports go where user specifies

---

## Integration with Other Commands

### Workflow 1: Refactor → Observe → Journal

```bash
# Identify hotspot
/refactor src/workflow/
# → P0: workflow_nodes.py (CC 18, 45 commits)

# Refactor the code
# ... apply Extract Method pattern ...

# Capture the change
/observe execution "Refactored score_report function (CC 18 → 4)"

# Document the learning
/journal pattern "Extract Method reduced CC by 78%"
```

---

### Workflow 2: Refactor → Validate → Refactor

```bash
# Initial analysis
/refactor src/workflow/ complexity
# → score_report: CC 18

# Refactor code
# ... apply patterns ...

# Validate improvement
/refactor src/workflow/ complexity
# → score_report: CC 4 ✅

# If still complex, iterate
```

---

### Workflow 3: Refactor (Before) → Code Change → Refactor (After)

```bash
# Baseline before adding feature
/refactor src/api/ baseline-before.md

# Add new feature
# ... implementation ...

# Compare complexity delta
/refactor src/api/ baseline-after.md

# Review: Did complexity increase? Where?
```

---

## Principles

### 1. Measure First, Refactor Second
Never refactor without data. Complexity analysis shows WHERE to focus effort.

### 2. Prioritize by Risk (Hotspots)
High churn + high complexity = highest risk. Fix these first.

### 3. Test Before and After
Run analysis before refactoring (baseline) and after (verify improvement).

### 4. One Pattern at a Time
Apply one refactoring pattern, verify, commit. Don't mix multiple patterns.

### 5. Aim for < 10 CC
Cyclomatic complexity > 10 is hard to test. Aim for 5-7 for critical code.

---

## Related Commands

- `/observe execution` - Capture refactoring actions
- `/journal pattern` - Document successful refactoring patterns
- `/validate` - Check that tests still pass after refactoring
- `/proof` - Prove complexity reduced (CC before vs after)

---

## See Also

- `.claude/skills/refactor/SKILL.md` - Refactor skill documentation
- `.claude/skills/refactor/REFACTORING-PATTERNS.md` - Pattern catalog
- `.claude/skills/refactor/scripts/analyze_complexity.py` - Complexity analysis tool
- `.claude/skills/refactor/scripts/analyze_hotspots.py` - Hotspot detection tool
