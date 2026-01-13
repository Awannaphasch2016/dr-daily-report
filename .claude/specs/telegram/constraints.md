# Telegram Mini App Constraints

**Objective**: Web dashboard via Telegram Mini App
**Last Updated**: 2026-01-13

---

## What Are Constraints?

Constraints are **learned restrictions** from experience. Unlike invariants (WHAT must hold), constraints define HOW we must operate.

---

## Platform Constraints

### Telegram Mini App
- **Viewport**: Must be responsive (320px - 1024px width)
- **SDK Version**: Use latest Telegram WebApp SDK
- **Theme**: Must respect Telegram theme colors
- **Back button**: Must handle Telegram back button properly
- **Share**: Native share uses Telegram's share sheet

### API Gateway HTTP
- **Timeout**: 30 seconds max
- **Payload size**: 10MB max request body
- **CORS**: Must configure for Mini App origin
- **Throttling**: Default rate limits apply

### Lambda
- **Cold start**: ~3-5s for Python with dependencies
- **Memory**: 1024MB for API processing
- **VPC**: Required for Aurora access
- **Concurrent executions**: Account limit applies

### Aurora MySQL
- **Connection limit**: Max 90 concurrent (db.t3.medium)
- **Query timeout**: Long queries affect response time
- **Timezone**: Must match Lambda TZ setting

### Frontend Build
- **Bundle size**: Target < 500KB gzipped
- **Initial load**: Target < 3s on 3G
- **Lazy loading**: Charts should be lazy loaded
- **Cache**: Static assets should have long cache TTL

---

## Learned Constraints (From Incidents)

### TC-001: Use VPC Gateway Endpoint for S3
**Discovered**: 2026-01 (NAT Gateway saturation)
**Constraint**: PDF storage operations must use VPC Gateway Endpoint
**Why**: NAT Gateway has connection rate limits
**Evidence**: First N PDF operations succeed, last M timeout
**Implementation**: Terraform VPC endpoint configuration

### TC-002: Always Show Loading States
**Discovered**: 2025-12 (user confusion)
**Constraint**: Every async operation must show loading indicator
**Why**: Users think app is broken without feedback
**Implementation**: Zustand `isLoading` state per operation

### TC-003: Handle Telegram Theme Changes
**Discovered**: 2025-11 (dark mode bugs)
**Constraint**: Theme must update when Telegram theme changes
**Why**: Telegram can change theme while app is open
**Implementation**: Listen to `themeChanged` event

### TC-004: Debounce Chart Interactions
**Discovered**: 2026-01 (performance issues)
**Constraint**: Zoom/pan events must be debounced (100ms)
**Why**: Rapid events cause excessive re-renders
**Implementation**: Use lodash debounce on chart handlers

### TC-005: Validate API Responses
**Discovered**: 2025-12 (runtime errors)
**Constraint**: All API responses must be validated against types
**Why**: Backend changes can break frontend silently
**Implementation**: Zod schemas for API responses

### TC-006: Pre-fetch Adjacent Data
**Discovered**: 2025-11 (UX improvement)
**Constraint**: When viewing ticker, pre-fetch adjacent tickers
**Why**: Smoother navigation experience
**Implementation**: Background fetch in Zustand store

### TC-007: Never Block on PDF Generation
**Discovered**: 2025-12 (timeout incidents)
**Constraint**: PDF generation must be async with progress
**Why**: Can take > 10s, users abandon if blocked
**Implementation**: Polling endpoint with progress updates

---

## Environment-Specific Constraints

### dev
```yaml
allowed:
  - Local API server (localhost)
  - Mock Telegram SDK
  - Stale data up to 48 hours
  - Debug logging enabled
  - React DevTools
  - Hot module replacement

forbidden:
  - Production API endpoint
  - Real Telegram auth
```

### stg
```yaml
allowed:
  - Staging API endpoint
  - Debug logging
  - Stale data up to 24 hours
  - Test Telegram bot

forbidden:
  - Production API
  - Mock SDK (must test real integration)
```

### prd
```yaml
allowed:
  - Production API only
  - Stale data up to 24 hours

forbidden:
  - Debug logging (performance)
  - Mock anything
  - DevTools in bundle
  - Source maps exposed
```

---

## React/TypeScript Constraints

### State Management
- [ ] No direct state mutation (use Zustand actions)
- [ ] No `any` types (except legacy migration)
- [ ] No inline styles (use TailwindCSS)
- [ ] No console.log in production

### Component Patterns
- [ ] Functional components only (no class components)
- [ ] Custom hooks for reusable logic
- [ ] Error boundaries for each page
- [ ] Memo for expensive computations

### Performance
- [ ] Lazy load routes
- [ ] Virtualize long lists (> 50 items)
- [ ] Image optimization (WebP, lazy load)
- [ ] Bundle splitting by route

---

## Adding New Constraints

When you discover something that MUST or MUST NOT be done:

1. **Document in this file** with:
   - Unique ID (TC-XXX)
   - When discovered
   - What the constraint is
   - Why it exists
   - Evidence (incident, audit, or test)

2. **Link to journal entry** if applicable

3. **Consider if it's actually an invariant**:
   - Constraint = HOW to operate
   - Invariant = WHAT must hold

---

*Objective: telegram*
*Spec: .claude/specs/telegram/spec.yaml*
