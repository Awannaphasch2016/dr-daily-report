---
name: understand
description: Build mental model and explain concepts - generalizes /explain to include internal understanding
accepts_args: true
arg_schema:
  - name: concept
    required: true
    description: "Concept, pattern, or system to understand and explain"
  - name: audience_level
    required: false
    description: "Optional: beginner, intermediate, expert (auto-detected if omitted)"
composition:
  - skill: research
---

# Understand Command

**Purpose**: Build mental model (for Claude) + explain clearly (for user)

**Two-phase process**:
1. **Understand** (internal): Research, analyze, build mental model
2. **Explain** (external): Communicate understanding to user

**Generalizes `/explain`**: `/explain` focuses on communication, `/understand` includes building the mental model first

---

## Execution Flow

### Phase 1: Internal Understanding (Research)

1. Research concept systematically
2. Identify key components, relationships, patterns
3. Build mental model (how it works, why it exists, what it connects to)

### Phase 2: External Explanation (Communication)

1. Detect audience level (beginner/intermediate/expert) from context or argument
2. Structure explanation appropriately
3. Use examples relevant to audience
4. Clarify terminology and assumptions

---

## Output Format

```markdown
## Understanding of {concept}

### Mental Model (What/How/Why)

**What it is**: {Definition}
**How it works**: {Mechanism}
**Why it exists**: {Purpose/rationale}
**Relationships**: {What it connects to}

### Explanation for {audience_level}

{Explanation tailored to audience}

**Key takeaways**:
- {Takeaway 1}
- {Takeaway 2}

**Related concepts**:
- {Related 1}
- {Related 2}
```

---

## Examples

```bash
/understand "feedback loops in thinking architecture"
→ Researches feedback loops, builds mental model, explains

/understand "Lambda cold start" beginner
→ Explains Lambda cold start at beginner level

/understand "Aurora connection pooling" expert
→ Deep technical explanation for expert audience
```

---

## Relationship to `/explain`

`/explain` → `/understand` (alias)

`/understand` is the primary command (internal + external)
`/explain` is an alias (external only, focuses on communication)

---

## Prompt Template

You are executing the `/understand` command with arguments: $ARGUMENTS

**Concept**: $1
**Audience Level**: ${2:-auto-detect}

---

### Step 1: Internal Understanding (Research Phase)

Use the research skill to systematically understand the concept:

1. **What is it?**
   - Definition
   - Core purpose
   - Key characteristics

2. **How does it work?**
   - Mechanism
   - Components
   - Interactions

3. **Why does it exist?**
   - Problem it solves
   - Design rationale
   - Trade-offs

4. **What does it connect to?**
   - Related concepts
   - Dependencies
   - Context

**Research sources**:
- Code files (if technical concept)
- Documentation files
- Architecture diagrams
- Observations/journals
- External knowledge (if appropriate)

---

### Step 2: External Explanation (Communication Phase)

**Detect audience level**:
- **Beginner**: High-level overview, minimal jargon, concrete examples
- **Intermediate**: Technical details, some assumptions, practical use cases
- **Expert**: Deep technical analysis, trade-offs, edge cases

**Structure explanation**:
1. Start with clear definition
2. Explain mechanism with appropriate detail level
3. Provide examples relevant to audience
4. Highlight key takeaways
5. Mention related concepts for further exploration

---

### Step 3: Output

Generate structured output following the format above:

```markdown
## Understanding of {concept}

### Mental Model (What/How/Why)

[Your mental model built from research]

### Explanation for {audience_level}

[Explanation tailored to detected/specified audience level]

**Key takeaways**:
- [Most important points]

**Related concepts**:
- [Concepts for further exploration]
```

---

## Notes

- If you already have a solid mental model of the concept, you can skip detailed research
- Focus on **clear, accurate explanation** tailored to audience level
- Use examples from the codebase when explaining technical concepts
- For complex concepts, break down into digestible components
