# Prompt Observability

**Reference**: Monitoring prompt performance and LLM operations.

---

## Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Langfuse                             │
├─────────────────────────────────────────────────────────┤
│  Traces → Spans → Generations → Scores                  │
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │ Trace   │→ │ Span    │→ │ Gen     │→ │ Score   │    │
│  │ (req)   │  │ (step)  │  │ (LLM)   │  │ (eval)  │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Key Metrics

### Operational Metrics

| Metric | Description | Target | Alert |
|--------|-------------|--------|-------|
| **Latency** | E2E response time | <5s | >10s |
| **Error Rate** | Failed generations | <1% | >5% |
| **Token Usage** | Tokens per request | <4K | >8K |
| **Cost** | $ per request | <$0.05 | >$0.10 |

### Quality Metrics

| Metric | Description | Target | Alert |
|--------|-------------|--------|-------|
| **Accuracy** | Correct outputs | >95% | <90% |
| **User Satisfaction** | Feedback score | >4.0 | <3.5 |
| **Hallucination Rate** | Invalid numbers | 0% | >0% |

---

## Langfuse Integration

### Trace Structure

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

langfuse = Langfuse()

@observe()
def generate_report(ticker: str, user_id: str) -> str:
    """Top-level trace for report generation."""
    # Update trace with context
    langfuse_context.update_current_trace(
        user_id=user_id,
        metadata={
            "ticker": ticker,
            "environment": os.getenv("ENVIRONMENT"),
        }
    )

    # Steps become spans automatically
    context = prepare_context(ticker)
    report = call_llm(context)
    validated = validate_output(report)

    return validated
```

### Generation Tracking

```python
@observe(as_type="generation")
def call_llm(prompt: str, model: str = "claude-3-sonnet") -> str:
    """Track LLM call with token usage."""
    response = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    # Langfuse automatically captures:
    # - Input/output tokens
    # - Latency
    # - Model used

    return response.content[0].text
```

---

## Prompt Version Tracking

### Link Generation to Prompt

```python
def generate_with_prompt_tracking(ticker: str) -> str:
    """Track which prompt version generated output."""
    # Get prompt with metadata
    prompt_result = prompt_service.get_prompt(
        "dr-report-main",
        label="production"
    )

    with langfuse.trace(name="report_generation") as trace:
        # Link to prompt in Langfuse
        generation = trace.generation(
            name="llm_call",
            prompt=langfuse.get_prompt(
                "dr-report-main",
                version=prompt_result.version
            ),
            input=context,
        )

        result = llm.invoke(prompt_result.content)
        generation.end(output=result)

    return result
```

### Metadata for Debugging

```python
metadata = {
    "prompt_name": "dr-report-main",
    "prompt_version": 4,
    "prompt_source": "langfuse",  # or "file"
    "ab_variant": "prod-a",
    "ticker": "PTT",
    "environment": "production",
}
```

---

## Scoring and Evaluation

### Automatic Scores

```python
def score_generation(trace_id: str, report: str, ground_truth: dict):
    """Automatically score generation quality."""

    # 1. Placeholder completion
    unreplaced = report.count("{{")
    langfuse.score(
        trace_id=trace_id,
        name="placeholder_completion",
        value=1.0 if unreplaced == 0 else 0.0,
    )

    # 2. Length check
    word_count = len(report.split())
    langfuse.score(
        trace_id=trace_id,
        name="length_appropriate",
        value=1.0 if 100 <= word_count <= 300 else 0.5,
    )

    # 3. Language check (Thai)
    thai_ratio = count_thai_chars(report) / len(report)
    langfuse.score(
        trace_id=trace_id,
        name="thai_language",
        value=thai_ratio,
    )
```

### User Feedback Scores

```python
def record_user_feedback(trace_id: str, thumbs_up: bool, comment: str = None):
    """Record user feedback from UI."""
    langfuse.score(
        trace_id=trace_id,
        name="user_satisfaction",
        value=1.0 if thumbs_up else 0.0,
        comment=comment,
    )
```

---

## Dashboard Queries

### Filter by Prompt Version

```
# In Langfuse UI
metadata.prompt_version = 4
metadata.prompt_name = "dr-report-main"
```

### Compare Prompt Versions

```
# Version 3 performance
metadata.prompt_version = 3
→ avg latency, error rate, scores

# Version 4 performance
metadata.prompt_version = 4
→ avg latency, error rate, scores
```

### Find Errors

```
status = "error"
timestamp > 2024-01-15
```

---

## Alerting

### Error Rate Alert

```python
def check_error_rate():
    """Alert if error rate exceeds threshold."""
    traces = langfuse.get_traces(
        filter={"timestamp": {"gte": "1h ago"}},
        limit=100,
    )

    errors = sum(1 for t in traces if t.status == "error")
    error_rate = errors / len(traces) if traces else 0

    if error_rate > 0.05:  # 5% threshold
        send_alert(f"High error rate: {error_rate:.1%}")
```

### Latency Alert

```python
def check_latency():
    """Alert if latency exceeds threshold."""
    traces = langfuse.get_traces(
        filter={"timestamp": {"gte": "1h ago"}},
        limit=100,
    )

    avg_latency = sum(t.duration for t in traces) / len(traces)

    if avg_latency > 10:  # 10s threshold
        send_alert(f"High latency: {avg_latency:.1f}s")
```

---

## Cost Tracking

### Per-Request Cost

```python
def calculate_cost(trace) -> float:
    """Calculate cost for a trace."""
    # Claude pricing (example)
    input_cost_per_1k = 0.003
    output_cost_per_1k = 0.015

    input_tokens = trace.usage.get("input_tokens", 0)
    output_tokens = trace.usage.get("output_tokens", 0)

    cost = (input_tokens / 1000 * input_cost_per_1k +
            output_tokens / 1000 * output_cost_per_1k)

    return cost
```

### Daily Cost Report

```python
def daily_cost_report():
    """Generate daily cost summary."""
    traces = langfuse.get_traces(
        filter={"timestamp": {"gte": "24h ago"}},
    )

    total_cost = sum(calculate_cost(t) for t in traces)
    avg_cost = total_cost / len(traces) if traces else 0

    return {
        "total_requests": len(traces),
        "total_cost": total_cost,
        "avg_cost_per_request": avg_cost,
    }
```

---

## Debugging Workflow

### 1. Find Problematic Trace

```
# In Langfuse UI
status = "error"
OR
scores.user_satisfaction < 0.5
OR
metadata.ticker = "PROBLEM_TICKER"
```

### 2. Inspect Trace Details

- Input/output content
- Token usage
- Latency breakdown
- Prompt version used

### 3. Compare with Successful Traces

```
# Same ticker, successful
metadata.ticker = "PROBLEM_TICKER"
status = "success"
```

### 4. Check Prompt Changes

- What version was used?
- When was it last changed?
- What changed between versions?

---

## References

- [SKILL.md](SKILL.md) - Overview
- [VERSIONING.md](VERSIONING.md) - Version management
- [AB-TESTING.md](AB-TESTING.md) - Experiment tracking
- [Langfuse Tracing](https://langfuse.com/docs/tracing)
- [Langfuse Scores](https://langfuse.com/docs/scores)
