# Research: Langfuse Built-in LLM-as-a-Judge Scores

**Date**: 2026-01-12
**Focus**: Comprehensive inventory
**Status**: Complete

---

## Summary

Langfuse provides built-in LLM-as-a-judge evaluators through two sources:
1. **Native Langfuse templates** - Core evaluation criteria
2. **RAGAS partnership** - RAG-specific and advanced metrics

---

## Built-in Langfuse Evaluator Templates

These are the **native Langfuse LLM-as-a-judge templates** that come out of the box:

| Evaluator | What It Measures | Score Type |
|-----------|------------------|------------|
| **Hallucination** | Whether output contains fabricated information not grounded in context | Numeric (0-1) |
| **Helpfulness** | How useful the response is for the user's needs | Numeric (0-1) |
| **Relevance** | Whether the answer addresses what was actually asked | Numeric (0-1) |
| **Toxicity** | Presence of harmful, offensive, or inappropriate content | Numeric (0-1) |
| **Correctness** | Factual accuracy of the response | Numeric (0-1) |
| **Context Relevance** | How relevant retrieved context is to the query | Numeric (0-1) |
| **Context Correctness** | Whether the context contains accurate information | Numeric (0-1) |
| **Conciseness** | Whether the response is appropriately brief without losing meaning | Numeric (0-1) |

---

## RAGAS Partnership Evaluators

Langfuse integrates with RAGAS for additional evaluators. Available via the evaluator library:

### Retrieval Augmented Generation (RAG)

| Evaluator | What It Measures |
|-----------|------------------|
| **Context Precision** | Proportion of relevant items in retrieved context |
| **Context Recall** | Coverage of ground truth by retrieved context |
| **Context Entities Recall** | Entity-level recall in retrieved context |
| **Noise Sensitivity** | Robustness to irrelevant information in context |
| **Response Relevancy** | How relevant the response is to the input |
| **Faithfulness** | Factual consistency of answer against context |
| **Multimodal Faithfulness** | Faithfulness for multimodal inputs |
| **Multimodal Relevance** | Relevance for multimodal inputs |

### Agent/Tool Use

| Evaluator | What It Measures |
|-----------|------------------|
| **Topic Adherence** | Whether agent stays on topic |
| **Tool Call Accuracy** | Correctness of tool/function calls |
| **Tool Call F1** | Precision/recall balance for tool calls |
| **Agent Goal Accuracy** | Whether agent achieved its goal |

### Natural Language Comparison

| Evaluator | What It Measures |
|-----------|------------------|
| **Factual Correctness** | Factual accuracy compared to reference |
| **Semantic Similarity** | Meaning similarity to reference |
| **BLEU Score** | N-gram overlap with reference |
| **ROUGE Score** | Recall-oriented overlap with reference |
| **Exact Match** | Exact string match with reference |

### SQL Evaluation

| Evaluator | What It Measures |
|-----------|------------------|
| **SQL Query Equivalence** | Semantic equivalence of SQL queries |
| **Execution-based Datacompy Score** | Result-based comparison of SQL outputs |

### General Purpose

| Evaluator | What It Measures |
|-----------|------------------|
| **Aspect Critic** | Custom aspect-based evaluation |
| **Simple Criteria Scoring** | Single-criterion scoring |
| **Rubrics-based Scoring** | Multi-level rubric evaluation |

---

## Langchain Integration Evaluators

When using Langfuse with Langchain, additional eval types available:

| Evaluator | What It Measures |
|-----------|------------------|
| **Coherence** | Logical flow and consistency |
| **Harmfulness** | Potential to cause harm |
| **Maliciousness** | Intent to deceive or harm |
| **Controversiality** | Presence of controversial content |
| **Misogyny** | Gender-based discriminatory content |
| **Criminality** | Content promoting illegal activities |
| **Insensitivity** | Lack of cultural/social awareness |

---

## Our Current Implementation

From `src/integrations/langfuse_client.py`, we use **5 custom scores**:

1. **faithfulness** - Factual consistency with source data
2. **completeness** - Coverage of required report sections
3. **reasoning_quality** - Quality of analytical reasoning
4. **compliance** - Adherence to format requirements
5. **consistency** - Internal logical consistency

These are **custom evaluators** (not using Langfuse built-in templates). We could potentially migrate to built-in templates for `faithfulness` and `compliance`.

---

## Configuration Options

All Langfuse LLM-as-a-judge evaluators support:

- **Model selection**: OpenAI, Azure OpenAI, Anthropic, AWS Bedrock (via LiteLLM)
- **Score type**: Numeric (0-1), Categorical, Boolean
- **Reasoning**: Optional reasoning/explanation for score
- **Async execution**: Non-blocking evaluation
- **Execution tracing**: Full trace of evaluator LLM calls (2025 feature)

---

## Recommendations for Our Project

### Keep Custom (Current Approach)
- `reasoning_quality` - No built-in equivalent
- `completeness` - Domain-specific definition
- `consistency` - Domain-specific definition

### Consider Migration to Built-in
- `faithfulness` → Use RAGAS **Faithfulness** evaluator
- `compliance` → Could map to **Correctness** or custom **Aspect Critic**

### Potential Additions
- **Hallucination** - Detect fabricated stock data or predictions
- **Toxicity** - Ensure reports don't contain inappropriate content
- **Conciseness** - Evaluate report verbosity

---

## Sources

- [LLM-as-a-Judge Evaluation - Langfuse](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Langfuse Evaluator Library Changelog](https://langfuse.com/changelog/2025-05-24-langfuse-evaluator-library)
- [RAG Observability and Evals - Langfuse Blog](https://langfuse.com/blog/2025-10-28-rag-observability-and-evals)
- [Ragas Available Metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)
- [Evaluation Overview - Langfuse](https://langfuse.com/docs/evaluation/overview)
