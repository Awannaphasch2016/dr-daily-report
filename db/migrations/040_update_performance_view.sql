-- Migration 040: Reshape v_model_performance_summary to per-score rows
--
-- Purpose: Enable per-scorer version comparison. The old pivoted view
-- (one row per model with avg_faithfulness, avg_completeness columns)
-- can't group each score by its own scorer_version. Per-score rows
-- with GROUP BY (model_id, trace_type, score_name, scorer_version)
-- allow apples-to-apples comparison when individual scorers change.

CREATE OR REPLACE VIEW v_model_performance_summary AS
SELECT
    t.model_id,
    t.trace_type,
    ts.score_name,
    ts.scorer_version,
    COUNT(*)                            AS sample_count,
    ROUND(AVG(ts.score_value), 2)       AS avg_score,
    ROUND(STDDEV(ts.score_value), 2)    AS stddev_score,
    ROUND(AVG(t.cost_usd), 6)          AS avg_cost_usd,
    ROUND(AVG(t.input_tokens + t.output_tokens), 0) AS avg_total_tokens,
    ROUND(
        AVG(ts.score_value) / NULLIF(AVG(t.cost_usd), 0),
        2
    )                                   AS score_per_dollar,
    MIN(t.created_at)                   AS first_seen,
    MAX(t.created_at)                   AS last_seen
FROM traces t
INNER JOIN trace_scores ts ON ts.trace_id = t.id
WHERE t.model_id IS NOT NULL
  AND t.status = 'completed'
GROUP BY t.model_id, t.trace_type, ts.score_name, ts.scorer_version;
