# DR Report Prompt Workflow

**Reference**: Step-by-step guide for prompt modifications.

---

## Workflow Overview

```
1. Understand → 2. Design → 3. Implement → 4. Test → 5. Deploy → 6. Monitor
```

---

## Phase 1: Understand Current State

### 1.1 Read Current Prompt

```bash
# Local file
cat src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt

# Or fetch from Langfuse
python -c "from src.integrations.prompt_service import PromptService; print(PromptService().get_prompt('dr-report-main', label='production').content)"
```

### 1.2 Understand Data Flow

```
Aurora Data
    ↓
market_analyzer.py → Numeric calculations
    ↓
semantic_state_generator.py → Semantic states
    ↓
context_builder.py → Context string
    ↓
prompt_builder.py → Compiled prompt
    ↓
LLM → Raw report
    ↓
number_injector.py → Final report with exact values
```

### 1.3 Identify Change Scope

| Change Type | Files to Modify |
|-------------|-----------------|
| Prompt wording | `prompt_templates/*.txt`, Langfuse |
| New indicator | `semantic_state_generator.py`, `context_builder.py` |
| New placeholder | `number_injector.py`, prompt template |
| Output format | Prompt template, `context_builder.py` |

---

## Phase 2: Design Changes

### 2.1 Apply Prompt Engineering Principles

From [prompt-engineering/SKILL.md](../prompt-engineering/SKILL.md):

- [ ] Be explicit and clear
- [ ] Provide structure and boundaries
- [ ] Include few-shot examples (3 optimal)
- [ ] Front-load critical instructions

### 2.2 Apply Context Engineering Principles

From [context-engineering/SKILL.md](../context-engineering/SKILL.md):

- [ ] Use semantic layer (Layer 1-4 separation)
- [ ] Use placeholders for all numbers
- [ ] Ground thresholds semantically
- [ ] Optimize token usage

### 2.3 Document Changes

Before implementing, document:

```markdown
## Change: [Brief description]

**Goal**: What should improve?
**Hypothesis**: Why will this change help?
**Metrics**: How will we measure success?
**Rollback**: How to revert if issues?
```

---

## Phase 3: Implement Changes

### 3.1 Layer-by-Layer Implementation

#### Layer 1: Numeric Calculations

```python
# src/analysis/market_analyzer.py
def calculate_new_metric(self, indicators: dict) -> float:
    """Add new numeric calculation."""
    return computed_value
```

#### Layer 2: Semantic Classification

```python
# src/analysis/semantic_state_generator.py
@dataclass
class NewState:
    level: str  # "LOW", "MEDIUM", "HIGH"

def classify_new_metric(self, value: float) -> NewState:
    """Convert numeric to semantic."""
    if value < 30:
        return NewState(level="LOW")
    elif value < 70:
        return NewState(level="MEDIUM")
    else:
        return NewState(level="HIGH")
```

#### Layer 3: Context Building

```python
# src/report/context_builder.py
def prepare_context(self, **kwargs) -> str:
    """Include new data in context."""
    sections = []

    # Existing sections...

    # New section
    new_state = self.semantic_generator.classify_new_metric(kwargs['new_value'])
    sections.append(f"New Metric: {new_state.level}")

    return "\n".join(sections)
```

#### Layer 4: Number Injection

```python
# src/report/number_injector.py
PLACEHOLDER_DEFINITIONS = {
    # ... existing ...
    '{{NEW_METRIC}}': 'New metric exact value',
}

def inject_deterministic_numbers(self, report: str, **kwargs) -> str:
    """Add new placeholder replacement."""
    replacements = {
        # ... existing ...
        '{{NEW_METRIC}}': f"{kwargs['new_value']:.1f}",
    }
    # ...
```

### 3.2 Update Prompt Template

```
# src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt

<placeholders>
...existing placeholders...
{{NEW_METRIC}} - New metric description
</placeholders>

<data>
...existing context...
New Metric: {new_metric_state}
</data>
```

---

## Phase 4: Test Changes

### 4.1 Unit Tests

```python
# tests/unit/test_semantic_state_generator.py
def test_classify_new_metric_low():
    generator = SemanticStateGenerator()
    result = generator.classify_new_metric(25.0)
    assert result.level == "LOW"
```

### 4.2 Integration Test

```python
# tests/integration/test_report_generation.py
def test_report_includes_new_metric():
    generator = ReportGeneratorSimple()
    report = generator.generate(ticker="PTT")

    # Verify placeholder replaced
    assert "{{NEW_METRIC}}" not in report

    # Verify content present
    assert "new metric" in report.lower() or check_metric_value(report)
```

### 4.3 Local End-to-End Test

```bash
# Generate test report
python -c "
from src.report.report_generator_simple import ReportGeneratorSimple
gen = ReportGeneratorSimple()
print(gen.generate('PTT'))
"
```

### 4.4 Validation Checklist

- [ ] All placeholders replaced
- [ ] No hallucinated numbers
- [ ] Thai language correct
- [ ] Report length appropriate (10-15 sentences)
- [ ] Semantic states accurate

---

## Phase 5: Deploy to Langfuse

### 5.1 Create New Version

1. Open Langfuse UI
2. Navigate to Prompts → `dr-report-main`
3. Click "New Version"
4. Paste updated prompt content
5. Add version note describing changes

### 5.2 Deploy to Dev

```
# In Langfuse UI
Version: v5 ← dev
```

Test in dev environment.

### 5.3 Deploy to Staging

```
# After dev validation
Version: v5 ← staging
```

Test in staging environment.

### 5.4 Deploy to Production

```
# After staging validation
Version: v5 ← production
```

---

## Phase 6: Monitor

### 6.1 Immediate Monitoring (First Hour)

- [ ] Error rate normal (<1%)
- [ ] Latency normal (<5s)
- [ ] No placeholder errors in logs

### 6.2 Short-term Monitoring (First Day)

- [ ] User feedback neutral/positive
- [ ] Output quality consistent
- [ ] No hallucination reports

### 6.3 Long-term Monitoring (First Week)

- [ ] Compare metrics vs previous version
- [ ] Document findings
- [ ] Decide: keep, iterate, or rollback

---

## Rollback Procedure

### Quick Rollback (Label Move)

```
# In Langfuse UI
Move 'production' label from v5 back to v4
```

No code deployment required. Takes effect immediately.

### Verify Rollback

```python
# Confirm version
prompt = prompt_service.get_prompt("dr-report-main", label="production")
print(f"Current version: {prompt.version}")  # Should be v4
```

---

## References

- [SKILL.md](SKILL.md) - Overview
- [CHECKLIST.md](CHECKLIST.md) - Pre-deployment checklist
- [prompt-engineering/](../prompt-engineering/) - Design patterns
- [context-engineering/](../context-engineering/) - Context patterns
- [prompt-management/](../prompt-management/) - Deployment patterns
