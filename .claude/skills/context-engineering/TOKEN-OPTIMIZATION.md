# Token Optimization

**Reference**: Strategies for efficient context usage in LLM applications.

---

## The Problem

> "In production RAG systems, 30-40% of retrieved context is semantically redundant. That's wasted tokens, higher API costs, and confused model outputs."

### Cost Impact

| Context Size | Tokens | Cost (GPT-4) |
|--------------|--------|--------------|
| Small | 2K | $0.06 |
| Medium | 8K | $0.24 |
| Large | 32K | $0.96 |
| Redundant | +40% | Wasted spend |

---

## Strategy 1: Front-Load Critical Instructions

**Problem**: Important instructions buried in long prompts get ignored.

**Solution**: Place critical information at the beginning.

```
✅ Good Structure:
1. CRITICAL REQUIREMENTS (first 100 tokens)
2. Task description
3. Context data
4. Examples
5. Output format

❌ Bad Structure:
1. Background information
2. Context data
3. Examples
4. Task description
5. CRITICAL REQUIREMENTS (buried at end)
```

### Implementation

```python
def build_prompt(self, context: str, requirements: list[str]) -> str:
    """Front-load critical requirements."""
    critical_section = "CRITICAL REQUIREMENTS:\n" + "\n".join(f"- {r}" for r in requirements)

    return f"""
{critical_section}

CONTEXT:
{context}

Generate analysis following the requirements above.
"""
```

---

## Strategy 2: Trim Redundant Context

**Problem**: Repeated information wastes tokens.

**Solution**: Deduplicate and summarize repetitive content.

### Before (Redundant)

```
News 1: "Stock XYZ rose 5% on strong earnings"
News 2: "XYZ shares gained 5% following earnings beat"
News 3: "XYZ up 5% after quarterly results"
→ Same information repeated 3x
```

### After (Deduplicated)

```
News Summary: "XYZ rose 5% on earnings beat (3 sources confirm)"
→ Single consolidated statement
```

### Implementation

```python
def deduplicate_news(self, news_items: list[dict]) -> list[dict]:
    """Remove semantically redundant news."""
    unique_news = []
    seen_topics = set()

    for item in news_items:
        # Extract key topic (simplified)
        topic = extract_topic(item['title'])

        if topic not in seen_topics:
            seen_topics.add(topic)
            unique_news.append(item)

    return unique_news
```

---

## Strategy 3: Use Structured Data Formats

**Problem**: Verbose prose wastes tokens.

**Solution**: Use structured formats for data sections.

### Before (Prose)

```
The stock's RSI indicator is currently at 72, which is considered
overbought territory. The ATR shows volatility of 2.5%, which is
moderate. The MACD line is above the signal line, indicating
bullish momentum. The current price is 5% above the 20-day VWAP.
```

### After (Structured)

```
Technical Indicators:
- RSI: 72 (OVERBOUGHT)
- ATR: 2.5% (MODERATE)
- MACD: BULLISH
- vs VWAP: +5%
```

**Token Savings**: ~60% reduction

### Implementation

```python
def format_indicators_compact(self, indicators: dict) -> str:
    """Format indicators in token-efficient structure."""
    return f"""Technical:
- RSI: {indicators['rsi']:.0f} ({classify_rsi(indicators['rsi'])})
- ATR: {indicators['atr_pct']:.1f}% ({classify_volatility(indicators['atr_pct'])})
- MACD: {classify_macd(indicators)}
- vs VWAP: {indicators['vwap_pct']:+.1f}%"""
```

---

## Strategy 4: Compress Conversation History

**Problem**: Long conversation history consumes context window.

**Solution**: Summarize older messages, keep recent ones verbatim.

### Compression Pattern

```
Old History (>5 turns): Summarized
Recent History (last 5 turns): Verbatim
Current Message: Full detail
```

### Implementation

```python
def compress_history(self, messages: list[dict], keep_recent: int = 5) -> list[dict]:
    """Compress old history, keep recent verbatim."""
    if len(messages) <= keep_recent:
        return messages

    # Summarize old messages
    old_messages = messages[:-keep_recent]
    summary = summarize_messages(old_messages)

    # Keep recent verbatim
    recent_messages = messages[-keep_recent:]

    return [{"role": "system", "content": f"Previous context: {summary}"}] + recent_messages
```

> "Mem0's memory compression engine intelligently distills conversations into optimized representations, cutting token usage by up to 80% while preserving fidelity."

---

## Strategy 5: Selective Context Inclusion

**Problem**: Including all available data overwhelms the model.

**Solution**: Select only relevant context based on task.

### Context Selection Matrix

| Task | Include | Exclude |
|------|---------|---------|
| Technical Analysis | Indicators, Price History | News, Fundamentals |
| News Summary | Headlines, Sentiment | Indicators, Charts |
| Full Report | All (prioritized) | Redundant duplicates |

### Implementation

```python
def select_context(self, task: str, available_data: dict) -> dict:
    """Select relevant context for task."""
    selection_map = {
        'technical': ['indicators', 'percentiles', 'price_history'],
        'news': ['news', 'news_summary', 'sentiment'],
        'fundamental': ['financials', 'ratios', 'sector_comparison'],
        'full_report': ['indicators', 'news_summary', 'key_financials'],
    }

    selected_keys = selection_map.get(task, selection_map['full_report'])
    return {k: v for k, v in available_data.items() if k in selected_keys}
```

---

## Token Budget Allocation

For a 4K token prompt budget:

| Section | Allocation | Tokens |
|---------|------------|--------|
| System Instructions | 10% | 400 |
| Critical Requirements | 5% | 200 |
| Context Data | 50% | 2000 |
| Few-Shot Examples | 25% | 1000 |
| Output Format | 10% | 400 |

### Implementation

```python
def allocate_tokens(self, total_budget: int = 4000) -> dict:
    """Allocate token budget by section."""
    return {
        'system': int(total_budget * 0.10),
        'requirements': int(total_budget * 0.05),
        'context': int(total_budget * 0.50),
        'examples': int(total_budget * 0.25),
        'format': int(total_budget * 0.10),
    }

def truncate_to_budget(self, text: str, max_tokens: int) -> str:
    """Truncate text to fit token budget."""
    # Approximate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text
```

---

## Monitoring Token Usage

### Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Input tokens per request | <4K | >8K |
| Output tokens per request | <1K | >2K |
| Redundancy ratio | <20% | >40% |
| Context utilization | >80% | <60% |

### Implementation

```python
def log_token_metrics(self, prompt: str, response: str):
    """Track token usage metrics."""
    input_tokens = len(prompt) // 4  # Approximate
    output_tokens = len(response) // 4

    logger.info(f"Token usage: input={input_tokens}, output={output_tokens}")

    if input_tokens > 8000:
        logger.warning(f"High token usage: {input_tokens} input tokens")
```

---

## References

- [SKILL.md](SKILL.md) - Overview
- [SEMANTIC-LAYER.md](SEMANTIC-LAYER.md) - Core architecture
- [HALLUCINATION-PREVENTION.md](HALLUCINATION-PREVENTION.md) - Accuracy patterns
- [Mem0 - Context Engineering](https://mem0.ai/blog/context-engineering-ai-agents-guide)
