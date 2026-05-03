---
name: Rate-limit solutions for dev precompute
description: Divergent exploration of fixes for the "14 of 56 tickers silently dropped" problem caused by Yahoo per-IP rate limiting
type: research
date: 2026-05-03
focus: comprehensive
---

# Research: Solving the precompute rate-limit problem (dev)

**Date**: 2026-05-03
**Focus**: comprehensive (effort × effectiveness × cost × risk, equal weight)
**Companion**: `docs/architecture/c4-plantuml/rendered/rate_limit_solutions.html`

---

## Problem one-liner

46 parallel report-workers in dev share one NAT egress IP and hit Yahoo Finance simultaneously every 5 AM. Yahoo throttles the IP, ~14 of 56 workers exhaust their fixed `2s × 3` retry budget, and the SFN Map state silently drops them — Aurora ends up with 42 of 56 rows and no alarm fires.

## Mental framework: 3 zones to intervene

```
[SOURCE: 46 workers]  →  [PIPE: shared NAT IP]  →  [SINK: Yahoo per-IP limit]
```

Every fix lands in exactly one zone. Knowing the zone tells you the trade-off shape:
- **SOURCE** fixes = control behavior of *our* code. Cheap, low-risk, but at best mitigates — doesn't structurally remove the dependency.
- **PIPE** fixes = expand the egress surface. Modest cost, AWS-native, helps but adds infra.
- **SINK** fixes = avoid the throttled service. Highest leverage, biggest change.

## Solution space (8 candidates, organized by zone)

### Zone: SOURCE

#### Option 1 — Lower `MaxConcurrency` 46 → 8
**How**: Single value change in `terraform/step_functions/precompute_workflow.json:32`. Spreads 56 calls over ~7 sequential batches of 8.
**Pros**: One-line change, reversible, no new components. Coverage usually approaches 56/56.
**Cons**: Total runtime goes from ~6 min to ~30 min. Doesn't fix the root cause — still hits same per-IP limit, just less aggressively.
**Examples**: Standard SFN throttling pattern; AWS Solutions blog uses 4-8 for upstream-bound work.

#### Option 2 — Exponential backoff + jitter
**How**: Replace `time.sleep(2)` × 3 in `data_fetcher.py:183` with `sleep(2,4,8) + random.uniform(0,1)`. Add a 4th retry at 16s.
**Pros**: Pure code, no infra. Survives transient throttle without slowing the fast path. Industry standard.
**Cons**: Doesn't help if Yahoo's window is >30s — workers still time out at the Lambda level.
**Examples**: AWS SDK default retry strategy; `tenacity` library.

#### Option 8 — Step Functions Wait+retry orchestration
**How**: Wrap each worker invoke in a Choice→Wait(60s)→Retry pattern at SFN level so failed tickers re-run after a delay.
**Pros**: SFN-native, observable in execution graph.
**Cons**: Costs more SFN state transitions per ticker. Doesn't reduce burst, just gives more total time.

### Zone: PIPE

#### Option 4 — NAT Gateway per AZ + Lambda subnet spread
**How**: dev currently runs Lambda in one or two AZs with one NAT. Spread Lambda across 3 AZs each with its own NAT (3 distinct egress IPs). Yahoo's per-IP budget triples.
**Pros**: AWS-native, no application changes, applies to *all* future Yahoo callers (telegram-api, slack-bot, ad-hoc) at once.
**Cons**: ~$32/AZ/month per extra NAT (×2 = $64/mo dev). Won't help if Yahoo bans the whole VPC ASN range.
**Examples**: Standard AWS multi-AZ pattern; recommended in AWS Lambda VPC best practices.

#### Option 7 — Residential / datacenter proxy pool
**How**: Route Yahoo calls through a paid proxy service (Bright Data, Oxylabs) with rotating IPs.
**Pros**: Effectively unlimited IPs.
**Cons**: $50–500/mo, **legal/ToS grey area** — Yahoo's ToS forbids circumvention; this is the kind of fix that works until it doesn't, then locks the whole account.
**Verdict**: Mention only as a last resort; do not recommend.

### Zone: SINK

#### Option 3 — Single-writer daily price cache (Aurora-backed) ★
**How**: One scheduled Lambda fetches each ticker once per day from Yahoo, stores rows in `daily_prices` / `daily_indicators`. Report-workers read from those tables (zero Yahoo calls during precompute fan-out).
**Pros**: Eliminates the rate-limit entirely from the precompute path. The cache table already exists schema-wise. One-Yahoo-call-per-ticker-per-day fits comfortably under any limit. Same shape as the deferred A4 fix in the PDF GORE — *both problems are "46 workers contending for a shared dependency"*.
**Cons**: Needs a new Lambda + scheduling. Doesn't help live `@dr-daily-report` queries that need fresher prices (but the daily report is by definition end-of-day data, so this is fine).
**Examples**: This is the textbook materialized-cache pattern (e.g., Reuters EoD pricing → in-house DB).

#### Option 5 — Replace Yahoo with paid market data API
**How**: Polygon.io ($29/mo Starter), Alpha Vantage Premium ($50/mo), or Financial Modeling Prep ($14/mo). All have proper rate-limit budgets and reliable Asia-listing coverage.
**Pros**: Removes Yahoo entirely from the dependency graph. Predictable SLA. Better API ergonomics.
**Cons**: Recurring cost; per-API auth + new client lib + tested coverage of every ticker we care about (especially `.HM`, `.SI`, `.VN` listings).
**Examples**: Most fintech production systems use a paid feed for this reason.

### Zone: SOURCE / PIPE hybrid

#### Option 6 — SQS + token-bucket consumer Lambda
**How**: Workers `SendMessage` ticker tasks to SQS instead of running directly. A small Lambda polls SQS at a fixed rate (e.g., 5/sec) and invokes the report-worker. Achieves rate-limit-aware pacing.
**Pros**: Decouples burst from execution. Easy to tune by changing the consumer poll interval. Replayable on failure.
**Cons**: New SQS queue + new consumer Lambda. Higher SFN-end-to-end latency.
**Examples**: AWS canonical "rate-limited consumer" pattern.

---

## Evaluation matrix

Scores 1-10 (higher = better). Effort: low = high score. Cost: cheap = high score.

| Option | Effort (low=10) | Effectiveness | Cost (cheap=10) | Risk (low=10) | Total |
|---|---:|---:|---:|---:|---:|
| 1. MaxConcurrency↓ 46→8 | **9** | 6 | 10 | **9** | **34** |
| 2. Backoff + jitter | 8 | 5 | 10 | **9** | 32 |
| 3. Single-writer price cache ★ | 5 | **9** | 9 | 7 | **30** |
| 4. NAT GW per AZ | 5 | 7 | 6 | 8 | 26 |
| 5. Paid market data API | 6 | **9** | 5 | 8 | 28 |
| 6. SQS + token-bucket | 4 | 8 | 8 | 7 | 27 |
| 7. Residential proxy pool | 4 | 7 | 4 | 3 | 18 |
| 8. SFN Wait+retry orchestration | 7 | 4 | 9 | 8 | 28 |

## Ranked recommendations

### Recommended path (3-step, ~1 sprint)

**Today (band-aid)**: combine #1 + #2.
Drop `MaxConcurrency` from 46 to 8 *and* swap fixed-2s retries for jittered exponential backoff. Two-line / two-file change. Buys you 56/56 coverage on most days while structural fix is built.

**This sprint (structural)**: implement #3 (single-writer price cache).
Decouples the report-worker from Yahoo entirely. Same architectural shape as the A4 RDS-Proxy fix in the PDF GORE — investing here pays off twice (precompute + ad-hoc bot queries).

**Skip unless needed**: #4 NAT-per-AZ. Useful as defense-in-depth but #3 makes it unnecessary. Revisit only if other Yahoo-callers (telegram-api, slack-bot live queries) start tripping the same limit.

**Avoid**: #7 proxy pool (ToS risk).

### Why #1+#2 first instead of jumping straight to #3

Two reasons:
1. **Buys observation time**. Once burst pressure is reduced, you can measure the *true* baseline failure rate and decide if #3 is even necessary or if a 16-min run is fine.
2. **Validates the diagnosis**. If lowering concurrency *doesn't* drop failure rate to zero, the bottleneck isn't per-IP throttling and #3 wouldn't help either.

### Why not just #3 alone

It's the right long-term shape but it's a multi-day build (new Lambda, scheduling, idempotency, backfill of historical data, switching report-worker reads). Meanwhile, every morning you ship at 42/56. #1+#2 unblock immediately.

---

## Resources

- AWS — SFN Map state `MaxConcurrency`: <https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html>
- AWS — exponential backoff + jitter: <https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/>
- yfinance behavior under load: <https://github.com/ranaroussi/yfinance/issues> (search "rate limit", "429", "Too Many Requests")
- Polygon.io pricing: <https://polygon.io/pricing>
- Alpha Vantage Premium: <https://www.alphavantage.co/premium/>
- Companion problem brief: `docs/architecture/c4-plantuml/rendered/precompute_rate_limit_problem.html`
- Visual framework: `docs/architecture/c4-plantuml/rendered/rate_limit_solutions.html`

---

## Next steps

```
# Recommended: lock in the band-aid + structural fix as a coordinated plan
/specify "rate-limit fix bundle: MaxConcurrency 46→8 + jittered backoff + single-writer price cache"

# Or compare top 2 in more depth before committing
/what-if "compare MaxConcurrency throttling vs single-writer cache for dev precompute coverage"

# Or validate that the diagnosis is correct before fixing
/validate "hypothesis: per-IP rate limit is the cause of the 14-of-56 daily gap"
```
