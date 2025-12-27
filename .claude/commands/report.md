---
name: report
description: Generate markdown summary of work sessions with decisions, problems solved, and next steps
accepts_args: true
arg_schema:
  - name: lookback
    required: false
    description: "Time period: session (default), 1h, today, week, or 'all'"
  - name: output_file
    required: false
    description: "Optional output file path (default: stdout)"
composition: []
---

# Report Command

**Purpose**: Generate comprehensive markdown summary of work sessions

**Core Principle**: "Knowledge captured is knowledge retained" - sessions fade from memory, reports preserve context

**When to use**:
- End of work session → Capture what was accomplished
- End of day → Daily summary
- End of week → Weekly review
- Before context switch → Preserve current work state
- Handoff to team → Document progress

---

## Quick Reference

```bash
/report                          # Current session (default)
/report 1h                       # Last hour
/report today                    # Today's work
/report week                     # Last 7 days
/report session output.md        # Save to file
/report today weekly-summary.md  # Today's work to file
```

---

## Report Sections

### 1. Summary
**What it contains**:
- High-level overview (2-3 paragraphs)
- Main theme of session
- Overall outcome (what was achieved)

### 2. Topics Covered
**What it contains**:
- Grouped by theme
- Each topic with outcome
- Links to related files/resources

### 3. Decisions Made
**What it contains**:
- Architectural decisions
- Technical choices
- Trade-offs considered
- Links to journal entries

### 4. Problems Solved
**What it contains**:
- Bugs fixed
- Issues resolved
- Root causes identified
- Links to error journals

### 5. Technical Details
**What it contains**:
- Files created/modified
- Commands executed
- Tools used
- Observations captured

### 6. Next Steps
**What it contains**:
- Action items
- Follow-up tasks
- Questions to answer
- Blockers identified

### 7. Knowledge Captured
**What it contains**:
- Journal entries created
- Observations recorded
- Patterns abstracted
- Skills updated

---

## Execution Flow

### Step 1: Parse Arguments

**Determine lookback period**:
```bash
/report              # session (current conversation)
/report 1h           # Last 1 hour
/report 2h           # Last 2 hours
/report today        # Since midnight
/report week         # Last 7 days
/report all          # Entire conversation history
```

**Determine output**:
```bash
/report                    # stdout (display in chat)
/report session out.md     # Save to file
/report today summary.md   # Today to file
```

---

### Step 2: Collect Session Data

**Analyze conversation messages** for:
- User requests and questions
- Claude responses and actions
- Tool calls (Read, Write, Edit, Bash, etc.)
- Files modified
- Observations created
- Journals written
- Validations performed
- Decompositions generated

**Extract metadata**:
- Timestamp of session start/end
- Duration
- Number of messages
- Number of tool calls
- Files touched

---

### Step 3: Group by Theme

**Identify themes** from conversation:
- Implementation (writing code)
- Debugging (solving errors)
- Planning (decomposing goals)
- Research (investigating questions)
- Documentation (writing docs)
- Deployment (releasing changes)
- Review (code review, validation)

**Group related messages** under each theme.

---

### Step 4: Extract Key Elements

#### Decisions Made
- **Pattern**: Look for `/journal architecture` or decision language
- **Extract**: What was decided, alternatives considered, rationale
- **Link**: Reference journal entries

#### Problems Solved
- **Pattern**: Look for `/observe failure`, `/journal error`, error messages
- **Extract**: What broke, root cause, solution applied
- **Link**: Reference observations and error journals

#### Files Modified
- **Pattern**: Tool calls to Write, Edit
- **Extract**: File paths, nature of changes
- **Group**: By purpose (new features, bug fixes, refactoring)

#### Commands Executed
- **Pattern**: Bash tool calls
- **Extract**: Significant commands (deploys, tests, AWS operations)
- **Categorize**: By purpose (deployment, testing, investigation)

#### Knowledge Captured
- **Pattern**: `/journal`, `/observe`, `/abstract`, `/validate`
- **Extract**: Entry titles, categories, file paths
- **Link**: Direct links to created files

---

### Step 5: Generate Report

```markdown
# Work Session Report

**Period**: {lookback period}
**Date**: {date range}
**Duration**: {session duration}

---

## Summary

{2-3 paragraph overview of what was accomplished}

**Key Achievements**:
- {Achievement 1}
- {Achievement 2}
- {Achievement 3}

---

## Topics Covered

### {Theme 1} (e.g., Implementation)
**Outcome**: {What was achieved}

**Work done**:
- {Specific task 1}
- {Specific task 2}

**Files modified**:
- `{file_path}` - {change description}

**Related**:
- {Link to observation/journal}

---

### {Theme 2} (e.g., Debugging)
**Outcome**: {What was resolved}

**Problems investigated**:
- {Problem 1}: {Root cause} → {Solution}
- {Problem 2}: {Root cause} → {Solution}

**Evidence**:
- Observation: `.claude/observations/{date}/{file}.md`
- Journal: `.claude/journals/error/{date}-{slug}.md`

---

### {Theme 3} (e.g., Planning)
[...]

---

## Decisions Made

### Decision 1: {Decision title}
**Context**: {Why this decision was needed}

**Options considered**:
- Option A: {Pros/cons}
- Option B: {Pros/cons}

**Choice**: {What was chosen}

**Rationale**: {Why}

**Documented in**: `.claude/journals/architecture/{date}-{slug}.md`

---

### Decision 2: {Decision title}
[...]

---

## Problems Solved

### Problem 1: {Problem description}
**Symptoms**: {What was observed}

**Root cause**: {What actually caused it}

**Solution**: {How it was fixed}

**Prevention**: {How to prevent recurrence}

**Evidence**:
- Observation: `.claude/observations/{date}/failure-{slug}.md`
- Journal: `.claude/journals/error/{date}-{slug}.md`

---

### Problem 2: {Problem description}
[...]

---

## Technical Details

### Files Created ({count})
```
{file_path} - {purpose}
{file_path} - {purpose}
```

### Files Modified ({count})
```
{file_path} - {changes}
{file_path} - {changes}
```

### Commands Executed
**Deployment**:
```bash
{command}
{command}
```

**Testing**:
```bash
{command}
```

**AWS Operations**:
```bash
{command}
```

### Tools Used
- Read: {count} files
- Write: {count} files
- Edit: {count} files
- Bash: {count} commands
- Grep: {count} searches

---

## Next Steps

### Immediate (This Session)
- [ ] {Action item}
- [ ] {Action item}

### Short-term (This Week)
- [ ] {Action item}
- [ ] {Action item}

### Questions to Answer
- {Question 1}
- {Question 2}

### Blockers
- {Blocker 1}: {Mitigation strategy}

---

## Knowledge Captured

### Observations ({count})
- **execution**: `.claude/observations/{date}/execution-{slug}.md`
  - {Brief description}
- **failure**: `.claude/observations/{date}/failure-{slug}.md`
  - {Brief description}
- **behavior**: `.claude/observations/{date}/behavior-{slug}.md`
  - {Brief description}

### Journals ({count})
- **architecture**: `.claude/journals/architecture/{date}-{slug}.md`
  - {Decision captured}
- **error**: `.claude/journals/error/{date}-{slug}.md`
  - {Solution documented}
- **pattern**: `.claude/journals/pattern/{date}-{slug}.md`
  - {Pattern identified}

### Validations ({count})
- `.claude/validations/{date}-{slug}.md`
  - Claim: {claim}
  - Result: {TRUE/FALSE/PARTIALLY/INCONCLUSIVE}

### Abstractions ({count})
- `.claude/abstractions/{pattern_type}-{date}-{slug}.md`
  - Pattern: {pattern name}
  - Confidence: {High/Medium/Low}

---

## Metrics

**Session Statistics**:
- Duration: {hours}h {minutes}m
- Messages: {count}
- Tool calls: {count}
- Files touched: {count}
- Knowledge entries: {count}

**Productivity Indicators**:
- Problems solved: {count}
- Decisions made: {count}
- Features implemented: {count}
- Tests written: {count}

---

## Related Context

**Previous sessions**:
- {Link to previous report if exists}

**Continuing work**:
- {Link to related observations/journals}

**References**:
- CLAUDE.md principles: {which ones were followed}
- Skills invoked: {which skills were used}

---

*Report generated by `/report {args}`*
*Session: {session_id}*
*Generated: {timestamp}*
```

---

### Step 6: Output Report

**If no output file specified** (default):
```
Display report in chat (markdown formatted)
```

**If output file specified**:
```bash
# Write to file
cat > "$OUTPUT_FILE" << 'EOF'
{report content}
EOF

# Confirm
echo "✅ Report saved to: $OUTPUT_FILE"
echo ""
echo "Preview:"
head -20 "$OUTPUT_FILE"
```

---

## Examples

### Example 1: Current Session Report

```bash
/report
```

**Output**:
```markdown
# Work Session Report

**Period**: Current session
**Date**: 2025-12-24 14:30 - 16:45
**Duration**: 2h 15m

---

## Summary

Implemented meta-cognitive learning loop with three new slash commands:
/observe (capture facts), /decompose (analyze), and /abstract (extract patterns).
These commands form a systematic approach to knowledge capture and pattern
extraction from development experience.

Updated all command documentation to support smart mode detection, eliminating
the need to specify modes explicitly. Claude now infers observation type,
decomposition mode, and pattern type from context.

**Key Achievements**:
- Implemented 3 meta-operation commands (1,600+ lines)
- Added smart mode detection to all commands
- Created comprehensive examples and documentation

---

## Topics Covered

### Implementation: Meta-Operations
**Outcome**: 3 new commands fully implemented and documented

**Work done**:
- Created /observe command (execution, failure, behavior modes)
- Created /decompose command (goal, failure modes)
- Created /abstract command (4 pattern types)
- Added smart mode detection to all 3 commands

**Files created**:
- `.claude/commands/observe.md` (712 lines)
- `.claude/commands/decompose.md` (881 lines)
- `.claude/commands/abstract.md` (1,036 lines)
- `.claude/observations/README.md` (412 lines)

---

### Enhancement: Smart Mode Detection
**Outcome**: Simplified command syntax by auto-detecting modes

**Work done**:
- Added keyword analysis for mode detection
- Updated all command documentation
- Provided backward compatibility

**Files modified**:
- `.claude/commands/observe.md` - Smart detection section
- `.claude/commands/decompose.md` - Smart detection section
- `.claude/commands/abstract.md` - Smart detection section
- `.claude/commands/README.md` - Updated examples

---

## Decisions Made

### Decision 1: Smart Mode Detection
**Context**: User requested simpler syntax without explicit modes

**Options considered**:
- A: Require explicit modes (current)
- B: Auto-detect with fallback to asking user

**Choice**: Option B - Smart detection with explicit override

**Rationale**: Better UX while maintaining precision. Backward compatible.

**Documented in**: Conversation (not journaled - implementation detail)

---

## Problems Solved

(None in this session - focused on greenfield implementation)

---

## Technical Details

### Files Created (7)
```
.claude/commands/observe.md - Observation capture command
.claude/commands/decompose.md - Goal/failure analysis command
.claude/commands/abstract.md - Pattern extraction command
.claude/observations/README.md - Observation system guide
(+ 3 directory structures)
```

### Files Modified (1)
```
.claude/commands/README.md - Added meta-operations section
```

---

## Next Steps

### Immediate (This Session)
- [ ] Implement /report command (in progress)
- [ ] Implement /evolve command
- [ ] Implement /validate command
- [ ] Implement /explain command

### Short-term (This Week)
- [ ] Test all commands with real examples
- [ ] Create sample observations/journals
- [ ] Update plan file with completion status

---

## Knowledge Captured

### Observations (0)
(None created - greenfield implementation session)

### Journals (0)
(None created - implementation focused, no decisions to journal)

### Commands Created (3)
- /observe - Fact capture
- /decompose - Analysis
- /abstract - Pattern extraction

---

## Metrics

**Session Statistics**:
- Duration: 2h 15m
- Messages: 47
- Tool calls: 23 (Write: 7, Edit: 12, Read: 4)
- Files touched: 8
- Knowledge entries: 0 (implementation session)

**Productivity Indicators**:
- Commands implemented: 3
- Documentation written: 3,000+ lines
- Features added: Smart mode detection

---

*Report generated by `/report`*
*Generated: 2025-12-24 16:45:32*
```

---

### Example 2: Daily Summary to File

```bash
/report today daily-summary-2025-12-24.md
```

**Output**:
```
✅ Report saved to: daily-summary-2025-12-24.md

Preview:
# Work Session Report

**Period**: Today (2025-12-24)
**Date**: 2025-12-24 09:00 - 17:30
**Duration**: 8h 30m

---

## Summary

Productive day implementing slash command system. Completed meta-operations
learning loop with /observe, /decompose, and /abstract commands. Enhanced
UX with smart mode detection. Started implementation of /validate, /report,
/evolve, and /explain commands.

[Full report in file...]
```

---

### Example 3: Weekly Summary

```bash
/report week
```

**Output**: Aggregates entire week's work:
```markdown
# Weekly Work Report

**Period**: Last 7 days
**Date**: 2025-12-18 - 2025-12-24
**Duration**: 32h 15m across 6 sessions

---

## Summary

Major milestone week: Implemented complete slash command system with meta-
cognitive learning loop. 7 commands implemented, 15+ documentation files
created, smart detection added across all commands.

**Week Highlights**:
- Implemented slash command system (Phase 1, 2A complete)
- Created meta-operations learning loop
- Enhanced with smart mode detection
- Began Phase 2B (validation, synthesis operations)

**Week in Numbers**:
- Commands implemented: 7
- Documentation: 8,000+ lines
- Files created: 25
- Problems solved: 3
- Decisions documented: 5

---

## Monday: Foundation
[Day summary...]

## Tuesday: Meta-Operations
[Day summary...]

## Wednesday-Thursday: Enhancement & Testing
[Day summary...]

## Friday: Validation & Synthesis
[Day summary...]

---

## Major Decisions This Week

1. Commands vs Skills architecture
2. Smart mode detection approach
3. Meta-operations learning loop design

---

## Problems Solved This Week

1. Lambda timeout issues (3 incidents)
2. Mode ambiguity in commands
3. Directory structure organization

---

[Full weekly aggregated details...]
```

---

## Report Customization

### Custom Sections

Users can request specific sections:
```bash
/report --sections="summary,decisions,next-steps"
/report --exclude="technical-details"
```

### Report Templates

Save report templates for different purposes:
- **Daily standup**: Focus on yesterday/today/blockers
- **Weekly review**: Aggregate week, highlight wins
- **Project handoff**: Complete context transfer
- **Post-incident**: Focus on problem investigation

---

## Integration with Other Commands

### Report → Journal (Graduation Path)
```
/report week
    ↓ (identifies significant decisions)
If decision is significant:
    ↓
/journal architecture "Decision from week's work"
```

### Observe → Report (Evidence Collection)
```
Work session with multiple /observe calls
    ↓
/report
    ↓ (automatically includes observations in "Knowledge Captured" section)
```

### Report → Evolve (Drift Detection)
```
/report week
    ↓ (shows patterns in behavior)
/evolve
    ↓ (uses report data to detect drift)
```

---

## Principles

### 1. Automatic Context Capture

Report should gather information automatically from:
- Conversation messages
- Tool calls
- Created files
- Observations/journals

No manual summarization needed.

### 2. Actionable Output

Report should end with clear next steps, not just summary of past.

### 3. Link Knowledge Artifacts

Connect report to observations, journals, validations for traceability.

### 4. Customizable Granularity

Support different time periods for different use cases.

### 5. Preserve Context

Reports enable resuming work after interruption or handoff to others.

---

## Related Commands

- `/journal` - Document specific decisions from report
- `/observe` - Create artifacts that reports reference
- `/evolve` - Uses report data to detect drift
- `/abstract` - Can analyze multiple reports for patterns

---

## See Also

- `.claude/commands/journal.md` - Knowledge journaling
- `.claude/commands/observe.md` - Observation capture
- `.claude/commands/README.md` - Command system overview
