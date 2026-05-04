-- slack_installations: per-workspace Slack OAuth install records.
-- Natural PK on team_id (Slack workspace id, e.g. "T01ABC...") — for a fixed
-- Slack app, team_id alone identifies the install row.
-- Idempotent on re-install: bot_token, bot_user_id, scope are refreshed via
-- INSERT ... ON DUPLICATE KEY UPDATE (see slack_installations_repository.py).

CREATE TABLE IF NOT EXISTS slack_installations (
    team_id      VARCHAR(50)  NOT NULL PRIMARY KEY,
    team_name    VARCHAR(255) NOT NULL,
    bot_token    VARCHAR(255) NOT NULL,
    bot_user_id  VARCHAR(50)  NOT NULL,
    scope        TEXT         NOT NULL,
    installed_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_slack_installations_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Slack OAuth install records, one row per installed workspace';
