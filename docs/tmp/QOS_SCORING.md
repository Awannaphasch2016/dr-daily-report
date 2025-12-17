# QoS Scoring Documentation

## Overview

The QoS (Quality of Service) Score measures operational performance metrics of the ticker report generation system. Unlike content quality scores (Faithfulness, Completeness, Reasoning Quality, Compliance), QoS focuses on system performance, reliability, and efficiency.

**Version**: 1.0.0  
**Last Updated**: 2024

## Purpose

QoS scoring helps answer:
- How fast is the system? (Latency)
- How much does it cost to generate a report? (Cost Efficiency)
- Is the system consistent? (Determinism)
- How reliable is the system? (Reliability)
- Are resources used efficiently? (Resource Efficiency)
- How well does it scale? (Scalability)

## Scoring Dimensions

### 1. Latency (Weight: 25%)

Measures time taken to generate a report.

**Sub-components:**
- **Data Fetch Latency**: Time to fetch ticker data from Yahoo Finance
- **News Fetch Latency**: Time to fetch and process news
- **Technical Analysis Latency**: Time to calculate indicators and percentiles
- **Chart Generation Latency**: Time to generate chart image
- **LLM Generation Latency**: Time for OpenAI API calls
- **Scoring Latency**: Time to calculate all quality scores
- **Total End-to-End Latency**: Total time from request to response

**Scoring Thresholds:**
- **Excellent** (< 5s): 100 points
- **Good** (5-10s): 85 points
- **Acceptable** (10-20s): 70 points
- **Poor** (> 20s): 50 points

**Issues Detected:**
- Component latency exceeds thresholds
- Total latency > 20s

**Strengths:**
- Low total latency
- Cache hits reduce latency

---

### 2. Cost Efficiency (Weight: 20%)

Measures operational cost per report.

**Sub-components:**
- **LLM Token Usage**: Input/output tokens for OpenAI API calls
- **LLM API Cost**: Estimated cost based on model pricing (gpt-4o)
- **Database Operation Cost**: Number of queries (read/write operations)
- **External API Calls**: Number of Yahoo Finance API calls
- **Cost per Report**: Total estimated cost (normalized)

**Cost Calculation:**
- **Actual Cost**: Extracted from OpenAI API response metadata (if available)
- **Estimated Cost**: `(input_tokens * input_rate) + (output_tokens * output_rate)`
- **GPT-4o Pricing**: $2.50 per 1M input tokens, $10.00 per 1M output tokens

**Scoring Thresholds:**
- **Excellent** (< $0.05): 100 points
- **Good** ($0.05-0.10): 85 points
- **Acceptable** ($0.10-0.20): 70 points
- **Poor** (> $0.20): 50 points

**Issues Detected:**
- High cost per report
- Multiple LLM calls (> 2)

**Strengths:**
- Low cost per report
- Single LLM call optimized
- Cache hits reduce API costs

---

### 3. Determinism (Weight: 15%)

Measures consistency of deterministic components only.

**Note**: LLM output variance is NOT penalized (temperature is intentional design choice).

**Sub-components:**
- **Data Fetch Consistency**: Consistent timing for data fetching
- **Technical Analysis Consistency**: Consistent timing for calculations
- **Database Query Consistency**: Deterministic database operations

**Scoring:**
- Base score: 90 (assumes deterministic execution)
- Historical comparison: Checks variance in timing (< 20% variance is good)
- Database operations: Should be deterministic

**Issues Detected:**
- High variance in timing (> 20%) for deterministic components

**Strengths:**
- Consistent timing for deterministic components
- Database queries executed consistently

---

### 4. Reliability (Weight: 20%)

Measures success rate and error handling.

**Sub-components:**
- **Success Rate**: Percentage of successful report generations
- **Error Rate**: Percentage of requests that fail
- **Partial Success Rate**: Success with optional components missing
- **Timeout Rate**: Percentage of requests that timeout

**Scoring:**
- **No Errors**: 100 points
- **Error Occurred**: 30 points
- **Very High Latency** (> 60s): -20 points (may indicate timeout)

**Issues Detected:**
- Errors during execution
- Very high latency suggesting timeout

**Strengths:**
- No errors during execution
- Graceful degradation (optional components handled)

---

### 5. Resource Efficiency (Weight: 10%)

Measures efficient use of system resources.

**Sub-components:**
- **Database Query Count**: Number of SQLite queries executed
- **Database Query Efficiency**: Average query execution time
- **LLM Call Efficiency**: Number of LLM API calls per report
- **Cache Hit Rate**: Percentage of times cached data/reports are used

**Scoring Thresholds:**
- **Database Queries**: 
  - < 5 queries: +0 points
  - 5-10 queries: -5 points
  - > 10 queries: -15 points
- **LLM Calls**:
  - 1 call: +0 points
  - 2 calls: +0 points
  - > 2 calls: -10 points

**Issues Detected:**
- High database query count (> 10)
- Multiple LLM calls (> 2)

**Strengths:**
- Efficient database usage
- Single LLM call optimized
- Cache utilization

---

### 6. Scalability (Weight: 10%)

Measures system performance under load (inferred from latency trends).

**Sub-components:**
- **Latency Trends**: Performance degradation over time
- **Concurrent Request Handling**: Performance under concurrent requests
- **Throughput**: Reports generated per unit time

**Scoring:**
- **Low Latency** (< 10s): 90 points
- **Moderate Latency** (10-20s): 75 points
- **High Latency** (> 20s): 60 points
- **Latency Increase** (> 20% from baseline): -15 points

**Issues Detected:**
- High latency limiting scalability
- Latency trending up (> 20% increase)

**Strengths:**
- Low latency suggests good scalability
- Latency improved from baseline

---

## Overall Score Calculation

The overall QoS score is calculated as a weighted average:

```
Overall QoS Score = (
    Latency Score × 0.25 +
    Cost Efficiency Score × 0.20 +
    Determinism Score × 0.15 +
    Reliability Score × 0.20 +
    Resource Efficiency Score × 0.10 +
    Scalability Score × 0.10
)
```

## Score Interpretation

### Overall Score Grades

- **90-100**: Excellent - System performs optimally
- **80-89**: Good - Minor optimizations possible
- **70-79**: Acceptable - Some improvements needed
- **60-69**: Needs Improvement - Significant optimization required
- **< 60**: Poor - Critical issues need immediate attention

### Per-Dimension Scores

Each dimension is scored 0-100 using the same grade scale.

## Historical Tracking

QoS metrics are stored in the database (`qos_metrics` table) to enable:

1. **Trend Analysis**: Track QoS degradation/improvement over time
2. **Baseline Comparison**: Compare current performance to historical baselines
3. **Anomaly Detection**: Identify performance regressions
4. **Optimization Guidance**: Identify which dimensions need improvement

### Database Schema

```sql
CREATE TABLE qos_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    overall_score REAL,
    latency_score REAL,
    cost_efficiency_score REAL,
    determinism_score REAL,
    reliability_score REAL,
    resource_efficiency_score REAL,
    scalability_score REAL,
    total_latency REAL,
    data_fetch_latency REAL,
    news_fetch_latency REAL,
    technical_analysis_latency REAL,
    chart_generation_latency REAL,
    llm_generation_latency REAL,
    scoring_latency REAL,
    llm_cost_actual REAL,
    llm_cost_estimated REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    llm_calls INTEGER,
    db_query_count INTEGER,
    cache_hit INTEGER DEFAULT 0,
    error_occurred INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### In Agent Workflow

QoS scoring is automatically performed after report generation:

```python
from src.qos_scorer import QoSScorer

qos_scorer = QoSScorer()

qos_score = qos_scorer.score_qos(
    timing_metrics=timing_metrics,
    api_costs=api_costs,
    database_metrics=database_metrics,
    error_occurred=False,
    cache_hit=False,
    llm_calls=1,
    historical_data=historical_data
)
```

### Accessing QoS Metrics

**From Agent State:**
```python
final_state = agent.graph.invoke(initial_state)
qos_score = final_state.get("qos_score")
timing_metrics = final_state.get("timing_metrics")
api_costs = final_state.get("api_costs")
database_metrics = final_state.get("database_metrics")
```

**From API Response:**
```json
{
  "qos_score": {
    "overall_score": 85.5,
    "dimension_scores": {
      "latency": 90.0,
      "cost_efficiency": 85.0,
      "determinism": 90.0,
      "reliability": 100.0,
      "resource_efficiency": 85.0,
      "scalability": 75.0
    },
    "metrics": {
      "timing": {
        "data_fetch": 1.2,
        "news_fetch": 2.5,
        "technical_analysis": 1.8,
        "chart_generation": 3.2,
        "llm_generation": 4.5,
        "scoring": 0.8,
        "total": 14.0
      },
      "costs": {
        "llm_actual": null,
        "llm_estimated": 0.08,
        "input_tokens": 3500,
        "output_tokens": 1200
      },
      "database": {
        "query_count": 3,
        "cache_hit": false
      },
      "llm_calls": 1,
      "error_occurred": false
    },
    "issues": [],
    "strengths": [
      "✅ Excellent total latency: 14.00s",
      "✅ Single LLM call optimized cost"
    ]
  }
}
```

## Example Output

```
======================================================================
QoS SCORE REPORT
======================================================================
Overall QoS Score: 85.5/100

Dimension Scores:
----------------------------------------------------------------------
  Latency                 :  90.0/100 (Excellent)
  Cost Efficiency         :  85.0/100 (Good)
  Determinism             :  90.0/100 (Excellent)
  Reliability             : 100.0/100 (Excellent)
  Resource Efficiency     :  85.0/100 (Good)
  Scalability             :  75.0/100 (Acceptable)

----------------------------------------------------------------------
Metrics:
----------------------------------------------------------------------
  Timing (seconds):
    data_fetch            :   1.20s
    news_fetch            :   2.50s
    technical_analysis    :   1.80s
    chart_generation      :   3.20s
    llm_generation        :   4.50s
    scoring               :   0.80s
    total                 :  14.00s

  Costs (USD):
    LLM Estimated Cost:     $0.000080
    Input Tokens:           3,500
    Output Tokens:          1,200

  Database:
    Query Count:            3
    Cache Hit:              No

  Other:
    LLM Calls:              1
    Error Occurred:         No

----------------------------------------------------------------------
Strengths:
  ✅ Excellent total latency: 14.00s
  ✅ Single LLM call optimized cost
  ✅ Deterministic components executed consistently
  ✅ No errors during execution
======================================================================
```

## Relationship to Other Scores

QoS is **independent** of content quality scores:

- **Faithfulness**: Measures factual accuracy (content quality)
- **Completeness**: Measures analytical coverage (content quality)
- **Reasoning Quality**: Measures explanation quality (content quality)
- **Compliance**: Measures format adherence (content quality)
- **QoS**: Measures system performance (operational quality)

These scores complement each other to provide a complete picture:
- **Content Quality** (Faithfulness + Completeness + Reasoning Quality + Compliance): "Is the report good?"
- **Operational Quality** (QoS): "Is the system performing well?"

## Architecture

### Components

1. **QoSScorer** (`src/qos_scorer.py`):
   - Main scoring logic
   - Dimension scoring methods
   - Cost calculation
   - Score formatting

2. **Database Integration** (`src/database.py`):
   - `save_qos_metrics()`: Store QoS metrics
   - `get_historical_qos()`: Retrieve historical metrics for trend analysis

3. **Agent Integration** (`src/agent.py`):
   - Timing instrumentation in workflow nodes
   - API cost tracking
   - Database query counting
   - QoS score calculation

4. **API Integration** (`src/api_handler.py`):
   - QoS score inclusion in API response
   - JSON serialization

### Timing Instrumentation

Timing is tracked using `time.perf_counter()` for high-precision measurements:

```python
start_time = time.perf_counter()
# ... operation ...
elapsed = time.perf_counter() - start_time
```

### Token Usage Extraction

Token usage is extracted from LangChain response metadata:

```python
response_metadata = getattr(response, 'response_metadata', {})
usage = response_metadata.get('token_usage', {})
input_tokens = usage.get('prompt_tokens', 0)
output_tokens = usage.get('completion_tokens', 0)
```

If metadata is unavailable, tokens are estimated (4 characters per token).

## Limitations

1. **Scalability Inference**: Scalability is inferred from latency trends rather than load testing
2. **Cost Estimation**: Actual costs depend on OpenAI pricing (may need updates)
3. **Cache Detection**: Cache hit detection is basic (could be enhanced)
4. **Determinism**: Only measures deterministic components (LLM variance not tracked)
5. **Historical Data**: Requires previous runs for trend analysis

## Best Practices

1. **Monitor Trends**: Track QoS scores over time to identify regressions
2. **Set Baselines**: Establish baseline QoS scores for comparison
3. **Optimize Low Scores**: Focus on dimensions with scores < 70
4. **Cost Monitoring**: Track costs to identify expensive operations
5. **Latency Targets**: Set latency targets per component and monitor

## Future Enhancements

1. **Cache Hit Tracking**: Enhanced cache detection and reporting
2. **Load Testing**: Actual scalability testing under concurrent load
3. **Cost Breakdown**: More detailed cost breakdown by component
4. **Alerting**: Automated alerts for QoS degradation
5. **Dashboard**: Visual dashboard for QoS metrics and trends

## Changelog

### v1.0.0 (2024)
- Initial implementation
- Six QoS dimensions
- Historical tracking
- Database integration
- API integration
