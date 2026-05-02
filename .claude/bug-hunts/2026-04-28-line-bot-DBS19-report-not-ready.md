---
title: LINE bot returns "report not ready" for DBS19 (and 11 other tickers) on 2026-04-28
bug_type: production-error
date: 2026-04-28
status: root_cause_found
confidence: HIGH
---

# Bug Hunt Report: DBS19 returns "report not ready" in dev LINE bot

## Symptom

User sent ticker `DBS19` to the dev LINE bot and received the fallback message:

> ขออภัยครับ รายงานสำหรับ DBS19 ยังไม่พร้อมในขณะนี้
> กรุณาลองใหม่ภายหลัง หรือติดต่อทีมสนับสนุนค่ะ

(Translation: *"Sorry, the report for DBS19 is not yet ready. Please try again later or contact the support team."*)

**First occurrence (today)**: 2026-04-28 14:29:15 BKK (07:29:15 UTC) — reproducible
**Affected scope**: 12 tickers in the dev environment (full list below)
**Impact**: Medium (dev only, but represents a production-shape failure mode)

---

## Root Cause

**Today's precompute pipeline crashed for DBS19 (and 11 other tickers) with MySQL error `(1040, 'Too many connections')` during the parallel fan-out of report-worker Lambdas.** Because the worker errored on its very first Aurora call (`fetch_data`), it never wrote a cached report. When the user later messaged the LINE bot, the bot's Aurora cache lookup missed and the bot returned its "report not ready" fallback.

**Confidence: HIGH** — direct error log, reproducible from CloudWatch evidence.

```
[ERROR] 2026-04-27T22:01:02.556Z  worker  Step Functions failed for DBS19: (1040, 'Too many connections')
```

---

## Evidence Chain (data flow)

```
   User sends "DBS19" via LINE
            │ 14:29:15 BKK
            ▼
   ┌─────────────────────────────────┐
   │  line-bot-dev Lambda            │
   │  ─────────────────────          │
   │  ✅ Webhook received            │
   │  ✅ Signature verified          │
   │  ✅ Aurora precompute service   │
   │     initialized                 │
   │  ❌ Aurora cache miss for       │  ← Layer 4 evidence
   │     DBS19, report not available │     of cache miss
   │  📤 Sends fallback text         │
   │     ↓                           │
   │  USER receives "ยังไม่พร้อม"  │
   └─────────────────────────────────┘
            │
            │ Why was the cache miss?
            ▼
   ┌─────────────────────────────────┐
   │  Today's precompute run         │
   │  precompute-20260428-050051     │
   │  ─────────────────────          │
   │  Step Function: SUCCEEDED       │  ← Layer 1 weak evidence
   │  duration: 2 min 22 sec         │     (misleading!)
   │  total_tickers: 46  (literal,   │  ← stale hardcoded value
   │     not computed!)              │     in SFN definition
   │                                 │
   │  Reality (Layer 3):             │
   │    56 worker invocations        │
   │    44 succeeded                 │
   │    12 FAILED with               │
   │       (1040, 'Too many          │
   │        connections')            │  ← actual ground truth
   └─────────────────────────────────┘
            │
            │ Why connection-pool exhaustion?
            ▼
   ┌─────────────────────────────────┐
   │  AWS Step Functions Map state   │
   │  ParallelProcessing             │
   │  ──────────────────             │
   │  Fans out 56 workers in         │
   │  parallel at 22:01:01 UTC       │
   │  (one per ticker)               │
   │                                 │
   │  Each worker opens one or       │
   │  more Aurora connections via    │
   │  RDS Proxy. Aggregate           │
   │  burst > Aurora's connection    │
   │  capacity → 12 victims lose     │
   │  the race                       │
   └─────────────────────────────────┘
```

---

## Hypotheses Tested

### Hypothesis 1: DBS19 isn't a known ticker

**Likelihood**: medium (initial guess)
**Test**: `grep DBS19` in repo + invoke `get-ticker-list-dev` Lambda
**Result**: ❌ ELIMINATED
- `data/tickers.csv:9` maps `DBS19 → D05.SI`
- `get-ticker-list-dev` returns 56 tickers and DBS19 is at position 9
- Worker logs show DBS19 was successfully processed on 2026-04-21

### Hypothesis 2: DBS19 was filtered out before processing

**Likelihood**: high (after seeing `total_tickers: 46` in SFN output and 56 from get-ticker-list)
**Test**: Cross-reference get-ticker-list output vs worker invocations today
**Result**: ❌ ELIMINATED
- All 56 tickers were invoked today (worker logs show every name)
- The "46" in SFN output is a **hardcoded literal** in the `AggregateResults` state definition, not a real count — a stale doc-string masquerading as a metric

### Hypothesis 3: Worker invocation for DBS19 failed during processing

**Likelihood**: high (after eliminating H2)
**Test**: Filter worker logs for DBS19 in today's window
**Result**: ✅ CONFIRMED
- Found `Step Functions failed for DBS19: (1040, 'Too many connections')` at 22:01:02.556 UTC
- Failure happened on first `fetch_data` call (~7 ms after worker start) — connection couldn't be established
- DBS19 was 1 of 12 tickers that hit the same error

### Hypothesis 4: Connection-pool exhaustion was systemic (not DBS19-specific)

**Likelihood**: high (after H3)
**Test**: Filter logs for `"Too many connections"` across all tickers today
**Result**: ✅ CONFIRMED — 12 affected tickers:

```
DBS19, MITSU19, QQQM19, SP500US19, THAIBEV19,
UNH19, UOB19, VCB19, VENTURE19, VHM19, VNM19, XIAOMI19
```

The list is alphabetically clustered around the back half — consistent with workers that started slightly later in the parallel fan-out losing the connection-pool race.

### Hypothesis 5: RDS Proxy is misconfigured

**Likelihood**: medium (worth checking since Proxy is supposed to multiplex)
**Test**: `aws rds describe-db-proxies`
**Result**: ⚠️ PARTIAL EVIDENCE
- Proxy `dr-daily-report-proxy-dev` exists
- `MaxConnectionsPercent: null` (should be set; default is 100% but the field returning null is suspicious)
- Workers may be bypassing the Proxy and hitting Aurora directly — needs code-level verification

---

## Why the SFN reported "SUCCEEDED" despite 12 worker failures

The Step Function's `ParallelProcessing` state uses Map with default error handling. Worker errors are caught/swallowed at the Map state level (likely `Catch: ["States.ALL"]` with passthrough) so the parent SFN exits cleanly with status SUCCEEDED. **This is a Layer-1 evidence trap**: the SFN status says "all good" while 21% of workers (12/56) silently failed. A reviewer relying on SFN status alone would never see the bug.

---

## Why this bug was invisible until a user complained

Three observability gaps:

1. **No per-ticker success/failure metric**: SFN reports a single status; individual worker outcomes aren't aggregated to CloudWatch.
2. **No alarm on worker errors**: The `dr-daily-report-precompute-errors-dev` alarm watches the controller, not individual workers.
3. **Hardcoded `total_tickers: 46`**: The SFN output's only ticker count is a string literal, decoupling reported metric from reality.

The connection-pool failure has been likely happening on multiple recent runs, but only surfaced when a user happened to query one of the failed tickers.

---

## Reproduction Steps

1. Wait for daily precompute run (5:00 AM BKK / 22:00 UTC).
2. Observe via CloudWatch:
   ```bash
   aws logs filter-log-events --region ap-southeast-1 \
     --log-group-name /aws/lambda/dr-daily-report-report-worker-dev \
     --start-time $(date -u -d 'today 21:00' +%s)000 \
     --filter-pattern '"Too many connections"' \
     --query 'events[].message' --output text \
     | grep -oP 'failed for \K[A-Z0-9]+' | sort -u
   ```
3. Pick any ticker from the result, send it to the dev LINE bot — receives "ยังไม่พร้อม" message.

---

## Fix Candidates

### Fix 1 — Bound the Map fan-out (quick, low-risk)

Add `MaxConcurrency: 10` (or similar) to the `ParallelProcessing` Map state in `terraform/step_functions/precompute_workflow.json`. Cap parallel workers so aggregate Aurora connections stay under capacity.

- **Pros**: Smallest change. No infra cost. Solves the immediate connection-pool problem.
- **Cons**: Total wall-clock time increases (was 2:22, becomes ~6× → ~14 min for 56 tickers / 10 conc); still works fine for daily 5 AM cron.
- **Effort**: 30 min (edit JSON + redeploy SFN)
- **Risk**: Low

### Fix 2 — Verify and tune RDS Proxy

Investigate `MaxConnectionsPercent: null` finding. Confirm workers are connecting via the Proxy, not directly to the Aurora endpoint. If bypassing Proxy: switch worker connection string to the Proxy's endpoint. If using Proxy: increase `MaxConnectionsPercent` and Aurora `max_connections` parameter.

- **Pros**: Addresses the architectural root cause; preserves parallel speed.
- **Cons**: Touching DB params requires reboot of Aurora instance (downtime in dev only). Code-level verification needed.
- **Effort**: 2-4 hours (investigation + parameter tune + redeploy)
- **Risk**: Medium (parameter group changes can have wider effects)

### Fix 3 — Per-ticker error visibility

Add CloudWatch metric on worker `Errors` with `FunctionName + ticker` dimensions, and an alarm if any worker fails. Also fix the SFN `total_tickers` literal to use `States.ArrayLength($.ticker_list.tickers)` so the metric is real.

- **Pros**: Closes the observability gap that hid this bug for an unknown duration. Future-proof.
- **Cons**: Doesn't fix today's data — needs to be paired with Fix 1 or 2.
- **Effort**: 1-2 hours
- **Risk**: Low

### Fix 4 — Worker-level retry on connection errors

Wrap the Aurora connection in a retry-with-backoff specifically for error codes 1040 (too many connections), 2003 (can't connect), 2013 (lost connection).

- **Pros**: Self-healing; tolerant of transient bursts.
- **Cons**: Masks the connection-pool design flaw. Retries amplify the problem if everyone retries simultaneously (thundering herd unless jittered).
- **Effort**: 2 hours
- **Risk**: Low if jittered; medium if naive retry

---

## Recommendation

**Combined approach**: ship Fix 1 (MaxConcurrency) and Fix 3 (visibility) together as P1 today. Then schedule Fix 2 (Proxy investigation) as P2 follow-up.

- Fix 1 stops the bleeding immediately (no more failed workers tomorrow).
- Fix 3 ensures we learn about future failures before users do.
- Fix 2 is the architectural cleanup but takes longer; safe to defer once the bleeding has stopped.

**Implementation priority**: P1 (user-visible, repeating daily, easy to fix)

---

## Immediate user remediation

To make DBS19 (and the other 11 tickers) work *right now* in dev without waiting for tomorrow's cron:

```bash
# Re-trigger the precompute manually (with reduced fan-out, ad-hoc)
# Or invoke just the failed tickers via report-worker directly:
for tk in DBS19 MITSU19 QQQM19 SP500US19 THAIBEV19 UNH19 UOB19 VCB19 VENTURE19 VHM19 VNM19 XIAOMI19; do
  aws lambda invoke --function-name dr-daily-report-report-worker-dev \
    --region ap-southeast-1 \
    --payload "{\"ticker\":\"$tk\"}" \
    --cli-binary-format raw-in-base64-out \
    /tmp/${tk}.out >/dev/null
  sleep 2  # crude jitter to avoid recreating the connection storm
done
```

Then re-test DBS19 in LINE bot — should return the actual report.

---

## Next Steps

- [ ] Patch `terraform/step_functions/precompute_workflow.json` with `MaxConcurrency: 10`
- [ ] Re-trigger precompute for the 12 failed tickers (one-off remediation)
- [ ] Verify DBS19 returns a real report in LINE bot after re-trigger
- [ ] Add per-ticker error metric + alarm
- [ ] Investigate RDS Proxy null `MaxConnectionsPercent`
- [ ] Document in `/journal error "Aurora connection-pool exhaustion in parallel precompute fan-out"`

---

## Investigation Trail

**What was checked** (in order):
1. CloudWatch logs — line-bot-dev (found cache miss)
2. Static ticker registry — `data/tickers.csv` (DBS19 is valid)
3. Worker logs — `report-worker-dev` (found DBS19's success on 2026-04-21)
4. Step Functions execution history (today's run SUCCEEDED at SFN level)
5. SFN definition (found hardcoded `total_tickers: 46`)
6. `get-ticker-list-dev` direct invoke (returns 56 tickers including DBS19)
7. Cross-reference today's worker invocations vs ticker-list (all 56 invoked)
8. DBS19 worker trace today (found error 1040)
9. Scope of failure (12 tickers affected)
10. Aurora cluster + RDS Proxy config

**What was ruled out**:
- Ticker not in registry (H1) — DBS19 is in `tickers.csv` and `get-ticker-list` output
- Ticker filtered out before processing (H2) — all 56 ran
- LINE bot bug — cache lookup logic is correct; the cache really doesn't have DBS19

**Tools used**:
- `aws logs filter-log-events`
- `aws stepfunctions list-executions / describe-execution / describe-state-machine`
- `aws lambda invoke`
- `aws scheduler get-schedule`
- `aws rds describe-db-clusters / describe-db-proxies / describe-db-cluster-parameters`
- `grep / python3 / jq`

**Time spent**: ~25 minutes evidence gathering, hypothesis ranking, root-cause confirmation.
