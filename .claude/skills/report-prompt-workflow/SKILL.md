---
name: report-prompt-workflow
description: Composed workflow for DR report prompt engineering, context building, and management
tier: 2
depends:
  - prompt-engineering
  - context-engineering
  - prompt-management
---

# Report Prompt Workflow Skill

**Focus**: Domain-specific workflow for DR (Daily Report) prompt lifecycle.

**Tier**: 2 (Composed from Tier-1 skills)

---

## Dependencies

This skill composes patterns from:

| Tier-1 Skill | What It Provides |
|--------------|------------------|
| [prompt-engineering](../prompt-engineering/) | Prompt design patterns |
| [context-engineering](../context-engineering/) | Semantic layer, token optimization |
| [prompt-management](../prompt-management/) | Langfuse versioning, A/B testing |

---

## When to Use This Skill

Use report-prompt-workflow when:
- Modifying DR report prompts
- Adding new data sections to reports
- Debugging report generation issues
- Optimizing report quality or performance
- Setting up A/B tests for report prompts

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DR Report Generation                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │   Aurora    │ → │  Semantic   │ → │   Context   │       │
│  │   Data      │   │   Layer     │   │   Builder   │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│         ↓                 ↓                 ↓               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Prompt Builder                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ Langfuse │→ │ Template │→ │ Compiled │          │   │
│  │  │ Fetch    │  │ Load     │  │ Prompt   │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│         ↓                                                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │    LLM      │ → │   Number    │ → │   Final     │       │
│  │   Call      │   │   Injector  │   │   Report    │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Organization

```
.claude/skills/report-prompt-workflow/
├── SKILL.md           # This file - entry point
├── WORKFLOW.md        # Step-by-step workflow guide
└── CHECKLIST.md       # Pre-deployment checklist
```

---

## Quick Reference

### Key Files

| File | Purpose |
|------|---------|
| `src/report/report_generator_simple.py` | Orchestration entry point |
| `src/report/prompt_builder.py` | Prompt loading and compilation |
| `src/report/context_builder.py` | Semantic context assembly |
| `src/report/number_injector.py` | Post-processing value injection |
| `src/analysis/semantic_state_generator.py` | Numeric → semantic conversion |
| `src/integrations/prompt_service.py` | Langfuse integration |

### Prompt Template

```
src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt
```

### Langfuse Prompt Name

```
dr-report-main
```

---

## Common Tasks

### Task 1: Modify Prompt Template

1. Read [WORKFLOW.md](WORKFLOW.md) for step-by-step guide
2. Apply [prompt-engineering](../prompt-engineering/) patterns
3. Test locally with file fallback
4. Deploy to Langfuse (dev → staging → production)

### Task 2: Add New Data Section

1. Add calculation in `src/analysis/` (Layer 1)
2. Add semantic classification (Layer 2)
3. Update `context_builder.py` (Layer 3)
4. Add placeholder in `number_injector.py` (Layer 4)
5. Update prompt template

### Task 3: Debug Poor Output

1. Check [CHECKLIST.md](CHECKLIST.md) items
2. Apply [context-engineering](../context-engineering/) diagnostics
3. Review Langfuse traces for patterns
4. Verify all placeholders replaced

### Task 4: A/B Test Prompt Change

1. Follow [prompt-management/AB-TESTING.md](../prompt-management/AB-TESTING.md)
2. Create variant in Langfuse
3. Assign labels (prod-a, prod-b)
4. Monitor metrics in Langfuse

---

## References

- [WORKFLOW.md](WORKFLOW.md) - Detailed workflow guide
- [CHECKLIST.md](CHECKLIST.md) - Pre-deployment checklist
- [.claude/reports/2026-01-15-prompt-construction-architecture.md](../../reports/2026-01-15-prompt-construction-architecture.md) - Architecture documentation
