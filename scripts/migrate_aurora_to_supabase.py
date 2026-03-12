#!/usr/bin/env python3
"""
Aurora MySQL → Supabase PostgreSQL Migration Script

One-time data migration. Aurora remains primary — this is a data copy.

Prerequisites:
    pip install psycopg2-binary
    SSM tunnel active for Aurora access
    SUPABASE_DATABASE_URL in Doppler (rag-chatbot-worktree / local_dev)

Usage:
    # Full migration (via SSM tunnel)
    doppler run --project rag-chatbot-worktree --config local_dev -- \
        python scripts/migrate_aurora_to_supabase.py

    # Schema only / Verify only / Dry run / Single table
    ... --schema-only
    ... --verify-only
    ... --dry-run
    ... --table daily_prices
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

TABLE_ORDER = [
    "ticker_master",
    "ticker_aliases",
    "daily_prices",
    "ticker_data",
    "ticker_cache_metadata",
    "fund_data",
    "daily_indicators",
    "indicator_percentiles",
    "comparative_features",
    "precomputed_reports",
    "chart_pattern_data",
]

BATCH_SIZES = {
    "ticker_master": 1000,
    "ticker_aliases": 1000,
    "daily_prices": 5000,
    "ticker_data": 2000,
    "ticker_cache_metadata": 2000,
    "fund_data": 5000,
    "daily_indicators": 2000,
    "indicator_percentiles": 2000,
    "comparative_features": 2000,
    "precomputed_reports": 100,
    "chart_pattern_data": 2000,
}

JSON_COLUMNS = {
    "ticker_data": {"price_history", "company_info", "financials_json"},
    "precomputed_reports": {"report_json"},
    "chart_pattern_data": {"pattern_data"},
}

BOOL_COLUMNS = {
    "ticker_master": {"is_active"},
    "ticker_aliases": {"is_primary"},
}

# Tables with updated_at that need trigger
TABLES_WITH_UPDATED_AT = [
    "ticker_master",
    "ticker_data",
    "ticker_cache_metadata",
    "daily_indicators",
    "indicator_percentiles",
    "comparative_features",
    "precomputed_reports",
    "chart_pattern_data",
]

# ============================================================================
# PostgreSQL DDL
# ============================================================================

TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

PG_DDL = {
    "ticker_master": """
CREATE TABLE IF NOT EXISTS ticker_master (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_name VARCHAR(255),
    exchange VARCHAR(100),
    currency VARCHAR(10),
    sector VARCHAR(100),
    industry VARCHAR(100),
    quote_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ticker_master_company ON ticker_master (company_name);
CREATE INDEX IF NOT EXISTS idx_ticker_master_active ON ticker_master (is_active);
""",
    "ticker_aliases": """
CREATE TABLE IF NOT EXISTS ticker_aliases (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id BIGINT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    symbol_type VARCHAR(20) CHECK (symbol_type IN ('dr', 'yahoo', 'bloomberg', 'other', 'eikon')),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ticker_id, symbol)
);
CREATE INDEX IF NOT EXISTS idx_aliases_ticker_id ON ticker_aliases (ticker_id);
CREATE INDEX IF NOT EXISTS idx_aliases_symbol ON ticker_aliases (symbol);
""",
    "daily_prices": """
CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open NUMERIC(18, 6),
    high NUMERIC(18, 6),
    low NUMERIC(18, 6),
    close NUMERIC(18, 6),
    adj_close NUMERIC(18, 6),
    volume BIGINT,
    daily_return NUMERIC(10, 6),
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, price_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_id ON daily_prices (ticker_id);
CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol ON daily_prices (symbol);
CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices (price_date);
CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices (symbol, price_date DESC);
""",
    "ticker_data": """
CREATE TABLE IF NOT EXISTS ticker_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_master_id BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    price_history JSONB NOT NULL,
    company_info JSONB,
    financials_json JSONB,
    history_start_date DATE,
    history_end_date DATE,
    row_count INT,
    source VARCHAR(50) DEFAULT 'yfinance',
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_cache_fetched ON ticker_data (fetched_at);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON ticker_data (expires_at);
""",
    "ticker_cache_metadata": """
CREATE TABLE IF NOT EXISTS ticker_cache_metadata (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cache_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    s3_key VARCHAR(255),
    rows_in_aurora INT DEFAULT 0,
    error_message TEXT,
    cached_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, cache_date)
);
CREATE INDEX IF NOT EXISTS idx_cache_date ON ticker_cache_metadata (cache_date);
CREATE INDEX IF NOT EXISTS idx_cache_status ON ticker_cache_metadata (status);
""",
    "fund_data": """
CREATE TABLE IF NOT EXISTS fund_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    d_trade DATE NOT NULL,
    stock VARCHAR(50) NOT NULL,
    ticker VARCHAR(50) NOT NULL,
    col_code VARCHAR(100) NOT NULL,
    value_numeric NUMERIC(20, 6),
    value_text TEXT,
    source VARCHAR(50) DEFAULT 'sql_server',
    s3_source_key VARCHAR(500),
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (d_trade, stock, ticker, col_code)
);
CREATE INDEX IF NOT EXISTS idx_fund_data_d_trade ON fund_data (d_trade DESC);
CREATE INDEX IF NOT EXISTS idx_fund_data_ticker ON fund_data (ticker);
CREATE INDEX IF NOT EXISTS idx_fund_data_col_code ON fund_data (col_code);
CREATE INDEX IF NOT EXISTS idx_fund_data_synced ON fund_data (synced_at DESC);
""",
    "daily_indicators": """
CREATE TABLE IF NOT EXISTS daily_indicators (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    indicator_date DATE NOT NULL,
    open_price NUMERIC(18, 6),
    high_price NUMERIC(18, 6),
    low_price NUMERIC(18, 6),
    close_price NUMERIC(18, 6),
    volume BIGINT,
    sma_20 NUMERIC(18, 6),
    sma_50 NUMERIC(18, 6),
    sma_200 NUMERIC(18, 6),
    rsi_14 NUMERIC(10, 4),
    macd NUMERIC(18, 6),
    macd_signal NUMERIC(18, 6),
    macd_histogram NUMERIC(18, 6),
    bb_upper NUMERIC(18, 6),
    bb_middle NUMERIC(18, 6),
    bb_lower NUMERIC(18, 6),
    atr_14 NUMERIC(18, 6),
    atr_percent NUMERIC(10, 4),
    vwap NUMERIC(18, 6),
    volume_sma_20 BIGINT,
    volume_ratio NUMERIC(10, 4),
    uncertainty_score NUMERIC(10, 4),
    price_vwap_pct NUMERIC(10, 4),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, indicator_date)
);
CREATE INDEX IF NOT EXISTS idx_indicators_ticker ON daily_indicators (ticker_id);
CREATE INDEX IF NOT EXISTS idx_indicators_date ON daily_indicators (indicator_date);
""",
    "indicator_percentiles": """
CREATE TABLE IF NOT EXISTS indicator_percentiles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    percentile_date DATE NOT NULL,
    lookback_days INT NOT NULL DEFAULT 365,
    current_price_percentile NUMERIC(5, 2),
    rsi_percentile NUMERIC(5, 2),
    rsi_mean NUMERIC(10, 4),
    rsi_std NUMERIC(10, 4),
    rsi_freq_above_70 NUMERIC(5, 2),
    rsi_freq_below_30 NUMERIC(5, 2),
    macd_percentile NUMERIC(5, 2),
    macd_freq_positive NUMERIC(5, 2),
    uncertainty_percentile NUMERIC(5, 2),
    uncertainty_freq_low NUMERIC(5, 2),
    uncertainty_freq_high NUMERIC(5, 2),
    atr_pct_percentile NUMERIC(5, 2),
    atr_freq_low NUMERIC(5, 2),
    atr_freq_high NUMERIC(5, 2),
    volume_ratio_percentile NUMERIC(5, 2),
    volume_freq_high NUMERIC(5, 2),
    volume_freq_low NUMERIC(5, 2),
    sma_20_dev_percentile NUMERIC(5, 2),
    sma_50_dev_percentile NUMERIC(5, 2),
    sma_200_dev_percentile NUMERIC(5, 2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, percentile_date, lookback_days)
);
CREATE INDEX IF NOT EXISTS idx_percentiles_ticker ON indicator_percentiles (ticker_id);
CREATE INDEX IF NOT EXISTS idx_percentiles_date ON indicator_percentiles (percentile_date);
""",
    "comparative_features": """
CREATE TABLE IF NOT EXISTS comparative_features (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    feature_date DATE NOT NULL,
    daily_return NUMERIC(10, 6),
    weekly_return NUMERIC(10, 6),
    monthly_return NUMERIC(10, 6),
    ytd_return NUMERIC(10, 6),
    volatility_30d NUMERIC(10, 6),
    volatility_90d NUMERIC(10, 6),
    sharpe_ratio_30d NUMERIC(10, 4),
    sharpe_ratio_90d NUMERIC(10, 4),
    max_drawdown_30d NUMERIC(10, 6),
    max_drawdown_90d NUMERIC(10, 6),
    rs_vs_set NUMERIC(10, 6),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, feature_date)
);
CREATE INDEX IF NOT EXISTS idx_features_ticker ON comparative_features (ticker_id);
CREATE INDEX IF NOT EXISTS idx_features_date ON comparative_features (feature_date);
""",
    "precomputed_reports": """
CREATE TABLE IF NOT EXISTS precomputed_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,
    report_text TEXT,
    report_json JSONB,
    generation_time_ms INT DEFAULT 0,
    chart_base64 TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    computed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    pdf_s3_key VARCHAR(500),
    pdf_presigned_url TEXT,
    pdf_url_expires_at TIMESTAMP,
    pdf_generated_at TIMESTAMPTZ,
    UNIQUE (symbol, report_date)
);
CREATE INDEX IF NOT EXISTS idx_report_ticker_id ON precomputed_reports (ticker_id);
CREATE INDEX IF NOT EXISTS idx_report_date ON precomputed_reports (report_date DESC);
CREATE INDEX IF NOT EXISTS idx_report_status ON precomputed_reports (status);
CREATE INDEX IF NOT EXISTS idx_pdf_generated ON precomputed_reports (pdf_generated_at DESC);
""",
    "chart_pattern_data": """
CREATE TABLE IF NOT EXISTS chart_pattern_data (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    pattern_date DATE NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_code VARCHAR(20) NOT NULL,
    implementation VARCHAR(50) NOT NULL,
    impl_version VARCHAR(20) NOT NULL,
    confidence VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (confidence IN ('high', 'medium', 'low')),
    start_date DATE,
    end_date DATE,
    pattern_data JSONB NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (symbol, pattern_date, pattern_type, implementation)
);
CREATE INDEX IF NOT EXISTS idx_cpd_ticker_id ON chart_pattern_data (ticker_id);
CREATE INDEX IF NOT EXISTS idx_cpd_symbol ON chart_pattern_data (symbol);
CREATE INDEX IF NOT EXISTS idx_cpd_pattern_date ON chart_pattern_data (pattern_date DESC);
CREATE INDEX IF NOT EXISTS idx_cpd_pattern_type ON chart_pattern_data (pattern_type);
CREATE INDEX IF NOT EXISTS idx_cpd_implementation ON chart_pattern_data (implementation);
""",
}

PG_FK_CONSTRAINTS = [
    "ALTER TABLE precomputed_reports ADD CONSTRAINT fk_precomputed_reports_ticker_id FOREIGN KEY (ticker_id) REFERENCES ticker_master(id);",
    "ALTER TABLE chart_pattern_data ADD CONSTRAINT fk_chart_pattern_data_ticker_id FOREIGN KEY (ticker_id) REFERENCES ticker_master(id);",
]


# ============================================================================
# Connection helpers
# ============================================================================


def connect_aurora() -> pymysql.Connection:
    """Connect to Aurora MySQL using env vars from Doppler."""
    host = os.environ.get("AURORA_HOST")
    port = int(os.environ.get("AURORA_PORT", "3306"))
    user = os.environ.get("AURORA_USERNAME", "admin")
    password = os.environ.get("AURORA_PASSWORD")
    database = os.environ.get("AURORA_DATABASE", "ticker_data")

    if not host or not password:
        logger.error("AURORA_HOST and AURORA_PASSWORD must be set (via Doppler)")
        sys.exit(1)

    logger.info(f"Connecting to Aurora: {host}:{port}/{database}")
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
        read_timeout=600,
        write_timeout=30,
    )
    logger.info("Aurora connection established")
    return conn


def connect_supabase() -> "psycopg2.extensions.connection":
    """Connect to Supabase PostgreSQL using SUPABASE_DATABASE_URL."""
    url = os.environ.get("SUPABASE_DATABASE_URL")
    if not url:
        logger.error("SUPABASE_DATABASE_URL must be set")
        sys.exit(1)

    logger.info("Connecting to Supabase...")
    conn = psycopg2.connect(url)
    conn.autocommit = False

    # Set timezone to UTC to preserve MySQL TIMESTAMP semantics
    with conn.cursor() as cur:
        cur.execute("SET timezone = 'UTC';")
    conn.commit()

    logger.info("Supabase connection established (timezone=UTC)")
    return conn


# ============================================================================
# Schema creation
# ============================================================================


def create_schema(pg_conn: "psycopg2.extensions.connection", tables: list[str]) -> None:
    """Create PostgreSQL tables, indexes, and triggers."""
    with pg_conn.cursor() as cur:
        # Create trigger function first
        logger.info("Creating update_updated_at_column() trigger function")
        cur.execute(TRIGGER_FUNCTION)

        for table in tables:
            ddl = PG_DDL.get(table)
            if not ddl:
                logger.warning(f"No DDL for table: {table}")
                continue
            logger.info(f"Creating table: {table}")
            cur.execute(ddl)

            # Create updated_at trigger if applicable
            if table in TABLES_WITH_UPDATED_AT:
                trigger_sql = f"""
                    DROP TRIGGER IF EXISTS trigger_update_{table}_updated_at ON {table};
                    CREATE TRIGGER trigger_update_{table}_updated_at
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """
                cur.execute(trigger_sql)
                logger.info(f"  + updated_at trigger for {table}")

    pg_conn.commit()
    logger.info("Schema creation complete")


# ============================================================================
# Column discovery
# ============================================================================


def get_columns(aurora_conn: pymysql.Connection, table: str) -> list[str]:
    """Get column names for a table from Aurora INFORMATION_SCHEMA."""
    with aurora_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (table,),
        )
        return [row["COLUMN_NAME"] for row in cur.fetchall()]


# ============================================================================
# Row transformation
# ============================================================================


def transform_row(row: dict, table: str) -> dict:
    """Transform a MySQL row for PostgreSQL insertion.

    Handles: bytes→str, dict/list→Json, MySQL booleans, etc.
    """
    json_cols = JSON_COLUMNS.get(table, set())
    bool_cols = BOOL_COLUMNS.get(table, set())
    transformed = {}

    for key, value in row.items():
        if value is None:
            transformed[key] = None
        elif key in bool_cols:
            transformed[key] = bool(value)
        elif isinstance(value, bytes):
            transformed[key] = value.decode("utf-8")
        elif key in json_cols and isinstance(value, (dict, list)):
            transformed[key] = psycopg2.extras.Json(value)
        elif key in json_cols and isinstance(value, str):
            # MySQL sometimes returns JSON as string
            import json
            try:
                parsed = json.loads(value)
                transformed[key] = psycopg2.extras.Json(parsed)
            except (json.JSONDecodeError, TypeError):
                transformed[key] = value
        elif isinstance(value, Decimal):
            transformed[key] = value
        elif isinstance(value, (datetime, date)):
            transformed[key] = value
        elif isinstance(value, str) and value in ("0000-00-00", "0000-00-00 00:00:00"):
            transformed[key] = None
        else:
            transformed[key] = value

    return transformed


# ============================================================================
# Table migration
# ============================================================================


def migrate_table(
    table: str,
    aurora_conn: pymysql.Connection,
    pg_conn: "psycopg2.extensions.connection",
    dry_run: bool = False,
) -> int:
    """Migrate a single table from Aurora to Supabase.

    Returns number of rows migrated.
    """
    batch_size = BATCH_SIZES.get(table, 2000)
    columns = get_columns(aurora_conn, table)

    if not columns:
        logger.error(f"No columns found for table: {table}")
        return 0

    # Get source row count
    with aurora_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        source_count = cur.fetchone()["cnt"]

    logger.info(f"[{table}] Source rows: {source_count:,} | Batch size: {batch_size}")

    if dry_run:
        logger.info(f"[{table}] DRY RUN — skipping data transfer")
        return 0

    # Truncate target table
    with pg_conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
    pg_conn.commit()
    logger.info(f"[{table}] Target table truncated")

    # Build INSERT statement
    col_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = (
        f"INSERT INTO {table} ({col_list}) "
        f"OVERRIDING SYSTEM VALUE "
        f"VALUES %s"
    )

    total_migrated = 0
    offset = 0

    # Determine ORDER BY column (use 'id' if exists, else first column)
    order_col = "id" if "id" in columns else columns[0]

    while True:
        # Read batch from Aurora
        with aurora_conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {table} ORDER BY {order_col} LIMIT %s OFFSET %s",
                (batch_size, offset),
            )
            rows = cur.fetchall()

        if not rows:
            break

        # Transform rows
        values = []
        for row in rows:
            transformed = transform_row(row, table)
            values.append(tuple(transformed[col] for col in columns))

        # Insert batch into PostgreSQL
        with pg_conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                insert_sql,
                values,
                template=None,
                page_size=1000,
            )
        pg_conn.commit()

        total_migrated += len(rows)
        offset += batch_size
        logger.info(
            f"[{table}] Progress: {total_migrated:,}/{source_count:,} "
            f"({total_migrated * 100 // max(source_count, 1)}%)"
        )

    logger.info(f"[{table}] Migration complete: {total_migrated:,} rows")
    return total_migrated


# ============================================================================
# Post-migration
# ============================================================================


def reset_sequences(pg_conn: "psycopg2.extensions.connection", tables: list[str]) -> None:
    """Reset identity sequences to max(id) + 1 for all tables."""
    logger.info("Resetting identity sequences...")
    with pg_conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false);"
                )
                cur.execute(f"SELECT currval(pg_get_serial_sequence('{table}', 'id'));")
                val = cur.fetchone()[0]
                logger.info(f"  {table}: next id = {val}")
            except Exception as e:
                logger.warning(f"  {table}: sequence reset skipped ({e})")
                pg_conn.rollback()
                continue
    pg_conn.commit()


def add_foreign_keys(pg_conn: "psycopg2.extensions.connection") -> None:
    """Add FK constraints after data load."""
    logger.info("Adding foreign key constraints...")
    with pg_conn.cursor() as cur:
        for fk_sql in PG_FK_CONSTRAINTS:
            table_name = fk_sql.split("ADD CONSTRAINT")[0].split("TABLE")[-1].strip()
            try:
                cur.execute(fk_sql)
                logger.info(f"  + {fk_sql.split('ADD CONSTRAINT ')[1].split(' ')[0]}")
            except psycopg2.errors.DuplicateObject:
                logger.info(f"  ~ FK already exists on {table_name}")
                pg_conn.rollback()
                continue
    pg_conn.commit()


# ============================================================================
# Verification
# ============================================================================


def verify(
    aurora_conn: pymysql.Connection,
    pg_conn: "psycopg2.extensions.connection",
    tables: list[str],
) -> bool:
    """Compare row counts between Aurora and Supabase."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION: Row count comparison")
    logger.info("=" * 60)

    all_pass = True
    results = []

    for table in tables:
        # Aurora count
        with aurora_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
            aurora_count = cur.fetchone()["cnt"]

        # Supabase count
        with pg_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
            pg_count = cur.fetchone()[0]

        match = aurora_count == pg_count
        status = "PASS" if match else "FAIL"
        if not match:
            all_pass = False

        results.append((table, aurora_count, pg_count, status))

    # Print summary table
    logger.info(f"\n{'Table':<25} {'Aurora':>10} {'Supabase':>10} {'Status':>8}")
    logger.info("-" * 55)
    for table, ac, pc, status in results:
        logger.info(f"{table:<25} {ac:>10,} {pc:>10,} {status:>8}")
    logger.info("-" * 55)

    total_aurora = sum(r[1] for r in results)
    total_pg = sum(r[2] for r in results)
    logger.info(f"{'TOTAL':<25} {total_aurora:>10,} {total_pg:>10,}")

    # Spot-check: sample rows from ticker_master
    logger.info("\nSpot-check: ticker_master (first 5 rows)")
    with aurora_conn.cursor() as cur:
        cur.execute("SELECT id, company_name, exchange, is_active FROM ticker_master ORDER BY id LIMIT 5")
        aurora_rows = cur.fetchall()
    with pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, company_name, exchange, is_active FROM ticker_master ORDER BY id LIMIT 5")
        pg_rows = cur.fetchall()

    for i, (ar, pr) in enumerate(zip(aurora_rows, pg_rows)):
        aurora_active = bool(ar["is_active"])
        pg_active = pr["is_active"]
        match = ar["id"] == pr["id"] and ar["company_name"] == pr["company_name"] and aurora_active == pg_active
        logger.info(f"  Row {i+1}: id={ar['id']} name={ar['company_name']!r} — {'OK' if match else 'MISMATCH'}")

    # Spot-check: sample rows from daily_prices
    logger.info("\nSpot-check: daily_prices (first 5 rows)")
    with aurora_conn.cursor() as cur:
        cur.execute("SELECT id, symbol, price_date, close FROM daily_prices ORDER BY id LIMIT 5")
        aurora_rows = cur.fetchall()
    with pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, symbol, price_date, close FROM daily_prices ORDER BY id LIMIT 5")
        pg_rows = cur.fetchall()

    for i, (ar, pr) in enumerate(zip(aurora_rows, pg_rows)):
        aurora_close = float(ar["close"]) if ar["close"] else None
        pg_close = float(pr["close"]) if pr["close"] else None
        match = ar["id"] == pr["id"] and ar["symbol"] == pr["symbol"] and aurora_close == pg_close
        logger.info(
            f"  Row {i+1}: id={ar['id']} symbol={ar['symbol']} date={ar['price_date']} "
            f"close={ar['close']} — {'OK' if match else 'MISMATCH'}"
        )

    if all_pass:
        logger.info("\nAll tables PASS row count verification")
    else:
        logger.error("\nSome tables FAILED row count verification")

    return all_pass


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Aurora MySQL to Supabase PostgreSQL")
    parser.add_argument("--schema-only", action="store_true", help="Create schema only, no data")
    parser.add_argument("--verify-only", action="store_true", help="Verify row counts only")
    parser.add_argument("--dry-run", action="store_true", help="Connect and show plan, no changes")
    parser.add_argument("--table", type=str, help="Migrate a single table")
    parser.add_argument("--skip-schema", action="store_true", help="Skip schema creation")
    parser.add_argument("--skip-fk", action="store_true", help="Skip foreign key constraints")
    args = parser.parse_args()

    # Determine tables to process
    if args.table:
        if args.table not in TABLE_ORDER:
            logger.error(f"Unknown table: {args.table}. Valid: {TABLE_ORDER}")
            sys.exit(1)
        tables = [args.table]
    else:
        tables = TABLE_ORDER

    start_time = time.time()
    logger.info(f"Migration target: {len(tables)} table(s)")
    logger.info(f"Tables: {', '.join(tables)}")

    # Connect to both databases
    aurora_conn = connect_aurora()
    pg_conn = connect_supabase()

    try:
        if args.verify_only:
            verify(aurora_conn, pg_conn, tables)
            return

        if args.dry_run:
            logger.info("DRY RUN mode — validating connectivity and schema DDL")
            # Test Aurora
            with aurora_conn.cursor() as cur:
                cur.execute("SELECT 1")
            logger.info("Aurora: OK")
            # Test Supabase
            with pg_conn.cursor() as cur:
                cur.execute("SELECT 1")
            logger.info("Supabase: OK")
            # Show table row counts from Aurora
            for table in tables:
                with aurora_conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                    count = cur.fetchone()["cnt"]
                logger.info(f"  {table}: {count:,} rows")
            logger.info("DRY RUN complete — no changes made")
            return

        # Step 1: Create schema
        if not args.skip_schema:
            create_schema(pg_conn, tables)
        else:
            logger.info("Schema creation skipped (--skip-schema)")

        if args.schema_only:
            logger.info("Schema-only mode — done")
            return

        # Step 2: Migrate data
        logger.info("\n" + "=" * 60)
        logger.info("DATA MIGRATION")
        logger.info("=" * 60)

        total_rows = 0
        for table in tables:
            rows = migrate_table(table, aurora_conn, pg_conn, dry_run=False)
            total_rows += rows

        # Step 3: Post-migration
        logger.info("\n" + "=" * 60)
        logger.info("POST-MIGRATION")
        logger.info("=" * 60)

        reset_sequences(pg_conn, tables)

        if not args.skip_fk and not args.table:
            add_foreign_keys(pg_conn)
        elif args.table:
            logger.info("Single-table mode — skipping FK constraints")

        # Step 4: Verify
        verify(aurora_conn, pg_conn, tables)

        elapsed = time.time() - start_time
        logger.info(f"\nMigration complete: {total_rows:,} total rows in {elapsed:.1f}s")

    finally:
        aurora_conn.close()
        pg_conn.close()
        logger.info("Connections closed")


if __name__ == "__main__":
    main()
