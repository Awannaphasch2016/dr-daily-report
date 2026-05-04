# -*- coding: utf-8 -*-
"""Slack Installations Repository

One row per Slack workspace that has installed the bot via OAuth v2.
Idempotent UPSERT — re-installs refresh bot_token in place.

Schema: db/migrations/041_create_slack_installations.sql
"""

import logging
from typing import Optional

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import SLACK_INSTALLATIONS

logger = logging.getLogger(__name__)


class SlackInstallationsRepository:
    """Repository for the slack_installations table."""

    def __init__(self):
        self.client = get_aurora_client()

    def upsert_installation(
        self,
        team_id: str,
        team_name: str,
        bot_token: str,
        bot_user_id: str,
        scope: str,
    ) -> None:
        """Insert a new install record or update an existing one in place.

        Re-installs (same team_id) refresh bot_token, bot_user_id, scope, and
        team_name; the row's installed_at is preserved while updated_at advances
        via ON UPDATE CURRENT_TIMESTAMP.
        """
        query = f"""
            INSERT INTO {SLACK_INSTALLATIONS}
                (team_id, team_name, bot_token, bot_user_id, scope)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                team_name   = VALUES(team_name),
                bot_token   = VALUES(bot_token),
                bot_user_id = VALUES(bot_user_id),
                scope       = VALUES(scope)
        """
        self.client.execute(query, (team_id, team_name, bot_token, bot_user_id, scope))
        logger.info(f"✅ Slack install upserted (team_id={team_id} team_name={team_name})")

    def get_token_by_team_id(self, team_id: str) -> Optional[str]:
        """Look up the bot_token for a workspace. Returns None if not installed.

        Reserved for the read-path multi-tenant refactor (follow-up spec) — the
        install path doesn't call this, but it's defined here so the read-path
        change becomes a one-liner later.
        """
        row = self.client.fetch_one(
            f"SELECT bot_token FROM {SLACK_INSTALLATIONS} WHERE team_id = %s",
            (team_id,),
        )
        return row["bot_token"] if row else None
