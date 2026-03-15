#!/usr/bin/env python3
"""Build Grafana dashboards via API and create public snapshots.

Usage:
    export GRAFANA_API_KEY="eyJr..."
    python scripts/build-grafana-dashboards.py

Creates 3 dashboards:
    1. Pipeline Health (CloudWatch + MySQL)
    2. Strategy Performance (MySQL)
    3. User Analytics (MySQL)

Each dashboard gets a public snapshot URL viewable without login.
"""

import json
import os
import sys

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENDPOINT = "https://g-4df4c51648.grafana-workspace.ap-southeast-1.amazonaws.com"
API_KEY = os.environ.get("GRAFANA_API_KEY", "")
MYSQL_DS = {"uid": "bfg0lw3z4zqbkf", "type": "mysql"}
CW_DS = {"uid": "cfg0lw8bf6fpce", "type": "cloudwatch"}

HEADERS = {}

# Lambda function names (for CloudWatch queries)
LAMBDA_FUNCTIONS = [
    "dr-daily-report-telegram-api-dev",
    "dr-daily-report-report-worker-dev",
    "dr-daily-report-ticker-scheduler-dev",
    "dr-daily-report-backtest-precompute-dev",
    "dr-daily-report-pattern-precompute-dev",
    "dr-daily-report-webhook-health-dev",
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


def table_panel(title, sql, x, y, w=24, h=8):
    """Create a table panel with MySQL query."""
    return {
        "id": _panel_id(),
        "type": "table",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"showHeader": True, "sortBy": []},
    }


def barchart_panel(title, sql, x, y, w=12, h=8):
    """Create a bar chart panel with MySQL query."""
    return {
        "id": _panel_id(),
        "type": "barchart",
        "title": title,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "datasource": MYSQL_DS,
        "targets": [{"rawSql": sql, "format": "table", "refId": "A"}],
        "fieldConfig": {"defaults": {}, "overrides": []},
        "options": {"orientation": "horizontal", "showValue": "always", "barWidth": 0.7},
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
                "label": dim_val.replace("dr-daily-report-", "").replace("-dev", ""),
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


def row_panel(title, y):
    """Create a row (section header) panel."""
    return {
        "id": _panel_id(),
        "type": "row",
        "title": title,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "collapsed": False,
    }


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
    lambda_dims = [("FunctionName", fn) for fn in LAMBDA_FUNCTIONS]
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

    # Row: Database Metrics
    panels.append(row_panel("Database Row Counts", 23))
    panels.append(stat_panel(
        "Price Records",
        "SELECT COUNT(*) AS value FROM daily_prices",
        x=0, y=24, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Indicator Records",
        "SELECT COUNT(*) AS value FROM daily_indicators",
        x=6, y=24, w=6, h=4,
    ))
    panels.append(stat_panel(
        "User Requests",
        "SELECT COUNT(*) AS value FROM user_requests",
        x=12, y=24, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Total Users",
        "SELECT COUNT(*) AS value FROM users",
        x=18, y=24, w=6, h=4,
    ))

    # Row: Webhook Health
    panels.append(row_panel("Webhook Health", 28))
    panels.append(stat_panel(
        "Webhook Status",
        "SELECT status AS value FROM webhook_health_checks WHERE endpoint='line_webhook' ORDER BY check_time DESC LIMIT 1",
        x=0, y=29, w=6, h=4,
        thresholds=[
            {"color": "red", "value": None},
        ],
    ))
    panels.append(gauge_panel(
        "Uptime % (30d)",
        "SELECT ROUND(SUM(status='healthy')*100.0/COUNT(*),1) AS value FROM webhook_health_checks WHERE check_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)",
        x=6, y=29, w=6, h=4,
    ))
    panels.append(stat_panel(
        "Avg Latency (7d)",
        "SELECT ROUND(AVG(latency_ms)) AS value FROM webhook_health_checks WHERE check_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        x=12, y=29, w=6, h=4, unit="ms",
    ))
    panels.append(stat_panel(
        "Last Check",
        "SELECT MAX(check_time) AS value FROM webhook_health_checks",
        x=18, y=29, w=6, h=4,
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
        x=0, y=33, w=12, h=8,
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
        x=12, y=33, w=12, h=8, unit="ms",
    ))
    panels.append(table_panel(
        "Recent Health Checks",
        """SELECT
            check_time AS 'Time',
            endpoint AS 'Endpoint',
            status AS 'Status',
            http_code AS 'HTTP Code',
            latency_ms AS 'Latency (ms)',
            body_valid AS 'Body Valid',
            error_msg AS 'Error'
        FROM webhook_health_checks
        ORDER BY check_time DESC
        LIMIT 14""",
        x=0, y=41, w=24, h=6,
    ))

    return {
        "uid": "pipeline-health",
        "title": "Pipeline Health",
        "panels": panels,
        "time": {"from": "now-24h", "to": "now"},
        "refresh": "5m",
        "schemaVersion": 39,
        "templating": {"list": []},
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

    # Template variable: ticker selector
    templating = {
        "list": [{
            "name": "ticker",
            "type": "query",
            "datasource": MYSQL_DS,
            "query": "SELECT DISTINCT symbol FROM backtest_results WHERE strategy_name != '_consensus' ORDER BY symbol",
            "current": {"text": "DBS19", "value": "DBS19"},
            "refresh": 1,
            "sort": 1,
        }]
    }

    return {
        "uid": "strategy-perf",
        "title": "Strategy Performance",
        "panels": panels,
        "time": {"from": "now-90d", "to": "now"},
        "refresh": "",
        "schemaVersion": 39,
        "templating": templating,
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
        "templating": {"list": []},
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
# Main
# ---------------------------------------------------------------------------
def main():
    global HEADERS

    api_key = API_KEY
    if not api_key:
        api_key = input("Enter Grafana API key: ").strip()
    if not api_key:
        print("ERROR: No API key provided. Set GRAFANA_API_KEY env var.")
        sys.exit(1)

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
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

    builders = [
        build_pipeline_health_dashboard,
        build_strategy_performance_dashboard,
        build_user_analytics_dashboard,
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
