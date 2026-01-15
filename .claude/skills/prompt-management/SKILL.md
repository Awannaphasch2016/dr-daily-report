---
name: prompt-management
description: Langfuse prompt versioning, A/B testing, and observability patterns
tier: 1
---

# Prompt Management Skill

**Focus**: Managing prompt lifecycles with versioning, testing, and observability.

**Source**: Langfuse documentation, research from 2025

---

## When to Use This Skill

Use prompt-management when:
- Versioning prompts in Langfuse
- Setting up A/B tests for prompt variants
- Tracking prompt performance metrics
- Deploying prompt changes to production
- Rolling back problematic prompts

**DO NOT use for:**
- Prompt design patterns (see [prompt-engineering](../prompt-engineering/))
- Context preparation (see [context-engineering](../context-engineering/))
- Domain-specific workflows (see [report-prompt-workflow](../report-prompt-workflow/))

---

## Core Concepts

### Prompt Lifecycle

```
Draft → Development → Staging → Production → Deprecated
  ↑                                              |
  └──────────── Rollback ←───────────────────────┘
```

### Environment Strategy

| Environment | Label | Purpose |
|-------------|-------|---------|
| Development | `dev` | Testing new prompts |
| Staging | `staging` | Pre-production validation |
| Production | `production` | Live traffic |

---

## Quick Reference

### Langfuse SDK Usage

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Get prompt by name and label
prompt = langfuse.get_prompt("dr-report-main", label="production")

# Get specific version
prompt_v2 = langfuse.get_prompt("dr-report-main", version=2)

# Compile with variables
compiled = prompt.compile(ticker=ticker, context=context)
```

### Key Operations

| Operation | When to Use |
|-----------|-------------|
| `get_prompt(name, label)` | Fetch current production prompt |
| `get_prompt(name, version)` | Fetch specific version |
| `prompt.compile(**vars)` | Fill template variables |
| Set label in UI | Promote version to environment |

---

## File Organization

```
.claude/skills/prompt-management/
├── SKILL.md           # This file - entry point
├── VERSIONING.md      # Version management patterns
├── AB-TESTING.md      # A/B testing setup
└── OBSERVABILITY.md   # Metrics and monitoring
```

---

## Current Implementation

```
src/integrations/prompt_service.py   # Langfuse integration
src/report/prompt_builder.py         # Prompt loading and compilation
```

### PromptService Pattern

```python
# src/integrations/prompt_service.py
class PromptService:
    def get_prompt(
        self,
        prompt_name: str,
        label: str | None = None,
        version: int | None = None,
        fallback_path: Path | None = None,
    ) -> PromptResult:
        """
        Fetch prompt from Langfuse with file fallback.

        Priority:
        1. Langfuse (if available and configured)
        2. Local file fallback

        Returns:
            PromptResult with content, source, version metadata
        """
```

---

## References

- [VERSIONING.md](VERSIONING.md) - Version management
- [AB-TESTING.md](AB-TESTING.md) - A/B testing patterns
- [OBSERVABILITY.md](OBSERVABILITY.md) - Metrics and monitoring
- [Langfuse Prompt Management](https://langfuse.com/docs/prompts)
- [src/integrations/prompt_service.py](../../../src/integrations/prompt_service.py)
