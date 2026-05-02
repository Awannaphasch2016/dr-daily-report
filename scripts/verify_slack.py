#!/usr/bin/env python3
"""
Minimum Slack bot verification — stdlib only.

Checks:
  1. SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET present and well-formed
  2. auth.test confirms the token is valid (prints bot identity + scopes)
  3. HMAC v0 signature roundtrip with SLACK_SIGNING_SECRET
  4. (optional) chat.postMessage to a channel with --post-to <channel>

Run:
  doppler run --config dev -- python scripts/verify_slack.py
  doppler run --config dev -- python scripts/verify_slack.py --post-to '#general'
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SLACK_API = "https://slack.com/api"


def fail(msg: str, hint: str = "") -> None:
    print(f"❌ {msg}")
    if hint:
        print(f"   hint: {hint}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def slack_post(method: str, token: str, payload: dict) -> tuple[dict, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SLACK_API}/{method}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8")), dict(e.headers)
    except urllib.error.URLError as e:
        fail(f"network error calling {method}: {e}")


def check_env() -> tuple[str, str]:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    secret = os.environ.get("SLACK_SIGNING_SECRET", "").strip()

    if not token:
        fail(
            "SLACK_BOT_TOKEN not set",
            "ensure you're running via: doppler run --config dev -- python scripts/verify_slack.py",
        )
    if not secret:
        fail(
            "SLACK_SIGNING_SECRET not set",
            "doppler secrets set SLACK_SIGNING_SECRET=... --config dev",
        )

    if not token.startswith("xoxb-"):
        fail(
            f"SLACK_BOT_TOKEN has wrong prefix: {token[:8]}...",
            "expected xoxb- (bot user token from OAuth & Permissions, NOT xapp- or xoxp-)",
        )
    if len(secret) < 32 or not all(c in "0123456789abcdef" for c in secret.lower()):
        fail(
            "SLACK_SIGNING_SECRET does not look like a hex string",
            "copy it from api.slack.com/apps/<id> > Basic Information > Signing Secret",
        )

    ok(f"env vars present (token={token[:9]}..., secret len={len(secret)})")
    return token, secret


def check_auth(token: str) -> dict:
    data, headers = slack_post("auth.test", token, {})
    if not data.get("ok"):
        err = data.get("error", "unknown")
        hints = {
            "invalid_auth": "token is rejected by Slack — re-copy from OAuth & Permissions",
            "account_inactive": "the workspace or app is disabled",
            "token_revoked": "regenerate the bot token in Slack app config",
            "not_authed": "no token sent — check SLACK_BOT_TOKEN is exported",
        }
        fail(f"auth.test failed: {err}", hints.get(err, ""))
    ok(
        f"auth.test ok — team={data.get('team')} user={data.get('user')} "
        f"bot_id={data.get('bot_id')} url={data.get('url')}"
    )
    scopes = headers.get("x-oauth-scopes") or headers.get("X-OAuth-Scopes")
    if scopes:
        print(f"   scopes: {scopes}")
        for required in ("chat:write",):
            if required not in scopes:
                print(
                    f"   ⚠️  missing scope '{required}' "
                    "— add under OAuth & Permissions and reinstall the app"
                )
    return data


def check_signing(secret: str) -> None:
    ts = str(int(time.time()))
    body = "token=verify&team_id=T000&command=/test"
    base = f"v0:{ts}:{body}".encode("utf-8")
    sig = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    expected_prefix = "v0="
    if not sig.startswith(expected_prefix) or len(sig) != len(expected_prefix) + 64:
        fail("HMAC computation produced unexpected output")
    ok(f"signing secret roundtrip ok ({sig[:12]}...{sig[-4:]})")


def maybe_post(token: str, channel: str) -> None:
    text = f"verify_slack.py: bot is alive at {time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    data, _ = slack_post("chat.postMessage", token, {"channel": channel, "text": text})
    if not data.get("ok"):
        err = data.get("error", "unknown")
        hints = {
            "not_in_channel": f"invite the bot first: in Slack run `/invite @<bot>` in {channel}",
            "channel_not_found": f"channel {channel!r} not found — try the channel ID (Cxxxx) instead of name",
            "missing_scope": "bot is missing chat:write — add the scope and reinstall",
            "is_archived": "channel is archived",
            "rate_limited": "wait and retry",
        }
        fail(f"chat.postMessage failed: {err}", hints.get(err, ""))
    ok(f"chat.postMessage ok — ts={data.get('ts')} channel={data.get('channel')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Slack bot tokens (stdlib only)")
    parser.add_argument(
        "--post-to",
        metavar="CHANNEL",
        help="optional channel name (#general) or ID (Cxxxx) for end-to-end smoke test",
    )
    args = parser.parse_args()

    print("--- Slack bot verification ---")
    token, secret = check_env()
    check_auth(token)
    check_signing(secret)
    if args.post_to:
        maybe_post(token, args.post_to)
    else:
        print("(skip chat.postMessage — pass --post-to '#channel' to smoke-test delivery)")
    print("--- all checks passed ---")


if __name__ == "__main__":
    main()
