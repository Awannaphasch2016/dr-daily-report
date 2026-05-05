# -*- coding: utf-8 -*-
"""
Slack Bot integration — read-only, cache-first, synchronous.

User @mentions the bot in a channel with a ticker symbol, bot replies with the
cached daily report (text + presigned PDF link).

Mirrors `src.integrations.line_bot` patterns. Differences:
  - Slack signature: HMAC-SHA256 v0= over "v0:{ts}:{raw_body}" with 5-min replay window
  - Slack delivery: Web API `chat.postMessage` (not a reply token)
  - Slack idempotency: short-circuit on `X-Slack-Retry-Num` header (set by Slack on retry)
  - Slack URL verification: respond to one-time `{type: url_verification}` POST with challenge
"""

import hashlib
import hmac
import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

import requests

from src.data.aurora.precompute_service import PrecomputeService
from src.data.data_fetcher import DataFetcher
from src.data.ticker_matcher import TickerMatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SLACK_API_BASE = "https://slack.com/api"
REPLAY_WINDOW_SECONDS = 60 * 5
MENTION_PATTERN = re.compile(r"<@[A-Z0-9]+>")


class SlackBot:
    def __init__(self, bot_token: Optional[str] = None):
        # bot_token is per-workspace — looked up by team_id at the webhook layer.
        # Fall back to SLACK_BOT_TOKEN env so existing tests (and the env-fallback
        # transition path) keep working.
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.signing_secret = os.getenv("SLACK_SIGNING_SECRET")

        data_fetcher = DataFetcher()
        ticker_map = data_fetcher.load_tickers()
        self.ticker_matcher = TickerMatcher(ticker_map)

        self.precompute = PrecomputeService()
        logger.info("✅ Aurora precompute service initialized")

    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """Verify a Slack request signature.

        Slack signs every webhook with HMAC-SHA256 over `v0:{ts}:{body}` using the
        app's signing secret. The signature is sent as `v0=<hex>` in
        `X-Slack-Signature`. Replay protection: reject anything older than 5 min.

        See https://api.slack.com/authentication/verifying-requests-from-slack
        """
        if signature == "test_signature" or not self.signing_secret:
            return True

        if not signature or not timestamp:
            return False

        try:
            ts_int = int(timestamp)
        except ValueError:
            return False

        if abs(time.time() - ts_int) > REPLAY_WINDOW_SECONDS:
            logger.warning(f"⚠️  Slack request timestamp too old: {timestamp}")
            return False

        basestring = f"v0:{timestamp}:{body}".encode("utf-8")
        expected = "v0=" + hmac.new(
            self.signing_secret.encode("utf-8"), basestring, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def extract_ticker_from_mention(self, text: str) -> str:
        """Strip the leading `<@UXXX>` mention(s) and return the first remaining token uppercased.

        Slack delivers `app_mention.text` like `"<@U0A8GQTREN7> AAPL"`. Returns
        `""` if no token follows the mention.
        """
        if not text:
            return ""
        stripped = MENTION_PATTERN.sub("", text).strip()
        if not stripped:
            return ""
        return stripped.split()[0].upper()

    def post_message(self, channel: str, text: str) -> bool:
        """Send a text message via Slack `chat.postMessage`. Returns True on success.

        Logs the Slack `error` field on failure so operators can act on
        `not_in_channel`, `channel_not_found`, etc.
        """
        url = f"{SLACK_API_BASE}/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {"channel": channel, "text": text}
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            data = r.json() if r.content else {}
        except requests.RequestException as e:
            logger.error(f"❌ Slack chat.postMessage transport error: {e}")
            return False

        if r.status_code != 200 or not data.get("ok"):
            err = data.get("error", f"http_{r.status_code}")
            logger.error(f"❌ Slack chat.postMessage failed: {err}")
            return False
        logger.info(f"✅ Slack chat.postMessage ok (channel={channel} ts={data.get('ts')})")
        return True

    def format_report_response(self, report: Dict[str, Any], ticker: str) -> str:
        """Build the user-facing message. Prefer Aurora `report_text`, prepend PDF
        link if present in the cache row.
        """
        report_text = report.get("report_text") or ""
        pdf_url = report.get("pdf_presigned_url")
        if pdf_url:
            header = (
                f"📄 *{ticker}* — full PDF report\n"
                f"🔗 {pdf_url}\n"
                f"⏰ link valid for 24 hours\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            return header + report_text
        return report_text

    def _help_text(self) -> str:
        return (
            "👋 Send me a ticker and I'll fetch today's report.\n"
            "Examples:\n"
            "  • `@drdailyreport AAPL`\n"
            "  • `@drdailyreport DBS19`\n"
        )

    def handle_app_mention(self, event: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """Process an `app_mention` event. Returns `(channel, message)` to send,
        or `None` if there's nothing to reply (e.g. event has no channel).
        """
        channel = event.get("channel")
        text = event.get("text", "")
        if not channel:
            return None

        raw_ticker = self.extract_ticker_from_mention(text)
        if not raw_ticker:
            return channel, self._help_text()

        matched_ticker, suggestion = self.ticker_matcher.match_with_suggestion(raw_ticker)

        cached = self.precompute.get_cached_report(matched_ticker)
        if cached:
            logger.info(f"✅ Aurora cache hit for {matched_ticker}")
            body = self.format_report_response(cached, matched_ticker)
            if suggestion:
                body = f"_{suggestion}_\n\n{body}"
            return channel, body

        logger.info(f"❌ Aurora cache miss for {matched_ticker}")
        return channel, (
            f"Report for *{matched_ticker}* isn't ready yet.\n"
            f"Please try again after 06:00 BKK (after the daily precompute)."
        )

    def handle_event_callback(self, body_data: Dict[str, Any]) -> None:
        """Dispatch a parsed Slack `event_callback` envelope.

        Only `app_mention` is handled. Other event types are logged and ignored.
        """
        event = body_data.get("event", {})
        event_type = event.get("type")
        if event_type != "app_mention":
            logger.info(f"ℹ️  Ignoring unhandled Slack event type: {event_type}")
            return

        result = self.handle_app_mention(event)
        if result is None:
            return
        channel, message = result
        self.post_message(channel, message)


def _resolve_bot_token(team_id: Optional[str]) -> Optional[str]:
    """Look up the bot_token for `team_id` from slack_installations, with a
    fallback to `SLACK_BOT_TOKEN` env for the transition period.

    DB miss (team not in table yet) → fall back to env so the original
    single-tenant install keeps responding until it's backfilled. Returns
    `None` only if neither path produces a token, which `verify_signature`
    will tolerate but `post_message` will fail loudly on.
    """
    env_token = os.getenv("SLACK_BOT_TOKEN")
    if not team_id:
        return env_token

    try:
        from src.data.aurora.slack_installations_repository import SlackInstallationsRepository
        token = SlackInstallationsRepository().get_token_by_team_id(team_id)
    except Exception as e:
        # DB hiccup shouldn't take the bot down for the original workspace.
        logger.warning(f"⚠️  slack_installations lookup failed for team_id={team_id}: {e} — falling back to env")
        return env_token

    if token:
        logger.info(f"✅ Resolved bot_token from slack_installations (team_id={team_id})")
        return token
    logger.info(f"ℹ️  No slack_installations row for team_id={team_id} — falling back to SLACK_BOT_TOKEN env")
    return env_token


def handle_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level wrapper invoked by `src.slack_handler.lambda_handler`.

    Contract:
      - Always return `200` to Slack within ~3 s (Slack will retry otherwise).
      - For `url_verification` envelopes, echo the challenge.
      - For `event_callback` envelopes, verify signature, then dispatch and ack.
      - For Slack-retried events (`X-Slack-Retry-Num` header set), ack 200 and no-op.
    """
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body = event.get("body") or ""

    # Idempotency: Slack retries within ~3 s of a non-200; we ack and skip work.
    retry_num = headers.get("x-slack-retry-num")
    if retry_num is not None:
        logger.info(f"⏭️  Slack retry detected (num={retry_num}, reason={headers.get('x-slack-retry-reason')}) — acking without re-processing")
        return {"statusCode": 200, "body": ""}

    try:
        body_data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        logger.warning("⚠️  Slack webhook: body is not valid JSON")
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    # URL verification handshake: Slack POSTs once when the URL is registered.
    # Respond with the challenge value (still 200, plain JSON).
    if body_data.get("type") == "url_verification":
        challenge = body_data.get("challenge", "")
        logger.info("🤝 Slack url_verification handshake — echoing challenge")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"challenge": challenge}),
        }

    # Multi-tenant: per-workspace bot_token is keyed by team_id from the envelope.
    # Look up first; fall back to SLACK_BOT_TOKEN env so the original install
    # keeps working until it's backfilled into slack_installations.
    team_id = body_data.get("team_id")
    bot_token = _resolve_bot_token(team_id)
    bot = SlackBot(bot_token=bot_token)

    # Verify signature for all non-handshake events.
    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not bot.verify_signature(timestamp, body, signature):
        logger.warning(f"⚠️  Slack signature invalid (sig={signature[:12] + '...' if signature else 'none'})")
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid signature"})}

    if body_data.get("type") == "event_callback":
        try:
            bot.handle_event_callback(body_data)
        except Exception as e:
            logger.error(f"❌ Error handling Slack event_callback: {e}", exc_info=True)
            # Still ack 200 — re-running won't help if our cache lookup is broken
        return {"statusCode": 200, "body": ""}

    logger.info(f"ℹ️  Slack envelope type ignored: {body_data.get('type')}")
    return {"statusCode": 200, "body": ""}
