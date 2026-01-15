---
name: context-engineering
description: Optimizing the information provided to LLMs through semantic layers, token optimization, and hallucination prevention
tier: 1
---

# Context Engineering Skill

**Focus**: Optimizing the information provided to LLMs for accuracy and efficiency.

**Source**: Research from dbt Labs, M1 Finance, Elastic, Mem0, RAGFlow (2025)

---

## When to Use This Skill

Use context-engineering when:
- Preparing data for LLM consumption
- Reducing token usage in prompts
- Preventing hallucinations in outputs
- Building semantic layers for data
- Optimizing RAG system context

**DO NOT use for:**
- Prompt design techniques (see [prompt-engineering](../prompt-engineering/))
- Prompt versioning/deployment (see [prompt-management](../prompt-management/))
- Domain-specific workflows (see [report-prompt-workflow](../report-prompt-workflow/))

---

## Core Principles

### 1. Semantic Layer Architecture

> "LLMs are fantastic for translating contextual questions into usable answers, but they struggle with hallucinations and consistency. The Semantic Layer has been theorized as a key interface for LLMs because each is strong where the other is weak."

**Accuracy Benchmark** (dbt Labs):
| Approach | Accuracy |
|----------|----------|
| Direct LLM | ~30% |
| Semantic Layer | **83%** |

### 2. Separate Concerns

> "Separate what numbers MEAN (code) from how to COMBINE them (LLM)."

- **Code handles**: Calculations, exact values, classifications
- **LLM handles**: Narrative synthesis, contextual interpretation

### 3. Token Efficiency

> "In production RAG systems, 30-40% of retrieved context is semantically redundant."

Strategies:
- Front-load critical information
- Trim redundant context
- Use structured data formats
- Compress with memory engines (up to 80% reduction)

### 4. Hallucination Prevention

> "Proper context engineering reduces hallucinations by 30-50%."

- Ground responses in verified sources
- Use semantic layers for business logic
- Constrain outputs with validation
- Provide explicit success criteria

---

## Quick Decision Tree

```
Preparing data for LLM?
├── Numeric data → Use Semantic Layer pattern
│   ├── Layer 1: Code calculates values
│   ├── Layer 2: Code classifies semantically
│   ├── Layer 3: LLM synthesizes narrative
│   └── Layer 4: Code injects exact values
├── Large context → Use Token Optimization
│   ├── Remove redundancy
│   ├── Compress history
│   └── Prioritize critical info
├── Hallucination risk → Use Ground Truth patterns
│   ├── Placeholders for numbers
│   ├── Citation requirements
│   └── Output validation
└── User preferences → Use Memory patterns
    ├── Episodic memory
    └── User context
```

---

## The Four Strategic Categories

| Category | Description | Purpose |
|----------|-------------|---------|
| **WRITE** | Add information to context | Enrich LLM knowledge |
| **SELECT** | Choose what to include | Focus on relevant data |
| **COMPRESS** | Reduce redundancy | Optimize tokens |
| **ISOLATE** | Separate concerns | Maintain clarity |

---

## File Organization

```
.claude/skills/context-engineering/
├── SKILL.md                    # This file - entry point
├── SEMANTIC-LAYER.md           # Three-layer architecture
├── TOKEN-OPTIMIZATION.md       # Token efficiency patterns
└── HALLUCINATION-PREVENTION.md # Ground truth patterns
```

---

## References

- [SEMANTIC-LAYER.md](SEMANTIC-LAYER.md) - Core architecture pattern
- [TOKEN-OPTIMIZATION.md](TOKEN-OPTIMIZATION.md) - Efficiency strategies
- [HALLUCINATION-PREVENTION.md](HALLUCINATION-PREVENTION.md) - Accuracy patterns
- [dbt Labs - Semantic Layer](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms)
- [M1 Finance Case Study](https://www.getdbt.com/blog/m1-finance-ai-self-service-claude-dbt)
- [Elastic - Context Engineering](https://www.elastic.co/search-labs/blog/context-engineering-overview)
