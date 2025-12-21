# ADR-005: Correlation-Based Peer Comparison

**Status:** ✅ Accepted
**Date:** 2024-02
**Deciders:** Development Team

## Context

Reports should include peer company comparisons to provide market context (e.g., "NVDA outperforming semiconductor peers by 15%"). We need a method to automatically identify relevant peer companies.

### Requirements

- Find peers for any ticker (no manual tagging)
- Based on actual market behavior, not subjective classification
- Fast enough for real-time API responses
- No external API dependencies

### Available Data

- Historical price data from yfinance (1 year, daily)
- ~2000 Thai tickers in database

## Decision

Use historical price correlation (Pearson coefficient) to identify peer companies.

### Implementation

```python
# src/api/peer_selector.py
def find_peers(self, ticker: str, max_peers: int = 5) -> List[str]:
    """Find peers using 1-year price correlation"""
    target_data = yf.download(ticker, period='1y')['Close']

    correlations = []
    for candidate in all_tickers:
        candidate_data = yf.download(candidate, period='1y')['Close']
        correlation = target_data.corr(candidate_data)  # Pearson coefficient
        if correlation > 0.5:  # Threshold
            correlations.append((candidate, correlation))

    return sorted(correlations, reverse=True)[:max_peers]
```

### Correlation Threshold

- **0.5**: Moderate positive correlation
- Higher threshold (0.7+): Too strict, finds too few peers
- Lower threshold (0.3): Too loose, finds unrelated companies

## Consequences

### Positive

- ✅ **No External APIs**: Uses yfinance data already fetched for analysis
- ✅ **Simple & Explainable**: Correlation coefficient easy to understand
- ✅ **Fast**: pandas.corr() efficient (~1s for 2000 tickers)
- ✅ **Data-Driven**: Based on actual price movements, not subjective tags
- ✅ **Automatic**: Works for any ticker, no manual classification needed

### Negative

- ❌ **Correlation ≠ Causation**: May find spuriously correlated stocks
- ❌ **Market Bias**: Correlated during bull markets doesn't mean fundamentally similar
- ❌ **Sector Drift**: Tech + finance can correlate during market-wide movements
- ❌ **Computation Cost**: Must calculate correlation with all tickers

### Mitigation

- Combine with sector filter (future enhancement)
- Display correlation coefficient in UI (transparency)
- Cache peer relationships (recalculate weekly, not per request)

## Alternatives Considered

### Alternative 1: Industry Classification

**Example:** Use GICS sectors from yfinance
```python
target_sector = yf.Ticker(ticker).info['sector']
peers = [t for t in tickers if yf.Ticker(t).info['sector'] == target_sector]
```

**Why Rejected:**
- Requires external data (not always available)
- Subjective: "Technology" sector includes very different companies
- Classification may be wrong or outdated
- Doesn't capture actual market behavior

### Alternative 2: Fundamental Similarity

**Example:** Find tickers with similar P/E, market cap, revenue growth
```python
peers = find_similar_fundamentals(ticker, metrics=['pe_ratio', 'market_cap'])
```

**Why Rejected:**
- Complex: Requires multiple metrics, weighting scheme
- Data availability: Not all tickers have complete fundamentals
- Slow: Must fetch fundamentals for all candidates
- Subjective: Which metrics matter? How to weight them?

### Alternative 3: ML Clustering

**Example:** Train k-means on price patterns, fundamentals, news
```python
clusters = kmeans.fit(price_features + fundamental_features)
peers = get_cluster_members(ticker, clusters)
```

**Why Rejected:**
- Overkill: Requires training data, model maintenance
- Difficult to explain to users
- Slower than correlation (model inference + feature extraction)
- Need labeled data for validation

### Alternative 4: Manual Peer Tagging

**Example:** Maintain database of ticker → peers mappings
```yaml
NVDA: [AMD, INTC, TSM]
AAPL: [MSFT, GOOGL]
```

**Why Rejected:**
- Doesn't scale: Manual work for 2000 tickers
- Requires maintenance as market changes
- Subjective: Who decides the peers?
- Can't handle new tickers automatically

## References

- **Implementation**: `src/api/peer_selector.py:find_peers()`
- **Correlation Coefficient**: Pearson's r (-1 to +1)
- **Data Source**: yfinance historical prices (1 year, daily)

## Decision Drivers

1. **Simplicity**: Correlation is one line of code (`pandas.corr()`)
2. **Speed**: Fast enough for real-time API (~1s)
3. **No Dependencies**: Uses data already fetched

## Future Enhancements

**Possible improvements (not implemented):**
- Sector filter: Only correlate within same sector
- Time-weighted correlation: Recent prices matter more
- Rolling correlation: Detect changing relationships
- Cache peer relationships: Recompute weekly instead of per request

**Why not now:**
- Current approach works well enough
- Premature optimization
- Can add later without breaking API

## Correlation vs Other Metrics

| Metric | Speed | Accuracy | Explainability |
|--------|-------|----------|----------------|
| Price Correlation | ⚡ Fast | ⭐⭐⭐ Good | ✅ Simple |
| Fundamental Similarity | 🐌 Slow | ⭐⭐⭐⭐ Better | ❓ Complex |
| Industry Classification | ⚡ Fast | ⭐⭐ OK | ✅ Simple |
| ML Clustering | 🐌 Slow | ⭐⭐⭐⭐ Better | ❌ Black box |

**Verdict:** Correlation provides best speed/accuracy/simplicity trade-off.
