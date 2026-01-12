# Behavioral Invariants

This directory contains invariant checklists for implementations and deployments.

## Purpose

Invariant checklists make implicit assumptions explicit. Before claiming "implementation complete", verify the invariant envelope holds.

## Directory Structure

```
.claude/invariants/
├── README.md                          # This file
├── TEMPLATE.md                        # Checklist template
├── system-invariants.md               # Project-wide invariants (always verify)
└── {date}-{slug}.md                   # Per-implementation checklists
```

## Usage

### For New Implementations

1. Copy `TEMPLATE.md` to `{date}-{slug}.md`
2. Fill in the invariant envelope before implementing
3. Verify each invariant after implementing
4. Reference the completed checklist in your "done" claim

### For Deployments

1. Reference `system-invariants.md` for critical path verification
2. Add implementation-specific invariants from your checklist
3. Verify bottom-up (Level 4 → Level 0)

## See Also

- [CLAUDE.md - Principle #25](../CLAUDE.md)
- [Behavioral Invariant Guide](../../docs/guides/behavioral-invariant-verification.md)
