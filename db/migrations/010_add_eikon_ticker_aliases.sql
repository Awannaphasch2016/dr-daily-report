-- Migration: Add Eikon symbol mappings from fund_data
-- Purpose: Enable Yahoo ↔ Eikon translation via DR symbol common key
--
-- Background:
--   - tickers.csv has DR ↔ Yahoo mappings (DBS19 ↔ D05.SI)
--   - fund_data has DR ↔ Eikon mappings (DBS19 ↔ DBSM.SI via stock/ticker columns)
--   - Problem: D05.SI (Yahoo) ≠ DBSM.SI (Eikon) for some tickers
--   - Solution: Add Eikon symbols to ticker_aliases for Yahoo → DR → Eikon translation
--
-- Expected outcome:
--   - 39 new ticker_aliases rows with symbol_type='eikon'
--   - Coverage increases from 16/92 (17%) to 39/92 (42%)

-- Step 0: Add 'eikon' to symbol_type ENUM (required before inserting eikon aliases)
ALTER TABLE ticker_aliases
MODIFY COLUMN symbol_type ENUM('dr','yahoo','bloomberg','other','eikon') NOT NULL;

-- Step 1: Populate ticker_master from fund_data (if not exists)
-- Use fund_data.stock (DR format) to find/create ticker_master entries
INSERT INTO ticker_master (company_name, exchange, is_active)
SELECT DISTINCT
    fd.stock as company_name,  -- Temporary: use DR symbol as company name
    CASE
        WHEN fd.ticker LIKE '%.SI' THEN 'SGX'
        WHEN fd.ticker LIKE '%.T' THEN 'TSE'
        WHEN fd.ticker LIKE '%.HK' THEN 'HKEX'
        WHEN fd.ticker LIKE '%.VN' THEN 'HOSE'
        WHEN fd.ticker LIKE '%.HM' THEN 'HOSE'
        ELSE 'UNKNOWN'
    END as exchange,
    TRUE as is_active
FROM fund_data fd
WHERE NOT EXISTS (
    SELECT 1 FROM ticker_aliases ta
    WHERE ta.symbol = fd.stock AND ta.symbol_type = 'dr'
)
GROUP BY fd.stock;

-- Step 2: Get ticker_id for each DR symbol from ticker_aliases
-- Then insert Eikon symbols
INSERT INTO ticker_aliases (ticker_id, symbol, symbol_type, is_primary)
SELECT DISTINCT
    ta_dr.ticker_id,           -- Get ticker_id from existing DR alias
    fd.ticker as symbol,       -- Eikon symbol (DBSM.SI)
    'eikon' as symbol_type,
    FALSE as is_primary        -- Yahoo is primary for most cases
FROM fund_data fd
JOIN ticker_aliases ta_dr ON ta_dr.symbol = fd.stock AND ta_dr.symbol_type = 'dr'
WHERE NOT EXISTS (
    SELECT 1 FROM ticker_aliases ta2
    WHERE ta2.ticker_id = ta_dr.ticker_id
    AND ta2.symbol = fd.ticker
    AND ta2.symbol_type = 'eikon'
)
GROUP BY ta_dr.ticker_id, fd.ticker
ON DUPLICATE KEY UPDATE
    ticker_id = VALUES(ticker_id),
    symbol_type = VALUES(symbol_type),
    is_primary = VALUES(is_primary);

-- Step 3: Verify insertion
SELECT
    COUNT(DISTINCT ticker_id) as tickers_with_eikon,
    COUNT(*) as total_eikon_aliases
FROM ticker_aliases
WHERE symbol_type = 'eikon';

-- Expected: ~39 tickers, 39 eikon aliases

-- Step 4: Verify Yahoo → Eikon mapping works
SELECT
    yahoo.symbol as yahoo_symbol,
    dr.symbol as dr_symbol,
    eikon.symbol as eikon_symbol,
    tm.company_name
FROM ticker_aliases yahoo
JOIN ticker_master tm ON yahoo.ticker_id = tm.id
JOIN ticker_aliases dr ON dr.ticker_id = tm.id AND dr.symbol_type = 'dr'
LEFT JOIN ticker_aliases eikon ON eikon.ticker_id = tm.id AND eikon.symbol_type = 'eikon'
WHERE yahoo.symbol_type = 'yahoo'
AND yahoo.symbol IN ('D05.SI', '7974.T', '8316.T')
ORDER BY yahoo.symbol
LIMIT 5;

-- Expected result:
-- yahoo_symbol | dr_symbol    | eikon_symbol | company_name
-- D05.SI       | DBS19        | DBSM.SI      | DBS Group Holdings
-- 7974.T       | NINTENDO19   | 7974.T       | Nintendo
-- 8316.T       | SMFG19       | 8316.T       | Sumitomo Mitsui Financial Group
