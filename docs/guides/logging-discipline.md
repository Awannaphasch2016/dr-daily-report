# Logging Discipline Guide (Storytelling Pattern)

**Principle #18** | Log for narrative reconstruction, not just event recording.

---

## Overview

### Core Problem
Logs that only record events don't help reconstruct what happened during failures. Without narrative structure, debugging requires correlating multiple sources to understand the execution flow.

### Key Insight
Reading logs should explain what was executed or failed without needing to inspect traces directly. Logs serve as "weaker ground truth"—faster to inspect than traces, more reliable than status codes.

---

## Log Level Semantics

Each log level tells a story:

| Level | Story | Example |
|-------|-------|---------|
| ERROR | What failed | `"❌ Failed to save report: ConnectionTimeout"` |
| WARNING | What's unexpected | `"⚠️ Cache miss, fetching from Aurora"` |
| INFO | What happened | `"✅ Generated report for DBS in 2.3s"` |
| DEBUG | How it happened | `"Query returned 145 rows in 0.8s"` |

---

## Narrative Structure

Every operation should have three phases:

### Beginning (Context)
```python
logger.info(f"Starting report generation for {symbol}")
logger.debug(f"Parameters: date={date}, include_news={include_news}")
```

### Middle (Milestones)
```python
logger.info(f"Fetched price data: {len(prices)} records")
logger.info(f"Generated analysis with {len(sections)} sections")
```

### End (Outcome)
```python
# Success
logger.info(f"✅ Report complete: {symbol} in {elapsed:.1f}s")

# Failure
logger.error(f"❌ Report failed: {symbol} - {error}", exc_info=True)
```

---

## Visual Scanability

### Status Symbols
Use consistent symbols for quick scanning:

```python
# Success
logger.info("✅ Operation completed successfully")

# Degraded (worked but with issues)
logger.warning("⚠️ Cache miss, using fallback")

# Failure
logger.error("❌ Operation failed")
```

### Chapter Separators
For long operations, use visual separators:

```python
logger.info("=" * 50)
logger.info("📄 Starting PDF Generation")
logger.info("=" * 50)
```

### Correlation IDs
For distributed operations, prefix with job ID:

```python
logger.info(f"[{job_id}] Starting batch processing")
logger.info(f"[{job_id}] Processing item 1/10")
logger.info(f"[{job_id}] ✅ Batch complete")
```

---

## Verification Logging (Defensive Storytelling)

Don't assume operations succeeded—verify and log explicitly:

```python
# WRONG: Silent assumption
result = client.execute(query)
# No verification, continues silently

# RIGHT: Explicit verification
result = client.execute(query)
if result.rowcount == 0:
    logger.error("❌ Operation failed - 0 rows affected")
    raise OperationError("No rows affected")
else:
    logger.info(f"✅ Affected {result.rowcount} rows")
```

---

## Boundary Logging Strategy

### The Problem
WHERE you log determines WHAT survives failures. Logs deep in call stack are lost when Lambda fails before log buffer flushes.

### The Solution
Log at layer boundaries where failures are caught:

```python
# LAYER BOUNDARY (Handler) - Always survives
logger.info(f"Starting S3 upload: {key}")

try:
    # LAYER BOUNDARY (Service call) - Survives if exception raised
    result = s3_client.upload_file(file_path, bucket, key)

    # LAYER BOUNDARY (Success verification) - Survives on success
    logger.info(f"✅ S3 upload completed: {key}")
except Exception as e:
    # LAYER BOUNDARY (Error handler) - Always survives
    logger.error(f"❌ S3 upload failed: {key}", exc_info=True)
    raise
```

### Layer Boundary Examples

| Layer | Log Placement | Survives |
|-------|--------------|----------|
| Handler entry | Before any processing | Always |
| Service call | Before external call | Always |
| Success verification | After confirmed success | On success |
| Error handler | In except block | On failure |
| Deep in call stack | Inside nested functions | Maybe not |

---

## Critical Insight: Execution Time ≠ Hang Location

### The Misconception
Lambda execution time of 600s means code hangs at line that takes 600s.

### The Reality
Execution time shows WHAT the system waits for (e.g., 10min S3 timeout), not WHERE code hangs (e.g., ReportLab).

### How to Find Actual Hang Point
Use stack traces (Layer 3 evidence), not execution time (Layer 1 evidence):

```python
# Stack trace reveals actual location
Traceback:
  File "handler.py", line 45, in handler
  File "report.py", line 123, in generate  # ← Actual hang point
  File "boto3/...", line 84, in upload     # ← Waiting for S3
```

---

## Anti-Patterns

### 1. Logging Errors at WARNING Level
```python
# WRONG: Invisible to error monitoring
logger.warning(f"Failed to save: {error}")

# RIGHT: Proper severity
logger.error(f"Failed to save: {error}")
```

### 2. Missing Narrative Phases
```python
# WRONG: Only logs failure, no context
def process():
    # ... processing ...
    if error:
        logger.error("Failed")

# RIGHT: Full narrative
def process():
    logger.info("Starting processing")
    # ... processing ...
    if error:
        logger.error("❌ Failed during processing")
    else:
        logger.info("✅ Processing complete")
```

### 3. Silent Success
```python
# WRONG: Only logs failures
def save_data():
    try:
        db.save(data)
    except Exception as e:
        logger.error(f"Save failed: {e}")

# RIGHT: Logs both outcomes
def save_data():
    try:
        db.save(data)
        logger.info("✅ Data saved successfully")
    except Exception as e:
        logger.error(f"❌ Save failed: {e}")
```

### 4. Logging Only at Depth
```python
# WRONG: Log in deep function (may not survive)
def deep_function():
    logger.debug("Processing item")  # Lost if Lambda crashes
    process_item()

# RIGHT: Log at boundary
def handler():
    logger.info("Starting item processing")  # Survives
    deep_function()
    logger.info("✅ Item processing complete")  # Survives
```

### 5. Confusing Execution Time with Hang Location
```python
# WRONG: "Lambda took 600s, so line X takes 600s"
# (Execution time is total, not per-line)

# RIGHT: Check stack trace for actual location
# (Stack trace shows where code is waiting)
```

---

## Complete Example

```python
import logging

logger = logging.getLogger(__name__)

def generate_report(symbol: str, date: str) -> dict:
    """Generate report with proper logging narrative."""

    # BEGINNING: Context
    logger.info(f"Starting report generation for {symbol}")
    logger.debug(f"Parameters: date={date}")

    try:
        # MIDDLE: Milestones
        logger.info("Fetching price data from Aurora")
        prices = fetch_prices(symbol, date)
        logger.info(f"✅ Fetched {len(prices)} price records")

        logger.info("Generating analysis sections")
        analysis = generate_analysis(prices)
        logger.info(f"✅ Generated {len(analysis)} sections")

        logger.info("Creating PDF document")
        pdf = create_pdf(analysis)
        logger.info(f"✅ PDF created: {pdf.size_kb}KB")

        # END: Success outcome
        logger.info(f"✅ Report complete for {symbol}")
        return {"status": "success", "pdf": pdf}

    except PriceDataError as e:
        # END: Failure outcome with context
        logger.error(f"❌ Report failed for {symbol}: Missing price data", exc_info=True)
        raise

    except Exception as e:
        # END: Unexpected failure
        logger.error(f"❌ Report failed for {symbol}: Unexpected error", exc_info=True)
        raise
```

---

## Integration with Principles

| Principle | Integration |
|-----------|-------------|
| #1 Defensive Programming | Verification logging (check and log outcomes) |
| #2 Progressive Evidence | Logs are Layer 3 observability evidence |
| #15 Infrastructure Contract | Log startup validation results |

---

## See Also

- [CLAUDE.md Principle #18](../../.claude/CLAUDE.md) - Core principle
- [Logging as Storytelling Abstraction](../../.claude/abstractions/architecture-2026-01-03-logging-as-storytelling.md) - Detailed abstraction
- [Error Investigation Skill](../../.claude/skills/error-investigation/) - Using logs for debugging

---

*Guide version: 2026-01-11*
*Principle: #18 Logging Discipline*
*Status: Active - extracted from CLAUDE.md for right abstraction level*
