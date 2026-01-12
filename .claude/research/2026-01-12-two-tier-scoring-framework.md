# Research: Two-Tier Scoring Framework for DR Report Evaluation

**Date**: 2026-01-12
**Focus**: Comprehensive evaluation framework
**Status**: Complete

---

## Problem Decomposition

**Goal**: Create a fixed scoring criteria system with two tiers:
1. **Gate Tier** (0 or 1): Is this prompt version "good enough" at all?
2. **Ranking Tier** (0 to 1): Among good-enough prompts, which produces the best output?

**Core Requirements**:
- Binary gate to filter out clearly bad prompts
- Continuous score to compare and rank good prompts
- Reproducible evaluation (same input → same score)
- Interpretable results (understand why a prompt failed/succeeded)

**Constraints**:
- Must work with existing Langfuse infrastructure
- Should leverage current scorer architecture in `src/scoring/`
- Cost-efficient (minimize LLM-as-judge calls for gate tier)

---

## Current Scoring Architecture

### Existing Scorers (7 total)

| Scorer | Type | Measures | Score Range |
|--------|------|----------|-------------|
| **FaithfulnessScorer** | Rule-based | Numbers/citations match data | 0-100 |
| **CompletenessScorer** | Rule-based | All analysis dimensions covered | 0-100 |
| **ReasoningQualityScorer** | Rule-based | Logical structure of analysis | 0-100 |
| **ComplianceScorer** | Rule-based | Format/structure requirements | 0-100 |
| **ConsistencyScorer** | Rule-based | Internal logical consistency | 0-100 |
| **QoSScorer** | Metrics | Latency, error rate, cache | 0-100 |
| **CostScorer** | Metrics | API costs, LLM calls | 0-100 |

### Score Categories

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCORE TAXONOMY                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RULE-BASED (Fast, Deterministic, Free)                        │
│  ─────────────────────────────────────                         │
│  Pattern matching, keyword detection, structure validation     │
│  Examples: Faithfulness, Completeness, Compliance              │
│  Best for: Gate tier (hard requirements)                       │
│                                                                 │
│  LLM-AS-JUDGE (Slow, Variable, Costly)                         │
│  ─────────────────────────────────────                         │
│  Semantic understanding, quality assessment                    │
│  Examples: RAGAS Faithfulness, Langfuse Hallucination          │
│  Best for: Ranking tier (nuanced quality)                      │
│                                                                 │
│  CONTEXT-BASED (Medium, Deterministic, Free)                   │
│  ─────────────────────────────────────────                     │
│  Compares output to provided context/reference                 │
│  Examples: Data grounding, citation accuracy                   │
│  Best for: Both tiers (objective verification)                 │
│                                                                 │
│  METRICS-BASED (Fast, Deterministic, Free)                     │
│  ─────────────────────────────────────────                     │
│  Performance/cost measurements                                 │
│  Examples: Latency, token count, API cost                      │
│  Best for: Gate tier (operational requirements)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Two-Tier Framework Design

### Tier 1: Gate Scores (Binary Pass/Fail)

**Purpose**: Filter out prompts that produce unacceptable outputs

**Principle**: Use fast, deterministic, rule-based checks for hard requirements

```
┌─────────────────────────────────────────────────────────────────┐
│                    GATE TIER (PASS/FAIL)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MUST PASS ALL of these checks:                                 │
│                                                                 │
│  1. FORMAT GATE                                                 │
│     ├── Output is valid Thai text (not empty, not error)       │
│     ├── Contains 4 required sections                           │
│     ├── No prohibited elements (tables, bullet lists)          │
│     └── Length within bounds (500-5000 chars)                  │
│     Source: ComplianceScorer (structure_score > 70)            │
│                                                                 │
│  2. GROUNDING GATE                                              │
│     ├── All cited numbers exist in source data                 │
│     ├── No hallucinated company names/sectors                  │
│     └── News citations [1],[2] reference valid news            │
│     Source: FaithfulnessScorer (numeric_accuracy > 80)         │
│                                                                 │
│  3. COVERAGE GATE                                               │
│     ├── Mentions technical analysis (RSI/MACD/SMA)             │
│     ├── Mentions volatility/risk                                │
│     ├── Mentions volume analysis                                │
│     └── Mentions historical context                             │
│     Source: CompletenessScorer (required dimensions)           │
│                                                                 │
│  4. SAFETY GATE                                                 │
│     ├── No explicit investment advice ("ควรซื้อ/ขาย")          │
│     ├── No future price predictions                             │
│     └── Disclaimer present if required                          │
│     Source: ComplianceScorer (policy_score > 90)               │
│                                                                 │
│  5. COST GATE (Optional)                                        │
│     ├── Token count < threshold                                 │
│     └── API cost < budget                                       │
│     Source: CostScorer                                          │
│                                                                 │
│  GATE RESULT: PASS if ALL gates pass, FAIL otherwise           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```python
def compute_gate_score(report_text: str, context: ScoringContext) -> bool:
    """
    Binary gate: Is this output acceptable at all?
    Returns True (pass) or False (fail)
    """
    # All gates must pass
    gates = {
        'format': compliance_scorer.check_structure(report_text) > 70,
        'grounding': faithfulness_scorer.check_numeric_accuracy(report_text, context) > 80,
        'coverage': completeness_scorer.check_required_dimensions(report_text) == 4,
        'safety': compliance_scorer.check_policy(report_text) > 90,
    }

    return all(gates.values())
```

### Tier 2: Ranking Scores (0.0 to 1.0)

**Purpose**: Compare quality among prompts that pass the gate

**Principle**: Use nuanced evaluation including LLM-as-judge for subjective quality

```
┌─────────────────────────────────────────────────────────────────┐
│                    RANKING TIER (0.0 - 1.0)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  QUALITY SCORES (60% weight):                                   │
│                                                                 │
│  1. FAITHFULNESS (15%)                                          │
│     Rule-based: numeric_accuracy, citation_accuracy             │
│     LLM-judge: claim grounding (RAGAS Faithfulness)             │
│                                                                 │
│  2. REASONING QUALITY (15%)                                     │
│     Rule-based: logical_flow, causal_language                   │
│     LLM-judge: coherence, insight quality                       │
│                                                                 │
│  3. COMPLETENESS (15%)                                          │
│     Rule-based: dimension_coverage                              │
│     LLM-judge: depth of analysis                                │
│                                                                 │
│  4. CONSISTENCY (15%)                                           │
│     Rule-based: internal_consistency                            │
│     LLM-judge: semantic coherence                               │
│                                                                 │
│  STYLE SCORES (25% weight):                                     │
│                                                                 │
│  5. COMPLIANCE (10%)                                            │
│     Rule-based: format adherence, length                        │
│                                                                 │
│  6. READABILITY (10%)                                           │
│     Rule-based: sentence length, Thai fluency markers           │
│     LLM-judge: natural Thai writing quality                     │
│                                                                 │
│  7. CONCISENESS (5%)                                            │
│     Rule-based: information density                             │
│                                                                 │
│  EFFICIENCY SCORES (15% weight):                                │
│                                                                 │
│  8. COST EFFICIENCY (10%)                                       │
│     Metrics: tokens_used / quality_score                        │
│                                                                 │
│  9. LATENCY (5%)                                                │
│     Metrics: generation_time                                    │
│                                                                 │
│  RANKING RESULT: Weighted sum normalized to 0.0-1.0             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Score Type Recommendations

### For Gate Tier (Use Rule-Based)

| Gate | Score Type | Implementation | Why |
|------|-----------|----------------|-----|
| Format | Rule-based | Regex + keyword | Fast, deterministic, free |
| Grounding | Context-based | Compare to input data | Objective verification |
| Coverage | Rule-based | Keyword detection | Binary presence check |
| Safety | Rule-based | Banned phrase detection | Critical, must be fast |
| Cost | Metrics | Token counting | Objective measurement |

### For Ranking Tier (Use Mix)

| Score | Type | When to Use |
|-------|------|-------------|
| Faithfulness | Rule + LLM | Rule for numbers, LLM for semantic claims |
| Reasoning | Rule + LLM | Rule for structure, LLM for insight quality |
| Completeness | Rule + LLM | Rule for coverage, LLM for depth |
| Consistency | Rule + LLM | Rule for contradictions, LLM for coherence |
| Readability | LLM | Thai fluency requires semantic understanding |
| Compliance | Rule | Objective format checks |
| Efficiency | Metrics | Objective measurements |

---

## Recommended Score Set

### Gate Scores (5)

```python
GATE_SCORES = {
    'format_valid': {
        'type': 'rule-based',
        'source': 'ComplianceScorer.structure_score',
        'threshold': 70,
        'description': 'Output has correct structure and format'
    },
    'grounded': {
        'type': 'context-based',
        'source': 'FaithfulnessScorer.numeric_accuracy',
        'threshold': 80,
        'description': 'All claims supported by input data'
    },
    'complete': {
        'type': 'rule-based',
        'source': 'CompletenessScorer.required_dimensions',
        'threshold': 4,  # Must cover all 4 required dimensions
        'description': 'Covers all required analysis dimensions'
    },
    'safe': {
        'type': 'rule-based',
        'source': 'ComplianceScorer.policy_score',
        'threshold': 90,
        'description': 'No investment advice or price predictions'
    },
    'within_budget': {
        'type': 'metrics',
        'source': 'CostScorer.total_cost',
        'threshold': 0.05,  # $0.05 per report
        'description': 'Generation cost within budget'
    }
}
```

### Ranking Scores (9)

```python
RANKING_SCORES = {
    # Quality (60%)
    'faithfulness': {
        'weight': 0.15,
        'type': 'hybrid',
        'rule_component': 'FaithfulnessScorer.overall_score',
        'llm_component': 'RAGAS.faithfulness',
        'description': 'Factual accuracy and claim grounding'
    },
    'reasoning_quality': {
        'weight': 0.15,
        'type': 'hybrid',
        'rule_component': 'ReasoningQualityScorer.overall_score',
        'llm_component': 'AspectCritic.insight_quality',
        'description': 'Logical structure and analytical depth'
    },
    'completeness': {
        'weight': 0.15,
        'type': 'hybrid',
        'rule_component': 'CompletenessScorer.overall_score',
        'llm_component': 'AspectCritic.analysis_depth',
        'description': 'Coverage and depth of analysis'
    },
    'consistency': {
        'weight': 0.15,
        'type': 'hybrid',
        'rule_component': 'ConsistencyScorer.overall_score',
        'llm_component': 'Langfuse.coherence',
        'description': 'Internal logical consistency'
    },

    # Style (25%)
    'compliance': {
        'weight': 0.10,
        'type': 'rule-based',
        'source': 'ComplianceScorer.overall_score',
        'description': 'Format and structure adherence'
    },
    'readability': {
        'weight': 0.10,
        'type': 'llm-judge',
        'source': 'AspectCritic.thai_fluency',
        'description': 'Natural Thai writing quality'
    },
    'conciseness': {
        'weight': 0.05,
        'type': 'rule-based',
        'source': 'info_density_score',
        'description': 'Information per token ratio'
    },

    # Efficiency (15%)
    'cost_efficiency': {
        'weight': 0.10,
        'type': 'metrics',
        'source': 'CostScorer.efficiency_ratio',
        'description': 'Quality per dollar spent'
    },
    'latency': {
        'weight': 0.05,
        'type': 'metrics',
        'source': 'QoSScorer.latency_score',
        'description': 'Generation speed'
    }
}
```

---

## Evaluation Matrix

| Score | Gate | Ranking | Type | Cost | Speed |
|-------|------|---------|------|------|-------|
| Format Valid | ✅ | | Rule | Free | Fast |
| Grounded | ✅ | | Context | Free | Fast |
| Complete | ✅ | | Rule | Free | Fast |
| Safe | ✅ | | Rule | Free | Fast |
| Within Budget | ✅ | | Metrics | Free | Fast |
| Faithfulness | | ✅ | Hybrid | ~$0.01 | Medium |
| Reasoning Quality | | ✅ | Hybrid | ~$0.01 | Medium |
| Completeness | | ✅ | Hybrid | ~$0.01 | Medium |
| Consistency | | ✅ | Hybrid | ~$0.01 | Medium |
| Compliance | | ✅ | Rule | Free | Fast |
| Readability | | ✅ | LLM | ~$0.01 | Slow |
| Conciseness | | ✅ | Rule | Free | Fast |
| Cost Efficiency | | ✅ | Metrics | Free | Fast |
| Latency | | ✅ | Metrics | Free | Fast |

**Estimated Cost per Evaluation**:
- Gate only: Free (all rule-based)
- Gate + Ranking (hybrid): ~$0.05 (5 LLM calls)
- Gate + Ranking (full LLM): ~$0.10 (10 LLM calls)

---

## Implementation Recommendations

### Phase 1: Gate Implementation (Quick Wins)

1. Extend `ComplianceScorer` with explicit gate methods
2. Add threshold-based pass/fail logic
3. Store gate results in Langfuse as boolean scores

```python
# Gate score naming convention
score_current_trace("gate_format", 1.0 if passed else 0.0)
score_current_trace("gate_grounded", 1.0 if passed else 0.0)
score_current_trace("gate_all_passed", 1.0 if all_passed else 0.0)
```

### Phase 2: Ranking Enhancement

1. Add LLM-as-judge for subjective quality (readability, insight quality)
2. Implement RAGAS integration for semantic faithfulness
3. Create composite ranking score with weighted average

```python
# Ranking score naming convention
score_current_trace("rank_faithfulness", 0.85)
score_current_trace("rank_readability", 0.72)
score_current_trace("rank_composite", 0.78)  # Weighted average
```

### Phase 3: Experiment Infrastructure

1. Create dataset of test cases (tickers + expected outputs)
2. Implement A/B testing framework for prompts
3. Use Langfuse experiments feature to compare prompt versions

---

## Next Steps

```bash
# Recommended: Create gate score implementation
/specify "Gate score implementation with 5 binary checks"

# Alternative: Create full evaluation spec
/specify "Two-tier evaluation framework with Langfuse integration"

# Optional: Validate threshold assumptions
/validate "hypothesis: format_score > 70 correlates with acceptable outputs"
```

---

## Sources

- Current scorer implementations: `src/scoring/`
- Langfuse schema: `.claude/skills/langfuse-observability/SCHEMA.md`
- RAGAS metrics: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
- Langfuse built-in evaluators research: `.claude/research/2026-01-12-langfuse-builtin-llm-as-judge-scores.md`
