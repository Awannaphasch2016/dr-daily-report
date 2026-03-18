"""OpenRouter credit balance checker Lambda handler.

Checks OpenRouter API credit balance against actual daily report cost
from Langfuse traces, pushes CloudWatch metrics, and sends Slack alert
if credits are insufficient for the next scheduled run.

Environment Variables:
    OPENROUTER_API_KEY: OpenRouter API key (required, sensitive)
    LANGFUSE_PUBLIC_KEY: Langfuse public key for trace cost queries (required)
    LANGFUSE_SECRET_KEY: Langfuse secret key for trace cost queries (required)
    LANGFUSE_HOST: Langfuse API host (default: https://cloud.langfuse.com)
    SLACK_WEBHOOK_URL: Slack incoming webhook URL (required)
    ENVIRONMENT: Environment name - dev, staging, prod (required)
    ESTIMATED_DAILY_COST: Fallback daily cost estimate in USD (default: 2.5)
    GRAFANA_DASHBOARD_URL: URL to Grafana Pipeline Health dashboard (optional)
    COST_MARGIN: Multiplier for threshold calculation (default: 1.5)

Triggered by: EventBridge Scheduler (every 6 hours)
"""

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")
ESTIMATED_DAILY_COST = float(os.environ.get("ESTIMATED_DAILY_COST", "2.5"))
GRAFANA_DASHBOARD_URL = os.environ.get("GRAFANA_DASHBOARD_URL", "")
COST_MARGIN = float(os.environ.get("COST_MARGIN", "1.5"))

OPENROUTER_TOPUP_URL = "https://openrouter.ai/settings/credits"
CW_NAMESPACE = "DR/OpenRouter"


def _validate_config():
    """Validate required configuration at startup (Principle #1: Defensive Programming)."""
    missing = []
    if not OPENROUTER_API_KEY:
        missing.append("OPENROUTER_API_KEY")
    if not SLACK_WEBHOOK_URL:
        missing.append("SLACK_WEBHOOK_URL")
    if not LANGFUSE_PUBLIC_KEY:
        missing.append("LANGFUSE_PUBLIC_KEY")
    if not LANGFUSE_SECRET_KEY:
        missing.append("LANGFUSE_SECRET_KEY")
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def _check_credit_balance(api_key: str) -> dict:
    """Check OpenRouter credit balance via API.

    Returns:
        Dict with keys: usage, limit, balance, label
    """
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/auth/key",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        key_data = data.get("data", {})
        usage = key_data.get("usage", 0.0)
        limit = key_data.get("limit", 0.0)
        balance = limit - usage if limit else usage * -1

        return {
            "usage": usage,
            "limit": limit,
            "balance": round(balance, 4),
            "label": key_data.get("label", "unknown"),
        }
    except urllib.error.HTTPError as e:
        logger.error(f"OpenRouter API error: HTTP {e.code}")
        raise
    except urllib.error.URLError as e:
        logger.error(f"OpenRouter API connection error: {e}")
        raise


def _get_actual_daily_cost() -> Optional[float]:
    """Get actual daily report cost from Langfuse traces.

    Queries Langfuse for precompute traces in the last 7 days,
    sums totalCost, and divides by number of days.

    Returns:
        Actual daily cost in USD, or None if Langfuse unavailable.
    """
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse credentials not configured, cannot query actual costs")
        return None

    try:
        now = datetime.now(timezone.utc)
        from_time = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Langfuse API uses Basic auth with public:secret
        credentials = base64.b64encode(
            f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
        ).decode()

        # Query traces with precompute tag
        url = (
            f"{LANGFUSE_HOST}/api/public/traces"
            f"?tags=precompute"
            f"&fromTimestamp={from_time}"
            f"&limit=500"
        )

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        traces = data.get("data", [])
        if not traces:
            logger.warning("No precompute traces found in last 7 days")
            return None

        # Sum costs from traces
        total_cost = 0.0
        trace_count = 0
        for trace in traces:
            cost = trace.get("totalCost")
            if cost is not None and cost > 0:
                total_cost += cost
                trace_count += 1

        if trace_count == 0:
            logger.warning("No traces with cost data found")
            return None

        # Calculate daily cost based on distinct days with traces
        trace_dates = set()
        for trace in traces:
            ts = trace.get("timestamp", "")
            if ts:
                trace_dates.add(ts[:10])  # Extract date part YYYY-MM-DD

        days = max(len(trace_dates), 1)
        daily_cost = round(total_cost / days, 4)

        logger.info(
            f"📊 Langfuse cost data: {trace_count} traces over {days} days, "
            f"total=${total_cost:.4f}, daily=${daily_cost:.4f}"
        )
        return daily_cost

    except urllib.error.HTTPError as e:
        logger.warning(f"Langfuse API error: HTTP {e.code} — falling back to estimate")
        return None
    except urllib.error.URLError as e:
        logger.warning(f"Langfuse API connection error: {e} — falling back to estimate")
        return None
    except Exception as e:
        logger.warning(f"Langfuse query failed: {e} — falling back to estimate")
        return None


def _push_cloudwatch_metrics(
    balance: float, daily_cost: float, days_remaining: float
):
    """Push credit metrics to CloudWatch for Grafana dashboards and backup alarms."""
    client = boto3.client("cloudwatch")

    client.put_metric_data(
        Namespace=CW_NAMESPACE,
        MetricData=[
            {
                "MetricName": "CreditBalance",
                "Value": balance,
                "Unit": "None",
                "Dimensions": [
                    {"Name": "Environment", "Value": ENVIRONMENT},
                ],
            },
            {
                "MetricName": "ActualDailyCost",
                "Value": daily_cost,
                "Unit": "None",
                "Dimensions": [
                    {"Name": "Environment", "Value": ENVIRONMENT},
                ],
            },
            {
                "MetricName": "DaysRemaining",
                "Value": days_remaining,
                "Unit": "Count",
                "Dimensions": [
                    {"Name": "Environment", "Value": ENVIRONMENT},
                ],
            },
        ],
    )
    logger.info(
        f"📈 Pushed CloudWatch metrics: balance=${balance:.2f}, "
        f"daily_cost=${daily_cost:.4f}, days_remaining={days_remaining:.1f}"
    )


def _format_credit_alert(
    balance: float,
    limit: float,
    daily_cost: float,
    days_remaining: float,
    cost_source: str,
) -> dict:
    """Format Slack alert message for low credit balance."""
    if days_remaining < 1:
        color = "danger"
        urgency = ":rotating_light: CRITICAL"
    else:
        color = "warning"
        urgency = ":warning: WARNING"

    fields = [
        {"title": "Balance", "value": f"${balance:.2f} / ${limit:.2f}", "short": True},
        {"title": "Environment", "value": ENVIRONMENT.upper(), "short": True},
        {"title": "Daily Report Cost", "value": f"${daily_cost:.4f}", "short": True},
        {"title": "Cost Source", "value": cost_source, "short": True},
        {
            "title": "Days Remaining",
            "value": f"~{days_remaining:.1f} days",
            "short": True,
        },
        {
            "title": "Margin",
            "value": f"{COST_MARGIN}x",
            "short": True,
        },
    ]

    actions_text = f":zap: *Action needed:*\n"
    actions_text += f"  • <{OPENROUTER_TOPUP_URL}|Top up OpenRouter credits>\n"
    if GRAFANA_DASHBOARD_URL:
        actions_text += f"  • <{GRAFANA_DASHBOARD_URL}|View Grafana dashboard>\n"

    return {
        "attachments": [
            {
                "color": color,
                "pretext": f"{urgency} OpenRouter Credit Alert — DR Daily Report ({ENVIRONMENT})",
                "fields": fields,
                "text": actions_text,
                "footer": f"Threshold: daily_cost (${daily_cost:.4f}) × {COST_MARGIN} = ${daily_cost * COST_MARGIN:.4f}",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ]
    }


def _send_slack_alert(message: dict) -> bool:
    """Send alert message to Slack webhook."""
    try:
        data = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("✅ Slack alert sent successfully")
                return True
            else:
                logger.error(f"Slack returned status {response.status}")
                return False

    except urllib.error.URLError as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Slack alert: {e}")
        return False


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for OpenRouter credit balance checking.

    Narrative flow (Principle #18):
    BEGIN → validate config → check balance → get actual cost
    → push metrics → evaluate threshold → alert if needed → END
    """
    logger.info(f"🔔 Credit check starting (env={ENVIRONMENT}, source={event.get('source', 'unknown')})")

    # Validate configuration
    try:
        _validate_config()
    except RuntimeError as e:
        logger.error(f"❌ Configuration error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    # Check OpenRouter credit balance
    try:
        credit_info = _check_credit_balance(OPENROUTER_API_KEY)
    except Exception as e:
        logger.error(f"❌ Failed to check OpenRouter balance: {e}")
        return {"statusCode": 502, "body": json.dumps({"error": f"OpenRouter API failed: {e}"})}

    balance = credit_info["balance"]
    limit = credit_info["limit"]
    logger.info(f"💰 OpenRouter balance: ${balance:.2f} / ${limit:.2f}")

    # Get actual daily cost from Langfuse (source of truth)
    actual_daily_cost = _get_actual_daily_cost()
    if actual_daily_cost is not None:
        daily_cost = actual_daily_cost
        cost_source = "Langfuse traces (7d)"
    else:
        daily_cost = ESTIMATED_DAILY_COST
        cost_source = f"Fallback estimate (${ESTIMATED_DAILY_COST})"
        logger.warning(f"⚠️ Using fallback estimate: ${daily_cost}")

    # Calculate days remaining
    days_remaining = balance / daily_cost if daily_cost > 0 else 999.0

    # Push CloudWatch metrics (always, regardless of alert)
    try:
        _push_cloudwatch_metrics(balance, daily_cost, days_remaining)
    except Exception as e:
        logger.warning(f"⚠️ CloudWatch metric push failed (non-blocking): {e}")

    # Evaluate threshold: can we afford the next run?
    threshold = daily_cost * COST_MARGIN
    alert_sent = False

    if balance < threshold:
        logger.warning(
            f"⚠️ Balance ${balance:.2f} < threshold ${threshold:.4f} "
            f"(daily_cost=${daily_cost:.4f} × {COST_MARGIN})"
        )
        message = _format_credit_alert(
            balance, limit, daily_cost, days_remaining, cost_source
        )
        alert_sent = _send_slack_alert(message)
    else:
        logger.info(
            f"✅ Balance ${balance:.2f} >= threshold ${threshold:.4f} — no alert needed"
        )

    # Summary (Principle #18: narrative end)
    logger.info(
        f"🏁 Credit check complete: balance=${balance:.2f}, "
        f"daily_cost=${daily_cost:.4f} ({cost_source}), "
        f"days_remaining={days_remaining:.1f}, alert_sent={alert_sent}"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "balance": balance,
            "limit": limit,
            "daily_cost": daily_cost,
            "cost_source": cost_source,
            "days_remaining": round(days_remaining, 1),
            "threshold": round(threshold, 4),
            "alert_sent": alert_sent,
        }),
    }
