# S3 Data Lake Phase 2 Implementation Plan

## Overview

**Phase 1 Status**: ✅ Complete - Raw yfinance data staging with versioning, tagging, and lifecycle policies

**Phase 2 Goal**: Store processed/transformed data (indicators, percentiles, computed features) alongside raw data for complete data lineage and reprocessing capabilities.

---

## Phase 2 Objectives

### 1. Processed Data Storage
Store computed indicators and percentiles to S3 Data Lake for:
- **Reprocessing**: Recompute indicators from raw data if logic changes
- **Audit Trail**: Track what indicators were computed from which raw data version
- **Data Lineage**: Link processed data back to source raw data via S3 tags/metadata

### 2. Data Structure
```
s3://bucket/
├── raw/yfinance/{ticker}/{date}/{timestamp}.json          # Phase 1 ✅
└── processed/
    ├── indicators/{ticker}/{date}/{timestamp}.json        # Phase 2
    ├── percentiles/{ticker}/{date}/{timestamp}.json       # Phase 2
    └── features/{ticker}/{date}/{timestamp}.json          # Phase 2 (future)
```

### 3. Key Features
- **Versioning**: Each computation creates new version (immutable)
- **Tagging**: Link processed data to source raw data version
- **Metadata**: Store computation metadata (timestamp, version, source S3 key)
- **Lifecycle**: Same lifecycle policies as raw data (90d → Glacier, 365d → Deep Archive)

---

## Implementation Steps

### Step 1: Extend DataLakeStorage Module
**File**: `src/data/data_lake.py`

Add methods for storing processed data:
- `store_indicators()` - Store computed indicators
- `store_percentiles()` - Store computed percentiles
- `store_features()` - Store comparative features (future)

**Key Structure**:
```python
# Processed indicators
s3_key = f"processed/indicators/{ticker}/{date}/{timestamp}.json"

# Tags linking to source raw data
tags = {
    'source': 'computed',
    'ticker': ticker,
    'computed_at': date_str,
    'source_raw_data': 'raw/yfinance/{ticker}/{date}/{raw_timestamp}.json'  # Link to source
}

# Metadata
metadata = {
    'computed_at': timestamp_str,
    'source': 'indicators_computation',
    'ticker': ticker,
    'source_raw_data_key': 'raw/yfinance/...',  # Full S3 key to source
    'computation_version': '1.0',  # Version of computation logic
    'data_classification': 'computed-data'
}
```

### Step 2: Update Indicator Computation
**File**: `src/analysis/technical_analysis.py` or `src/data/aurora/precompute_service.py`

After computing indicators/percentiles:
1. Store to Aurora (existing)
2. Store to S3 Data Lake (new) - for lineage and reprocessing

**Pattern**:
```python
# Compute indicators
indicators = calculate_indicators(ticker_data)

# Store to Aurora (existing)
aurora_repo.store_indicators(ticker, indicators)

# Store to Data Lake (Phase 2)
data_lake.store_indicators(
    ticker=ticker,
    indicators=indicators,
    source_raw_data_key='raw/yfinance/NVDA/2025-01-15/20250115_120000.json',
    computed_at=datetime.now()
)
```

### Step 3: Add Retrieval Methods
**File**: `src/data/data_lake.py`

Add methods to retrieve processed data:
- `get_latest_indicators()` - Get most recent indicators for a ticker
- `get_indicators_by_date()` - Get indicators for specific date
- `get_indicators_by_version()` - Get specific version (for reprocessing)

### Step 4: Update Terraform (if needed)
**File**: `terraform/modules/s3-data-lake/main.tf`

Lifecycle policy for `processed/` prefix already exists (lines 97-113), so no changes needed.

---

## Data Lineage Tracking

### Tag Structure
```json
{
  "source": "computed",
  "ticker": "NVDA",
  "computed_at": "2025-01-15",
  "source_raw_data": "raw/yfinance/NVDA/2025-01-15/20250115_120000.json",
  "computation_version": "1.0",
  "computation_type": "indicators"
}
```

### Metadata Structure
```json
{
  "computed_at": "2025-01-15T12:30:00Z",
  "source": "indicators_computation",
  "ticker": "NVDA",
  "source_raw_data_key": "raw/yfinance/NVDA/2025-01-15/20250115_120000.json",
  "computation_version": "1.0",
  "data_classification": "computed-data",
  "indicators_computed": ["sma_20", "sma_50", "rsi_14", "macd", "bb_upper", "bb_lower"]
}
```

---

## Testing Checklist

- [ ] Store indicators to data lake after computation
- [ ] Store percentiles to data lake after computation
- [ ] Tags link processed data to source raw data
- [ ] Metadata contains computation version and source key
- [ ] Multiple computations create multiple versions (versioning)
- [ ] Retrieval methods work correctly
- [ ] Lifecycle policies apply to processed data
- [ ] Data lake storage failure doesn't break Aurora storage

---

## Success Criteria

✅ Processed indicators stored to S3 Data Lake with proper structure
✅ Processed percentiles stored to S3 Data Lake with proper structure
✅ Tags enable data lineage tracking (processed → raw)
✅ Metadata enables reprocessing (know which raw data was used)
✅ Versioning enables historical access to all computations
✅ Integration doesn't break existing Aurora storage
✅ All tests pass

---

## Future Phases

**Phase 3**: Query/Retrieval API
- Athena integration for SQL queries over S3 data
- Glue catalog for schema discovery
- API endpoints to query data lake

**Phase 4**: Data Quality Validation
- Schema validation before storage
- Data quality checks (completeness, accuracy)
- Automated alerts on data quality issues

---

## References

- Phase 1 Implementation: `src/data/data_lake.py`
- Terraform Module: `terraform/modules/s3-data-lake/main.tf`
- Lifecycle Policies: Already configured for `processed/` prefix
- Indicator Computation: `src/analysis/technical_analysis.py`
- Precompute Service: `src/data/aurora/precompute_service.py`
