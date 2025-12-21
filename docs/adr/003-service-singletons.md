# ADR-003: Service Singletons vs Dependency Injection

**Status:** ✅ Accepted
**Date:** 2024-01
**Deciders:** Development Team

## Context

AWS Lambda functions require service initialization (e.g., loading CSV data, database connections). Container reuse is common - Lambda may reuse the same container for multiple invocations.

### Initialization Patterns Considered

1. **Dependency Injection (DI)**: Pass services as constructor parameters
2. **Service Singletons**: Module-level global instances
3. **Request-Scoped**: Create new service instance per request

### Constraints

- Lambda cold start time matters (affects user experience)
- CSV ticker data (~2000 tickers) should load once, not per request
- Testing requires ability to mock services
- Team prefers simple patterns over frameworks

## Decision

Use module-level global singletons with lazy initialization for all API services.

### Pattern

```python
# src/api/ticker_service.py
_service: Optional[TickerService] = None

def get_ticker_service() -> TickerService:
    global _service
    if _service is None:
        _service = TickerService()  # Loads CSV on first call
    return _service

# Usage
service = get_ticker_service()
tickers = service.search("NVDA")
```

### Services Using This Pattern

- `TickerService`: CSV ticker data (~2000 tickers)
- `RankingsService`: Aurora query service
- `PeerSelector`: Correlation calculations
- `WatchlistService`: DynamoDB operations
- `JobService`: DynamoDB job tracking
- `Transformer`: Report transformation logic

## Consequences

### Positive

- ✅ **Lambda Cold Starts**: Container reuse preserves singletons (no re-init)
- ✅ **Performance**: CSV data loaded once per container, not per request
- ✅ **Memory Efficiency**: Single service instance vs multiple per request
- ✅ **Simplicity**: No DI container framework needed
- ✅ **Explicit Lifecycle**: Easy to understand when services are initialized

### Negative

- ❌ **Testing Complexity**: Requires patching globals to mock services
- ❌ **Less Flexible**: Can't easily swap implementations
- ❌ **Hidden Dependencies**: Global state not visible in function signatures
- ❌ **Race Conditions**: Possible if Lambda concurrency > 1 per container (rare)

### Mitigation Strategies

**For Testing:**
```python
# tests/conftest.py
@pytest.fixture(autouse=True, scope='function')
def reset_api_singletons():
    """Reset singletons before each test"""
    import src.api.ticker_service as ticker_mod
    ticker_mod._service = None
    yield
```

**For Flexibility:**
- Services are stateless (can be replaced without side effects)
- Environment variables control behavior (no hardcoded config)

## Alternatives Considered

### Alternative 1: Dependency Injection Framework

**Example:**
```python
from dependency_injector import containers, providers

class ServiceContainer(containers.DeclarativeContainer):
    ticker_service = providers.Singleton(TickerService)
    rankings_service = providers.Singleton(RankingsService)

container = ServiceContainer()
```

**Why Rejected:**
- Adds framework dependency (dependency-injector, punq)
- Increases complexity for minimal benefit in Lambda environment
- Team unfamiliar with DI frameworks
- Lambda container reuse already provides singleton behavior

### Alternative 2: Request-Scoped Services

**Example:**
```python
# Create new service per request
def handler(event, context):
    ticker_service = TickerService()  # Re-loads CSV every time
    return ticker_service.search("NVDA")
```

**Why Rejected:**
- Performance: Re-loading CSV (2000 tickers) on every request
- Memory: Multiple service instances consume more RAM
- Cost: Slower responses increase Lambda execution time

### Alternative 3: Manual Dependency Injection

**Example:**
```python
# Pass services explicitly
def process_ticker(ticker: str, service: TickerService):
    return service.search(ticker)

# Caller must inject
service = TickerService()
result = process_ticker("NVDA", service)
```

**Why Rejected:**
- Boilerplate: Every function needs service parameters
- Lambda handlers have fixed signatures (can't inject cleanly)
- No significant testability improvement vs global singletons

## References

- Service Implementations: `src/api/*.py`
- Test Reset Pattern: `tests/conftest.py:reset_api_singletons`
- Lambda Container Reuse: https://aws.amazon.com/blogs/compute/container-reuse-in-lambda/

## Decision Drivers

1. **Lambda Performance**: Container reuse makes singletons natural fit
2. **Simplicity**: Team preference for explicit over framework magic
3. **CSV Loading Cost**: 2000-ticker CSV must load once, not per request

## Performance Impact

**Cold Start (First Request):**
- With Singletons: Load CSV once = ~200ms
- Without Singletons: Load CSV per request = ~200ms per request

**Warm Requests (Container Reuse):**
- With Singletons: CSV already loaded = ~0ms overhead
- Without Singletons: Reload CSV = ~200ms per request

**Verdict:** Singletons provide ~200ms improvement per warm request.
