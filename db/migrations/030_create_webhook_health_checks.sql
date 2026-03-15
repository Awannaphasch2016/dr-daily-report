-- Migration 030: Create webhook_health_checks table
-- Purpose: Store daily webhook health probe results for monitoring and Grafana dashboards
-- Dependencies: None (standalone table)

CREATE TABLE IF NOT EXISTS webhook_health_checks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    check_time DATETIME NOT NULL COMMENT 'When the check ran',
    endpoint VARCHAR(50) NOT NULL COMMENT 'line_webhook | telegram_api | ...',
    url VARCHAR(500) NOT NULL COMMENT 'Full URL checked',
    status VARCHAR(20) NOT NULL COMMENT 'healthy | degraded | down',
    http_code INT NOT NULL DEFAULT 0 COMMENT '200, 500, 0=timeout',
    latency_ms INT NOT NULL DEFAULT 0 COMMENT 'Response time in ms',
    body_valid BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Response body matches expected',
    error_msg TEXT NULL COMMENT 'Error details if not healthy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_whc_endpoint_time (endpoint, check_time DESC),
    INDEX idx_whc_status (status, check_time DESC),
    INDEX idx_whc_check_time (check_time DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Daily webhook endpoint health check results';
