# ADR-004: LangGraph TypedDict State

**Status:** ✅ Accepted
**Date:** 2024-01
**Deciders:** Development Team

## Context

The ticker analysis workflow has multiple steps (fetch data → analyze → generate report → evaluate) that need to pass state between nodes. We need an orchestration pattern that provides:

- Type safety for state fields
- Error propagation between nodes
- Observability of workflow execution
- Integration with LLM tracing tools

### Requirements

- Type hints for IDE autocomplete and static analysis
- State evolution visible in debugging tools
- Error handling that doesn't crash entire workflow
- LangSmith integration for LLM call tracing

## Decision

Use LangGraph with TypedDict state instead of custom orchestration.

### Implementation

```python
# src/types.py
from typing import TypedDict, Annotated, Sequence
import operator

class AgentState(TypedDict):
    """State dictionary for LangGraph workflow"""
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    ticker: str
    ticker_data: dict
    indicators: dict
    percentiles: dict
    news: list
    report: str
    error: str
    # ... all workflow fields

# src/agent.py
from langgraph.graph import StateGraph

workflow = StateGraph(AgentState)
workflow.add_node("fetch_data", fetch_data_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("generate_report", generate_report_node)
```

### State Management Pattern

- **Immutability**: Each node returns new state dict (doesn't mutate input)
- **Error Propagation**: `state["error"]` field instead of raising exceptions
- **Message Accumulation**: `Annotated[Sequence, operator.add]` auto-merges messages
- **Type Safety**: IDE autocomplete for all state fields

## Consequences

### Positive

- ✅ **Type Safety**: IDE autocomplete prevents typos in state field names
- ✅ **Type Checking**: Static analysis catches missing/wrong field types
- ✅ **LangSmith Integration**: Automatic tracing of workflow execution
- ✅ **Error Recovery**: `state["error"]` pattern enables resumable workflows
- ✅ **Observability**: See state evolution through each node in LangSmith traces
- ✅ **LangChain Ecosystem**: Integrates with LangChain tools, agents, memory

### Negative

- ❌ **Learning Curve**: Team must learn LangGraph concepts (nodes, edges, StateGraph)
- ❌ **Framework Lock-in**: Tied to LangChain/LangGraph ecosystem
- ❌ **Overhead**: LangGraph adds ~100ms per workflow execution
- ❌ **Debugging**: Stack traces go through LangGraph internals

### Mitigation

- TypedDict provides explicit contract (reduces LangGraph magic)
- Can extract logic from nodes for unit testing (not tied to LangGraph)
- LangSmith tracing compensates for debugging complexity

## Alternatives Considered

### Alternative 1: Custom Orchestration

**Example:**
```python
def analyze_ticker(ticker: str) -> dict:
    state = {}
    state['ticker_data'] = fetch_data(ticker)
    state['indicators'] = analyze(state['ticker_data'])
    state['report'] = generate_report(state)
    return state
```

**Why Rejected:**
- No automatic tracing (must implement manually)
- No type safety (plain dict)
- Error handling requires custom try/except everywhere
- No integration with LangSmith

### Alternative 2: Apache Airflow

**Why Rejected:**
- Overkill for single workflow (designed for complex DAGs)
- Requires infrastructure (Airflow server, database)
- No LLM-specific features
- Heavyweight for Lambda environment

### Alternative 3: Prefect

**Why Rejected:**
- Similar to Airflow (too heavyweight)
- No LLM-specific tracing
- Requires hosted Prefect server for observability

### Alternative 4: Plain Pydantic Models

**Example:**
```python
class WorkflowState(BaseModel):
    ticker: str
    ticker_data: dict
    indicators: dict
```

**Why Rejected:**
- No workflow orchestration (still need to write control flow)
- No automatic LangSmith integration
- LangGraph requires TypedDict specifically

## References

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **TypedDict**: https://docs.python.org/3/library/typing.html#typing.TypedDict
- **Implementation**: `src/types.py:AgentState`, `src/agent.py`
- **LangSmith**: https://docs.smith.langchain.com/

## Decision Drivers

1. **Observability**: LangSmith integration crucial for debugging LLM calls
2. **Type Safety**: TypedDict prevents entire class of runtime errors
3. **Ecosystem**: LangChain tools, agents, memory all integrate seamlessly

## Type Safety Example

```python
# IDE autocomplete works
state: AgentState = {...}
ticker = state["ticker"]  # ✅ IDE suggests "ticker"
data = state["tickr"]     # ❌ IDE shows error (typo)

# Type checker catches errors
state["ticker"] = 123     # ❌ Type checker: expected str, got int
```

## Error Propagation Pattern

```python
def analyze_node(state: AgentState) -> AgentState:
    # Check for upstream errors
    if state.get("error"):
        return state  # Skip execution, propagate error

    try:
        indicators = calculate_indicators(state["ticker_data"])
        return {**state, "indicators": indicators}
    except Exception as e:
        # Don't crash workflow, set error field
        return {**state, "error": str(e)}
```

**Benefit:** Workflow continues, collects all errors, fails gracefully.
