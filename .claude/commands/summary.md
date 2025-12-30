---
name: summary
description: Summarize information - alias for /consolidate (focuses on communication step)
accepts_args: true
arg_schema:
  - name: topic
    required: true
    description: "Topic to summarize"
composition:
  - command: consolidate
---

# Summary Command

**This is an alias for `/consolidate`**

`/summary` focuses on the **communication step** (presenting results), while `/consolidate` includes gathering and synthesizing first.

---

## Purpose

Summarize information about a topic clearly and concisely.

---

## Execution

This command delegates to `/consolidate` with the same arguments.

---

## Prompt Template

You are executing the `/summary` command, which is an alias for `/consolidate`.

Forward all arguments to `/consolidate`:

```bash
/consolidate $ARGUMENTS
```

The `/consolidate` command will:
1. Gather information (research phase)
2. Understand patterns (analysis phase)
3. Consolidate knowledge (synthesis phase)
4. Communicate results (summary phase)

For `/summary`, you can **skip detailed synthesis** if information is already coherent. Focus on **clear communication** of the summary.

---

## Examples

```bash
/summary "Lambda timeout behavior"
→ Delegates to /consolidate, focuses on presenting unified summary

/summary "Error handling patterns"
→ Delegates to /consolidate, focuses on clear communication
```

---

## Relationship to `/consolidate`

`/consolidate` is the primary command (gather + synthesize + communicate)
`/summary` is an alias (communication focus, presentation step)

---

## See Also

- `/consolidate` - Primary command (gather, understand, consolidate, communicate)
- `.claude/skills/research/` - Research methodology used by /consolidate
