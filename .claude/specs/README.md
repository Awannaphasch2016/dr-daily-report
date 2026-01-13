# Knowledge Substrate: Specifications

**Purpose**: Spec-driven knowledge substrate for long-running agents with checkpoint and error recovery.

Each specification defines a complete contract for one objective, enabling:
- **Specification-driven development**: Query spec before implementing
- **Fixed-point convergence**: Verify invariants until delta = 0
- **Checkpoint/recovery**: Resume at verified state
- **Environment awareness**: Different constraints per environment

---

## Directory Structure

```
.claude/specs/
├── README.md                    # This file
│
├── linebot/                     # LINE Bot Objective
│   ├── spec.yaml               # Metadata, dependencies, owner
│   ├── invariants.md           # Behavioral contracts (5 levels)
│   ├── constraints.md          # Learned restrictions
│   └── acceptance.md           # "Done" criteria
│
├── telegram/                    # Telegram Mini App Objective
│   ├── spec.yaml
│   ├── invariants.md
│   ├── constraints.md
│   └── acceptance.md
│
├── shared/                      # Cross-Cutting Specifications
│   ├── aurora/                 # Data layer
│   ├── langfuse/               # Observability
│   └── deployment/             # CI/CD
│
└── environments/                # Environment-Specific Constraints
    ├── local.yaml              # Local dev (mocks allowed)
    ├── dev.yaml                # AWS dev (real APIs, relaxed SLAs)
    ├── stg.yaml                # AWS staging (real APIs, monitored)
    └── prd.yaml                # AWS production (real APIs + SLAs enforced)
```

---

## Core Concepts

### Specification
A complete contract for one objective containing:
- **Invariants**: What MUST hold (behavioral contracts)
- **Constraints**: What we've LEARNED (restrictions from experience)
- **Acceptance Criteria**: How to verify "done"

### Invariant Levels
| Level | Type | What to Verify |
|-------|------|----------------|
| 4 | Configuration | Env vars, constants |
| 3 | Infrastructure | Connectivity, permissions |
| 2 | Data | Schema, freshness |
| 1 | Service | API contracts, responses |
| 0 | User | End-to-end experience |

### Environment Overlays
Same specification, different constraints:
- **local**: Mocks allowed, no SLAs (development machine)
- **dev**: Real APIs, relaxed SLAs (AWS dev)
- **stg**: Real APIs, monitored SLAs (AWS staging)
- **prd**: Real APIs + enforced SLAs (AWS production)

---

## Usage

### Load Specification
```bash
/spec linebot           # View LINE Bot specification
/spec telegram dev      # View Telegram spec with dev constraints
/spec status            # Show convergence status for all specs
```

### Verify Invariants
```bash
/invariant linebot stg  # Check LINE Bot invariants in staging
/reconcile linebot      # Generate fixes for violations
```

### Track Convergence
```bash
/spec check linebot     # Run invariant check, update convergence
/spec history           # Show convergence history
```

---

## Fixed-Point Convergence

The goal is reaching a **fixed-point** where all invariants are satisfied:

```
START: δ > 0 (violations exist)
    │
    ├── /invariant → detect violations
    │
    ├── /reconcile → generate fixes
    │
    ├── Apply fixes
    │
    ├── /invariant → verify fixes
    │
    └── IF δ = 0: FIXED-POINT REACHED ✅
        ELSE: Loop back
```

**Error bound**: With spec verification, error ∝ check frequency, not steps × drift.

---

## Checkpoint & Recovery

For long-running agents, specs enable safe restart:

1. **Checkpoint**: Save progress + convergence state
2. **Failure**: Agent can fail at any point
3. **Recovery**: Resume from last checkpoint
4. **Verification**: Re-verify invariants before continuing

See `.claude/state/checkpoints/` for checkpoint storage.

---

## Relationship to Existing Files

| Existing | Relationship | Migration Path |
|----------|--------------|----------------|
| `.claude/invariants/` | Organized by domain | Keep for backward compat, specs reference |
| `.claude/principles/` | Orthogonal (task-based) | Principles guide HOW, specs define WHAT |
| `CLAUDE.md` | Core principles | Principle #25 defines invariant framework |
| `.claude/state/` | Runtime state | Convergence tracking |

---

## Creating New Specifications

1. Create directory: `.claude/specs/{objective}/`
2. Copy templates from existing specs
3. Define invariants (5 levels)
4. Document known constraints
5. Write acceptance criteria
6. Register in this README

---

*Created: 2026-01-13*
*Status: Active - Spec-driven development substrate*
