# Prompt Engineering Techniques

**Reference**: Core techniques for effective LLM prompting.

---

## Technique Matrix

| Technique | Description | When to Use |
|-----------|-------------|-------------|
| **Zero-shot** | Direct task without examples | Simple, well-defined tasks |
| **Few-shot** | 1-5 examples before task | Format/style guidance needed |
| **Chain-of-Thought** | Step-by-step reasoning | Complex reasoning, math |
| **Tree-of-Thought** | Multiple reasoning paths | Exploration, creativity |
| **Role/Persona** | Assign expert identity | Domain expertise needed |
| **Meta-prompting** | LLM generates prompts | Prompt optimization |

---

## Zero-Shot Prompting

Direct instruction without examples. Best for simple tasks where the model has strong prior knowledge.

```
Classify the sentiment of this review as positive, negative, or neutral:
"The product arrived on time and works as expected."
```

**When to use**: Simple classification, translation, summarization.

**When NOT to use**: Complex formatting, domain-specific outputs.

---

## Few-Shot Prompting

Provide examples to guide output format and style.

### Optimal Configuration
- **3 examples** (diminishing returns after)
- **Include edge cases** (bullish, bearish, volatile)
- **Match output format exactly**

```python
examples = [
    {"input": "RSI=75, trend=up", "output": "Bullish momentum..."},    # Bullish case
    {"input": "RSI=25, trend=down", "output": "Bearish pressure..."},  # Bearish case
    {"input": "ATR=5%, RSI=50", "output": "High volatility..."},       # Volatile case
]
```

### Example Template

```
You are a Thai financial analyst. Generate a brief market analysis.

Example 1:
Input: RSI=75, MACD=positive, volume=high
Output: 📈 หุ้นแสดงโมเมนตัมขาขึ้นแข็งแกร่ง RSI ที่ 75 บ่งชี้แรงซื้อสูง...

Example 2:
Input: RSI=25, MACD=negative, volume=low
Output: 📉 หุ้นอยู่ในแรงกดดันขาลง RSI ที่ 25 เข้าเขต oversold...

Example 3:
Input: ATR=5%, RSI=50, MACD=neutral
Output: ⚠️ หุ้นมีความผันผวนสูง ATR 5% แนะนำระวังการเคลื่อนไหว...

Now analyze:
Input: {current_indicators}
Output:
```

---

## Chain-of-Thought (CoT)

Guide the model through step-by-step reasoning.

### Standard CoT

```
Analyze this stock step by step:

1. First, examine the trend direction from moving averages
2. Then, assess momentum from RSI and MACD
3. Next, evaluate volume patterns
4. Finally, synthesize into a recommendation

Data: {indicators}
```

### Zero-Shot CoT

Add "Let's think step by step" to trigger reasoning:

```
Determine if this stock is a buy, hold, or sell.
Let's think step by step.

Data: {indicators}
```

---

## Prompt Chaining

Break complex tasks into sequential prompts.

```python
# Stage 1: Data Analysis
prompt_1 = "Summarize the key technical indicators for {ticker}"

# Stage 2: Quality Review
prompt_2 = "Review this summary for accuracy and completeness: {summary}"

# Stage 3: Final Synthesis
prompt_3 = "Improve the summary based on this feedback: {feedback}"
```

### When to Use Chaining

- ✅ Complex multi-step analysis
- ✅ Quality assurance workflows
- ✅ Different expertise needed per step
- ❌ Simple single-output tasks (overhead not worth it)

---

## Task Decomposition

> "LLMs can struggle with overly complex tasks. Splitting into smaller steps improves both accuracy and efficiency."

### Decomposition Pattern

```
Original: "Generate a complete financial report with analysis,
           recommendations, and risk assessment"

Decomposed:
1. "Analyze technical indicators and classify trend"
2. "Identify key risks based on volatility metrics"
3. "Generate recommendations based on analysis"
4. "Synthesize into cohesive report"
```

---

## Role/Persona Prompting

Assign an expert identity to activate domain knowledge.

```
You are an experienced Thai financial analyst with 15 years of
experience in SET market analysis. You specialize in technical
analysis and risk assessment for retail investors.
```

### Modern Note (2025)

> "Heavy role prompting is less necessary with modern models like Claude and GPT-4. Use sparingly—focus on specific expertise rather than elaborate backstories."

---

## Meta-Prompting

Use LLM to generate or improve prompts.

```
I need to create a prompt for generating Thai stock market reports.
The reports should:
- Be 10-15 sentences
- Use Thai language
- Include technical analysis
- Be suitable for retail investors

Generate an effective prompt template for this task.
```

---

## Technique Selection Guide

| Scenario | Recommended Technique |
|----------|----------------------|
| Classification task | Zero-shot |
| Specific output format | Few-shot (3 examples) |
| Math or logic problem | Chain-of-Thought |
| Creative exploration | Tree-of-Thought |
| Domain expertise | Role prompting |
| Complex multi-step | Prompt chaining |
| Prompt optimization | Meta-prompting |

---

## References

- [SKILL.md](SKILL.md) - Overview and principles
- [ANTI-PATTERNS.md](ANTI-PATTERNS.md) - What to avoid
- [Prompt Engineering Guide - Techniques](https://www.promptingguide.ai/techniques)
