---
name: perf
description: Performance monitoring and diagnostics using CloudWatch metrics, logs, and alarms
accepts_args: true
arg_schema:
  - name: mode
    required: false
    description: One of status, diagnose, trace, recommend (default: status)
  - name: target
    required: false
    description: Specific component to analyze (e.g., telegram-api, aurora, frontend)
composition:
  - skill: performance-investigation
---

# Performance Command

**Purpose**: Quick access to performance metrics, diagnostics, and optimization recommendations.

**Mode**: `observe` (Tuple Effect: Reveals performance Constraints for decision-making)

---

## Quick Reference

```bash
# Quick health check (default)
/perf
/perf status

# Diagnose specific component
/perf diagnose telegram-api
/perf diagnose aurora
/perf diagnose report-worker

# Deep trace into layer
/perf trace lambda
/perf trace aurora
/perf trace frontend

# Get optimization recommendations
/perf recommend
/perf recommend telegram-api
```

---

## Modes

### `status` (default) - Quick Health Check

Shows current performance state at a glance.

**What it checks**:
- Active CloudWatch alarms
- Error rates (last 15 min)
- P50/P95/P99 latency for key Lambdas
- Aurora connection count and CPU
- Recent error patterns

**Output format**:
```markdown
## Performance Status

**Time**: 2026-01-15 14:30 UTC
**Environment**: dev

### Alarms
| Alarm | Status | Since |
|-------|--------|-------|
| telegram-api-errors | ✅ OK | - |
| report-worker-errors | ⚠️ ALARM | 10 min ago |

### Lambda Latency (last 15 min)
| Function | P50 | P95 | P99 | Cold Start % |
|----------|-----|-----|-----|--------------|
| telegram-api | 1.2s | 3.5s | 8.2s | 15% |
| report-worker | 2.1s | 5.0s | 12s | 8% |

### Aurora
- Connections: 12/50
- CPU: 25%
- Read IOPS: 150

### Recent Errors (last 15 min)
- telegram-api: 3 errors (timeout)
- report-worker: 0 errors

**Quick Assessment**: ⚠️ Minor issues - report-worker alarm active
```

---

### `diagnose` - Root Cause Analysis

Deep dive into specific component performance issues.

**Usage**:
```bash
/perf diagnose telegram-api
/perf diagnose aurora
/perf diagnose scheduler
```

**What it does**:
1. Queries CloudWatch Logs Insights for errors and slow operations
2. Analyzes metric patterns (duration, memory, cold starts)
3. Compares current vs baseline (last 24h average)
4. Identifies correlations (e.g., cold starts → latency spikes)

**Output format**:
```markdown
## Diagnose: telegram-api

**Time window**: Last 1 hour
**Environment**: dev

### Error Analysis
```
Top error patterns:
1. TimeoutError (5 occurrences)
   - Correlation: 100% during cold starts
   - First seen: 14:15 UTC

2. ConnectionError (2 occurrences)
   - Correlation: Aurora connection pool exhausted
```

### Latency Breakdown
| Phase | Duration | % of Total |
|-------|----------|------------|
| Cold start | 2.5s | 45% |
| Aurora query | 1.8s | 32% |
| LLM call | 1.0s | 18% |
| Other | 0.3s | 5% |

### Baseline Comparison
| Metric | Current | Baseline (24h) | Delta |
|--------|---------|----------------|-------|
| P95 latency | 5.2s | 3.1s | +68% ⚠️ |
| Error rate | 2.1% | 0.5% | +320% ⚠️ |
| Cold start % | 25% | 12% | +108% ⚠️ |

### Root Cause Hypothesis
**Primary**: High cold start rate (25%) causing timeouts
**Secondary**: Aurora connection contention during bursts

### Suggested Actions
1. Add provisioned concurrency (reduces cold start to <1%)
2. Implement connection pooling for Aurora
3. Add retry with exponential backoff for transient errors
```

---

### `trace` - Deep Layer Investigation

Detailed analysis of specific infrastructure layer.

**Layers**:
- `lambda` - Lambda execution details (memory, duration, cold starts)
- `aurora` - Database performance (queries, connections, CPU)
- `frontend` - Web Vitals (if configured), bundle size, CDN
- `api-gateway` - API Gateway latency, 4xx/5xx rates

**Usage**:
```bash
/perf trace lambda
/perf trace aurora
```

**Output** (lambda example):
```markdown
## Trace: Lambda Layer

### telegram-api-dev
| Metric | Value | Status |
|--------|-------|--------|
| Memory configured | 512 MB | |
| Memory used (avg) | 380 MB | ✅ OK |
| Memory used (max) | 485 MB | ⚠️ Near limit |
| Duration P50 | 1.2s | ✅ OK |
| Duration P95 | 3.5s | ⚠️ High |
| Cold start rate | 15% | ⚠️ High |
| Cold start duration | 2.5s | ⚠️ High |
| Concurrent executions | 5 | ✅ OK |
| Throttles | 0 | ✅ OK |

### Optimization Opportunities
1. **Memory**: Increase to 1024MB (may reduce duration)
2. **Cold start**: Add provisioned concurrency (5 instances)
3. **VPC**: Consider VPC endpoint for faster ENI attach

### report-worker-dev
[Similar breakdown...]
```

---

### `recommend` - Optimization Suggestions

Generate actionable optimization recommendations based on current metrics.

**Usage**:
```bash
/perf recommend              # All components
/perf recommend telegram-api # Specific component
```

**Output**:
```markdown
## Performance Recommendations

### High Priority

#### 1. Add Provisioned Concurrency for telegram-api
**Problem**: 25% cold start rate causing P95 latency of 5.2s
**Solution**: Add 5 provisioned concurrent instances
**Expected improvement**: P95 latency 5.2s → 2.0s (62% reduction)
**Cost impact**: +$15/month
**Effort**: Low (Terraform change)

```hcl
# terraform/telegram_api.tf
resource "aws_lambda_provisioned_concurrency_config" "telegram_api" {
  function_name                     = aws_lambda_function.telegram_api.function_name
  provisioned_concurrent_executions = 5
  qualifier                         = aws_lambda_alias.telegram_api_live.name
}
```

#### 2. Increase Lambda Memory
**Problem**: Memory at 94% utilization, potential GC pressure
**Solution**: Increase from 512MB to 1024MB
**Expected improvement**: Duration reduction 10-20%
**Cost impact**: +$8/month (offset by faster execution)
**Effort**: Low (Terraform change)

### Medium Priority

#### 3. Implement Aurora Connection Pooling
**Problem**: Connection contention during traffic bursts
**Solution**: Use RDS Proxy or application-level pooling
**Expected improvement**: Reduce connection errors by 90%
**Cost impact**: +$20/month (RDS Proxy)
**Effort**: Medium (code + infrastructure)

### Low Priority

#### 4. Enable X-Ray Tracing
**Problem**: Limited visibility into request flow
**Solution**: Enable X-Ray for Lambda functions
**Expected improvement**: Better debugging, trace visualization
**Cost impact**: ~$5/month
**Effort**: Low (Terraform + code change)
```

---

## CloudWatch Integration

This command uses the CloudWatch MCP tools:

| Tool | Used For |
|------|----------|
| `mcp__cloudwatch__get_active_alarms` | Status: active alarms |
| `mcp__cloudwatch__execute_log_insights_query` | Diagnose: error patterns, slow queries |
| `mcp__cloudwatch__get_metric_data` | Trace: Lambda metrics, Aurora metrics |
| `mcp__cloudwatch__analyze_metric` | Recommend: trend analysis |

---

## Environment Targeting

By default, `/perf` targets the current environment based on branch:
- `dev` branch → dev environment
- `main` branch → staging environment
- Tagged commits → production environment

Override with environment prefix:
```bash
/dev /perf status      # Explicit dev
/stg /perf diagnose    # Explicit staging
/prd /perf status      # Explicit production (read-only)
```

---

## Resource Naming

Resources are resolved using project naming convention:

| Component | Log Group | Lambda |
|-----------|-----------|--------|
| telegram-api | `/aws/lambda/dr-daily-report-telegram-api-{env}` | `dr-daily-report-telegram-api-{env}` |
| report-worker | `/aws/lambda/dr-daily-report-report-worker-{env}` | `dr-daily-report-report-worker-{env}` |
| scheduler | `/aws/lambda/dr-daily-report-scheduler-{env}` | `dr-daily-report-scheduler-{env}` |
| linebot | `/aws/lambda/dr-daily-report-linebot-{env}` | `dr-daily-report-linebot-{env}` |

---

## Skill Integration

This command references the `performance-investigation` skill for:
- Metrics glossary (LCP, TTFB, etc.)
- Metrics → Infrastructure → Code mapping
- Optimization patterns with code examples
- Investigation checklist

See: `.claude/skills/performance-investigation/`

---

## Examples

### Example 1: Quick Morning Check

```bash
/perf
```
→ Shows alarms, latency, errors for quick assessment

### Example 2: Investigate Slow API

```bash
/perf diagnose telegram-api
```
→ Deep dive into telegram-api performance, identifies bottlenecks

### Example 3: Pre-Optimization Analysis

```bash
/perf trace lambda
/perf recommend
```
→ Get detailed Lambda metrics, then specific recommendations

### Example 4: Production Monitoring

```bash
/prd /perf status
```
→ Check production performance (read-only)

---

## Related Commands

| Command | Relationship |
|---------|--------------|
| `/optimize` | Uses `/perf` for measurement, then optimizes with invariant preservation |
| `/invariant` | Performance invariants checked after optimization |
| `/dev`, `/stg`, `/prd` | Environment targeting for metrics |

---

## See Also

- `.claude/skills/performance-investigation/` - Detailed investigation patterns
- `.claude/invariants/frontend-invariants.md` - Performance invariants (Web Vitals)
- `terraform/monitoring.tf` - CloudWatch alarm definitions
