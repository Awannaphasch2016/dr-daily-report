# -*- coding: utf-8 -*-
"""
Telegram Mini App Authentication

Validates Telegram WebApp initData using HMAC-SHA256.
See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import os
import time
from typing import Optional
from urllib.parse import parse_qs, unquote
import logging

logger = logging.getLogger(__name__)

# Auth configuration
AUTH_EXPIRATION_SECONDS = 86400  # 24 hours


class TelegramAuthError(Exception):
    """Telegram authentication error"""
    pass


class TelegramAuth:
    """Validates Telegram Mini App authentication data"""

    def __init__(self, bot_token: Optional[str] = None):
        """Initialize with bot token

        Args:
            bot_token: Telegram bot token. If None, reads from TELEGRAM_BOT_TOKEN env var
        """
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - auth validation will be skipped")

    def validate_init_data(self, init_data: str) -> dict:
        """Validate Telegram WebApp initData and extract user info

        Args:
            init_data: The initData string from Telegram WebApp

        Returns:
            Dict containing user info and other validated data

        Raises:
            TelegramAuthError: If validation fails
        """
        if not init_data:
            raise TelegramAuthError("initData is empty")

        if not self.bot_token:
            # Skip validation if no bot token (development mode)
            logger.warning("Skipping auth validation - no bot token configured")
            return self._parse_init_data_unsafe(init_data)

        try:
            # Parse the init_data query string
            parsed = parse_qs(init_data, keep_blank_values=True)

            # Extract hash
            received_hash = parsed.get("hash", [None])[0]
            if not received_hash:
                raise TelegramAuthError("Missing hash in initData")

            # Check auth_date expiration
            auth_date_str = parsed.get("auth_date", [None])[0]
            if auth_date_str:
                auth_date = int(auth_date_str)
                current_time = int(time.time())
                if current_time - auth_date > AUTH_EXPIRATION_SECONDS:
                    raise TelegramAuthError("initData has expired")

            # Build data_check_string (sorted key=value pairs, excluding hash)
            data_check_pairs = []
            for key in sorted(parsed.keys()):
                if key != "hash":
                    # For each key, join multiple values or use single value
                    value = parsed[key][0] if len(parsed[key]) == 1 else parsed[key]
                    if isinstance(value, list):
                        value = value[0]
                    data_check_pairs.append(f"{key}={value}")

            data_check_string = "\n".join(data_check_pairs)

            # Compute secret key: HMAC-SHA256(bot_token, "WebAppData")
            secret_key = hmac.new(
                b"WebAppData",
                self.bot_token.encode('utf-8'),
                hashlib.sha256
            ).digest()

            # Compute hash: HMAC-SHA256(data_check_string, secret_key)
            computed_hash = hmac.new(
                secret_key,
                data_check_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Compare hashes
            if not hmac.compare_digest(computed_hash, received_hash):
                raise TelegramAuthError("Invalid hash - authentication failed")

            # Parse and return user data
            result = {}
            for key, values in parsed.items():
                if key == "hash":
                    continue
                value = values[0] if len(values) == 1 else values
                # Parse JSON fields (user, receiver, chat)
                if key in ("user", "receiver", "chat") and value:
                    try:
                        result[key] = json.loads(unquote(value))
                    except json.JSONDecodeError:
                        result[key] = value
                else:
                    result[key] = value

            logger.info(f"✅ Telegram auth validated for user: {result.get('user', {}).get('id', 'unknown')}")
            return result

        except TelegramAuthError:
            raise
        except Exception as e:
            logger.error(f"Auth validation error: {e}")
            raise TelegramAuthError(f"Failed to validate initData: {e}")

    def _parse_init_data_unsafe(self, init_data: str) -> dict:
        """Parse initData without validation (for development only)

        Args:
            init_data: The initData string

        Returns:
            Parsed data dict
        """
        try:
            parsed = parse_qs(init_data, keep_blank_values=True)
            result = {}
            for key, values in parsed.items():
                if key == "hash":
                    continue
                value = values[0] if len(values) == 1 else values
                if key in ("user", "receiver", "chat") and value:
                    try:
                        result[key] = json.loads(unquote(value))
                    except json.JSONDecodeError:
                        result[key] = value
                else:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Failed to parse initData: {e}")
            return {}

    def get_user_id(self, init_data: str) -> str:
        """Validate initData and extract user ID

        Args:
            init_data: The initData string from Telegram WebApp

        Returns:
            User ID as string

        Raises:
            TelegramAuthError: If validation fails or user ID not found
        """
        validated = self.validate_init_data(init_data)
        user = validated.get("user", {})
        user_id = user.get("id")

        if not user_id:
            raise TelegramAuthError("User ID not found in initData")

        return str(user_id)


# Module-level singleton
_auth_instance: Optional[TelegramAuth] = None


def get_telegram_auth() -> TelegramAuth:
    """Get or create TelegramAuth singleton"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = TelegramAuth()
    return _auth_instance
