# Telegram Mini App Acceptance Criteria

**Objective**: Web dashboard via Telegram Mini App
**Last Updated**: 2026-01-13

---

## What is Acceptance?

Acceptance criteria define **when work is "done"**. They are the conditions that must be met before claiming completion.

---

## Feature: View Dashboard

### Acceptance Criteria

#### Functional
- [ ] Mini App opens from Telegram
- [ ] Watchlist displays with current prices
- [ ] Tickers are clickable
- [ ] Prices update on refresh

#### Performance
- [ ] Initial load < 3 seconds
- [ ] Data fetch < 1 second
- [ ] No jank during scrolling

#### Visual
- [ ] Theme matches Telegram
- [ ] Responsive on mobile
- [ ] Loading states visible

### Verification
```bash
# Manual in Telegram:
# 1. Open Mini App
# 2. Time initial load
# 3. Verify watchlist appears
# 4. Click refresh, verify update
```

---

## Feature: View Stock Report

### Acceptance Criteria

#### Functional
- [ ] Selecting ticker shows report
- [ ] Report has all sections (market, analysis, recommendation)
- [ ] Data is current (today's prices)
- [ ] Back navigation works

#### Performance
- [ ] Report loads < 2 seconds
- [ ] Chart renders < 1 second

#### API
- [ ] GET /api/v1/report/{ticker} returns 200
- [ ] Response matches TypeScript types
- [ ] Invalid ticker returns 404

### Verification
```bash
# API test
curl https://api.{env}.example.com/api/v1/report/ADVANC | jq '.ticker'

# Manual:
# 1. Select ticker from list
# 2. Verify report displays
# 3. Check all sections present
# 4. Navigate back
```

---

## Feature: Interactive Chart

### Acceptance Criteria

#### Functional
- [ ] Candlestick chart renders
- [ ] OHLCV data accurate
- [ ] Zoom in/out works
- [ ] Pan works
- [ ] Tooltip shows data on hover

#### Pattern Overlays
- [ ] Toggle button visible
- [ ] Patterns render when enabled
- [ ] Patterns align with candles
- [ ] Legend shows pattern types

#### Performance
- [ ] Chart renders < 1 second
- [ ] Interactions feel smooth (60fps)
- [ ] No excessive re-renders

### Verification
```bash
# Manual:
# 1. Open report with chart
# 2. Verify candles display
# 3. Zoom in, verify data
# 4. Enable pattern overlay
# 5. Verify patterns align
```

---

## Feature: Generate PDF Report

### Acceptance Criteria

#### Functional
- [ ] "Generate PDF" button visible
- [ ] Progress indicator shown
- [ ] PDF downloads successfully
- [ ] PDF contains all report sections
- [ ] Share via Telegram works

#### Performance
- [ ] Generation < 30 seconds
- [ ] Progress updates every 5 seconds

#### Error Handling
- [ ] Timeout shows retry option
- [ ] Error shows friendly message

### Verification
```bash
# Manual:
# 1. Click Generate PDF
# 2. Verify progress shown
# 3. Verify PDF downloads
# 4. Open PDF, verify content
# 5. Test share button
```

---

## Deployment Acceptance

### Pre-Deployment

#### Backend
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Docker image builds
- [ ] No security vulnerabilities

#### Frontend
- [ ] Build succeeds (`npm run build`)
- [ ] No TypeScript errors
- [ ] No lint errors
- [ ] Bundle size < 500KB gzipped

### Post-Deployment

#### Backend
- [ ] Health endpoint returns 200
- [ ] CloudWatch logs show activity
- [ ] No errors in first 5 minutes
- [ ] Langfuse traces appearing

#### Frontend
- [ ] CloudFront serving new version
- [ ] Cache invalidated
- [ ] No console errors
- [ ] Lighthouse score > 90

### Rollback Criteria
Rollback immediately if:
- [ ] API returns 500 errors
- [ ] Frontend shows blank page
- [ ] > 5% error rate
- [ ] Performance degraded > 50%

---

## Component Acceptance Template

For each new component:

### Design
- [ ] Props interface defined (TypeScript)
- [ ] State requirements identified
- [ ] Loading/error states designed
- [ ] Mobile responsive

### Implementation
- [ ] Component created in correct directory
- [ ] Props typed correctly
- [ ] Hooks at top level
- [ ] Error handling implemented

### Styling
- [ ] TailwindCSS classes used
- [ ] Telegram theme colors
- [ ] Responsive breakpoints

### Testing
- [ ] Renders without error
- [ ] Loading state works
- [ ] Error state works
- [ ] User interactions work

---

## Claiming "Done"

Use this template:

```markdown
## Telegram Work Complete: {description}

**Environment**: {dev | stg | prd}
**Component**: {backend | frontend | both}

### Acceptance Verified
- [x] Functional: {specific criteria}
- [x] Performance: {metrics observed}
- [x] Visual: {screenshot evidence}

### Invariant Convergence
- [x] Level 4 (Config): Env vars set, build succeeds
- [x] Level 3 (Infra): Connectivity verified
- [x] Level 2 (Data): Types correct, data fresh
- [x] Level 1 (Service): APIs respond, components render
- [x] Level 0 (User): End-to-end working

### Evidence
- API response: {curl output or screenshot}
- Frontend: {screenshot}
- Langfuse trace: {trace ID}
- Lighthouse: {score}

**Convergence**: delta = 0
```

---

*Objective: telegram*
*Spec: .claude/specs/telegram/spec.yaml*
