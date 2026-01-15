---
name: prompt-engineering
description: Techniques for designing effective LLM prompts including zero-shot, few-shot, chain-of-thought, and anti-patterns
tier: 1
---

# Prompt Engineering Skill

**Focus**: Designing effective LLM prompts for accuracy, consistency, and reliability.

**Source**: Research from Prompt Engineering Guide, Lakera, Palantir, DigitalOcean (2025)

---

## When to Use This Skill

Use prompt-engineering when:
- Designing new prompts for LLM tasks
- Debugging poor LLM output quality
- Optimizing prompt for token efficiency
- Preventing prompt injection attacks
- Adding few-shot examples

**DO NOT use for:**
- Context/data preparation (see [context-engineering](../context-engineering/))
- Prompt versioning/deployment (see [prompt-management](../prompt-management/))
- Domain-specific report workflows (see [report-prompt-workflow](../report-prompt-workflow/))

---

## Core Principles

### 1. Be Explicit and Clear
> "Don't assume the model will infer what you want—state it directly."

```
❌ Bad: "Write a report"
✅ Good: "Create a 3-section report with executive summary, key findings,
         and recommendations. Use bullet points for findings."
```

### 2. Provide Structure and Boundaries
> "Add boundaries to focus the AI's response."

```
✅ "Explain quantum computing in exactly 100 words using only terms
   a high school student would understand."
```

### 3. Build Systems, Not Just Prompts
> "The most effective prompt engineers don't simply collect prompts, they build systems."

- Prompts become reusable frameworks
- Tested, refined, improved over time
- Parameterized for different scenarios

### 4. Iterate and Refine
> "The first prompt rarely works perfectly. Test and refine."

---

## Quick Decision Tree

```
Need to design a prompt?
├── Simple, well-defined task → Zero-shot (direct instruction)
├── Need format/style guidance → Few-shot (3 examples)
├── Complex reasoning required → Chain-of-Thought
├── Multiple approaches needed → Tree-of-Thought
├── Domain expertise needed → Role/Persona prompting
└── Optimizing existing prompt → Meta-prompting
```

---

## File Organization

```
.claude/skills/prompt-engineering/
├── SKILL.md           # This file - entry point
├── TECHNIQUES.md      # Core prompting techniques
├── ANTI-PATTERNS.md   # Common mistakes to avoid
└── SECURITY.md        # Prompt injection prevention
```

---

## References

- [TECHNIQUES.md](TECHNIQUES.md) - Detailed technique documentation
- [ANTI-PATTERNS.md](ANTI-PATTERNS.md) - What NOT to do
- [SECURITY.md](SECURITY.md) - Security considerations
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Lakera Ultimate Guide 2025](https://www.lakera.ai/blog/prompt-engineering-guide)
- [Palantir Best Practices](https://www.palantir.com/docs/foundry/aip/best-practices-prompt-engineering)
