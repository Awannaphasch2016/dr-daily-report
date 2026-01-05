# Proposed Updates to Thinking Process Architecture

**Date**: 2026-01-04
**Changes**: Add 3-tier decision classification and principle-first workflow

---

## Summary of Changes

### 1. New Section: Decision Tiers and Principle Checking

Add new section after "## 5. Full Thinking Cycle (Decision Making)" explaining the 3-tier decision classification.

### 2. Updated Section 5: Full Thinking Cycle (Decision Making)

Replace current flowchart with updated version that includes `/check-principles` gates for strategic decisions.

### 3. Updated Section 10: Cognitive Assistance Model

Add "CHECK PRINCIPLES" node to DECIDE branch showing when principle checking is enforced.

---

## New Section to Add (Insert after Section 5)

```markdown
## 5.1 Decision Tiers and Principle Checking

Not all decisions require the same rigor. Claude classifies decisions into three tiers based on impact, reversibility, and scope.

### Three Decision Tiers

```mermaid
graph TB
    subgraph "Tier 1: STRATEGIC Decisions"
        S1[Deployments]
        S2[Architecture]
        S3[Technology Selection]
        S4[Process Changes]

        S1 -.->|MUST| PC1["/check-principles<br/>DEPLOYMENT"]
        S2 -.->|MUST| PC2["/check-principles<br/>ARCHITECTURE"]
        S3 -.->|MUST| PC3["/check-principles<br/>DECISION"]
        S4 -.->|MUST| PC4["/check-principles<br/>ARCHITECTURE"]
    end

    subgraph "Tier 2: ANALYTICAL Decisions"
        A1[Refactoring]
        A2[Code Review]
        A3[Test Strategy]
        A4[Code Organization]

        A1 -.->|SHOULD| REF1[Reference principles<br/>in analysis]
        A2 -.->|SHOULD| REF2[Reference principles<br/>in analysis]
        A3 -.->|SHOULD| REF3[Reference principles<br/>in analysis]
        A4 -.->|SHOULD| REF4[Reference principles<br/>in analysis]
    end

    subgraph "Tier 3: TACTICAL/RESEARCH Decisions"
        T1[File Naming]
        T2[Variable Naming]
        T3[Exploration]
        T4[Debugging]

        T1 -.->|NO CHECK| SKIP1[Fast iteration]
        T2 -.->|NO CHECK| SKIP2[Fast iteration]
        T3 -.->|NO CHECK| SKIP3[Fast iteration]
        T4 -.->|NO CHECK| SKIP4[Fast iteration]
    end

    style S1 fill:#dc3545,color:#fff
    style S2 fill:#dc3545,color:#fff
    style S3 fill:#dc3545,color:#fff
    style S4 fill:#dc3545,color:#fff

    style A1 fill:#ffc107
    style A2 fill:#ffc107
    style A3 fill:#ffc107
    style A4 fill:#ffc107

    style T1 fill:#28a745,color:#fff
    style T2 fill:#28a745,color:#fff
    style T3 fill:#28a745,color:#fff
    style T4 fill:#28a745,color:#fff

    style PC1 fill:#e1e5f5
    style PC2 fill:#e1e5f5
    style PC3 fill:#e1e5f5
    style PC4 fill:#e1e5f5
```

### Tier 1: STRATEGIC Decisions (MUST check principles)

**Characteristics**:
- High impact (affects system architecture, infrastructure, operations)
- Long-term consequences (difficult/expensive to reverse)
- Multi-stakeholder (affects team, users, infrastructure)
- Risk of principle violation causes major issues

**Commands that enforce principle checking**:
- `/deploy` - Already enforces `/check-principles DEPLOYMENT`
- `/architect` - Should enforce `/check-principles ARCHITECTURE`
- `/problem-statement` - Should include principle compliance matrix

**Why enforcement matters**:
- Prevents deployment failures (Principle #15: Infrastructure-Application Contract)
- Ensures monitoring discipline (Principle #6: Deployment Monitoring Discipline)
- Validates boundary testing (Principle #19: Cross-Boundary Contract Testing)
- Checks artifact promotion (Principle #11: Artifact Promotion Principle)

**Workflow**:
```
Strategic Decision Detected
    ↓
/check-principles {scope}
    ↓
Audit relevant principles
    ↓
If CRITICAL violations → BLOCK decision, show required fixes
    ↓
If clear → Proceed with analysis and decision-making
```

---

### Tier 2: ANALYTICAL Decisions (SHOULD reference principles)

**Characteristics**:
- Medium impact (affects code quality, performance, maintainability)
- Reversible (can change approach without major cost)
- Developer-facing (affects how we write code, not what system does)
- Principle violations create technical debt, not system failures

**Commands that reference principles**:
- `/what-if` - Include principle alignment in comparison
- `code-review` skill - Check patterns against principles
- `/restructure` - Reference relevant principles in recommendations

**Why reference matters**:
- Ensures defensive programming (Principle #1: Fail fast and visible)
- Validates error handling (Principle #8: Error Handling Duality)
- Checks logging patterns (Principle #18: Logging Discipline)
- Verifies test quality (Principle #10: Testing Anti-Patterns Awareness)

**Workflow**:
```
Analytical Decision
    ↓
Perform analysis
    ↓
Include principle alignment in framework
    ↓
Present options with principle considerations
    ↓
User makes decision (not blocked on violations)
```

---

### Tier 3: TACTICAL/RESEARCH Decisions (NO principle check)

**Characteristics**:
- Low impact (local changes, exploratory work)
- Highly reversible (git revert, quick iteration)
- Learning/discovery phase (don't know what decision is yet)
- Principle violations caught in code review or testing

**Commands that skip principle checking**:
- `/explore` - Research phase, no decision yet
- `/research` skill - Investigation, not decision-making
- `/trace` - Debugging, focused on root cause
- `/hypothesis` - Hypothesis generation, exploration

**Why no check needed**:
- Decision scope too small to violate principles
- Enforcement adds friction without benefit
- Code review catches issues later
- Slows iteration during learning/debugging

**Workflow**:
```
Tactical/Research Decision
    ↓
Fast iteration (no gate)
    ↓
Code review catches violations (if any)
```

---

### Decision Tier Classification Heuristic

**When Claude encounters a decision**, classify using:

| Criterion | Strategic | Analytical | Tactical |
|-----------|-----------|------------|----------|
| **Impact** | System-wide | Module-level | Local |
| **Reversibility** | Expensive | Moderate | Cheap |
| **Scope** | Multi-component | Single component | File/function |
| **Duration** | Long-term | Medium-term | Short-term |
| **Stakeholders** | Team + users | Developers | Individual |

**Examples by tier**:

| Decision | Tier | Reason |
|----------|------|--------|
| "Deploy Lambda timeout increase" | STRATEGIC | Infrastructure change, affects reliability |
| "Choose Redis vs DynamoDB" | STRATEGIC | Technology selection, long-term commitment |
| "Refactor this function" | ANALYTICAL | Code quality, reversible |
| "Name this variable" | TACTICAL | Local scope, trivial to change |
| "Explore authentication patterns" | TACTICAL | Research, no decision yet |

---

### Integration with Existing Workflow

**Current workflow** (Section 5):
```
Problem → Decompose → Explore → Specify → Validate → Implement
```

**Updated workflow** (with principle checking):
```
Problem
    ↓
Classify Decision Tier
    ↓
If STRATEGIC → /check-principles {scope}
    ↓
If ANALYTICAL → Reference principles in analysis
    ↓
If TACTICAL → Skip principle check
    ↓
Decompose → Explore → Specify → Validate → Implement
```

---
```

## Updated Section 5: Full Thinking Cycle (Decision Making)

Replace current Section 5 content with:

```markdown
## 5. Full Thinking Cycle (Decision Making with Principle Checking)

```mermaid
flowchart TD
    START[Problem/Question] --> CLASSIFY{Classify<br/>Decision Tier}

    CLASSIFY -->|STRATEGIC| CHECK_PRINCIPLES["/check-principles<br/>{scope}"]
    CLASSIFY -->|ANALYTICAL| UNDERSTAND
    CLASSIFY -->|TACTICAL| UNDERSTAND

    CHECK_PRINCIPLES --> VIOLATIONS{CRITICAL<br/>violations?}
    VIOLATIONS -->|Yes| BLOCK[BLOCK Decision<br/>Show required fixes]
    VIOLATIONS -->|No| UNDERSTAND[Understand Context]

    BLOCK --> FIX_VIOLATIONS[Fix Violations]
    FIX_VIOLATIONS --> CHECK_PRINCIPLES

    UNDERSTAND --> CMD_DECOMPOSE["/decompose<br/>Break down problem"]
    CMD_DECOMPOSE -.->|Uses| SKILL_RESEARCH[research skill<br/>systematic analysis]

    CMD_DECOMPOSE --> CMD_EXPLORE["/explore<br/>Find all solutions"]
    CMD_EXPLORE -.->|Uses| SKILL_RESEARCH

    CMD_EXPLORE --> EVAL{Multiple<br/>good options?}

    EVAL -->|Yes| CMD_WHATIF["/what-if<br/>Compare alternatives"]
    EVAL -->|No| CMD_SPECIFY

    CMD_WHATIF -.->|Binary| BINARY["Scenario analysis<br/>X instead of Y"]
    CMD_WHATIF -.->|Multi-way| MULTIWAY["Evaluation matrix<br/>Compare X vs Y vs Z"]
    CMD_WHATIF -.->|Relationship| RELATE["Relationship analysis<br/>How do X and Y relate"]

    CMD_WHATIF -.->|ANALYTICAL tier| REF_PRINCIPLES[Include principle<br/>alignment in comparison]
    REF_PRINCIPLES --> CMD_WHATIF

    CMD_WHATIF --> CMD_SPECIFY["/specify<br/>Detail chosen approach"]
    CMD_SPECIFY -.->|Uses| SKILL_CODEREVIEW[code-review skill<br/>quality patterns]
    CMD_SPECIFY -.->|Uses| SKILL_API[api-design skill<br/>REST patterns]

    CMD_SPECIFY --> CMD_VALIDATE["/validate<br/>Test assumptions"]
    CMD_VALIDATE -.->|Uses| SKILL_TESTING[testing-workflow skill<br/>test patterns]

    CMD_VALIDATE --> IMPLEMENT[Implement Solution]
    IMPLEMENT -.->|Uses| SKILL_CODEREVIEW
    IMPLEMENT -.->|Uses| SKILL_TESTING
    IMPLEMENT -.->|Uses| SKILL_DEPLOY[deployment skill<br/>zero-downtime]

    IMPLEMENT --> CMD_OBSERVE["/observe<br/>Track execution"]

    CMD_OBSERVE --> WORKED{Success?}

    WORKED -->|Yes| CMD_JOURNAL["/journal<br/>Document decision"]
    WORKED -->|No| CMD_BUGHUNT["/bug-hunt<br/>Investigate failure"]

    CMD_BUGHUNT -.->|Uses| SKILL_ERROR[error-investigation skill<br/>AWS diagnostics]
    CMD_BUGHUNT --> FIX[Fix Issue]
    FIX --> IMPLEMENT

    CMD_JOURNAL --> CMD_ABSTRACT["/abstract<br/>Extract pattern"]
    CMD_ABSTRACT --> EVOLVE["/evolve<br/>Update principles"]

    EVOLVE --> END[Knowledge Base Updated]

    style CHECK_PRINCIPLES fill:#f8d7da
    style BLOCK fill:#dc3545,color:#fff
    style FIX_VIOLATIONS fill:#ffc107
    style CLASSIFY fill:#17a2b8,color:#fff
    style REF_PRINCIPLES fill:#fff3cd

    style CMD_DECOMPOSE fill:#e1e5f5
    style CMD_EXPLORE fill:#e1e5f5
    style CMD_WHATIF fill:#e1e5f5
    style CMD_SPECIFY fill:#e1e5f5
    style CMD_VALIDATE fill:#e1e5f5
    style CMD_OBSERVE fill:#e1e5f5
    style CMD_JOURNAL fill:#e1e5f5
    style CMD_BUGHUNT fill:#e1e5f5
    style CMD_ABSTRACT fill:#e1e5f5

    style SKILL_RESEARCH fill:#e1f5e1
    style SKILL_CODEREVIEW fill:#e1f5e1
    style SKILL_TESTING fill:#e1f5e1
    style SKILL_DEPLOY fill:#e1f5e1
    style SKILL_ERROR fill:#e1f5e1
    style SKILL_API fill:#e1f5e1
```

**Full cycle with principle checking**:
```
Problem
    → Classify Decision Tier (STRATEGIC/ANALYTICAL/TACTICAL)
    → [If STRATEGIC] Check Principles (BLOCK if violations)
    → [If ANALYTICAL] Reference Principles (include in analysis)
    → [If TACTICAL] Skip principle check (fast iteration)
    → Decompose → Explore → Specify → Validate → Implement
    → Observe → Document → Learn
```

**Key changes from previous version**:
1. **Added CLASSIFY node** - Determines decision tier before proceeding
2. **Added CHECK_PRINCIPLES gate** - Enforced for STRATEGIC decisions only
3. **Added BLOCK path** - CRITICAL violations prevent decision progression
4. **Added REF_PRINCIPLES note** - ANALYTICAL decisions include principle alignment
5. **Color coding** - Red (strategic gate), Yellow (analytical reference), Blue (tactical skip)
```

## Updated Section 10: Cognitive Assistance Model

Replace current Section 10 mindmap with:

```markdown
## 10. Cognitive Assistance Model (with Principle Checking)

```mermaid
mindmap
    root((Claude's<br/>Thinking))
        UNDERSTAND[Understand Problem]
            Decompose complexity
            Identify constraints
            Map dependencies
            "/decompose command"
            "research skill"

        CLASSIFY[Classify Decision Tier]
            STRATEGIC (High impact)
            ANALYTICAL (Medium impact)
            TACTICAL (Low impact)

        CHECK_PRINCIPLES[Check Principles]
            "/check-principles command"
            DEPLOYMENT scope
            ARCHITECTURE scope
            DECISION scope
            BLOCK on CRITICAL violations

        EXPLORE[Explore Solutions]
            Generate alternatives
            Evaluate trade-offs
            Rank options
            "/explore command"
            "research skill"

        DECIDE[Make Decisions]
            Compare scenarios
            Validate assumptions
            Reference principles (ANALYTICAL)
            Document rationale
            "/what-if command"
            "/problem-statement command"
            "/validate command"

        DESIGN[Design Solution]
            Specify architecture
            Define interfaces
            Plan implementation
            "/specify command"
            "api-design skill"
            "code-review skill"

        IMPLEMENT[Implement]
            Write code
            Follow patterns
            Ensure quality
            "code-review skill"
            "testing-workflow skill"
            "security-review skill"

        DEPLOY[Deploy]
            Pre-deployment verification
            Zero-downtime
            Verify health
            Monitor metrics
            "/deploy command"
            "deployment skill"
            "monitoring-observability skill"

        LEARN[Learn & Improve]
            Observe outcomes
            Extract patterns
            Update principles
            "/observe command"
            "/journal command"
            "/abstract command"
            "/evolve command"
```

**New nodes**:
- **CLASSIFY**: Decision tier classification (determines if principle checking needed)
- **CHECK_PRINCIPLES**: Principle compliance audit (enforced for STRATEGIC decisions)

**Integration with existing flow**:
```
UNDERSTAND → CLASSIFY → [If STRATEGIC] CHECK_PRINCIPLES → EXPLORE → DECIDE → ...
```
```

---

## Additional Changes

### Update Section Summary

Update the "Summary: How It All Works Together" section to include decision tier classification:

**Before**:
```markdown
### The Full Cycle
\`\`\`
User Problem
    ↓
Commands orchestrate workflow
    ↓
Skills guide methodology
    ↓
System Prompt constrains decisions
    ↓
Tools execute actions
    ↓
Outputs generated
    ↓
Feedback updates knowledge base
\`\`\`
```

**After**:
```markdown
### The Full Cycle (with Principle Checking)
\`\`\`
User Problem
    ↓
Classify Decision Tier (STRATEGIC/ANALYTICAL/TACTICAL)
    ↓
[If STRATEGIC] Check Principles (MUST gate)
[If ANALYTICAL] Reference Principles (SHOULD include)
[If TACTICAL] Skip Principles (NO check)
    ↓
Commands orchestrate workflow
    ↓
Skills guide methodology
    ↓
System Prompt constrains decisions
    ↓
Tools execute actions
    ↓
Outputs generated
    ↓
Feedback updates knowledge base
\`\`\`
```

---

## Files to Modify

1. **`.claude/diagrams/thinking-process-architecture.md`**:
   - Add new Section 5.1 (Decision Tiers and Principle Checking)
   - Replace Section 5 (Full Thinking Cycle)
   - Replace Section 10 (Cognitive Assistance Model)
   - Update Summary section

2. **Create new evolution report**:
   - `.claude/evolution/2026-01-04-thinking-architecture-principle-checking.md`
   - Document rationale for changes
   - Link to principle-first-decision-workflow.md analysis

---

## Benefits of These Changes

**Clarity**:
- Explicit decision tier classification (no ambiguity about when to check principles)
- Visual representation in diagrams (color-coded by tier)
- Clear workflow integration (shows where principle checking fits)

**Consistency**:
- All decision-making commands follow same tier classification
- Principle checking enforced systematically for strategic decisions
- Analytical decisions reference principles consistently

**Discoverability**:
- New users see decision tiers in architecture diagram
- Understanding when to use `/check-principles` is clearer
- Integration with existing thinking process is explicit

---

## Next Steps

1. Review proposed changes with user
2. If approved, update `.claude/diagrams/thinking-process-architecture.md`
3. Create evolution report documenting changes
4. Update related commands (` /architect`, `/problem-statement`) to match new workflow
