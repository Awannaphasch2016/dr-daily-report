# Feedback Loop Taxonomy - Detailed Guide

**Purpose**: This guide provides detailed case studies, implementation patterns, and practical examples for the feedback loop taxonomy defined in [Thinking Process Architecture - Section 11](../.claude/diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties).

**Relationship to Architecture**: This document elaborates on Section 11 with:
- Real-world case studies from this project
- Step-by-step implementation patterns using thinking tools
- Cross-domain examples (code, knowledge, communication)
- Detailed escalation heuristics with tool-based signals

**For structural overview and decision tree, see Section 11 first.**

---

## Section 1: Purpose + Principle

### Why Feedback Loops Matter

**Problem**: When debugging or problem-solving, we often get stuck repeating the same unsuccessful approach without realizing it.

**Solution**: Explicit awareness of feedback loop types enables metacognitive monitoring—knowing WHEN to change your approach, not just HOW.

**Key Principle**: "Same execution → Same outcome = no progress. Different execution → Same outcome = wrong strategy."

### The Self-Healing Property

Claude's thinking process includes self-healing through loop escalation:

```
Try fix (Retrying Loop)
    → Still failing? → Question assumptions (Initial-Sensitive Loop)
    → Still failing? → Try different path (Branching Loop)
    → Still failing? → Update learning process (Meta-Loop)
```

**Meta-loop** is the crucial innovation—when current loop type doesn't work, change the loop type itself.

---

## Section 2: The Self-Healing Problem

### Pattern: The Stuck Loop

**Scenario**: You've tried fixing a Lambda timeout 3 times:
1. Added caching → Still timeout
2. Optimized query → Still timeout
3. Increased memory → Still timeout

**Problem**: You're stuck in **retrying loop** (changing execution), but the real issue might be the 30s timeout limit itself (assumption).

**Self-Healing**: `/reflect` detects pattern → "Same error 3x" → Meta-loop trigger → Escalate to initial-sensitive → `/hypothesis` "What if 30s is too short for this workload?"

### Without Feedback Loop Awareness

```
Iteration 1: Fix A → Failed (8 min wasted)
Iteration 2: Fix B → Failed (8 min wasted)
Iteration 3: Fix C → Failed (8 min wasted)
Iteration 4: Fix D → Failed (8 min wasted)
Iteration 5: Give up or random success (40 min wasted)
```

### With Feedback Loop Awareness

```
Iteration 1: Fix A → Failed
Iteration 2: Fix B → Failed
/reflect: "Stuck in retrying loop" → Escalate to initial-sensitive
Iteration 3: /hypothesis "Timeout limit wrong" → Success (16 min total)
```

**Savings**: 24 minutes + frustration avoided

---

## Section 3: Five Fundamental Loop Types

### Loop Type 1: Retrying Loop (Single-Loop Learning)

**Learning Level**: Single-Loop (Argyris & Schön, 1978)

**What changes**: Execution (HOW you do it)

**What stays same**: Strategy, assumptions, goals

**When to use**: First occurrence of failure, execution error

**Escalation trigger**: Same `/trace` output repeatedly (zero gradient)

#### Real-World Example: Lambda N+1 Query

**Problem**: Lambda timeout after processing 100 items

**Retrying Loop iterations**:

```
Attempt 1:
→ /trace: N+1 query detected in process_items()
→ Fix: Add batch loading
→ /validate: Deploy + test
→ Result: Still timing out

Attempt 2:
→ /trace: Different N+1 query in related_data()
→ Fix: Add batch loading there too
→ /validate: Deploy + test
→ Result: Success!
```

**Why it worked**: Root causes were different (two separate N+1 queries). Retrying loop appropriate because execution problem, not strategy problem.

**Tool usage**:
- `/trace` (backward): Find root cause
- Fix code
- `/validate`: Test solution
- `/observe`: Monitor results

**Gradient**: Positive (different root causes found each time)

#### When Retrying Loop Fails (Zero Gradient)

```
Attempt 1:
→ /trace: Lambda timeout, no specific cause
→ Fix: Increase memory 512MB → 1024MB
→ Result: Still timing out

Attempt 2:
→ /trace: Lambda timeout, no specific cause (SAME!)
→ Fix: Optimize database query
→ Result: Still timing out

Attempt 3:
→ /trace: Lambda timeout, no specific cause (SAME!)
→ Fix: Add caching
→ Result: Still timing out

❌ STUCK SIGNAL: Same /trace output 3x
/reflect: "Execution changes but outcome doesn't"
→ Meta-loop trigger: Escalate to initial-sensitive
```

---

### Loop Type 2: Initial-Sensitive Loop (Double-Loop Learning)

**Learning Level**: Double-Loop (question assumptions)

**What changes**: Assumptions, initial state (WHAT you believe)

**What stays same**: Approach, method

**When to use**: Execution varies but outcome identical, assumptions might be wrong

**Escalation trigger**: `/validate` fails multiple hypotheses

#### Real-World Example: API Authentication Failure

**Context**: API returning 401 Unauthorized

**Failed Retrying Loop** (led to escalation):
```
Attempt 1: Refresh JWT token → Still 401
Attempt 2: Check token expiry → Token valid, still 401
Attempt 3: Verify API key → API key correct, still 401
```

**Initial-Sensitive Loop iterations**:

```
/reflect: "I'm stuck, execution changes but outcome doesn't"
→ Meta-loop trigger: Question assumptions

Hypothesis 1:
→ /hypothesis: "Maybe JWT expired server-side but we cache it client-side"
→ /research: Check server token validation logic
→ /validate: No, server validates correctly
→ Result: Assumption wrong

Hypothesis 2:
→ /hypothesis: "Maybe API requires different auth header format"
→ /research: Read API docs carefully (again!)
→ /validate: Docs say 'Bearer <token>', we send 'JWT <token>'
→ Result: ✅ FOUND IT! Assumption about header format was wrong

Fix: Change 'JWT' → 'Bearer'
→ Success!
```

**Why it worked**: Problem wasn't execution (code was correct for JWT format), but assumption (we assumed 'JWT' prefix, API expected 'Bearer').

**Tool usage**:
- `/reflect`: Detect stuck pattern
- `/hypothesis`: Generate alternative assumptions
- `/research`: Test each hypothesis
- `/validate`: Check if assumption correct

**Gradient**: Positive (different hypotheses each time, learning from failures)

#### When Initial-Sensitive Loop Fails

```
Hypothesis 1: JWT format wrong → /validate: No
Hypothesis 2: API endpoint wrong → /validate: No
Hypothesis 3: Permission scope wrong → /validate: No
Hypothesis 4: Rate limit issue → /validate: No

❌ STUCK SIGNAL: Multiple hypotheses all fail
/reflect: "Assumptions vary but all wrong"
→ Meta-loop trigger: Escalate to branching
```

---

### Loop Type 3: Branching Loop (Double-Loop Learning)

**Learning Level**: Double-Loop (explore alternative paths)

**What changes**: Exploration path, direction (WHERE you look)

**What stays same**: Problem definition

**When to use**: Multiple approaches needed, current path inadequate

**Escalation trigger**: `/impact` shows all paths inadequate

#### Real-World Example: Performance Optimization

**Context**: API response time too slow (2000ms, target 500ms)

**Failed Initial-Sensitive Loop** (led to escalation):
```
Hypothesis 1: Database query slow → Query already optimized
Hypothesis 2: Network latency → Can't control
Hypothesis 3: Large payload → Already minimized
→ All assumptions checked, none fix the problem
```

**Branching Loop iterations**:

```
/reflect: "Multiple assumptions checked, none work"
→ Meta-loop trigger: Need different exploration path

Path 1: Caching approach
→ /impact: Analysis shows 30% hit rate (limited benefit)
→ Trade-off: Complexity vs minor gain
→ Assessment: Not worth it

Path 2: Database denormalization
→ /impact: Analysis shows 80% speedup but 3x storage
→ Trade-off: Performance vs storage cost
→ Assessment: Too costly

Path 3: Async processing + real-time updates
→ /impact: Analysis shows immediate response (50ms) + background job
→ Trade-off: User experience vs architectural complexity
→ Assessment: Best option

/compare: Path 1 vs Path 2 vs Path 3
→ Decision: Path 3 (async processing)
→ Implementation: Return 202 Accepted immediately, process async, update via WebSocket
→ Result: Success! (50ms response time)
```

**Why it worked**: Problem required different APPROACH (async instead of sync), not just fixing assumptions about sync approach.

**Tool usage**:
- `/reflect`: Detect need for different path
- `/compare`: Evaluate alternatives systematically
- `/impact`: Assess consequences of each path
- `/validate`: Test chosen approach

**Gradient**: Positive (explored multiple paths, learned trade-offs)

#### When Branching Loop Fails

```
Path 1: Approach A → /impact: Inadequate
Path 2: Approach B → /impact: Inadequate
Path 3: Approach C → /impact: Inadequate

❌ STUCK SIGNAL: All paths inadequate
/reflect: "Multiple paths explored, none solve problem"
→ Meta-loop trigger: Question problem framing itself
```

---

### Loop Type 4: Synchronize Loop (Single/Double-Loop Learning)

**Learning Level**: Single-Loop (align with reality) or Double-Loop (update strategy)

**What changes**: Knowledge alignment with reality

**What stays same**: Goal

**When to use**: Drift detected (knowledge outdated), NOT failure-driven

**Escalation trigger**: Drift recurring despite `/consolidate`

#### Real-World Example: Documentation Drift

**Context**: Deployment guide says "ECR repository auto-created", but actually need to create manually

**Synchronize Loop iterations**:

```
Observation:
→ /observe: New team member follows deployment guide
→ Error: ECR repository doesn't exist
→ Investigation: Check current infrastructure code
→ Reality: ECR repository creation removed in commit abc123 (6 months ago)

Drift detected:
→ Documentation (says auto-created) ≠ Reality (manual creation needed)

Synchronization:
→ /validate: Check actual deployment process
→ /consolidate: Update mental model + documentation
→ Fix: Update deployment guide with manual ECR creation step
→ Result: Documentation now matches reality
```

**Why it worked**: This wasn't a FAILURE (no bug), but DRIFT (knowledge outdated). Synchronize loop corrects the drift.

**Tool usage**:
- `/observe`: Notice discrepancy
- `/validate`: Check current reality
- `/consolidate`: Align knowledge with reality
- Document changes (journal/evolve)

**Gradient**: N/A (not failure-driven, drift-driven)

#### When Synchronize Loop Fails

```
Week 1: Update docs to match reality
Week 2: Drift recurs (reality changed again)
Week 3: Update docs again
Week 4: Drift recurs (reality changed again)

❌ STUCK SIGNAL: Drift recurring despite synchronization
/reflect: "Synchronization strategy ineffective"
→ Meta-loop trigger: Need different sync strategy (automation, not manual updates)
```

---

### Loop Type 5: Meta-Loop (Triple-Loop Learning)

**Learning Level**: Triple-Loop (update learning process itself)

**What changes**: Loop type itself, perspective

**What stays same**: Ultimate goal (solve problem)

**When to use**: Current loop type not making progress, stuck

**Escalation trigger**: `/reflect` reveals loop type ineffective

#### Real-World Example: Meta-Loop Escalation Chain

**Full escalation sequence**:

```
STAGE 1: Retrying Loop (Single-Loop)
Problem: Lambda timeout
→ Attempt 1: Add caching → Still timeout
→ Attempt 2: Optimize query → Still timeout
→ Attempt 3: Increase memory → Still timeout
→ /reflect: "Same error 3x, zero gradient"
→ META-LOOP TRIGGER: Escalate to initial-sensitive

STAGE 2: Initial-Sensitive Loop (Double-Loop)
→ /hypothesis: "Maybe 30s timeout too short for this workload"
→ /research: Measure actual processing time (45s average)
→ /validate: Yes, workload genuinely needs >30s
→ Fix approach: Increase timeout to 60s
→ /validate: Deploy + test
→ Result: Still timeout (now at 60s!)
→ /reflect: "Assumption was right but fix didn't work"
→ META-LOOP TRIGGER: Escalate to branching

STAGE 3: Branching Loop (Double-Loop)
→ Path 1: Increase timeout to 15min (Lambda max)
   → /impact: Works but costs $$$ for long execution
→ Path 2: Break work into chunks + Step Functions
   → /impact: Solves timeout but adds complexity
→ Path 3: Move to ECS Fargate (no timeout limit)
   → /impact: Solves timeout but migration effort
→ /compare: Analyze trade-offs
   → Decision: Path 2 (Step Functions) - best balance
→ Implementation: Chunked processing with Step Functions
→ Result: Success!

Total iterations: 3 (retrying) + 1 (initial-sensitive) + 3 (branching) = 7
Time: ~2 hours (with meta-loop escalation)
Without meta-loop: Would likely continue retrying indefinitely or give up
```

**Why it worked**: Meta-loop enabled perspective shifts:
1. Retrying → Initial-Sensitive: "Not execution, but assumption"
2. Initial-Sensitive → Branching: "Not one assumption, but approach itself"
3. Success: Found right architectural solution (Step Functions)

**Tool usage**:
- `/reflect`: Detect stuck patterns at each stage
- `/compare`: Evaluate loop types (which to use next)
- All other tools: Used within each loop type

**Gradient**: Meta-loop restores positive gradient by changing loop type

---

## Section 4: Decision Tree

### When to Use Which Loop?

```
Problem detected
├─ First occurrence? → RETRYING LOOP (fix execution)
│  ├─ Fixed after 1-2 attempts? → Success, document
│  └─ Same error after 3 attempts? → ESCALATE to INITIAL-SENSITIVE
│
├─ Execution varies but outcome identical? → INITIAL-SENSITIVE LOOP (question assumptions)
│  ├─ Found wrong assumption, fixed? → Success, document
│  └─ Multiple hypotheses all fail? → ESCALATE to BRANCHING
│
├─ Need different approach/path? → BRANCHING LOOP (evaluate alternatives)
│  ├─ Found better path? → Success, document
│  └─ All paths inadequate? → ESCALATE to META-LOOP
│
├─ Knowledge drift (not failure)? → SYNCHRONIZE LOOP (align with reality)
│  ├─ Drift resolved? → Success, document
│  └─ Drift recurring? → ESCALATE to META-LOOP
│
└─ Current loop type not working? → META-LOOP (change loop type)
   └─ Always document learnings → /journal → /abstract → /evolve
```

### Self-Check Questions (Metacognitive Monitoring)

**"Am I making progress?"**
- Same output repeatedly? → Zero gradient (stuck) → Escalate
- Different output each time? → Positive gradient (learning) → Continue

**"Am I fixing execution or questioning strategy?"**
- Fixing HOW → Retrying loop
- Questioning WHAT → Initial-sensitive loop
- Evaluating WHERE → Branching loop

**"Have I tried this approach before with same failure?"**
- Yes, same failure → Stuck in current loop → Escalate
- No, different failure → Making progress → Continue

---

## Section 5: Meta-Loop Escalation Patterns

### Pattern 1: Retrying → Initial-Sensitive

**Trigger**: Same `/trace` output repeatedly (zero gradient)

**Signal**: "Execution changes but outcome doesn't"

**Tool transition**:
- From: `/trace` (root cause) + fix code
- To: `/hypothesis` (question assumptions) + `/research`

**Example**: Lambda timeout case above (caching/query/memory all fail → question timeout assumption)

---

### Pattern 2: Initial-Sensitive → Branching

**Trigger**: `/validate` fails multiple hypotheses

**Signal**: "Assumptions vary but all wrong"

**Tool transition**:
- From: `/hypothesis` (generate assumptions) + `/validate`
- To: `/compare` (evaluate paths) + `/impact`

**Example**: API performance case above (multiple optimization assumptions fail → evaluate different architectural approaches)

---

### Pattern 3: Branching → Meta-Loop (Problem Reframing)

**Trigger**: `/impact` shows all paths inadequate

**Signal**: "Multiple paths explored, none work"

**Tool transition**:
- From: `/compare` (evaluate alternatives) + `/impact`
- To: `/reflect` (question problem framing)

**Example**: "How to make sync API fast" → No solution → Reframe: "Do we need sync API or can we use async?" → New solution space

---

### Pattern 4: Synchronize → Meta-Loop (Automation)

**Trigger**: Drift recurring despite `/consolidate`

**Signal**: "Manual synchronization ineffective"

**Tool transition**:
- From: `/validate` (check reality) + `/consolidate` (update manually)
- To: `/reflect` (evaluate sync strategy) + automate sync process

**Example**: Documentation drift case above (manual updates can't keep up → automate docs generation from code)

---

## Section 6: Real-World Case Studies

### Case Study 1: AWS Lambda Permission Error (Full Escalation)

**Initial Problem**: Lambda returning "AccessDeniedException" when writing to DynamoDB

**Stage 1: Retrying Loop** (3 attempts)
```
Attempt 1:
→ /trace: Missing DynamoDB permissions in IAM role
→ Fix: Add dynamodb:PutItem permission
→ /validate: Test locally with mocked DynamoDB
→ Deploy: Still failing!

Attempt 2:
→ /trace: Still AccessDeniedException
→ Fix: Add dynamodb:UpdateItem, dynamodb:GetItem
→ /validate: Test with AWS CLI using same role
→ Deploy: Still failing!

Attempt 3:
→ /trace: Still same error (ZERO GRADIENT!)
→ /reflect: "I'm stuck in retrying loop - added 3 permissions, still failing"
→ META-LOOP TRIGGER: Escalate to initial-sensitive
```

**Stage 2: Initial-Sensitive Loop** (2 hypotheses)
```
Hypothesis 1:
→ /hypothesis: "Maybe I need dynamodb:* (all permissions)"
→ /research: Check AWS docs for required permissions
→ /validate: Add dynamodb:* → Test
→ Result: Still failing! (Hypothesis wrong)

Hypothesis 2:
→ /hypothesis: "Maybe resource ARN is wrong (different region/account)"
→ /research: Check actual table ARN vs IAM policy ARN
→ /validate: Compare ARNs
→ Result: ✅ FOUND IT! ARN had typo (us-east-1 instead of us-west-2)

Fix: Correct ARN in IAM policy
→ Success!
```

**Learnings**:
- Retrying loop tried 3 permission changes (zero gradient)
- Meta-loop escalation revealed assumption wrong (not permissions, but ARN)
- Total time: 45 min (with escalation) vs 2+ hours (without)

---

### Case Study 2: Database Migration Rollback (Branching Loop)

**Problem**: Need to rollback failed database migration, multiple approaches possible

**Branching Loop evaluation**:

```
Path 1: Manual SQL rollback
→ /impact:
   - Direct: Execute rollback SQL manually
   - Cascading: Risk of data loss if rollback incomplete
   - Indirect: No audit trail
→ Assessment: Fast but risky

Path 2: Automated migration tool rollback
→ /impact:
   - Direct: Run 'alembic downgrade -1'
   - Cascading: Rollback tracked in migration history
   - Indirect: Assumes migration is reversible
→ Assessment: Safe but assumes good down() method

Path 3: Restore from backup
→ /impact:
   - Direct: Restore DB snapshot from before migration
   - Cascading: Lose all data changes since migration
   - Indirect: Downtime during restore (5-10 min)
→ Assessment: Safest but loses recent data

/compare: Path 1 vs Path 2 vs Path 3
→ Decision criteria:
   - Data loss tolerance: Low
   - Downtime tolerance: Medium
   - Risk tolerance: Low
→ Decision: Path 2 (automated rollback) + verify with Path 3 backup available
→ Result: Success! Rolled back cleanly with full audit trail
```

**Learnings**:
- Branching loop enabled systematic evaluation
- `/impact` revealed hidden consequences (data loss, downtime)
- `/compare` applied decision criteria to choose best path

---

### Case Study 3: Performance Regression (Synchronize Loop)

**Problem**: API suddenly slow after no code changes (drift from expected performance)

**Synchronize Loop resolution**:

```
Observation:
→ /observe: API response time increased from 200ms to 2000ms
→ No code changes in past week
→ CloudWatch shows gradual degradation

Investigation:
→ /validate: Check current system state
   - Database query plan changed (index not used)
   - Aurora statistics outdated
→ Reality: Database planner chose different (slow) query path

Synchronization:
→ /consolidate: Update understanding
   - Expected: Queries always use index
   - Reality: Planner can choose full table scan if statistics stale
→ Fix: Run ANALYZE to update statistics
→ /validate: Performance restored (200ms)
→ Document: Add nightly ANALYZE to maintenance schedule

Prevention:
→ /evolve: Update monitoring to alert on query plan changes
→ Result: Future drift detected automatically
```

**Learnings**:
- Synchronize loop recognized drift (not failure)
- Root cause was environment change, not code
- Solution involved aligning expectations with reality + prevention

---

### Case Study 4: Flaky Test (Meta-Loop for Test Strategy)

**Problem**: Test passes 90% of time, fails 10% randomly

**Full escalation sequence**:

```
RETRYING LOOP (3 attempts):
Attempt 1: Re-run test → Passes
Attempt 2: Re-run test → Passes
Attempt 3: Re-run test → Fails
→ /reflect: "Flakiness persists, retrying doesn't help"
→ META-LOOP: Escalate to initial-sensitive

INITIAL-SENSITIVE LOOP (2 hypotheses):
Hypothesis 1: Race condition in async code
→ /research: Add delays
→ /validate: Still flaky
Hypothesis 2: Test isolation issue (shared state)
→ /research: Check test setup/teardown
→ /validate: Tests share database fixtures!
→ Fix: Isolate database per test
→ Result: Still flaky (hypothesis partially right)
→ META-LOOP: Escalate to branching

BRANCHING LOOP (3 paths):
Path 1: Fix flakiness (isolate all shared state)
→ /impact: Time-consuming, hard to guarantee
Path 2: Retry flaky test automatically (pytest-rerunfailures)
→ /impact: Masks problem, doesn't fix root cause
Path 3: Accept flakiness, skip in CI, run manually
→ /impact: Reduces CI reliability
→ /compare: Path 1 best but need different approach

META-LOOP (reframe problem):
→ /reflect: "All paths try to fix flakiness, but what if we redesign test?"
→ Reframe: "How to test this WITHOUT shared state?"
→ New approach: Mock database instead of real one
→ Implementation: Switch to pytest mocks
→ Result: Test no longer flaky!
```

**Learnings**:
- Meta-loop enabled reframing: "fix flakiness" → "redesign test"
- Each loop type tried, each revealed partial truth
- Final solution required perspective shift (mock instead of real DB)

---

### Case Study 5: Team Onboarding (Synchronize + Meta-Loop)

**Problem**: New team members struggle with setup despite detailed docs

**Synchronize Loop attempt**:

```
Week 1:
→ /observe: New hire follows setup guide, gets stuck on Doppler config
→ /validate: Check current setup process
→ Reality: Doppler CLI commands changed (v3 → v4)
→ /consolidate: Update docs with new CLI syntax
→ Result: Next hire succeeds

Week 3:
→ /observe: Another new hire stuck on AWS permissions
→ /validate: Check IAM setup
→ Reality: New AWS account structure requires different permissions
→ /consolidate: Update docs with new IAM policy
→ Result: Next hire succeeds

Week 5:
→ /observe: Another new hire stuck on Docker build
→ Reality: ARM vs x86 architecture issue
→ /consolidate: Update docs with architecture-specific commands

❌ DRIFT RECURRING: Manual updates can't keep pace
→ /reflect: "Synchronize loop working but inefficient"
→ META-LOOP: Need different strategy
```

**Meta-Loop solution**:

```
/reflect: "Manual doc updates reactive, need proactive"
→ Reframe: "How to make onboarding self-documenting?"
→ New approach:
   1. Automated setup script (validates environment, installs deps)
   2. Setup wizard (detects config, guides user)
   3. Automated doc generation from setup script
→ Implementation: Create setup.sh with validation
→ Result: Onboarding time reduced 80%, docs stay in sync
```

**Learnings**:
- Synchronize loop worked but was inefficient (manual)
- Meta-loop reframed: reactive docs → proactive automation
- Solution: Shift from documentation to executable automation

---

## Section 7: Checklist + References

### Quick Checklist: "Am I Stuck?"

Use `/reflect` and ask:

**Pattern Detection**:
- [ ] Have I tried same approach 3+ times?
- [ ] Is my `/trace` output identical across attempts?
- [ ] Am I changing execution but getting same outcome?

**If YES to above → STUCK in Retrying Loop → Escalate to Initial-Sensitive**

**Assumption Validation**:
- [ ] Have I questioned 3+ assumptions, all wrong?
- [ ] Is my `/validate` consistently failing hypotheses?
- [ ] Am I changing assumptions but getting same outcome?

**If YES to above → STUCK in Initial-Sensitive Loop → Escalate to Branching**

**Path Evaluation**:
- [ ] Have I explored 3+ paths, all inadequate?
- [ ] Does my `/impact` analysis show no good options?
- [ ] Am I evaluating paths but none solve problem?

**If YES to above → STUCK in Branching Loop → Escalate to Meta-Loop (reframe)**

**Drift Monitoring**:
- [ ] Is knowledge drift recurring despite updates?
- [ ] Is my `/consolidate` ineffective at preventing drift?
- [ ] Am I synchronizing manually repeatedly?

**If YES to above → STUCK in Synchronize Loop → Escalate to Meta-Loop (automate)**

---

### Thinking Tools Quick Reference

| Tool | Purpose | Loop Relationship |
|------|---------|-------------------|
| `/reflect` | Metacognitive analysis | Meta-loop trigger (all loops) |
| `/trace` | Root cause analysis | Retrying loop (find root cause) |
| `/hypothesis` | Generate assumptions | Initial-sensitive loop |
| `/research` | Test hypotheses | Initial-sensitive loop |
| `/validate` | Check claims | All loops (verify solutions) |
| `/compare` | Evaluate alternatives | Branching loop |
| `/impact` | Assess consequences | Branching loop |
| `/consolidate` | Synthesize knowledge | Synchronize loop |
| `/observe` | Notice phenomenon | All loops (gather data) |

---

### Theoretical References

**Argyris & Schön (1978)**: *Organizational Learning: A Theory of Action Perspective*
- Single-Loop Learning: Error correction at execution level
- Double-Loop Learning: Question governing variables (assumptions, norms)
- Triple-Loop Learning: Learn how to learn (meta-learning)

**Flavell (1979)**: *Metacognition and Cognitive Monitoring*
- Metacognition requires explicit representation
- Monitoring enables self-regulation
- Awareness prerequisite for control

**Wei et al. (2022)**: *Chain-of-Thought Prompting Elicits Reasoning in Large Language Models*
- Explicit reasoning steps improve LLM performance
- Thinking traces enable metacognition
- Pattern recognition emerges from explicit representation

---

### Project-Specific Evidence

**Validation Files** (proof loops exist):
- `.claude/validations/2025-12-27-thinking-process-has-feedback-loops.md` - 4 loop types identified in architecture

**What-If Analyses** (design decisions):
- `.claude/what-if/2025-12-27-loops-as-part-of-thinking-process-architecture.md` - Why loops belong in Section 11
- `.claude/what-if/2025-12-27-thinking-tools-instead-of-gradient-measurement.md` - Tools vs gradient approach

**Architecture** (canonical source):
- `.claude/diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties` - Structural overview
- `.claude/diagrams/thinking-process-architecture.md#metacognitive-commands-thinking-about-thinking` - Tool definitions

---

### Next Steps

After reading this guide:

1. **Internalize the pattern**: Same output repeatedly = stuck → Escalate
2. **Use `/reflect` proactively**: After 2-3 attempts, check for stuck pattern
3. **Trust meta-loop**: When current loop doesn't work, change loop type
4. **Document learnings**: Use `/journal` → `/abstract` → `/evolve` to capture patterns
5. **Practice recognition**: As you work, notice which loop you're in

**Remember**: The goal isn't to avoid loops (they're natural), but to recognize when to escalate.
