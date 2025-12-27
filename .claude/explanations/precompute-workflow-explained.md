# Explanation: Precompute Workflow

**Audience**: Beginner
**Format**: Tutorial - Input to Output
**Last updated**: 2025-12-24

---

## Quick Summary

The **Precompute Workflow** is an automated system that generates financial reports for all 46 supported stocks in parallel, storing them in the database BEFORE users ask for them. This makes user requests super fast (~300ms) because the reports are already ready!

Think of it like a restaurant preparing popular dishes ahead of time (mise en place) vs cooking everything from scratch when customers order.

---

## Why Precompute?

### The Problem Without Precompute

```
User: "Give me NVDA report"
   ↓ Call Yahoo Finance API (2-5 seconds)
   ↓ Call News API (3-7 seconds)
   ↓ Run AI analysis (8-12 seconds)
   ↓ Generate charts (2-3 seconds)
Total: ~15-27 seconds! 😱
```

User waits nearly half a minute for a report!

### The Solution With Precompute

```
BEFORE user asks (nightly at 5 AM):
   ↓ Generate all 46 reports (15 minutes total in parallel)
   ↓ Store in Aurora database

When user asks:
User: "Give me NVDA report"
   ↓ Query Aurora database (50ms)
   ↓ Return cached report
Total: ~300ms! ✅
```

User gets instant response!

---

## Complete Workflow: Input → Output

### INPUT: Trigger Event

The workflow can be triggered in two ways:

**Method 1: Automatic (Daily Schedule)**
```json
{
  "source": "scheduler",
  "action": "precompute",
  "triggered_at": "2025-12-24T05:00:00Z"
}
```
Sent by the **Scheduler Lambda** after fetching ticker data at 5 AM Bangkok.

**Method 2: Manual (Testing or On-Demand)**
```json
{
  "limit": 5,
  "source": "manual"
}
```
Invoked manually via AWS CLI or console (useful for testing with just 5 tickers instead of all 46).

---

## STAGE 1: Start Workflow (Precompute Controller)

**What happens:**
```
1. Precompute Controller Lambda receives trigger event
   ↓
2. Validates environment variables
   ↓
3. Starts Step Functions state machine
   ↓
4. Returns execution ARN (tracking ID)
```

**Code Location:** `src/scheduler/precompute_controller_handler.py:35-120`

**Real Input Example:**
```python
# Event received by Lambda
event = {
    "limit": None,  # All tickers (46)
    "source": "scheduler"
}
```

**Output:**
```json
{
  "statusCode": 200,
  "body": {
    "message": "Precompute workflow started",
    "execution_arn": "arn:aws:states:...:execution:precompute-20251224-055723",
    "execution_name": "precompute-20251224-055723",
    "workflow_input": {
      "limit": null,
      "triggered_at": "2025-12-24T05:57:23",
      "triggered_by": "scheduler"
    }
  }
}
```

---

## STAGE 2: Get Ticker List (Step Functions)

**What happens:**
```
Step Functions calls GetTickerList Lambda
   ↓
Lambda queries Aurora ticker_master table
   ↓
Returns list of 46 active DR symbols
```

**Code:** State machine calls `get_ticker_list_handler`

**Step Functions State:**
```json
{
  "PrepareTickerList": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:get-ticker-list-dev",
    "ResultPath": "$.ticker_list"
  }
}
```

**Output:**
```json
{
  "ticker_list": {
    "tickers": [
      "NVDA", "AAPL", "TSLA", "DBS19", "OCBC19",
      "UOB19", "NINTENDO19", "SONY19", ...
    ],
    "count": 46
  }
}
```

---

## STAGE 3: Fan-Out to SQS (Parallel Processing)

**What happens:**
```
Step Functions Map state iterates over 46 tickers
   ↓
For EACH ticker, send message to SQS queue
   ↓
46 messages sent in parallel (MaxConcurrency: 46)
```

**Step Functions Map State:**
```json
{
  "FanOutToWorkers": {
    "Type": "Map",
    "ItemsPath": "$.ticker_list.tickers",
    "MaxConcurrency": 46,
    "Iterator": {
      "StartAt": "SubmitToSQS",
      "States": {
        "SubmitToSQS": {
          "Type": "Task",
          "Resource": "arn:aws:states:::sqs:sendMessage",
          "Parameters": {
            "QueueUrl": "https://sqs.../dr-daily-report-telegram-queue-dev",
            "MessageBody": {
              "job_id": "rpt_NVDA_precompute-20251224-055723",
              "ticker": "NVDA",
              "execution_id": "precompute-20251224-055723",
              "source": "step_functions_precompute"
            }
          }
        }
      }
    }
  }
}
```

**What Each SQS Message Looks Like:**
```json
{
  "job_id": "rpt_NVDA_precompute-20251224-055723",
  "ticker": "NVDA",
  "execution_id": "precompute-20251224-055723",
  "source": "step_functions_precompute"
}
```

**Result:**
- 46 messages in SQS queue
- Each message triggers a separate Lambda worker
- All 46 workers run in parallel!

---

## STAGE 4: Process Each Report (Worker Lambda)

**What happens for EACH ticker:**
```
1. Worker Lambda triggered by SQS message
   ↓
2. Parse message (get job_id, ticker)
   ↓
3. Mark job as "in_progress" in DynamoDB
   ↓
4. Run AI analysis (TickerAnalysisAgent)
   ↓
5. Transform result to API format
   ↓
6. Store to DynamoDB + Aurora cache
   ↓
7. Mark job as "completed"
```

**Code Location:** `src/report_worker_handler.py:114-230`

**Detailed Breakdown:**

### Step 4a: Parse Message & Validate
```python
# Extract from SQS message
message = json.loads(body)
job_id = message['job_id']           # "rpt_NVDA_..."
ticker_raw = message['ticker']       # "NVDA"

# Resolve ticker (handles both DR symbols and Yahoo symbols)
resolver = get_ticker_resolver()
resolved = resolver.resolve(ticker_raw)
ticker = resolved.dr_symbol  # Canonical form
```

### Step 4b: Mark Job as In Progress
```python
job_service = get_job_service()
job_service.start_job(job_id)

# DynamoDB record created:
# {
#   "job_id": "rpt_NVDA_...",
#   "status": "in_progress",
#   "ticker": "NVDA",
#   "created_at": "2025-12-24T05:57:30Z"
# }
```

### Step 4c: Run AI Analysis
```python
# Initialize AI agent
agent = TickerAnalysisAgent()

# Create initial empty state
initial_state = {
    "ticker": "NVDA",
    "ticker_data": {},
    "indicators": {},
    "news": [],
    "report": "",
    "error": ""
}

# Run complete analysis (takes ~60-120 seconds)
final_state = agent.graph.invoke(initial_state)
```

**What the Agent Does Internally:**
```
1. Fetch Ticker Data (from Aurora - already pre-fetched)
   ↓ Price history, company info

2. Calculate Technical Indicators
   ↓ Moving averages, RSI, MACD, etc.

3. Fetch News
   ↓ Recent news articles

4. Analyze Comparative Data
   ↓ Compare to peers, sector

5. Generate Chart
   ↓ Price chart with indicators

6. Generate Narrative Report (AI)
   ↓ Call OpenRouter API with LLM

7. Quality Scoring
   ↓ Validate report quality
```

### Step 4d: Transform to API Format
```python
transformer = get_transformer()
response = await transformer.transform_report(final_state, ticker_info)
result = response.model_dump()

# Result structure:
# {
#   "narrative_report": "## NVDA Analysis...",
#   "chart_base64": "iVBORw0KGgo...",
#   "user_facing_scores": {
#     "faithfulness": 9.2,
#     "completeness": 8.8,
#     ...
#   },
#   "timing_metrics": {...},
#   "api_costs": {...}
# }
```

### Step 4e: Store Results
```python
# Store to DynamoDB (primary)
job_service.complete_job(job_id, result)

# DynamoDB record updated:
# {
#   "job_id": "rpt_NVDA_...",
#   "status": "completed",
#   "result": { ...full report... },
#   "completed_at": "2025-12-24T05:59:15Z"
# }

# Store to Aurora cache (for instant future lookups)
precompute_service = PrecomputeService()
precompute_service.store_report_from_api(
    symbol="NVDA",
    report_text=result['narrative_report'],
    report_json=result,
    chart_base64=final_state['chart_base64']
)

# Aurora record created:
# precomputed_reports table
# {
#   "symbol": "NVDA",
#   "report_json": {...},
#   "chart_base64": "iVBORw0KGgo...",
#   "created_at": "2025-12-24T05:59:15Z"
# }
```

---

## STAGE 5: Wait for Completion (Step Functions)

**What happens:**
```
Step Functions waits 5 minutes (300 seconds)
   ↓
This gives all 46 workers time to finish
   ↓
Slowest ticker takes ~120 seconds
   ↓
5 minutes provides 2.5x buffer
```

**Step Functions State:**
```json
{
  "WaitForWorkers": {
    "Type": "Wait",
    "Seconds": 300,
    "Next": "AggregateResults"
  }
}
```

**Why Fixed Wait?**
- Simpler than polling DynamoDB for completion
- 46 workers run in parallel, so max time ≈ slowest ticker
- 5 minutes is safe buffer (historically enough)

---

## STAGE 6: Aggregate Results (Final Step)

**What happens:**
```
Step Functions marks workflow as "completed"
   ↓
Returns final summary
   ↓
Workflow execution ends
```

**Step Functions State:**
```json
{
  "AggregateResults": {
    "Type": "Pass",
    "Parameters": {
      "status": "completed",
      "total_tickers": 46,
      "message": "Precompute workflow completed",
      "next_steps": "Query DynamoDB jobs table for individual results"
    },
    "End": true
  }
}
```

---

## OUTPUT: What Gets Created

### 1. DynamoDB Jobs Table (46 records)

```
dr-daily-report-telegram-jobs-dev
├─ Job: rpt_NVDA_precompute-20251224-055723
│  ├─ status: completed
│  ├─ ticker: NVDA
│  ├─ result: {narrative_report, chart_base64, scores, ...}
│  └─ completed_at: 2025-12-24T05:59:15Z
│
├─ Job: rpt_AAPL_precompute-20251224-055723
│  ├─ status: completed
│  └─ ...
│
└─ ... (44 more jobs)
```

### 2. Aurora Cache Table (46 reports)

```
precomputed_reports table
├─ symbol: NVDA
│  ├─ report_json: {full report JSON}
│  ├─ chart_base64: {PNG chart encoded}
│  └─ created_at: 2025-12-24T05:59:15Z
│
├─ symbol: AAPL
│  └─ ...
│
└─ ... (44 more)
```

### 3. CloudWatch Logs

```
/aws/lambda/dr-daily-report-worker-dev
├─ Log Stream: 2025/12/24/[$LATEST]abc123
│  ├─ "Processing job rpt_NVDA_..."
│  ├─ "Agent analysis complete for NVDA"
│  ├─ "✅ Cached report in Aurora for NVDA"
│  └─ "Completed job rpt_NVDA_..."
│
└─ ... (logs for all 46 workers)
```

### 4. Step Functions Execution Record

```
Execution: precompute-20251224-055723
├─ Status: SUCCEEDED
├─ Started: 2025-12-24T05:57:25Z
├─ Ended: 2025-12-24T06:02:25Z
├─ Duration: 5 minutes
└─ Output: {status: "completed", total_tickers: 46}
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT (Trigger)                          │
│  EventBridge (5 AM) OR Manual invocation                        │
│  {"source": "scheduler", "limit": null}                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Precompute Controller Lambda                          │
│  - Validate environment variables                               │
│  - Start Step Functions state machine                           │
│  Output: execution_arn                                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: Get Ticker List (Step Functions)                      │
│  - Query Aurora ticker_master table                             │
│  Output: ["NVDA", "AAPL", ..., "UOB19"] (46 tickers)           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 3: Fan-Out to SQS (Step Functions Map)                   │
│  - For each ticker, send SQS message                            │
│  - 46 messages sent in parallel                                │
│  Output: 46 SQS messages in queue                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 4: Process Reports (46 Worker Lambdas in Parallel)       │
│                                                                  │
│  Worker 1 (NVDA)    Worker 2 (AAPL)    ...    Worker 46 (UOB19)│
│       ↓                  ↓                          ↓           │
│  1. Parse SQS       1. Parse SQS             1. Parse SQS      │
│  2. Mark progress   2. Mark progress         2. Mark progress  │
│  3. Run AI agent    3. Run AI agent          3. Run AI agent   │
│  4. Transform       4. Transform             4. Transform      │
│  5. Store DynamoDB  5. Store DynamoDB        5. Store DynamoDB │
│  6. Cache Aurora    6. Cache Aurora          6. Cache Aurora   │
│  7. Mark complete   7. Mark complete         7. Mark complete  │
│       ↓                  ↓                          ↓           │
│  Output: Report    Output: Report          Output: Report     │
│  (~60-120s)        (~60-120s)              (~60-120s)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 5: Wait for Completion (Step Functions)                  │
│  - Wait 300 seconds (5 minutes)                                 │
│  - Allow all workers to finish                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 6: Aggregate Results (Step Functions)                    │
│  - Mark workflow as completed                                   │
│  Output: {status: "completed", total_tickers: 46}              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FINAL OUTPUT                                │
│                                                                  │
│  DynamoDB: 46 completed jobs                                    │
│  Aurora: 46 cached reports                                      │
│  CloudWatch: Execution logs                                     │
│  Step Functions: Execution record (SUCCEEDED)                   │
│                                                                  │
│  ✅ All 46 reports ready for instant user access!               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Try It Yourself

### Exercise 1: Trigger Precompute Manually (Limited)

```bash
# Test with just 5 tickers (faster, cheaper)
aws lambda invoke \
  --function-name dr-daily-report-precompute-controller-dev \
  --payload '{"limit":5,"source":"manual"}' \
  /tmp/precompute-start.json

# Check response
cat /tmp/precompute-start.json | jq .

# Expected output:
# {
#   "statusCode": 200,
#   "body": {
#     "execution_arn": "arn:aws:states:...",
#     "execution_name": "precompute-20251224-120000"
#   }
# }
```

### Exercise 2: Monitor Step Functions Execution

```bash
# Get execution ARN from Exercise 1
EXECUTION_ARN="arn:aws:states:..."

# Check status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query '{status:status,startDate:startDate,stopDate:stopDate}' \
  --output table

# Expected while running:
# | status  | RUNNING |
# After 5 minutes:
# | status  | SUCCEEDED |
```

### Exercise 3: Verify Reports in DynamoDB

```bash
# Count completed jobs
aws dynamodb scan \
  --table-name dr-daily-report-telegram-jobs-dev \
  --filter-expression "#st = :status" \
  --expression-attribute-names '{"#st":"status"}' \
  --expression-attribute-values '{":status":{"S":"completed"}}' \
  --select COUNT \
  --output json | jq '.Count'

# Expected: 5 (if you used limit=5)
# Expected: 46 (if you ran full precompute)
```

### Exercise 4: Check Cached Report in Aurora

```bash
# Connect to Aurora (assumes SSM tunnel active)
mysql -h localhost -P 3307 -u admin -p

# Query cached report
SELECT
  symbol,
  JSON_EXTRACT(report_json, '$.narrative_report') as report_snippet,
  created_at
FROM precomputed_reports
WHERE symbol = 'NVDA'
ORDER BY created_at DESC
LIMIT 1;

# Expected: Latest NVDA report with timestamp
```

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Total Duration** | ~5-6 minutes | For all 46 tickers in parallel |
| **Per-Ticker Time** | ~60-120 seconds | Varies by ticker complexity |
| **Parallelism** | 46 concurrent workers | Limited by Lambda concurrency |
| **Step Functions Cost** | ~$0.0001 | 6 state transitions |
| **Lambda Cost** | ~$0.10 | 46 invocations × ~120s × memory |
| **OpenRouter Cost** | ~$0.50-1.00 | 46 LLM API calls |
| **Total Cost** | ~$0.60-1.10 per run | Daily expense |

---

## Common Questions

### Q: What happens if a worker fails?

**A**: The worker marks the job as "failed" in DynamoDB with the error message. Other workers continue independently. Step Functions still waits the full 5 minutes and completes successfully - you need to check DynamoDB to see individual failures.

Example failed job:
```json
{
  "job_id": "rpt_QQQM_...",
  "status": "failed",
  "error": "Aurora ticker_data storage failed",
  "failed_at": "2025-12-24T05:58:30Z"
}
```

### Q: Can we run precompute more than once per day?

**A**: Yes! You can trigger it manually anytime. Each execution is independent and creates new job records in DynamoDB. Aurora cache gets overwritten with latest report.

### Q: What if Step Functions times out?

**A**: Step Functions has 1-year max execution time, so timeout is not a concern. The 5-minute wait is intentionally conservative.

### Q: How do we know if ALL 46 reports completed successfully?

**A**: Query DynamoDB:
```bash
# Count completed
aws dynamodb scan --table-name ... --filter-expression "status=:s" ... | jq '.Count'

# Count failed
aws dynamodb scan --table-name ... --filter-expression "status=:f" ... | jq '.Count'

# Expected: completed=46, failed=0
```

### Q: Can we reduce the 5-minute wait time?

**A**: Yes, but risky. If you know your slowest ticker takes <90 seconds, you could reduce to 2 minutes. But if a slow ticker appears, it won't be cached.

### Q: What's the difference between DynamoDB and Aurora storage?

**A**:
- **DynamoDB jobs table**: Temporary job tracking (TTL: 7 days)
- **Aurora precomputed_reports**: Long-term cache (persistent)
- **User API reads from**: Aurora only (fast, indexed queries)

---

## Key Takeaways

1. **Precompute = Pre-generate reports** before users ask
   - Makes user requests 50-100x faster (from 15s to 300ms)

2. **Parallel processing** = Efficiency
   - 46 workers run simultaneously
   - Total time ≈ slowest ticker (not sum of all)

3. **Step Functions** = Orchestration
   - Coordinates the workflow
   - Provides visibility and tracking
   - Direct SQS integration (no Lambda glue code)

4. **Dual storage** = Reliability + Performance
   - DynamoDB: Job tracking, temporary results
   - Aurora: Long-term cache, user queries

5. **Fail-independent** = Resilience
   - One ticker failure doesn't block others
   - Step Functions completes even if workers fail
   - Check DynamoDB for individual status

---

## Sources

**From this project:**
- Code: `src/scheduler/precompute_controller_handler.py:35-120` (Controller Lambda)
- Code: `src/report_worker_handler.py:114-230` (Worker Lambda)
- Config: `terraform/step_functions/precompute_workflow.json` (State machine)
- CLAUDE.md: Aurora-First Data Architecture principle

**Architecture:**
- Step Functions Map state for parallel processing
- SQS for decoupling orchestration from execution
- DynamoDB for job tracking
- Aurora for report caching

---

*Explanation generated by `/explain "precompute workflow"`*
*Generated: 2025-12-24*
