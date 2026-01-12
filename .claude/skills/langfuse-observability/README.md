# Langfuse Observability Skill

**Purpose**: Workflows for LLM observability, tracing, scoring, and evaluation using Langfuse.

**When to use**:
- Adding observability to new LLM operations
- Investigating quality issues via traces
- Setting up evaluation pipelines
- Managing prompt versions

**Quick Links**:
- [SCHEMA.md](./SCHEMA.md) - Complete column reference and hierarchy
- [CHECKLIST.md](./CHECKLIST.md) - Verification checklists

---

## Quick Reference

### Instrument New Operation

```python
from src.evaluation import observe, score_current_trace, flush

@observe(name="my_operation")
def my_llm_operation(input_data):
    result = llm.generate(input_data)

    # Score if high-value output
    score_current_trace("quality", evaluate(result))

    return result

# In Lambda handler
def handler(event, context):
    result = my_llm_operation(event)
    flush()  # Critical!
    return result
```

### View Traces

1. Go to: https://us.cloud.langfuse.com
2. Click **Traces** in left sidebar
3. Filter by name, time, or user
4. Click trace to see hierarchy and scores

### Debug Quality Issues

1. Find low-scoring traces in Langfuse
2. Inspect inputs/outputs at each step
3. Identify where quality degraded
4. Extract example to dataset for testing

---

## Workflows

### 1. Adding Tracing to New Feature

**Checklist**:
- [ ] Import: `from src.evaluation import observe, flush`
- [ ] Add `@observe(name="descriptive_name")` to entry point
- [ ] Add `flush()` before Lambda returns
- [ ] Test locally with `doppler run --config dev_local`
- [ ] Verify trace appears in Langfuse UI

**Example**:
```python
from src.evaluation import observe, flush

@observe(name="backtest_strategy")
def backtest_strategy(ticker: str, params: dict):
    data = fetch_historical_data(ticker)
    results = run_backtest(data, params)
    return results

def lambda_handler(event, context):
    result = backtest_strategy(event["ticker"], event["params"])
    flush()
    return {"statusCode": 200, "body": result}
```

---

### 2. Adding Quality Scores

**When to score**:
- Final user-facing outputs (reports, responses)
- Critical intermediate steps (retrieval quality)
- Operations you want to track over time

**Checklist**:
- [ ] Determine what to score (correctness, relevance, etc.)
- [ ] Choose scorer type (static rule-based or LLM-as-judge)
- [ ] Call `score_current_trace()` within `@observe` context
- [ ] Verify scores appear on trace in Langfuse

**Example**:
```python
from src.evaluation import observe, score_current_trace

@observe(name="generate_report")
def generate_report(ticker: str):
    report = llm.generate(build_prompt(ticker))

    # Score the output
    quality = evaluate_report_quality(report)
    score_current_trace("report_quality", quality.score, quality.comment)

    return report
```

---

### 3. Investigating Quality Issues

**Workflow**:

1. **Identify problem traces**:
   - Go to Langfuse → Traces
   - Filter by low scores or time range
   - Sort by score ascending

2. **Analyze trace hierarchy**:
   - Click on problem trace
   - View each span/generation
   - Compare inputs vs outputs

3. **Find root cause**:
   - Did input data look correct?
   - Did LLM receive proper context?
   - Was prompt appropriate?
   - Did scoring work correctly?

4. **Extract for dataset**:
   - Copy problematic input
   - Create dataset item in Langfuse
   - Use for regression testing

**Common issues**:
| Symptom | Likely Cause |
|---------|--------------|
| Low faithfulness | Missing/stale data in context |
| Low completeness | Prompt missing required sections |
| Low consistency | Contradictory data in context |
| All scores low | LLM model issue or prompt problem |

---

### 4. Setting Up Evaluation Pipeline

**Offline Evaluation** (before deployment):

1. **Create dataset**:
   - Langfuse UI → Datasets → Create
   - Add 20-30 representative examples
   - Include expected outputs

2. **Run experiment**:
   ```python
   from langfuse import Langfuse

   langfuse = Langfuse()
   dataset = langfuse.get_dataset("daily-reports-test")

   for item in dataset.items:
       result = generate_report(item.input)
       langfuse.score(
           trace_id=result.trace_id,
           name="accuracy",
           value=compare(result.output, item.expected_output)
       )
   ```

3. **Analyze results**:
   - Compare scores across runs
   - Identify regression patterns
   - Update prompts if needed

**Online Evaluation** (in production):

1. **Collect implicit feedback**:
   - Track session duration
   - Count follow-up questions
   - Monitor retry rate

2. **Collect explicit feedback**:
   - Add thumbs up/down to UI
   - Push as scores to Langfuse

3. **Alert on degradation**:
   - Set up Langfuse alerts
   - Monitor score trends

---

### 5. Prompt Version Management (Future)

**Current state**: Prompts in `src/prompts/prompt_builder.py`

**Target state**: Prompts in Langfuse

**Migration workflow**:

1. **Extract prompt to Langfuse**:
   - Copy prompt text to Langfuse UI
   - Create version v1
   - Label as "production"

2. **Update code to fetch**:
   ```python
   from langfuse import Langfuse

   langfuse = Langfuse()

   def get_report_prompt():
       return langfuse.get_prompt("daily-report", label="production")
   ```

3. **Iterate safely**:
   - Create new version in UI
   - Test against dataset
   - Update label when ready

**Benefits**:
- Non-engineers can edit prompts
- Instant rollback via label change
- No code deployment for prompt changes

---

## Checklists

### Pre-Deployment Observability Check

Before deploying LLM feature:

- [ ] Entry point has `@observe` decorator
- [ ] Lambda handler calls `flush()` before return
- [ ] High-value outputs have quality scores
- [ ] Environment has `LANGFUSE_*` keys configured
- [ ] Tested locally and verified trace in UI

### Quality Investigation Checklist

When investigating low scores:

- [ ] Identified specific low-scoring traces
- [ ] Reviewed input data quality
- [ ] Reviewed LLM prompt and context
- [ ] Reviewed output vs expected
- [ ] Identified root cause
- [ ] Created dataset item for regression test
- [ ] Fixed issue and verified improvement

### Prompt Update Checklist

When updating prompts:

- [ ] Created new version in Langfuse (don't edit existing)
- [ ] Tested against evaluation dataset
- [ ] Compared scores to baseline
- [ ] Updated label only after validation
- [ ] Monitored production scores post-deployment

---

## Anti-Patterns

### Don't Score Everything

```python
# BAD - scoring infrastructure
@observe(name="fetch_cache")
def fetch_cache(key):
    result = cache.get(key)
    score_current_trace("cache_hit", 1 if result else 0)  # Unnecessary!
    return result

# GOOD - score user value
@observe(name="generate_report")
def generate_report(data):
    report = llm.generate(data)
    score_current_trace("quality", evaluate(report))  # Meaningful!
    return report
```

### Don't Forget Flush

```python
# BAD - traces may be lost in Lambda
def handler(event, context):
    return process(event)

# GOOD - ensures traces sent
def handler(event, context):
    result = process(event)
    flush()
    return result
```

### Don't Block on Scoring

```python
# BAD - synchronous heavy evaluation
@observe(name="generate")
def generate(data):
    result = llm.generate(data)
    heavy_evaluation(result)  # Blocks response!
    return result

# GOOD - score lightweight, heavy eval async
@observe(name="generate")
def generate(data):
    result = llm.generate(data)
    quick_score(result)  # Fast static check
    return result

# Heavy eval runs separately via Langfuse evaluation engine
```

---

## Configuration

Per [Principle #23: Configuration Variation Axis](../../CLAUDE.md) (Tier-0), Langfuse configuration follows clear separation between env vars (vary by environment/secret) and constants (never vary).

### Environment Variables (Doppler)

Set via Doppler, read once at startup:

| Variable | Type | Purpose |
|----------|------|---------|
| `LANGFUSE_PUBLIC_KEY` | Secret | API authentication |
| `LANGFUSE_SECRET_KEY` | Secret | API authentication |
| `LANGFUSE_HOST` | Environment | API endpoint URL |
| `LANGFUSE_RELEASE` | Environment | Version identifier (`dev-local`, `dev`, `stg`, `prd`) |
| `LANGFUSE_TRACING_ENVIRONMENT` | Environment | Environment tag (`local`, `dev`, `stg`, `prd`) |

### Python Constants

Values that NEVER vary are Python constants in `src/config.py`:

```python
from src.config import TRACE_NAMES, OBSERVATION_NAMES, SCORE_NAMES, TRACE_TAGS

# Use in @observe decorators
@observe(name=TRACE_NAMES.ANALYZE_TICKER)
def analyze_ticker():
    ...

# Use for scoring
score_current_trace(SCORE_NAMES.FAITHFULNESS, 85)

# Use for tagging
trace_context(tags=[TRACE_TAGS.REPORT_GENERATION])
```

| Constant Class | Purpose | Examples |
|----------------|---------|----------|
| `TRACE_NAMES` | Root-level trace names | `ANALYZE_TICKER`, `TEST_SCORING` |
| `OBSERVATION_NAMES` | Span/observation names | `FETCH_DATA`, `GENERATE_REPORT` |
| `SCORE_NAMES` | Quality score names | `FAITHFULNESS`, `COMPLETENESS` |
| `TRACE_TAGS` | Standard tag values | `REPORT_GENERATION`, `TEST`, `CLI` |
| `DEFAULT_USER_ID` | Default user ID | `"anak"` |

### Trace Context (Runtime)

Set dynamically per trace via `trace_context()`:

```python
from src.evaluation import observe, trace_context

@observe(name="analyze_ticker")
def analyze_ticker(ticker: str, user_id: str = None):
    with trace_context(
        user_id=user_id or DEFAULT_USER_ID,
        session_id=f"daily_{date.today().isoformat()}",
        tags=[TRACE_TAGS.REPORT_GENERATION],
        metadata={"ticker": ticker, "model": "gpt-4o-mini"}
    ):
        ...
```

### Dynamic Levels

Set observation/trace levels for error filtering:

```python
from src.evaluation import set_observation_level, set_trace_level

@observe(name="fetch_data")
def fetch_data(ticker: str):
    data = get_aurora_data(ticker)
    if data is None:
        set_observation_level("ERROR")  # Mark observation as error
        return None
    return data

# At trace level (in agent.py)
final_state = self.graph.invoke(initial_state)
if final_state.get("error"):
    set_trace_level("ERROR")  # Mark entire trace as error
```

**Level meanings**:
- `DEFAULT`: Normal successful execution
- `WARNING`: Degraded path (optional step failed)
- `ERROR`: Critical failure (required step failed)

---

## Related

- [SCHEMA.md](./SCHEMA.md) - Complete trace hierarchy and column reference
- [Langfuse Integration Guide](../../../docs/guides/langfuse-integration.md)
- [Scoring Service](../../../src/scoring/scoring_service.py)
- [Quality Scorers](../../../src/scoring/)
- [Langfuse Official Docs](https://langfuse.com/docs)
- [Principle #22: LLM Observability Discipline](../principles/integration-principles.md)
- [Principle #23: Configuration Variation Axis](../../CLAUDE.md) (Tier-0)
