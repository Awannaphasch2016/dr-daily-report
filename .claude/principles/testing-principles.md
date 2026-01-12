# Testing Principles Cluster

**Load when**: Writing tests, fixing test failures, improving test coverage, reviewing test quality

**Principles**: #10, #19

**Related skills**: [testing-workflow](../skills/testing-workflow/)

---

## Principle #10: Testing Anti-Patterns Awareness

Test outcomes, not execution. Verify results, not just that functions were called. MagicMock defaults are truthy—explicitly mock failure states. Round-trip tests for persistence. Database operations fail without exceptions—check rowcount. After writing test, break code to verify test catches it.

**Deployment fidelity testing**: Test deployment artifacts (Docker images with Lambda base image), not just source code. Validates imports work in `/var/task`, catches environment mismatches before deployment.

**Common anti-patterns**:
- ❌ Testing imports locally only (local ≠ Lambda)
- ❌ Mocking all environment (hides missing config)
- ❌ Only testing deployed systems (doesn't catch fresh deployment gaps)
- ❌ Assuming local tests pass = Lambda works

**Test sabotage verification**: After writing a test, intentionally break the code. If test still passes, test is useless.

**Real incidents**: LINE bot 7-day outage (ImportError in Lambda, not local), query_tool_handler deployment blocker.

See [testing-workflow skill](../skills/testing-workflow/) for test patterns, anti-patterns, and comprehensive checklists.

---

## Principle #19: Cross-Boundary Contract Testing

Test transitions between execution phases, service components, data domains, and temporal states—not just behavior within a single boundary. Integration tests against deployed systems miss contract violations at **boundary crossings** where assumptions, configurations, or type systems change.

**Boundary types**:
- **Phase**: Build → Runtime (Docker container import tests)
- **Service**: Lambda → Aurora (connection, schema)
- **Data**: Python → JSON (type conversion, special values)
- **Time**: 23:59 → 00:00 (date boundary cache keys)

**When to apply**:
- Before deployment (phase boundaries)
- When integrating services (service boundaries)
- When handling user input (data boundaries)
- When dealing with time-sensitive operations (time boundaries)

**Test pattern template**:
```python
def test_<source>_to_<target>_boundary():
    """<Boundary type>: <Source> → <Target>

    Tests that <contract> is upheld when crossing boundary.
    """
    # 1. Set up boundary conditions (remove mocks)
    # 2. Invoke the transition
    # 3. Verify contract upheld
    # 4. Clean up
```

See [Cross-Boundary Contract Testing Guide](../../docs/guides/cross-boundary-contract-testing.md).

---

## Test Tiers Quick Reference

| Tier | Command | Includes | Use Case |
|------|---------|----------|----------|
| 0 | `pytest --tier=0` | Unit only | Fast local iteration |
| 1 | `pytest` (default) | Unit + mocked | Deploy gate |
| 2 | `pytest --tier=2` | + integration | Nightly |
| 3 | `pytest --tier=3` | + smoke | Pre-deploy |
| 4 | `pytest --tier=4` | + e2e | Release |

---

## Quick Checklist

Writing a new test:
- [ ] Testing outcomes, not execution
- [ ] MagicMock failure states explicitly set
- [ ] Round-trip test for persistence (if applicable)
- [ ] Test sabotage verification (break code, test should fail)

Boundary tests:
- [ ] Docker container import test (phase boundary)
- [ ] Real API Gateway event structure (service boundary)
- [ ] Special value handling (NaN, null) for data boundaries
- [ ] Date boundary tests with freeze_time

Before PR:
- [ ] `pytest` passes (Tier 1)
- [ ] Docker import tests pass
- [ ] No new anti-patterns introduced

---

*Cluster: testing-principles*
*Last updated: 2026-01-12*
