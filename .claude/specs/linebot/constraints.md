# LINE Bot Constraints

**Objective**: Chat-based financial reports via LINE
**Last Updated**: 2026-01-13

---

## What Are Constraints?

Constraints are **learned restrictions** from experience—things we've discovered DON'T work or MUST be done a certain way. Unlike invariants (which define WHAT must hold), constraints define HOW we must operate.

---

## Platform Constraints

### LINE Messaging API
- **Webhook timeout**: 20 seconds max response time
- **Message size**: 5000 characters max per text message
- **Reply token**: Valid for 30 seconds only
- **Rate limit**: 1000 messages/minute (free tier)

### Lambda Execution
- **Cold start**: ~3-5s for Python with dependencies
- **Memory**: 512MB minimum for PDF generation (ReportLab)
- **Timeout**: Must be > webhook timeout (30s configured)
- **VPC required**: Aurora access requires VPC configuration

### Aurora MySQL
- **Connection limit**: Max 90 concurrent connections (db.t3.medium)
- **Query timeout**: Long queries can cause webhook timeout
- **Timezone**: Parameter group must set `time_zone = 'Asia/Bangkok'`

---

## Learned Constraints (From Incidents)

### LC-001: Never Use Blocking PDF Generation
**Discovered**: 2025-12 (LINE bot timeout incident)
**Constraint**: PDF generation must complete within webhook timeout
**Workaround**: Pre-generate PDFs or use async pattern
**Evidence**: Users received no response when PDF took >20s

### LC-002: Always Verify LINE Signature
**Discovered**: Security audit
**Constraint**: Every webhook request must have valid X-Line-Signature
**Why**: Prevents replay attacks and unauthorized access
**Implementation**: Use LINE SDK's `validate_signature()` before processing

### LC-003: Log Before External Calls
**Discovered**: 2026-01 (debugging session)
**Constraint**: Log entry point before any LINE API or Aurora call
**Why**: If Lambda times out, at least we know what operation was attempted
**Pattern**: Boundary logging (Principle #18)

### LC-004: No Silent Fallbacks for Missing Data
**Discovered**: 2025-11 (stale report incident)
**Constraint**: If precomputed data missing, return error—don't fetch live
**Why**: Live fetch can timeout; inconsistent user experience
**Implementation**: Fail fast with "Data not yet available" message

### LC-005: VPC Endpoint Required for S3
**Discovered**: 2026-01 (NAT Gateway saturation)
**Constraint**: S3 operations must use VPC Gateway Endpoint, not NAT
**Why**: NAT Gateway has connection rate limits causing deterministic timeouts
**Evidence**: First N operations succeed, last M timeout

---

## Environment-Specific Constraints

### dev
```yaml
allowed:
  - MOCK_LINE=true (bypass LINE API for local testing)
  - Stale data up to 48 hours
  - Debug logging enabled
  - Test LINE channel

forbidden:
  - Production LINE channel
  - Real user data
```

### stg
```yaml
allowed:
  - Test LINE channel
  - Debug logging
  - Stale data up to 24 hours

forbidden:
  - MOCK_LINE (must test real LINE API)
  - Production LINE channel
```

### prd
```yaml
allowed:
  - Production LINE channel only
  - Stale data up to 24 hours

forbidden:
  - MOCK_LINE
  - Debug logging (performance overhead)
  - Test LINE channel
  - Any mock data
```

---

## Adding New Constraints

When you discover something that MUST or MUST NOT be done:

1. **Document in this file** with:
   - Unique ID (LC-XXX)
   - When discovered
   - What the constraint is
   - Why it exists (root cause)
   - Evidence (incident, audit, or test)

2. **Link to journal entry** if applicable:
   ```markdown
   See: .claude/journal/2026-01-XX-{description}.md
   ```

3. **Consider if it's actually an invariant**:
   - Constraint = HOW to operate (learned restriction)
   - Invariant = WHAT must hold (behavioral contract)

---

*Objective: linebot*
*Spec: .claude/specs/linebot/spec.yaml*
