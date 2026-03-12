"""Slack notifier Lambda handler for CloudWatch alarms via SNS.

This Lambda receives SNS notifications from CloudWatch alarms and forwards
formatted messages to a Slack channel via incoming webhook.

Environment Variables:
    SLACK_WEBHOOK_URL: Slack incoming webhook URL
    ENVIRONMENT: Environment name (dev, staging, prod)
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment configuration
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "unknown")


def get_severity_emoji(alarm_name: str) -> str:
    """Get emoji based on alarm severity."""
    if "scheduler" in alarm_name.lower() or "precompute" in alarm_name.lower():
        return ":rotating_light:"  # Critical - data pipeline
    elif "5xx" in alarm_name.lower():
        return ":x:"  # High - server errors
    elif "4xx" in alarm_name.lower():
        return ":warning:"  # Medium - client errors
    else:
        return ":bell:"  # Default


def get_severity_level(alarm_name: str) -> str:
    """Get severity level based on alarm name."""
    if "scheduler" in alarm_name.lower() or "precompute" in alarm_name.lower():
        return "CRITICAL"
    elif "5xx" in alarm_name.lower() or "errors" in alarm_name.lower():
        return "HIGH"
    elif "4xx" in alarm_name.lower() or "duration" in alarm_name.lower():
        return "MEDIUM"
    else:
        return "INFO"


def get_color(state: str) -> str:
    """Get Slack attachment color based on alarm state."""
    if state == "ALARM":
        return "danger"  # Red
    elif state == "OK":
        return "good"  # Green
    else:
        return "warning"  # Yellow


def format_slack_message(sns_message: dict[str, Any]) -> dict[str, Any]:
    """Format CloudWatch alarm message for Slack.

    Args:
        sns_message: Parsed SNS message containing CloudWatch alarm data

    Returns:
        Slack message payload with blocks and attachments
    """
    alarm_name = sns_message.get("AlarmName", "Unknown Alarm")
    new_state = sns_message.get("NewStateValue", "UNKNOWN")
    old_state = sns_message.get("OldStateValue", "UNKNOWN")
    reason = sns_message.get("NewStateReason", "No reason provided")
    timestamp = sns_message.get("StateChangeTime", datetime.utcnow().isoformat())
    region = sns_message.get("Region", "ap-southeast-1")

    # Extract metric details
    trigger = sns_message.get("Trigger", {})
    namespace = trigger.get("Namespace", "")
    metric_name = trigger.get("MetricName", "")
    dimensions = trigger.get("Dimensions", [])

    # Build dimension string
    dim_str = ", ".join(
        f"{d.get('name', 'unknown')}={d.get('value', 'unknown')}"
        for d in dimensions
    )

    emoji = get_severity_emoji(alarm_name)
    severity = get_severity_level(alarm_name)
    color = get_color(new_state)

    # CloudWatch console link
    console_link = (
        f"https://{region}.console.aws.amazon.com/cloudwatch/home?"
        f"region={region}#alarmsV2:alarm/{alarm_name}"
    )

    # Format state transition
    state_transition = f"{old_state} → {new_state}"

    # Build Slack message
    if new_state == "OK":
        title = f"{emoji} RESOLVED: {alarm_name}"
        pretext = f"Alarm resolved in *{ENVIRONMENT}* environment"
    else:
        title = f"{emoji} [{severity}] {alarm_name}"
        pretext = f"Alarm triggered in *{ENVIRONMENT}* environment"

    return {
        "attachments": [
            {
                "color": color,
                "pretext": pretext,
                "title": title,
                "title_link": console_link,
                "fields": [
                    {
                        "title": "State",
                        "value": state_transition,
                        "short": True
                    },
                    {
                        "title": "Environment",
                        "value": ENVIRONMENT.upper(),
                        "short": True
                    },
                    {
                        "title": "Metric",
                        "value": f"{namespace}/{metric_name}" if namespace else metric_name,
                        "short": True
                    },
                    {
                        "title": "Severity",
                        "value": severity,
                        "short": True
                    },
                    {
                        "title": "Reason",
                        "value": reason[:500] if len(reason) > 500 else reason,
                        "short": False
                    }
                ],
                "footer": f"CloudWatch Alarm | {dim_str}" if dim_str else "CloudWatch Alarm",
                "ts": int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp())
                if timestamp else int(datetime.utcnow().timestamp())
            }
        ]
    }


def send_to_slack(message: dict[str, Any]) -> bool:
    """Send message to Slack webhook.

    Args:
        message: Slack message payload

    Returns:
        True if successful, False otherwise
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured - skipping notification")
        return False

    try:
        data = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("Successfully sent alert to Slack")
                return True
            else:
                logger.error(f"Slack returned status {response.status}")
                return False

    except urllib.error.URLError as e:
        logger.error(f"Failed to send to Slack: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending to Slack: {e}")
        return False


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for SNS notifications from CloudWatch alarms.

    Args:
        event: Lambda event containing SNS records
        context: Lambda context

    Returns:
        Response indicating success/failure
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Validate webhook URL at startup (Principle #1: Defensive Programming)
    if not SLACK_WEBHOOK_URL:
        logger.error("SLACK_WEBHOOK_URL environment variable not set")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "SLACK_WEBHOOK_URL not configured"})
        }

    processed = 0
    errors = 0

    # Process SNS records
    for record in event.get("Records", []):
        try:
            sns_data = record.get("Sns", {})
            message_str = sns_data.get("Message", "{}")

            # Parse CloudWatch alarm message
            try:
                sns_message = json.loads(message_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse SNS message as JSON: {message_str[:200]}")
                # If not JSON, treat as plain text
                sns_message = {"AlarmName": "Unknown", "NewStateReason": message_str}

            # Format and send to Slack
            slack_message = format_slack_message(sns_message)

            if send_to_slack(slack_message):
                processed += 1
            else:
                errors += 1

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            errors += 1

    # Log summary (Principle #18: Logging Discipline)
    logger.info(f"Processed {processed} alerts, {errors} errors")

    return {
        "statusCode": 200 if errors == 0 else 207,
        "body": json.dumps({
            "processed": processed,
            "errors": errors
        })
    }
