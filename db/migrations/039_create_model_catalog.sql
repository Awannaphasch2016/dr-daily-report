-- model_catalog: synced model metadata from OpenRouter
-- Natural PK on model_id — matches traces.model_id for direct joins.
-- Typed columns for SQL queries + raw_json for future-proofing.

CREATE TABLE IF NOT EXISTS model_catalog (
    model_id                VARCHAR(150) NOT NULL PRIMARY KEY,
    name                    VARCHAR(255),
    context_length          INT,
    input_price_per_token   DECIMAL(16,12),
    output_price_per_token  DECIMAL(16,12),
    modality                VARCHAR(50),
    tokenizer               VARCHAR(50),
    provider                VARCHAR(100),
    is_free                 BOOLEAN DEFAULT FALSE,
    created_at_source       TIMESTAMP NULL,
    raw_json                JSON,
    synced_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_model_catalog_provider (provider),
    INDEX idx_model_catalog_modality (modality),
    INDEX idx_model_catalog_synced (synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Model metadata synced from OpenRouter API';


-- v_model_performance_summary: aggregates traces + trace_scores per (model_id, trace_type)
-- VIEW (not materialized) — traces grow slowly (~80 rows/day), always current, zero maintenance.

CREATE OR REPLACE VIEW v_model_performance_summary AS
SELECT
    t.model_id,
    t.trace_type,
    COUNT(*)                                                    AS sample_count,
    ROUND(AVG(CASE WHEN ts.score_name = 'faithfulness'
                   THEN ts.score_value END), 2)                 AS avg_faithfulness,
    ROUND(AVG(CASE WHEN ts.score_name = 'completeness'
                   THEN ts.score_value END), 2)                 AS avg_completeness,
    ROUND(AVG(CASE WHEN ts.score_name = 'placeholder_compliance'
                   THEN ts.score_value END), 2)                 AS avg_placeholder_compliance,
    ROUND(AVG(CASE WHEN ts.score_name = 'cost_efficiency'
                   THEN ts.score_value END), 2)                 AS avg_cost_efficiency,
    ROUND(AVG(t.cost_usd), 6)                                  AS avg_cost_usd,
    ROUND(AVG(t.input_tokens + t.output_tokens), 0)            AS avg_total_tokens,
    ROUND(
        (
            COALESCE(AVG(CASE WHEN ts.score_name = 'faithfulness'
                              THEN ts.score_value END), 0)
          + COALESCE(AVG(CASE WHEN ts.score_name = 'completeness'
                              THEN ts.score_value END), 0)
          + COALESCE(AVG(CASE WHEN ts.score_name = 'placeholder_compliance'
                              THEN ts.score_value END), 0)
          + COALESCE(AVG(CASE WHEN ts.score_name = 'cost_efficiency'
                              THEN ts.score_value END), 0)
        ) / 4.0
        / NULLIF(AVG(t.cost_usd), 0),
        2
    )                                                           AS quality_per_dollar,
    MIN(t.created_at)                                           AS first_seen,
    MAX(t.created_at)                                           AS last_seen
FROM traces t
LEFT JOIN trace_scores ts ON ts.trace_id = t.id
WHERE t.model_id IS NOT NULL
  AND t.status = 'completed'
GROUP BY t.model_id, t.trace_type;
