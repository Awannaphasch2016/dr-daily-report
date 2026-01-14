# Implementation Guides

Comprehensive how-to guides for implementing CLAUDE.md principles. Each guide provides concrete methods, examples, checklists, and real-world incident analysis.

---

## Principle Implementation Guides

### Testing & Verification

#### [Thinking Tuple Protocol](thinking-tuple-protocol.md)
**Principle #26** | The atomic unit of disciplined reasoning that forces composition of all layers at each reasoning step.

- **Tuple structure**: (Constraints, Invariant, Principles, Process, Actions, Check)
- **Layer integration**: Principles → Constraints slot, Skills → Actions slot, Thinking Arch → Process slot
- **Process modes**: diverge, converge, decompose, compare, reframe, escape
- **Error bound**: Without tuples, error ∝ (steps × drift). With tuples, error bounded by check frequency
- **Checkpoint semantics**: Each tuple is a checkpoint. If Check fails, spin new tuple with updated Constraints

---

#### [Behavioral Invariant Verification](behavioral-invariant-verification.md)
**Principle #25** | Every implementation operates within an invariant envelope—behaviors that MUST remain true for the system to function.

- **Invariant hierarchy**: Level 0 (User) → Level 1 (Service) → Level 2 (Data) → Level 3 (Infrastructure) → Level 4 (Configuration)
- **Implementation workflow**: State invariants (before) → implement → verify invariants (after)
- **Claiming "Done"**: Requires explicit invariant verification, not just "code deployed"
- **Verification strength**: Critical invariants require Layer 4 (ground truth) verification
- **Real impact**: LINE bot 7-day outage, ETL timezone bug, NAT Gateway timeout (all implicit invariants)

---

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

### External Service Integration

#### [External Service Credential Isolation](external-service-credential-isolation.md)
**Principle #24** | External services with webhook-based integrations require per-environment credentials.

- **Pattern**: LINE, Telegram, Slack webhooks are per-channel—cannot share credentials across environments
- **Isolation checklist**: Create channel → generate credentials → configure webhook → store in Doppler → verify E2E
- **Verification**: HTTP 200 is insufficient—must verify user receives message (ground truth)
- **Real incident**: LINE staging "account cannot reply" (used dev credentials for staging)
- **Related**: Contextual Transfer Framework (separating portable vs context-bound)

---

### Logging & Observability

#### [Logging Discipline](logging-discipline.md)
**Principle #18** | Log for narrative reconstruction, not just event recording.

- **Log level semantics**: ERROR (what failed), WARNING (what's unexpected), INFO (what happened), DEBUG (how it happened)
- **Narrative structure**: Beginning (context) → Middle (milestones) → End (outcome with symbols)
- **Boundary logging strategy**: WHERE you log determines WHAT survives Lambda failures
- **Visual scanability**: Status symbols (✅⚠️❌), chapter separators, correlation IDs
- **Critical insight**: Execution time shows WHAT system waits for, not WHERE code hangs

---

### Configuration & Environment

#### [Configuration Variation Axis](configuration-variation.md)
**Principle #23** | Choose configuration mechanism based on WHAT varies and WHEN it varies.

- **Decision tree**: Secret → Doppler | Environment-specific → Doppler | Per-deployment → CI/CD | Complex → JSON | Static → Constant
- **Doppler as isolation container**: Each environment is isolated with complete configuration set
- **Flow patterns**: Doppler → Terraform (via TF_VAR_), CI/CD → Lambda (direct update)
- **One-path execution**: Read env vars ONCE at startup (singleton pattern)
- **Anti-patterns**: Hardcoding secrets, duplicating config, reading env vars per request

#### [Timezone Discipline](timezone-discipline.md)
**Principle #16** | Use Bangkok timezone (Asia/Bangkok, UTC+7) consistently across all system components.

- **Infrastructure configuration**: Aurora, Lambda, EventBridge all use Bangkok timezone
- **Code pattern**: Always use explicit `datetime.now(ZoneInfo("Asia/Bangkok"))`
- **Date boundary handling**: Prevents cache misses at UTC/Bangkok date boundaries
- **Anti-patterns**: Using `datetime.utcnow()`, missing TZ env var, implicit timezone
- **Real incident**: Cache miss at date boundary (21:00 UTC Dec 30 ≠ 04:00 Bangkok Dec 31)

---

## When to Use These Guides

### Before Starting Any Guide: Surface Knowledge Gaps

Before diving into implementation, use `/qna` to surface what you know, assume, and don't know:

```bash
/qna "deployment pipeline" deep
```

This reveals:
- **Confident knowledge**: Facts from code/docs
- **Assumptions**: Inferred beliefs that might be wrong
- **Knowledge gaps**: Missing information that could block you

**Why this matters**: Many guide failures happen because implementers have incorrect assumptions. `/qna` surfaces them BEFORE you start, enabling user correction.

**See**: [/qna command](../../.claude/commands/qna.md), [Thinking Tuple Constraints](thinking-tuple-protocol.md#1-constraints-start-state)

---

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

### When Stuck (Same Error Repeatedly)
1. **Use `/qna`**: Surface your assumptions about the problem
2. **User Verification**: Get user to correct incorrect beliefs
3. **Regenerate Hypotheses**: With corrected knowledge, try again

This is the Initial-Sensitive Loop escalation pattern—see [Thinking Process Architecture](../../.claude/diagrams/thinking-process-architecture.md#2-initial-sensitive-loop-double-loop-learning).

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

## Relationship to CLAUDE.md and Principle Clusters

### New Tiered Architecture (2026-01-12)

Principles are now organized by **applicability tier**:

```
CLAUDE.md (~156 lines)
├── Tier-0: Core Principles (ALWAYS apply)
│   └── #1, #2, #18, #20, #23, #25
└── Routing Index → principle clusters

.claude/principles/ (context-specific)
├── deployment-principles.md (#6, #11, #15, #19, #21)
├── testing-principles.md (#10, #19)
├── data-principles.md (#3, #5, #14, #16)
├── configuration-principles.md (#13, #24)
├── integration-principles.md (#4, #7, #8, #22)
└── meta-principles.md (#9, #12, #17)
```

**Benefits**:
- **Token efficiency**: ~60% reduction (load only relevant clusters)
- **High discoverability**: Routing index guides to relevant principles
- **High connascence**: Related principles grouped together
- **Separation of concerns**: Core vs context-specific

### Document Purposes

| Document | Purpose | Content Level |
|----------|---------|---------------|
| **CLAUDE.md** | Core principles | WHY + condensed WHAT |
| **Principle Clusters** | Task-specific principles | Full principle text |
| **Implementation Guides** | Deep how-to | HOW + examples + incidents |
| **Skills** | Executable workflows | Checklists + patterns |

**Pattern**: Principle (tier-0/cluster) → Implementation Guide → Skill

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

- **2026-01-13**: Thinking Tuple Protocol - Runtime composition protocol for disciplined reasoning
  - Added Principle #26 (Thinking Tuple Protocol) to CLAUDE.md Tier-0
  - Created `/step` command for explicit tuple instantiation
  - Added Section 12 (Thinking Tuple Protocol) to Thinking Process Architecture
  - Created thinking-tuple-protocol.md implementation guide
  - Tuple = (Constraints, Invariant, Principles, Process, Actions, Check)
- **2026-01-13**: Thinking Process Architecture update - Added Invariant Feedback Loop
  - Added Section 11.5 (Invariant Feedback Loop) to Thinking Process Architecture
  - Added Verification Commands (/invariant, /reconcile) to command composition
  - Updated Full Thinking Cycle to include invariant verification after implementation
  - Added new knowledge outputs (.claude/invariants/, .claude/reports/, .claude/what-if/)
  - Updated behavioral-invariant-verification.md with link to Section 11.5
- **2026-01-12**: Major architecture refactor - Principle Classification & Documentation Architecture
  - Introduced tier-based principle classification (Tier-0 core vs Tier-1/2/3 context-specific)
  - Created `.claude/principles/` directory with 6 connascent clusters
  - Reduced CLAUDE.md from 301 lines to 156 lines (~48% reduction)
  - Added routing index for context-based principle loading
  - Token efficiency: ~60% savings by loading only relevant clusters
- **2026-01-12**: Added Behavioral Invariant Verification guide (Principle #25)
  - New principle addressing implicit assumptions in "done" claims
  - Created invariant hierarchy (Levels 0-4)
  - Added `.claude/invariants/` directory with templates
- **2026-01-12**: Added guides during CLAUDE.md abstraction level refactoring
  - Logging Discipline (Principle #18) - extracted from CLAUDE.md
  - Configuration Variation Axis (Principle #23) - extracted from CLAUDE.md
  - Timezone Discipline (Principle #16) - extracted from CLAUDE.md
- **2026-01-11**: Added External Service Credential Isolation guide (Principle #24)
  - Derived from LINE staging deployment incident
  - Integrated with Contextual Transfer Framework
- **2026-01-04**: Initial guides created during CLAUDE.md abstraction refactoring
  - Cross-Boundary Contract Testing (Principle #19)
  - Execution Boundary Discipline (Principle #20)
  - Deployment Blocker Resolution (Principle #21)
  - Infrastructure-Application Contract (Principle #15)
  - Shared Virtual Environment (Principle #17)

---

## See Also

- **CLAUDE.md**: [../../.claude/CLAUDE.md](../../.claude/CLAUDE.md) - Tier-0 core principles + routing index
- **Principle Clusters**: [../../.claude/principles/](../../.claude/principles/) - Context-specific principle clusters
- **Abstractions**: [../../.claude/abstractions/](../../.claude/abstractions/) - Pattern analysis and graduation path
- **Skills**: [../../.claude/skills/](../../.claude/skills/) - Executable workflows and checklists
- **Invariants**: [../../.claude/invariants/](../../.claude/invariants/) - System invariant checklists
- **Documentation Index**: [../README.md](../README.md) - Complete documentation map

---

*Index version: 2026-01-13*
*Guides: 11 implementation guides (Principles #15, #16, #17, #18, #19, #20, #21, #23, #24, #25, #26)*
*Status: Active - guides referenced by CLAUDE.md principles*
