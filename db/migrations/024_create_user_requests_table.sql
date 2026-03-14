-- Migration 024: Create user_requests table
-- Logs every ticker request with user, result, and timing
-- Grows ~250 rows/day at current scale (~9 MB/year)

CREATE TABLE IF NOT EXISTS user_requests (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(20) NOT NULL COMMENT 'Denormalized from users for fast queries',
    result VARCHAR(20) NOT NULL COMMENT 'cache_hit | cache_miss | job_submitted | error',
    duration_ms INT DEFAULT NULL,
    request_id VARCHAR(64) DEFAULT NULL COMMENT 'Lambda request_id for CloudWatch correlation',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_ur_user_time (user_id, requested_at DESC),
    INDEX idx_ur_ticker_time (ticker, requested_at DESC),
    INDEX idx_ur_requested_at (requested_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
