---
name: explain
description: Multi-stage concept explanation through clarify → search → synthesize pipeline (demonstrates command composition)
accepts_args: true
arg_schema:
  - name: concept
    required: true
    description: "Concept to explain (quoted if spaces)"
  - name: audience_level
    required: false
    description: "Optional: beginner, intermediate, expert (auto-detected if omitted)"
composition:
  - skill: research
---

# Explain Command

**Purpose**: Generate comprehensive concept explanations through multi-stage pipeline

**Core Principle**: "Explanation clarity through systematic search" - demonstrates how commands compose via sequential stages

**When to use**:
- Learning new concepts → Get structured explanation
- Onboarding team members → Generate documentation
- Documenting patterns → Capture tribal knowledge
- Teaching → Create tutorials

**Educational Value**: This command demonstrates **command composition** - how multiple stages can work together in a pipeline.

---

## Quick Reference

```bash
/explain "Lambda cold start optimization"
/explain "Aurora-First Data Architecture"
/explain "Validation gates before workflow nodes"
/explain "Research Before Iteration Principle" expert
```

---

## Three-Stage Pipeline

### Stage 1: Clarify Requirements
**What it does**:
- Determines audience level (beginner/intermediate/expert)
- Identifies context (what user knows already)
- Defines depth needed (high-level vs deep dive)
- Sets explanation format (tutorial, reference, conceptual)

**Output**: Requirements specification

---

### Stage 2: Search Knowledge
**What it does**:
- Searches CLAUDE.md for principles
- Searches skills/ for patterns
- Searches docs/ for documentation
- Searches codebase for examples
- Optionally searches web for external context

**Output**: Collected sources and examples

---

### Stage 3: Synthesize Explanation
**What it does**:
- Structures content based on requirements
- Integrates examples from codebase
- Links to related concepts
- Generates exercises (if appropriate)

**Output**: Comprehensive explanation

---

## Execution Flow

### Stage 1: Clarify Requirements

#### Step 1A: Detect or Ask Audience Level

**If level provided**:
```bash
/explain "Aurora caching" expert
# Skip detection, use expert level
```

**If level NOT provided** (auto-detect):
```bash
/explain "Aurora caching"
```

Analyze concept for complexity:
- **beginner**: Fundamental concepts, common patterns
- **intermediate**: Project-specific patterns, implementation details
- **expert**: Deep dives, trade-offs, alternatives

Ask user if uncertain:
```
🤔 Who is the audience for this explanation?

Concept: "Aurora caching"

1. Beginner - New to databases/caching
2. Intermediate - Familiar with databases, learning Aurora specifics
3. Expert - Deep dive into Aurora internals and optimization

Select level (1-3):
```

---

#### Step 1B: Determine Context

**Questions to answer**:
- What does user likely know already?
- What background is needed?
- What can we assume as prerequisite?

**Based on audience level**:
- **Beginner**: Assume minimal background, explain fundamentals
- **Intermediate**: Assume general knowledge, focus on specifics
- **Expert**: Assume deep knowledge, focus on nuances

---

#### Step 1C: Define Depth and Format

**Depth**:
- **High-level**: Conceptual understanding (what and why)
- **Implementation**: How to use (with code examples)
- **Deep dive**: Trade-offs, internals, alternatives

**Format**:
- **Tutorial**: Step-by-step guide with examples
- **Reference**: Comprehensive documentation
- **Conceptual**: Principles and patterns

---

### Stage 2: Search Knowledge Sources

#### Step 2A: Invoke Research Skill

Use `research` skill for systematic search across:

#### Step 2B: Search CLAUDE.md

```bash
grep -i "concept" .claude/CLAUDE.md
```

**Look for**:
- Principles related to concept
- Why patterns exist
- When to apply

**Example**: For "Aurora caching", find:
- Aurora-First Data Architecture principle
- Retry/Fallback Pattern
- System Boundary Principle

---

#### Step 2C: Search Skills

```bash
grep -r "concept" .claude/skills/
```

**Look for**:
- Skill documentation of pattern
- Implementation guidelines
- Anti-patterns to avoid

**Example**: For "deployment", search:
- `.claude/skills/deployment/`
- Zero-downtime patterns
- Multi-environment strategy

---

#### Step 2D: Search Documentation

```bash
find docs/ -name "*.md" -exec grep -l "concept" {} \;
```

**Look for**:
- Architecture Decision Records (ADRs)
- Implementation guides
- API documentation

**Example**: For "Aurora caching":
- `docs/adr/008-aurora-first-architecture.md`
- `docs/CODE_STYLE.md#aurora-first-data-architecture`

---

#### Step 2E: Search Codebase for Examples

```bash
grep -r "concept" src/ tests/
```

**Look for**:
- Real implementations
- Test cases showing usage
- Comments explaining why

**Example**: For "Aurora caching":
- `src/data/aurora_cache.py` - Implementation
- `tests/test_aurora_cache.py` - Usage examples

---

#### Step 2F: Search Journals/Observations (Optional)

```bash
grep -r "concept" .claude/journals/ .claude/observations/
```

**Look for**:
- Historical context (why pattern adopted)
- Evolution of understanding
- Lessons learned

---

#### Step 2G: External Search (Optional)

If concept not well-documented internally:
```
Search: {concept} + {technology stack}
```

Only if internal sources insufficient.

---

### Stage 3: Synthesize Explanation

#### Step 3A: Structure Content

**Based on audience level and depth**:

**For Beginners**:
```markdown
1. Quick Summary (1-2 sentences)
2. Why It Matters (motivation)
3. Core Concept (explain fundamentals)
4. Simple Example (minimal code)
5. Try It Yourself (exercise)
6. Next Steps (what to learn next)
```

**For Intermediate**:
```markdown
1. Quick Summary
2. Context (when/why to use)
3. How It Works (implementation)
4. In This Project (real examples)
5. Common Pitfalls
6. Related Concepts
7. Further Reading
```

**For Expert**:
```markdown
1. Quick Summary
2. Deep Dive (internals, trade-offs)
3. Alternative Approaches (comparison)
4. Implementation Details (code)
5. Performance Considerations
6. Edge Cases
7. Related Patterns
8. External References
```

---

#### Step 3B: Integrate Examples

**From codebase**:
```markdown
## In This Project

**Implementation**: `src/data/aurora_cache.py:42-58`

```python
def get_cached_report(ticker: str) -> Optional[Report]:
    """
    Retrieve pre-computed report from Aurora cache.

    Follows Aurora-First principle: Query cache first,
    no fallback to external APIs during request.
    """
    query = "SELECT report_json FROM precomputed_reports WHERE ticker = %s"
    result = execute_query(query, (ticker,))
    return result if result else None
```

**Why this works**: {Explanation from principles}
```

---

#### Step 3C: Link Related Concepts

**Identify connections**:
- Prerequisites (what to understand first)
- Related patterns (similar concepts)
- Next steps (what to learn after)

**Example**: For "Aurora caching":
```markdown
## Related Concepts

**Prerequisites**:
- Database caching basics
- AWS Aurora fundamentals

**Related Patterns**:
- Stale-While-Revalidate (UI caching)
- Precomputation strategies
- Read-through vs write-through caching

**Next Steps**:
- Cache invalidation strategies
- Aurora performance optimization
```

---

#### Step 3D: Generate Exercises (If Appropriate)

**For tutorial format**:
```markdown
## Try It Yourself

**Exercise 1**: Query the cache
```bash
# Connect to Aurora (assumes SSM tunnel active)
mysql -h localhost -P 3307 -u user -p

# Query precomputed reports
SELECT ticker, created_at FROM precomputed_reports LIMIT 5;
```

**Exercise 2**: Implement cache-first pattern
Task: Modify `get_report()` to check cache before fetching live data
Hint: See `src/data/aurora_cache.py` for reference

**Exercise 3**: Measure cache hit rate
Task: Add logging to track cache hits vs misses
Expected: 95%+ hit rate for common tickers
```

---

#### Step 3E: Create Final Explanation

```markdown
# Explanation: {Concept}

**Audience**: {beginner | intermediate | expert}
**Format**: {tutorial | reference | conceptual}
**Last updated**: {date}

---

## Quick Summary

{1-2 sentence explanation suitable for audience level}

---

## {Section 1 based on structure}

{Content from search + synthesis}

---

## {Section 2}

{...}

---

## Key Takeaways

- {Takeaway 1}
- {Takeaway 2}
- {Takeaway 3}

---

## Sources

**From this project**:
- CLAUDE.md: {section} - {principle}
- Skill: {skill_name} - {pattern}
- ADR: {adr_number} - {decision}
- Code: `{file_path}:{line}` - {example}

**External references**:
- {URL} - {description}

---

*Explanation generated by `/explain "{concept}"`*
*Generated: {timestamp}*
```

---

### Step 4: Save Explanation

Create: `.claude/explanations/{slug}.md`

**Example**: `.claude/explanations/aurora-first-data-architecture.md`

Display summary:
```
✅ Explanation complete

Concept: "Aurora-First Data Architecture"
Audience: Intermediate
Format: Reference

Sections: 7
Sources: CLAUDE.md, ADR-008, 3 code files

Output: .claude/explanations/aurora-first-data-architecture.md
```

---

## Examples

### Example 1: Beginner Level

```bash
/explain "What is Lambda cold start"
```

**Clarify**: Detects beginner (fundamental concept)

**Search**:
- CLAUDE.md: Cold Start Optimization
- docs/deployment/LAMBDA_BEST_PRACTICES.md
- src/: Module-level initialization examples

**Synthesize**:
```markdown
# Explanation: Lambda Cold Start

**Audience**: Beginner
**Format**: Tutorial

---

## Quick Summary

Lambda cold start is the initialization time when AWS Lambda creates
a new instance of your function. The first request is slow (5-10s),
subsequent requests are fast (<200ms).

---

## Why It Matters

**User impact**: First user after deployment waits 5-10 seconds for response.

**Example**: User requests stock report → Lambda needs to:
1. Download your code (1-2s)
2. Start Python runtime (1-2s)
3. Import dependencies (pandas, numpy) (3-5s)
4. Run your code (0.5s)
Total: ~8 seconds! 😱

Next request (warm): Skip steps 1-3, only run code (0.5s) ✅

---

## How It Works

**Cold start** (first request):
```
User request → AWS creates container → Download code → Start runtime
→ Import libs → Initialize → Run handler → Response (8s)
```

**Warm start** (subsequent):
```
User request → Reuse container → Run handler → Response (0.5s)
```

---

## In This Project

**Our cold start**: ~7.5 seconds (production)
**Our warm start**: ~200ms

**Optimization** (`src/services/openrouter.py`):
```python
# ❌ DON'T: Import inside function (re-imports every time)
def generate_report(ticker):
    import pandas as pd  # Slow!
    ...

# ✅ DO: Import at module level (once per container)
import pandas as pd  # Fast! (only on cold start)

def generate_report(ticker):
    ...
```

**Why this works**: Module-level imports happen once when container
starts, not on every request.

---

## Try It Yourself

**Exercise**: Measure cold vs warm start

```bash
# Cold start: Redeploy function
aws lambda update-function-code --function-name my-function

# Invoke and time (cold start)
time curl https://api.example.com/report/NVDA19
# Output: ~8 seconds

# Invoke again immediately (warm start)
time curl https://api.example.com/report/NVDA19
# Output: ~0.5 seconds
```

**Expected**: Second request 15-20x faster!

---

## Next Steps

- Learn: How to optimize cold starts (module-level init)
- Learn: How to keep Lambdas warm (scheduled pings)
- Read: docs/deployment/LAMBDA_BEST_PRACTICES.md

---

## Sources

- CLAUDE.md: Cold Start Optimization
- docs/deployment/LAMBDA_BEST_PRACTICES.md
- src/services/openrouter.py:15 (module-level imports)
```

---

### Example 2: Expert Level

```bash
/explain "Aurora-First Data Architecture" expert
```

**Clarify**: Expert level - deep dive into trade-offs

**Search**:
- CLAUDE.md: Aurora-First principle
- ADR-008: Architecture decision
- src/scheduler/: Precomputation implementation
- .claude/journals/architecture/: Related decisions

**Synthesize**:
```markdown
# Explanation: Aurora-First Data Architecture

**Audience**: Expert
**Format**: Deep dive

---

## Quick Summary

Aurora-First is a read-optimized architecture pattern where Aurora serves
as the single source of truth for all user-facing requests. Data is
pre-populated via nightly scheduler; APIs are strictly read-only.

---

## Architecture Pattern

**Write Path** (Scheduler, nightly):
```
Scheduler Lambda → yfinance API → NewsAPI → Aurora (precomputed_reports)
    ↓ 15 min/ticker × 46 tickers = ~12 hours
Aurora populated with next-day data
```

**Read Path** (User requests):
```
User → API Gateway → Lambda → Aurora query → Response (200ms avg)
```

**Critical constraint**: Read path has ZERO external API calls.

---

## Design Rationale

**Problem solved**:
- External APIs (yfinance, NewsAPI) have unpredictable latency (5-15s)
- Rate limits (yfinance: 2000 req/day, NewsAPI: 1000 req/day)
- User requests need consistent performance (<500ms)

**Trade-off**:
- ✅ Pro: Predictable latency (Aurora <50ms)
- ✅ Pro: No rate limit concerns (APIs called once/day per ticker)
- ✅ Pro: Cost efficiency (fewer API calls)
- ❌ Con: Data can be stale (up to 24h)
- ❌ Con: Precomputation overhead (12h nightly job)

**When this pattern fits**:
- Data changes daily (stock prices after market close) ✅
- Users tolerate 24h staleness ✅
- Predictable performance > real-time data ✅

**When NOT to use**:
- Real-time requirements (intraday trading) ❌
- Unpredictable data needs (arbitrary ticker queries) ❌

---

## Implementation Details

**Precomputation** (`src/scheduler/ticker_fetcher_handler.py`):
```python
@scheduled_event(cron="0 5 * * ? *")  # 5 AM Bangkok time
def populate_aurora(event, context):
    for ticker in TICKER_MASTER:
        # Fetch from external APIs (with retry/fallback)
        ticker_data = fetch_with_exponential_backoff(ticker)
        news_data = fetch_news_with_fallback(ticker)

        # Compute report (LLM synthesis)
        report = generate_report(ticker_data, news_data)

        # Store in Aurora
        save_to_aurora(ticker, report)
```

**API Read** (`src/telegram/report_handler.py`):
```python
def get_report(ticker: str) -> Report:
    # Aurora-only query (NO external API fallback)
    report = query_aurora("SELECT report_json FROM precomputed_reports WHERE ticker = %s", ticker)

    if not report:
        # Fail fast - do NOT call external APIs
        raise DataNotAvailableError(f"Report for {ticker} not found")

    return report
```

**Why NO fallback**: Fallback to external APIs would:
- Introduce 5-15s latency (defeats the purpose)
- Risk rate limit exhaustion
- Create inconsistent performance (some fast, some slow)

---

## Failure Modes

### Failure 1: Precomputation Fails
**Symptom**: Aurora has no data for ticker
**Impact**: API returns 404
**Mitigation**: Monitor precomputation job, alert on failures

### Failure 2: Stale Data Beyond 24h
**Symptom**: Reports older than expected
**Impact**: User sees outdated analysis
**Mitigation**: Scheduler success monitoring, SLA alerts

### Failure 3: Aurora Performance Degradation
**Symptom**: Queries > 100ms
**Impact**: Slow API responses
**Mitigation**: Aurora query optimization, indexing

---

## Alternative Approaches

### Approach 1: Compute-on-Demand
**Pattern**: Call external APIs during user request

**Pros**:
- Always fresh data
- No precomputation overhead

**Cons**:
- Unpredictable latency (5-15s)
- Rate limit risk
- Higher API costs

**When better**: Intraday updates required

---

### Approach 2: Hybrid (Cache + Fallback)
**Pattern**: Try Aurora first, fallback to live API

**Pros**:
- Best of both worlds
- Handles arbitrary tickers

**Cons**:
- Inconsistent latency (cache: 200ms, miss: 8s)
- Complex fallback logic
- Still risk rate limits

**When better**: Unpredictable ticker queries

---

## Performance Characteristics

**Measured (production)**:
- Aurora query: p50: 42ms, p95: 87ms, p99: 120ms
- API response: p50: 180ms, p95: 350ms, p99: 500ms
- Cache hit rate: 98.7% (46/46 tickers populated)

**Optimization potential**:
- Add Aurora read replica → p95 < 50ms
- Add CDN caching → p50 < 100ms (API Gateway level)

---

## Related Patterns

**Similar**:
- **Materialized Views** (databases): Pre-computed query results
- **Static Site Generation** (web): Pre-render pages at build time
- **Content Delivery Network**: Pre-position content geographically

**Complementary**:
- **Stale-While-Revalidate** (frontend): Show cache while fetching fresh
- **Circuit Breaker** (resilience): Prevent cascade failures

**Contrasts**:
- **Cache-Aside**: Write-through on cache miss (we don't)
- **Event Sourcing**: Replay events to rebuild state (we don't)

---

## Evolution History

**Original** (6 months ago):
- Direct API calls during user requests
- Problem: Timeouts, rate limits

**Migration** (ADR-008):
- Adopted Aurora-First
- Impact: 98% latency reduction

**Current refinement**:
- Loud Mock pattern for dev speed
- Research Before Iteration for scheduler bugs

---

## Sources

**Internal**:
- ADR-008: Aurora-First Architecture Decision
- CLAUDE.md: Aurora-First Data Architecture principle
- src/scheduler/ticker_fetcher_handler.py:42-89
- src/telegram/report_handler.py:67-82

**External**:
- Materialized Views pattern: https://...
- Cache-Aside pattern: https://...
```

---

## Directory Structure

```
.claude/
├── explanations/         # NEW: Generated explanations
│   ├── lambda-cold-start.md
│   ├── aurora-first-data-architecture.md
│   └── ...
```

---

## Integration with Other Commands

### Explain → Journal
```
/explain "Pattern X"
    ↓ (generates comprehensive explanation)
If pattern significant:
    ↓
/journal pattern "Pattern X" (link to explanation)
```

### Validate → Explain
```
/validate "Claim about concept"
    ↓ (need to understand concept to validate)
/explain "Concept"
    ↓ (now understand concept, can validate)
```

### Teach New Team Member
```
/explain "Aurora caching" beginner
/explain "Deployment workflow" intermediate
/explain "Testing tiers" beginner
    ↓ (series of explanations form onboarding docs)
```

---

## Principles

### 1. Search Before Creating

Don't invent explanations. Search internal docs first, use existing knowledge.

### 2. Examples from Reality

Always include real code examples from the project, not hypotheticals.

### 3. Level-Appropriate Depth

Beginners need motivation and simple examples. Experts need trade-offs and alternatives.

### 4. Link Related Concepts

Explanations should connect to broader knowledge graph.

### 5. Preserve Sources

Always cite where information came from (CLAUDE.md, ADRs, code).

---

## Why This Demonstrates Composition

`/explain` shows how commands can have **internal stages**:

**Stage 1** (Clarify) uses:
- User interaction (ask questions)
- Heuristics (detect level from concept complexity)

**Stage 2** (Search) uses:
- `research` skill (systematic search methodology)
- Multiple search tools (Grep, Read, Glob)
- Multiple sources (CLAUDE.md, skills, docs, code)

**Stage 3** (Synthesize) uses:
- Templating (structure based on audience)
- Integration (combine sources into coherent explanation)
- Generation (create exercises, examples)

**This pattern** can be applied to other commands:
- Multi-stage validation
- Multi-phase deployment
- Iterative refinement workflows

---

## Related Commands

- `/validate` - May need to explain concept to validate claim
- `/journal` - Can reference explanations
- `/search` - Simpler version of Stage 2
- All commands - Can be explained via `/explain`

---

## See Also

- `.claude/commands/README.md` - Command composition patterns
- `.claude/skills/research/` - Search methodology
- `.claude/CLAUDE.md` - Principles to explain
