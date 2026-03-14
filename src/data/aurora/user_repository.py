"""User Repository for Aurora MySQL

Tracks users and their ticker requests across LINE and Telegram platforms.
Uses UPSERT pattern (INSERT ... ON DUPLICATE KEY UPDATE) for idempotent user tracking.
"""

import logging
from typing import Optional

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import USERS, USER_REQUESTS

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for users and user_requests tables."""

    def __init__(self):
        self.client = get_aurora_client()

    def upsert_user(self, platform: str, platform_uid: str) -> int:
        """Insert new user or update existing. Returns user id.

        Uses ON DUPLICATE KEY UPDATE to increment request_count
        and update last_seen_at on each interaction.
        """
        query = f"""
            INSERT INTO {USERS} (platform, platform_uid, request_count)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE
                last_seen_at = NOW(),
                request_count = request_count + 1
        """
        self.client.execute(query, (platform, platform_uid))

        # Fetch the user id (works for both insert and update)
        row = self.client.fetch_one(
            f"SELECT id FROM {USERS} WHERE platform = %s AND platform_uid = %s",
            (platform, platform_uid)
        )
        return row["id"]

    def record_request(self, user_id: int, ticker: str, platform: str,
                       result: str, duration_ms: Optional[float] = None,
                       request_id: Optional[str] = None,
                       response_body: Optional[str] = None) -> None:
        """Record a user's ticker request."""
        query = f"""
            INSERT INTO {USER_REQUESTS}
                (user_id, ticker, platform, result, duration_ms, request_id, response_body)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        duration_int = int(duration_ms) if duration_ms is not None else None
        # Truncate to 10KB to avoid bloating the table
        truncated_body = response_body[:10000] if response_body else None
        self.client.execute(query, (user_id, ticker, platform, result,
                                    duration_int, request_id, truncated_body))
