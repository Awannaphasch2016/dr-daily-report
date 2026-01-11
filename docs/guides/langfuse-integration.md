# Langfuse Integration Guide

**Purpose**: LLM observability, evaluation, and prompt management for the Daily Report system.

**Related**: [PromptOS Architecture](../../.claude/overviews/promptos-infrastructure-overview.md), [Principle #2: Progressive Evidence Strengthening](../CLAUDE.md)

---

## Overview

Langfuse provides three core capabilities:

| Capability | What It Does | Our Usage |
|------------|--------------|-----------|
| **Tracing** | Capture LLM calls, inputs, outputs, timing | Track `analyze_ticker` workflow |
| **Scoring** | Attach quality metrics to traces | Push 5 quality scores per report |
| **Prompt Management** | Version and deploy prompts | Future: Manage report prompts |

For complete trace hierarchy and column reference, see [Trace Schema Reference](../../.claude/skills/langfuse-observability/SCHEMA.md).

---

## Current Implementation

### Architecture

```
agent.analyze_ticker()          ← @observe creates trace
  │
  ├── workflow_nodes.fetch_data()
  ├── workflow_nodes.generate_report()
  │     ├── LLM call (generation)
  │     └── scoring_service.compute_all_quality_scores()
  │           └── score_trace_batch()  ← Push 5 scores to Langfuse
  │
  └── flush()                   ← Ensure traces sent before Lambda shutdown
```

### Files

| File | Purpose |
|------|---------|
| `src/integrations/langfuse_client.py` | Core client, `@observe`, scoring functions |
| `src/evaluation/__init__.py` | Public API exports |
| `src/agent.py` | `@observe` on entry point, `flush()` before return |
| `src/workflow/workflow_nodes.py` | Quality scoring + Langfuse push (lines 878-926) |

### Environment Variables (Doppler)

Per [Principle #23: Configuration Variation Axis](../../.claude/CLAUDE.md), Langfuse configuration uses env vars because values vary by environment or contain secrets.

| Variable | Type | Purpose | Values |
|----------|------|---------|--------|
| `LANGFUSE_PUBLIC_KEY` | Secret | API authentication | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | Secret | API authentication | `sk-lf-...` |
| `LANGFUSE_HOST` | Environment-specific | API endpoint | `https://us.cloud.langfuse.com` |
| `LANGFUSE_RELEASE` | Environment-specific | Version identifier | `dev-local`, `dev`, `stg`, `prd` |
| `LANGFUSE_TRACING_ENVIRONMENT` | Environment-specific | Environment tag | `local`, `dev`, `stg`, `prd` |

### Python Constants

Values that NEVER vary across environments are Python constants (not env vars):

| Constant | Location | Purpose |
|----------|----------|---------|
| Trace names | `@observe(name="...")` in code | `analyze_ticker`, `test_scoring` |
| Span names | `@observe(name="...")` in workflow nodes | `fetch_data`, `generate_report`, etc. |
| Score names | `src/config/langfuse.py` | `faithfulness`, `completeness`, etc. |
| Score thresholds | `src/config/langfuse.py` | Min acceptable values |

### Trace Context Attributes

Set via `trace_context()` at runtime:

| Attribute | How Set | Example |
|-----------|---------|---------|
| `user_id` | `trace_context(user_id=...)` | `"anak"` (default) |
| `session_id` | `trace_context(session_id=...)` | `daily_YYYYMMDD` |
| `tags` | `trace_context(tags=...)` | `["report_generation"]` |
| `metadata` | `trace_context(metadata=...)` | `{ticker, workflow, model}` |

---

## API Reference

### @observe Decorator

Creates a trace (if outermost) or span (if nested) for the decorated function.

```python
from src.evaluation import observe

@observe(name="my_operation")
def my_function(arg1, arg2):
    # Automatically captures:
    # - Function inputs (arg1, arg2)
    # - Function output (return value)
    # - Execution time
    # - Errors (if raised)
    return result
```

**Parameters**:
- `name`: Optional trace/span name (defaults to function name)

**Behavior**:
- If Langfuse not configured (missing keys), executes function normally without tracing
- Thread-safe and async-safe (uses contextvars)

### score_current_trace()

Attach a score to the currently active trace. Must be called within an `@observe`-decorated function.

```python
from src.evaluation import score_current_trace

@observe(name="generate_report")
def generate_report():
    report = create_report()

    # Score the trace (0-100 scale, auto-normalized to 0-1)
    score_current_trace(
        name="quality",
        value=85.5,
        comment="Good numeric accuracy"
    )

    return report
```

**Parameters**:
- `name`: Score name (e.g., "faithfulness", "quality")
- `value`: Score value (0-100 scale, normalized to 0-1 for Langfuse)
- `comment`: Optional explanation

**Returns**: `True` if scored, `False` if Langfuse unavailable

### score_trace_batch()

Push multiple scores at once.

```python
from src.evaluation import score_trace_batch

@observe(name="evaluate")
def evaluate_report(report):
    scores = compute_all_scores(report)

    # Push all scores in one call
    langfuse_scores = {
        "faithfulness": (scores.faithfulness, "Sub-scores: ..."),
        "completeness": (scores.completeness, None),
        "reasoning_quality": (scores.reasoning, None),
    }

    pushed = score_trace_batch(langfuse_scores)
    print(f"Pushed {pushed} scores")
```

**Parameters**:
- `scores`: Dict mapping name to (value, comment) tuple

**Returns**: Count of successfully pushed scores

### flush()

Ensure all pending traces are sent to Langfuse. Critical for Lambda functions.

```python
from src.evaluation import flush

def lambda_handler(event, context):
    result = process(event)
    flush()  # Must call before returning!
    return result
```

---

## Quality Scores

We push 5 quality scores per report:

| Score | Type | What It Measures |
|-------|------|------------------|
| `faithfulness` | Static | Numeric accuracy vs ground truth |
| `completeness` | Static | Coverage of required analysis dimensions |
| `reasoning_quality` | Static | Clarity, specificity, structure |
| `compliance` | Static | Format and guideline adherence |
| `consistency` | LLM-as-Judge | Logical consistency (GPT-4o-mini) |

**Score Range**: 0-100 in our system, normalized to 0-1 for Langfuse.

---

## Viewing in Langfuse UI

### 1. Access Dashboard

Go to: https://us.cloud.langfuse.com

### 2. View Traces

1. Click **Traces** in left sidebar
2. Filter by:
   - Time range
   - Trace name (e.g., "analyze_ticker")
   - User ID (if tracked)
3. Click a trace to see full hierarchy

### 3. View Scores

1. Open a trace
2. Scroll to **Scores** section
3. See all 5 quality scores with values and comments

### 4. Analyze Trends

1. Go to **Analytics** or **Dashboards**
2. View score distributions over time
3. Identify quality degradation patterns

---

## Best Practices

### 1. Always Flush in Lambda

```python
# BAD - traces may be lost
def handler(event, context):
    return process(event)

# GOOD - ensures traces are sent
def handler(event, context):
    result = process(event)
    flush()
    return result
```

### 2. Score High-Value Operations

Focus scoring on operations that impact user value:

```python
# GOOD - score final output quality
@observe(name="generate_report")
def generate_report():
    report = llm.generate(...)
    score_current_trace("quality", evaluate(report))
    return report

# UNNECESSARY - don't score infrastructure
@observe(name="fetch_from_cache")
def fetch_from_cache():
    # Don't score cache hits/misses
    return cache.get(key)
```

### 3. Use Meaningful Trace Names

```python
# BAD - generic
@observe()
def process():
    ...

# GOOD - descriptive
@observe(name="analyze_ticker_DBS19")
def process():
    ...
```

### 4. Handle Langfuse Unavailability Gracefully

All Langfuse operations are non-blocking and fail silently:

```python
# This is safe - won't break if Langfuse is down
score_current_trace("quality", 85)  # Returns False if unavailable
```

---

## Troubleshooting

### Traces Not Appearing

1. **Check keys**: Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set
2. **Check flush**: Ensure `flush()` is called before Lambda returns
3. **Check logs**: Look for "Langfuse client initialized" message

### Scores Not Attached

1. **Check context**: `score_current_trace()` must be within `@observe`-decorated function
2. **Check logs**: Look for "Failed to score trace" warnings

### High Latency

Langfuse SDK is asynchronous by default. If experiencing latency:
- Ensure you're not calling `flush()` too frequently
- Check network connectivity to Langfuse host

---

## Future Enhancements

### Phase 1: User Tracking (Recommended)

Add user ID to traces for per-user analytics:

```python
@observe(name="analyze_ticker")
def analyze_ticker(self, ticker: str, user_id: str = None):
    # Langfuse will track metrics per user
    ...
```

### Phase 2: Prompt Management

Move prompts from `prompt_builder.py` to Langfuse:

```python
# Instead of hardcoded prompt
prompt = langfuse.get_prompt("daily-report-v2")
```

Benefits:
- Version prompts without code changes
- A/B test prompt versions
- Non-engineers can iterate prompts

### Phase 3: Evaluation Datasets

Create test datasets for systematic evaluation:

1. Create dataset in Langfuse UI
2. Add representative ticker reports
3. Run experiments against prompt versions
4. Compare quality scores

---

## Related Documentation

**Internal**:
- [Trace Schema Reference](../../.claude/skills/langfuse-observability/SCHEMA.md) - Complete column hierarchy and relationships
- [Langfuse Observability Skill](../../.claude/skills/langfuse-observability/) - Workflows and checklists
- [Principle #22: LLM Observability Discipline](../../.claude/CLAUDE.md)
- [Principle #23: Configuration Variation Axis](../../.claude/CLAUDE.md)

**External**:
- [Langfuse Official Docs](https://langfuse.com/docs)
- [Python SDK Reference](https://langfuse.com/docs/sdk/python)
- [Scoring Best Practices](https://langfuse.com/docs/evaluation/overview)
