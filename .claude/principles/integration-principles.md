# Integration Principles Cluster

**Load when**: API integration, type system issues, error handling patterns, LLM operations

**Principles**: #4, #7, #8, #22

**Related skills**: [error-investigation](../skills/error-investigation/), [langfuse-observability](../skills/langfuse-observability/)

---

## Principle #4: Type System Integration Research

Research type compatibility BEFORE integrating heterogeneous systems (APIs, databases, message queues). Type mismatches cause silent failures.

**Research questions**:
1. What types does target accept?
2. What types does source produce?
3. How does target handle invalid types?

**Integration workflow**:
Convert types → handle special values → validate schema → verify outcome

**Common type mismatches**:
- Python `float('nan')` → JSON (JSON rejects NaN)
- Python `dict` → MySQL JSON column (needs `json.dumps()`)
- Python `None` → JSON `null` (different semantics)
- Python `datetime` → JSON string (needs serialization)

**Example**:
```python
# Python allows NaN
data = {'value': float('nan')}

# JSON spec rejects NaN - this will fail
json.dumps(data)  # ValueError

# Must sanitize before serialization
import math
sanitized = {'value': None if math.isnan(data['value']) else data['value']}
json.dumps(sanitized)  # Works
```

See [Type System Integration Guide](../../docs/TYPE_SYSTEM_INTEGRATION.md).

---

## Principle #7: Loud Mock Pattern

Mock/stub data in production code must be centralized, explicit, and loud. Register ALL mocks in centralized registry (`src/mocks/__init__.py`), log loudly at startup (WARNING level), gate behind environment variables (fail in production if unexpected mocks active), document why each mock exists (owner, date, reason).

**Valid uses**: Speeding local development.
**Invalid uses**: Hiding implementation gaps, bypassing security.

**Implementation**:
```python
# src/mocks/__init__.py
ACTIVE_MOCKS = {}

def register_mock(name, reason, owner):
    ACTIVE_MOCKS[name] = {'reason': reason, 'owner': owner}
    logger.warning(f"🚨 MOCK ACTIVE: {name} - {reason}")

# At startup
if os.environ.get('ENABLE_MOCKS') and os.environ.get('ENV') == 'production':
    raise RuntimeError("Mocks cannot be enabled in production")
```

---

## Principle #8: Error Handling Duality

Workflow nodes use state-based error propagation (collect all errors, enable resumable workflows). Utility functions raise descriptive exceptions (fail fast). Never mix patterns.

**Workflow nodes** (LangGraph):
```python
def workflow_node(state: AgentState) -> AgentState:
    try:
        result = do_work()
        return {**state, 'result': result}
    except Exception as e:
        # Collect error in state, don't raise
        return {**state, 'errors': state.get('errors', []) + [str(e)]}
```

**Utility functions**:
```python
def fetch_price(symbol: str) -> float:
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    # ... implementation
    # Don't return None on failure - raise exception
```

**Anti-pattern**: Functions returning `None` on failure create cascading silent failures.

See [Code Style Guide](../../docs/CODE_STYLE.md#error-handling-patterns).

---

## Principle #22: LLM Observability Discipline

Use Langfuse for LLM tracing, scoring, and prompt management. Every user-facing LLM operation must be traced. Quality scores enable trend analysis and regression detection. Langfuse provides Layer 3 evidence (Principle #2) for LLM operations.

**Tracing**:
```python
from langfuse.decorators import observe

@observe(name="generate_report")
def generate_report(ticker: str) -> dict:
    # LLM operations traced automatically
    ...

# CRITICAL: Lambda handlers must flush
def lambda_handler(event, context):
    result = generate_report(event['ticker'])
    langfuse.flush()  # Don't forget!
    return result
```

**Scoring**: Score high-value outputs (reports, responses), not infrastructure. 5 quality scores per report: faithfulness, completeness, reasoning_quality, compliance, consistency.

**Graceful degradation**: All Langfuse operations non-blocking. Core functionality works without Langfuse.

**Versioning**: Format `{env}-{version|branch}-{short_sha}`, set automatically by CI/CD via `LANGFUSE_RELEASE`.

See [Langfuse Integration Guide](../../docs/guides/langfuse-integration.md) and [langfuse-observability skill](../skills/langfuse-observability/).

---

## Quick Checklist

API Integration:
- [ ] Type compatibility researched
- [ ] Special values handled (NaN, null, infinity)
- [ ] Schema validated before/after conversion
- [ ] Outcome verified (not just status code)

Error Handling:
- [ ] Workflow nodes: state-based propagation
- [ ] Utility functions: raise exceptions
- [ ] No `None` returns on failure
- [ ] Errors are descriptive

LLM Operations:
- [ ] Entry point decorated with `@observe()`
- [ ] `flush()` called in Lambda handler
- [ ] High-value outputs scored
- [ ] LANGFUSE_RELEASE env var set

---

*Cluster: integration-principles*
*Last updated: 2026-01-12*
