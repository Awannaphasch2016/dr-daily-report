# Principle Compliance Audit: Stock-Pattern PyPI Install

**Audit Date**: 2026-01-11
**Scope**: DEPLOYMENT (implementing Option 1 from design)
**Context**: Adding stock-pattern library via PyPI to enable pattern detection

---

## Audit Summary

**Principles audited**: 6
**Status**:
- ✅ Compliant: 2
- ⚠️ Partial: 3
- ❌ Violations: 1

**Overall compliance**: 50% (must address violations before deployment)

---

## Compliance Results

### Principle #4: Type System Integration

**Compliance question**: Are type conversions explicit when crossing library boundary?

**Verification method**: Check adapter code for serialization handling

**Evidence**:
```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py:130-131
# Serialize result (convert Timestamps to strings)
serialized = stock_pattern_lib.make_serializable(result)
```

**Status**: ✅ COMPLIANT

**Notes**: The adapter already calls `make_serializable()` to convert pandas Timestamps and numpy types to JSON-compatible Python types. This handles the type boundary correctly.

---

### Principle #15: Infrastructure-Application Contract

**Compliance question**: Does requirements.txt align with adapter's expected imports?

**Verification method**: Compare adapter imports vs requirements.txt

**Evidence**:
```
# Current adapter expects:
sys.path.insert(0, '/tmp/stock-pattern/src')
import utils as stock_pattern_lib

# requirements.txt:
stock-pattern NOT present

# After fix, adapter should expect:
from stock_pattern.utils import find_bullish_flag, ...
```

**Status**: ❌ VIOLATION

**Gap**:
1. `stock-pattern` not in requirements.txt
2. Adapter uses wrong import path (`/tmp/stock-pattern/src` instead of PyPI package)

**Impact**: Library won't load after adding to requirements.txt unless import path is also fixed

---

### Principle #1: Defensive Programming

**Compliance question**: Does adapter fail fast and log loudly on import failure?

**Verification method**: Check error handling in adapter

**Evidence**:
```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py:36-37
except ImportError:
    logger.debug("stock-pattern library not available (optional for Lambda)")
```

**Status**: ⚠️ PARTIAL

**Gap**: Import failure logged at DEBUG level (silent), should be INFO or WARNING when library is expected to be available.

**Impact**: If stock-pattern installation fails silently, custom adapter will be used without clear indication why.

**Recommendation**: Add startup validation that logs at INFO level when stock-pattern successfully loads, and WARNING when expected but missing.

---

### Principle #10: Testing Anti-Patterns

**Compliance question**: Are there tests for the stock-pattern adapter?

**Verification method**: Search for adapter tests

**Evidence**:
```
# tests/analysis/test_pattern_detectors.py
- Tests ChartPatternDetector, CandlestickPatternDetector, SupportResistanceDetector
- NO tests for StockPatternAdapter or CustomPatternAdapter
- NO tests for registry fallback behavior
```

**Status**: ⚠️ PARTIAL

**Gap**:
1. No unit tests for `StockPatternAdapter`
2. No tests verifying registry fallback (stock-pattern → custom)
3. No tests for `make_serializable()` output format

**Impact**: If stock-pattern library API changes, adapter may break silently.

**Recommendation**: Add tests for:
- `StockPatternAdapter.is_available()` returns True when installed
- `StockPatternAdapter.detect()` returns expected structure
- Registry fallback works when stock-pattern unavailable

---

### Principle #11: Artifact Promotion

**Compliance question**: Will Docker image build correctly with new dependency?

**Verification method**: Check Dockerfile and existing image size

**Evidence**:
```
# Current image size: 2.97GB
# stock-pattern dependencies already in requirements.txt:
- pandas (already present)
- numpy (already present)
- matplotlib (already present)

# New dependencies from stock-pattern:
- mplfinance (new)
- fast_csv_loader (new)
- questionary (new, CLI - not needed)
- prompt-toolkit (new, CLI - not needed)
- tqdm (new)
```

**Status**: ⚠️ PARTIAL

**Gap**:
1. stock-pattern pulls in CLI dependencies (questionary, prompt-toolkit) that aren't needed for Lambda
2. Image size may increase (~50-100MB)
3. Need to verify matplotlib AGG backend works (headless)

**Impact**: Increased Lambda cold start time, larger deployment artifact

**Recommendation**:
- Test Docker build locally before pushing
- Monitor cold start time after deployment
- Consider future optimization (vendor only utils.py if size becomes issue)

---

### Principle #18: Logging Discipline

**Compliance question**: Does adapter log narrative (beginning, middle, end)?

**Verification method**: Check logging statements

**Evidence**:
```python
# Current logging:
logger.info("stock-pattern library loaded successfully")  # Beginning ✅
logger.info(f"  {pattern_type.replace('_', ' ').title()}")  # Middle ✅
logger.error(f"Function '{func_name}' not found...")  # Error ✅
# Missing: End marker (✅ or ❌ after detection completes)
```

**Status**: ✅ COMPLIANT

**Notes**: Logging follows narrative pattern. Could add end marker but not critical.

---

## Recommendations

### Critical (Blocking)

**Priority**: CRITICAL
**Principle**: #15 (Infrastructure-Application Contract)
**Gap**: Requirements.txt missing stock-pattern AND adapter import path wrong
**Fix**:
1. Add `stock-pattern>=1.0.0` to requirements.txt
2. Update adapter import from `/tmp/...` to PyPI package import

**Verification**:
```bash
# After fix, verify import works:
python -c "from stock_pattern.utils import find_bullish_flag; print('OK')"
```

**Blocker**: Deployment will not enable stock-pattern without these fixes

---

### High (Risky)

**Priority**: HIGH
**Principle**: #10 (Testing)
**Gap**: No tests for StockPatternAdapter
**Fix**: Add tests in `tests/analysis/test_stock_pattern_adapter.py`

```python
# Minimal test coverage needed:
def test_adapter_available_when_installed():
    adapter = StockPatternAdapter()
    assert adapter.is_available() == True

def test_adapter_detect_returns_expected_structure():
    adapter = StockPatternAdapter()
    result = adapter.detect('bullish_flag', ticker, df, pivots, config)
    assert result is None or 'type' in result
```

**Verification**: `pytest tests/analysis/test_stock_pattern_adapter.py -v`

---

### Medium (Debt)

**Priority**: MEDIUM
**Principle**: #1 (Defensive Programming)
**Gap**: Import failure logged at DEBUG (too silent)
**Fix**: Change to INFO for success, add startup validation

```python
try:
    from stock_pattern.utils import ...
    STOCK_PATTERN_AVAILABLE = True
    logger.info("✅ stock-pattern library loaded successfully")
except ImportError as e:
    logger.info(f"⚠️ stock-pattern library not available: {e}")
    logger.info("   Falling back to custom pattern detector")
```

**Verification**: Check CloudWatch logs show library status at startup

---

### Low (Nice-to-have)

**Priority**: LOW
**Principle**: #11 (Artifact Promotion)
**Gap**: Pulls unnecessary CLI dependencies
**Fix**: Consider `--no-deps` + explicit deps, or vendor only utils.py later

**Verification**: Monitor Lambda cold start time post-deployment

---

## Implementation Checklist

### Step 1: Update requirements.txt (CRITICAL)

```bash
# Add to requirements.txt:
echo "stock-pattern>=1.0.0" >> requirements.txt
```

### Step 2: Update adapter import path (CRITICAL)

```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py

# REMOVE these lines:
# sys.path.insert(0, '/tmp/stock-pattern/src')
# import utils as stock_pattern_lib

# ADD these lines:
try:
    from stock_pattern.utils import (
        find_bullish_flag,
        find_bearish_flag,
        find_triangles,
        find_double_bottom,
        find_double_top,
        find_hns,
        find_reverse_hns,
        find_bullish_vcp,
        find_bearish_vcp,
        make_serializable,
    )

    # Create namespace object for compatibility
    class _StockPatternLib:
        find_bullish_flag = staticmethod(find_bullish_flag)
        find_bearish_flag = staticmethod(find_bearish_flag)
        find_triangles = staticmethod(find_triangles)
        find_double_bottom = staticmethod(find_double_bottom)
        find_double_top = staticmethod(find_double_top)
        find_hns = staticmethod(find_hns)
        find_reverse_hns = staticmethod(find_reverse_hns)
        find_bullish_vcp = staticmethod(find_bullish_vcp)
        find_bearish_vcp = staticmethod(find_bearish_vcp)
        make_serializable = staticmethod(make_serializable)

    stock_pattern_lib = _StockPatternLib()
    STOCK_PATTERN_AVAILABLE = True
    logger.info("✅ stock-pattern library loaded from PyPI")
except ImportError as e:
    logger.info(f"⚠️ stock-pattern not available: {e}")
    stock_pattern_lib = None
    STOCK_PATTERN_AVAILABLE = False
```

### Step 3: Test locally (HIGH)

```bash
# Install locally
pip install stock-pattern

# Verify import
python -c "from stock_pattern.utils import find_bullish_flag; print('OK')"

# Run adapter test
python -c "
from src.analysis.pattern_detectors import StockPatternAdapter
adapter = StockPatternAdapter()
print(f'Available: {adapter.is_available()}')
print(f'Patterns: {adapter.supported_patterns}')
"
```

### Step 4: Docker build test (HIGH)

```bash
# Build Docker image
docker build -f Dockerfile.lambda.container -t test-stock-pattern .

# Test import in container
docker run --rm test-stock-pattern python -c \
  "from stock_pattern.utils import find_bullish_flag; print('OK')"
```

### Step 5: Deploy to dev

```bash
git add requirements.txt src/analysis/pattern_detectors/stock_pattern_adapter.py
git commit -m "feat(patterns): Add stock-pattern library via PyPI

- Add stock-pattern>=1.0.0 to requirements.txt
- Update adapter to import from PyPI package
- Improve logging for library availability

Enables stock-pattern implementation (priority=10) in pattern registry.
Custom implementation remains as fallback (priority=5)."

git push origin dev
```

### Step 6: Verify deployment

```bash
# Check CloudWatch logs for:
# "✅ stock-pattern library loaded from PyPI"
# "Registered stock-pattern adapter (priority=10)"

# Test API returns stock_pattern implementation
curl https://dev-api.example.com/api/v1/report/NVDA19 | \
  jq '.chart_patterns[].implementation'
# Should show: "stock_pattern" or "stock_pattern_lib"
```

---

## Next Audit

**Recommended timing**: After dev deployment
**Focus areas**:
1. Verify stock-pattern actually used (not custom fallback)
2. Check Lambda cold start time
3. Verify pattern detection quality matches expectations
