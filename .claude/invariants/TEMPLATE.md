# Invariant Checklist: {Feature/Change Name}

**Date**: {YYYY-MM-DD}
**Author**: Claude
**Scope**: {Brief description of what's being implemented}

---

## Pre-Implementation

### Invariant Envelope

**What I'm changing**:
{Detailed description of the change}

**What could break**:
{List of things this change could affect}

---

### Level 0 (User-Facing)
- [ ] {User behavior that must continue working}
- [ ] {Another user behavior}

### Level 1 (Service)
- [ ] {Lambda/API behavior that must work}
- [ ] {Another service behavior}

### Level 2 (Data)
- [ ] {Data condition that must hold}
- [ ] {Another data condition}

### Level 3 (Infrastructure)
- [ ] {Connectivity/resource that must work}
- [ ] {Another infrastructure condition}

### Level 4 (Configuration)
- [ ] {Env var/config that must be set}
- [ ] {Another configuration}

---

### Assumptions
- {Assumption 1 - something I'm taking for granted}
- {Assumption 2}

---

## Post-Implementation

### Verification Results

**Level 4 (Configuration)**:
- [ ] {Check}: {Actual result}
  - Evidence: {command/output}

**Level 3 (Infrastructure)**:
- [ ] {Check}: {Actual result}
  - Evidence: {command/output}

**Level 2 (Data)**:
- [ ] {Check}: {Actual result}
  - Evidence: {command/output}

**Level 1 (Service)**:
- [ ] {Check}: {Actual result}
  - Evidence: {command/output}

**Level 0 (User)**:
- [ ] {Check}: {Actual result}
  - Evidence: {screenshot/confirmation}

---

## Summary

**Implementation complete**: {timestamp}

**Invariants verified**: {X}/{Y}

**Verification evidence**:
- {Link to logs}
- {Link to screenshot}

**Confidence**:
- [ ] HIGH: All levels verified to Layer 4
- [ ] MEDIUM: Critical levels verified to Layer 3
- [ ] LOW: Partial verification only

**Notes**:
{Any observations, caveats, or follow-up items}
