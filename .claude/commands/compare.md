---
name: compare
description: Compare multiple alternatives - alias for /what-if (multi-way comparison mode)
accepts_args: true
arg_schema:
  - name: alternatives
    required: true
    description: "Alternatives to compare (e.g., 'Redis vs DynamoDB vs ElastiCache')"
  - name: save
    required: false
    description: "Optional: 'save' to create persistent comparison document"
composition:
  - command: what-if
---

# Compare Command

**This is an alias for `/what-if` (multi-way comparison mode)**

`/compare` is **specialized for comparing 2+ alternatives**, while `/what-if` supports:
1. Binary comparison (scenario analysis)
2. Multi-way comparison ← **this is what `/compare` does**
3. Relationship analysis

---

## Purpose

Compare multiple alternatives (2+) with structured evaluation matrix.

---

## Execution

This command delegates to `/what-if` with comparison mode.

---

## Prompt Template

You are executing the `/compare` command, which is an alias for `/what-if` in **multi-way comparison mode**.

Forward to `/what-if` with "compare" prefix:

```bash
/what-if "compare $ARGUMENTS"
```

The `/what-if` command will:
1. Detect "compare" keyword → use multi-way comparison template
2. Generate comparison matrix
3. Evaluate alternatives across dimensions
4. Provide recommendation

---

## Output Format

The output will use `/what-if`'s multi-way comparison template:

```markdown
MULTI-WAY COMPARISON: {Option A} vs {Option B} vs {Option C}

## Comparison Matrix

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Performance | X/10 | Y/10 | Z/10 |
| Cost | X/10 | Y/10 | Z/10 |
| Complexity | X/10 | Y/10 | Z/10 |
| TOTAL | XX/40 | YY/40 | ZZ/40 |

## Recommendation: {Winner}

{Rationale}
```

---

## Examples

```bash
/compare "Redis vs DynamoDB vs ElastiCache for caching"
→ Invokes: /what-if "compare Redis vs DynamoDB vs ElastiCache for caching"
→ Generates comparison matrix

/compare "Lambda vs ECS vs EKS" save
→ Invokes: /what-if "compare Lambda vs ECS vs EKS" save
→ Saves comparison to .claude/what-if/
```

---

## Relationship to `/what-if`

`/what-if` is the **superset** (3 modes: binary, multi-way, relationship)
`/compare` is a **specialized entry point** for multi-way comparison only

**When to use**:
- Use `/compare` when you have 2+ specific alternatives to evaluate
- Use `/what-if` for single-scenario exploration or relationship analysis

---

## See Also

- `/what-if` - Primary command (scenario analysis, multi-way comparison, relationship analysis)
- `.claude/skills/research/` - Research methodology
