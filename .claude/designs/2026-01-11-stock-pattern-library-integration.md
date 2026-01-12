# Design: Stock-Pattern Library Integration Options

**Date**: 2026-01-11
**Domain**: python (infrastructure + code)
**Goal**: Integrate https://github.com/BennyThadikaran/stock-pattern into chart pattern registry

---

## Executive Summary

**What we're designing**: Options to deploy the stock-pattern library so it becomes an active implementation in our pattern detector registry (priority=10, preferred over custom).

**Current state**:
- Adapter exists (`src/analysis/pattern_detectors/stock_pattern_adapter.py`)
- Library never deployed (expects `/tmp/stock-pattern/src`)
- Custom adapter active by default (priority=5)

**Key decisions**:
1. How to package the library (PyPI vs Git clone vs vendoring)
2. Where to store library files in Lambda
3. Whether to use full library or extract specific functions

---

## Option Analysis

### Option 1: Install via PyPI (Recommended)

**Discovery**: The library IS on PyPI: `pip install stock-pattern`

**Implementation**:
```dockerfile
# Dockerfile.lambda.container - just add to requirements.txt
# No changes needed to Dockerfile itself
```

```txt
# requirements.txt - add line:
stock-pattern==X.X.X
```

```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py
# Change import path:

# BEFORE:
try:
    sys.path.insert(0, '/tmp/stock-pattern/src')
    import utils as stock_pattern_lib

# AFTER:
try:
    from stock_pattern import utils as stock_pattern_lib
```

**Pros**:
- Simplest deployment (just add to requirements.txt)
- Version pinning via pip
- Automatic dependency resolution
- No git in Docker build

**Cons**:
- Large dependencies (~200MB: matplotlib, mplfinance, PIL)
- May include unnecessary CLI components

**Effort**: 30 minutes
**Risk**: Low

---

### Option 2: Git Clone in Dockerfile

**Implementation**:
```dockerfile
# Dockerfile.lambda.container
FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

# Install git and clone stock-pattern
RUN yum install -y git && \
    git clone --depth 1 https://github.com/BennyThadikaran/stock-pattern.git /tmp/stock-pattern && \
    chmod -R 755 /tmp/stock-pattern && \
    yum remove -y git && \
    rm -rf /var/cache/yum

# Rest of Dockerfile...
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

**Pros**:
- Uses existing adapter code (no changes to `stock_pattern_adapter.py`)
- Gets latest version from GitHub
- Can pin to specific commit/tag

**Cons**:
- Adds git to build (temporary, can remove)
- `/tmp` in Lambda is ephemeral (but works since we COPY during build)
- Harder to track version changes

**Effort**: 45 minutes
**Risk**: Medium (git in build adds complexity)

---

### Option 3: Vendor Library Source

**Implementation**:
```
# Pre-build step (in CI or Makefile)
git clone --depth 1 https://github.com/BennyThadikaran/stock-pattern.git
cp -r stock-pattern/src vendor/stock_pattern/
rm -rf stock-pattern
```

```dockerfile
# Dockerfile.lambda.container
COPY vendor/ ${LAMBDA_TASK_ROOT}/vendor/
```

```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py
try:
    sys.path.insert(0, '/var/task/vendor')
    from stock_pattern import utils as stock_pattern_lib
```

**Directory structure**:
```
vendor/
└── stock_pattern/
    ├── __init__.py
    ├── utils.py        # Pattern detection (104KB)
    ├── Plotter.py      # Optional: chart rendering
    └── loaders/        # Optional: data loaders
```

**Pros**:
- Full control over what's included
- No external fetch during build
- Version pinned by commit in repo
- Can exclude unused components (CLI, Plotter)

**Cons**:
- Must update vendor manually
- Adds ~150KB to repo
- License compliance (GPL-3.0 requires source availability)

**Effort**: 1 hour
**Risk**: Low

---

### Option 4: Extract Core Functions Only

**Implementation**: Copy only the detection functions we need into our codebase.

From their `utils.py` (104KB), extract:
- `find_bullish_flag()` / `find_bearish_flag()`
- `find_triangles()` / `is_triangle()`
- `find_double_bottom()` / `find_double_top()`
- `find_hns()` / `find_reverse_hns()`
- `find_bullish_vcp()` / `find_bearish_vcp()`
- Helper functions: `get_atr()`, `getY()`, `make_serializable()`

**Create**:
```python
# src/analysis/pattern_detectors/stock_pattern_functions.py
"""
Extracted pattern detection functions from stock-pattern library.
Source: https://github.com/BennyThadikaran/stock-pattern
License: GPL-3.0
"""

def find_bullish_flag(sym, df, pivots, config):
    """Detect bullish flag pattern."""
    # ... extracted code
```

**Pros**:
- Minimal footprint (~20KB vs 104KB)
- No matplotlib/mplfinance dependency
- Can optimize/adapt functions
- Faster Lambda cold starts

**Cons**:
- Manual updates when library changes
- Must understand and maintain code
- GPL-3.0 implications (derivative work)
- Loses future improvements automatically

**Effort**: 3-4 hours
**Risk**: Medium (maintenance burden)

---

### Option 5: Lambda Layer

**Implementation**: Package stock-pattern as a reusable Lambda layer.

```bash
# Build layer
mkdir -p layer/python
pip install stock-pattern -t layer/python/
cd layer && zip -r stock-pattern-layer.zip python/

# Upload to AWS
aws lambda publish-layer-version \
  --layer-name stock-pattern \
  --zip-file fileb://stock-pattern-layer.zip \
  --compatible-runtimes python3.11
```

```hcl
# terraform/lambda.tf
resource "aws_lambda_function" "telegram_api" {
  layers = [
    aws_lambda_layer_version.stock_pattern.arn,
  ]
}
```

**Pros**:
- Reusable across multiple Lambdas
- Separate update cycle from main code
- Reduces main deployment size
- Can share with other projects

**Cons**:
- More infrastructure to manage
- Layer version tracking
- 5 layer limit per Lambda
- More complex deployment

**Effort**: 2 hours
**Risk**: Medium (infrastructure complexity)

---

## Recommendation Matrix

| Criterion | PyPI | Git Clone | Vendor | Extract | Layer |
|-----------|------|-----------|--------|---------|-------|
| Simplicity | 9/10 | 6/10 | 7/10 | 5/10 | 6/10 |
| Deployment size | 5/10 | 5/10 | 8/10 | 10/10 | 7/10 |
| Maintainability | 9/10 | 7/10 | 6/10 | 4/10 | 7/10 |
| Version control | 9/10 | 7/10 | 8/10 | 5/10 | 8/10 |
| Build complexity | 10/10 | 6/10 | 7/10 | 8/10 | 5/10 |
| **Total** | **42** | **31** | **36** | **32** | **33** |

---

## Recommended Approach: Option 1 (PyPI) with Optimization

**Phase 1: Quick Win (30 min)**
1. Add `stock-pattern` to requirements.txt
2. Update adapter import path
3. Deploy and verify

**Phase 2: Optimize if Needed (optional)**
If Lambda size/cold start becomes issue:
- Switch to Option 3 (Vendor) with selective imports
- Exclude matplotlib/mplfinance if not using Plotter

---

## Implementation Plan

### Step 1: Update requirements.txt

```txt
# requirements.txt - add:
stock-pattern>=1.0.0
```

### Step 2: Update Adapter Import

```python
# src/analysis/pattern_detectors/stock_pattern_adapter.py

import logging
from typing import Dict, List, Optional, Any
import pandas as pd

from .registry import PatternDetectorInterface

logger = logging.getLogger(__name__)

# Try to load stock-pattern library
stock_pattern_lib = None
STOCK_PATTERN_AVAILABLE = False

try:
    # NEW: Import from installed package
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

    # Create module-like object for compatibility
    class StockPatternLib:
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

    stock_pattern_lib = StockPatternLib()
    STOCK_PATTERN_AVAILABLE = True
    logger.info("stock-pattern library loaded successfully from PyPI package")

except ImportError as e:
    logger.debug(f"stock-pattern library not available: {e}")

# OLD code to remove:
# try:
#     sys.path.insert(0, '/tmp/stock-pattern/src')
#     import utils as stock_pattern_lib
#     ...
```

### Step 3: Verify Registration

After deployment, check logs for:
```
INFO - stock-pattern library loaded successfully from PyPI package
INFO - Registered stock-pattern adapter (priority=10)
```

### Step 4: Test Pattern Detection

```bash
# Verify stock-pattern is being used
curl https://dev-api.example.com/api/v1/report/NVDA19 | jq '.chart_patterns[].implementation'
# Should show: "stock_pattern" (not null or "custom")
```

---

## Dependencies Analysis

**stock-pattern requires**:
```
pandas>=2.0.3
numpy>=2.2.6
matplotlib>=3.10.3      # Heavy (~40MB)
mplfinance>=0.12.10b0   # Chart rendering
pillow>=11.2.1          # Image processing
fast_csv_loader>=2.0.0
questionary>=2.0.1      # CLI (not needed)
prompt-toolkit>=3.0.36  # CLI (not needed)
tqdm>=4.66.5            # Progress bars
```

**Already in our requirements.txt**:
- pandas (compatible)
- numpy (compatible)

**New dependencies**:
- matplotlib, mplfinance, pillow (chart rendering - may not be needed)
- fast_csv_loader (data loading)
- questionary, prompt-toolkit (CLI - not needed)

**Optimization opportunity**: If matplotlib adds too much size, we can:
1. Use headless matplotlib backend (AGG)
2. Vendor only `utils.py` (skip Plotter.py)

---

## Verification Checklist

- [ ] requirements.txt updated with stock-pattern
- [ ] Adapter import path updated
- [ ] Local test: `python -c "from stock_pattern import utils"`
- [ ] Docker build successful
- [ ] Deploy to dev environment
- [ ] Check CloudWatch logs for "stock-pattern library loaded"
- [ ] Check registry stats show stock_pattern registered
- [ ] API returns patterns with `implementation: "stock_pattern"`
- [ ] Compare pattern detection quality (stock_pattern vs custom)

---

## Trade-offs Made

| Decision | Alternatives | Why This Choice |
|----------|-------------|-----------------|
| PyPI install | Git clone, vendor | Simplest, standard pip workflow |
| Full package | Extract functions | Maintainability > size optimization |
| Direct import | sys.path hack | Cleaner, standard Python imports |

---

## Risk Mitigation

**Risk**: Large package size impacts cold start
**Mitigation**: Monitor cold start times; switch to vendor approach if >5s

**Risk**: matplotlib causes issues in Lambda
**Mitigation**: Use AGG backend (headless); matplotlib works in Lambda

**Risk**: Library API changes break adapter
**Mitigation**: Pin version in requirements.txt; test before upgrading

---

## Next Steps

1. [ ] Add stock-pattern to requirements.txt
2. [ ] Update adapter import path
3. [ ] Run local tests
4. [ ] Deploy to dev
5. [ ] Verify pattern detection working
6. [ ] Compare detection quality: stock-pattern vs custom
7. [ ] Document findings in research file

---

## Alternative: Hybrid Approach

If you want **both** implementations available:

```python
# src/services/pattern_detection_service.py

def __init__(self, impl_name: Optional[str] = None):
    """
    Args:
        impl_name: Force specific implementation:
            - 'stock_pattern': Use external library (if available)
            - 'custom': Use internal implementation
            - None: Auto-select (stock_pattern preferred, custom fallback)
    """
    self.impl_name = impl_name
```

**API can expose both**:
```python
# Option A: Use best available (default)
result = service.detect_patterns(ticker)

# Option B: Force specific implementation
result_stock = service.detect_patterns(ticker, impl='stock_pattern')
result_custom = service.detect_patterns(ticker, impl='custom')

# Option C: Compare both
comparison = service.compare_implementations(ticker)
```

This enables A/B testing and quality comparison between implementations.
