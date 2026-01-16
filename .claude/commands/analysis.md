---
name: analysis
description: Comprehensive analysis workflow - automates explore → what-if → validate → consolidate chain
accepts_args: true
arg_schema:
  - name: topic
    required: true
    description: "Topic to analyze comprehensively"
composition:
  - command: explore
  - command: what-if
  - command: validate
  - command: consolidate
---

# Analysis Command

**Purpose**: Automate comprehensive analysis workflow by chaining multiple thinking commands in sequence.

**Core Principle**: "One command, full understanding" - execute complete analytical workflow without manual command chaining.

**When to use**:
- Need deep understanding from all perspectives
- Want alternative approaches evaluated
- Require assumptions tested
- Need findings synthesized into coherent summary

**When NOT to use**:
- Quick lookups (use `/explore` only)
- Single-angle investigation (use specific command)
- Already know what you need (use targeted command)

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `orchestrate`

**Tier**: 2 (Composes: `/explore`, `/what-if`, `/validate`, `/consolidate`)

When `/analysis` executes, it orchestrates a multi-mode pipeline:

| Pipeline Step | Command | Mode | Tuple Effect |
|---------------|---------|------|--------------|
| 1 | `/explore` | divergent | Expands Constraints with alternatives |
| 2 | `/what-if` | compare | Adds alternatives to Constraints |
| 3 | `/validate` | verify | Tests Invariant, annotates Check |
| 4 | `/consolidate` | converge | Synthesizes Constraints into decision |

**Aggregate Tuple Effect**:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **COMPREHENSIVE**: Full topic understanding from all angles |
| **Invariant** | **REFINED**: Validated assumptions, tested hypotheses |
| **Principles** | **NONE**: Does not modify principles |
| **Strategy** | Consumes 4 modes in sequence |
| **Check** | Aggregates checks from all 4 phases |

**Pipeline State Flow**:
```yaml
phase_1_explore:
  constraints_added: ["alternative_1", "alternative_2", "edge_cases"]

phase_2_what_if:
  constraints_added: ["comparison_matrix", "trade_offs"]

phase_3_validate:
  check_annotation:
    hypotheses_tested: 3
    validated: 2
    refuted: 1

phase_4_consolidate:
  output: "synthesized_understanding"
  confidence: HIGH
```

---

## Local Check (Mode Completion Criteria)

The `/analysis` orchestration is complete when ALL phases complete:

| Phase | Completion Criterion |
|-------|---------------------|
| **Explore** | Multiple perspectives gathered, alternatives identified |
| **What-If** | Alternatives compared, trade-offs documented |
| **Validate** | Key assumptions tested with evidence |
| **Consolidate** | Findings synthesized into coherent summary |

**Aggregate Check Result**:
- **PASS**: All 4 phases completed → comprehensive analysis ready
- **PARTIAL**: Some phases incomplete → continue remaining phases
- **FAIL**: Explore phase failed → topic too vague, need clarification

---

## Execution Flow

This command automatically chains four analysis phases:

### Phase 1: Multi-Angle Exploration
**Command**: `/explore {topic}`

- Understand the topic from all perspectives
- Identify key concepts, patterns, and relationships
- Discover alternatives and edge cases

### Phase 2: Alternative Evaluation
**Command**: `/what-if`

- Evaluate alternatives discovered in exploration
- Compare different approaches
- Assess trade-offs and implications

### Phase 3: Assumption Testing
**Command**: `/validate`

- Test key assumptions identified
- Verify hypotheses
- Confirm or refute beliefs

### Phase 4: Knowledge Synthesis
**Command**: `/consolidate`

- Synthesize findings from all phases
- Create coherent summary
- Provide actionable conclusions

---

## Usage

```bash
/analysis "Lambda timeout behavior"
```

**Automatically executes**:
1. `/explore "Lambda timeout behavior"` - Multi-angle exploration
2. `/what-if` (based on alternatives found in exploration)
3. `/validate` (based on hypotheses identified)
4. `/consolidate "Lambda timeout analysis"` - Synthesize all findings

**Output**: Comprehensive analysis covering exploration, alternatives, validation, and synthesis.

---

## Examples

### Example 1: Technical Investigation

```bash
/analysis "Aurora MySQL connection pooling"
```

**Workflow**:
- **Explore**: How connection pooling works, current implementation, patterns
- **What-if**: Compare connection pool libraries (HikariCP vs c3p0)
- **Validate**: Test assumption "connection pool reduces latency by 50%"
- **Consolidate**: Synthesize findings into implementation recommendation

---

### Example 2: Architectural Decision

```bash
/analysis "SQS vs Lambda async processing"
```

**Workflow**:
- **Explore**: Both architectures, use cases, constraints
- **What-if**: Compare SQS-based vs Lambda-based approaches
- **Validate**: Test assumptions about cost, latency, complexity
- **Consolidate**: Recommendation with rationale

---

## Relationship to Other Commands

**Replaces manual workflow**:
```bash
# Before /analysis (manual chaining)
/explore {topic}
  ↓ (read results, identify alternatives)
/what-if {alternatives discovered}
  ↓ (read results, identify assumptions)
/validate {hypotheses identified}
  ↓ (read results)
/consolidate {findings}

# After /analysis (automated workflow)
/analysis {topic}
  ↓ (all phases automated)
```

**Individual commands still available**:
- Use `/explore` alone for quick investigation
- Use `/what-if` alone for focused comparison
- Use `/validate` alone for assumption testing
- Use `/consolidate` alone for synthesis

---

## Best Practices

### Do
- **Use for deep dives** (complex topics requiring full understanding)
- **Let workflow complete** (all four phases provide value)
- **Trust the process** (each phase builds on previous)

### Don't
- **Use for simple lookups** (overkill for "where is X defined?")
- **Interrupt workflow** (let all phases complete)
- **Skip reading output** (comprehensive analysis requires engagement)

---

## Implementation Note

This command uses **multi-command composition** to automate the analytical workflow. If your version of Claude Code doesn't support multi-command chaining in the `composition` frontmatter, this command will only execute the first command (`/explore`). In that case, manually run the subsequent commands:

```bash
/analysis {topic}      # Runs /explore
/what-if              # Run manually
/validate             # Run manually
/consolidate          # Run manually
```

---

## See Also

- `/explore` - Multi-angle exploration (first phase)
- `/what-if` - Alternative evaluation (second phase)
- `/validate` - Assumption testing (third phase)
- `/consolidate` - Knowledge synthesis (fourth phase)
- `.claude/diagrams/thinking-process-architecture.md` - Thinking process design
