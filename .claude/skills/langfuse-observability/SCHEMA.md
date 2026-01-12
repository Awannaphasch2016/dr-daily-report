# Langfuse Tracing Schema Reference

**Purpose**: Complete reference for Langfuse trace structure, columns, and relationships.

**Related**: [Configuration](./README.md#configuration), [Principle #22](../principles/integration-principles.md), [Principle #23](../../CLAUDE.md) (Tier-0)

---

## Hierarchy Overview

```
Trace (root)
├── id, name, timestamp, user_id, session_id, tags, metadata, release, environment, level
├── input (function args), output (return value)
│
├── Observation/Span (nested @observe)
│   ├── id, name, timestamp, level
│   ├── input, output, latency
│   │
│   ├── Generation (LLM call via LangChain callback)
│   │   ├── id, name, model, timestamp
│   │   ├── input (prompt), output (completion)
│   │   ├── tokens (prompt_tokens, completion_tokens, total_tokens)
│   │   ├── cost (input_cost, output_cost, total_cost)
│   │   └── latency
│   │
│   └── Observation/Span (nested)
│       └── ...recursive
│
└── Score (attached to trace)
    ├── name, value (0-1), comment
    └── Can have multiple scores per trace
```

---

## Column Reference

### Trace Columns (Root Level)

| Column | Type | Set Via | When Set | Description |
|--------|------|---------|----------|-------------|
| `id` | string | Auto | Creation | Unique trace identifier |
| `name` | string | `@observe(name="...")` | Creation | Trace name for filtering |
| `timestamp` | datetime | Auto | Creation | Trace start time |
| `input` | JSON | Auto | Creation | Function arguments captured |
| `output` | JSON | Auto | Completion | Function return value captured |
| `latency` | float | Auto | Completion | Execution duration (ms) |
| `user_id` | string | `trace_context(user_id=...)` | Runtime | User identifier |
| `session_id` | string | `trace_context(session_id=...)` | Runtime | Session grouping |
| `tags` | string[] | `trace_context(tags=[...])` | Runtime | Filterable tags |
| `metadata` | JSON | `trace_context(metadata={...})` | Runtime | Key-value metadata |
| `release` | string | `LANGFUSE_RELEASE` env var | Client init | Version identifier (format: `{env}-{version}-{sha}`) |
| `environment` | string | `LANGFUSE_TRACING_ENVIRONMENT` env var | Client init | Environment name |
| `level` | enum | `set_trace_level(...)` | Runtime | DEBUG/DEFAULT/WARNING/ERROR |

### Observation/Span Columns (Nested)

| Column | Type | Set Via | When Set | Description |
|--------|------|---------|----------|-------------|
| `id` | string | Auto | Creation | Unique observation identifier |
| `name` | string | `@observe(name="...")` | Creation | Observation name |
| `parent_id` | string | Auto | Creation | Parent trace/observation ID |
| `timestamp` | datetime | Auto | Creation | Observation start time |
| `input` | JSON | Auto | Creation | Function arguments |
| `output` | JSON | Auto | Completion | Function return value |
| `latency` | float | Auto | Completion | Execution duration (ms) |
| `level` | enum | `set_observation_level(...)` | Runtime | DEBUG/DEFAULT/WARNING/ERROR |

### Generation Columns (LLM Calls)

| Column | Type | Set Via | When Set | Description |
|--------|------|---------|----------|-------------|
| `id` | string | Auto | Creation | Unique generation identifier |
| `name` | string | Auto/LangChain | Creation | Model call name |
| `model` | string | LangChain callback | Creation | Model identifier (e.g., "gpt-4o-mini") |
| `input` | JSON | LangChain callback | Creation | Prompt/messages sent |
| `output` | JSON | LangChain callback | Completion | Model response |
| `prompt_tokens` | int | LangChain callback | Completion | Input token count |
| `completion_tokens` | int | LangChain callback | Completion | Output token count |
| `total_tokens` | int | LangChain callback | Completion | Total token count |
| `input_cost` | float | Auto (model pricing) | Completion | Input cost (USD) |
| `output_cost` | float | Auto (model pricing) | Completion | Output cost (USD) |
| `total_cost` | float | Auto (model pricing) | Completion | Total cost (USD) |
| `latency` | float | Auto | Completion | LLM response time (ms) |

### Score Columns

| Column | Type | Set Via | When Set | Description |
|--------|------|---------|----------|-------------|
| `name` | string | `score_current_trace(name=...)` | Runtime | Score name |
| `value` | float | `score_current_trace(value=...)` | Runtime | Score value (0-1 normalized) |
| `comment` | string | `score_current_trace(comment=...)` | Runtime | Optional explanation |
| `trace_id` | string | Auto | Runtime | Associated trace ID |

---

## Column Relationships

### Inheritance (What Propagates)

```
Langfuse Client (singleton)
    │
    ├── release ─────────────► All traces in this client session
    ├── environment ─────────► All traces in this client session
    │
    └── Trace
        ├── user_id ─────────► Visible on trace only (not observations)
        ├── session_id ──────► Groups traces together
        ├── tags ────────────► Visible on trace only
        ├── metadata ────────► Visible on trace only
        │
        └── Observations
            └── (each has own input/output/level, inherits trace_id)
```

### What Does NOT Propagate

| From | Column | To | Behavior |
|------|--------|----|----------|
| Trace | `user_id` | Observations | NOT inherited - trace-level only |
| Trace | `tags` | Observations | NOT inherited - trace-level only |
| Trace | `metadata` | Observations | NOT inherited - trace-level only |
| Trace | `level` | Observations | NOT inherited - each has own level |
| Observation | `level` | Child observations | NOT inherited - each has own level |

### Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ Langfuse Client (Singleton)                                     │
│ Set at: Lambda cold start                                       │
│ Columns: release, environment, host                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ creates
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Trace (Root)                                                     │
│ Created by: @observe on outermost function                      │
│ Set at creation: id, name, timestamp, input                     │
│ Set at completion: output, latency                              │
│ Set via trace_context(): user_id, session_id, tags, metadata   │
│ Set via set_trace_level(): level                                │
│ Inherited from client: release, environment                     │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Observation 1    │ │ Observation 2    │ │ Score            │
│ (Span)           │ │ (Span)           │ │                  │
│                  │ │                  │ │ name, value,     │
│ id, name, input, │ │ id, name, input, │ │ comment          │
│ output, latency, │ │ output, latency, │ │                  │
│ level            │ │ level            │ │ Attached to      │
│                  │ │                  │ │ trace_id         │
│ parent: trace    │ │ parent: trace    │ └──────────────────┘
└──────────────────┘ └──────────────────┘
         │
         ▼
┌──────────────────┐
│ Generation       │
│ (LLM Call)       │
│                  │
│ model, tokens,   │
│ cost, prompt,    │
│ completion       │
│                  │
│ parent: obs 1    │
└──────────────────┘
```

---

## Column Source Matrix

Where each column gets its value:

| Column | Env Var | Constructor | @observe | trace_context | set_*_level | score_* | Auto |
|--------|---------|-------------|----------|---------------|-------------|---------|------|
| release | `LANGFUSE_RELEASE` | ✅ | | | | | |
| environment | `LANGFUSE_TRACING_ENVIRONMENT` | ✅ | | | | | |
| name | | | ✅ | | | | |
| user_id | | | | ✅ | | | |
| session_id | | | | ✅ | | | |
| tags | | | | ✅ | | | |
| metadata | | | | ✅ | | | |
| level (trace) | | | | | ✅ | | |
| level (obs) | | | | | ✅ | | |
| score name | | | | | | ✅ | |
| score value | | | | | | ✅ | |
| id | | | | | | | ✅ |
| timestamp | | | | | | | ✅ |
| input | | | | | | | ✅ |
| output | | | | | | | ✅ |
| latency | | | | | | | ✅ |
| tokens | | | | | | | ✅* |
| cost | | | | | | | ✅* |

*Tokens and cost only appear on Generation nodes when using LangChain callback handler.

---

## Timing: When Columns Are Set

```
Lambda Cold Start
    │
    └── Langfuse() constructor
        └── release, environment set (from env vars)

Request Arrives
    │
    └── @observe(name="analyze_ticker") ─────► Trace created
        │                                       id, name, timestamp, input set
        │
        └── trace_context() ─────────────────► user_id, session_id, tags, metadata set
            │
            └── @observe(name="fetch_data") ─► Observation created
                │                               id, name, timestamp, input set
                │
                ├── (function executes)
                │
                ├── set_observation_level("ERROR") ─► level set (if error)
                │
                └── (function returns) ──────────► output, latency set

            └── @observe(name="generate_report")
                │
                ├── LLM call with callback ──────► Generation created
                │                                   model, prompt, completion,
                │                                   tokens, cost set
                │
                └── score_current_trace() ───────► Score attached to trace

        └── (workflow complete)
            │
            ├── set_trace_level("ERROR") ────────► trace level set (if error)
            │
            └── flush() ─────────────────────────► All data sent to Langfuse
```

---

## Level Values

| Level | Meaning | When to Use | Color in UI |
|-------|---------|-------------|-------------|
| `DEBUG` | Verbose tracing | Development debugging | Gray |
| `DEFAULT` | Normal execution | Success path (default) | Blue |
| `WARNING` | Degraded path | Fallback used, retry succeeded | Yellow |
| `ERROR` | Failure | Required step failed | Red |

### Level Setting Examples

```python
# Observation level - set within @observe function
@observe(name="fetch_data")
def fetch_data(ticker: str):
    data = get_aurora_data(ticker)
    if data is None:
        set_observation_level("ERROR")  # This observation failed
        return None
    return data

# Trace level - set at workflow end
@observe(name="analyze_ticker")
def analyze_ticker(ticker: str):
    with trace_context(user_id="anak"):
        result = run_workflow(ticker)
        if result.get("error"):
            set_trace_level("ERROR")  # Entire trace marked as error
        return result
```

---

## Tokens & Cost (Generation Only)

Tokens and cost columns **only appear on Generation nodes**, not on Traces or Observations.

### Requirements for Token Tracking

1. Use LangChain for LLM calls
2. Pass Langfuse callback handler
3. Model must be in Langfuse pricing database

```python
from src.evaluation import get_langchain_handler

handler = get_langchain_handler()
if handler:
    response = llm.invoke(messages, config={"callbacks": [handler]})
```

### Why test_scoring Has No Tokens

The `test_scoring` trace creates no Generation nodes because it:
- Doesn't make LLM calls
- Only runs static scoring functions
- Correct behavior - no tokens expected

---

## Common Patterns

### Pattern 1: Full Trace with All Columns

```python
from src.evaluation import observe, trace_context, score_current_trace, flush, set_trace_level
from src.config import TRACE_NAMES, TRACE_TAGS, SCORE_NAMES, DEFAULT_USER_ID

@observe(name=TRACE_NAMES.ANALYZE_TICKER)
def analyze_ticker(ticker: str, user_id: str = None):
    with trace_context(
        user_id=user_id or DEFAULT_USER_ID,
        session_id=f"daily_{date.today().isoformat()}",
        tags=[TRACE_TAGS.REPORT_GENERATION],
        metadata={"ticker": ticker, "model": "gpt-4o-mini"}
    ):
        result = run_workflow(ticker)

        # Score the result
        score_current_trace(SCORE_NAMES.FAITHFULNESS, result.faithfulness)
        score_current_trace(SCORE_NAMES.COMPLETENESS, result.completeness)

        # Set trace level if error
        if result.error:
            set_trace_level("ERROR")

        return result

# In Lambda handler
def handler(event, context):
    result = analyze_ticker(event["ticker"])
    flush()  # Critical!
    return result
```

### Pattern 2: Observation with Level

```python
from src.evaluation import observe, set_observation_level
from src.config import OBSERVATION_NAMES

@observe(name=OBSERVATION_NAMES.FETCH_DATA)
def fetch_data(ticker: str):
    data = get_aurora_data(ticker)

    if data is None:
        set_observation_level("ERROR")
        logger.error(f"No data for {ticker}")
        return {"error": f"No data for {ticker}"}

    if data.is_stale:
        set_observation_level("WARNING")
        logger.warning(f"Stale data for {ticker}")

    return data
```

---

## Validation Checklist

Before deploying, verify:

- [ ] `LANGFUSE_RELEASE` set in Doppler (shows in Version column)
- [ ] `LANGFUSE_TRACING_ENVIRONMENT` set in Doppler (shows in Environment column)
- [ ] Entry point uses `@observe` with descriptive name
- [ ] `trace_context()` called with user_id, session_id, tags
- [ ] `flush()` called before Lambda returns
- [ ] Scores attached for high-value outputs
- [ ] Levels set appropriately for errors/warnings

---

## Troubleshooting

### Empty Columns

| Empty Column | Cause | Fix |
|--------------|-------|-----|
| Release | `LANGFUSE_RELEASE` not set | Add to Doppler |
| Environment | `LANGFUSE_TRACING_ENVIRONMENT` not set | Add to Doppler |
| User | `trace_context(user_id=...)` not called | Add trace_context |
| Session | `trace_context(session_id=...)` not called | Add trace_context |
| Tags | `trace_context(tags=[...])` not called | Add trace_context |
| Tokens | No LangChain callback or no LLM calls | Use `get_langchain_handler()` |
| Cost | Model not in Langfuse pricing DB | Check model name |
| Scores | `score_current_trace()` not called | Add scoring |

### Level Not Showing

- Ensure `set_observation_level()` called within `@observe` decorated function
- Ensure `set_trace_level()` called within trace context
- Check logs for "Failed to set level" warnings

---

## See Also

- [README.md](./README.md) - Skill overview and configuration
- [CHECKLIST.md](./CHECKLIST.md) - Verification checklists
- [Langfuse Integration Guide](../../../docs/guides/langfuse-integration.md)
- [Langfuse Official Docs](https://langfuse.com/docs)
