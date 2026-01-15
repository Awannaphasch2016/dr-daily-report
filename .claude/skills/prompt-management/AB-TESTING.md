# A/B Testing Prompts

**Reference**: Setting up and running prompt experiments.

---

## A/B Testing Architecture

```
                    ┌──────────────┐
                    │   Request    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Random      │
                    │  Selection   │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │  Variant A  │          │  Variant B  │
       │  (prod-a)   │          │  (prod-b)   │
       └──────┬──────┘          └──────┬──────┘
              │                         │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │   Track      │
                    │   Metrics    │
                    └──────────────┘
```

---

## Setup Steps

### 1. Create Variant Versions

In Langfuse UI:
1. Create `dr-report-main` v5 (Variant A)
2. Create `dr-report-main` v6 (Variant B)

### 2. Assign Labels

```
v5 ← prod-a
v6 ← prod-b
```

### 3. Implement Random Selection

```python
import random

def get_ab_variant() -> str:
    """Randomly select A/B variant."""
    return random.choice(["prod-a", "prod-b"])

def get_prompt_for_request(prompt_name: str) -> PromptResult:
    """Get prompt with A/B variant selection."""
    variant = get_ab_variant()
    return prompt_service.get_prompt(prompt_name, label=variant)
```

### 4. Track Variant in Traces

```python
def generate_report(ticker: str) -> str:
    variant = get_ab_variant()
    prompt = prompt_service.get_prompt("dr-report-main", label=variant)

    # Track variant in Langfuse trace
    with langfuse.trace(
        name="report_generation",
        metadata={"ab_variant": variant}
    ) as trace:
        result = llm.invoke(prompt.content)
        trace.update(output=result)

    return result
```

---

## Metric Collection

### Key Metrics to Track

| Metric | Description | How to Measure |
|--------|-------------|----------------|
| **Latency** | Response time | `trace.duration` |
| **Token Usage** | Input + output tokens | `trace.usage` |
| **User Satisfaction** | Thumbs up/down | User feedback |
| **Error Rate** | Failed generations | `trace.status` |
| **Accuracy** | Correct information | Manual review |

### Langfuse Score Integration

```python
def record_user_feedback(trace_id: str, score: int, comment: str = None):
    """Record user feedback as Langfuse score."""
    langfuse.score(
        trace_id=trace_id,
        name="user_satisfaction",
        value=score,  # 1-5 scale
        comment=comment,
    )
```

---

## Analysis Queries

### Compare Variants in Langfuse

Filter traces by metadata:

```
metadata.ab_variant = "prod-a"
metadata.ab_variant = "prod-b"
```

### Export for Analysis

```python
# Export traces for statistical analysis
traces_a = langfuse.get_traces(
    filter={"metadata.ab_variant": "prod-a"},
    limit=1000,
)

traces_b = langfuse.get_traces(
    filter={"metadata.ab_variant": "prod-b"},
    limit=1000,
)

# Calculate metrics
avg_latency_a = sum(t.duration for t in traces_a) / len(traces_a)
avg_latency_b = sum(t.duration for t in traces_b) / len(traces_b)
```

---

## Statistical Significance

### Sample Size Calculator

```python
import math

def required_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> int:
    """Calculate required sample size per variant."""
    # Simplified formula
    z_alpha = 1.96  # 95% confidence
    z_beta = 0.84   # 80% power

    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_detectable_effect)

    n = (2 * ((z_alpha + z_beta) ** 2) * p1 * (1 - p1)) / ((p2 - p1) ** 2)
    return math.ceil(n)

# Example: Detect 10% improvement in satisfaction (baseline 70%)
sample_size = required_sample_size(0.7, 0.1)
# → ~300 samples per variant
```

### When to Conclude

| Samples | Confidence | Action |
|---------|------------|--------|
| <100 | Low | Keep running |
| 100-300 | Medium | Review trends |
| >300 | High | Make decision |

---

## A/B Test Lifecycle

```
1. Hypothesis
   "Adding few-shot examples will improve accuracy by 10%"

2. Setup
   - Create variants (v5 = control, v6 = treatment)
   - Assign labels (prod-a, prod-b)
   - Deploy random selection code

3. Run
   - Collect data for 1-2 weeks
   - Monitor for errors
   - Don't peek too early

4. Analyze
   - Compare metrics by variant
   - Check statistical significance
   - Document findings

5. Conclude
   - Winner → Promote to production
   - Loser → Archive or iterate
   - Inconclusive → Run longer or redesign
```

---

## Implementation Example

### Full A/B Test Flow

```python
# src/report/report_generator_ab.py
import random
from langfuse import Langfuse

class ABTestReportGenerator:
    def __init__(self):
        self.langfuse = Langfuse()
        self.prompt_service = PromptService()

    def generate(self, ticker: str, user_id: str) -> str:
        # 1. Select variant (consistent per user for session)
        variant = self._get_user_variant(user_id)

        # 2. Get prompt for variant
        prompt = self.prompt_service.get_prompt(
            "dr-report-main",
            label=variant
        )

        # 3. Generate with tracing
        with self.langfuse.trace(
            name="ab_test_generation",
            user_id=user_id,
            metadata={
                "ab_variant": variant,
                "prompt_version": prompt.version,
            }
        ) as trace:
            result = self._generate_report(ticker, prompt)
            trace.update(output=result)

        return result

    def _get_user_variant(self, user_id: str) -> str:
        """Consistent variant per user (sticky assignment)."""
        # Hash user_id for consistent assignment
        hash_val = hash(user_id) % 100
        return "prod-a" if hash_val < 50 else "prod-b"
```

---

## Best Practices

### Do

- ✅ Define clear hypothesis before starting
- ✅ Calculate required sample size upfront
- ✅ Use sticky assignment (same user = same variant)
- ✅ Track all relevant metrics from start
- ✅ Document experiment setup and results

### Don't

- ❌ Peek at results too early
- ❌ Change variants mid-experiment
- ❌ Conclude without statistical significance
- ❌ Run multiple tests on same traffic
- ❌ Forget to track error rates

---

## References

- [SKILL.md](SKILL.md) - Overview
- [VERSIONING.md](VERSIONING.md) - Version management
- [OBSERVABILITY.md](OBSERVABILITY.md) - Metrics and monitoring
- [Langfuse A/B Testing](https://langfuse.com/docs/prompts/example-experiment-tracking)
