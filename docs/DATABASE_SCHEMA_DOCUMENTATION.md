# Database Schema Documentation: Research Report

**Date:** 2025-12-29
**Goal:** Prevent semantic misinterpretation by embedding documentation IN the database schema
**Problem:** Date fields like `price_date` vs `fetched_at` require context to understand semantics
**Requirement:** Documentation must be queryable, maintainable, inline with schema, and MySQL/Aurora compatible

**Note (2025-12-30):** Examples in this document reference `ticker_info` table which was removed in migration 018. The documentation principles remain valid - examples show historical schema patterns. For current schema, see `db/migrations/` and use `ticker_master` instead.

---

## Executive Summary

**Recommendation: Hybrid Approach (Native COMMENT + Migration Documentation)**

Use MySQL native `COMMENT` syntax as the primary documentation mechanism, supplemented by migration file documentation and optional schema validation tooling. This provides the best balance of:
- **Queryability:** Direct database access via `INFORMATION_SCHEMA.COLUMNS`
- **Maintainability:** Version-controlled through migration files
- **Inline Storage:** Native database feature, no separate infrastructure
- **MySQL Compatibility:** Full Aurora MySQL support

**Implementation Priority:**
1. Add `COMMENT` to all date/timestamp columns in reconciliation migration (immediate value)
2. Establish comment conventions in migration templates
3. Optional: Implement schema validation script to verify comments exist

---

## Approach 1: MySQL COMMENT Syntax (Native Database Feature)

### Overview
MySQL provides native `COMMENT` syntax for both table-level and column-level documentation stored in the database's data dictionary.

### How It Works

**CREATE TABLE with Comments:**
```sql
CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    ticker_id INT NOT NULL COMMENT 'FK to ticker_info.id',
    symbol VARCHAR(20) NOT NULL COMMENT 'Stock symbol (e.g., AAPL.BK)',

    -- Date fields with semantic clarity
    price_date DATE NOT NULL COMMENT 'Trading date for this OHLCV data (NOT fetch date)',

    -- OHLCV data
    open DECIMAL(18, 6) COMMENT 'Opening price for trading date',
    close DECIMAL(18, 6) COMMENT 'Closing price for trading date',

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance' COMMENT 'Data source provider',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When this data was fetched from API',

    UNIQUE KEY uk_symbol_date (symbol, price_date)
) ENGINE=InnoDB COMMENT='Historical OHLCV price data indexed by trading date';
```

**ALTER TABLE to Add/Modify Comments:**
```sql
-- Add comment to existing column
ALTER TABLE daily_prices
MODIFY COLUMN price_date DATE NOT NULL
COMMENT 'Trading date for this OHLCV data (NOT fetch date)';

-- Add comment to existing table
ALTER TABLE daily_prices
COMMENT 'Historical OHLCV price data indexed by trading date';
```

**Query Comments Programmatically:**
```sql
-- Query all column comments for a table
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_NAME = 'daily_prices'
ORDER BY ORDINAL_POSITION;

-- Query table comments
SELECT
    TABLE_NAME,
    TABLE_COMMENT
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_NAME = 'daily_prices';
```

**View Comments:**
```sql
-- Show column details including comments
SHOW FULL COLUMNS FROM daily_prices;

-- Show table creation with all comments
SHOW CREATE TABLE daily_prices;
```

### Pros
- **Native Database Feature:** Built-in MySQL functionality, no external tools required
- **Queryable via INFORMATION_SCHEMA:** Standard SQL queries via `INFORMATION_SCHEMA.COLUMNS.COLUMN_COMMENT`
- **Visible in Standard Tools:** MySQL Workbench, CLI, and ORMs can display comments
- **Migration-Friendly:** Comments can be added via reconciliation migrations (idempotent)
- **No Additional Infrastructure:** No separate metadata tables or systems to maintain
- **AI/Developer Accessible:** Direct database queries retrieve semantic context
- **Version Control:** Comments defined in `.sql` migration files tracked by Git

### Cons
- **Limited Rich Text:** Plain text only, no markdown/HTML formatting
- **No Validation:** MySQL doesn't enforce comment existence or format
- **Migration Overhead:** Must explicitly add comments (not auto-generated)
- **Sparse Adoption:** Developers often skip writing comments (discipline required)
- **Single Language:** No multi-language support for internationalization

### MySQL/Aurora Compatibility
- **Fully Supported:** MySQL 5.7+, MySQL 8.0+, Aurora MySQL 2.x, Aurora MySQL 3.x
- **Standard SQL Syntax:** Works across all MySQL-compatible databases
- **Performance:** Zero performance impact (stored in data dictionary, not queried per row)

### Implementation Example for This Project

**Reconciliation Migration (Immediate Fix):**
```sql
-- File: db/migrations/013_add_semantic_comments.sql
-- Purpose: Add comments to prevent date field misinterpretation
-- Type: Reconciliation (idempotent)

USE ticker_data;

-- Add semantic clarity to daily_prices date columns
ALTER TABLE daily_prices
MODIFY COLUMN price_date DATE NOT NULL
COMMENT 'Trading date for this OHLCV data (NOT fetch date)';

ALTER TABLE daily_prices
MODIFY COLUMN fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
COMMENT 'When this data was fetched from external API';

-- Add semantic clarity to fund_data
ALTER TABLE fund_data
MODIFY COLUMN d_trade DATE NOT NULL
COMMENT 'Trading date from source system (business date)';

ALTER TABLE fund_data
MODIFY COLUMN synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
COMMENT 'When data was synced from S3 to Aurora';

-- Add semantic clarity to precomputed_reports
ALTER TABLE precomputed_reports
MODIFY COLUMN report_date DATE NOT NULL
COMMENT 'Trading date this report analyzes (NOT creation date)';

ALTER TABLE precomputed_reports
MODIFY COLUMN computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
COMMENT 'When this report was generated';

-- Verify comments were added
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND COLUMN_COMMENT != ''
  AND COLUMN_NAME LIKE '%date%'
   OR COLUMN_NAME LIKE '%_at'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

**Query Script for Schema Documentation:**
```python
# File: scripts/query_schema_comments.py
"""Query all table and column comments for documentation generation."""

from src.data.aurora.client import get_aurora_client

def get_schema_comments():
    """Retrieve all comments from database schema."""
    client = get_aurora_client()

    # Query all column comments
    query = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE,
            COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND COLUMN_COMMENT != ''
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """

    columns = client.fetch_all(query, ())

    # Query all table comments
    table_query = """
        SELECT
            TABLE_NAME,
            TABLE_COMMENT
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_COMMENT != ''
        ORDER BY TABLE_NAME
    """

    tables = client.fetch_all(table_query, ())

    return {'columns': columns, 'tables': tables}

if __name__ == "__main__":
    schema_docs = get_schema_comments()

    print("\n=== TABLE COMMENTS ===")
    for table in schema_docs['tables']:
        print(f"\n{table['TABLE_NAME']}: {table['TABLE_COMMENT']}")

    print("\n=== COLUMN COMMENTS ===")
    for col in schema_docs['columns']:
        print(f"\n{col['TABLE_NAME']}.{col['COLUMN_NAME']} ({col['COLUMN_TYPE']})")
        print(f"  → {col['COLUMN_COMMENT']}")
```

---

## Approach 2: Schema Documentation Tools

### Overview
External tools that generate documentation from database schema, often with enhanced features beyond native comments.

### Tools Evaluated

#### Dataedo
- **Purpose:** Advanced database documentation tool
- **Features:** Creates HTML/PDF/Excel docs, supports MySQL/Aurora
- **Pricing:** Commercial ($499-$999/year)
- **Pros:** Rich formatting, version history, collaboration features
- **Cons:** External dependency, cost, requires separate infrastructure

#### DbSchema
- **Purpose:** Database design and documentation tool
- **Features:** Visual schema diagrams, 15+ years of development
- **Pricing:** Commercial ($127-$297 one-time)
- **Pros:** Visual diagrams, offline mode, extensive database support
- **Cons:** Desktop application, not integrated with codebase

#### MySQL Workbench
- **Purpose:** Official MySQL database tool
- **Features:** Free, tightly integrated with MySQL ecosystem
- **Pros:** Free, official Oracle tool, native comment support
- **Cons:** Desktop GUI only, no programmatic access

### Pros
- **Rich Formatting:** Support markdown, HTML, embedded images
- **Visual Diagrams:** Auto-generate ER diagrams, data flow diagrams
- **Collaboration Features:** Review workflows, approval processes
- **Version History:** Track documentation changes over time
- **Multi-Language Support:** Internationalization for global teams

### Cons
- **External Dependency:** Requires separate tool installation/licensing
- **Synchronization Risk:** Documentation can drift from actual schema
- **Cost:** Commercial tools require budget allocation
- **Infrastructure Overhead:** Hosting, maintenance, user access management
- **Not Code-Integrated:** Separate from version control system

### MySQL/Aurora Compatibility
- Most tools support MySQL/Aurora via JDBC/ODBC
- Some tools can read native MySQL comments and enhance them
- Typically require read-only database access for schema reflection

### Implementation Recommendation
**Suitable for:** Large teams with documentation compliance requirements (SOC 2, HIPAA)
**Not recommended for this project:** Overhead exceeds benefit for 11-table schema

---

## Approach 3: Schema Metadata Tables (Custom Solution)

### Overview
Create dedicated metadata tables to store table/column descriptions separate from native comments.

### Schema Design Example

```sql
-- Table to store table-level documentation
CREATE TABLE IF NOT EXISTS _schema_table_docs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    purpose TEXT,
    owner VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_table_name (table_name)
) ENGINE=InnoDB COMMENT='Metadata: Table-level documentation';

-- Table to store column-level documentation
CREATE TABLE IF NOT EXISTS _schema_column_docs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(64) NOT NULL,
    column_name VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    semantic_type VARCHAR(50),  -- e.g., 'trading_date', 'fetch_timestamp'
    data_source VARCHAR(100),   -- e.g., 'yfinance API', 'SQL Server sync'

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_table_column (table_name, column_name),
    INDEX idx_semantic_type (semantic_type)
) ENGINE=InnoDB COMMENT='Metadata: Column-level documentation';

-- Insert example documentation
INSERT INTO _schema_column_docs
(table_name, column_name, description, semantic_type, data_source)
VALUES
('daily_prices', 'price_date',
 'Trading date for this OHLCV data (NOT when data was fetched)',
 'trading_date', 'yfinance API'),

('daily_prices', 'fetched_at',
 'Timestamp when this data was fetched from external API',
 'fetch_timestamp', 'system_generated');

-- Query documentation
SELECT
    c.COLUMN_NAME,
    c.DATA_TYPE,
    d.description,
    d.semantic_type,
    d.data_source
FROM INFORMATION_SCHEMA.COLUMNS c
LEFT JOIN _schema_column_docs d
    ON c.TABLE_NAME = d.table_name
   AND c.COLUMN_NAME = d.column_name
WHERE c.TABLE_SCHEMA = 'ticker_data'
  AND c.TABLE_NAME = 'daily_prices'
ORDER BY c.ORDINAL_POSITION;
```

### Pros
- **Rich Metadata:** Store additional fields (owner, semantic_type, data_source)
- **Queryable with Joins:** Combine with INFORMATION_SCHEMA for comprehensive views
- **Programmatic Updates:** Can be updated via application code
- **Extensible Schema:** Add new metadata fields as needed (tags, examples, constraints)
- **Search Capabilities:** Full-text search on descriptions

### Cons
- **Manual Synchronization:** Must keep metadata tables in sync with schema changes
- **Migration Complexity:** Two migrations for schema changes (table + metadata)
- **Storage Overhead:** Additional tables consume database resources
- **Orphaned Records Risk:** Deleted columns leave stale metadata
- **Developer Discipline:** Requires team to update metadata tables consistently

### MySQL/Aurora Compatibility
- Fully compatible (standard MySQL tables)
- Can use triggers to detect schema changes (advanced pattern)

### Implementation Recommendation
**Suitable for:** Data warehouses with hundreds of tables requiring rich metadata (lineage, PII classification)
**Not recommended for this project:** Overhead too high for 11-table OLTP schema

---

## Approach 4: Code-First Schema Documentation

### Overview
Document schema in ORM models or migration files, then sync to database.

### ORM Model Documentation (SQLAlchemy)

```python
# File: src/data/models/daily_prices.py
from sqlalchemy import Column, Integer, String, Date, DECIMAL, TIMESTAMP, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DailyPrice(Base):
    """Historical OHLCV price data indexed by trading date.

    This table stores daily price data fetched from external APIs (yfinance).
    Key semantic distinction: price_date is the TRADING DATE (business date),
    while fetched_at is the SYSTEM TIMESTAMP when data was retrieved.
    """

    __tablename__ = 'daily_prices'
    __table_args__ = {
        'comment': 'Historical OHLCV price data indexed by trading date'
    }

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment='Synthetic primary key'
    )

    ticker_id = Column(
        Integer,
        nullable=False,
        comment='Foreign key to ticker_info.id'
    )

    symbol = Column(
        String(20),
        nullable=False,
        comment='Stock symbol (e.g., AAPL.BK)'
    )

    price_date = Column(
        Date,
        nullable=False,
        comment='Trading date for this OHLCV data (NOT fetch date)'
    )

    open = Column(
        DECIMAL(18, 6),
        comment='Opening price for trading date'
    )

    close = Column(
        DECIMAL(18, 6),
        comment='Closing price for trading date'
    )

    fetched_at = Column(
        TIMESTAMP,
        server_default='CURRENT_TIMESTAMP',
        comment='When this data was fetched from external API'
    )
```

**Generate Migration with Comments:**
```bash
# Alembic autogenerate will detect column comments
alembic revision --autogenerate -m "add_column_comments"
```

**Alembic Migration File:**
```python
# File: alembic/versions/xxx_add_column_comments.py
def upgrade():
    # Alembic generates ALTER TABLE statements with comments
    op.alter_column('daily_prices', 'price_date',
                    existing_type=sa.Date(),
                    comment='Trading date for this OHLCV data (NOT fetch date)',
                    existing_nullable=False)

    op.alter_column('daily_prices', 'fetched_at',
                    existing_type=sa.TIMESTAMP(),
                    comment='When this data was fetched from external API',
                    server_default='CURRENT_TIMESTAMP')
```

### Migration File Documentation

```sql
-- File: db/migrations/004_create_daily_prices.sql
-- ============================================================================
-- Migration: 004_create_daily_prices.sql
-- Type: CREATE
-- Purpose: Create daily_prices table with historical OHLCV data
-- Created: 2025-12-12
-- ============================================================================
--
-- SEMANTIC DOCUMENTATION:
-- - price_date: Trading date (business date) - represents the day this price applies to
-- - fetched_at: System timestamp - when we retrieved this data from yfinance API
-- - source: Data provider identifier (e.g., 'yfinance', 'alpha_vantage')
--
-- PRE-CONDITION:
-- - ticker_info table exists with id column (FK target)
--
-- POST-CONDITION:
-- - daily_prices table exists with historical OHLCV data
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Foreign keys
    ticker_id INT NOT NULL COMMENT 'FK to ticker_info.id',
    symbol VARCHAR(20) NOT NULL COMMENT 'Stock symbol (e.g., AAPL.BK)',

    -- Trading date (business date, NOT system timestamp)
    price_date DATE NOT NULL COMMENT 'Trading date for this OHLCV data (NOT fetch date)',

    -- OHLCV data
    open DECIMAL(18, 6) COMMENT 'Opening price for trading date',
    high DECIMAL(18, 6) COMMENT 'High price for trading date',
    low DECIMAL(18, 6) COMMENT 'Low price for trading date',
    close DECIMAL(18, 6) COMMENT 'Closing price for trading date',
    adj_close DECIMAL(18, 6) COMMENT 'Adjusted closing price accounting for splits/dividends',
    volume BIGINT COMMENT 'Trading volume for the day',

    -- Calculated fields
    daily_return DECIMAL(10, 6) COMMENT 'Daily return percentage (close vs previous close)',

    -- Metadata
    source VARCHAR(50) DEFAULT 'yfinance' COMMENT 'Data source provider',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When this data was fetched from external API',

    -- Constraints
    UNIQUE KEY uk_symbol_date (symbol, price_date),

    -- Indexes
    INDEX idx_daily_prices_symbol (symbol),
    INDEX idx_daily_prices_date (price_date),
    INDEX idx_daily_prices_symbol_date (symbol, price_date DESC)
) ENGINE=InnoDB COMMENT='Historical OHLCV price data indexed by trading date';
```

### Pros
- **Version Controlled:** Documentation lives in migration files (Git tracked)
- **Single Source of Truth:** Schema definition includes documentation
- **ORM Integration:** SQLAlchemy models document schema for developers
- **Alembic Autogenerate:** Can detect comment changes and generate migrations
- **Code Review Process:** Documentation reviewed alongside schema changes

### Cons
- **Requires ORM Adoption:** Project currently uses raw SQL (no SQLAlchemy models)
- **Migration Overhead:** Every comment change requires migration file
- **Sync Challenges:** Must ensure migration comments match database reality
- **Limited Queryability:** Comments in files aren't queryable at runtime (unless synced to DB)

### MySQL/Aurora Compatibility
- SQLAlchemy 1.2+ supports column/table comments for MySQL
- Alembic can autogenerate comment changes (with configuration)
- Comments stored in database via DDL statements

### Implementation Recommendation
**Suitable for:** Projects using ORM (SQLAlchemy, Django ORM) with CI/CD autogenerate
**Moderate fit for this project:** Would require adopting SQLAlchemy models (future consideration)

---

## Approach 5: Real-World Patterns from Production Systems

### Pattern 1: Hybrid Approach (Native Comments + Migration Headers)

**Used by:** Large e-commerce platforms, financial institutions

```sql
-- Migration file header (Git-tracked documentation)
-- ============================================================================
-- Purpose: Daily price data for technical analysis
-- Semantic Model:
--   - price_date: Trading date (T) - the business day this price represents
--   - fetched_at: Fetch timestamp (T+N) - when we retrieved data from API
--   - source: Data provider (yfinance, alpha_vantage, refinitiv)
-- Data Lineage:
--   yfinance API -> S3 staging -> Aurora daily_prices table
-- ============================================================================

CREATE TABLE daily_prices (
    price_date DATE NOT NULL COMMENT 'Trading date (T) - business date for this price',
    fetched_at TIMESTAMP COMMENT 'Fetch timestamp (T+N) - when data retrieved from API'
) COMMENT='OHLCV price data keyed by trading date';
```

**Why it works:**
- Migration header provides detailed context (lineage, semantic model)
- Native comments provide quick reference at database level
- Both are version controlled and reviewed

### Pattern 2: Data Dictionary + Native Comments

**Used by:** Data warehouses, analytics platforms

- **Native Comments:** Short descriptions (50-100 chars)
- **Data Dictionary Table:** Extended metadata (PII classification, retention policy, SLA)
- **Documentation Portal:** Searchable UI powered by data dictionary table

**Example:**
```sql
-- Short comment in database
ALTER TABLE user_events
MODIFY COLUMN event_timestamp TIMESTAMP
COMMENT 'Event occurrence time (user timezone)';

-- Extended metadata in dictionary table
INSERT INTO data_dictionary VALUES (
    'user_events',
    'event_timestamp',
    'Timestamp when user event occurred in their local timezone. Used for user activity analysis. PII: No. Retention: 2 years. SLA: 99.9% accuracy within 1 second.'
);
```

### Pattern 3: Schema Validation CI/CD

**Used by:** Regulated industries (finance, healthcare)

- **Required Comments:** CI/CD fails if certain columns lack comments
- **Comment Conventions:** Enforced patterns (e.g., all date columns must explain if trading/system date)
- **Automated Auditing:** Weekly reports of uncommented columns

**Example CI/CD Check:**
```python
# File: scripts/validate_schema_comments.py
"""CI/CD check: Ensure critical columns have comments."""

REQUIRED_COMMENT_PATTERNS = {
    'date': ['date', 'day'],
    'timestamp': ['when', 'time'],
    'datetime': ['when', 'occurred', 'created']
}

def validate_comments():
    """Check that date/timestamp columns have semantic comments."""
    query = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND DATA_TYPE IN ('date', 'timestamp', 'datetime')
          AND (COLUMN_COMMENT IS NULL OR COLUMN_COMMENT = '')
    """

    results = client.fetch_all(query)

    if results:
        print("ERROR: Found date/timestamp columns without comments:")
        for row in results:
            print(f"  {row['TABLE_NAME']}.{row['COLUMN_NAME']} ({row['DATA_TYPE']})")
        sys.exit(1)

    print("✅ All date/timestamp columns have comments")
```

---

## Ranked Recommendations

### Tier 1: Immediate Implementation (High Value, Low Cost)

**1. Add Native COMMENT to Date/Timestamp Columns**

**Implementation:**
```sql
-- File: db/migrations/013_add_semantic_comments.sql
-- Reconciliation migration (idempotent)

ALTER TABLE daily_prices
MODIFY COLUMN price_date DATE NOT NULL
COMMENT 'Trading date for this OHLCV data (NOT fetch date)';

ALTER TABLE daily_prices
MODIFY COLUMN fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
COMMENT 'When this data was fetched from external API';

-- Repeat for all tables with ambiguous date fields
```

**Benefits:**
- Immediate semantic clarity for AI and developers
- Zero infrastructure cost (native MySQL feature)
- Queryable via INFORMATION_SCHEMA
- Version controlled via migration files

**Effort:** 1-2 hours to add comments to all date columns across 11 tables

---

### Tier 2: Medium-Term Enhancement (Medium Value, Medium Cost)

**2. Establish Comment Conventions in Migration Templates**

**Implementation:**
- Update migration file template to include comment checklist
- Add comment examples to database-migration skill
- Document convention in PROJECT_CONVENTIONS.md

**Template Example:**
```sql
-- ============================================================================
-- Migration: NNN_description.sql
-- Type: CREATE | ALTER | RECONCILE
-- Purpose: [Why this change exists]
-- ============================================================================
--
-- SEMANTIC DOCUMENTATION:
-- [ ] All date/timestamp columns have comments explaining trading vs system time
-- [ ] All FK columns comment target table
-- [ ] All ENUM columns comment allowed values
-- [ ] Table comment describes purpose and key semantic model
--
-- PRE-CONDITION:
-- POST-CONDITION:
-- VERIFICATION:
-- ============================================================================
```

**Benefits:**
- Prevents future semantic ambiguity
- Self-documenting migrations
- Review checklist for PRs

**Effort:** 2-3 hours to create template and update documentation

---

**3. Optional: Schema Validation Script**

**Implementation:**
```python
# File: scripts/validate_schema_comments.py
"""Validate that critical columns have semantic comments."""

def validate_date_comments():
    """Ensure all date/timestamp columns have comments."""
    query = """
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND DATA_TYPE IN ('date', 'timestamp', 'datetime')
          AND (COLUMN_COMMENT IS NULL OR COLUMN_COMMENT = '')
    """
    # ... validation logic
```

**Benefits:**
- Automated enforcement of documentation standards
- CI/CD integration prevents uncommented columns
- Living documentation (always current)

**Effort:** 3-4 hours to implement and integrate with CI/CD

---

### Tier 3: Future Consideration (Low Priority)

**4. SQLAlchemy Model Adoption** (if migrating from raw SQL to ORM)

**5. External Documentation Tools** (if team grows to 10+ developers)

**6. Schema Metadata Tables** (if building data catalog/governance platform)

---

## Implementation Checklist

### Phase 1: Immediate Value (Week 1)
- [ ] Create reconciliation migration `013_add_semantic_comments.sql`
- [ ] Add COMMENT to all date/timestamp columns (priority: `price_date`, `fetched_at`, `d_trade`, `synced_at`)
- [ ] Add COMMENT to ambiguous FK columns (`ticker_id`, `ticker_master_id`)
- [ ] Add table-level COMMENT to all 11 tables
- [ ] Test migration locally via Aurora tunnel
- [ ] Deploy to dev environment
- [ ] Verify comments queryable via `SHOW FULL COLUMNS` and INFORMATION_SCHEMA

### Phase 2: Conventions (Week 2)
- [ ] Create migration template with comment checklist
- [ ] Update `.claude/skills/database-migration/SKILL.md` with comment examples
- [ ] Add comment conventions to `docs/DATABASE_MIGRATIONS.md`
- [ ] Document INFORMATION_SCHEMA query patterns for retrieving comments

### Phase 3: Validation (Week 3, Optional)
- [ ] Implement `scripts/validate_schema_comments.py`
- [ ] Add GitHub Actions workflow to run validation on PRs
- [ ] Create weekly report of uncommented columns

---

## Example Queries for Developers/AI

### Query All Table Comments
```sql
SELECT
    TABLE_NAME,
    TABLE_COMMENT,
    TABLE_ROWS
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_COMMENT != ''
ORDER BY TABLE_NAME;
```

### Query All Column Comments for a Table
```sql
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND TABLE_NAME = 'daily_prices'
  AND COLUMN_COMMENT != ''
ORDER BY ORDINAL_POSITION;
```

### Find All Date Columns with Comments
```sql
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'ticker_data'
  AND DATA_TYPE IN ('date', 'timestamp', 'datetime')
  AND COLUMN_COMMENT != ''
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

### Generate Schema Documentation Report
```sql
SELECT
    c.TABLE_NAME,
    c.COLUMN_NAME,
    c.DATA_TYPE,
    c.COLUMN_TYPE,
    c.IS_NULLABLE,
    c.COLUMN_KEY,
    c.COLUMN_COMMENT,
    t.TABLE_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS c
JOIN INFORMATION_SCHEMA.TABLES t
    ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
   AND c.TABLE_NAME = t.TABLE_NAME
WHERE c.TABLE_SCHEMA = 'ticker_data'
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
```

---

## References

### MySQL Documentation
- [MySQL 8.0 Reference Manual - Comments](https://dev.mysql.com/doc/refman/8.0/en/comments.html)
- [MySQL 8.0 INFORMATION_SCHEMA COLUMNS Table](https://dev.mysql.com/doc/refman/8.0/en/information-schema-columns-table.html)
- [MySQL CREATE TABLE Statement](https://dev.mysql.com/doc/refman/8.0/en/create-table.html)
- [MySQL ALTER TABLE Statement](https://dev.mysql.com/doc/refman/8.0/en/alter-table.html)

### SQLAlchemy
- [Schema Definition Language - SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/core/schema.html)
- [MetaData / Schema - SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/faq/metadata_schema.html)

### Database Documentation Tools
- [7 Best Database Documentation Tools for 2025](https://www.comparitech.com/net-admin/best-database-documentation-tools/)
- [How to Document a MySQL Database Schema in 2025](https://dbschema.com/blog/mysql/database-documentation/)
- [Best MySQL Database Design Tools in 2025](https://dbschema.com/blog/mysql/best-database-design-tools-mysql/)

### Best Practices
- [What are the most common techniques for documenting database schema?](https://www.linkedin.com/advice/3/what-most-common-techniques-documenting-database-vaphc)
- [Why It Is More Important to Document Database Than Application Code](https://dataedo.com/blog/why-it-is-more-important-to-document-database-than-application-code)
- [8 database management best practices to know in 2025](https://www.instaclustr.com/education/data-architecture/8-database-management-best-practices-to-know-in-2025/)
- [Data Dictionary for Database Documentation: Pros and Cons](https://www.linkedin.com/advice/1/what-benefits-drawbacks-using-data-dictionary-database)

### Metadata Standards
- [What is Metadata: Examples, Benefits, and Best Practices](https://lakefs.io/blog/what-is-metadata/)
- [Semantic Metadata - ScienceDirect Topics](https://www.sciencedirect.com/topics/computer-science/semantic-metadata)

### Alembic
- [Auto Generating Migrations - Alembic 1.17.2](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Support Comments on Table / Columns - Issue #422](https://github.com/sqlalchemy/alembic/issues/422)

---

## Conclusion

**Primary Recommendation: Native MySQL COMMENT**

For this project (11 tables, 3-person team, OLTP workload), native MySQL `COMMENT` syntax provides the optimal balance of:
- **Immediate value:** Prevents semantic misinterpretation now
- **Low overhead:** No new infrastructure or tools required
- **High maintainability:** Version-controlled via migration files
- **Developer friendly:** Queryable via standard SQL, visible in all tools
- **AI accessible:** Direct database queries retrieve semantic context

The hybrid approach (native comments + migration file documentation) mirrors production patterns from large-scale systems while remaining lightweight enough for this project's scale.

**Next Steps:**
1. Create reconciliation migration adding comments to all date/timestamp columns
2. Establish comment conventions in migration templates
3. Optional: Implement validation script for CI/CD enforcement
