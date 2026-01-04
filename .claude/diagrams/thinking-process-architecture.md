# Claude's Thinking Process Architecture

**How Skills and Commands Guide Claude's Cognition**

---

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph "User Layer"
        U[User]
    end

    subgraph "Interface Layer"
        CMD["/commands<br/>(User-Invoked)"]
        CHAT[Natural Language]
    end

    subgraph "Claude's Cognitive Layer"
        CLAUDE[Claude Code Session]
        SKILLS[Skills<br/>(Auto-Discovered)]
        SYSPROMPT[System Prompt<br/>CLAUDE.md]
    end

    subgraph "Execution Layer"
        TOOLS[Tools<br/>(Read, Write, Bash, etc.)]
        MCP[MCP Servers<br/>(AWS, GitHub, etc.)]
    end

    subgraph "Storage Layer"
        FILES[".claude/ Files"]
        CODEBASE["Codebase<br/>(src/, docs/)"]
    end

    U -->|1. Invokes| CMD
    U -->|2. Asks| CHAT

    CMD -->|Orchestrates| CLAUDE
    CHAT -->|Processed by| CLAUDE

    CLAUDE -->|Reads guidance from| SKILLS
    CLAUDE -->|Follows principles from| SYSPROMPT

    SKILLS -.->|"Auto-discovered<br/>(when relevant)"| CLAUDE

    CLAUDE -->|Uses| TOOLS
    CLAUDE -->|Uses| MCP

    TOOLS -->|Read/Write| FILES
    TOOLS -->|Read/Write| CODEBASE
    MCP -->|Access| EXT[External Systems]

    style SKILLS fill:#e1f5e1
    style CMD fill:#e1e5f5
    style SYSPROMPT fill:#f5e1e1
    style CLAUDE fill:#fff4e1
```

**Key principles**:
- **Commands** = User-invoked workflows (explicit)
- **Skills** = Auto-discovered knowledge (implicit)
- **System Prompt** = Always-active principles (global)
- **Claude** = Orchestrator (applies all guidance)

---

## 2. Command Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Command
    participant Claude
    participant Skills
    participant Tools
    participant Output

    User->>Command: /explore "How to test nested skills"
    activate Command

    Command->>Claude: Load command template
    Note over Command: Command defines:<br/>- Workflow steps<br/>- Required args<br/>- Success criteria

    Claude->>Skills: Check for relevant skills
    Note over Skills: Auto-discover:<br/>- research skill<br/>- testing-workflow skill

    Skills-->>Claude: Apply methodology
    Note over Claude: Skills guide HOW to:<br/>- Decompose problem<br/>- Explore alternatives<br/>- Evaluate options

    Claude->>Tools: Execute workflow steps
    activate Tools
    Tools->>Tools: Read files
    Tools->>Tools: Search codebase
    Tools->>Tools: Write documents
    Tools-->>Claude: Results
    deactivate Tools

    Claude->>Output: Generate exploration doc
    Output-->>Command: Document created
    Command-->>User: .claude/explorations/2025-12-25-*.md
    deactivate Command

    Note over User,Output: Command orchestrates workflow<br/>Skills guide thinking<br/>Tools execute actions
```

**Flow**:
1. User invokes command with arguments
2. Command loads workflow template
3. Claude auto-discovers relevant skills
4. Skills guide HOW to approach problem
5. Claude executes using tools
6. Output generated per command spec

---

## 3. Skill Auto-Discovery Flow

```mermaid
flowchart TD
    START[User Request] --> PARSE[Parse Intent]

    PARSE --> CHECK{Task Type?}

    CHECK -->|Debug bug| SKILL1[Load: research skill]
    CHECK -->|Write code| SKILL2[Load: code-review skill]
    CHECK -->|Deploy| SKILL3[Load: deployment skill]
    CHECK -->|Refactor| SKILL4[Load: refactor skill]
    CHECK -->|Test| SKILL5[Load: testing-workflow skill]
    CHECK -->|Database| SKILL6[Load: database-migration skill]

    SKILL1 --> APPLY[Apply Skill Methodology]
    SKILL2 --> APPLY
    SKILL3 --> APPLY
    SKILL4 --> APPLY
    SKILL5 --> APPLY
    SKILL6 --> APPLY

    APPLY --> GUIDE{Skill Guides:<br/>How to approach?}

    GUIDE -->|Research| M1[Progressive Evidence Strengthening:<br/>Surface → Content → Observability → Ground Truth]
    GUIDE -->|Code Review| M2[Security + Performance checklist]
    GUIDE -->|Deploy| M3[Zero-downtime pattern]
    GUIDE -->|Refactor| M4[Complexity analysis first]
    GUIDE -->|Test| M5[FIRST principles]
    GUIDE -->|Database| M6[Reconciliation migrations]

    M1 --> EXECUTE[Execute Task]
    M2 --> EXECUTE
    M3 --> EXECUTE
    M4 --> EXECUTE
    M5 --> EXECUTE
    M6 --> EXECUTE

    EXECUTE --> OUTPUT[Deliver Result]

    style SKILL1 fill:#e1f5e1
    style SKILL2 fill:#e1f5e1
    style SKILL3 fill:#e1f5e1
    style SKILL4 fill:#e1f5e1
    style SKILL5 fill:#e1f5e1
    style SKILL6 fill:#e1f5e1
```

**Discovery logic**:
- Claude analyzes task intent
- Matches to skill domain (debugging → research, code → code-review)
- Loads skill methodology automatically
- Applies "how to" guidance from skill
- User never explicitly invokes skills (auto-discovered)

---

### 3.1 Progressive Evidence Strengthening Pattern

**Universal verification principle**: Evidence sources have natural strength hierarchies. Always verify from weakest to strongest, never stop at surface signals.

**Pattern structure**:
```
Weak Evidence → Stronger Evidence → Strongest Evidence
     ↓                  ↓                    ↓
  Confirms          Validates            Proves
  execution         correctness          ground truth
```

**Domain instantiations**:

| Domain | Surface | Content | Observability | Ground Truth |
|--------|---------|---------|---------------|--------------|
| HTTP APIs | Status code | Response payload | Application logs | Database state |
| File ops | Exit code | File content | System logs | Disk state |
| Database | Rowcount | Query result | DB logs | Table inspection |
| Testing | Test passed | Output matches | No error logs | Side effects correct |
| Deployments | Process exit | Health checks | CloudWatch logs | Traffic metrics |

**Anti-pattern**: Trusting weak evidence
```python
# WRONG: Stop at surface signal
if response.status_code == 200:
    return "Success"  # But payload might be error!

# CORRECT: Progress to ground truth
if response.status_code == 200:
    if validate_schema(response.json()):
        if check_logs_clean():
            if verify_database_state():
                return "Verified success"
```

**Application in commands**:
- `/validate`: Should progress through all evidence layers (currently stops at surface)
- `/verify` (proposed): Always enforces full hierarchy
- `/bug-hunt`: Should check data integrity (ground truth), not just existence (surface)

---

## 4. Thinking Process: Commands + Skills + Tools

```mermaid
graph LR
    subgraph "Input Layer"
        U[User Request]
    end

    subgraph "Orchestration Layer"
        CMD1["/explore"]
        CMD2["/specify"]
        CMD3["/validate"]
        CMD4["/implement"]
    end

    subgraph "Methodology Layer (Skills)"
        SK1[research<br/>systematic investigation]
        SK2[code-review<br/>quality patterns]
        SK3[testing-workflow<br/>test patterns]
        SK4[deployment<br/>zero-downtime]
    end

    subgraph "Execution Layer"
        T1[Read files]
        T2[Search code]
        T3[Write docs]
        T4[Run commands]
    end

    subgraph "Output Layer"
        O1[Documents]
        O2[Code]
        O3[Tests]
    end

    U -->|Invokes| CMD1

    CMD1 -->|Loads| SK1
    SK1 -.->|Guides| CMD1
    CMD1 -->|Uses| T1
    CMD1 -->|Uses| T2
    CMD1 -->|Uses| T3
    T3 --> O1

    CMD1 -->|"Next: /specify"| CMD2

    CMD2 -->|Loads| SK2
    SK2 -.->|Guides| CMD2
    CMD2 -->|Uses| T3
    T3 --> O1

    CMD2 -->|"Next: /validate"| CMD3

    CMD3 -->|Loads| SK3
    SK3 -.->|Guides| CMD3
    CMD3 -->|Uses| T1
    CMD3 -->|Uses| T4
    T4 --> O3

    CMD3 -->|"Next: implement"| CMD4

    CMD4 -->|Loads| SK2
    CMD4 -->|Loads| SK3
    CMD4 -->|Loads| SK4
    SK2 -.->|Guides| CMD4
    SK3 -.->|Guides| CMD4
    SK4 -.->|Guides| CMD4
    CMD4 -->|Uses| T1
    CMD4 -->|Uses| T2
    CMD4 -->|Uses| T3
    CMD4 -->|Uses| T4
    T3 --> O2
    T4 --> O3

    style CMD1 fill:#e1e5f5
    style CMD2 fill:#e1e5f5
    style CMD3 fill:#e1e5f5
    style CMD4 fill:#e1e5f5
    style SK1 fill:#e1f5e1
    style SK2 fill:#e1f5e1
    style SK3 fill:#e1f5e1
    style SK4 fill:#e1f5e1
```

**Pattern**: Commands orchestrate workflow, Skills guide methodology

---

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

---

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

### Metacognitive Commands (Thinking About Thinking)

Beyond problem-solving commands, Claude uses metacognitive tools to monitor and adjust its own thinking process.

#### `/reflect` - Analyze Actions and Reasoning

**Purpose**: Understand what happened and why you did what you did

**Output**: Pattern recognition, effectiveness assessment, behavioral insights

**When to use**:
- After completing a task (synthesize learnings)
- When stuck in a loop (detect patterns)
- Before escalating to different approach (meta-loop trigger)

**Relationship to Loops**:
- **Meta-loop trigger**: Reveals when current loop type isn't working
- **Pattern detection**: "I've tried 3 fixes with same error" → stuck signal
- **Effectiveness assessment**: Determines if current strategy making progress

**Example**:
```
/reflect
→ Pattern: Same /trace output 3 times (stuck in retrying loop)
→ Assessment: Execution varies but outcome identical
→ Meta-loop trigger: Escalate to initial-sensitive (question assumptions)
```

---

#### `/understand {concept}` - Build Mental Model

**Purpose**: Internal understanding (for Claude) + external explanation (for user)

**Prerequisite**: None (but often follows `/research`)

**Output**: Mental model, connections, explanations

**When to use**:
- Research skill (build understanding from investigation)
- Initial-sensitive loop (check if assumptions correct)
- Before explaining to user (ensure comprehension first)

**Relationship to Loops**:
- **Initial-sensitive**: Reveals faulty assumptions about system
- **Synchronize**: Aligns mental model with reality

**Generalization of**: `/explain` (which focuses on communication step only)

---

#### `/hypothesis {observation}` - Construct Explanations

**Purpose**: Ask "why" and construct plausible paths to explore

**Prerequisite**: Requires `/observe` output (need something to explain)

**Output**: Testable hypotheses, predictions, evidence needed

**When to use**:
- Before `/research` (generate what to investigate)
- Initial-sensitive loop (propose alternative assumptions)
- Root cause analysis (generate candidate causes)

**Relationship to Loops**:
- **Initial-sensitive**: Generates new assumptions to test
- **Retrying**: Proposes alternative root causes

**Workflow**: `/observe` → `/hypothesis` → `/research` → `/validate`

---

#### `/consolidate {topic}` - Synthesize Knowledge

**Purpose**: Gather → Understand → Consolidate → Communicate

**Superset of**: `/summary` (which only communicates final result)

**Output**: Unified coherent model, contradictions resolved, gaps identified

**When to use**:
- Synchronize loop (ensure knowledge coherence)
- Knowledge evolution (after learning from multiple sources)
- Before major decision (unify understanding)

**Relationship to Loops**:
- **Synchronize**: Ensures knowledge aligns with reality
- **Meta-loop**: Synthesizes learnings across loop iterations

**Steps**:
1. **Gather**: Collect information from sources
2. **Understand**: Build mental model
3. **Consolidate**: Resolve contradictions, fill gaps
4. **Communicate**: Present unified view

---

#### `/impact {change}` - Assess Change Scope

**Purpose**: Identify affected artifacts (direct + cascading effects)

**Output**: Ripple analysis (Level 1/2/3 effects), risk assessment

**When to use**:
- Branching loop (evaluate consequences of each path)
- Before major changes (understand blast radius)
- Architecture decisions (assess system-wide impact)

**Relationship to Loops**:
- **Branching**: Evaluates path consequences
- **Meta-loop**: Assesses impact of changing loop type

**Levels**:
- **Level 1**: Direct effects (files/modules explicitly changed)
- **Level 2**: Cascading effects (dependencies affected)
- **Level 3**: Indirect effects (assumptions, patterns, principles)

---

#### `/compare {A} vs {B}` - Structured Comparison

**Purpose**: Contrast alternatives across dimensions

**Output**: Trade-off analysis, decision criteria, recommendation

**When to use**:
- Branching loop (choose between paths)
- Choosing between approaches
- Evaluating trade-offs

**Relationship to Loops**:
- **Branching**: Evaluates multiple paths systematically
- **Meta-loop**: Compares loop types (which loop to use)

**Note**: `/compare` invokes `/what-if` with comparison mode. `/what-if` is broader (single scenario analysis), `/compare` is specialized (multi-alternative comparison).

---

#### `/trace {event} [forward|backward]` - Follow Causality

**Purpose**: Trace implications (forward) or root cause (backward)

**Output**: Causal chains (Event → Consequence OR Event ← Cause)

**When to use**:
- Retrying loop (find root cause of failure)
- Meta-loop (trace implications of decisions)
- Impact analysis (forward trace from change)

**Relationship to Loops**:
- **Retrying**: Backward trace to find root cause
- **Meta-loop**: Forward trace to understand implications

**Modes**:
- **Backward**: Event ← Cause ← Root (debugging)
- **Forward**: Event → Effect → Consequence (prediction)

---

### Tool Prerequisites (Workflow Ordering)

Natural ordering emerges from tool prerequisites (no hardcoded workflows):

```
/observe (notice phenomenon)
    ↓
/hypothesis (explain why) - REQUIRES: /observe output
    ↓
/research (test hypothesis) - REQUIRES: /hypothesis
    ↓
/validate (check claim) - REQUIRES: /research evidence
/proof (derive theorem) - REQUIRES: /research evidence
    ↓
/reflect (synthesize) - REQUIRES: completed work
    ↓
/consolidate (unify knowledge) - REQUIRES: /reflect insights
```

**Key principle**: Workflow emerges from tool design (self-documenting)

**Why prerequisites matter**:
- `/validate` and `/proof` require evidence → must follow `/research`
- `/hypothesis` requires observation → must follow `/observe`
- `/consolidate` requires insights → must follow `/reflect`
- `/reflect` requires completed work → comes after task completion

**Example workflow** (debugging):
```
/observe (notice failure)
    → /hypothesis (why might this fail?)
    → /research (test each hypothesis)
    → /validate (which hypothesis correct?)
    → /trace (find root cause)
    → /reflect (what pattern do I see?)
    → /consolidate (synthesize understanding)
```

---

## 6. Skill Types in Thinking Process

```mermaid
graph TB
    subgraph "Generalized Skills (Methodology)"
        G1[research<br/><i>How to investigate<br/>ANY problem</i>]
        G2[refactor<br/><i>How to improve<br/>ANY code</i>]
        G3[code-review<br/><i>How to review<br/>ANY code</i>]
        G4[testing-workflow<br/><i>How to test<br/>ANY feature</i>]
        G5[security-review<br/><i>How to secure<br/>ANY system</i>]
        G6[performance-optimization<br/><i>How to optimize<br/>ANY service</i>]
    end

    subgraph "Domain-Specific Skills (Domain Expertise)"
        D1[deployment<br/><i>How to deploy<br/>Lambda specifically</i>]
        D2[database-migration<br/><i>How to migrate<br/>Aurora MySQL</i>]
        D3[error-investigation<br/><i>How to debug<br/>AWS services</i>]
        D4[line-uiux<br/><i>How to design<br/>LINE Bot UI</i>]
        D5[telegram-uiux<br/><i>How to design<br/>Telegram Mini App</i>]
        D6[monitoring-observability<br/><i>How to monitor<br/>CloudWatch</i>]
        D7[api-design<br/><i>How to design<br/>FastAPI endpoints</i>]
        D8[terraform-patterns<br/><i>How to write<br/>Terraform modules</i>]
    end

    subgraph "Task Application"
        TASK[User Task]
    end

    TASK -->|"Debugging AWS Lambda"| G1
    TASK -->|"Debugging AWS Lambda"| D3
    G1 -->|Methodology| APPROACH1[Systematic investigation]
    D3 -->|Domain Knowledge| APPROACH1
    APPROACH1 --> RESULT1[Multi-layer AWS diagnostics]

    TASK -->|"Refactor React component"| G2
    TASK -->|"Refactor React component"| D5
    G2 -->|Methodology| APPROACH2[Complexity analysis]
    D5 -->|Domain Knowledge| APPROACH2
    APPROACH2 --> RESULT2[Telegram UI patterns applied]

    TASK -->|"Deploy new Lambda"| D1
    TASK -->|"Deploy new Lambda"| G6
    D1 -->|Domain Knowledge| APPROACH3[Zero-downtime deployment]
    G6 -->|Methodology| APPROACH3
    APPROACH3 --> RESULT3[Optimized Lambda deployment]

    style G1 fill:#d4edda
    style G2 fill:#d4edda
    style G3 fill:#d4edda
    style G4 fill:#d4edda
    style G5 fill:#d4edda
    style G6 fill:#d4edda

    style D1 fill:#d1ecf1
    style D2 fill:#d1ecf1
    style D3 fill:#d1ecf1
    style D4 fill:#d1ecf1
    style D5 fill:#d1ecf1
    style D6 fill:#d1ecf1
    style D7 fill:#d1ecf1
    style D8 fill:#d1ecf1
```

**Pattern**: Generalized (HOW to think) + Domain-specific (WHAT to apply) = Complete solution

---

## 7. Command Composition Pattern

```mermaid
graph LR
    subgraph "Meta-Cognitive Commands"
        MC1[/decompose]
        MC2[/abstract]
        MC3[/evolve]
        MC4[/explain]
    end

    subgraph "Exploration Commands"
        EX1[/explore]
        EX2[/what-if]
        EX3[/specify]
    end

    subgraph "Validation Commands"
        V1[/validate]
        V2[/proof]
    end

    subgraph "Documentation Commands"
        D1[/journal]
        D2[/observe]
    end

    subgraph "Workflow Commands"
        W1[/bug-hunt]
        W2[/refactor]
        W3[/review]
    end

    MC1 -->|"Feeds into"| EX1
    EX1 -->|"Feeds into"| EX2
    EX2 -->|"Feeds into"| EX3
    EX3 -->|"Feeds into"| V1
    V1 -->|"If valid"| IMPL[Implementation]
    IMPL -->|"Track"| D2
    D2 -->|"Document"| D1
    D1 -->|"Extract patterns"| MC2
    MC2 -->|"Update principles"| MC3

    W1 -.->|"Uses"| MC1
    W1 -.->|"Uses"| D2
    W1 -.->|"Uses"| D1

    W2 -.->|"Uses"| MC1
    W2 -.->|"Uses"| V1

    W3 -.->|"Uses"| V1

    style MC1 fill:#fff3cd
    style MC2 fill:#fff3cd
    style MC3 fill:#fff3cd
    style MC4 fill:#fff3cd

    style EX1 fill:#d1ecf1
    style EX2 fill:#d1ecf1
    style EX3 fill:#d1ecf1

    style V1 fill:#d4edda
    style V2 fill:#d4edda

    style D1 fill:#f8d7da
    style D2 fill:#f8d7da

    style W1 fill:#e2e3e5
    style W2 fill:#e2e3e5
    style W3 fill:#e2e3e5
```

**Composition**: Commands build on each other (decompose → explore → specify → validate → implement → observe → journal → abstract → evolve)

---

## 8. Information Flow Architecture

```mermaid
flowchart TB
    subgraph "Knowledge Sources (Input)"
        S1[CLAUDE.md<br/>Stable Principles]
        S2[Skills<br/>Methodologies]
        S3[Commands<br/>Workflows]
        S4[docs/<br/>Reference]
        S5[Codebase<br/>Ground Truth]
    end

    subgraph "Claude's Working Memory"
        WM[Active Context]

        subgraph "Loaded Guidance"
            L1[Active Skills]
            L2[Active Command]
            L3[System Prompt]
        end

        subgraph "Analysis State"
            A1[Problem Model]
            A2[Solution Options]
            A3[Decisions Made]
        end
    end

    subgraph "Execution Actions"
        E1[Read files]
        E2[Search code]
        E3[Run commands]
        E4[Write output]
    end

    subgraph "Knowledge Outputs"
        O1[.claude/explorations/<br/>Solution analysis]
        O2[.claude/journals/<br/>Decisions]
        O3[.claude/observations/<br/>Learnings]
        O4[.claude/validations/<br/>Proofs]
        O5[Code changes]
    end

    S1 -->|Always loaded| L3
    S2 -->|Auto-discovered| L1
    S3 -->|User-invoked| L2
    S4 -->|Referenced| WM
    S5 -->|Analyzed| WM

    L1 -.->|Guides| A1
    L1 -.->|Guides| A2
    L2 -.->|Structures| A3
    L3 -.->|Constrains| A1
    L3 -.->|Constrains| A2

    A1 --> E1
    A2 --> E2
    A2 --> E3
    A3 --> E4

    E4 --> O1
    E4 --> O2
    E4 --> O3
    E4 --> O4
    E4 --> O5

    O1 -.->|Feeds back| S4
    O2 -.->|Feeds back| S1
    O3 -.->|Feeds back| S2
    O5 -.->|Updates| S5

    style S1 fill:#f8d7da
    style S2 fill:#d4edda
    style S3 fill:#d1ecf1
    style L1 fill:#d4edda
    style L2 fill:#d1ecf1
    style L3 fill:#f8d7da
```

**Flow**: Knowledge sources → Claude's working memory → Execution → Knowledge outputs → Feedback loop

---

## 9. Thinking Layers (Abstraction Hierarchy)

```mermaid
graph TB
    subgraph "Layer 1: Foundational Principles (Stable)"
        L1A[CLAUDE.md<br/>Core principles]
        L1B[System constraints]
        L1C[Must-follow rules]
    end

    subgraph "Layer 2: Methodologies (Semi-Stable)"
        L2A[Generalized Skills<br/>research, refactor, etc.]
        L2B[Problem-solving frameworks]
        L2C[Decision-making patterns]
    end

    subgraph "Layer 3: Domain Knowledge (Evolving)"
        L3A[Domain-Specific Skills<br/>deployment, database, etc.]
        L3B[Technology patterns]
        L3C[Best practices]
    end

    subgraph "Layer 4: Workflows (Frequently Updated)"
        L4A[Commands<br/>explore, specify, etc.]
        L4B[Orchestration patterns]
        L4C[Composition rules]
    end

    subgraph "Layer 5: Tactical Execution (Session-Specific)"
        L5A[Current task context]
        L5B[Active decisions]
        L5C[Intermediate results]
    end

    L1A --> L2A
    L1B --> L2B
    L1C --> L2C

    L2A --> L3A
    L2B --> L3B
    L2C --> L3C

    L3A --> L4A
    L3B --> L4B
    L3C --> L4C

    L4A --> L5A
    L4B --> L5B
    L4C --> L5C

    L5C -.->|"Feedback:<br/>abstract → evolve"| L1A
    L5C -.->|"Feedback:<br/>journal → document"| L2A
    L5C -.->|"Feedback:<br/>observe → refine"| L3A

    style L1A fill:#dc3545
    style L1B fill:#dc3545
    style L1C fill:#dc3545

    style L2A fill:#ffc107
    style L2B fill:#ffc107
    style L2C fill:#ffc107

    style L3A fill:#17a2b8
    style L3B fill:#17a2b8
    style L3C fill:#17a2b8

    style L4A fill:#28a745
    style L4B fill:#28a745
    style L4C fill:#28a745

    style L5A fill:#6c757d
    style L5B fill:#6c757d
    style L5C fill:#6c757d
```

**Hierarchy**:
- **Layer 1** (Principles): Rarely change, foundational
- **Layer 2** (Methodologies): Generalized thinking patterns
- **Layer 3** (Domain): Technology-specific knowledge
- **Layer 4** (Workflows): Orchestration and composition
- **Layer 5** (Execution): Active session state

**Feedback loops**: Execution results feed back to update higher layers

---

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

---

## Summary: How It All Works Together

### Commands (Blue boxes)
- **User-invoked** workflows
- **Orchestrate** the thinking process
- **Compose** with other commands
- **Example**: `/explore` → `/what-if` → `/specify` → `/validate`

### Skills (Green boxes)
- **Auto-discovered** by Claude
- **Guide** HOW to approach problems
- **Apply** methodology automatically
- **Example**: When debugging, `research` + `error-investigation` skills activate

### System Prompt (Red boxes)
- **Always active** principles
- **Constrain** all decisions
- **Foundational** rules
- **Example**: CLAUDE.md principles always enforced

### Tools (Gray boxes)
- **Execute** concrete actions
- **Access** files and systems
- **Produce** outputs
- **Example**: Read, Write, Bash, MCP tools

### The Full Cycle (with Principle Checking)
```
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
```

**Result**: Claude thinks systematically, consistently, and learns over time.

---

## 11. Feedback Loop Types (Self-Healing Properties)

Claude's thinking process includes self-healing mechanisms through five fundamental feedback loop types. These loops enable recovery from failures and continuous improvement.

### Progress as Gradient (Implicit, Not Measured)

**Principle**: Failure is not binary (0 or 1), but a gradient (0.0 to 1.0)

**Gradient Definition**:
- **1.0**: Goal fully achieved
- **0.5**: Halfway toward goal (making progress)
- **0.0**: Maximum distance from goal (complete failure)

**Failure Redefined**: "Step taken moves away from goal"
- **Negative gradient** (moving from 0.5 → 0.3) = failure (regressing)
- **Positive gradient** (moving from 0.3 → 0.5) = progress (improving)
- **Zero gradient** (stuck at 0.3) = no progress (trigger for escalation, not failure itself)

**Key Insight**: "Not reaching goal" ≠ failure
- Progress (0.0 → 0.7) without reaching goal (1.0) = still success (moving in right direction)
- Regression (0.7 → 0.5) even if above baseline = failure (moved away from goal)

**Relationship to Thinking Tools**:
- Gradient is **implicit** (not measured explicitly)
- Tools reveal gradient through patterns:
  - Same `/trace` output repeatedly = zero gradient (stuck)
  - Different `/trace` output each time = positive gradient (learning)
  - `/reflect` makes gradient patterns visible ("I'm stuck" or "I'm making progress")
- **No numeric measurement required** - pattern recognition sufficient

---

### Five Fundamental Loop Types

#### 1. Retrying Loop (Single-Loop Learning)

**What changes**: Execution (HOW), strategy unchanged

**When to use**: First occurrence of failure, execution error

**Tools**: `/trace` (find root cause), `/validate` (test fix)

**Example**:
```
Bug: Lambda timeout
→ /trace → Root cause: N+1 query
→ Fix: Add batch loading
→ /validate → Still timing out
→ /trace → Root cause: Still N+1 (different location)
→ Fix: Add caching
→ /validate → Success
```

**Escalation signal**: Same `/trace` output repeatedly (stuck)

---

#### 2. Initial-Sensitive Loop (Double-Loop Learning)

**What changes**: Assumptions/initial state (WHAT), approach unchanged

**When to use**: Execution varies but outcome identical, assumptions might be wrong

**Tools**: `/hypothesis` (generate alternatives), `/research` (test), `/validate` (check)

**Example**:
```
After 3 retrying attempts with same failure:
→ /reflect → "Execution varies, outcome identical"
→ /hypothesis → "Maybe assumption X is wrong"
→ /research → Test alternative assumption
→ /validate → New assumption correct
→ Success with different starting point
```

**Escalation signal**: `/validate` fails multiple hypotheses

---

#### 3. Branching Loop (Double-Loop Learning)

**What changes**: Exploration path (WHERE), problem unchanged

**When to use**: Multiple approaches needed, current path inadequate

**Tools**: `/compare` (evaluate paths), `/impact` (assess consequences)

**Example**:
```
Problem: Improve API performance
→ Path 1: Caching → /impact → Limited gains
→ Path 2: Query optimization → /impact → Better but complex
→ Path 3: Async processing → /impact → Best trade-off
→ /compare → Choose async processing
```

**Escalation signal**: `/impact` shows all paths inadequate

---

#### 4. Synchronize Loop (Single/Double-Loop Learning)

**What changes**: Knowledge alignment with reality

**When to use**: Drift detected, knowledge outdated (NOT failure-driven)

**Tools**: `/validate` (check reality), `/consolidate` (align knowledge)

**Example**:
```
Documentation says API uses JWT, code uses sessions
→ /validate → Code reality = sessions
→ /consolidate → Update mental model
→ Documentation updated
```

**Escalation signal**: Drift recurring despite `/consolidate`

---

#### 5. Meta-Loop (Triple-Loop Learning)

**What changes**: Loop type itself (PERSPECTIVE)

**When to use**: Current loop type not making progress, perspective shift needed

**Tools**: `/reflect` (detect stuck pattern), `/compare` (evaluate loop types)

**Example**:
```
After multiple retrying attempts:
→ /reflect → "I'm stuck in retrying loop"
→ Pattern: Execution changes but outcome doesn't
→ Meta-loop trigger: Switch to initial-sensitive
→ /hypothesis → Question assumptions instead
```

**Escalation signal**: `/reflect` reveals loop type ineffective

---

### Escalation via Thinking Tools

**Retrying → Initial-Sensitive**:
- **Tool signal**: `/trace` shows same root cause repeatedly
- **`/reflect` reveals**: "Execution varies but outcome identical"
- **Pattern**: Retrying loop isn't working
- **Escalate**: Use `/hypothesis` to question assumptions (initial-sensitive)

**Initial-Sensitive → Branching**:
- **Tool signal**: `/validate` shows multiple assumptions all fail
- **`/reflect` reveals**: "Assumptions vary but all wrong"
- **Pattern**: Initial-sensitive loop isn't working
- **Escalate**: Use `/compare` to evaluate different paths (branching)

**Branching → Meta-Loop**:
- **Tool signal**: `/impact` shows all paths inadequate
- **`/reflect` reveals**: "Multiple paths explored, none work"
- **Pattern**: Branching loop isn't working
- **Escalate**: Use `/reflect` to question problem framing (meta-loop)

**Synchronize → Meta-Loop**:
- **Tool signal**: `/validate` shows drift recurring despite sync
- **`/reflect` reveals**: "Synchronization strategy ineffective"
- **Pattern**: Synchronize loop isn't working
- **Escalate**: Use `/compare` to evaluate sync strategies (meta-loop)

---

### Tool-Loop Mapping

| Loop Type | Primary Tools | Escalation Signal | Learning Level |
|-----------|---------------|-------------------|----------------|
| **Retrying** | `/trace`, `/validate` | Same `/trace` output repeatedly | Single-Loop |
| **Initial-Sensitive** | `/hypothesis`, `/research`, `/validate` | `/validate` fails multiple hypotheses | Double-Loop |
| **Branching** | `/compare`, `/impact` | `/impact` shows all paths inadequate | Double-Loop |
| **Synchronize** | `/validate`, `/consolidate` | Drift recurring despite `/consolidate` | Single/Double-Loop |
| **Meta-Loop** | `/reflect`, `/compare` | `/reflect` reveals loop type ineffective | Triple-Loop |

**Learning Levels** (Argyris & Schön, 1978):
- **Single-Loop**: Error correction at execution level
- **Double-Loop**: Question assumptions/strategy
- **Triple-Loop**: Update learning process itself

---

### Metacognitive Self-Check (Tool-Based)

When debugging or stuck, ask:

**Pattern Detection**:
- `/reflect`: "What pattern do I see in my attempts?"
  - Same execution → Same outcome = normal progress
  - Different execution → Same outcome = stuck in retrying (escalate!)

**Root Cause Analysis**:
- `/trace`: "What's the root cause?"
  - If same answer repeatedly → stuck in retrying loop
  - If different answers → making progress

**Assumption Validation**:
- `/validate`: "Is my assumption correct?"
  - If fails repeatedly → escalate to initial-sensitive

**Path Evaluation**:
- `/compare`: "Which approach is better?"
  - If all inadequate → escalate to branching or meta-loop

**Progress Assessment**:
- Gradient implicit in tool outputs
- Repetition = zero gradient = escalation trigger
- Variation = positive gradient = keep current loop

---

### Full Cycle with Self-Healing

**Happy path**:
```
Problem → Decompose → Explore → Specify → Validate → Implement → Observe → Success
```

**Failure path (Retrying Loop)**:
```
Observe (failure) → /trace (root cause) → Fix → Implement → Observe → Success
```

**Strategy failure (Initial-Sensitive Loop)**:
```
Retrying (3x same error)
    → /reflect (stuck signal)
    → /hypothesis (new assumptions)
    → /research (test)
    → /validate (check)
    → Success with different assumption
```

**Approach failure (Branching Loop)**:
```
Multiple approaches tried, all fail
    → /compare (evaluate paths)
    → /impact (assess alternatives)
    → Choose best path
    → Success with different direction
```

**Meta-cognitive failure (Meta-Loop)**:
```
Current loop type not working
    → /reflect (detect pattern)
    → /compare (loop types)
    → Switch loop type
    → Success with different perspective
```
