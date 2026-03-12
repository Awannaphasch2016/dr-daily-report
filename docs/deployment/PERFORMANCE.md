# Performance Optimization

Backend (Lambda) and Frontend (Web Vitals) performance optimization techniques.

---

## Lambda Container Lifecycle

### Container Reuse Pattern

Lambda containers persist across invocations for performance:

```
First Invocation (Cold Start):
  1. Create container (~2s)
  2. Load Python runtime (~500ms)
  3. Import packages (~3s)
  4. Module-level initialization (~2s)
  5. Execute handler (~200ms)
  Total: ~7.5s

Second Invocation (Warm):
  1. Reuse existing container (0s)
  2. Skip imports (0s)
  3. Reuse singletons (0s)
  4. Execute handler (~200ms)
  Total: ~200ms (37x faster!)
```

**Key Insight:** Containers can be reused for 5-45 minutes (AWS doesn't guarantee duration).

---

## Cold Start Optimization Techniques

### 1. Module-Level Initialization

**Pattern:** Load heavy dependencies once at module level, not in handler.

```python
# src/agent.py - GOOD: Module-level imports
import logging
logger = logging.getLogger(__name__)

# Heavy imports at module level (loaded once per container)
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
import pandas as pd
import numpy as np

# Service singletons (persist across invocations)
_agent_instance: Optional[TickerAnalysisAgent] = None

def get_agent() -> TickerAnalysisAgent:
    """Get or create agent singleton (cold start optimization)"""
    global _agent_instance
    if _agent_instance is None:
        logger.info("🚀 Cold start: Initializing agent...")
        _agent_instance = TickerAnalysisAgent()
        logger.info("✅ Agent initialized")
    return _agent_instance

# Lambda handler
def lambda_handler(event, context):
    agent = get_agent()  # Reuses existing instance if warm
    return agent.process(event)
```

**Anti-Pattern:**
```python
# BAD: Importing inside handler (re-imports every invocation)
def lambda_handler(event, context):
    import pandas as pd  # ❌ Slow on every call
    import numpy as np
    from langchain_openai import ChatOpenAI
    # ...
```

### 2. Service Singleton Pattern

**Pattern:** Create service instances once, reuse across invocations.

```python
# src/api/ticker_service.py
_ticker_service: Optional[TickerService] = None

def get_ticker_service() -> TickerService:
    """Get or create global ticker service instance"""
    global _ticker_service
    if _ticker_service is None:
        logger.info("🚀 Cold start: Loading ticker data...")
        _ticker_service = TickerService()
        logger.info("✅ Loaded 2000+ tickers")
    return _ticker_service

# In Lambda handler
service = get_ticker_service()  # Fast after first call
```

**What gets cached:**
- CSV file data (2000+ tickers)
- DynamoDB connections
- yfinance ticker objects
- Compiled regex patterns

### 3. Pre-compiled Patterns

```python
# Module-level regex compilation
TICKER_PATTERN = re.compile(r'^[A-Z]{2,5}19$')  # Compiled once
PRICE_PATTERN = re.compile(r'\$?\d+\.?\d*')

def validate_ticker(ticker: str) -> bool:
    return TICKER_PATTERN.match(ticker)  # Fast lookup
```

### 4. Static File Loading

```python
# Load CSV once at module level
import pandas as pd
from pathlib import Path

# Module-level load (happens once per container)
TICKERS_DF = pd.read_csv(Path(__file__).parent / "data" / "tickers.csv")

def get_ticker_info(symbol: str) -> dict:
    # Fast lookup - no file I/O
    row = TICKERS_DF[TICKERS_DF['symbol'] == symbol]
    return row.to_dict('records')[0] if not row.empty else None
```

---

## Performance Metrics

### Measuring Cold Start vs Warm Start

**CloudWatch Logs Pattern:**
```
# Cold start (first invocation)
INIT_START Runtime Version: python:3.11.v1
INIT_DURATION: 7523.45 ms  ← Cold start overhead
DURATION: 245.67 ms         ← Handler execution

# Warm start (subsequent invocations)
DURATION: 198.34 ms         ← Handler execution only (no INIT)
```

**Monitoring Cold Starts:**
```bash
# Get cold start percentage
aws logs filter-log-events \
  --log-group-name /aws/lambda/dr-daily-report-telegram-api-dev \
  --filter-pattern "INIT_DURATION" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text | wc -l

# Total invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=dr-daily-report-telegram-api-dev \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600

# Cold start % = (cold starts / total invocations) * 100
```

### Benchmarking Container Reuse

```python
# Add to Lambda handler for tracking
import time
import os

# Track if container is warm
_container_start_time = time.time()

def lambda_handler(event, context):
    container_age = time.time() - _container_start_time

    # Log container age
    logger.info(f"Container age: {container_age:.1f}s")

    # First invocation on this container
    if container_age < 1:
        logger.info("🆕 COLD START")
    else:
        logger.info(f"♻️  WARM START (container reused for {container_age:.1f}s)")

    # ... handler logic
```

---

## Memory vs Performance Trade-offs

### Memory Configuration Impact

| Memory | CPU (proportional) | Cold Start | Warm Start | Cost per 100ms |
|--------|-------------------|------------|------------|----------------|
| 512 MB | 0.5 vCPU | ~8s | ~300ms | $0.0000008 |
| 1024 MB | 1 vCPU | ~5s | ~200ms | $0.0000016 |
| 1536 MB | 1.5 vCPU | ~4s | ~150ms | $0.0000024 |
| 2048 MB | 2 vCPU | ~3s | ~120ms | $0.0000032 |

**Key Insight:** More memory = more CPU = faster execution.

**Cost Analysis:**
```python
# Example: Report generation taking 60s

# With 512 MB: 60s execution = 600 compute units
Cost = 600 * $0.0000008 = $0.00048 per report

# With 1024 MB: 40s execution (faster CPU) = 400 compute units
Cost = 400 * $0.0000016 = $0.00064 per report

# Decision: 1024 MB is 25% more expensive but 33% faster
# Trade-off: User experience > marginal cost increase
```

### Recommended Configuration

```hcl
# terraform/telegram_api.tf
resource "aws_lambda_function" "telegram_api" {
  memory_size = 1024  # Sweet spot for most workloads
  timeout     = 120   # 2 minutes for report generation

  # Reserved concurrency (optional - prevents cost overruns)
  reserved_concurrent_executions = 10
}
```

---

## Minimizing Package Size

### Lambda Package Size Impact

Smaller packages = faster cold starts (less data to load).

**Current package size:**
```bash
# Check deployment package size
aws lambda get-function --function-name dr-daily-report-telegram-api-dev \
  --query 'Configuration.CodeSize' \
  --output text
# → 245678901 bytes (~246 MB)
```

### Optimization Techniques

**1. Use Lambda Layers for Dependencies**
```hcl
# terraform/telegram_api.tf
resource "aws_lambda_layer_version" "dependencies" {
  layer_name = "telegram-api-dependencies"

  # Separate heavy dependencies (pandas, numpy, langchain)
  compatible_runtimes = ["python3.11"]
}

resource "aws_lambda_function" "telegram_api" {
  layers = [aws_lambda_layer_version.dependencies.arn]
}
```

**2. Exclude Unnecessary Files from Docker Image**
```dockerfile
# Dockerfile.lambda.container
FROM public.ecr.aws/lambda/python:3.11

# Copy only requirements (not tests, docs)
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy only src/ (exclude tests/, docs/, .git/)
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Exclude test files
RUN find ${LAMBDA_TASK_ROOT} -type d -name "__pycache__" -exec rm -rf {} +
RUN find ${LAMBDA_TASK_ROOT} -type f -name "*.pyc" -delete
RUN find ${LAMBDA_TASK_ROOT} -type f -name "*.pyo" -delete
```

**3. Use Minimal Dependencies**
```txt
# requirements.txt - Only production dependencies
langchain-openai==0.1.0
langgraph==0.0.42
pandas==2.1.0
numpy==1.25.0

# NOT included (dev dependencies):
# pytest
# black
# mypy
```

---

## Container Reuse Best Practices

### 1. Avoid Global State Mutations

```python
# BAD: Global state can leak between invocations
_request_count = 0  # ❌ Persists across invocations

def lambda_handler(event, context):
    global _request_count
    _request_count += 1  # Leaks state!
    return {"count": _request_count}

# GOOD: Use context-scoped variables
def lambda_handler(event, context):
    request_id = context.request_id  # Fresh per invocation
    return {"request_id": request_id}
```

### 2. Clean Up Resources

```python
# GOOD: Close connections/files after use
def lambda_handler(event, context):
    conn = get_db_connection()
    try:
        result = conn.query("SELECT ...")
        return result
    finally:
        conn.close()  # Clean up for next invocation
```

### 3. Avoid /tmp Accumulation

```python
# BAD: /tmp fills up over time (512 MB limit)
def lambda_handler(event, context):
    with open("/tmp/report.pdf", "wb") as f:
        f.write(generate_pdf())  # Never cleaned up!

# GOOD: Clean up after use
def lambda_handler(event, context):
    tmp_file = f"/tmp/{context.request_id}.pdf"
    try:
        with open(tmp_file, "wb") as f:
            f.write(generate_pdf())
        # Upload to S3
        s3.upload_file(tmp_file, bucket, key)
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)  # Clean up
```

---

## Profiling Lambda Performance

### Using AWS X-Ray

```hcl
# terraform/telegram_api.tf
resource "aws_lambda_function" "telegram_api" {
  tracing_config {
    mode = "Active"  # Enable X-Ray tracing
  }
}
```

**Add instrumentation:**
```python
# src/agent.py
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture("analyze_ticker")
def analyze_ticker(ticker: str) -> dict:
    # X-Ray tracks this function's execution time
    return agent.analyze(ticker)

def lambda_handler(event, context):
    with xray_recorder.capture("lambda_handler"):
        # Trace entire handler
        result = analyze_ticker(event['ticker'])
    return result
```

### Custom CloudWatch Metrics

```python
import boto3
cloudwatch = boto3.client('cloudwatch')

def publish_metric(name: str, value: float, unit: str = 'Milliseconds'):
    cloudwatch.put_metric_data(
        Namespace='TelegramAPI',
        MetricData=[{
            'MetricName': name,
            'Value': value,
            'Unit': unit
        }]
    )

# In handler
start = time.time()
result = generate_report(ticker)
duration = (time.time() - start) * 1000

publish_metric('ReportGenerationTime', duration)
```

---

## Frontend Performance (Core Web Vitals)

### Key Metrics

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5s - 4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | 200ms - 500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1 - 0.25 | > 0.25 |
| TTFB (Time to First Byte) | < 200ms | 200ms - 500ms | > 500ms |

### Frontend Optimization Patterns

**1. Cache-First Loading**
```typescript
// App.tsx - Skip fetch if data exists
const handleSelectMarket = (market: Market) => {
  setSelectedTicker(market.id);
  setIsModalOpen(true);

  const hasCompleteData = market.report?.all_scores?.length > 0;
  if (!hasCompleteData) {
    fetchReport(market.id);  // Only fetch if needed
  }
};
```

**2. React Query for Automatic Caching**
```typescript
// Already installed but not used - enable for deduplication
import { useQuery } from '@tanstack/react-query';

const useReport = (ticker: string | null) => {
  return useQuery({
    queryKey: ['report', ticker],
    queryFn: () => apiClient.getCachedReport(ticker),
    staleTime: 5 * 60 * 1000,  // 5 min cache
  });
};
```

**3. Code Splitting**
```typescript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'vendor-react': ['react', 'react-dom'],
        'vendor-charts': ['recharts'],
      },
    },
  },
}
```

**4. Skeleton Loading**
```typescript
// Prevent CLS with fixed-dimension skeletons
const ModalSkeleton = () => (
  <div className="animate-pulse">
    <div className="h-8 bg-gray-200 rounded w-3/4 mb-4" />
    <div className="h-64 bg-gray-200 rounded mb-4" />
  </div>
);
```

### Performance Monitoring

**Add Web Vitals to Frontend:**
```typescript
// main.tsx
import { onLCP, onFID, onCLS, onINP, onTTFB } from 'web-vitals';

onLCP(console.log);
onINP(console.log);
onCLS(console.log);
onTTFB(console.log);
```

### Frontend Performance Checklist

- [ ] LCP < 2.5s (Lighthouse audit)
- [ ] INP < 200ms (user interactions)
- [ ] CLS < 0.1 (layout stability)
- [ ] Bundle size < 200KB (gzipped)
- [ ] Images lazy loaded
- [ ] Cache-first data loading
- [ ] Skeleton loading states

---

## Performance Skills Reference

For comprehensive performance investigation:
- [Performance Investigation Skill](../../.claude/skills/performance-investigation/SKILL.md)
- [Metrics → Code Mapping](../../.claude/skills/performance-investigation/METRICS-MAP.md)
- [Optimization Patterns](../../.claude/skills/performance-investigation/OPTIMIZATION-PATTERNS.md)

---

## See Also

- [Lambda Best Practices](LAMBDA_BEST_PRACTICES.md) - NumPy serialization, environment detection
- [Lambda Versioning](LAMBDA_VERSIONING.md) - Zero-downtime deployment
- [CI/CD Architecture](CI_CD.md) - Deployment pipeline
