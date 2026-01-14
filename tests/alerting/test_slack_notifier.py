"""Tests for Slack notifier Lambda handler.

Tests the SNS → Slack notification pipeline per alerting-invariants.md.
Follows Principle #10 (Testing Anti-Patterns): No external calls, deterministic data.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# Import functions under test
from src.alerting.slack_notifier import (
    get_severity_emoji,
    get_severity_level,
    get_color,
    format_slack_message,
    send_to_slack,
    lambda_handler,
)


class TestSeverityEmoji:
    """Tests for get_severity_emoji function.

    Invariant: Alarm names map to correct severity emojis per alerting-invariants.md.
    """

    def test_critical_scheduler_alarm_gets_rotating_light(self):
        """CRITICAL alarms (scheduler) get rotating_light emoji."""
        assert get_severity_emoji("dr-daily-report-scheduler-errors-dev") == ":rotating_light:"

    def test_critical_precompute_alarm_gets_rotating_light(self):
        """CRITICAL alarms (precompute) get rotating_light emoji."""
        assert get_severity_emoji("dr-daily-report-precompute-errors-dev") == ":rotating_light:"
        assert get_severity_emoji("precompute-workflow-failures") == ":rotating_light:"

    def test_5xx_alarm_gets_x_emoji(self):
        """5xx alarms get x emoji (HIGH severity)."""
        assert get_severity_emoji("api-5xx-errors") == ":x:"

    def test_4xx_alarm_gets_warning_emoji(self):
        """4xx alarms get warning emoji (MEDIUM severity)."""
        assert get_severity_emoji("api-4xx-errors") == ":warning:"

    def test_default_alarm_gets_bell_emoji(self):
        """Unknown alarms get default bell emoji."""
        assert get_severity_emoji("some-other-alarm") == ":bell:"


class TestSeverityLevel:
    """Tests for get_severity_level function.

    Invariant: Alarm names map to correct severity levels.
    """

    def test_scheduler_alarm_is_critical(self):
        """Scheduler alarms are CRITICAL severity."""
        assert get_severity_level("scheduler-errors") == "CRITICAL"

    def test_precompute_alarm_is_critical(self):
        """Precompute alarms are CRITICAL severity."""
        assert get_severity_level("precompute-errors") == "CRITICAL"

    def test_5xx_alarm_is_high(self):
        """5xx alarms are HIGH severity."""
        assert get_severity_level("api-5xx-errors") == "HIGH"

    def test_errors_alarm_is_high(self):
        """Generic errors alarms are HIGH severity."""
        assert get_severity_level("telegram-api-errors") == "HIGH"

    def test_4xx_alarm_is_medium(self):
        """4xx alarms are MEDIUM severity (when not containing 'errors')."""
        # Note: "api-4xx-errors" contains "errors" which triggers HIGH
        # Pure 4xx patterns without "errors" return MEDIUM
        assert get_severity_level("api-4xx-rate") == "MEDIUM"
        assert get_severity_level("client-4xx") == "MEDIUM"
        # With "errors" suffix, it becomes HIGH
        assert get_severity_level("api-4xx-errors") == "HIGH"

    def test_duration_alarm_is_medium(self):
        """Duration alarms are MEDIUM severity."""
        assert get_severity_level("telegram-api-duration") == "MEDIUM"

    def test_unknown_alarm_is_info(self):
        """Unknown alarms default to INFO severity."""
        assert get_severity_level("some-random-metric") == "INFO"


class TestColorMapping:
    """Tests for get_color function.

    Invariant: Alarm states map to correct Slack attachment colors.
    """

    def test_alarm_state_returns_danger(self):
        """ALARM state returns danger (red) color."""
        assert get_color("ALARM") == "danger"

    def test_ok_state_returns_good(self):
        """OK state returns good (green) color."""
        assert get_color("OK") == "good"

    def test_other_state_returns_warning(self):
        """Other states (INSUFFICIENT_DATA) return warning (yellow)."""
        assert get_color("INSUFFICIENT_DATA") == "warning"
        assert get_color("UNKNOWN") == "warning"


class TestFormatSlackMessage:
    """Tests for format_slack_message function.

    Invariant: Slack message contains all required fields per alerting-invariants.md.
    """

    @pytest.fixture
    def sample_alarm_message(self):
        """Sample CloudWatch alarm message."""
        return {
            "AlarmName": "dr-daily-report-scheduler-errors-dev",
            "NewStateValue": "ALARM",
            "OldStateValue": "OK",
            "NewStateReason": "Threshold Crossed: 1 datapoint was greater than threshold",
            "StateChangeTime": "2026-01-14T10:00:00.000Z",
            "Region": "ap-southeast-1",
            "Trigger": {
                "Namespace": "AWS/Lambda",
                "MetricName": "Errors",
                "Dimensions": [
                    {"name": "FunctionName", "value": "dr-daily-report-scheduler-dev"}
                ],
            },
        }

    def test_message_contains_attachments(self, sample_alarm_message):
        """Message has attachments array."""
        result = format_slack_message(sample_alarm_message)
        assert "attachments" in result
        assert len(result["attachments"]) > 0

    def test_attachment_has_correct_color_for_alarm(self, sample_alarm_message):
        """Attachment color is danger (red) for ALARM state."""
        result = format_slack_message(sample_alarm_message)
        assert result["attachments"][0]["color"] == "danger"

    def test_attachment_has_correct_color_for_ok(self, sample_alarm_message):
        """Attachment color is good (green) for OK state."""
        sample_alarm_message["NewStateValue"] = "OK"
        sample_alarm_message["OldStateValue"] = "ALARM"
        result = format_slack_message(sample_alarm_message)
        assert result["attachments"][0]["color"] == "good"

    def test_title_contains_alarm_name(self, sample_alarm_message):
        """Title contains the alarm name."""
        result = format_slack_message(sample_alarm_message)
        assert "scheduler-errors" in result["attachments"][0]["title"]

    def test_title_link_points_to_cloudwatch(self, sample_alarm_message):
        """Title link points to CloudWatch console."""
        result = format_slack_message(sample_alarm_message)
        title_link = result["attachments"][0]["title_link"]
        assert "console.aws.amazon.com/cloudwatch" in title_link
        assert "alarmsV2" in title_link

    def test_fields_contain_state_transition(self, sample_alarm_message):
        """Fields include state transition."""
        result = format_slack_message(sample_alarm_message)
        fields = result["attachments"][0]["fields"]
        state_field = next((f for f in fields if f["title"] == "State"), None)
        assert state_field is not None
        assert "OK → ALARM" in state_field["value"]

    def test_fields_contain_severity(self, sample_alarm_message):
        """Fields include severity level."""
        result = format_slack_message(sample_alarm_message)
        fields = result["attachments"][0]["fields"]
        severity_field = next((f for f in fields if f["title"] == "Severity"), None)
        assert severity_field is not None
        assert severity_field["value"] == "CRITICAL"

    def test_fields_contain_metric_info(self, sample_alarm_message):
        """Fields include metric namespace/name."""
        result = format_slack_message(sample_alarm_message)
        fields = result["attachments"][0]["fields"]
        metric_field = next((f for f in fields if f["title"] == "Metric"), None)
        assert metric_field is not None
        assert "AWS/Lambda" in metric_field["value"]
        assert "Errors" in metric_field["value"]

    def test_resolved_message_has_prefix(self, sample_alarm_message):
        """OK state messages have RESOLVED prefix."""
        sample_alarm_message["NewStateValue"] = "OK"
        result = format_slack_message(sample_alarm_message)
        assert "RESOLVED" in result["attachments"][0]["title"]


class TestSendToSlack:
    """Tests for send_to_slack function.

    Invariant: Function handles success/failure cases gracefully.
    """

    def test_returns_false_when_webhook_url_empty(self):
        """Returns False when SLACK_WEBHOOK_URL not configured."""
        with patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", ""):
            result = send_to_slack({"text": "test"})
            assert result is False

    @patch("src.alerting.slack_notifier.urllib.request.urlopen")
    @patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    def test_returns_true_on_successful_send(self, mock_urlopen):
        """Returns True when Slack accepts the message."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = send_to_slack({"text": "test"})
        assert result is True

    @patch("src.alerting.slack_notifier.urllib.request.urlopen")
    @patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    def test_returns_false_on_http_error(self, mock_urlopen):
        """Returns False when Slack returns error status."""
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = send_to_slack({"text": "test"})
        assert result is False


class TestLambdaHandler:
    """Tests for lambda_handler function.

    Invariant: Handler processes SNS events correctly per alerting-invariants.md.
    """

    @pytest.fixture
    def sns_event(self):
        """Sample SNS event with CloudWatch alarm."""
        return {
            "Records": [
                {
                    "Sns": {
                        "Message": json.dumps({
                            "AlarmName": "test-alarm",
                            "NewStateValue": "ALARM",
                            "OldStateValue": "OK",
                            "NewStateReason": "Test reason",
                        })
                    }
                }
            ]
        }

    def test_returns_500_when_webhook_not_configured(self, sns_event):
        """Returns 500 when SLACK_WEBHOOK_URL not set."""
        with patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", ""):
            result = lambda_handler(sns_event, None)
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "not configured" in body["error"]

    @patch("src.alerting.slack_notifier.send_to_slack")
    @patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    def test_processes_all_records(self, mock_send, sns_event):
        """Processes all SNS records in the event."""
        mock_send.return_value = True

        # Add another record
        sns_event["Records"].append({
            "Sns": {
                "Message": json.dumps({
                    "AlarmName": "test-alarm-2",
                    "NewStateValue": "OK",
                })
            }
        })

        result = lambda_handler(sns_event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["processed"] == 2
        assert body["errors"] == 0

    @patch("src.alerting.slack_notifier.send_to_slack")
    @patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    def test_returns_207_on_partial_failure(self, mock_send, sns_event):
        """Returns 207 when some notifications fail."""
        mock_send.side_effect = [True, False]

        sns_event["Records"].append({
            "Sns": {"Message": json.dumps({"AlarmName": "test-2"})}
        })

        result = lambda_handler(sns_event, None)
        assert result["statusCode"] == 207
        body = json.loads(result["body"])
        assert body["processed"] == 1
        assert body["errors"] == 1

    @patch("src.alerting.slack_notifier.send_to_slack")
    @patch("src.alerting.slack_notifier.SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    def test_handles_malformed_json_gracefully(self, mock_send):
        """Handles non-JSON SNS messages gracefully."""
        mock_send.return_value = True

        event = {
            "Records": [
                {"Sns": {"Message": "This is not JSON"}}
            ]
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        # Should still attempt to send with fallback message
        mock_send.assert_called_once()
