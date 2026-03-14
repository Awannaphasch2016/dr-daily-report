-- Migration 023: Create users table
-- Tracks users across LINE and Telegram platforms
-- Supports UPSERT pattern: INSERT on first interaction, UPDATE on subsequent

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL COMMENT 'line | telegram',
    platform_uid VARCHAR(64) NOT NULL COMMENT 'Platform-specific user ID (LINE: U123..., Telegram: numeric)',
    display_name VARCHAR(128) DEFAULT NULL COMMENT 'Optional, fetched from platform API',
    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_platform_uid (platform, platform_uid),
    INDEX idx_users_last_seen (last_seen_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
