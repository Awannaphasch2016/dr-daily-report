---
name: handholding
description: Step-by-step guidance through complex tasks with explicit confirmation at each step
accepts_args: true
arg_schema:
  - name: task
    required: true
    description: "What you want to accomplish (e.g., 'deploy to production', 'set up new environment')"
  - name: pace
    required: false
    description: "Optional pace: careful (default), quick, thorough"
---

# Handholding Command

**Purpose**: Guide users through complex or unfamiliar tasks step-by-step with explicit confirmation, explanation, and escape hatches at each step.

**Core Philosophy**: "Psychological safety through explicit control" - Users should feel safe attempting complex tasks because they understand each step and can abort anytime.

**When to use**:
- Nervous about a complex operation (first production deploy)
- Learning a new workflow (unfamiliar with the process)
- High-stakes tasks where mistakes are costly
- Want to understand what's happening, not just do it
- Teaching someone else through a process

**When NOT to use**:
- Routine tasks you're comfortable with
- Time-critical operations (use direct commands)
- Simple one-step operations
- Already know the process well

---

## Quick Reference

```bash
# Basic usage
/handholding "deploy to production"
/handholding "set up feature-alerts environment"
/handholding "debug this timeout error"
/handholding "configure new MCP server"

# With pace modifier
/handholding "deploy to staging" quick      # Fewer confirmations
/handholding "migrate database" careful     # Default, confirm each step
/handholding "set up CI/CD" thorough        # Extra explanations
```

---

## What Makes /handholding Different

| Aspect | Regular Commands | `/handholding` |
|--------|-----------------|----------------|
| **Confirmation** | At end or critical points | Every step |
| **Explanation** | Minimal | What, Why, Risk for each step |
| **Progress** | Implicit | Explicit "Step X of Y" |
| **Abort** | Say "stop" | Explicit [Abort] option |
| **Reversibility** | Not stated | Stated for each step |
| **Pace** | Claude decides | User controls |

---

## Output Format

Each step follows this structure:

```markdown
---

## Step {N} of {Total}: {Step Name}

**What I'll do**: {Clear description of the action}

**Why**: {Rationale - why this step is necessary}

**Reversible**: {Yes | No | Partially} - {explanation if needed}

**Risk**: {None | Low | Medium | High} - {what could go wrong}

---

**Ready?**

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]
```

---

## Pace Levels

### `careful` (default)
- Confirm before EVERY step
- Full explanations
- Show all options
- Best for: First time, high stakes, learning

### `quick`
- Confirm only before write/destructive operations
- Brief explanations
- Skip read-only confirmations
- Best for: Familiar but want safety net

### `thorough`
- Confirm before every step
- Extended explanations with examples
- Show related commands and alternatives
- Best for: Teaching, documentation, deep understanding

---

## Execution Flow

### Step 1: Parse Task and Analyze

```markdown
## Handholding Mode: {task}

**Pace**: {careful | quick | thorough}

I'll guide you through this step by step. You can:
- **Proceed**: Continue to the next step
- **Skip**: Skip this step (if safe)
- **Explain More**: Get more details
- **Abort**: Stop safely at any point

---

### Analysis

**Task**: {task description}
**Estimated steps**: {N}
**Estimated time**: {X minutes}
**Overall risk**: {Low | Medium | High}

**Prerequisites** (checking now...):
- [ ] {Prerequisite 1}
- [ ] {Prerequisite 2}

Ready to begin?

[ Start ] [ Show All Steps First ] [ Abort ]
```

### Step 2: Execute Each Step

For each step:

1. **Present the step** with What/Why/Risk/Reversibility
2. **Wait for user choice**: Proceed / Skip / Explain More / Abort
3. **If Proceed**: Execute and show result
4. **If Skip**: Note skipped, continue to next
5. **If Explain More**: Provide detailed explanation, then re-present choice
6. **If Abort**: Clean up gracefully, summarize what was done

### Step 3: Completion Summary

```markdown
---

## Handholding Complete

**Task**: {task}
**Result**: {Success | Partial | Aborted}

### Steps Completed
- [x] Step 1: {name} - {outcome}
- [x] Step 2: {name} - {outcome}
- [ ] Step 3: {name} - skipped
- [x] Step 4: {name} - {outcome}

### What Was Done
{Summary of changes made}

### What Was NOT Done
{If any steps skipped or aborted}

### Next Steps (if any)
{Recommendations for follow-up}

### Rollback Instructions (if needed)
{How to undo if something went wrong}

---

You're all set! If anything seems wrong, let me know.
```

---

## User Response Handling

### [ Proceed ]
```
User: proceed / yes / continue / next / go / ok / y
Action: Execute current step, show result, move to next
```

### [ Skip ]
```
User: skip / pass / later / not now
Action:
  - If safe to skip: Note skipped, continue
  - If required: Explain why can't skip, re-present options
```

### [ Explain More ]
```
User: explain / why / more / details / tell me more
Action:
  - Provide detailed explanation
  - Show examples if available
  - Explain consequences of doing vs not doing
  - Re-present original options
```

### [ Abort ]
```
User: abort / stop / cancel / quit / exit / nevermind
Action:
  - Confirm abort intention
  - Clean up any partial state
  - Show what was completed
  - Provide rollback instructions if needed
```

---

## Examples

### Example 1: Production Deployment

```bash
/handholding "deploy to production"
```

**Output**:
```markdown
## Handholding Mode: Deploy to Production

**Pace**: careful (default)

I'll guide you through deploying to production step by step. You can:
- **Proceed**: Continue to the next step
- **Skip**: Skip this step (if safe)
- **Explain More**: Get more details
- **Abort**: Stop safely at any point

---

### Analysis

**Task**: Deploy current code to production environment
**Estimated steps**: 7
**Estimated time**: 10-15 minutes
**Overall risk**: Medium (production deployment)

**Prerequisites** (checking now...):
- [x] On dev branch
- [x] Working directory clean
- [x] Tests passing locally
- [ ] Staging deployment verified (checking...)

Ready to begin?

[ Start ] [ Show All Steps First ] [ Abort ]
```

User: "start"

```markdown
---

## Step 1 of 7: Verify Staging Deployment

**What I'll do**: Check that staging has been deployed and tested

**Why**: Production should never deploy code that hasn't been verified in staging first

**Reversible**: Yes - this is a read-only check

**Risk**: None

---

I'll run: `aws lambda get-function --function-name dr-daily-report-telegram-api-staging`

**Ready?**

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]
```

User: "proceed"

```markdown
✅ Step 1 Complete

Staging deployment verified:
- Image: sha256:abc123...
- Last modified: 2026-01-14 10:30 (Bangkok)
- Status: Active

---

## Step 2 of 7: Compare Staging with Production

**What I'll do**: Show differences between staging and production deployments

**Why**: Understand exactly what will change in production

**Reversible**: Yes - read-only comparison

**Risk**: None

---

**Ready?**

[ Proceed ] [ Skip ] [ Explain More ] [ Abort ]
```

### Example 2: Abort Mid-Process

User at Step 4: "abort"

```markdown
---

## Abort Requested

Are you sure you want to abort?

**Completed so far**:
- [x] Step 1: Verified staging deployment
- [x] Step 2: Compared staging with production
- [x] Step 3: Created backup tag

**Not yet done**:
- [ ] Step 4: Update production Lambda (current)
- [ ] Step 5: Verify production health
- [ ] Step 6: Run smoke tests
- [ ] Step 7: Update deployment log

**Safe to abort?** Yes - no production changes made yet

[ Confirm Abort ] [ Continue from Step 4 ]
```

User: "confirm abort"

```markdown
---

## Handholding Aborted

**Task**: Deploy to production
**Result**: Aborted at Step 4 (before any production changes)

### What Was Done
- Verified staging deployment is healthy
- Compared staging vs production configurations
- Created backup tag: `pre-deploy-2026-01-14`

### What Was NOT Done
- Production Lambda was NOT updated
- No production changes were made

### To Resume Later
```bash
/handholding "deploy to production"
```
The backup tag `pre-deploy-2026-01-14` is available if needed.

---

Aborted safely. No production changes were made.
```

### Example 3: Quick Pace

```bash
/handholding "run integration tests" quick
```

**Output**:
```markdown
## Handholding Mode: Run Integration Tests

**Pace**: quick (fewer confirmations)

---

### Quick Pace Active

I'll only ask for confirmation before:
- Destructive operations
- External service calls
- Operations that can't be undone

Read-only steps will proceed automatically.

---

## Steps 1-2: Environment Check (auto-proceeding...)

✅ Virtual environment active
✅ Dependencies up to date

## Step 3 of 5: Start Test Database

**What I'll do**: Start LocalStack for DynamoDB simulation

**Why**: Integration tests need database access

**Reversible**: Yes - can stop LocalStack after

**Risk**: Low - local only

**Ready?**

[ Proceed ] [ Explain More ] [ Abort ]
```

---

## Integration with Other Commands

### Wrapping Other Commands

`/handholding` can wrap other commands to add step-by-step guidance:

```bash
# These are equivalent in outcome, different in experience
/deploy prod                           # Direct execution
/handholding "deploy to production"    # Step-by-step guidance

/env "feature-alerts" deploy           # Direct execution
/handholding "deploy feature-alerts"   # Step-by-step guidance
```

### Complementary Commands

```bash
# Before: Understand what you're doing
/qna "production deployment"           # Check knowledge gaps
/handholding "deploy to production"    # Then do it step-by-step

# During: If something goes wrong
/handholding "deploy to production"    # Step 5 shows error
/bug-hunt "deployment error"           # Investigate the error
/handholding "deploy to production"    # Resume after fixing

# After: Document what you learned
/handholding "deploy to production"    # Complete successfully
/journal meta "First production deploy" # Document the experience
```

---

## When Handholding Recommends Other Commands

During execution, `/handholding` may suggest other commands:

```markdown
## Step 3 of 7: Investigate Error

The previous step encountered an error.

**Options**:
1. **Continue anyway** (not recommended)
2. **Investigate with `/bug-hunt`** (recommended)
3. **Abort and fix manually**

[ Continue ] [ Launch /bug-hunt ] [ Abort ]
```

---

## Prompt Template

You are executing the `/handholding` command to guide the user through a task step by step.

**Task**: $1
**Pace**: ${2:-careful}

---

### Execution Rules

1. **Always present steps in the standard format**:
   - Step N of Total: Name
   - What I'll do
   - Why
   - Reversible: Yes/No/Partially
   - Risk: None/Low/Medium/High
   - Options: [ Proceed ] [ Skip ] [ Explain More ] [ Abort ]

2. **Wait for explicit user response** before proceeding to next step

3. **Handle user responses**:
   - "proceed/yes/continue/go/ok/y" → Execute step, show result, present next
   - "skip/pass" → Check if safe to skip, note skipped, present next
   - "explain/why/more" → Provide detailed explanation, re-present options
   - "abort/stop/cancel" → Confirm, clean up, show summary

4. **Pace adjustments**:
   - `careful`: Confirm every step
   - `quick`: Auto-proceed read-only steps, confirm writes
   - `thorough`: Confirm every step with extended explanations

5. **On completion**: Show summary of what was done, what was skipped, next steps

6. **On abort**: Show what was completed, what wasn't, rollback instructions if needed

7. **On error**: Present options clearly - continue, investigate, abort

---

## See Also

- `/step` - Thinking Tuple Protocol (Claude's internal discipline)
- `/deploy` - Deployment workflow (can be wrapped with `/handholding`)
- `/qna` - Check knowledge gaps before starting
- `/bug-hunt` - If something goes wrong during handholding
