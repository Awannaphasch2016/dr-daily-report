# Implementation Guides

Comprehensive how-to guides for implementing CLAUDE.md principles. Each guide provides concrete methods, examples, checklists, and real-world incident analysis.

---

## Principle Implementation Guides

### Testing & Verification

#### [Cross-Boundary Contract Testing](cross-boundary-contract-testing.md)
**Principle #19** | Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within boundaries.

- **Boundary types**: Phase (Build → Runtime), Service (Lambda → Aurora), Data (Python → JSON), Time (23:59 → 00:00)
- **Test pattern template**: Set up boundary conditions → invoke transition → verify contract → clean up
- **5 comprehensive examples**: Docker container testing, Lambda startup validation, API Gateway events, MySQL JSON, date boundaries
- **Boundary identification heuristic**: Map components, list phases, trace transformations, identify time-sensitive ops
- **Real impact**: LINE Bot 7-day outage (ImportError), PDF schema bug

---

#### [Execution Boundary Discipline](execution-boundary-discipline.md)
**Principle #20** | Reading code ≠ Verifying code works. Systematically identify and verify execution boundaries before concluding "code is correct."

- **5 verification questions**: WHERE runs? WHAT environment? WHAT systems? WHAT entity properties? HOW verify?
- **5 layers of correctness**: Syntactic → Semantic → Boundary → Configuration → Intentional
- **Concrete methods**: Docker container testing, Terraform verification, Aurora schema validation
- **Execution boundary checklist**: Process, network, data, deployment boundaries
- **Real impact**: 32 min wasted (3 failed deployments) vs 19 min (systematic verification)

---

### Deployment & Infrastructure

#### [Deployment Blocker Resolution](deployment-blocker-resolution.md)
**Principle #21** | Not all blockers require fixing—bypass safely when evidence supports it, fix systemic issues separately.

- **Decision heuristic**: When to bypass (5 conditions) vs when to fix blocker first (5 conditions)
- **Manual deployment discipline**: Artifact promotion (not rebuild), traceability, same validation as CI/CD
- **Step-by-step decision template**: Classify → assess evidence → check compatibility → choose path → document
- **Manual Lambda deployment workflow**: Complete script with prerequisites, verification, rollback
- **Real example**: Step Functions migration unblocked (15 min manual vs 4+ hours debugging)

---

#### [Infrastructure-Application Contract](infrastructure-application-contract.md)
**Principle #15** | Maintain contract between application code, infrastructure, and principles. Missing Step 3 causes silent failures hours after deployment.

- **Deployment update order**: 9 steps from principle → code → schema → Terraform → secrets → verification
- **Schema migration checklist**: 7 steps to prevent data inconsistencies
- **Startup validation pattern**: Fail fast when critical configuration missing
- **Pre-deployment validation script**: Automated contract verification
- **4 real failure instances**: Missing CACHE_TABLE_NAME (2+ hour debug), TZ timezone bug, Langfuse graceful degradation, copy-paste inheritance

---

### Development Environment

#### [Shared Virtual Environment](shared-virtual-environment.md)
**Principle #17** | Four-repository ecosystem shares single venv via symlink—eliminates version conflicts, saves 75% disk space.

- **Project structure**: Parent venv (500MB actual) → sibling symlinks (0KB each)
- **Setup workflow**: Verify symlink → activate → verify CLI → fallback if broken
- **Common scenarios**: Installing packages, updating requirements, broken symlinks, CI/CD integration
- **Benefits**: Consistency (identical versions), disk efficiency (75% savings), simplicity (one venv), speed (updates immediate)
- **Related pattern**: Doppler config inheritance (Principle #13)

---

## When to Use These Guides

### Before Deployment
1. **Cross-Boundary Contract Testing**: Validate phase boundaries (Docker container tests)
2. **Execution Boundary Discipline**: Verify WHERE code runs and WHAT it needs
3. **Infrastructure-Application Contract**: Run pre-deployment validation script
4. **Deployment Blocker Resolution**: If pipeline blocked, apply decision heuristic

### During Development
1. **Shared Virtual Environment**: Set up symlinked venv for dependency consistency
2. **Cross-Boundary Contract Testing**: Write boundary tests for service integrations
3. **Execution Boundary Discipline**: Apply 5-question checklist before claiming "code works"

### When Debugging
1. **Execution Boundary Discipline**: "Code looks correct but doesn't work" → identify boundaries
2. **Infrastructure-Application Contract**: Check env vars, schema, permissions match code
3. **Cross-Boundary Contract Testing**: Add boundary tests to prevent regression
4. **Deployment Blocker Resolution**: Pipeline blocked → bypass unrelated blocker, fix separately

---

## Guide Structure

Each guide follows consistent structure:

### 1. Overview
- Principle number and statement
- Core problem and insight
- Category and related abstractions

### 2. Core Content
- Concrete methods and patterns
- Step-by-step workflows
- Code examples and templates
- Checklists and verification steps

### 3. Anti-Patterns
- Common mistakes
- Why they fail
- Correct alternatives

### 4. Real-World Impact
- Actual incidents prevented/caused
- Time/cost savings
- Before/after comparisons

### 5. Integration
- Related principles
- When to apply
- Rationale and benefits

### 6. References
- Abstraction files
- Skills and checklists
- Related documentation

---

## Relationship to CLAUDE.md

**CLAUDE.md** (Principles): WHY and WHEN
- Goldilocks Zone of abstraction
- Principles guide behavior
- 8-15 lines per principle
- Links to implementation guides

**docs/guides/** (Implementation): HOW
- Comprehensive how-to guides
- Concrete methods and examples
- Detailed workflows and checklists
- Real-world incident analysis

**Pattern**: Principle → Abstraction → Implementation Guide

---

## Graduation Path

Patterns become implementation guides through this path:

1. **Observe pattern** (repeated instances)
2. **Document abstraction** (`.claude/abstractions/`)
3. **Graduate to principle** (add to CLAUDE.md)
4. **Create implementation guide** (extract details to `docs/guides/`)
5. **Trim principle** (keep 8-15 lines, link to guide)

**Result**: CLAUDE.md stays concise (300 lines), guides provide depth

---

## Version History

- **2026-01-04**: Initial guides created during CLAUDE.md abstraction refactoring
  - Cross-Boundary Contract Testing (Principle #19)
  - Execution Boundary Discipline (Principle #20)
  - Deployment Blocker Resolution (Principle #21)
  - Infrastructure-Application Contract (Principle #15)
  - Shared Virtual Environment (Principle #17)

---

## See Also

- **CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md) - Core principles (WHY/WHEN)
- **Abstractions**: [.claude/abstractions/](.claude/abstractions/) - Pattern analysis and graduation path
- **Skills**: [.claude/skills/](.claude/skills/) - Executable workflows and checklists
- **Documentation Index**: [docs/README.md](../README.md) - Complete documentation map

---

*Index version: 2026-01-04*
*Guides: 5 implementation guides (Principles #15, #17, #19, #20, #21)*
*Status: Active - guides referenced by CLAUDE.md principles*
