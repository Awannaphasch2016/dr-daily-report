---
name: qna
description: Reveal Claude's understanding and knowledge gaps to align with user's objective before proceeding
accepts_args: true
arg_schema:
  - name: topic
    required: true
    description: "Topic or objective to probe understanding about"
  - name: depth
    required: false
    description: "Optional depth: surface, moderate, deep (default: moderate)"
composition: []
---

# QnA Command (Knowledge Alignment Check)

**Purpose**: Proactively reveal Claude's understanding and knowledge gaps to align with user's objective before implementation

**Core Principle**: "Uncertainty should be explicit" - surface assumptions and gaps early to prevent rework from misalignment.

**When to use**:
- Before starting feature implementation -> Verify understanding
- When user describes complex requirements -> Check interpretation
- Before making architectural decisions -> Confirm shared mental model
- When working on unfamiliar domain -> Reveal knowledge boundaries

**When NOT to use**:
- Simple, well-defined tasks (typo fixes, clear bugs)
- When you're confident about requirements
- After implementation (use `/validate` instead)

---

## Tuple Effects (Universal Kernel Integration)

**Mode Type**: `probe`

When `/qna` executes, it surfaces Claude's internal state for user verification:

| Tuple Component | Effect |
|-----------------|--------|
| **Constraints** | **REVEAL**: Surfaces current assumptions and known facts |
| **Invariant** | **NONE**: Does not modify success criteria |
| **Principles** | **NONE**: Does not modify principles |
| **Strategy** | Enables user correction before proceeding |
| **Check** | Outputs confidence levels for alignment verification |

**Knowledge State Revelation**:
```yaml
# What /qna surfaces:
knowledge_state:
  confident:
    - "Telegram Mini App uses React + TypeScript"
    - "Data comes from Aurora MySQL"
  assumed:
    - "User wants real-time updates" # Inferred, not stated
    - "Alert delivery via Telegram notification"
  unknown:
    - "What defines 'real-time'? (1s? 1min? 15min?)"
    - "Should alerts be user-configurable?"
  questions:
    - "What latency is acceptable for price updates?"
    - "Should users set their own thresholds?"
```

---

## Local Check (Mode Completion Criteria)

The `/qna` mode is complete when ALL of the following hold:

| Criterion | Verification |
|-----------|--------------|
| **Knowledge Stated** | Confident facts explicitly listed |
| **Assumptions Surfaced** | Inferred beliefs made explicit |
| **Gaps Identified** | Unknown information acknowledged |
| **Questions Generated** | Clarifying questions proposed |
| **Confidence Scored** | Overall alignment confidence rated |

**Check Result Mapping**:
- **PASS (High confidence)**: Understanding aligns, can proceed
- **PARTIAL (Medium confidence)**: Some gaps, user should clarify
- **FAIL (Low confidence)**: Major gaps, need significant clarification

---

## Quick Reference

```bash
# Basic knowledge probe
/qna "real-time stock alerts"

# Probe with depth level
/qna "deployment pipeline" deep
/qna "error handling" surface

# Domain-specific probing
/qna "telegram mini app architecture"
/qna "aurora data model"
```

---

## Output Format

```markdown
## My Understanding of: {topic}

### What I Know (Confident)
Facts I'm certain about from codebase/docs/context:
- {Fact 1} [Source: {file/doc}]
- {Fact 2} [Source: {file/doc}]
- {Fact 3} [Source: {file/doc}]

### What I Assume (Medium Confidence)
Beliefs I've inferred but haven't verified:
- {Assumption 1} - Inferred from: {source/context}
- {Assumption 2} - Inferred from: {source/context}
- {Assumption 3} - Based on: {pattern/convention}

### What I Don't Know (Knowledge Gaps)
Information I need to proceed correctly:
- {Gap 1} - Need clarification on: {aspect}
- {Gap 2} - No information about: {aspect}
- {Gap 3} - Ambiguous: {what's unclear}

### Questions to Align

1. **{Question 1}**
   Why it matters: {impact on implementation}

2. **{Question 2}**
   Why it matters: {impact on implementation}

3. **{Question 3}**
   Why it matters: {impact on implementation}

---

### Confidence Score: {X}/10

**Assessment**: {High | Medium | Low} alignment confidence

**Recommendation**:
- {If high}: Proceed with implementation
- {If medium}: Clarify {specific gaps} before proceeding
- {If low}: Need significant discussion before starting
```

---

## Depth Levels

### `surface` - Quick alignment check
- 3-5 key facts
- Top 2-3 assumptions
- 1-2 critical gaps
- Fast, lightweight

### `moderate` (default) - Standard probe
- 5-10 facts with sources
- 3-5 assumptions with reasoning
- 3-5 gaps identified
- 3-5 clarifying questions

### `deep` - Comprehensive knowledge audit
- Exhaustive fact gathering
- All assumptions explicit
- Systematic gap analysis
- Detailed question rationale
- Domain model verification

---

## Execution Flow

### Step 1: Parse Topic and Depth

```bash
TOPIC="$1"
DEPTH="${2:-moderate}"  # Default: moderate
```

### Step 2: Gather Knowledge (Research Phase)

**Search for relevant information**:
```bash
# Code
grep -r "{topic keywords}" src/ tests/

# Documentation
grep -r "{topic keywords}" docs/ .claude/

# Specifications
grep -r "{topic keywords}" .claude/specs/

# Recent context
# (conversation history, recent files)
```

### Step 3: Categorize Knowledge

**For each piece of information**:
```
IF source is authoritative (code, config, docs):
  → CONFIDENT (high certainty)
ELIF inferred from patterns/context:
  → ASSUMED (medium certainty)
ELIF information is missing:
  → GAP (needs clarification)
```

### Step 4: Generate Questions

**For each gap or assumption**:
```
Question = {
  text: "What is X?",
  impact: "Affects Y implementation",
  options: [possible answers if known]
}
```

### Step 5: Calculate Confidence

```
confidence = (
  confident_facts * 1.0 +
  verified_assumptions * 0.5 -
  critical_gaps * 0.3
) / total_information_needed

score = round(confidence * 10)
```

### Step 6: Output Structured Response

Generate markdown following output format.

---

## Examples

### Example 1: Feature Understanding

```bash
/qna "real-time stock price alerts"
```

**Output**:
```markdown
## My Understanding of: Real-time Stock Price Alerts

### What I Know (Confident)
- Stock data comes from Aurora `daily_prices` table [Source: src/data/aurora/]
- Telegram Mini App is the UI [Source: .claude/specs/telegram/]
- Lambda functions handle backend [Source: terraform/]
- Current data refresh is nightly via precompute [Source: src/data/aurora/precompute_service.py]

### What I Assume (Medium Confidence)
- "Real-time" means < 15 minute delay - Inferred from: yfinance limitations
- Alerts delivered via Telegram notification - Inferred from: platform choice
- Single alert per price threshold - Based on: typical UX patterns
- User sets their own thresholds - Assumed from: "alerts" implying customization

### What I Don't Know (Knowledge Gaps)
- Acceptable latency for "real-time" - Need clarification: 1s? 1min? 15min?
- Alert persistence - No information: Store history or fire-and-forget?
- Threshold configuration - Ambiguous: Fixed options or user-defined?
- Multiple tickers per user - Unknown: One alert or many?
- Alert cooldown - No information: Prevent spam for volatile stocks?

### Questions to Align

1. **What latency defines "real-time" for this feature?**
   Why it matters: Determines architecture (polling vs websocket vs scheduled)

2. **Should users configure their own price thresholds?**
   Why it matters: Affects data model and UI complexity

3. **How should we handle rapid price fluctuations?**
   Why it matters: Prevents alert spam, affects user experience

4. **Should alert history be persisted?**
   Why it matters: Storage requirements, UI for past alerts

---

### Confidence Score: 5/10

**Assessment**: Medium alignment confidence

**Recommendation**:
Clarify latency requirements and threshold configuration before implementation.
These fundamentally affect architecture choice.
```

---

### Example 2: Architecture Understanding

```bash
/qna "telegram mini app architecture" deep
```

**Output**:
```markdown
## My Understanding of: Telegram Mini App Architecture

### What I Know (Confident)
- Frontend: React 18 + TypeScript + Vite [Source: frontend/twinbar/package.json]
- State management: Zustand [Source: frontend/twinbar/src/stores/]
- Charts: Lightweight Charts [Source: frontend/twinbar/src/components/]
- Backend: Lambda + API Gateway v2 [Source: terraform/]
- Database: Aurora MySQL Serverless v2 [Source: terraform/main.tf]
- CDN: CloudFront for static assets [Source: .claude/specs/telegram/spec.yaml]
- Environments: dev, stg, prd [Source: terraform/terraform.*.tfvars]

### What I Assume (Medium Confidence)
- CORS configured for API calls - Inferred from: API Gateway setup
- Telegram WebApp SDK initialized on load - Based on: Mini App requirements
- Theme colors sync with Telegram - Standard Mini App behavior
- Touch gestures enabled for charts - Assumed from: mobile-first

### What I Don't Know (Knowledge Gaps)
- None critical for architecture understanding

### Questions to Align

1. **Is there anything about the architecture you'd like me to verify?**
   Why it matters: Ensure my model matches your expectations

---

### Confidence Score: 9/10

**Assessment**: High alignment confidence

**Recommendation**:
Proceed with implementation. Architecture is well-documented.
```

---

### Example 3: Surface-Level Quick Check

```bash
/qna "error handling" surface
```

**Output**:
```markdown
## My Understanding of: Error Handling

### What I Know (Confident)
- Principle #8: Error Handling Duality (workflow vs utility)
- Workflow nodes: state-based propagation
- Utility functions: raise exceptions

### What I Assume
- You want me to follow existing patterns

### Gaps
- None for general error handling

### Confidence Score: 9/10

Proceed with existing patterns.
```

---

## Integration with Other Commands

### /qna -> Implementation
```bash
/qna "stock backtester"           # Reveal understanding
# User clarifies gaps
# Now proceed with implementation
```

### /qna -> /feature
```bash
/qna "new notification system"    # Check understanding
# User confirms alignment
/feature "notification-system"    # Create spec with shared understanding
```

### /qna -> /validate
```bash
/qna "caching strategy"           # Reveal assumptions
/validate "Redis faster than Aurora for hot data"  # Test specific assumption
```

---

## Best Practices

### Do
- Use before complex implementations
- Surface ALL assumptions (not just obvious ones)
- Ask specific, actionable questions
- Include sources for confident knowledge
- Rate confidence honestly

### Don't
- Skip for trivial tasks
- Hide uncertainty
- Ask rhetorical questions
- Overload with too many questions (prioritize)
- Proceed with low confidence without clarification

---

## See Also

- `.claude/commands/understand.md` - Build mental model (different purpose)
- `.claude/commands/validate.md` - Test specific claims
- `.claude/commands/feature.md` - Create feature spec after alignment
- `AskUserQuestion` tool - Runtime clarification (triggered by Claude)
