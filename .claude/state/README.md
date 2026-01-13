# State Tracking

**Purpose**: Runtime state for specification convergence and checkpoint/recovery.

This directory tracks the current state of specification verification, enabling:
- **Convergence tracking**: How close each spec is to fixed-point (delta = 0)
- **Checkpoint/recovery**: Resume long-running agents at verified states
- **Audit trail**: History of invariant verification

---

## Directory Structure

```
.claude/state/
├── README.md                    # This file
│
├── convergence/                 # Current verification state
│   ├── linebot.yaml            # LINE Bot convergence status
│   ├── telegram.yaml           # Telegram convergence status
│   └── shared.yaml             # Shared components status
│
├── checkpoints/                 # Saved states for recovery
│   ├── {timestamp}-{objective}.yaml
│   └── ...
│
└── history/                     # Verification audit trail
    ├── {date}-{objective}-{env}.md
    └── ...
```

---

## Convergence State Format

Each convergence file tracks:

```yaml
objective: linebot
environment: dev
last_verified: 2026-01-13T10:30:00+07:00
verified_by: Claude

convergence:
  delta: 0  # 0 = fixed-point, >0 = violations exist
  status: converged  # converged | diverging | unknown

levels:
  level_4_config:
    status: passed
    violations: []
    last_checked: 2026-01-13T10:30:00+07:00

  level_3_infra:
    status: passed
    violations: []
    last_checked: 2026-01-13T10:30:00+07:00

  level_2_data:
    status: passed
    violations: []
    last_checked: 2026-01-13T10:30:00+07:00

  level_1_service:
    status: passed
    violations: []
    last_checked: 2026-01-13T10:30:00+07:00

  level_0_user:
    status: passed
    violations: []
    last_checked: 2026-01-13T10:30:00+07:00
```

---

## Checkpoint Format

Checkpoints are saved when:
- All invariants verified (delta = 0)
- Before major changes
- At stable states in long-running tasks

```yaml
checkpoint_id: "20260113-103000-linebot-dev"
created: 2026-01-13T10:30:00+07:00
objective: linebot
environment: dev

state:
  convergence_delta: 0
  all_invariants_passed: true

context:
  task: "Deploy LINE Bot v1.2.3"
  commit: "abc1234"
  notes: "All invariants verified after deployment"

resumable: true
recovery_instructions: |
  To resume from this checkpoint:
  1. Verify environment matches (dev)
  2. Run /invariant linebot dev
  3. If delta > 0, run /reconcile
```

---

## Usage

### Check Convergence Status
```bash
/spec status            # Show all specs
/spec status linebot    # Show LINE Bot status
```

### Update Convergence
```bash
/invariant linebot dev  # Verify and update status
/reconcile linebot      # Fix violations, update status
```

### Create Checkpoint
```bash
/checkpoint linebot     # Save current state
```

### Recover from Checkpoint
```bash
/checkpoint list        # List available checkpoints
/checkpoint restore {id}  # Restore to checkpoint
```

---

## Automated Updates

The convergence state is updated automatically by:
- `/invariant` command (after verification)
- `/reconcile` command (after fixing violations)
- `/deploy` skill (after deployment verification)

Manual updates should not be needed.

---

## Integration with Specs

```
.claude/specs/{objective}/
├── spec.yaml           # What the spec is
├── invariants.md       # What must hold
├── constraints.md      # How to operate
└── acceptance.md       # When it's done

.claude/state/convergence/{objective}.yaml
└── Current verification state (dynamic)
```

Specs define the contract. State tracks compliance with the contract.

---

*Created: 2026-01-13*
*Status: Active - Runtime state tracking*
