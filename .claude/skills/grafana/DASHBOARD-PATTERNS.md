---
name: grafana-dashboard-patterns
description: Panel type reference, SQL patterns, CloudWatch dimensions, and template variables for Grafana dashboards
---

# Dashboard Patterns

Panel types, SQL query patterns, CloudWatch dimensions, and template variable configuration for `scripts/build-grafana-dashboards.py`.

---

## Panel Type Reference

All panel helpers are defined in `scripts/build-grafana-dashboards.py`. Each returns a Grafana panel dict.

### stat_panel

**Use**: Single metric display (counts, dates, latest values).

```python
stat_panel(title, sql, x, y, w=6, h=4, unit="", thresholds=None)
```

**Parameters**:
- `unit` — Grafana unit string (e.g., `"ms"`, `"percent"`)
- `thresholds` — List of `{"color": "...", "value": ...}` dicts for background coloring

**Example**:
```python
stat_panel(
    "Active Tickers",
    "SELECT COUNT(*) AS value FROM ticker_master WHERE is_active = 1",
    x=18, y=1, w=6, h=4,
)
```

### timeseries_panel

**Use**: Time-series line charts with MySQL data.

```python
timeseries_panel(title, sql, x, y, w=12, h=8, unit="")
```

**SQL format**: Must return `time`, `metric` (series name), `value` columns with `format: "time_series"`.

**Example**:
```python
timeseries_panel(
    "Buy Return Over Time",
    """SELECT
        backtest_date AS time,
        strategy_name AS metric,
        buy_total_return_pct AS value
    FROM backtest_results
    WHERE symbol = '$ticker'
        AND $__timeFilter(backtest_date)
    ORDER BY backtest_date""",
    x=0, y=16, w=12, h=8, unit="percent",
)
```

### table_panel

**Use**: Raw data tables with column headers.

```python
table_panel(title, sql, x, y, w=24, h=8)
```

**SQL format**: Column aliases become header names. Uses `format: "table"`.

**Example**:
```python
table_panel(
    "Recent Requests",
    """SELECT
        requested_at AS Time,
        ur.ticker AS Ticker,
        ur.platform AS Platform,
        ur.result AS Result,
        ur.duration_ms AS 'Duration (ms)'
    FROM user_requests ur
    ORDER BY requested_at DESC
    LIMIT 25""",
    x=0, y=24, w=24, h=8,
)
```

### barchart_panel

**Use**: Horizontal bar comparisons.

```python
barchart_panel(title, sql, x, y, w=12, h=8)
```

**Options**: `orientation: "horizontal"`, `showValue: "always"`, `barWidth: 0.7`.

### gauge_panel

**Use**: Threshold-based visualization (percentages, rates).

```python
gauge_panel(title, sql, x, y, w=6, h=5, unit="percent", max_val=100)
```

**Default thresholds**: Red (0) → Yellow (50%) → Green (75%) of `max_val`.

### piechart_panel

**Use**: Distribution visualization.

```python
piechart_panel(title, sql, x, y, w=12, h=8)
```

**SQL format**: Must return `metric` (label) and `value` (count) columns.

### cloudwatch_timeseries

**Use**: AWS CloudWatch metrics with dimension-based multi-series.

```python
cloudwatch_timeseries(title, metric_name, namespace, stat, x, y, w=12, h=8,
                      dimensions=None, period="300")
```

**Parameters**:
- `metric_name` — CloudWatch metric name (e.g., `"Errors"`, `"Duration"`)
- `namespace` — CloudWatch namespace (e.g., `"AWS/Lambda"`, `"DR/OpenRouter"`)
- `stat` — Statistic: `"Sum"`, `"Average"`, `"Maximum"`, `"Minimum"`
- `dimensions` — List of `(dim_key, dim_val)` tuples. One target per dimension value.
- `period` — Seconds between data points (default `"300"` = 5 min)

**Example**:
```python
lambda_dims = [("FunctionName", f"{PROJECT_NAME}-{base}-${{env}}")
               for base in LAMBDA_BASE_NAMES]
cloudwatch_timeseries(
    "Lambda Errors", "Errors", "AWS/Lambda", "Sum",
    x=0, y=6, w=12, h=8, dimensions=lambda_dims,
)
```

### row_panel

**Use**: Section headers to organize dashboard into collapsible rows.

```python
row_panel(title, y)
```

---

## SQL Patterns

### Time-Series Format

Grafana MySQL time-series requires 3 columns: `time`, `metric`, `value`.

```sql
SELECT
    backtest_date AS time,
    strategy_name AS metric,
    buy_total_return_pct AS value
FROM backtest_results
WHERE $__timeFilter(backtest_date)
ORDER BY backtest_date
```

### $__timeFilter Macro

Grafana replaces `$__timeFilter(column)` with a time range filter based on the dashboard time picker.

```sql
WHERE $__timeFilter(check_time)
-- Becomes: WHERE check_time BETWEEN '2026-03-18 00:00:00' AND '2026-03-19 00:00:00'
```

### Template Variable References

Use `$variable_name` in SQL to reference dashboard template variables:

```sql
WHERE symbol = '$ticker'
```

For CloudWatch dimensions, use `${env}` (curly braces needed in Python f-strings):

```python
f"{PROJECT_NAME}-{base}-${{env}}"
# Produces: "dr-daily-report-report-worker-${env}"
```

### Table Format

For `stat_panel` and `table_panel`, use `format: "table"`:
- `stat_panel`: Return single row with `value` column
- `table_panel`: Return multiple rows, column aliases become headers

---

## CloudWatch Patterns

### Lambda Dimensions

Lambda functions use `FunctionName` dimension with naming pattern:

```
{PROJECT_NAME}-{base_name}-${env}
```

Where `base_name` comes from `LAMBDA_BASE_NAMES`:
- `telegram-api`, `report-worker`, `ticker-scheduler`
- `precompute-controller`, `line-bot`, `credit-checker`

Labels strip the project prefix and env suffix for readability.

### Custom Namespaces

The project publishes custom CloudWatch metrics:

| Namespace | Metrics | Dimensions |
|-----------|---------|------------|
| `DR/OpenRouter` | `CreditBalance`, `DaysRemaining`, `ActualDailyCost` | `Environment` |
| `AWS/Lambda` | `Errors`, `Duration`, `Invocations` | `FunctionName` |
| `AWS/ApiGateway` | `Count`, `5XXError` | (default) |

---

## Template Variables

### Standard Variables (_env_template_variables)

Every dashboard calls `_env_template_variables()` to get 3 standard variables:

```python
def _env_template_variables(extra_vars=None):
    template_vars = [
        {
            "name": "datasource",
            "type": "datasource",
            "query": "mysql",
            "regex": "/mysql-.*/",
            "current": {"text": DEFAULT_MYSQL_DS, "value": DEFAULT_MYSQL_DS},
            "label": "Database",
        },
        {
            "name": "env",
            "type": "custom",
            "query": AVAILABLE_ENVS,
            "current": {"text": DEFAULT_ENV, "value": DEFAULT_ENV},
            "label": "Environment",
        },
        {
            "name": "cw_datasource",
            "type": "datasource",
            "query": "cloudwatch",
            "current": {"text": "cloudwatch", "value": "cloudwatch"},
            "label": "CloudWatch",
            "hide": 2,  # Hidden — only one CW datasource
        },
    ]
    if extra_vars:
        template_vars.extend(extra_vars)
    return template_vars
```

### Adding Dashboard-Specific Variables

Pass via `extra_vars` parameter. Example — ticker dropdown:

```python
ticker_var = {
    "name": "ticker",
    "type": "query",
    "datasource": MYSQL_DS,
    "query": "SELECT DISTINCT symbol FROM backtest_results WHERE strategy_name != '_consensus' ORDER BY symbol",
    "current": {"text": "DBS19", "value": "DBS19"},
    "refresh": 1,  # Refresh on time range change
    "sort": 1,     # Alphabetical
}

return {
    ...
    "templating": {"list": _env_template_variables(extra_vars=[ticker_var])},
}
```

### Variable Types

| Type | Use | Example |
|------|-----|---------|
| `datasource` | Select from registered datasources of a type | MySQL selector (`/mysql-.*/`) |
| `custom` | Static comma-separated values | Environment selector (`"dev"`) |
| `query` | Dynamic values from a SQL query | Ticker dropdown from `backtest_results` |

---

## Adding a New Dashboard

1. **Create builder function** in `build-grafana-dashboards.py`:
   ```python
   def build_my_dashboard():
       _reset_panel_id()
       panels = []
       # Add row_panel + content panels...
       return {
           "uid": "my-dashboard",      # Unique, URL-safe identifier
           "title": "My Dashboard",
           "panels": panels,
           "time": {"from": "now-24h", "to": "now"},
           "refresh": "5m",
           "schemaVersion": 39,
           "templating": {"list": _env_template_variables()},
       }
   ```

2. **Register in `main()`**:
   ```python
   builders = [
       build_pipeline_health_dashboard,
       build_strategy_performance_dashboard,
       build_user_analytics_dashboard,
       build_my_dashboard,  # Add here
   ]
   ```

3. **Deploy**: `python scripts/build-grafana-dashboards.py`

---

## Adding a New Panel

1. **Choose panel helper** based on visualization type (see reference above)

2. **Write SQL query** following the appropriate format:
   - Time-series: `time`, `metric`, `value` columns
   - Table: column aliases as headers
   - Stat: single `value` column
   - Pie/bar: `metric`/label and `value` columns

3. **Calculate `gridPos`**:
   - Grid is 24 columns wide
   - `x`: horizontal position (0-23)
   - `y`: vertical position (increment from previous panel's `y + h`)
   - `w`: width (common: 6, 8, 12, 24)
   - `h`: height (common: 4, 5, 6, 8)

4. **Append to panels list**:
   ```python
   panels.append(stat_panel(
       "My Metric",
       "SELECT COUNT(*) AS value FROM my_table",
       x=0, y=next_y, w=6, h=4,
   ))
   ```

5. **Use row_panel for sections**: Group related panels under a row header.

---

## Current Dashboards

| Dashboard | UID | Builder | Content |
|-----------|-----|---------|---------|
| Pipeline Health | `pipeline-health` | `build_pipeline_health_dashboard` | Data freshness, Lambda health, API Gateway, LLM credits, DB row counts, webhook health |
| Strategy Performance | `strategy-perf` | `build_strategy_performance_dashboard` | Buy/sell returns, Sharpe ratios, win rates, time-series performance |
| User Analytics | `user-analytics` | `build_user_analytics_dashboard` | User counts, request trends, platform split, top tickers, cache hit rate |
