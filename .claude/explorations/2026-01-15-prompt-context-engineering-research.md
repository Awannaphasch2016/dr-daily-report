# Research: Prompt + Context Engineering, Prompt Management

**Date**: 2026-01-15
**Focus**: Comprehensive research for skill development
**Status**: Complete

---

## Executive Summary

This research synthesizes best practices across three domains:
1. **Prompt Engineering** - Techniques for designing effective LLM prompts
2. **Context Engineering** - Optimizing the information provided to LLMs
3. **Prompt Management** - Infrastructure for versioning, testing, and deploying prompts

Key findings inform the design of Tier-1 modular skills.

---

## Part 1: Prompt Engineering

### Core Techniques

| Technique | Description | When to Use |
|-----------|-------------|-------------|
| **Zero-shot** | Direct task without examples | Simple, well-defined tasks |
| **Few-shot** | 1-5 examples before task | Format/style guidance needed |
| **Chain-of-Thought** | Step-by-step reasoning | Complex reasoning, math |
| **Tree-of-Thought** | Multiple reasoning paths | Exploration, creativity |
| **Role/Persona** | Assign expert identity | Domain expertise needed |
| **Meta-prompting** | LLM generates prompts | Prompt optimization |

**Sources**: [Prompt Engineering Guide](https://www.promptingguide.ai/), [Lakera Guide](https://www.lakera.ai/blog/prompt-engineering-guide)

### Best Practices (2025)

#### 1. Be Explicit and Clear
> "Don't assume the model will infer what you want—state it directly."

```
❌ Bad: "Write a report"
✅ Good: "Create a 3-section report with executive summary, key findings,
         and recommendations. Use bullet points for findings."
```

#### 2. Provide Structure and Context
> "Add boundaries to focus the AI's response."

```
✅ "Explain quantum computing in exactly 100 words using only terms
   a high school student would understand."
```

#### 3. Build Systems, Not Just Prompts
> "The most effective prompt engineers don't simply collect prompts,
   they build systems."

- Prompts become reusable frameworks
- Tested, refined, improved over time
- Parameterized for different scenarios

#### 4. Iterate and Refine
> "The first prompt rarely works perfectly. Test and refine."

#### 5. What to Avoid
- **Don't over-engineer**: Longer ≠ better
- **Don't ignore basics**: Advanced techniques need clear foundation
- **Don't assume mind-reading**: Be specific
- **Don't use every technique at once**: Select for specific challenges
- **Outdated techniques**: XML tags and heavy role prompting less necessary with modern models

**Source**: [Palantir Best Practices](https://www.palantir.com/docs/foundry/aip/best-practices-prompt-engineering)

### Advanced Patterns

#### Few-Shot Learning
```python
# Optimal: 3 examples (diminishing returns after)
# Include edge cases (bullish, bearish, volatile)
# Match output format exactly

examples = [
    {"input": "...", "output": "..."},  # Bullish case
    {"input": "...", "output": "..."},  # Bearish case
    {"input": "...", "output": "..."},  # Volatile case
]
```

#### Prompt Chaining
```python
# Complex task → multiple prompts
# Each stage adds refinement

prompt_1 = "Summarize this paper covering methodology, findings, implications"
prompt_2 = "Review the summary for accuracy and clarity. Provide feedback."
prompt_3 = "Improve the summary based on this feedback."
```

#### Task Decomposition
> "LLMs can struggle with overly complex tasks. Splitting into smaller
   steps improves both accuracy and efficiency."

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| **Number Leakage** | LLM hallucinates numbers | Use placeholders, inject deterministically |
| **Verbose Instructions** | LLM ignores long text | Front-load critical instructions |
| **Missing Examples** | Cold-start problem | Add 3 few-shot examples |
| **Prompt Injection** | Security vulnerability | Input validation, output filtering |

---

## Part 2: Context Engineering

### Definition

> "Context engineering refers to a collection of practices that can be combined
   to provide the right information to Large Language Models to help them
   accomplish the desired task."

**Source**: [Elastic - Context Engineering Overview](https://www.elastic.co/search-labs/blog/context-engineering-overview)

### Core Components

| Component | Description | Purpose |
|-----------|-------------|---------|
| **System Prompt** | Agent's procedural memory | Defines behavior |
| **Message History** | Short-term working memory | Conversation context |
| **Retrieved Context** | External knowledge (RAG) | Domain knowledge |
| **User Preferences** | Episodic memory | Personalization |

**Source**: [Mem0 - Context Engineering Guide](https://mem0.ai/blog/context-engineering-ai-agents-guide)

### Four Strategic Categories

1. **WRITE** - Add information to context
2. **SELECT** - Choose what to include
3. **COMPRESS** - Reduce redundancy
4. **ISOLATE** - Separate concerns

**Source**: [Medium - Context Engineering](https://medium.com/@kuldeep.paul08/context-engineering-optimizing-llm-memory-for-production-ai-agents-6a7c9165a431)

### The Semantic Layer Pattern

> "LLMs are fantastic for translating contextual questions into usable answers,
   but they struggle with hallucinations and consistency. The Semantic Layer
   has been theorized as a key interface for LLMs because each is strong
   where the other is weak."

**Key Insight**: Separate what numbers MEAN (code) from how to COMBINE them (LLM).

#### How It Works

```
Layer 1 (Code): Numeric calculations → Ground truth values
    ↓
Layer 2 (Code): Semantic classification → Categorical labels
    ↓
Layer 3 (LLM): Narrative synthesis → Natural language
    ↓
Layer 4 (Code): Post-processing → Inject exact values
```

#### Accuracy Impact

| Approach | Accuracy | Problem |
|----------|----------|---------|
| Direct LLM | ~30% | Hallucinations, wrong data |
| Semantic Layer | **83%** | Vetted metrics only |

> "In testing, dbt Labs saw an 83% accuracy rate for natural language
   questions being answered via AI in the dbt Semantic Layer."

**Source**: [dbt Labs - Semantic Layer](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms)

#### M1 Finance Case Study

> "Hallucinations are almost completely eliminated, with SQL syntax errors
   and misinterpretations virtually nonexistent."

Before (Direct catalog approach):
- LLM frequently responded with hallucinations
- SQL queries could run but retrieved wrong data

After (Semantic layer):
- LLM serves as interface between user and semantic layer
- SQL output always conforms to how data team wants it queried
- Business users only submit queries for predefined, vetted metrics

**Source**: [M1 Finance Case Study](https://www.getdbt.com/blog/m1-finance-ai-self-service-claude-dbt)

### Token Optimization

> "In production RAG systems, 30-40% of retrieved context is semantically
   redundant. That's wasted tokens, higher API costs, and confused model outputs."

#### Strategies

1. **Front-load critical instructions**
2. **Trim redundant context**
3. **Use structured data formats**
4. **Compress with memory engines** (up to 80% reduction)

> "Mem0's memory compression engine intelligently distills conversations
   into optimized representations, cutting token usage by up to 80%
   while preserving fidelity."

### Context Window Evolution

| Year | Model | Context Window |
|------|-------|----------------|
| 2022 | ChatGPT | 4K tokens |
| 2024 | Gemini 1.5 Pro | 1M tokens |
| 2025 | GPT-4.1 | 1M tokens |
| 2025 | Llama 4 | 10M tokens |

**Caveat**: Larger ≠ better. Computational cost increases quadratically.

### Hallucination Prevention

> "Proper context engineering reduces hallucinations by 30-50% through
   several mechanisms. RAG systems ground responses in verified knowledge
   sources rather than relying on parametric memory."

**Strategies**:
1. Ground responses in verified sources
2. Use semantic layers for business logic
3. Constrain outputs with validation
4. Provide explicit success criteria

**Source**: [RAGFlow - From RAG to Context](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)

---

## Part 3: Prompt Management Infrastructure

### Langfuse Capabilities

| Feature | Description |
|---------|-------------|
| **Version Control** | Track all prompt iterations |
| **Labels** | Deploy to environments (dev, staging, prod) |
| **A/B Testing** | Compare prompt versions |
| **Caching** | Client-side caching for zero latency |
| **Observability** | Track metrics, costs, quality |

**Source**: [Langfuse Documentation](https://langfuse.com/docs/prompt-management/overview)

### Separation of Concerns

> "When prompts live in Langfuse, non-technical team members update them
   directly in the UI while your application automatically fetches the
   latest version. This separation of concerns means prompt updates deploy
   instantly, without needing to involve engineering or triggering a deployment."

### A/B Testing Workflow

1. **Create variants**: Label versions `prod-a` and `prod-b`
2. **Randomize selection**: Application alternates between versions
3. **Track metrics**: Langfuse captures per-version data
4. **Compare**: Latency, cost, token usage, quality scores

```python
# Langfuse A/B testing pattern
import random

variant = random.choice(["prod-a", "prod-b"])
prompt = langfuse.get_prompt("report-generation", label=variant)

# Execute with tracking
with langfuse.trace(name="report") as trace:
    trace.update(metadata={"prompt_variant": variant})
    result = llm.invoke(prompt)
```

### Best Practices for A/B Testing

**When to use**:
- ✅ App has good success metrics
- ✅ Deals with varied user inputs
- ✅ Already validated on test datasets
- ✅ Consumer apps where mistakes aren't critical

**When NOT to use**:
- ❌ High-stakes decisions (financial, medical)
- ❌ No clear success metrics
- ❌ Haven't tested on datasets first

**Source**: [Langfuse A/B Testing](https://langfuse.com/docs/prompt-management/features/a-b-testing)

### Production Patterns

#### 1. Prompt as Code
> "Prompt is the core asset of LLM applications and needs to be managed
   in a standardized way like code management."

#### 2. Centralized Repository
> "A centralized repository acts as the main hub for managing prompts
   across different teams and projects. This setup minimizes duplication
   and ensures prompt engineering remains consistent."

#### 3. CI/CD Integration
> "Many of these tools can also be integrated into CI/CD pipelines,
   streamlining testing and deployment."

#### 4. Monitoring & Observability
Track:
- Usage statistics
- Latency trends
- Execution logs
- Cost metrics
- Quality scores

**Source**: [LLM Prompt Management Tools](https://medium.com/@kuldeep.paul08/llm-prompt-management-tools-a-comprehensive-guide-for-production-ai-systems-a7695768ca2d)

---

## Synthesis: Skill Design Implications

### Tier-1: Prompt Engineering Skill

**Patterns to include**:
1. Zero-shot, few-shot, chain-of-thought techniques
2. Task decomposition for complex prompts
3. Few-shot example design (3 examples, edge cases)
4. Anti-patterns (number leakage, verbose instructions)
5. Security (prompt injection prevention)

### Tier-1: Context Engineering Skill

**Patterns to include**:
1. Semantic layer architecture (Layer 1-4)
2. Token optimization strategies
3. Section ordering and prioritization
4. Placeholder patterns for deterministic values
5. Hallucination prevention techniques

### Tier-1: Prompt Management Skill

**Patterns to include**:
1. Langfuse integration patterns
2. Version control workflow
3. Label-based deployment (dev → staging → prod)
4. A/B testing methodology
5. Observability and metrics

### Tier-2: Report Prompt Workflow

**Composed from Tier-1 skills**:
- Uses prompt engineering for template design
- Uses context engineering for data formatting
- Uses prompt management for versioning and testing

---

## Key Takeaways

1. **Semantic Layer is critical**: 83% accuracy vs ~30% without it
2. **Separate concerns**: Code handles numbers, LLM handles narrative
3. **Placeholders prevent hallucination**: Inject values deterministically
4. **Few-shot examples**: 3 examples optimal, include edge cases
5. **Version control prompts**: Treat as code artifacts
6. **A/B test in production**: After thorough dataset testing
7. **Monitor everything**: Latency, cost, quality, usage

---

## References

### Prompt Engineering
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Lakera - Ultimate Guide 2025](https://www.lakera.ai/blog/prompt-engineering-guide)
- [Palantir Best Practices](https://www.palantir.com/docs/foundry/aip/best-practices-prompt-engineering)
- [DigitalOcean - Best Practices](https://www.digitalocean.com/resources/articles/prompt-engineering-best-practices)

### Context Engineering
- [dbt Labs - Semantic Layer for LLMs](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms)
- [M1 Finance Case Study](https://www.getdbt.com/blog/m1-finance-ai-self-service-claude-dbt)
- [RAGFlow - From RAG to Context](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)
- [Elastic - Context Engineering](https://www.elastic.co/search-labs/blog/context-engineering-overview)
- [Mem0 - Context Engineering Guide](https://mem0.ai/blog/context-engineering-ai-agents-guide)

### Prompt Management
- [Langfuse Documentation](https://langfuse.com/docs/prompt-management/overview)
- [Langfuse A/B Testing](https://langfuse.com/docs/prompt-management/features/a-b-testing)
- [LLM Prompt Management Tools](https://medium.com/@kuldeep.paul08/llm-prompt-management-tools-a-comprehensive-guide-for-production-ai-systems-a7695768ca2d)

### Hallucination Prevention
- [AWS - Reducing Hallucinations](https://aws.amazon.com/blogs/machine-learning/reducing-hallucinations-in-llm-agents-with-a-verified-semantic-cache-using-amazon-bedrock-knowledge-bases/)
- [Red Hat - LLM Hallucinations](https://www.redhat.com/en/blog/when-llms-day-dream-hallucinations-how-prevent-them)
