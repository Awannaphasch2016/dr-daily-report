# Adaptations

This directory contains adaptation documents tracking the integration of external techniques into this codebase.

## What is an Adaptation?

An adaptation is the process of taking techniques, patterns, or algorithms from external sources (libraries, repos, experiments) and implementing them in a way that:
- Follows local codebase conventions (CLAUDE.md principles)
- Preserves the core technique's value
- Creates truly native code (not copied foreign code)
- Documents decisions for future maintainers

## Directory Structure

```
adaptations/
├── README.md                              # This file
├── {date}-{slug}.md                       # Adaptation documents
└── ...
```

## Adaptation Document Naming

Format: `{YYYY-MM-DD}-{descriptive-slug}.md`

Examples:
- `2026-01-05-stock-pattern-integration.md`
- `2026-01-10-oauth2-flow.md`
- `2026-01-15-pdf-optimization.md`

## Creating an Adaptation

Use the `/adapt` command:

```bash
/adapt "source" "goal"

# Examples:
/adapt "stock-pattern library" "chart pattern detection"
/adapt "https://github.com/user/repo" "authentication flow"
/adapt "experiment-branch" "PDF improvements"
```

## Six-Phase Workflow

1. **Study** - Understand the source
2. **Map** - Map concepts to local equivalents
3. **Design** - Design local implementation
4. **Implement** - Build using local patterns
5. **Verify** - Test functionality preserved
6. **Document** - Record decisions and learnings

## Status Values

| Status | Meaning |
|--------|---------|
| `planning` | Phases 1-3 (Study, Map, Design) |
| `in_progress` | Phases 4-5 (Implement, Verify) |
| `complete` | All phases done |
| `abandoned` | Decided not to proceed (document why) |

## After Adaptation

Consider:
- `/abstract` - Extract reusable patterns from this adaptation
- `/evolve` - Update CLAUDE.md if significant learning
- `/journal` - Record insights for future reference

## Index

<!-- Keep this list updated as adaptations are added -->

| Date | Adaptation | Source | Status |
|------|------------|--------|--------|
| - | - | - | - |

## Related

- `.claude/commands/adapt.md` - The adapt command
- `.claude/research/` - Research documents (pre-adaptation analysis)
- `.claude/abstractions/` - Patterns extracted from adaptations
