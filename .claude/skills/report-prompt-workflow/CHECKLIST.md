# DR Report Prompt Checklist

**Reference**: Pre-deployment validation for prompt changes.

---

## Pre-Change Checklist

Before making changes, verify:

- [ ] Current prompt version documented
- [ ] Baseline metrics recorded (latency, error rate, quality)
- [ ] Rollback procedure understood
- [ ] Change scope identified (which files/layers)

---

## Design Checklist

### Prompt Engineering (from [prompt-engineering/](../prompt-engineering/))

- [ ] Instructions are explicit and clear
- [ ] Critical requirements front-loaded
- [ ] 3 few-shot examples included
- [ ] Examples cover edge cases (bullish, bearish, volatile)
- [ ] No verbose/redundant instructions
- [ ] No conflicting techniques

### Context Engineering (from [context-engineering/](../context-engineering/))

- [ ] Numbers use placeholders (never hardcoded)
- [ ] Semantic states provided for thresholds
- [ ] Token budget respected (<4K input)
- [ ] No redundant context sections
- [ ] Ground truth values prepared for injection

### Security (from [prompt-engineering/SECURITY.md](../prompt-engineering/SECURITY.md))

- [ ] No secrets in prompt
- [ ] User input sanitized (if applicable)
- [ ] Output validation implemented

---

## Implementation Checklist

### Layer Compliance

- [ ] **Layer 1**: Numeric calculations in code (not LLM)
- [ ] **Layer 2**: Semantic classification in code
- [ ] **Layer 3**: Context building uses semantic states
- [ ] **Layer 4**: Number injector has all new placeholders

### Code Changes

- [ ] `semantic_state_generator.py` updated (if new metrics)
- [ ] `context_builder.py` updated (if new sections)
- [ ] `number_injector.py` updated (if new placeholders)
- [ ] `prompt_templates/*.txt` updated (if local fallback)

### Placeholder Verification

```python
# All placeholders must be defined
REQUIRED_PLACEHOLDERS = [
    '{{RSI}}',
    '{{ATR_PCT}}',
    '{{PRICE_CHANGE}}',
    '{{VWAP_PCT}}',
    # ... all used in prompt
]

for placeholder in REQUIRED_PLACEHOLDERS:
    assert placeholder in number_injector.PLACEHOLDER_DEFINITIONS
```

---

## Testing Checklist

### Unit Tests

- [ ] New semantic classification functions tested
- [ ] Edge cases covered (zero values, missing data)
- [ ] Threshold boundaries tested

### Integration Tests

- [ ] Report generates without errors
- [ ] All placeholders replaced
- [ ] Output format matches expectations

### Manual Validation

- [ ] Generate 3+ test reports
- [ ] Verify numbers match ground truth
- [ ] Verify Thai language quality
- [ ] Verify report length (10-15 sentences)

---

## Deployment Checklist

### Langfuse Setup

- [ ] New version created in Langfuse
- [ ] Version note added with change description
- [ ] `dev` label assigned to new version

### Dev Environment

- [ ] Deploy code changes to dev
- [ ] Test report generation
- [ ] Check logs for errors
- [ ] Verify Langfuse traces

### Staging Environment

- [ ] Move `staging` label to new version
- [ ] Test report generation
- [ ] Compare output quality to baseline
- [ ] No unexpected latency increase

### Production Environment

- [ ] Move `production` label to new version
- [ ] Monitor error rate for 1 hour
- [ ] Monitor user feedback
- [ ] Ready to rollback if issues

---

## Post-Deployment Checklist

### Immediate (First Hour)

- [ ] Error rate < 1%
- [ ] Latency < 5s average
- [ ] No unreplaced placeholders in logs
- [ ] No user complaints

### Short-term (First Day)

- [ ] Output quality consistent
- [ ] No hallucination reports
- [ ] Metrics stable

### Long-term (First Week)

- [ ] Compare vs baseline metrics
- [ ] Document learnings
- [ ] Update this checklist if needed

---

## Rollback Checklist

If issues detected:

1. [ ] Identify severity (critical, major, minor)
2. [ ] For critical: Immediate rollback
3. [ ] Move `production` label to previous version in Langfuse
4. [ ] Verify rollback effective (check version in traces)
5. [ ] Document issue and root cause
6. [ ] Plan fix for next iteration

---

## Quality Metrics

### Must Pass

| Metric | Threshold |
|--------|-----------|
| Placeholder completion | 100% |
| Error rate | <1% |
| Thai language ratio | >80% |

### Should Pass

| Metric | Threshold |
|--------|-----------|
| Latency | <5s |
| Token usage | <4K input |
| User satisfaction | >4.0/5 |

### Nice to Have

| Metric | Threshold |
|--------|-----------|
| Cost per report | <$0.05 |
| Report length | 10-15 sentences |

---

## Common Issues

### Issue: Unreplaced Placeholders

**Symptom**: `{{PLACEHOLDER}}` appears in output
**Cause**: Missing definition in `number_injector.py`
**Fix**: Add placeholder to PLACEHOLDER_DEFINITIONS

### Issue: Hallucinated Numbers

**Symptom**: Numbers don't match ground truth
**Cause**: Number not using placeholder pattern
**Fix**: Replace hardcoded number with `{{PLACEHOLDER}}`

### Issue: High Latency

**Symptom**: Report generation >10s
**Cause**: Prompt too long or complex
**Fix**: Apply token optimization from [context-engineering/](../context-engineering/)

### Issue: Poor Thai Quality

**Symptom**: Grammatical errors, unnatural phrasing
**Cause**: Examples not representative
**Fix**: Improve few-shot examples with native review

---

## References

- [SKILL.md](SKILL.md) - Overview
- [WORKFLOW.md](WORKFLOW.md) - Step-by-step guide
- [prompt-engineering/ANTI-PATTERNS.md](../prompt-engineering/ANTI-PATTERNS.md)
- [context-engineering/HALLUCINATION-PREVENTION.md](../context-engineering/HALLUCINATION-PREVENTION.md)
