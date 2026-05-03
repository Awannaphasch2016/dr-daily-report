#!/usr/bin/env python3
"""Build Grafana dashboards via API and create public snapshots.

Usage:
    python scripts/build-grafana-dashboards.py

Authentication: Uses AWS IAM credentials (via boto3) to self-provision a
short-lived Grafana Service Account Token. No manual API key needed.

Creates 5 dashboards:
    1. Pipeline Health (CloudWatch + MySQL)
    2. Strategy Performance (MySQL)
    3. User Analytics (MySQL)
    4. Data Freshness (MySQL)
    5. Daily Ticker Coverage (MySQL)

Each dashboard gets a public snapshot URL viewable without login.
"""

import json
import os
import sys

import boto3
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REGION = "ap-southeast-1"
WORKSPACE_ID = "g-4df4c51648"
ENDPOINT = f"https://{WORKSPACE_ID}.grafana-workspace.{REGION}.amazonaws.com"

# Datasources use Grafana template variables — resolved at render time.
# Requires MySQL datasources named "mysql-dev", "mysql-staging", "mysql-prod".
MYSQL_DS = {"uid": "${datasource}", "type": "mysql"}
CW_DS = {"uid": "${cw_datasource}", "type": "cloudwatch"}

HEADERS = {}

# --- Environment configuration (single place to expand later) ---
# To add staging/prod: change AVAILABLE_ENVS and DEFAULT_ENV
AVAILABLE_ENVS = "dev"  # Future: "dev,staging,prod"
DEFAULT_ENV = "dev"     # Future: "prod"
DEFAULT_MYSQL_DS = f"mysql-{DEFAULT_ENV}"
PROJECT_NAME = "dr-daily-report"

# Lambda base names — combined with ${env} in CloudWatch panels
LAMBDA_BASE_NAMES = [
    "telegram-api",
    "report-worker",
    "ticker-scheduler",
    "precompute-controller",
    "line-bot",
    "credit-checker",
]


# ---------------------------------------------------------------------------
# Panel helpers
# ---------------------------------------------------------------------------
def _panel_id():
    """Auto-incrementing panel ID."""
    _panel_id.counter = getattr(_panel_id, "counter", 0) + 1
    return _panel_id.counter


def _reset_panel_id():
    _panel_id.counter = 0


def stat_panel(title, sql, x, y, w=6, h=4, unit="", thresholds=None):
    """Create a stat panel with MySQL query."""
    panel = {
        "id": _panel_id(),
        "type": "stat",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "options": {"colorMode": "background", "graphMode": "none", "textMode": "value"},
        "fieldConfig": {"defaults": {}, "overrides": []},
    }
    if unit:
        panel["fieldConfig"]["defaults"]["unit"] = unit
    if thresholds:
        panel["fieldConfig"]["defaults"]["thresholds"] = {
            "mode": "absolute",
            "steps": thresholds,
        }
    return panel


def timeseries_panel(title, sql, x, y, w=12, h=8, unit=""):
    """Create a time-series panel with MySQL query."""
    panel = {
        "id": _panel_id(),
        "type": "timeseries",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "time_series", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
    }
    if unit:
        panel["fieldConfig"]["defaults"]["unit"] = unit
    return panel


def table_panel(title, sql, x, y, w=24, h=8, overrides=None):
    """Create a table panel with MySQL query.

    `overrides` (optional) — list of Grafana field-override dicts, e.g. to
    color a cell by value. Pass `None` (default) to keep the panel uncoloured.
    """
    return {
        "id": _panel_id(),
        "type": "table",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": overrides or []},
        "options": {"showHeader": True, "sortBy": []},
    }


def barchart_panel(title, sql, x, y, w=12, h=8, orientation="horizontal", overrides=None):
    """Create a bar chart panel with MySQL query.

    `orientation` — "horizontal" (default, days/categories on Y) or "vertical"
    (categories on X — natural for time-series-like data).
    `overrides` — optional list of Grafana field-override dicts (e.g., to color
    a specific series by name). Pass `None` to keep the panel uncoloured.
    """
    return {
        "id": _panel_id(),
        "type": "barchart",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": overrides or []},
        "options": {"orientation": orientation, "showValue": "always", "barWidth": 0.7},
    }


def gauge_panel(title, sql, x, y, w=6, h=5, unit="percent", max_val=100):
    """Create a gauge panel with MySQL query."""
    return {
        "id": _panel_id(),
        "type": "gauge",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "max": max_val,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": max_val * 0.5},
                        {"color": "green", "value": max_val * 0.75},
                    ],
                },
            },
            "overrides": [],
        },
    }


def piechart_panel(title, sql, x, y, w=12, h=8):
    """Create a pie chart panel with MySQL query."""
    return {
        "id": _panel_id(),
        "type": "piechart",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "right"}},
    }


def cloudwatch_timeseries(title, metric_name, namespace, stat, x, y, w=12, h=8,
                          dimensions=None, period="300"):
    """Create a time-series panel with CloudWatch query."""
    targets = []
    if dimensions:
        # One target per dimension value (e.g., per Lambda function)
        for i, (dim_key, dim_val) in enumerate(dimensions):
            targets.append({
                "refId": chr(65 + i),
                "datasource": CW_DS,
                "namespace": namespace,
                "metricName": metric_name,
                "statistics": [stat],
                "dimensions": {dim_key: [dim_val]},
                "period": period,
                "id": f"m{i}",
                "label": dim_val.replace(f"{PROJECT_NAME}-", "").replace("-${env}", ""),
                "region": "ap-southeast-1",
                "matchExact": True,
            })
    else:
        targets.append({
            "refId": "A",
            "datasource": CW_DS,
            "namespace": namespace,
            "metricName": metric_name,
            "statistics": [stat],
            "dimensions": {},
            "period": period,
            "region": "ap-southeast-1",
        })

    return {
        "id": _panel_id(),
        "type": "timeseries",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": CW_DS,
        "targets": targets,
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
    }


def state_timeline_panel(title, sql, x, y, w=24, h=4, thresholds=None, data_links=None):
    """Create a state-timeline panel (calendar-row heatmap) with MySQL query.

    SQL must return time-series format (time, metric, value). Cell color is
    driven by `value` against `thresholds`. Useful for "row of cells per day"
    coverage views where you want to spot good/bad days at a glance.

    `data_links` (optional) — list of {title, url} dicts. URL can substitute
    Grafana variables like ${__value.time:date:YYYY-MM-DD} to drive cross-panel
    interactivity by writing to template variables on click.
    """
    defaults = {
        "custom": {"lineWidth": 0, "fillOpacity": 80},
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": thresholds or [
                {"color": "red", "value": None},
                {"color": "yellow", "value": 100},
                {"color": "green", "value": 250},
            ],
        },
    }
    if data_links:
        defaults["links"] = data_links
    return {
        "id": _panel_id(),
        "type": "state-timeline",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "time_series", "refId": "A"}],
        "options": {
            "showValue": "auto",
            "alignValue": "center",
            "rowHeight": 0.9,
            "mergeValues": False,
            "legend": {"displayMode": "list", "placement": "bottom"},
        },
        "fieldConfig": {
            "defaults": defaults,
            "overrides": [],
        },
    }


def row_panel(title, y):
    """Create a row (section header) panel."""
    return {
        "id": _panel_id(),
        "type": "row",
        "title": title,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "collapsed": False,
    }


def _env_template_variables(extra_vars=None):
    """Template variables for environment switching.

    Provides datasource + env dropdowns at the top of every dashboard.
    To add staging/prod: change AVAILABLE_ENVS and DEFAULT_ENV at top of file.
    """
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
            "hide": 2,  # Hidden — only one CW datasource, avoids hardcoding UID
        },
    ]
    if extra_vars:
        template_vars.extend(extra_vars)
    return template_vars


# ---------------------------------------------------------------------------
# Dashboard 1: Pipeline Health
# ---------------------------------------------------------------------------
def build_pipeline_health_dashboard():
    _reset_panel_id()
    panels = []

    # Row: Data Freshness
    panels.append(row_panel("Data Freshness", 0))
    panels.append(stat_panel(
        "Prices Last Date",
        "SELECT MAX(price_date) AS value FROM daily_prices",
        x=0, y=1, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Indicators Last Date",
        "SELECT MAX(indicator_date) AS value FROM daily_indicators",
        x=6, y=1, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Reports Last Date",
        "SELECT MAX(report_date) AS value FROM precomputed_reports",
        x=12, y=1, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Active Tickers",
        "SELECT COUNT(*) AS value FROM ticker_master WHERE is_active = 1",
        x=18, y=1, w=6, h=4,
    ))

    # Row: Lambda Health
    panels.append(row_panel("Lambda Health (CloudWatch)", 5))
    lambda_dims = [("FunctionName", f"{PROJECT_NAME}-{base}-${{env}}") for base in LAMBDA_BASE_NAMES]
    panels.append(cloudwatch_timeseries(
        "Lambda Errors", "Errors", "AWS/Lambda", "Sum",
        x=0, y=6, w=12, h=8, dimensions=lambda_dims,
    ))
    panels.append(cloudwatch_timeseries(
        "Lambda Duration (avg ms)", "Duration", "AWS/Lambda", "Average",
        x=12, y=6, w=12, h=8, dimensions=lambda_dims,
    ))

    # Row: API Gateway
    panels.append(row_panel("API Gateway", 14))
    panels.append(cloudwatch_timeseries(
        "API Requests", "Count", "AWS/ApiGateway", "Sum",
        x=0, y=15, w=12, h=8,
    ))
    panels.append(cloudwatch_timeseries(
        "API 5xx Errors", "5XXError", "AWS/ApiGateway", "Sum",
        x=12, y=15, w=12, h=8,
    ))

    # Row: LLM Credits (OpenRouter)
    panels.append(row_panel("LLM Credits", 23))
    credit_dims = [("Environment", "${env}")]
    panels.append(cloudwatch_timeseries(
        "Credit Balance ($)", "CreditBalance", "DR/OpenRouter", "Minimum",
        x=0, y=24, w=8, h=6, dimensions=credit_dims,
    ))
    panels.append(cloudwatch_timeseries(
        "Days Remaining", "DaysRemaining", "DR/OpenRouter", "Minimum",
        x=8, y=24, w=8, h=6, dimensions=credit_dims,
    ))
    panels.append(cloudwatch_timeseries(
        "Actual Daily Cost ($)", "ActualDailyCost", "DR/OpenRouter", "Maximum",
        x=16, y=24, w=8, h=6, dimensions=credit_dims,
    ))
    panels.append(cloudwatch_timeseries(
        "Credit Balance History", "CreditBalance", "DR/OpenRouter", "Average",
        x=0, y=30, w=24, h=8, dimensions=credit_dims,
    ))

    # Row: Database Metrics
    panels.append(row_panel("Database Row Counts", 38))
    panels.append(stat_panel(
        "Price Records",
        "SELECT COUNT(*) AS value FROM daily_prices",
        x=0, y=39, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Indicator Records",
        "SELECT COUNT(*) AS value FROM daily_indicators",
        x=6, y=39, w=6, h=4,
    ))
    panels.append(stat_panel(
        "User Requests",
        "SELECT COUNT(*) AS value FROM user_requests",
        x=12, y=39, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Total Users",
        "SELECT COUNT(*) AS value FROM users",
        x=18, y=39, w=6, h=4,
    ))

    # Row: Webhook Health
    panels.append(row_panel("Webhook Health", 43))
    panels.append(stat_panel(
        "Webhook Status",
        "SELECT status AS value FROM webhook_health_checks WHERE endpoint='line_webhook' ORDER BY check_time DESC LIMIT 1",
        x=0, y=44, w=6, h=4,
        thresholds=[
            {"color": "red", "value": None},
        ],
    ))
    panels.append(gauge_panel(
        "Uptime % (30d)",
        "SELECT ROUND(SUM(status='healthy')*100.0/COUNT(*),1) AS value FROM webhook_health_checks WHERE check_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
        x=6, y=44, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Avg Latency (7d)",
        "SELECT ROUND(AVG(latency_ms)) AS value FROM webhook_health_checks WHERE check_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        x=12, y=44, w=6, h=4, unit="ms",
    ))
    panels.append(stat_panel(
        "Last Check",
        "SELECT MAX(check_time) AS value FROM webhook_health_checks",
        x=18, y=44, w=6, h=4,
    ))
    panels.append(timeseries_panel(
        "Webhook Status Over Time",
        """SELECT
            check_time AS time,
            endpoint AS metric,
            CASE status WHEN 'healthy' THEN 1 WHEN 'degraded' THEN 0.5 ELSE 0 END AS value
        FROM webhook_health_checks
        WHERE $__timeFilter(check_time)
        ORDER BY check_time""",
        x=0, y=48, w=12, h=8,
    ))
    panels.append(timeseries_panel(
        "Webhook Latency Over Time",
        """SELECT
            check_time AS time,
            endpoint AS metric,
            latency_ms AS value
        FROM webhook_health_checks
        WHERE $__timeFilter(check_time)
        ORDER BY check_time""",
        x=12, y=48, w=12, h=8, unit="ms",
    ))
    panels.append(table_panel(
        "Recent Health Checks",
        """SELECT
            CONCAT(DATE_FORMAT(check_time, '%Y-%m-%d %H:%i:%s'), ' (ICT)') AS 'Time (Bangkok)',
            endpoint AS 'Endpoint',
            status AS 'Status',
            http_code AS 'HTTP Code',
            latency_ms AS 'Latency (ms)',
            body_valid AS 'Body Valid',
            error_msg AS 'Error'
        FROM webhook_health_checks
        ORDER BY check_time DESC
        LIMIT 14""",
        x=0, y=56, w=24, h=6,
    ))

    return {
        "uid": "pipeline-health",
        "title": "Pipeline Health",
        "panels": panels,
        "time": {"from": "now-24h", "to": "now"},
        "refresh": "5m",
        "schemaVersion": 39,
        "templating": {"list": _env_template_variables()},
    }


# ---------------------------------------------------------------------------
# Dashboard 2: Strategy Performance
# ---------------------------------------------------------------------------
def build_strategy_performance_dashboard():
    _reset_panel_id()
    panels = []

    # Row: Overview
    panels.append(row_panel("Strategy Comparison", 0))
    panels.append(barchart_panel(
        "Buy vs Sell Return by Strategy",
        """SELECT
            strategy_name AS strategy,
            buy_total_return_pct AS 'Buy Return %',
            sell_total_return_pct AS 'Sell Return %'
        FROM backtest_results
        WHERE symbol = '$ticker'
            AND strategy_name != '_consensus'
            AND backtest_date = (SELECT MAX(backtest_date) FROM backtest_results WHERE symbol = '$ticker')
        ORDER BY strategy_name""",
        x=0, y=1, w=12, h=8,
    ))
    panels.append(barchart_panel(
        "Sharpe Ratio by Strategy",
        """SELECT
            strategy_name AS strategy,
            buy_sharpe_ratio AS 'Buy Sharpe',
            sell_sharpe_ratio AS 'Sell Sharpe'
        FROM backtest_results
        WHERE symbol = '$ticker'
            AND strategy_name != '_consensus'
            AND backtest_date = (SELECT MAX(backtest_date) FROM backtest_results WHERE symbol = '$ticker')
        ORDER BY strategy_name""",
        x=12, y=1, w=12, h=8,
    ))

    # Row: Win Rate Gauges
    panels.append(row_panel("Win Rates", 9))
    strategies = ["sma_crossover", "rsi_threshold", "macd_crossover", "bollinger_band"]
    for i, strat in enumerate(strategies):
        panels.append(gauge_panel(
            f"{strat} Buy Win Rate",
            f"""SELECT buy_win_rate AS value
            FROM backtest_results
            WHERE symbol = '$ticker' AND strategy_name = '{strat}'
                AND backtest_date = (SELECT MAX(backtest_date) FROM backtest_results WHERE symbol = '$ticker')""",
            x=i * 6, y=10, w=6, h=5,
        ))

    # Row: Time series
    panels.append(row_panel("Performance Over Time", 15))
    panels.append(timeseries_panel(
        "Buy Return Over Time",
        """SELECT
            backtest_date AS time,
            strategy_name AS metric,
            buy_total_return_pct AS value
        FROM backtest_results
        WHERE symbol = '$ticker'
            AND strategy_name != '_consensus'
            AND $__timeFilter(backtest_date)
        ORDER BY backtest_date""",
        x=0, y=16, w=12, h=8, unit="percent",
    ))
    panels.append(timeseries_panel(
        "Sell Return Over Time",
        """SELECT
            backtest_date AS time,
            strategy_name AS metric,
            sell_total_return_pct AS value
        FROM backtest_results
        WHERE symbol = '$ticker'
            AND strategy_name != '_consensus'
            AND $__timeFilter(backtest_date)
        ORDER BY backtest_date""",
        x=12, y=16, w=12, h=8, unit="percent",
    ))

    # Row: Full metrics table
    panels.append(row_panel("Detailed Metrics", 24))
    panels.append(table_panel(
        "All Strategy Metrics",
        """SELECT
            strategy_name AS Strategy,
            buy_total_return_pct AS 'Buy Return %',
            buy_sharpe_ratio AS 'Buy Sharpe',
            buy_win_rate AS 'Buy Win %',
            buy_max_drawdown_pct AS 'Buy Drawdown %',
            buy_num_signals AS 'Buy Signals',
            buy_profit_factor AS 'Buy PF',
            sell_total_return_pct AS 'Sell Return %',
            sell_sharpe_ratio AS 'Sell Sharpe',
            sell_win_rate AS 'Sell Win %',
            sell_max_drawdown_pct AS 'Sell Drawdown %',
            sell_num_signals AS 'Sell Signals',
            sell_profit_factor AS 'Sell PF'
        FROM backtest_results
        WHERE symbol = '$ticker'
            AND strategy_name != '_consensus'
            AND backtest_date = (SELECT MAX(backtest_date) FROM backtest_results WHERE symbol = '$ticker')
        ORDER BY strategy_name""",
        x=0, y=25, w=24, h=6,
    ))

    # Template variable: ticker selector (uses datasource template var)
    ticker_var = {
        "name": "ticker",
        "type": "query",
        "datasource": MYSQL_DS,
        "query": "SELECT DISTINCT symbol FROM backtest_results WHERE strategy_name != '_consensus' ORDER BY symbol",
        "current": {"text": "DBS19", "value": "DBS19"},
        "refresh": 1,
        "sort": 1,
    }

    return {
        "uid": "strategy-perf",
        "title": "Strategy Performance",
        "panels": panels,
        "time": {"from": "now-90d", "to": "now"},
        "refresh": "",
        "schemaVersion": 39,
        "templating": {"list": _env_template_variables(extra_vars=[ticker_var])},
    }


# ---------------------------------------------------------------------------
# Dashboard 3: User Analytics
# ---------------------------------------------------------------------------
def build_user_analytics_dashboard():
    _reset_panel_id()
    panels = []

    # Row: Overview stats
    panels.append(row_panel("Overview", 0))
    panels.append(stat_panel(
        "Total Users",
        "SELECT COUNT(*) AS value FROM users",
        x=0, y=1, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Requests Today",
        "SELECT COUNT(*) AS value FROM user_requests WHERE DATE(requested_at) = CURDATE()",
        x=6, y=1, w=6, h=4,
    ))
    panels.append(gauge_panel(
        "Cache Hit Rate",
        """SELECT
            ROUND(SUM(CASE WHEN result = 'cache_hit' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS value
        FROM user_requests
        WHERE requested_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)""",
        x=12, y=1, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Avg Response Time",
        """SELECT ROUND(AVG(duration_ms)) AS value
        FROM user_requests
        WHERE requested_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)""",
        x=18, y=1, w=6, h=4, unit="ms",
    ))

    # Row: Trends
    panels.append(row_panel("Trends", 5))
    panels.append(timeseries_panel(
        "Requests Over Time",
        """SELECT
            DATE(requested_at) AS time,
            COUNT(*) AS requests
        FROM user_requests
        WHERE $__timeFilter(requested_at)
        GROUP BY DATE(requested_at)
        ORDER BY time""",
        x=0, y=6, w=12, h=8,
    ))
    panels.append(piechart_panel(
        "Platform Split",
        """SELECT
            platform AS metric,
            COUNT(*) AS value
        FROM users
        GROUP BY platform""",
        x=12, y=6, w=12, h=8,
    ))

    # Row: Top tickers and result breakdown
    panels.append(row_panel("Usage Breakdown", 14))
    panels.append(barchart_panel(
        "Top 10 Requested Tickers",
        """SELECT
            ticker,
            COUNT(*) AS requests
        FROM user_requests
        WHERE requested_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY ticker
        ORDER BY requests DESC
        LIMIT 10""",
        x=0, y=15, w=12, h=8,
    ))
    panels.append(piechart_panel(
        "Result Distribution",
        """SELECT
            result AS metric,
            COUNT(*) AS value
        FROM user_requests
        WHERE requested_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY result""",
        x=12, y=15, w=12, h=8,
    ))

    # Row: Recent activity
    panels.append(row_panel("Recent Activity", 23))
    panels.append(table_panel(
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
    ))

    return {
        "uid": "user-analytics",
        "title": "User Analytics",
        "panels": panels,
        "time": {"from": "now-7d", "to": "now"},
        "refresh": "5m",
        "schemaVersion": 39,
        "templating": {"list": _env_template_variables()},
    }


# ---------------------------------------------------------------------------
# Dashboard 4: Data Freshness
# ---------------------------------------------------------------------------
def build_data_freshness_dashboard():
    _reset_panel_id()
    panels = []

    # === Layer 1: How Stale? ===
    panels.append(row_panel("Layer 1: How Stale?", 0))
    panels.append(stat_panel(
        "Prices Lag (days)",
        "SELECT DATEDIFF(CURDATE(), MAX(price_date)) AS value FROM daily_prices",
        x=0, y=1, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 2},
        ],
    ))
    panels.append(stat_panel(
        "Indicators Lag (days)",
        "SELECT DATEDIFF(CURDATE(), MAX(indicator_date)) AS value FROM daily_indicators",
        x=6, y=1, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 2},
        ],
    ))
    panels.append(stat_panel(
        "Reports Lag (days)",
        "SELECT DATEDIFF(CURDATE(), MAX(report_date)) AS value FROM precomputed_reports WHERE status = 'completed'",
        x=12, y=1, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 2},
        ],
    ))
    panels.append(stat_panel(
        "Backtests Lag (days)",
        "SELECT DATEDIFF(CURDATE(), MAX(backtest_date)) AS value FROM backtest_results",
        x=18, y=1, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 2},
        ],
    ))

    # === Layer 2: How Complete? ===
    panels.append(row_panel("Layer 2: How Complete?", 5))
    coverage_thresholds = [
        {"color": "red", "value": None},
        {"color": "yellow", "value": 50},
        {"color": "green", "value": 80},
    ]
    panels.append(stat_panel(
        "Price Coverage Today",
        """SELECT ROUND(
            COUNT(DISTINCT symbol) * 100.0 /
            (SELECT COUNT(*) FROM ticker_master WHERE is_active = 1), 1
        ) AS value
        FROM daily_prices
        WHERE price_date = (SELECT MAX(price_date) FROM daily_prices)""",
        x=0, y=6, w=6, h=4, unit="percent",
        thresholds=coverage_thresholds,
    ))
    panels.append(stat_panel(
        "Indicator Coverage Today",
        """SELECT ROUND(
            COUNT(DISTINCT symbol) * 100.0 /
            (SELECT COUNT(*) FROM ticker_master WHERE is_active = 1), 1
        ) AS value
        FROM daily_indicators
        WHERE indicator_date = (SELECT MAX(indicator_date) FROM daily_indicators)""",
        x=6, y=6, w=6, h=4, unit="percent",
        thresholds=coverage_thresholds,
    ))
    panels.append(stat_panel(
        "Report Coverage Today",
        """SELECT ROUND(
            COUNT(DISTINCT symbol) * 100.0 /
            (SELECT COUNT(*) FROM ticker_master WHERE is_active = 1), 1
        ) AS value
        FROM precomputed_reports
        WHERE report_date = (SELECT MAX(report_date) FROM precomputed_reports WHERE status = 'completed')
          AND status = 'completed'""",
        x=12, y=6, w=6, h=4, unit="percent",
        thresholds=coverage_thresholds,
    ))
    panels.append(stat_panel(
        "Backtest Coverage Today",
        """SELECT ROUND(
            COUNT(DISTINCT symbol) * 100.0 /
            (SELECT COUNT(*) FROM ticker_master WHERE is_active = 1), 1
        ) AS value
        FROM backtest_results
        WHERE backtest_date = (SELECT MAX(backtest_date) FROM backtest_results)
          AND strategy_name != '_consensus'""",
        x=18, y=6, w=6, h=4, unit="percent",
        thresholds=coverage_thresholds,
    ))
    panels.append(timeseries_panel(
        "Price Coverage Over Time",
        """SELECT price_date AS time, 'coverage' AS metric,
            COUNT(DISTINCT symbol) AS value
        FROM daily_prices
        WHERE $__timeFilter(price_date)
        GROUP BY price_date
        ORDER BY price_date""",
        x=0, y=10, w=12, h=8,
    ))
    panels.append(timeseries_panel(
        "Report Coverage Over Time",
        """SELECT report_date AS time, 'completed' AS metric,
            COUNT(DISTINCT symbol) AS value
        FROM precomputed_reports
        WHERE status = 'completed' AND $__timeFilter(report_date)
        GROUP BY report_date
        ORDER BY report_date""",
        x=12, y=10, w=12, h=8,
    ))

    # === Layer 3: How Much? ===
    panels.append(row_panel("Layer 3: How Much?", 18))
    panels.append(stat_panel(
        "Prices Today",
        """SELECT COUNT(*) AS value FROM daily_prices
        WHERE price_date = (SELECT MAX(price_date) FROM daily_prices)""",
        x=0, y=19, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Indicators Today",
        """SELECT COUNT(*) AS value FROM daily_indicators
        WHERE indicator_date = (SELECT MAX(indicator_date) FROM daily_indicators)""",
        x=6, y=19, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Reports Today",
        """SELECT COUNT(*) AS value FROM precomputed_reports
        WHERE report_date = (SELECT MAX(report_date) FROM precomputed_reports)""",
        x=12, y=19, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Backtests Today",
        """SELECT COUNT(*) AS value FROM backtest_results
        WHERE backtest_date = (SELECT MAX(backtest_date) FROM backtest_results)
          AND strategy_name != '_consensus'""",
        x=18, y=19, w=6, h=4,
    ))
    panels.append(timeseries_panel(
        "Daily Price Records Trend",
        """SELECT price_date AS time, 'records' AS metric,
            COUNT(*) AS value
        FROM daily_prices
        WHERE $__timeFilter(price_date)
        GROUP BY price_date
        ORDER BY price_date""",
        x=0, y=23, w=12, h=8,
    ))
    panels.append(timeseries_panel(
        "Daily Report Records by Status",
        """SELECT report_date AS time, status AS metric,
            COUNT(*) AS value
        FROM precomputed_reports
        WHERE $__timeFilter(report_date)
        GROUP BY report_date, status
        ORDER BY report_date""",
        x=12, y=23, w=12, h=8,
    ))

    # === Layer 4: When Did It Land? ===
    panels.append(row_panel("Layer 4: When Did It Land?", 31))
    panels.append(timeseries_panel(
        "Price Ingestion Lag",
        """SELECT price_date AS time, 'avg_lag_hours' AS metric,
            ROUND(AVG(TIMESTAMPDIFF(HOUR, price_date, fetched_at)), 1) AS value
        FROM daily_prices
        WHERE $__timeFilter(price_date)
        GROUP BY price_date
        ORDER BY price_date""",
        x=0, y=32, w=12, h=8, unit="h",
    ))
    panels.append(timeseries_panel(
        "Report Computation Lag",
        """SELECT report_date AS time, 'avg_lag_hours' AS metric,
            ROUND(AVG(TIMESTAMPDIFF(HOUR, report_date, computed_at)), 1) AS value
        FROM precomputed_reports
        WHERE status = 'completed' AND $__timeFilter(report_date)
        GROUP BY report_date
        ORDER BY report_date""",
        x=12, y=32, w=12, h=8, unit="h",
    ))

    # === Layer 5: What's Broken? ===
    panels.append(row_panel("Layer 5: What's Broken?", 40))
    panels.append(stat_panel(
        "Failed Reports (latest date)",
        """SELECT COUNT(*) AS value FROM precomputed_reports
        WHERE report_date = (SELECT MAX(report_date) FROM precomputed_reports)
          AND status = 'failed'""",
        x=0, y=41, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 3},
        ],
    ))
    panels.append(stat_panel(
        "Pending Reports (latest date)",
        """SELECT COUNT(*) AS value FROM precomputed_reports
        WHERE report_date = (SELECT MAX(report_date) FROM precomputed_reports)
          AND status = 'pending'""",
        x=6, y=41, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 3},
        ],
    ))
    panels.append(stat_panel(
        "Missing Price Tickers",
        """SELECT COUNT(*) AS value
        FROM ticker_master m
        JOIN ticker_aliases a ON m.id = a.ticker_id AND a.symbol_type = 'dr'
        LEFT JOIN daily_prices dp ON a.symbol = dp.symbol
          AND dp.price_date = (SELECT MAX(price_date) FROM daily_prices)
        WHERE m.is_active = 1 AND dp.id IS NULL""",
        x=12, y=41, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 3},
        ],
    ))
    panels.append(stat_panel(
        "Missing Report Tickers",
        """SELECT COUNT(*) AS value
        FROM ticker_master m
        JOIN ticker_aliases a ON m.id = a.ticker_id AND a.symbol_type = 'dr'
        LEFT JOIN precomputed_reports pr ON a.symbol = pr.symbol
          AND pr.report_date = (SELECT MAX(report_date) FROM precomputed_reports WHERE status = 'completed')
          AND pr.status = 'completed'
        WHERE m.is_active = 1 AND pr.id IS NULL""",
        x=18, y=41, w=6, h=4,
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 1},
            {"color": "red", "value": 3},
        ],
    ))
    panels.append(table_panel(
        "Failed Reports Detail (7d)",
        """SELECT
            pr.symbol AS Symbol,
            pr.report_date AS Date,
            pr.status AS Status,
            pr.error_message AS Error,
            CONCAT(ROUND(pr.generation_time_seconds, 1), 's') AS GenTime
        FROM precomputed_reports pr
        WHERE pr.status = 'failed'
          AND pr.report_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ORDER BY pr.report_date DESC, pr.symbol""",
        x=0, y=45, w=24, h=8,
    ))
    panels.append(table_panel(
        "Missing Tickers Detail",
        """SELECT
            m.company_name AS Company,
            a.symbol AS Symbol,
            CASE WHEN dp.id IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasPrices,
            CASE WHEN di.id IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasIndicators,
            CASE WHEN pr.id IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasReport,
            CASE WHEN bt.id IS NOT NULL THEN 'Yes' ELSE 'No' END AS HasBacktest
        FROM ticker_master m
        JOIN ticker_aliases a ON m.id = a.ticker_id AND a.symbol_type = 'dr'
        LEFT JOIN daily_prices dp ON a.symbol = dp.symbol
          AND dp.price_date = (SELECT MAX(price_date) FROM daily_prices)
        LEFT JOIN daily_indicators di ON a.symbol = di.symbol
          AND di.indicator_date = (SELECT MAX(indicator_date) FROM daily_indicators)
        LEFT JOIN precomputed_reports pr ON a.symbol = pr.symbol
          AND pr.report_date = (SELECT MAX(report_date) FROM precomputed_reports WHERE status = 'completed')
          AND pr.status = 'completed'
        LEFT JOIN backtest_results bt ON a.symbol = bt.symbol
          AND bt.backtest_date = (SELECT MAX(backtest_date) FROM backtest_results)
          AND bt.strategy_name != '_consensus'
        WHERE m.is_active = 1
          AND (dp.id IS NULL OR di.id IS NULL OR pr.id IS NULL OR bt.id IS NULL)
        ORDER BY m.company_name""",
        x=0, y=53, w=24, h=8,
    ))

    return {
        "uid": "data-freshness",
        "title": "Data Freshness",
        "panels": panels,
        "time": {"from": "now-14d", "to": "now"},
        "refresh": "5m",
        "schemaVersion": 39,
        "templating": {"list": _env_template_variables()},
    }


# ---------------------------------------------------------------------------
# Dashboard 5: Daily Ticker Coverage
# ---------------------------------------------------------------------------
def build_daily_ticker_coverage_dashboard():
    """Visual-first 'did the scheduled precompute produce all tickers today?' view.

    Sister to Dashboard 4 (Data Freshness): same underlying tables but framed
    as 'show me the days and the missing tickers' rather than '5-layer pipeline
    health'. Three panels stacked: calendar row, daily bar, per-ticker table.
    """
    _reset_panel_id()
    panels = []

    # === Calendar row: tickers cached per day ===
    panels.append(row_panel("Coverage Calendar", 0))
    panels.append(state_timeline_panel(
        "Tickers Generated per Day",
        """SELECT
            pr.report_date AS time,
            'tickers' AS metric,
            COUNT(DISTINCT pr.symbol) AS value
        FROM precomputed_reports pr
        WHERE pr.status = 'completed'
          AND $__timeFilter(pr.report_date)
        GROUP BY pr.report_date
        ORDER BY pr.report_date""",
        x=0, y=1, w=24, h=4,
        thresholds=[
            {"color": "red", "value": None},
            {"color": "yellow", "value": 30},
            {"color": "green", "value": 45},
        ],
        data_links=[{
            "title": "View this day's per-ticker status",
            "url": "/d/daily-ticker-coverage/daily-ticker-coverage"
                   "?var-selected_date=${__value.time:date:YYYY-MM-DD}"
                   "&${__url_time_range}",
        }],
    ))

    # === Daily count bar chart ===
    # Two-series trick to highlight the selected day in red:
    #   - `tickers`: count for every day (default color)
    #   - `selected`: same count, but ONLY on the selected day (NULL elsewhere)
    # Field override paints `selected` red — visually it appears as a
    # red twin-bar next to the default bar on the chosen day.
    # The COALESCE expression must stay in lock-step with Panel 6's table SQL
    # so the bar and the table never disagree about which day is "selected".
    panels.append(row_panel("Daily Count", 5))
    panels.append(barchart_panel(
        "Tickers Cached per Day",
        """SELECT
            DATE_FORMAT(pr.report_date, '%m-%d') AS day,
            COUNT(DISTINCT pr.symbol) AS tickers,
            CASE WHEN pr.report_date = COALESCE(
                NULLIF('$selected_date', ''),
                (SELECT MAX(report_date) FROM precomputed_reports WHERE status = 'completed')
            )
            THEN COUNT(DISTINCT pr.symbol)
            ELSE NULL END AS selected
        FROM precomputed_reports pr
        WHERE pr.status = 'completed'
          AND $__timeFilter(pr.report_date)
        GROUP BY pr.report_date
        ORDER BY pr.report_date""",
        x=0, y=6, w=24, h=8,
        orientation="horizontal",
        overrides=[
            {
                "matcher": {"id": "byName", "options": "selected"},
                "properties": [
                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "red"}},
                    {"id": "displayName", "value": "Selected day"},
                ],
            },
            {
                "matcher": {"id": "byName", "options": "tickers"},
                "properties": [
                    {"id": "displayName", "value": "Tickers cached"},
                ],
            },
        ],
    ))

    # === Per-ticker status table for the latest completed day ===
    panels.append(row_panel("Per-Ticker Status (latest completed day)", 14))
    panels.append(table_panel(
        "Coverage by Country / Exchange / Ticker",
        """SELECT
            CASE
                WHEN tm.exchange IN ('NASDAQ', 'NYSE', 'AMEX') THEN 'US'
                WHEN tm.exchange IN ('SET', 'MAI') THEN 'Thailand'
                WHEN tm.exchange IN ('HKEX', 'HKG') THEN 'Hong Kong'
                WHEN tm.exchange = 'SGX' THEN 'Singapore'
                WHEN tm.exchange IN ('TSE', 'OSE') THEN 'Japan'
                WHEN tm.exchange IN ('HOSE', 'HNX') THEN 'Vietnam'
                WHEN tm.exchange = 'TWSE' THEN 'Taiwan'
                WHEN tm.exchange = 'KRX' THEN 'Korea'
                WHEN tm.exchange = 'BSE' THEN 'India'
                ELSE 'Other'
            END AS Country,
            COALESCE(tm.exchange, 'Unknown') AS Exchange,
            ta.symbol AS Ticker,
            tm.company_name AS Company,
            CASE WHEN pr.id IS NOT NULL THEN 'cached' ELSE 'missing' END AS Status,
            pr.computed_at AS LastGenerated
        FROM ticker_master tm
        JOIN ticker_aliases ta ON tm.id = ta.ticker_id AND ta.symbol_type = 'yahoo'
        LEFT JOIN precomputed_reports pr
            ON ta.symbol = pr.symbol
            AND pr.report_date = COALESCE(
                NULLIF('$selected_date', ''),
                (SELECT MAX(report_date) FROM precomputed_reports WHERE status = 'completed')
            )
            AND pr.status = 'completed'
        WHERE tm.is_active = 1
        ORDER BY Country, Exchange, ta.symbol""",
        x=0, y=15, w=24, h=16,
        overrides=[{
            "matcher": {"id": "byName", "options": "Status"},
            "properties": [
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "color-background", "mode": "basic"},
                },
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "cached":  {"color": "green", "index": 0},
                                "missing": {"color": "red",   "index": 1},
                            },
                        },
                    ],
                },
            ],
        }],
    ))

    # Hidden state slot — written by clicking a calendar cell (data link),
    # read by the per-ticker table SQL via COALESCE(NULLIF, MAX). Empty string
    # on first load → table falls back to latest completed report_date.
    selected_date_var = {
        "name": "selected_date",
        "type": "textbox",
        "current": {"text": "", "value": ""},
        "label": "Selected Date",
        "hide": 2,  # hide variable + label entirely from the dashboard bar
    }

    return {
        "uid": "daily-ticker-coverage",
        "title": "Daily Ticker Coverage",
        "panels": panels,
        "time": {"from": "now-30d", "to": "now"},
        "refresh": "5m",
        "schemaVersion": 39,
        "templating": {"list": _env_template_variables(extra_vars=[selected_date_var])},
    }


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def push_dashboard(dashboard_def):
    """Push a dashboard to Grafana. Returns the dashboard URL."""
    payload = {
        "dashboard": dashboard_def,
        "overwrite": True,
        "message": "Auto-generated by build-grafana-dashboards.py",
    }
    resp = requests.post(
        f"{ENDPOINT}/api/dashboards/db",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ERROR pushing dashboard: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    url = f"{ENDPOINT}{data.get('url', '')}"
    return url


def create_snapshot(dashboard_uid):
    """Create a public snapshot of a dashboard. Returns the snapshot URL."""
    # Fetch the full dashboard
    resp = requests.get(
        f"{ENDPOINT}/api/dashboards/uid/{dashboard_uid}",
        headers=HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  ERROR fetching dashboard for snapshot: {resp.status_code}")
        return None

    dashboard = resp.json()["dashboard"]

    # Create snapshot (expires in 24 hours)
    resp = requests.post(
        f"{ENDPOINT}/api/snapshots",
        headers=HEADERS,
        json={
            "dashboard": dashboard,
            "name": dashboard.get("title", "Snapshot"),
            "expires": 86400,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  ERROR creating snapshot: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    return data.get("url")


# ---------------------------------------------------------------------------
# Auth: self-provision a short-lived Grafana Service Account Token via boto3
# ---------------------------------------------------------------------------
SERVICE_ACCOUNT_NAME = "dashboard-deployer"


def _get_or_create_service_account(client):
    """Find existing service account or create one. Returns service account ID."""
    paginator = client.get_paginator("list_workspace_service_accounts")
    for page in paginator.paginate(workspaceId=WORKSPACE_ID):
        for sa in page["serviceAccounts"]:
            if sa["name"] == SERVICE_ACCOUNT_NAME:
                return sa["id"]

    resp = client.create_workspace_service_account(
        name=SERVICE_ACCOUNT_NAME,
        grafanaRole="ADMIN",
        workspaceId=WORKSPACE_ID,
    )
    print(f"Created service account: {SERVICE_ACCOUNT_NAME}")
    return resp["id"]


def _provision_token(client, sa_id):
    """Create a short-lived token (5 min) for this run. Returns token key."""
    resp = client.create_workspace_service_account_token(
        name="ephemeral-deploy",
        secondsToLive=300,  # 5 minutes — just enough for this run
        serviceAccountId=sa_id,
        workspaceId=WORKSPACE_ID,
    )
    return resp["serviceAccountToken"]["key"]


def _cleanup_stale_tokens(client, sa_id):
    """Delete old ephemeral tokens to avoid accumulation."""
    paginator = client.get_paginator("list_workspace_service_account_tokens")
    for page in paginator.paginate(serviceAccountId=sa_id, workspaceId=WORKSPACE_ID):
        for token in page["serviceAccountTokens"]:
            if token["name"] == "ephemeral-deploy":
                client.delete_workspace_service_account_token(
                    serviceAccountId=sa_id,
                    tokenId=token["id"],
                    workspaceId=WORKSPACE_ID,
                )


def get_grafana_token():
    """Self-provision a short-lived Grafana token using AWS IAM credentials."""
    client = boto3.client("grafana", region_name=REGION)
    sa_id = _get_or_create_service_account(client)
    _cleanup_stale_tokens(client, sa_id)
    token = _provision_token(client, sa_id)
    return token


# ---------------------------------------------------------------------------
# Datasource helpers
# ---------------------------------------------------------------------------
def rename_datasource_if_needed(old_uid, new_name):
    """Rename a datasource to follow mysql-{env} convention if not already named."""
    resp = requests.get(
        f"{ENDPOINT}/api/datasources/uid/{old_uid}",
        headers=HEADERS,
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  Datasource uid={old_uid} not found ({resp.status_code}), skipping rename")
        return

    ds = resp.json()
    if ds["name"] == new_name:
        print(f"  Datasource '{new_name}' already correctly named")
        return

    old_name = ds["name"]
    ds["name"] = new_name
    resp = requests.put(
        f"{ENDPOINT}/api/datasources/{ds['id']}",
        headers=HEADERS,
        json=ds,
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  ERROR renaming datasource: {resp.status_code} {resp.text}")
    else:
        print(f"  Renamed datasource '{old_name}' → '{new_name}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
# Known datasource UIDs (from original hardcoded config)
MYSQL_DS_UID = "bfg0lw3z4zqbkf"


def main():
    global HEADERS

    print("Provisioning Grafana API token via AWS IAM...")
    token = get_grafana_token()

    HEADERS = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Verify API access
    resp = requests.get(f"{ENDPOINT}/api/org", headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        print(f"ERROR: Cannot connect to Grafana API: {resp.status_code}")
        sys.exit(1)
    print(f"Connected to Grafana: {resp.json().get('name', 'unknown')}")
    print(f"Endpoint: {ENDPOINT}")
    print()

    # Rename MySQL datasource to mysql-{env} convention
    print("Checking datasource naming...")
    rename_datasource_if_needed(MYSQL_DS_UID, DEFAULT_MYSQL_DS)
    print()

    builders = [
        build_pipeline_health_dashboard,
        build_strategy_performance_dashboard,
        build_user_analytics_dashboard,
        build_data_freshness_dashboard,
        build_daily_ticker_coverage_dashboard,
    ]

    results = []
    for builder in builders:
        dashboard = builder()
        title = dashboard["title"]
        uid = dashboard["uid"]
        print(f"Building: {title}...")

        url = push_dashboard(dashboard)
        if url:
            print(f"  Dashboard: {url}")
        else:
            print(f"  FAILED to push dashboard")
            continue

        snapshot_url = create_snapshot(uid)
        if snapshot_url:
            print(f"  Snapshot:  {snapshot_url}")
        else:
            print(f"  FAILED to create snapshot")

        results.append({"title": title, "url": url, "snapshot": snapshot_url})
        print()

    # Summary
    print("=" * 60)
    print("DASHBOARD SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"\n{r['title']}:")
        print(f"  Dashboard: {r['url']}")
        if r.get("snapshot"):
            print(f"  Snapshot:  {r['snapshot']}  (public, no login, 24h expiry)")
    print()


if __name__ == "__main__":
    main()
