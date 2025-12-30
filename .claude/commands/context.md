---
name: context
description: Extract relevant context for specific tasks
accepts_args: true
arg_schema:
  - name: task_description
    required: true
    description: "Task you're about to work on (quoted if spaces)"
composition:
  - skill: research
---

# /context - Task-Focused Context Extraction

**Purpose**: Smart context gathering to reduce overhead before starting a specific task

**Category**: Productivity Tool

**Core Principle**: "Context before code - know what exists before building new"

---

## Differentiation from Similar Commands

### vs /explore
- **`/explore`**: "What are ALL the options?" (divergent exploration)
- **`/context`**: "Where do I start for THIS specific task?" (focused context)

**Example**:
```bash
# Exploration (broad)
/explore "What state management libraries exist for React?"
→ Evaluates: Redux, Zustand, Jotai, MobX, Context (5+ options)

# Context (focused)
/context "Add user preferences persistence to Telegram Mini App"
→ Returns: Zustand store files, TMA cloud storage examples, relevant tests
```

---

### vs /consolidate
- **`/consolidate`**: "Help me understand this concept" (knowledge synthesis)
- **`/context`**: "What files/patterns do I need for this task?" (actionable references)

**Example**:
```bash
# Consolidation (conceptual)
/consolidate "How does error handling work in our codebase?"
→ Synthesizes: State-based vs exceptions, when to use each, examples from across codebase

# Context (practical)
/context "Add error boundary to portfolio page"
→ Returns: Existing error boundary components, React error handling patterns, test examples
```

---

### vs /understand
- **`/understand`**: "Explain this concept to me" (learning)
- **`/context`**: "Show me what to read for this task" (doing)

**Relationship**: Use `/understand` to learn, `/context` to execute

---

## When to Use

**✅ Use /context when**:
- About to start implementation (need to find similar patterns)
- Want to avoid reinventing the wheel (find existing solutions)
- Need to know dependencies (what imports, AWS resources)
- Looking for test examples (how to test similar feature)

**❌ Don't use when**:
- Exploring alternatives (use `/explore` instead)
- Learning concepts (use `/understand` or `/consolidate`)
- Already know where to look (just read the files)
- No similar patterns exist yet (first implementation)

---

## Usage

```bash
# Backend tasks
/context "Add rate limiting to API endpoints"
/context "Implement pagination for ticker list"
/context "Add caching to expensive Aurora queries"

# Frontend tasks
/context "Add loading skeleton to portfolio page"
/context "Implement dark mode toggle"
/context "Add chart filtering by date range"

# Infrastructure tasks
/context "Add CloudWatch alarm for Lambda errors"
/context "Set up S3 lifecycle policy for data lake"
/context "Configure Aurora read replica"

# Testing tasks
/context "Write E2E test for report generation flow"
/context "Add property-based tests for ticker validation"
```

---

## Output Structure

```markdown
# Context: {Task Description}

**Generated**: 2025-12-28
**Task Type**: {Backend/Frontend/Infrastructure/Testing}
**Estimated Effort**: {X} hours (based on similar tasks)

---

## Relevant Files to Read (3-5 most relevant)

### File 1: `{path}`
**Why relevant**: {Explanation}
**What to look for**: {Specific patterns, functions, or sections}
**Lines to focus on**: {Line ranges}

### File 2: `{path}`
**Why relevant**: {Explanation}
**What to look for**: {Specific patterns}
**Lines to focus on**: {Line ranges}

[Continue for 3-5 files]

---

## Files You'll Likely Modify

1. **`{path}`** - {What you'll change}
2. **`{path}`** - {What you'll add}
3. **`{path}`** - {Tests to update}

---

## Similar Implementations

### Pattern 1: {Description}
**Location**: `{file}:{lines}`
**Code Snippet**:
```python
# Example of similar implementation
def existing_pattern():
    # Pattern to follow
    pass
```

**Why similar**: {Explanation of similarity}
**Adapt by**: {What to change for your task}

---

### Pattern 2: {Description}
**Location**: `{file}:{lines}`
[Similar structure]

---

## Dependencies

### Imports Required (Python)
```python
from fastapi import HTTPException
from src.services.cache import get_cache, set_cache
from pydantic import BaseModel
```

### Imports Required (TypeScript)
```typescript
import { useQuery } from '@tanstack/react-query'
import { create } from 'zustand'
```

### AWS Resources Needed
- **Lambda**: Already has permissions (no changes)
- **DynamoDB**: May need new table or GSI
- **S3**: May need new bucket or prefix

---

## Related Documentation

### Core Principles (from CLAUDE.md)
- **Defensive Programming** - Validate inputs, fail fast
- **Multi-Layer Verification** - Check status, payload, logs
- **Aurora-First Data Architecture** - Read from Aurora, no external APIs

**Relevant sections**:
- `.claude/CLAUDE.md#defensive-programming`
- `.claude/CLAUDE.md#multi-layer-verification`

---

### Patterns (from skills/docs)
- **Testing**: `.claude/skills/testing-workflow/` - Test patterns to follow
- **API Design**: `docs/PROJECT_CONVENTIONS.md#adding-api-endpoints`
- **State Management**: `docs/frontend/UI_PRINCIPLES.md#state-management`

---

## Related Journal Entries

### Recent Related Work
1. **2025-12-20**: Added similar feature to scheduler
   - Location: `.claude/journals/pattern/2025-12-20-rate-limiting.md`
   - Key insight: Use slowapi library, not custom middleware

2. **2025-12-15**: Implemented caching pattern
   - Location: `.claude/journals/architecture/2025-12-15-dynamo-cache.md`
   - Key decision: DynamoDB over Redis for serverless

---

## Prerequisites

### Before Starting
- [ ] Read similar implementations above
- [ ] Understand dependencies required
- [ ] Review relevant principles

### Questions to Answer First
- [ ] {Question 1 about requirements}
- [ ] {Question 2 about edge cases}
- [ ] {Question 3 about performance}

---

## Recommended Approach

### Step 1: Read Similar Patterns
**Duration**: 15-20 min

Read similar implementations identified above. Understand:
- How they structure the code
- What edge cases they handle
- What tests they have

---

### Step 2: Design API Contract (if applicable)
**Duration**: 10-15 min

Define:
- Request schema (Pydantic model)
- Response schema
- Error responses
- Example usage

**Document in**: `spec/API_CONTRACT.md`

---

### Step 3: Implement Following Patterns
**Duration**: 1-2 hours

Follow existing patterns identified. Don't reinvent.
- Copy-paste-modify approach is OK
- Maintain consistency with codebase
- Add defensive checks (validation, error handling)

---

### Step 4: Test (Happy Path + Edge Cases)
**Duration**: 30-45 min

Write tests:
- Happy path (typical usage)
- Edge cases (empty input, invalid data, timeouts)
- Round-trip tests (if persistence)

**Pattern**: See similar tests in related files

---

### Step 5: Document
**Duration**: 10-15 min

Update:
- `spec/API_CONTRACT.md` (if new endpoint)
- `docs/PROJECT_CONVENTIONS.md` (if new pattern)
- Inline docstrings (if complex logic)

---

## Next Steps

### If Patterns Are Clear
```bash
# Start implementing directly
# (Similar patterns provide blueprint)
```

### If Design Needed
```bash
# Design first, then implement
/specify "{Task description}"
# → Generates detailed design specification
```

### If Requirements Unclear
```bash
# Clarify before starting
/what-if "compare approach A vs approach B"
# → Evaluates alternatives
```

---

## Estimated Effort Breakdown

**Total**: {X} hours

- Context gathering: 20 min (done by this command)
- Reading similar patterns: 15 min
- Design/specification: 10 min
- Implementation: 1-2 hours
- Testing: 30 min
- Documentation: 10 min
- Code review iterations: 30 min

---

## Related Commands

- `/explore` - Explore alternatives (when multiple options)
- `/consolidate` - Understand concepts (when learning)
- `/specify` - Design specification (when approach unclear)
- `/onboard` - Developer onboarding (when new to codebase)

---

## See Also

- `docs/PROJECT_CONVENTIONS.md` - Patterns and conventions
- `docs/CODE_STYLE.md` - Coding standards
- `docs/ARCHITECTURE_INVENTORY.md` - All tools/services
- `.claude/CLAUDE.md` - Core principles
```

---

## Examples

### Example 1: Backend Task

```bash
/context "Add rate limiting to API endpoints"
```

**Output**:

```markdown
# Context: Add rate limiting to API endpoints

**Task Type**: Backend
**Estimated Effort**: 2 hours

## Relevant Files

### 1. `src/api/middleware.py`
**Why**: Contains existing middleware (CORS, logging)
**What to look for**: Middleware structure, how to apply to routes
**Lines**: 15-45 (CORS middleware example)

### 2. `requirements.txt`
**Why**: Check if slowapi already installed
**What to look for**: Line with `slowapi`
**Lines**: 40 (slowapi>=0.1.9)

### 3. `tests/integration/test_rate_limit.py`
**Why**: Test patterns for rate limiting
**What to look for**: How to test 429 responses
**Lines**: Full file

## Files to Modify
1. `src/api/main.py` - Add rate limiter to FastAPI app
2. `src/api/endpoints.py` - Apply rate limit decorator to endpoints
3. `tests/integration/test_rate_limit.py` - Add tests

## Similar Implementation

### Pattern: slowapi Rate Limiter
**Location**: (To be implemented first time)
**Package Docs**: https://slowapi.readthedocs.io/

**Example**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/report/{ticker}")
@limiter.limit("10/minute")
async def get_report(ticker: str):
    # Rate limited to 10 requests per minute
    pass
```

## Dependencies

### Imports Required
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
```

### AWS Resources
- No new AWS resources needed
- Lambda concurrency may need adjustment if high traffic

## Related Documentation

- **Defensive Programming** - `.claude/CLAUDE.md#defensive-programming`
- **API Design Patterns** - `docs/PROJECT_CONVENTIONS.md#api-patterns`

## Recommended Approach

1. Install slowapi (already in requirements.txt)
2. Create limiter instance in `src/api/main.py`
3. Apply `@limiter.limit()` decorator to endpoints
4. Add exception handler for `RateLimitExceeded`
5. Test with `tests/integration/test_rate_limit.py`

**Estimated**: 2 hours
```

---

### Example 2: Frontend Task

```bash
/context "Add loading skeleton to portfolio page"
```

**Output**:

```markdown
# Context: Add loading skeleton to portfolio page

**Task Type**: Frontend
**Estimated Effort**: 1 hour

## Relevant Files

### 1. `frontend/twinbar/src/components/Skeleton.tsx`
**Why**: Existing skeleton component
**What to look for**: How to create pulse animation
**Lines**: Full file (~50 lines)

### 2. `frontend/twinbar/src/pages/Portfolio.tsx`
**Why**: Portfolio page to add skeleton to
**What to look for**: Data loading state (`isLoading` from useQuery)
**Lines**: 45-80 (useQuery hooks)

### 3. `frontend/twinbar/src/components/TickerCard.tsx`
**Why**: Component that needs skeleton while loading
**What to look for**: Component structure to replicate in skeleton
**Lines**: Full file

## Files to Modify
1. `frontend/twinbar/src/components/TickerCard.tsx` - Add TickerCardSkeleton
2. `frontend/twinbar/src/pages/Portfolio.tsx` - Show skeleton during loading
3. `frontend/twinbar/src/components/Skeleton.tsx` - Extend base skeleton if needed

## Similar Implementation

### Pattern: Existing Skeleton Component
**Location**: `frontend/twinbar/src/components/Skeleton.tsx`

**Code**:
```typescript
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-gray-300 dark:bg-gray-700 rounded ${className}`} />
  )
}
```

**Usage Example**:
```typescript
{isLoading ? (
  <Skeleton className="h-20 w-full" />
) : (
  <TickerCard ticker={ticker} />
)}
```

## Dependencies

### Imports Required
```typescript
import { Skeleton } from '@/components/Skeleton'
import { useQuery } from '@tanstack/react-query'
```

### Tailwind Classes
- `animate-pulse` - Built-in pulse animation
- `bg-gray-300` / `dark:bg-gray-700` - Light/dark mode colors

## Related Documentation

- **UI Principles** - `docs/frontend/UI_PRINCIPLES.md#loading-states`
- **Tailwind CSS** - https://tailwindcss.com/docs/animation

## Recommended Approach

1. Create `TickerCardSkeleton` component matching `TickerCard` layout
2. Update `Portfolio.tsx` to show skeleton when `isLoading === true`
3. Test loading state (artificially delay query with devtools)

**Estimated**: 1 hour
```

---

### Example 3: Infrastructure Task

```bash
/context "Add CloudWatch alarm for Lambda errors"
```

**Output**:

```markdown
# Context: Add CloudWatch alarm for Lambda errors

**Task Type**: Infrastructure
**Estimated Effort**: 1.5 hours

## Relevant Files

### 1. `terraform/modules/lambda/alarms.tf`
**Why**: Existing CloudWatch alarms for Lambda
**What to look for**: Alarm structure, metrics, thresholds
**Lines**: Full file (~120 lines)

### 2. `terraform/telegram_api.tf`
**Why**: Lambda function definition
**What to look for**: Function name, how to reference in Terraform
**Lines**: 35-60 (Lambda resource)

### 3. `terraform/modules/sns/main.tf`
**Why**: SNS topic for alarm notifications
**What to look for**: Topic ARN to use in alarm
**Lines**: 10-25 (SNS topic resource)

## Files to Modify
1. `terraform/modules/lambda/alarms.tf` - Add error rate alarm
2. `terraform/telegram_api.tf` - Enable alarm for telegram_api function

## Similar Implementation

### Pattern: Lambda Duration Alarm
**Location**: `terraform/modules/lambda/alarms.tf:45-65`

**Code**:
```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.function_name}-duration-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Average"
  threshold           = 10000  # 10 seconds

  dimensions = {
    FunctionName = var.function_name
  }

  alarm_actions = [var.sns_topic_arn]
}
```

**Adapt for errors**:
- Change `metric_name` to `"Errors"`
- Change `statistic` to `"Sum"`
- Change `threshold` to `5` (5 errors in 2 periods)

## Dependencies

### Terraform Resources
- `aws_cloudwatch_metric_alarm` - Alarm resource
- SNS topic ARN (already exists)
- Lambda function name (from variable)

### AWS Permissions
- `cloudwatch:PutMetricAlarm` (already granted in deployment policy)

## Related Documentation

- **CloudWatch Alarms** - https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- **Lambda Metrics** - https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html

## Recommended Approach

1. Copy existing duration alarm from `alarms.tf`
2. Modify for error metric (Errors, Sum, threshold=5)
3. Add to telegram_api module
4. Test with `terraform plan`
5. Apply with `terraform apply`

**Estimated**: 1.5 hours
```

---

## Decision Tree

```
Starting new task?
  │
  ├─ Similar patterns exist?
  │  ├─ YES → Use /context (find files, patterns, tests)
  │  └─ NO → First implementation (no context to gather)
  │
  ├─ Exploring alternatives?
  │  └─ Use /explore (not /context - wrong tool)
  │
  ├─ Learning concept?
  │  └─ Use /consolidate or /understand (not /context)
  │
  └─ Already know what to do?
     └─ Skip /context (just code)
```

---

## Anti-Patterns

### ❌ Using /context for Exploration

```bash
# Bad
/context "What caching solutions exist?"

# Good
/explore "Caching solutions for Lambda" --focus=performance
```

**Why bad**: /context is for focused task context, not broad exploration

---

### ❌ Using /context for Learning

```bash
# Bad
/context "How does Zustand work?"

# Good
/understand "Zustand state management"
```

**Why bad**: /context provides files to read, not conceptual explanations

---

### ❌ Using /context for Documentation

```bash
# Bad
/context "What AWS services do we use?"

# Good
Read docs/ARCHITECTURE_INVENTORY.md
```

**Why bad**: Static documentation already exists, no need for context extraction

---

## Maintenance

### Update Triggers
- New patterns added to codebase (update similar implementations)
- Directory structure changes (update file paths)
- New documentation added (update related docs section)

### Quality Checks
- [ ] Relevant files are actually relevant (not generic)
- [ ] Similar patterns are truly similar (not superficial match)
- [ ] Dependencies are complete (no missing imports)
- [ ] Estimated effort is realistic (±50% of actual)

---

## Success Metrics

**Context is valuable when**:
- [ ] User starts with context files (not random exploration)
- [ ] Similar patterns are copy-paste-modified (not reinvented)
- [ ] All dependencies identified upfront (no surprises mid-task)
- [ ] Estimated effort is accurate (±1 hour for 2-3 hour task)
- [ ] User completes task faster than without context

---

## See Also

- `/explore` - Divergent exploration of alternatives
- `/consolidate` - Concept understanding and synthesis
- `/specify` - Detailed design specification
- `/onboard` - Developer onboarding (broader context)
- `docs/PROJECT_CONVENTIONS.md` - Conventions and patterns
- `docs/ARCHITECTURE_INVENTORY.md` - Complete tool inventory
