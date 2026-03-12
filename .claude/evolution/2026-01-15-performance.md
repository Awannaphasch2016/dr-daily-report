# Knowledge Evolution Report

**Date**: 2026-01-15
**Period reviewed**: Performance analysis session (2026-01-15)
**Focus area**: Frontend performance (Telegram Mini App)

---

## Executive Summary

**Drift detected**: 3 areas
**New patterns**: 5 patterns discovered
**Abandoned patterns**: 0
**Proposed updates**: 7 proposals (all implemented)

**Overall assessment**: Moderate drift - performance practices not previously documented, now codified into skills and invariants.

---

## Drift Analysis

### Positive Drift: Performance Skill Created

**What changed**: Created comprehensive performance investigation skill based on real analysis work.

**Evidence** (from session):
- Validated modal reload issue in `App.tsx:111-118`
- Identified React Query installed but unused
- Documented Core Web Vitals terminology gap
- Created metrics-to-code mapping

**Before** (no documentation):
```
No documented process for:
- Performance investigation workflow
- Core Web Vitals terminology
- Metrics → Code mapping
- Frontend optimization patterns
```

**After** (skill created):
```
.claude/skills/performance-investigation/
├── SKILL.md              # Decision tree and workflow
├── METRICS-GLOSSARY.md   # Web Vitals terminology
├── METRICS-MAP.md        # Metrics → Code mapping
├── OPTIMIZATION-PATTERNS.md  # 10 concrete patterns
├── TOOLS.md              # DevTools, CloudWatch, libraries
└── CHECKLIST.md          # Step-by-step procedure
```

**Why it's better**:
- Systematic approach to performance issues
- Terminology reference for future sessions
- Code locations mapped to metrics
- Prioritized optimization patterns

**Status**: ✅ IMPLEMENTED

---

### New Pattern: Cache-First Loading

**Where found**: Performance analysis of `App.tsx:handleSelectMarket`

**Pattern description**:
```typescript
// BAD: Always fetch (current)
const handleSelectMarket = (market: Market) => {
  fetchReport(market.id);  // ALWAYS fetches, even if data exists
};

// GOOD: Cache-first (recommended)
const handleSelectMarket = (market: Market) => {
  const hasCompleteData = market.report?.all_scores?.length > 0;
  if (!hasCompleteData) {
    fetchReport(market.id);  // Only fetch if needed
  }
};
```

**Impact**: ~1000ms saved per repeat click

**Graduation path**:
- [x] Added to optimization patterns skill
- [x] Added to docs/deployment/PERFORMANCE.md
- [ ] Implement in frontend code (future task)

**Status**: ✅ DOCUMENTED (implementation pending)

---

### New Pattern: React Query Unused

**Where found**: `package.json` shows `@tanstack/react-query` installed, but no usage in codebase.

**Pattern description**:
React Query provides:
- Automatic caching
- Request deduplication
- Stale-while-revalidate
- Loading/error states

Currently using manual Zustand fetching without these benefits.

**Graduation path**:
- [x] Documented as optimization opportunity
- [ ] Implement React Query hooks (future task)

**Status**: ✅ DOCUMENTED (implementation pending)

---

### Invariant Update: Performance SLAs

**What changed**: Added Core Web Vitals SLAs to invariant documents.

**Before**:
```markdown
### Performance
- [ ] Initial load < 3s
```

**After**:
```markdown
### Performance (Core Web Vitals)
- [ ] LCP (Largest Contentful Paint) < 2.5s
- [ ] INP (Interaction to Next Paint) < 200ms
- [ ] CLS (Cumulative Layout Shift) < 0.1
- [ ] Modal interaction response < 100ms
```

**Files updated**:
- `.claude/invariants/frontend-invariants.md`
- `.claude/specs/telegram/invariants.md`

**Status**: ✅ IMPLEMENTED

---

## Files Created

| File | Purpose |
|------|---------|
| `.claude/skills/performance-investigation/SKILL.md` | Entry point, decision tree |
| `.claude/skills/performance-investigation/METRICS-GLOSSARY.md` | Core Web Vitals terminology |
| `.claude/skills/performance-investigation/METRICS-MAP.md` | Metrics → Code locations |
| `.claude/skills/performance-investigation/OPTIMIZATION-PATTERNS.md` | 10 optimization patterns |
| `.claude/skills/performance-investigation/TOOLS.md` | DevTools, CloudWatch, libraries |
| `.claude/skills/performance-investigation/CHECKLIST.md` | Investigation procedure |

---

## Files Updated

| File | Change |
|------|--------|
| `.claude/skills/README.md` | Added skill #11 (performance-investigation) |
| `.claude/invariants/frontend-invariants.md` | Added Core Web Vitals SLAs, performance anti-patterns |
| `.claude/specs/telegram/invariants.md` | Added performance SLAs, known patterns table |
| `docs/deployment/PERFORMANCE.md` | Added frontend section with patterns |

---

## Action Items

### Completed (This Session)
- [x] Created performance-investigation skill (6 files)
- [x] Updated frontend-invariants.md with Core Web Vitals
- [x] Updated telegram/invariants.md with performance SLAs
- [x] Updated docs/deployment/PERFORMANCE.md with frontend section
- [x] Updated skills README with skill #11

### Implementation Backlog (Future)
- [ ] Implement cache-first loading in `App.tsx`
- [ ] Enable React Query for automatic caching
- [ ] Add code splitting to `vite.config.ts`
- [ ] Add skeleton loading to modal components
- [ ] Add Web Vitals monitoring to `main.tsx`
- [ ] Increase Lambda memory if cold starts persist

---

## Priority Matrix

| Pattern | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Cache-First Loading | High | Low | **Do First** |
| Skeleton States | Medium | Low | **Do First** |
| Web Vitals Monitoring | Low (enables others) | Low | **Do First** |
| React Query | High | Medium | **This Sprint** |
| Code Splitting | Medium | Medium | **This Sprint** |
| Search Debounce | Low | Low | **Quick Win** |

---

## Metrics

**Review scope**:
- Validations reviewed: 5
- Journals reviewed: 3
- Frontend files analyzed: 10+
- Backend files analyzed: 5+

**Documentation updates**:
- High priority: 4 files updated
- Skills created: 1 (6 files)
- Invariants enhanced: 2 files

---

## Next Evolution Review

**Recommended**: 2026-02-15

**Focus areas for next time**:
- Verify if cache-first implemented
- Check React Query adoption
- Measure actual Core Web Vitals improvement
- Review pattern precompute impact on latency

---

*Report generated by `/evolve performance`*
*Generated: 2026-01-15*
