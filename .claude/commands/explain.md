---
name: explain
description: Explain concepts clearly - alias for /understand (focuses on communication step)
accepts_args: true
arg_schema:
  - name: concept
    required: true
    description: "Concept to explain"
  - name: audience_level
    required: false
    description: "Optional: beginner, intermediate, expert (auto-detected if omitted)"
composition:
  - command: understand
---

# Explain Command

**This is an alias for `/understand`**

`/explain` focuses on the **communication step** (external explanation), while `/understand` includes building a mental model first.

---

## Purpose

Explain concepts clearly to the user at appropriate level (beginner/intermediate/expert).

---

## Execution

This command delegates to `/understand` with the same arguments.

---

## Prompt Template

You are executing the `/explain` command, which is an alias for `/understand`.

Forward all arguments to `/understand`:

```bash
/understand $ARGUMENTS
```

The `/understand` command will:
1. Build internal mental model (research phase)
2. Explain to user (communication phase)

For `/explain`, you can **skip detailed research** if you already understand the concept. Focus on **clear communication** to the user.

---

## Examples

```bash
/explain "feedback loops in thinking architecture"
→ Delegates to /understand, focuses on clear explanation

/explain "Lambda cold start" beginner
→ Delegates to /understand with beginner level

/explain "Aurora connection pooling" expert
→ Delegates to /understand with expert level
```

---

## Relationship to `/understand`

`/understand` is the primary command (internal + external)
`/explain` is an alias (external focus, communication step)

---

## See Also

- `/understand` - Primary command (build mental model + explain)
- `.claude/skills/research/` - Research methodology used by /understand
