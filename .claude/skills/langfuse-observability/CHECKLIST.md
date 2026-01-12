# Langfuse Observability Checklist

Quick reference checklists for common Langfuse operations.

---

## New Feature Instrumentation

When adding observability to a new LLM feature:

### Setup
- [ ] Feature has clear entry point function
- [ ] Entry point is suitable for top-level trace

### Implementation
- [ ] Added `from src.evaluation import observe, flush`
- [ ] Added `@observe(name="descriptive_name")` to entry point
- [ ] Name is descriptive (e.g., `"analyze_ticker_DBS19"` not `"process"`)
- [ ] Added `flush()` call before Lambda handler returns

### Scoring (if applicable)
- [ ] Identified high-value output to score
- [ ] Added `score_current_trace()` within `@observe` context
- [ ] Score name is meaningful (e.g., `"report_quality"`)
- [ ] Score value is 0-100 (auto-normalized to 0-1)

### Testing
- [ ] Ran locally with `doppler run --config dev_local`
- [ ] Verified trace appears in Langfuse UI
- [ ] Verified scores appear on trace
- [ ] Tested error path (trace should still be created)

### Deployment
- [ ] Environment has `LANGFUSE_PUBLIC_KEY` configured (Doppler)
- [ ] Environment has `LANGFUSE_SECRET_KEY` configured (Doppler)
- [ ] Environment has `LANGFUSE_HOST` configured (Doppler)
- [ ] Environment has `LANGFUSE_RELEASE` configured (e.g., `dev`, `stg`, `prd`)
- [ ] Environment has `LANGFUSE_TRACING_ENVIRONMENT` configured (e.g., `dev`, `stg`, `prd`)

---

## Quality Investigation

When investigating quality issues:

### Identify
- [ ] Opened Langfuse UI: https://us.cloud.langfuse.com
- [ ] Navigated to Traces
- [ ] Filtered by relevant criteria (time, name, user)
- [ ] Identified low-scoring or problematic traces

### Analyze
- [ ] Clicked on problem trace to open details
- [ ] Reviewed trace hierarchy (spans, generations)
- [ ] Examined inputs at each step
- [ ] Examined outputs at each step
- [ ] Identified where quality degraded

### Root Cause
- [ ] Checked input data quality
- [ ] Checked prompt/context construction
- [ ] Checked LLM response appropriateness
- [ ] Checked scoring accuracy

### Document
- [ ] Extracted problematic example
- [ ] Created dataset item for regression testing
- [ ] Documented root cause in journal (if significant)

### Fix
- [ ] Implemented fix
- [ ] Verified improvement in local test
- [ ] Deployed and monitored production scores

---

## Prompt Version Update

When updating prompts (future workflow):

### Before Change
- [ ] Identified current prompt version in Langfuse
- [ ] Noted current production label
- [ ] Created baseline score metrics

### Make Change
- [ ] Created NEW version (never edit existing)
- [ ] Labeled new version as "staging" or "testing"
- [ ] Did NOT change production label yet

### Validate
- [ ] Ran experiment against evaluation dataset
- [ ] Compared scores to baseline
- [ ] Verified no regression in key metrics
- [ ] Tested edge cases

### Deploy
- [ ] Moved "production" label to new version
- [ ] Kept old version (don't delete)
- [ ] Monitored production scores for 24-48 hours

### Rollback (if needed)
- [ ] Moved "production" label back to previous version
- [ ] Documented reason for rollback
- [ ] Investigated and fixed issue

---

## Evaluation Dataset Creation

When creating a test dataset:

### Plan
- [ ] Defined purpose of dataset
- [ ] Identified representative examples (20-30)
- [ ] Defined expected outputs (if applicable)
- [ ] Defined evaluation criteria

### Create
- [ ] Created dataset in Langfuse UI
- [ ] Named descriptively (e.g., `"daily-reports-quality-v1"`)
- [ ] Added description explaining purpose

### Populate
- [ ] Added diverse examples (different tickers, edge cases)
- [ ] Included expected outputs where applicable
- [ ] Verified inputs are complete and valid

### Validate
- [ ] Ran baseline experiment
- [ ] Verified scoring works correctly
- [ ] Documented baseline scores

---

## Production Monitoring

Regular monitoring tasks:

### Daily
- [ ] Check for any failed traces (errors)
- [ ] Spot check recent low scores

### Weekly
- [ ] Review score trends over past week
- [ ] Identify any degradation patterns
- [ ] Compare scores to baseline

### Monthly
- [ ] Review cost trends
- [ ] Update evaluation dataset with new examples
- [ ] Clean up old/unused datasets
- [ ] Review prompt version effectiveness

---

## Troubleshooting

### Traces Not Appearing

- [ ] Verified `LANGFUSE_PUBLIC_KEY` is set
- [ ] Verified `LANGFUSE_SECRET_KEY` is set
- [ ] Verified `flush()` is called before Lambda returns
- [ ] Checked logs for "Langfuse client initialized" message
- [ ] Checked logs for any Langfuse errors

### Scores Not Attached

- [ ] Verified `score_current_trace()` is within `@observe` context
- [ ] Checked logs for "Failed to score trace" warnings
- [ ] Verified score value is numeric (0-100)

### High Latency

- [ ] Verified not calling `flush()` too frequently
- [ ] Checked network connectivity to Langfuse
- [ ] Considered if too many spans/scores per trace

### Missing Trace Metadata

- [ ] Verified `LANGFUSE_RELEASE` is set in Doppler
- [ ] Verified `LANGFUSE_TRACING_ENVIRONMENT` is set in Doppler
- [ ] Checked that `trace_context()` is used for user_id, session_id, tags
- [ ] Verified metadata is JSON-serializable

---

## Configuration Verification

Per [Principle #23: Configuration Variation Axis](../../CLAUDE.md) (Tier-0):

### Env Vars (Must be in Doppler)
- [ ] `LANGFUSE_PUBLIC_KEY` - API key (secret)
- [ ] `LANGFUSE_SECRET_KEY` - API secret (secret)
- [ ] `LANGFUSE_HOST` - API endpoint (environment-specific)
- [ ] `LANGFUSE_RELEASE` - Version identifier (environment-specific)
- [ ] `LANGFUSE_TRACING_ENVIRONMENT` - Environment tag (environment-specific)

### Constants (Must be in src/config.py)
- [ ] Trace names use `TRACE_NAMES` class
- [ ] Observation names use `OBSERVATION_NAMES` class
- [ ] Score names use `SCORE_NAMES` class
- [ ] Tag values use `TRACE_TAGS` class
- [ ] Default user uses `DEFAULT_USER_ID`

### Anti-Pattern Detection
- [ ] No hardcoded trace/score names (use constants)
- [ ] No env vars for static values (should be constants)
- [ ] No constants for secrets (should be Doppler)
- [ ] No reading env vars on every request (should be singleton)
