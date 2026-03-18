-- traces: provenance + link to external tracing service
-- Detailed trace data (tokens, cost, spans) lives in the tracing service.
-- We store: WHO produced it, WHERE the full trace lives, and WHAT the outcome was.

CREATE TABLE IF NOT EXISTS traces (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_type          VARCHAR(50)  NOT NULL,        -- "report_generation", "sgx_ingestion", etc.

    -- Provenance: what produced this output
    model_id            VARCHAR(100),                 -- "openai/gpt-4o", NULL for non-LLM traces
    prompt_version      VARCHAR(50),                  -- "v4.2", from Langfuse prompt mgmt
    agent_type          VARCHAR(50),                  -- "single-stage", "multi-agent"
    `release`           VARCHAR(100),                 -- git SHA or version tag (code provenance)

    -- External trace link: where full trace details live
    trace_provider      VARCHAR(50),                  -- "langfuse", "langsmith", NULL
    trace_external_id   VARCHAR(200),                 -- ID in that system

    -- Type-specific context
    context             JSON,                         -- {symbol, report_date, ...}

    -- Outcome
    status              VARCHAR(20) NOT NULL DEFAULT 'completed',  -- "completed", "failed"
    error_message       TEXT,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_traces_type_created (trace_type, created_at),
    INDEX idx_traces_model (model_id, created_at),
    INDEX idx_traces_release (`release`),
    INDEX idx_traces_provider (trace_provider, trace_external_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Provenance metadata and tracing service link for any workload type';


-- trace_scores: quality measurements with full reproducibility metadata
-- EAV pattern: new score types added as rows, not columns.

CREATE TABLE IF NOT EXISTS trace_scores (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id        BIGINT NOT NULL,

    -- What score
    score_name      VARCHAR(100) NOT NULL,            -- "faithfulness", "placeholder_compliance"
    score_value     FLOAT        NOT NULL,            -- 0-100 (our scale)
    scorer_type     VARCHAR(20)  NOT NULL,            -- "rule", "llm", "computed"
    scorer_version  VARCHAR(20)  NOT NULL,            -- "1.0" -- for apples-to-apples comparison

    -- How it was calculated (reproducibility)
    sub_scores      JSON,                             -- {numeric_accuracy: 92, percentile: 78, ...}
    config          JSON,                             -- {weights: {numeric: .35, ...}, thresholds: {...}}
    comment         TEXT,                             -- human-readable summary

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_trace_score (trace_id, score_name),
    INDEX idx_score_lookup (score_name, score_value),
    INDEX idx_scorer_version (score_name, scorer_version),

    CONSTRAINT fk_trace_scores_trace
        FOREIGN KEY (trace_id) REFERENCES traces(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Quality scores with sub-score breakdown and config for reproducibility';
