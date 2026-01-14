# Meta Principles Cluster

**Load when**: Debugging persistent issues, stuck in loops, concept analysis, local development setup

**Principles**: #9, #12, #17

**Related**: [Thinking Process Architecture](../diagrams/thinking-process-architecture.md)

---

## Principle #9: Feedback Loop Awareness

When failures persist, use `/reflect` to identify which loop type you're using:

| Loop Type | When to Use | Pattern |
|-----------|-------------|---------|
| **Retrying** | Fix execution errors | Same approach, different input |
| **Initial-sensitive** | Change assumptions | Same goal, different starting point |
| **Branching** | Try different path | Same goal, different approach |
| **Synchronize** | Align knowledge | Update understanding to match reality |
| **Meta-loop** | Change loop type | Stop and reconsider strategy |

**Thinking tools for loop identification**:
- `/trace` - Root cause analysis (why did this fail?)
- `/qna` - Surface knowledge state (what do I know/assume/not know?)
- `/hypothesis` - Generate new assumptions
- `/compare` - Evaluate alternative paths
- `/reflect` - Identify current loop pattern

**Escalation with `/qna` (Initial-Sensitive Loop)**:

When stuck in a retrying loop (same error repeated), use `/qna` to surface your knowledge state before generating new hypotheses:

```
Retrying Loop (3x same error)
    ↓
/reflect → "Execution varies, outcome identical" (stuck signal)
    ↓
/qna "{problem}" → Surface knowledge state for user verification
    → Confident: "Lambda uses Python 3.11"
    → Assumed: "Cache invalidates on data change" ← Might be wrong!
    → Unknown: "How TTL is configured"
    ↓
User: "Actually, cache uses fixed 15-min TTL"
    ↓
/hypothesis → Generate alternatives with CORRECTED knowledge
```

**Why `/qna` before `/hypothesis`**: Without surfacing current beliefs, you might generate hypotheses that are all wrong because they're based on faulty assumptions. `/qna` enables user correction BEFORE exploring alternatives.

**When to switch loops**:
- 2+ failed retries → Use `/qna` to surface assumptions, then Initial-sensitive
- Same error repeated → Initial-sensitive (wrong assumptions)
- No progress → Meta-loop (change strategy entirely)

See [Thinking Process Architecture - Feedback Loops](../diagrams/thinking-process-architecture.md#11-feedback-loop-types-self-healing-properties), [Initial-Sensitive Loop with /qna](../diagrams/thinking-process-architecture.md#2-initial-sensitive-loop-double-loop-learning), and [/qna command](../commands/qna.md).

---

## Principle #12: OWL-Based Relationship Analysis

Use formal ontology relationships (OWL, RDF) for structured concept comparison. Eliminates "it depends" answers by applying 4 fundamental relationship types:

| Relationship | Question | Example |
|--------------|----------|---------|
| **Part-whole** | Is X part of Y? | "Is authentication part of API Gateway?" |
| **Complement** | Does X complete Y? | "Does caching complement database queries?" |
| **Substitution** | Can X replace Y? | "Can Redis substitute DynamoDB for caching?" |
| **Composition** | Is X composed of Y+Z? | "Is deployment composed of build + test + promote?" |

**Usage**:
```
/compare "SQS vs Lambda async processing"

Apply relationship analysis:
1. Part-whole: Both are parts of AWS serverless architecture
2. Complement: SQS complements Lambda (decoupling)
3. Substitution: Partial - SQS can replace Lambda destinations
4. Composition: Lambda async = Lambda + dead-letter queue
```

**Benefit**: Transforms vague "X vs Y" questions into precise analytical frameworks with concrete examples.

See [Relationship Analysis Guide](../../docs/RELATIONSHIP_ANALYSIS.md).

---

## Principle #17: Shared Virtual Environment Pattern

Four-repository ecosystem shares single Python virtual environment via symlink (`venv -> ../dr-daily-report/venv`). Eliminates version conflicts between related projects, saves 75% disk space (500MB shared vs 2GB isolated), simplifies management (update once affects all).

**Setup**:
```bash
# Activate shared venv (works via symlink)
source venv/bin/activate

# Verify it's the shared one
which python  # Should show parent venv path
```

**Fallback** (if parent missing):
```bash
rm venv
python -m venv venv
pip install -r requirements.txt
```

**Benefits**:
- **Consistency**: Identical versions across projects
- **Disk efficiency**: 75% savings
- **Speed**: Updates immediate across all projects
- **Simplicity**: One venv to manage

**When to use isolated venv**:
- Testing specific version compatibility
- Project has conflicting dependencies
- CI/CD (always isolated)

See [Shared Virtual Environment Guide](../../docs/guides/shared-virtual-environment.md).

---

## Quick Checklist

Stuck debugging:
- [ ] Identify current loop type (retrying? branching?)
- [ ] After 2 retries, switch to research
- [ ] Use `/reflect` to assess progress
- [ ] Use `/trace` for root cause

Concept comparison:
- [ ] Apply 4 relationship types
- [ ] Provide concrete examples
- [ ] Avoid "it depends" without framework

Local development:
- [ ] Shared venv activated
- [ ] `which python` shows parent path
- [ ] Dependencies up to date

---

*Cluster: meta-principles*
*Last updated: 2026-01-12*
