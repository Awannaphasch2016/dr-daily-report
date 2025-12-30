---
name: reflect
description: Analyze what happened and why you did what you did - metacognitive awareness for detecting stuck patterns
accepts_args: false
composition:
  - skill: research
---

# Reflect Command

**Purpose**: Metacognitive analysis - understand what happened and why you did what you did

**Core Principle**: Pattern recognition enables meta-loop escalation. When execution varies but outcomes don't, you're stuck.

**When to use**:
- After completing a task (synthesize learnings)
- When stuck in a loop (detect patterns)
- Before escalating to different approach (meta-loop trigger)
- After multiple failed attempts (assess effectiveness)

**Output**: Pattern recognition, effectiveness assessment, stuck signals, meta-loop triggers

---

## Quick Reference

```bash
# After task completion
/reflect
→ Synthesize what worked, what didn't
→ Extract patterns for future reference

# When stuck
/reflect
→ Detect: "Same /trace output 3 times"
→ Pattern: Stuck in retrying loop
→ Trigger: Escalate to initial-sensitive

# Before changing approach
/reflect
→ Assess: Is current strategy working?
→ Decide: Continue or escalate?
```

---

## Reflect vs Other Commands

| Command | Purpose | Focus |
|---------|---------|-------|
| **`/observe`** | Notice phenomenon | External behavior (what system does) |
| **`/trace`** | Follow causality | Causal chains (why system does it) |
| **`/reflect`** | Analyze actions | Internal behavior (why YOU did it) |
| **`/journal`** | Document decisions | Record for future (what was decided) |

**Key difference**: `/reflect` is metacognitive (thinking about YOUR thinking), others are system-focused.

---

## Execution Flow

### Step 1: Analyze Actions Taken

**What to capture**:
```
Actions in current session:
- Tool calls made (Read, Write, Bash, etc.)
- Commands invoked (/explore, /what-if, /validate, etc.)
- Code changes written
- Research paths explored
- Hypotheses tested
```

**Focus**: WHAT you did (concrete actions)

---

### Step 2: Identify Reasoning

**Why you did it**:
```
Rationale behind actions:
- Assumptions made ("I assumed X would work")
- Strategy chosen ("I tried approach Y")
- Tools selected ("I used /trace because...")
- Decisions made ("I chose path Z")
```

**Focus**: WHY you did it (reasoning process)

---

### Step 3: Recognize Patterns

**Pattern detection**:
```
Look for repetition:
- Same /trace output repeatedly → Zero gradient (stuck)
- Different /trace output each time → Positive gradient (learning)
- Same error after multiple fixes → Retrying loop not working
- Multiple hypotheses all fail → Initial-sensitive loop not working
- All paths inadequate → Branching loop not working
```

**Focus**: PATTERNS in your attempts (meta-awareness)

---

### Step 4: Assess Effectiveness

**Effectiveness metrics**:
```
Progress indicators:
✅ Making progress:
   - Different outputs each iteration
   - Error changing (even if not solved)
   - Understanding deepening

❌ Stuck (zero gradient):
   - Same output repeatedly
   - Same error after multiple attempts
   - No new information gained

🔄 Need escalation:
   - Stuck for 3+ iterations
   - Current loop type ineffective
   - Perspective shift needed
```

**Focus**: Is your approach WORKING? (self-assessment)

---

### Step 5: Generate Insights

**Insights to extract**:
```
Learning outcomes:
1. What worked? (strategies to reuse)
2. What didn't? (anti-patterns to avoid)
3. What surprised you? (assumptions violated)
4. What pattern emerged? (generalizable knowledge)
5. What would you do differently? (future improvements)
```

**Focus**: LEARNINGS for future (knowledge capture)

---

### Step 6: Meta-Loop Trigger (If Stuck)

**Escalation decision**:
```
If stuck pattern detected:
→ Current loop: Retrying (execution changes)
→ Stuck signal: Same /trace output 3x
→ Meta-loop trigger: Escalate to initial-sensitive
→ New approach: Use /hypothesis to question assumptions
```

**Focus**: ESCALATION to different loop type (meta-cognitive action)

---

## Output Format

```markdown
## What Happened

**Actions taken**:
- [Action 1]: [What I did]
- [Action 2]: [What I did]
- [Action 3]: [What I did]

**Outcomes**:
- [Outcome 1]: [What resulted]
- [Outcome 2]: [What resulted]

---

## Why I Did It

**Reasoning**:
- [Assumption 1]: [What I believed]
- [Strategy]: [Approach I chose]
- [Tool selection]: [Why I used X tool]

**Rationale**:
[Explanation of thinking process]

---

## Pattern Recognition

**Pattern detected**:
[Description of repetition or variation]

**Gradient assessment**:
- Same output repeatedly? → Zero gradient (stuck)
- Different output each time? → Positive gradient (learning)

**Effectiveness**:
✅ Making progress | ❌ Stuck | 🔄 Need escalation

---

## Meta-Loop Trigger (If Applicable)

**Current loop type**: [Retrying | Initial-Sensitive | Branching | Synchronize]

**Stuck signal**: [Evidence of being stuck]

**Escalation recommendation**:
→ From: [Current loop]
→ To: [Suggested loop]
→ Reason: [Why escalate]
→ Next action: [Concrete tool to use]

---

## Insights & Learnings

**What worked**:
- [Success 1]
- [Success 2]

**What didn't work**:
- [Failure 1]
- [Failure 2]

**Surprises** (assumptions violated):
- [Surprise 1]
- [Surprise 2]

**Future improvements**:
- [Improvement 1]
- [Improvement 2]
```

---

## Examples

### Example 1: Task Completion (Happy Path)

```bash
/reflect

## What Happened
- Added caching to API endpoint
- Wrote tests for cache logic
- Deployed to dev environment
- Verified performance improvement

## Why I Did It
- User requested faster API response
- Caching natural solution for read-heavy endpoint
- Tests ensure correctness
- Dev deployment for validation

## Pattern Recognition
- No stuck pattern (first attempt succeeded)
- Positive gradient (each step progressed)

## Insights
- Caching reduced latency 80%
- Redis better than in-memory for this use case
- Remember to invalidate on write
```

---

### Example 2: Stuck in Retrying Loop (Meta-Loop Trigger)

```bash
/reflect

## What Happened
- Lambda timeout (attempt 1) → Added caching
- Lambda timeout (attempt 2) → Optimized query
- Lambda timeout (attempt 3) → Increased memory

## Why I Did It
- Assumed execution issue (N+1 query, memory, etc.)
- Tried fixing execution each time
- Strategy: Improve performance

## Pattern Recognition
❌ STUCK SIGNAL DETECTED
- Same error: Lambda timeout
- Different fixes: Caching, query, memory
- Same outcome: Still timing out
- **Zero gradient**: Not making progress

## Meta-Loop Trigger
→ Current loop: Retrying (fixing execution)
→ Stuck signal: 3 attempts, same timeout
→ Pattern: Execution varies but outcome doesn't
→ Escalation: Switch to Initial-Sensitive
→ Next action: /hypothesis "Why might Lambda timeout regardless of optimizations?"
→ New assumption: Maybe 30s limit itself is the constraint, not execution

## Insights
- Retrying loop effective for 1-2 attempts
- After 3 attempts with same error, question assumptions
- Meta-loop escalation needed
```

---

### Example 3: Multiple Hypotheses Failed (Escalate to Branching)

```bash
/reflect

## What Happened
- Hypothesis 1: JWT expired → /validate → No, JWT valid
- Hypothesis 2: CORS issue → /validate → No, CORS configured
- Hypothesis 3: Rate limit → /validate → No, under limit
- Hypothesis 4: Permission denied → /validate → No, permissions correct

## Why I Did It
- Escalated from retrying to initial-sensitive
- Tested multiple assumptions
- Each /validate showed assumption wrong

## Pattern Recognition
❌ STUCK SIGNAL DETECTED
- All hypotheses fail validation
- Assumptions vary but outcome doesn't (all wrong)
- **Zero gradient**: Not finding root cause

## Meta-Loop Trigger
→ Current loop: Initial-Sensitive (questioning assumptions)
→ Stuck signal: 4 hypotheses all fail
→ Pattern: Need different exploration path
→ Escalation: Switch to Branching
→ Next action: /compare "Different debugging approaches" (code review vs logs vs network trace)
→ New strategy: Try different PATH, not different assumption

## Insights
- Initial-sensitive effective when 1-2 assumptions wrong
- After multiple hypotheses fail, need different approach
- Branching loop evaluates multiple paths
```

---

## Relationship to Feedback Loops

`/reflect` is the **meta-loop trigger** - it makes invisible patterns visible.

### How /reflect Detects Stuck Patterns

**Retrying Loop**:
```
/trace → Root cause A
/validate → Still failing
/trace → Root cause A (again!)
→ /reflect → "Stuck in retrying loop"
→ Meta-loop: Escalate to initial-sensitive
```

**Initial-Sensitive Loop**:
```
/hypothesis → Assumption X
/validate → Wrong
/hypothesis → Assumption Y
/validate → Wrong
→ /reflect → "Multiple hypotheses fail"
→ Meta-loop: Escalate to branching
```

**Branching Loop**:
```
/compare → All paths inadequate
/impact → No good options
→ /reflect → "Problem framing might be wrong"
→ Meta-loop: Question the problem itself
```

### Integration with Thinking Tools

`/reflect` synthesizes outputs from other tools:
- Analyzes `/trace` outputs for repetition
- Evaluates `/validate` results for patterns
- Assesses `/hypothesis` effectiveness
- Reviews `/compare` outcomes

**Result**: Metacognitive awareness → Autonomous loop escalation

---

## Best Practices

### Do
- **Use after 3+ attempts** with same outcome (stuck signal)
- **Analyze tool outputs** for repetition patterns
- **Assess gradient** (zero vs positive)
- **Trigger meta-loop** when current loop ineffective
- **Extract learnings** for future reference

### Don't
- **Don't reflect after every action** (too granular)
- **Don't ignore stuck signals** (zero gradient = escalate)
- **Don't stay in same loop** when /reflect shows ineffective
- **Don't forget to document** learnings (/journal after /reflect)

---

## See Also

- **Architecture**: [Thinking Process Architecture - Section 11](../.claude/diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties)
- **Metacognitive Tools**: [Section 5 - Metacognitive Commands](../.claude/diagrams/thinking-process-architecture.md#metacognitive-commands-thinking-about-thinking)
- **Skills**: [research](../.claude/skills/research/) - Systematic investigation methodology
- **Commands**:
  - `/observe` - Notice phenomenon (external)
  - `/trace` - Follow causality (system)
  - `/journal` - Document decisions (record)

---

## Prompt Template

When you invoke `/reflect`, analyze:

**Actions**: What did you do? (concrete steps)

**Reasoning**: Why did you do it? (assumptions, strategy)

**Patterns**: What repetition do you see? (same output = stuck)

**Effectiveness**: Is it working? (gradient assessment)

**Insights**: What did you learn? (future improvements)

**Meta-Loop**: Need to escalate? (if stuck pattern detected)

**Output**: Structured reflection following the format above.
