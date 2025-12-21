# Lambda Logging Configuration Guide

## The Problem

AWS Lambda Python runtime **pre-configures logging before your code runs**. This breaks the standard `logging.basicConfig()` pattern that works in local development.

### What Doesn't Work

```python
# ❌ This does NOTHING in Lambda
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("This won't appear")  # Invisible if root logger at WARNING
```

### Why It Fails

**Lambda runtime initialization (before your code):**
```python
# Lambda does this automatically:
import logging
import sys

root_logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
root_logger.addHandler(handler)
root_logger.setLevel(logging.WARNING)  # Default level

# NOW your handler code runs
```

**By the time your code executes:**
- Root logger already has handlers (basicConfig checks this)
- `basicConfig()` becomes a no-op: "does nothing if root logger already has handlers"
- Your `logger.info()` calls are invisible (root logger at WARNING, filters them out)

## The Solution

**Set root logger level directly:**

```python
import logging

# Configure for both Lambda and local dev
root_logger = logging.getLogger()
if root_logger.handlers:  # Lambda (already configured)
    root_logger.setLevel(logging.INFO)
else:  # Local dev (needs configuration)
    logging.basicConfig(level=logging.INFO)

# Now create module logger
logger = logging.getLogger(__name__)

# This works in both environments
logger.info("✅ This appears in CloudWatch")
logger.warning("⚠️ This also appears")
logger.error("❌ And this too")
```

## Canonical Pattern for Lambda Handlers

**At the top of every Lambda handler module:**

```python
# src/scheduler/ticker_fetcher_handler.py
import logging
import json
from datetime import datetime
from typing import Any, Dict

# =============================================================================
# Logging Configuration (Lambda-compatible)
# =============================================================================
root_logger = logging.getLogger()
if root_logger.handlers:  # Lambda runtime already configured
    root_logger.setLevel(logging.INFO)
else:  # Local development
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Lambda handler started")  # ✅ Visible in CloudWatch
    # ... rest of handler
```

## Common Pitfalls

### Pitfall 1: Setting Level on Child Logger

```python
# ❌ WRONG: Sets level on module logger, not root
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Doesn't help if root is WARNING
```

**Why it fails:** Child loggers inherit the root logger's level. Setting child logger to INFO doesn't override root logger's WARNING filter.

**Fix:** Set root logger level, not child logger.

### Pitfall 2: Using basicConfig() in Lambda

```python
# ❌ WRONG: No-op in Lambda
logging.basicConfig(level=logging.INFO)
```

**Why it fails:** Root logger already has handlers from Lambda runtime.

**Fix:** Use the if/else pattern shown above.

### Pitfall 3: Assuming print() and logger Are Equivalent

```python
print("Debug message")      # ✅ Always visible (stdout → CloudWatch)
logger.info("Debug message") # ❌ Invisible if root logger at WARNING
```

**When to use each:**
- `print()`: Temporary debugging, proof-of-life checks, development
- `logger.info()`: Production logging, structured messages, filterable by level

### Pitfall 4: Configuring Logging in Imported Modules

```python
# src/scheduler/ticker_fetcher.py
import logging
logger = logging.getLogger(__name__)

# ❌ WRONG: Trying to configure here
logging.basicConfig(level=logging.INFO)  # No effect

class TickerFetcher:
    def __init__(self):
        logger.info("Initializing...")  # Invisible if root at WARNING
```

**Why it fails:** By the time this module is imported, Lambda runtime already configured logging. The import happens AFTER Lambda's setup.

**Fix:** Only configure logging in the entry point handler. All other modules just create loggers.

## Log Levels and CloudWatch

### Default Lambda Behavior

| Level | Numeric Value | Visible in CloudWatch? | Use Case |
|-------|--------------|------------------------|----------|
| DEBUG | 10 | ❌ No (filtered by WARNING) | Detailed diagnostics |
| INFO  | 20 | ❌ No (filtered by WARNING) | General information |
| WARNING | 30 | ✅ Yes | Recoverable issues |
| ERROR | 40 | ✅ Yes | Errors requiring attention |
| CRITICAL | 50 | ✅ Yes | System failures |

**After setting root to INFO:**

| Level | Visible? | Use Case |
|-------|----------|----------|
| DEBUG | ❌ No | Needs root at DEBUG |
| INFO  | ✅ Yes | General flow tracking |
| WARNING | ✅ Yes | Potential issues |
| ERROR | ✅ Yes | Actual failures |
| CRITICAL | ✅ Yes | System-level failures |

### Monitoring Implications

From CLAUDE.md "Log Level Determines Discoverability":

- **ERROR/CRITICAL**: Monitored, triggers alerts, visible in dashboards
- **WARNING**: Logged but not alerted, requires manual log review
- **INFO/DEBUG**: Requires active searching, not monitored

**Pattern:** Use ERROR for failures that need alerts, WARNING for issues that need investigation, INFO for normal operations.

## Testing Logging Configuration

### Local Development Test

```python
# test_logging.py
import logging

# Your handler's logging setup
root_logger = logging.getLogger()
if root_logger.handlers:
    root_logger.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Test all levels
logger.debug("DEBUG: Should not appear (root at INFO)")
logger.info("INFO: Should appear")
logger.warning("WARNING: Should appear")
logger.error("ERROR: Should appear")

print(f"Root logger level: {logging.getLevelName(root_logger.level)}")
print(f"Root logger handlers: {root_logger.handlers}")
```

**Expected output:**
```
INFO: Should appear
WARNING: Should appear
ERROR: Should appear
Root logger level: INFO
Root logger handlers: [<StreamHandler <stderr> (NOTSET)>]
```

### Lambda Environment Test

Create a test Lambda handler:

```python
# test_lambda_logging.py
import logging
import json

# Apply fix
root_logger = logging.getLogger()
if root_logger.handlers:
    root_logger.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    # Diagnostic info
    print(f"🔍 Root logger level: {logging.getLevelName(root_logger.level)}")
    print(f"🔍 Root logger handlers: {root_logger.handlers}")

    # Test all levels
    logger.debug("DEBUG message")
    logger.info("INFO message")
    logger.warning("WARNING message")
    logger.error("ERROR message")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'root_level': logging.getLevelName(root_logger.level),
            'handlers_count': len(root_logger.handlers)
        })
    }
```

**Deploy and invoke:**
```bash
aws lambda invoke \
  --function-name test-logging-lambda \
  --payload '{}' \
  /tmp/response.json

# Check logs
aws logs tail /aws/lambda/test-logging-lambda --since 1m
```

**Expected CloudWatch output:**
```
🔍 Root logger level: INFO
🔍 Root logger handlers: [<LambdaLoggerHandler (NOTSET)>]
INFO message
WARNING message
ERROR message
```

## Migration Checklist

If you have existing Lambda handlers using `basicConfig()`:

- [ ] Locate all Lambda handler modules (files with `lambda_handler()` function)
- [ ] Replace `logging.basicConfig()` with root logger pattern
- [ ] Test locally to ensure logs still appear
- [ ] Deploy to Lambda
- [ ] Verify logs appear in CloudWatch
- [ ] Check that INFO-level logs are now visible
- [ ] Remove any temporary `print()` debugging statements

## Real-World Example

**Before (broken in Lambda):**

```python
# src/scheduler/ticker_fetcher_handler.py
import logging

logging.basicConfig(level=logging.INFO)  # ❌ No-op in Lambda
logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Handler started")  # ❌ Invisible in CloudWatch

    from src.scheduler.ticker_fetcher import TickerFetcher
    fetcher = TickerFetcher()  # ❌ Initialization logs invisible
```

**After (works everywhere):**

```python
# src/scheduler/ticker_fetcher_handler.py
import logging

# Lambda-compatible logging setup
root_logger = logging.getLogger()
if root_logger.handlers:  # Lambda
    root_logger.setLevel(logging.INFO)
else:  # Local dev
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    logger.info("Handler started")  # ✅ Visible in CloudWatch

    from src.scheduler.ticker_fetcher import TickerFetcher
    fetcher = TickerFetcher()  # ✅ Initialization logs visible
```

## Why Lambda Works This Way

**Design philosophy:**
- **Standardization**: All Lambda functions log consistently
- **Zero-config**: Works out of the box for simple cases
- **CloudWatch integration**: stdout/stderr automatically captured
- **Managed runtime**: Lambda controls the execution environment

**Trade-off:** You lose control over initial logging setup, but gain:
- Automatic CloudWatch integration
- Consistent log format across all functions
- No need to configure handlers or formatters
- Built-in request ID tracking

## References

- [AWS Lambda Python Logging](https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html)
- [Python logging.basicConfig() docs](https://docs.python.org/3/library/logging.html#logging.basicConfig)
- CLAUDE.md: "Log Level Determines Discoverability" principle

## Quick Reference

```python
# ✅ CORRECT: Works in Lambda and local dev
root_logger = logging.getLogger()
if root_logger.handlers:
    root_logger.setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

# ❌ WRONG: No-op in Lambda
logging.basicConfig(level=logging.INFO)

# ❌ WRONG: Sets child logger, not root
logger.setLevel(logging.INFO)

# ✅ For debugging: Always works
print("Debug output")

# ✅ For production: Use after configuring root logger
logger.info("Production log")
```
