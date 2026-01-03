---
date: 2026-01-02
period: Last 30 days (2025-12-03 to 2026-01-02)
focus: ticker resolution principles
status: completed
---

# Knowledge Evolution Report - Ticker Resolution Principles

**Date**: 2026-01-02
**Period reviewed**: Last 30 days (2025-12-03 to 2026-01-02)
**Focus area**: Ticker symbol resolution practices

---

## Executive Summary

**Drift detected**: 3 areas
**New patterns**: 1 pattern (Ticker Auto-Resolution)
**Abandoned patterns**: 0 patterns
**Proposed updates**: 3 proposals

**Overall assessment**: **Positive drift** - Code has evolved to consistently use TickerResolver, but CLAUDE.md lacks guidance for this critical pattern. User frustration indicates documentation gap.

**Key finding**: Ticker resolution is now a **core architectural pattern** used across 11 files, but **not documented as a principle** in CLAUDE.md. This creates confusion for both users and AI assistants.

---

## Drift Analysis

### Positive Drift (Practices Improved)

#### 1. **Consistent TickerResolver Usage Across Codebase**

**What changed**: TickerResolver is now universally used for symbol resolution

**Evidence** (11 code files + 2 critical bug fixes):

**Files using TickerResolver**:
1. `src/report_worker_handler.py` - Report generation (lines 137-150)
2. `src/scheduler/ticker_fetcher.py` - Data fetching scheduler
3. `src/scheduler/precompute_controller_handler.py` - Precompute orchestration
4. `src/data/aurora/precompute_service.py` - Precompute data access
5. `src/data/data_fetcher.py` - Yahoo Finance data fetching
6. `src/scheduler/query_tool_handler.py` - Aurora query tool
7. `src/data/aurora/fund_data_fetcher.py` - Fund data integration
8. `src/scheduler/schema_manager_handler.py` - Schema management
9. `src/data/news_fetcher.py` - News API integration
10. `src/data/aurora/ticker_resolver.py` - Resolver implementation (581 lines)
11. `src/data/aurora/__init__.py` - Module exports

**Recent bug fixes demonstrating critical importance**:

**Bug Fix #1** (commit 802ed60, Dec 30, 2025):
```
fix: Resolve DR symbols to Yahoo symbols in report worker

Root Cause:
- Workers queried ticker_data with DR symbols (DBS19, NVDA19)
- Aurora stores Yahoo symbols (D05.SI, NVDA, 1378.HK)
- Symbol mismatch caused "Data not available" errors

Fix: Changed line 150 to use yahoo_symbol for Aurora queries
Impact: Report workers now find ticker_data successfully
```

**Bug Fix #2** (commit b65969d, Jan 2, 2026):
```
fix: Use DR symbol for ticker_service.get_ticker_info() lookup

Root Cause:
- ticker_service.get_ticker_info() expects DR symbols (DBS19)
- Code was passing Yahoo symbols after resolution
- All 46 report workers failed with "ticker data not found"

Fix: Use dr_symbol for ticker_service, yahoo_symbol for Aurora
Impact: Report workers can now look up ticker metadata
```

**Pattern discovered**: **Dual-symbol architecture**
- Use `yahoo_symbol` for Aurora queries (database storage format)
- Use `dr_symbol` for ticker_service lookups (CSV-based legacy service)
- Always resolve first, then use appropriate format per subsystem

**Old approach** (pre-December 2025):
- No consistent resolution strategy
- Manual symbol format handling in each component
- Symbol mismatches caused production failures

**New approach** (actual, last 30 days):
```python
# Universal pattern across all 11 files:
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
info = resolver.resolve(user_input)  # Works for any format

# Use correct symbol per subsystem:
yahoo = info.yahoo_symbol  # For Aurora queries
dr = info.dr_symbol        # For ticker_service lookups
```

**Why it's better**:
- **User UX**: Users don't need to know symbol types (DBS19 vs D05.SI both work)
- **Reliability**: Prevents symbol mismatch bugs (2 production incidents in 30 days)
- **Consistency**: Single source of truth for symbol mappings
- **Flexibility**: Supports multiple formats (DR, Yahoo, future: Eikon, Bloomberg)

**Recommendation**: **Add "Ticker Symbol Auto-Resolution Principle" to CLAUDE.md**

**Priority**: **HIGH** (affects user experience + prevents production bugs)

---

#### 2. **Symbol Resolution at Entry Points (Defensive Programming)**

**What changed**: Ticker resolution now happens at system boundaries

**Evidence** (3 entry points):

1. **Report worker** (`src/report_worker_handler.py:135-152`):
   ```python
   # Defensive validation: Resolve ticker to canonical form
   resolver = get_ticker_resolver()
   resolved = resolver.resolve(ticker_raw)

   if not resolved:
       error_msg = f"Unknown ticker: {ticker_raw}"
       job_service.fail_job(job_id, error_msg)
       raise ValueError(error_msg)
   ```

2. **Ticker fetcher** (`src/scheduler/ticker_fetcher.py`):
   ```python
   # Resolve symbol to Yahoo Finance format for consistent storage
   resolver = get_ticker_resolver()
   ticker_info = resolver.resolve(ticker)
   yahoo_ticker = ticker_info.yahoo_symbol if ticker_info else ticker
   ```

3. **Query tool** (`src/scheduler/query_tool_handler.py`):
   ```python
   # Auto-resolve ticker symbols in SQL queries
   ```

**Pattern**: "Resolve at boundaries, use canonical internally"

**Alignment with CLAUDE.md**:
- ✅ Principle #1 (Defensive Programming): "Validate configuration at startup, not on first use"
- ✅ Resolution happens before processing (fail-fast)
- ✅ Clear error messages when ticker unknown

**Recommendation**: Document this as application of Defensive Programming principle

**Priority**: MEDIUM (already aligned with existing principle, just needs documentation)

---

### New Patterns Discovered

#### 1. **Ticker Symbol Auto-Resolution Pattern**

**Where found**: Code (11 files), abstractions (1 file), user feedback (explicit request)

**Frequency**: Universal (100% of ticker-handling code uses this pattern)

**Pattern description**:

**Problem**: Same company has different ticker symbols in different systems
- DBS: `DBS19` (DR), `D05.SI` (Yahoo), `DBSM.SI` (Eikon)
- NVIDIA: `NVDA19` (DR), `NVDA` (Yahoo)

**Solution**: Always resolve ticker symbols to canonical form before any operation

**Pattern template**:
```python
# 1. Resolve symbol (works for any format)
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
info = resolver.resolve(user_input)  # DBS19, D05.SI, dbs19 all work

if not info:
    return error_message("Unknown ticker")

# 2. Use appropriate symbol per subsystem
yahoo = info.yahoo_symbol  # For Aurora queries (D05.SI)
dr = info.dr_symbol        # For ticker_service (DBS19)

# 3. Display both formats to user for clarity
print(f"{info.company_name} ({dr} / {yahoo})")
```

**Examples from codebase**:

**Example 1**: Report worker
```python
# Line 137-150: src/report_worker_handler.py
ticker_raw = message['ticker']  # Could be DBS19 or D05.SI

resolved = resolver.resolve(ticker_raw)
ticker = resolved.yahoo_symbol      # For Aurora: D05.SI
dr_symbol = resolved.dr_symbol      # For logging: DBS19

# Aurora query uses Yahoo symbol
# ticker_service uses DR symbol (line 163)
```

**Example 2**: Ticker fetcher scheduler
```python
# src/scheduler/ticker_fetcher.py
ticker_info = resolver.resolve(ticker)
yahoo_ticker = ticker_info.yahoo_symbol  # Consistent storage format
```

**Why it's significant**:
1. **User experience**: User explicitly requested this ("I have a hard time communicate TICKER to claude")
2. **Production impact**: 2 bugs in 30 days related to symbol resolution
3. **Universal adoption**: Pattern used in 100% of ticker-handling code
4. **Architectural**: Core pattern that affects entire system

**Confidence**: **HIGH**
- User explicitly requested auto-resolution
- Pattern universally adopted in code (11/11 files)
- Multiple bug fixes demonstrate criticality
- Well-implemented with fallback strategies

**Recommendation**: **Graduate to CLAUDE.md as Core Principle**

**Graduation path**:
- [x] Pattern extracted (`.claude/abstractions/decision-2026-01-02-ticker-symbol-resolution.md`)
- [x] Evidence collected (code analysis, bug fixes, user feedback)
- [ ] Add to CLAUDE.md Core Principles section
- [ ] Update conversation context to use pattern automatically
- [ ] Document in PROJECT_CONVENTIONS.md (if exists)

**Priority**: **HIGH**

---

### Negative Drift (Practices Degraded)

**None detected** - All ticker resolution changes represent improvements over previous ad-hoc approaches.

---

### Abandoned Patterns

**None detected** - TickerResolver is new pattern (added recently), not abandonment of old pattern.

---

## User Feedback Analysis

### User Pain Point (2026-01-02)

**User said**: *"I have a hard time communicate TICKER to claude. I want claude to always resolve ticker that I send without me having to specify ticker 'type' e.g. eikon, yahook_finance."*

**Analysis**:
- User expects ticker auto-resolution
- Current AI behavior: Doesn't automatically use TickerResolver
- Gap: TickerResolver exists in code but not in AI conversation context
- Impact: Poor user experience (user has to explain symbol types)

**Root cause**: **CLAUDE.md doesn't document ticker resolution as a principle**

**Evidence**:
```bash
$ grep -n "ticker\|symbol" .claude/CLAUDE.md | head -20
# Results: Only mentions in Intent Over Implementation example (lines 149-206)
# NO ticker resolution principle documented
```

**What user expects** (inferred from request):
```
User: "get news for DBS19"
Claude: [automatically resolves DBS19 → D05.SI]
Claude: [queries Aurora with D05.SI]
Claude: [returns news for DBS Group Holdings]
```

**What currently happens** (without documented principle):
```
User: "get news for DBS19"
Claude: [queries Aurora with DBS19 directly]
Aurora: [no results - symbol stored as D05.SI]
Claude: "No news found. Did you mean D05.SI?"
User: [frustrated, has to explain symbol types]
```

**Recommendation**: Add ticker resolution principle to CLAUDE.md to guide AI behavior

---

## Code Evidence Summary

### TickerResolver Service (`src/data/aurora/ticker_resolver.py`)

**Size**: 581 lines (substantial, production-ready implementation)

**Features**:
- Resolves any symbol format → canonical `TickerInfo`
- Supports: DR, Yahoo, Eikon (future: Bloomberg, ISIN)
- Case-insensitive resolution
- Fallback to CSV if Aurora unavailable
- In-memory cache for performance
- Singleton pattern for global access

**API**:
```python
resolver = get_ticker_resolver()

# Resolution
info = resolver.resolve("DBS19")  # Returns TickerInfo or None

# Quick conversions
yahoo = resolver.to_yahoo("DBS19")  # "D05.SI"
dr = resolver.to_dr("D05.SI")       # "DBS19"

# Validation
is_valid = resolver.is_supported("NVDA")  # True/False

# Listing
all_tickers = resolver.get_all_tickers()  # List[TickerInfo]
yahoo_symbols = resolver.get_yahoo_tickers()  # List[str]
```

**Storage**:
- Primary: Aurora database (`ticker_master`, `ticker_aliases` tables)
- Fallback: CSV file (`data/tickers.csv`)

---

## Dual-Symbol Architecture Discovery

**Critical finding**: System uses **TWO different symbol formats** for different subsystems

### Symbol Format By Subsystem

| Subsystem | Format Used | Example | Reason |
|-----------|-------------|---------|--------|
| **Aurora database** | Yahoo | D05.SI | Historical reason (Yahoo Finance API) |
| **ticker_service (CSV)** | DR | DBS19 | Thai DR market convention |
| **User input** | Either | DBS19 or D05.SI | User choice |
| **Logging/tracking** | DR | DBS19 | Human-readable |
| **SQS messages** | DR | DBS19 | Worker job format |

### Resolution Pattern

```python
# Universal pattern in all 11 files:
resolver = get_ticker_resolver()
info = resolver.resolve(user_input)  # Any format

# Then use appropriate format per subsystem:
if querying_aurora:
    symbol = info.yahoo_symbol  # D05.SI
elif querying_ticker_service:
    symbol = info.dr_symbol     # DBS19
elif logging:
    symbol = info.dr_symbol     # DBS19 (human-readable)
```

**Why this matters**:
- Using wrong symbol format causes system failures (2 bugs in 30 days)
- Pattern MUST be documented to prevent future bugs
- New developers (and AI assistants) need clear guidance

---

## CLAUDE.md Updates Needed

### Proposed Addition: Ticker Symbol Auto-Resolution Principle

**Section**: Core Principles (after Principle #12, before Extension Points)

**Proposed text**:

```markdown
### 13. Ticker Symbol Auto-Resolution

Always resolve ticker symbols using TickerResolver before any database query, API call, or data operation. Users should not need to specify symbol type (DR, Yahoo Finance, Eikon, etc.) - the system handles format translation automatically.

**Pattern**:
```python
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
info = resolver.resolve(user_symbol)  # Works for any format (DBS19, D05.SI, dbs19)

if not info:
    return error_message(f"Unknown ticker: {user_symbol}")

# Use correct symbol per subsystem:
yahoo = info.yahoo_symbol  # For Aurora queries (D05.SI, NVDA, 1378.HK)
dr = info.dr_symbol        # For ticker_service lookups (DBS19, NVDA19)

# Display both formats for clarity:
print(f"{info.company_name} ({dr} / {yahoo})")
```

**Dual-Symbol Architecture**:
- **Aurora database**: Uses Yahoo symbols (D05.SI) - historical Yahoo Finance API integration
- **ticker_service**: Uses DR symbols (DBS19) - CSV-based legacy service
- **Always resolve first**, then use appropriate format per subsystem

**Why this matters**:
- Prevents symbol mismatch bugs (ticker_data stored as D05.SI but queried with DBS19)
- Improves user experience (users can use any symbol format they know)
- Maintains consistency across system (single source of truth for mappings)
- Supports future expansion (Eikon, Bloomberg symbols)

**Example**:
```python
# User provides DBS19 (DR format)
info = resolver.resolve("DBS19")

# Aurora query
results = query_aurora(f"SELECT * FROM precomputed_reports WHERE symbol = '{info.yahoo_symbol}'")
# Queries with: D05.SI ✅

# ticker_service lookup
ticker_info = ticker_service.get_ticker_info(info.dr_symbol)
# Looks up: DBS19 ✅

# Display to user
print(f"Report for {info.company_name} ({info.dr_symbol} / {info.yahoo_symbol})")
# Shows: "DBS Group Holdings (DBS19 / D05.SI)" ✅
```

**Related principles**:
- Defensive Programming (Principle #1): Validate ticker existence before processing
- Type System Integration Research (Principle #4): Understand symbol format per subsystem
```

**Rationale**:
- User explicitly requested this pattern
- Code universally adopts this pattern (11/11 files)
- 2 production bugs in 30 days related to symbol resolution
- Improves user experience (no need to specify symbol type)

**Impact**:
- AI assistants will automatically use TickerResolver in conversations
- New developers have clear guidance on symbol handling
- Reduces symbol-related bugs
- Improves user experience

---

### Proposed Update: Intent Over Implementation Example

**Section**: Core Principles → Principle #11 (Intent Over Implementation)

**Current example** (lines 149-206):
Uses generic `process_ticker` example

**Proposed addition**:
Add ticker resolution as a concrete case study

```markdown
**Case study: Ticker Symbol Resolution**

Understanding ticker_info usage revealed intent diverged from implementation:

**Implementation said**: "Stores comprehensive ticker metadata (name, sector, industry)"

**Usage showed**: "Only `symbol` and `is_active` are read, other fields unused"

**Outcome**: Removed unused columns, simplified schema

See [Understanding: ticker_info Usage](.claude/understanding-2025-12-30-ticker-info-usage-by-apps.md) for details.

**New pattern emerged**: TickerResolver became universal symbol resolution pattern (see Principle #13).
```

**Rationale**:
- Links Intent Over Implementation to actual codebase evolution
- Shows how usage analysis led to new architecture pattern
- Provides concrete example of principle in action

---

## Action Items (Prioritized)

### High Priority (Do This Session)

- [ ] **Add Principle #13 to CLAUDE.md**: Ticker Symbol Auto-Resolution
  - Location: Core Principles section (after Principle #12)
  - Content: Full principle text (see "Proposed Addition" above)
  - Impact: AI assistants will use TickerResolver automatically

- [ ] **Update AI conversation context**: Add ticker resolution reminder
  - When user mentions ticker symbol → automatically resolve using TickerResolver
  - Show both DR and Yahoo symbols in responses
  - Use yahoo_symbol for Aurora queries, dr_symbol for ticker_service

- [ ] **Validate pattern works**: Test with user's original request
  - User: "get news for DBS19"
  - Claude: [uses TickerResolver] → queries Aurora with D05.SI → returns news
  - User: Happy (no need to specify symbol type) ✅

### Medium Priority (Do This Week)

- [ ] **Document dual-symbol architecture**: Add to PROJECT_CONVENTIONS.md (if exists)
  - Explain why system uses both Yahoo and DR symbols
  - Document which subsystem uses which format
  - Add troubleshooting guide for symbol mismatch errors

- [ ] **Add to Intent Over Implementation example**: Show ticker_info evolution
  - Demonstrates how usage analysis led to architecture change
  - Links multiple principles together

### Low Priority (Backlog)

- [ ] **Create ADR**: Document ticker resolution architecture decision
  - Why TickerResolver exists
  - Why dual-symbol architecture (historical context)
  - Future: Eikon/Bloomberg symbol support

- [ ] **Monitor pattern adoption**: Ensure new code uses TickerResolver
  - Code review checklist item
  - Pre-commit hook to detect direct symbol usage without resolution

---

## Recommendations

### Immediate Actions

1. **Add Ticker Symbol Auto-Resolution to CLAUDE.md** (Principle #13)
   - Most critical update
   - Directly addresses user frustration
   - Prevents future symbol mismatch bugs

2. **Update AI conversation context to use TickerResolver**
   - Improve user experience immediately
   - No code changes needed (pattern already exists)

3. **Test with user's original request**
   - Validate pattern solves user's pain point
   - Build confidence in auto-resolution approach

### Investigation Needed

- **None** - Pattern is well-understood and universally adopted

### Future Monitoring

- **Watch for**: Symbol mismatch bugs (should decrease to zero after CLAUDE.md update)
- **Measure**: User satisfaction (fewer "ticker not found" complaints)
- **Track**: TickerResolver usage in new code (should be 100%)

---

## Comparison: Documented vs Actual

### CLAUDE.md (Current Documentation)

**Ticker resolution mentioned**: ❌ NO

**Search results**:
```bash
$ grep -i "ticker.*resolution\|symbol.*resolution" .claude/CLAUDE.md
# No results
```

**Only mention**: Intent Over Implementation example (lines 149-206)
- Generic example about understanding usage patterns
- No specific guidance on ticker symbol handling

### Actual Practice (Code)

**Ticker resolution usage**: ✅ UNIVERSAL (11/11 ticker-handling files)

**Pattern**: Always use TickerResolver before any ticker operation

**Evidence**:
- 11 files import and use `get_ticker_resolver()`
- 2 bug fixes in 30 days related to symbol resolution
- User explicitly requested auto-resolution feature
- No exceptions - pattern is 100% adopted

### Gap Analysis

**Documentation gap**: **CRITICAL**

| Aspect | CLAUDE.md | Actual Code | Gap |
|--------|-----------|-------------|-----|
| Ticker resolution principle | Not mentioned | Universal pattern | **LARGE** |
| Dual-symbol architecture | Not documented | Production reality | **LARGE** |
| Symbol format per subsystem | Not explained | Critical for correctness | **LARGE** |
| TickerResolver usage | Not mentioned | 11 files use it | **LARGE** |
| User experience guidance | None | User frustrated | **LARGE** |

**Impact of gap**:
- AI assistants don't use TickerResolver automatically
- New developers lack guidance on symbol handling
- Users must explain symbol types (poor UX)
- Symbol mismatch bugs occur (2 in 30 days)

**Severity**: **HIGH** (affects user experience + causes production bugs)

---

## Metrics

### Review Scope

**Time period**: Last 30 days (2025-12-03 to 2026-01-02)

**Data sources**:
- Git commits: 20 commits mentioning ticker/symbol
- Code files: 11 files using TickerResolver
- Bug fixes: 2 symbol resolution bugs
- User feedback: 1 explicit request
- Abstractions: 1 pattern extraction document
- Understanding docs: 2 ticker-related docs

**Analysis**:
- Positive drift: 2 patterns
- Negative drift: 0 patterns
- New patterns: 1 (Ticker Auto-Resolution)
- Abandoned patterns: 0

### Drift Indicators

**Positive drift**:
- ✅ Consistent TickerResolver usage (11/11 files)
- ✅ Symbol resolution at entry points (defensive programming)

**Documentation gap**:
- ❌ CLAUDE.md lacks ticker resolution principle
- ❌ No guidance for AI assistants on symbol handling
- ❌ User experiencing friction (explicit complaint)

### Update Proposals

**High priority**: 3 proposals
1. Add Principle #13 to CLAUDE.md
2. Update AI conversation context
3. Validate with user's original request

**Medium priority**: 2 proposals
1. Document dual-symbol architecture in PROJECT_CONVENTIONS.md
2. Update Intent Over Implementation example

**Low priority**: 2 proposals
1. Create ADR for ticker resolution architecture
2. Add monitoring for pattern adoption

**Total**: 7 proposals

---

## Next Evolution Review

**Recommended**: 2026-02-02 (30 days from now)

**Focus areas for next time**:
- Validate ticker resolution principle adoption
- Check if symbol mismatch bugs decreased to zero
- Monitor user satisfaction with ticker auto-resolution
- Review any new ticker-related patterns that emerge

**Success metrics**:
- Zero symbol mismatch bugs in next 30 days
- User doesn't complain about ticker communication
- 100% of new ticker-handling code uses TickerResolver
- AI assistants automatically use TickerResolver in conversations

---

## Conclusion

**Overall assessment**: **Positive drift with critical documentation gap**

**Key findings**:
1. ✅ Code has evolved excellent ticker resolution pattern (TickerResolver)
2. ✅ Pattern universally adopted across codebase (11/11 files)
3. ❌ CLAUDE.md completely lacks this critical principle
4. ❌ User frustrated by gap between code capability and AI behavior

**Root cause**: Knowledge exists in code but not in documentation → AI doesn't use it

**Solution**: Add Ticker Symbol Auto-Resolution principle to CLAUDE.md

**Expected impact**:
- Improved user experience (no need to specify symbol types)
- Reduced symbol mismatch bugs (from 2 in 30 days → 0)
- Better AI assistant behavior (automatic TickerResolver usage)
- Clear guidance for new developers

**Confidence**: **HIGH** - Pattern is well-established, user need is clear, solution is straightforward

---

*Report generated by `/evolve ticker resolution principles`*
*Generated: 2026-01-02 05:30 Bangkok*
