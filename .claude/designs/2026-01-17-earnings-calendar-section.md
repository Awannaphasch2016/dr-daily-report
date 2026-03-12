# Design: Earnings Calendar Context Section (P3)

**Status**: Design Only (awaiting data source decision)
**Priority**: P3
**Created**: 2026-01-17

---

## Problem Statement

DR reports lack earnings calendar awareness. Reports generated near earnings dates should:
1. Acknowledge upcoming earnings event
2. Adjust volatility expectations
3. Warn about event-driven risk

---

## Proposed Solution

### New Context Section

```
=== EARNINGS CALENDAR ===
Next Earnings Date: {{NEXT_EARNINGS_DATE}}
Days Until: {{EARNINGS_DAYS_UNTIL}}
Historical Avg Surprise: {{EARNINGS_SURPRISE_AVG}}%

Guidance: Earnings within 14 days significantly impacts volatility expectations.
```

### Data Required

| Field | Type | Source |
|-------|------|--------|
| `next_earnings_date` | date | External API |
| `days_until_earnings` | int | Calculated |
| `earnings_surprise_avg` | float | Historical data |
| `last_eps_actual` | float | External API |
| `last_eps_estimate` | float | External API |

---

## Data Source Options

### Option A: Financial Datasets MCP (Recommended)

**Pros**:
- Already integrated in codebase
- Consistent with existing MCP pattern
- Reliable financial data

**Cons**:
- May require additional MCP tool call
- Need to verify earnings data availability

**Implementation**:
```python
# In context_builder.py or separate service
from src.integrations.mcp_client import get_financial_datasets_client

async def get_earnings_calendar(symbol: str) -> dict:
    client = get_financial_datasets_client()
    return await client.get_earnings_calendar(symbol)
```

### Option B: Yahoo Finance (yfinance)

**Pros**:
- Free, no API key
- Already used for some ticker data

**Cons**:
- Rate limited
- Less reliable for earnings dates
- May be blocked

### Option C: SEC EDGAR

**Pros**:
- Official source
- Already integrated for filings

**Cons**:
- Only shows past filings, not future dates
- Requires parsing

---

## Implementation Plan

### Phase 1: Data Source Integration

1. Decide on data source (recommend Option A)
2. Add earnings fetching to data layer
3. Include in ticker_data dict

### Phase 2: Context Section

```python
# In context_builder.py

def _build_earnings_section(self, ticker_data: Dict) -> str:
    """Build earnings calendar section if data available"""
    next_earnings = ticker_data.get('next_earnings_date')
    if not next_earnings:
        return ""  # Omit section if no data

    from datetime import datetime
    days_until = (next_earnings - datetime.now()).days

    return f"""
=== EARNINGS CALENDAR ===
Next Earnings: {{{{NEXT_EARNINGS_DATE}}}}
Days Until: {{{{EARNINGS_DAYS_UNTIL}}}}
Historical Surprise: {{{{EARNINGS_SURPRISE_AVG}}}}%

Guidance: Earnings within 14 days impacts volatility.
"""
```

### Phase 3: Placeholders

```python
# In number_injector.py

EARNINGS_PLACEHOLDERS = {
    'NEXT_EARNINGS_DATE': '',
    'EARNINGS_DAYS_UNTIL': ' days',
    'EARNINGS_SURPRISE_AVG': '%',
}
```

---

## Invariants

- [ ] Section only appears when earnings data available
- [ ] Graceful degradation if API fails
- [ ] Placeholder injection works correctly
- [ ] No raw numbers in context (use placeholders)

---

## Decision Required

**Which data source to use?**

- [ ] Option A: Financial Datasets MCP
- [ ] Option B: Yahoo Finance
- [ ] Option C: SEC EDGAR
- [ ] Defer: Implement later

---

## See Also

- `/analysis` output recommending this feature
- `src/report/context_builder.py` - where section would be added
- `src/report/number_injector.py` - placeholder registration
