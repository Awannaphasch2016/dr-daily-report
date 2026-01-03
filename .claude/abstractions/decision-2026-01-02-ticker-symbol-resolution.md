---
claim: User sends ticker symbols without type specification
type: decision
date: 2026-01-02
status: pattern-extracted
confidence: Medium
instances: User frustration + existing codebase analysis
---

# Abstraction: Ticker Symbol Resolution Decision Pattern

**Abstracted From**:
- User request: "I have a hard time communicate TICKER to claude. I want claude to always resolve ticker that I send without me having to specify ticker 'type' e.g. eikon, yahook_finance."
- Codebase: `src/data/aurora/ticker_resolver.py` (existing implementation)
- Usage examples: `DBS19` vs `D05.SI` vs `DBSM.SI` (user confusion)

**Total Instances**: 1 explicit user request + codebase analysis

**Confidence**: Medium
- User has expressed clear frustration with current UX
- Technical solution exists but not exposed to Claude conversation layer
- Pattern: User shouldn't specify symbol type, system should infer

---

## Pattern Description

**What it is**:
A decision pattern for handling ambiguous ticker symbols from users without requiring them to specify the symbol type (DR, Yahoo Finance, Eikon, etc.).

**When it occurs**:
- User asks about a ticker (e.g., "DBS19", "NVDA", "D05.SI")
- Claude receives ticker symbol in conversation
- Claude needs to query Aurora or resolve ticker information
- User shouldn't need to know what "type" the symbol is

**Why it happens**:
- Multiple ticker naming conventions exist (DR, Yahoo, Eikon, Bloomberg, ISIN)
- Same company has different symbols in different systems:
  - DBS: `DBS19` (DR), `D05.SI` (Yahoo), `DBSM.SI` (Eikon)
  - NVIDIA: `NVDA19` (DR), `NVDA` (Yahoo)
- Current system has TickerResolver but Claude doesn't use it automatically

---

## Problem Statement

### User Pain Point
User said: **"I have a hard time communicate TICKER to claude"**

**Specific frustration**:
- User types "DBS19" but Claude doesn't find it (asks for clarification)
- User types "DBS" and Claude doesn't know if it's DBS Group or another entity
- User has to explain "use Yahoo Finance symbol" or "it's a DR symbol"

**Root cause**:
Claude is not using the existing `TickerResolver` service to automatically resolve symbols.

---

## Current State Analysis

### Existing Solution: TickerResolver Service

**Location**: `src/data/aurora/ticker_resolver.py`

**What it does**:
- Resolves ANY symbol format to canonical TickerInfo
- Maintains mapping between different symbol types
- Fallback to CSV if Aurora unavailable

**Supported symbol types**:
```python
class TickerInfo:
    dr_symbol: Optional[str]       # NVDA19, DBS19
    yahoo_symbol: Optional[str]    # NVDA, D05.SI
    eikon_symbol: Optional[str]    # DBSM.SI (future)
```

**Example usage**:
```python
resolver = get_ticker_resolver()

# All of these resolve to same TickerInfo:
resolver.resolve("NVDA19")   # DR symbol
resolver.resolve("NVDA")     # Yahoo symbol
resolver.resolve("nvda")     # Case-insensitive

# Quick conversions:
resolver.to_yahoo("DBS19")   # Returns: "D05.SI"
resolver.to_dr("D05.SI")     # Returns: "DBS19"
```

### Gap: Claude Doesn't Use TickerResolver Automatically

**Current flow**:
```
User: "get news for DBS19"
    ↓
Claude: Receives "DBS19"
    ↓
Claude: Queries Aurora with "DBS19" (exact match)
    ↓
Aurora: No results (symbol is "D05.SI" in precomputed_reports)
    ↓
Claude: Asks user to clarify or fails
```

**Desired flow**:
```
User: "get news for DBS19"
    ↓
Claude: Receives "DBS19"
    ↓
Claude: Calls resolver.resolve("DBS19")
    ↓
Resolver: Returns TickerInfo(yahoo_symbol="D05.SI", dr_symbol="DBS19")
    ↓
Claude: Queries Aurora with "D05.SI"
    ↓
Aurora: Returns results ✅
    ↓
Claude: Shows news to user
```

---

## Generalized Pattern

### Decision Point: User Provides Ticker Symbol

**When user says**:
- "DBS19"
- "NVDA"
- "D05.SI"
- "get report for DBS"
- "news about NVIDIA"

**Claude should**:
1. Extract ticker symbol from user message
2. Call `TickerResolver.resolve(symbol)` to get canonical info
3. Use `yahoo_symbol` for Aurora queries (since Aurora stores Yahoo symbols)
4. Display both DR and Yahoo symbols in response for user clarity

### Heuristic: Always Resolve First

**Rule**: Before ANY ticker-based operation, resolve symbol to canonical form.

**Operations that need ticker resolution**:
- Querying Aurora for reports (`precomputed_reports.symbol`)
- Fetching ticker data (scheduler)
- Displaying ticker information to user
- Generating reports

**Implementation**:
```python
# Pattern: Resolve before query
def get_news_for_ticker(user_input: str):
    resolver = get_ticker_resolver()

    # Resolve symbol (works for any format)
    info = resolver.resolve(user_input)

    if not info:
        return f"Ticker '{user_input}' not found. Did you mean...?"

    # Use yahoo_symbol for Aurora queries
    yahoo = info.yahoo_symbol

    # Query Aurora
    results = query_aurora(f"SELECT * FROM precomputed_reports WHERE symbol = '{yahoo}'")

    # Display to user with both symbols for clarity
    return f"News for {info.company_name} ({info.dr_symbol} / {info.yahoo_symbol}): ..."
```

---

## Pattern Template (Decision)

### Pattern Name: Ticker Symbol Auto-Resolution

**Decision Point**: User provides ticker symbol in any format

**Options**:
A. Ask user to specify symbol type ("Is this Yahoo Finance or DR symbol?")
B. Automatically resolve using TickerResolver
C. Try both formats and return whichever works

**Selection Heuristic**:

**Choose B (Auto-resolve) when** (RECOMMENDED):
- TickerResolver service is available
- Symbol is for querying data (Aurora, APIs)
- User is end-user (not developer debugging)
- System has mapping of symbol types

**Choose A (Ask user) when**:
- Symbol genuinely ambiguous (e.g., "DBS" could be multiple companies)
- TickerResolver doesn't recognize symbol
- User needs to learn symbol conventions (educational context)

**Choose C (Try multiple) when**:
- TickerResolver unavailable (fallback mode)
- Performance not critical (can afford multiple queries)
- High confidence symbol is valid (just wrong format)

**Default**: B (Auto-resolve) - best UX, leverages existing infrastructure

**Trade-offs**:

**Option A** (Ask user):
- ❌ Poor UX (user has to know symbol types)
- ❌ More back-and-forth messages
- ✅ Explicit, no ambiguity
- ✅ Educational (user learns system)

**Option B** (Auto-resolve):
- ✅ Best UX (works with any symbol format)
- ✅ Leverages existing TickerResolver service
- ✅ Consistent with codebase patterns
- ❌ Requires TickerResolver to be accurate
- ❌ May fail silently if resolver has bugs

**Option C** (Try multiple):
- ✅ Works without TickerResolver
- ❌ Multiple database queries (performance cost)
- ❌ Doesn't scale (N symbol types = N queries)
- ❌ Harder to debug (which query succeeded?)

---

## Implementation Recommendation

### For Claude Code Conversation Layer

**Add to CLAUDE.md** (Principle):

```markdown
### Ticker Symbol Auto-Resolution Principle

When user provides ticker symbol, ALWAYS resolve using TickerResolver before querying Aurora or displaying information.

**Pattern**:
1. Extract ticker from user message (e.g., "DBS19", "NVDA")
2. Call `get_ticker_resolver().resolve(symbol)`
3. Use `yahoo_symbol` for Aurora queries (Aurora stores Yahoo format)
4. Display both `dr_symbol` and `yahoo_symbol` in responses for clarity

**Example**:
```python
from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
info = resolver.resolve(user_ticker)  # Works for any format

if info:
    yahoo = info.yahoo_symbol  # For Aurora queries
    dr = info.dr_symbol        # For user display
else:
    # Symbol not recognized
    suggest_alternatives()
```

**Why**: Users shouldn't need to know symbol type conventions (DR vs Yahoo vs Eikon). System should handle format translation automatically.
```

### For Claude Instructions (This Session)

**Add reminder** when user mentions tickers:
```
When user mentions ticker symbol:
1. Use TickerResolver to resolve to canonical form
2. Use yahoo_symbol for Aurora queries
3. Show both DR and Yahoo symbols in response
4. If not found, suggest alternatives from resolver.get_all_tickers()
```

---

## Concrete Examples

### Example 1: User Asks About DBS19

**User message**: "does aurora has news info in it? show me DBS19 latest news"

**Current behavior** (WITHOUT pattern):
```python
# Claude queries directly
query = "SELECT * FROM precomputed_reports WHERE symbol = 'DBS19'"
# Result: Empty (no symbol 'DBS19' in Aurora, it's stored as 'D05.SI')
```

**Improved behavior** (WITH pattern):
```python
# 1. Resolve symbol
resolver = get_ticker_resolver()
info = resolver.resolve("DBS19")  # Returns TickerInfo

# 2. Use yahoo_symbol for query
yahoo = info.yahoo_symbol  # "D05.SI"
query = f"SELECT * FROM precomputed_reports WHERE symbol = '{yahoo}'"
# Result: Found news for D05.SI ✅

# 3. Display to user with both symbols
response = f"""
Latest news for {info.company_name}:
Symbol: {info.dr_symbol} (DR) / {info.yahoo_symbol} (Yahoo Finance)

{news_items}
"""
```

### Example 2: User Uses Yahoo Symbol Directly

**User message**: "get report for D05.SI"

**Behavior** (WITH pattern - works the same):
```python
# 1. Resolve symbol (also works for Yahoo format)
info = resolver.resolve("D05.SI")  # Same TickerInfo as "DBS19"

# 2. Use yahoo_symbol
yahoo = info.yahoo_symbol  # "D05.SI"
# ... query works ...

# User sees: "DBS Group Holdings (DBS19 / D05.SI)"
# Both formats shown for clarity
```

### Example 3: Ambiguous Symbol

**User message**: "show me news for DBS"

**Behavior**:
```python
# 1. Try to resolve
info = resolver.resolve("DBS")  # Returns None (ambiguous)

# 2. Search for similar
all_tickers = resolver.get_all_tickers()
matches = [t for t in all_tickers if "DBS" in t.company_name.upper() or
                                       "DBS" in (t.dr_symbol or "").upper()]

# 3. Suggest alternatives
response = f"""
Multiple tickers found for "DBS":
1. DBS Group Holdings (DBS19 / D05.SI)
2. DBS Bank Indonesia (if exists)

Which one did you mean?
"""
```

---

## Variations

**Observed variations** across instances:

### Variation 1: User Knows Yahoo Symbol
User says: "NVDA" (no "19" suffix)
→ Resolver recognizes as Yahoo symbol
→ Works directly

### Variation 2: User Knows DR Symbol
User says: "NVDA19" (DR format)
→ Resolver recognizes as DR symbol
→ Converts to Yahoo ("NVDA") for Aurora query
→ Works

### Variation 3: User Uses Eikon Symbol (Future)
User says: "DBSM.SI" (Eikon format)
→ Resolver has eikon_symbol mapping
→ Converts to Yahoo ("D05.SI")
→ Works

**When to deviate**:
- Symbol genuinely not recognized → Ask user to clarify or check tickers.csv
- Symbol ambiguous (multiple matches) → Present options
- Developer debugging → Show raw query (don't auto-resolve)

---

## Graduation Path

**Current confidence**: Medium (1 user request + codebase analysis)

**To increase confidence**:
- [ ] Implement pattern in this conversation (test with user)
- [ ] Observe user satisfaction (fewer clarification requests?)
- [ ] Check resolver accuracy (does it work for all user inputs?)

**If pattern works well** (HIGH confidence after testing):
- Graduate to CLAUDE.md as core principle
- Add to conversation context permanently
- Document in project README (user-facing)

**If pattern has issues** (LOW confidence after testing):
- Refine based on failures
- Maybe Option C (try multiple) is better fallback
- Update TickerResolver if mapping incomplete

---

## Action Items

- [ ] **Test pattern in current conversation**: Use TickerResolver for next ticker query
- [ ] **Validate resolver accuracy**: Check if DBS19 → D05.SI works
- [ ] **Add to CLAUDE.md** (if tests pass): New principle "Ticker Symbol Auto-Resolution"
- [ ] **Update conversation prompts**: Always use resolver before ticker queries
- [ ] **Document for user**: Add to README (users can use any ticker format)

---

## Metadata

**Pattern Type**: decision (how to handle ticker symbols)
**Confidence**: Medium (1 instance + technical analysis)
**Created**: 2026-01-02
**Instances**: 1 (user frustration)
**Last Updated**: 2026-01-02

---

## References

### Code
- `src/data/aurora/ticker_resolver.py` - TickerResolver implementation
- `src/utils/ticker_utils.py` - Ticker utilities
- `data/tickers.csv` - Symbol mappings

### Related Patterns
- **Progressive Evidence Strengthening** (CLAUDE.md Principle #2): Verify resolver works (not just assume)
- **Defensive Programming** (CLAUDE.md Principle #1): Handle resolver failures gracefully

### User Request
Original message: "I have a hard time communicate TICKER to claude. I want claude to always resolve ticker that I send without me having to specify ticker 'type' e.g. eikon, yahook_finance."

---

## Next Steps (For This Conversation)

**Immediate**: Apply pattern to demonstrate UX improvement

```python
# User said: "DBS19"
# Claude should do:

from src.data.aurora.ticker_resolver import get_ticker_resolver

resolver = get_ticker_resolver()
info = resolver.resolve("DBS19")

if info:
    print(f"Resolved: {info.company_name}")
    print(f"  DR Symbol: {info.dr_symbol}")
    print(f"  Yahoo Symbol: {info.yahoo_symbol}")
    print(f"  Exchange: {info.exchange}")

    # Use yahoo_symbol for Aurora queries
    yahoo = info.yahoo_symbol
else:
    print("Symbol not recognized")
```

**Test query**: "Get latest news for DBS19" should automatically resolve to D05.SI and work.
