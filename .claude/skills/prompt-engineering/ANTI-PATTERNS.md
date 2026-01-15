# Prompt Engineering Anti-Patterns

**Reference**: Common mistakes that reduce prompt effectiveness.

---

## Anti-Pattern Matrix

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| **Number Leakage** | LLM hallucinates numbers | Use placeholders, inject deterministically |
| **Verbose Instructions** | LLM ignores long text | Front-load critical instructions |
| **Missing Examples** | Cold-start problem | Add 3 few-shot examples |
| **Prompt Injection** | Security vulnerability | Input validation, output filtering |
| **Over-Engineering** | Longer ≠ better | Keep prompts focused |
| **Every Technique** | Using all techniques at once | Select for specific challenges |

---

## 1. Number Leakage

**Problem**: LLMs hallucinate specific numbers, percentages, and statistics.

```
❌ Bad: "The stock rose 15.3% with RSI at 72..."
   → LLM may generate "rose 18.7%" or "RSI at 68"
```

**Solution**: Use placeholder pattern and inject deterministically.

```python
# In prompt template
"The stock changed {{PRICE_CHANGE_PCT}} with RSI at {{RSI}}..."

# Post-processing
report = report.replace("{{PRICE_CHANGE_PCT}}", f"{actual_change:.1f}%")
report = report.replace("{{RSI}}", str(actual_rsi))
```

**See**: [context-engineering/SEMANTIC-LAYER.md](../context-engineering/SEMANTIC-LAYER.md)

---

## 2. Verbose Instructions

**Problem**: Critical instructions buried in long prompts get ignored.

```
❌ Bad:
"You are a helpful assistant. Please analyze the following data
 carefully and thoroughly. Make sure to consider all aspects of
 the analysis including technical, fundamental, and sentiment
 factors. The analysis should be comprehensive but also concise.
 Remember to use Thai language and include specific numbers.
 IMPORTANT: Always mention the RSI value."

→ LLM often forgets the RSI requirement
```

**Solution**: Front-load critical instructions.

```
✅ Good:
"CRITICAL: Include RSI value in every analysis.

Analyze this stock data in Thai:
- Technical indicators
- Key risk factors
- Actionable recommendation"
```

---

## 3. Missing Examples

**Problem**: LLM doesn't know expected output format.

```
❌ Bad:
"Generate a stock report."
→ Output format varies wildly between calls
```

**Solution**: Include 3 few-shot examples.

```
✅ Good:
"Generate a stock report following this format:

Example 1: [bullish case with exact format]
Example 2: [bearish case with exact format]
Example 3: [volatile case with exact format]

Now generate for: {current_data}"
```

---

## 4. Over-Engineering

**Problem**: Adding complexity without improving output.

```
❌ Bad:
"As an expert financial analyst with deep expertise in Thai
 equity markets, technical analysis, fundamental analysis,
 macroeconomic trends, sector rotation strategies, and
 behavioral finance, please analyze..."

→ Longer prompt ≠ better output
```

**Solution**: Keep prompts focused on essential instructions.

```
✅ Good:
"You are a Thai financial analyst.
Analyze {ticker} focusing on: trend, momentum, risk.
Output in Thai, 10-15 sentences."
```

---

## 5. Using Every Technique

**Problem**: Mixing incompatible techniques.

```
❌ Bad:
"Let's think step by step (CoT).
Here are 5 examples (few-shot).
You are an expert (role).
Consider multiple approaches (ToT)..."

→ Conflicting instructions confuse the model
```

**Solution**: Select technique based on specific challenge.

| Challenge | Use |
|-----------|-----|
| Need reasoning | Chain-of-Thought only |
| Need format | Few-shot only |
| Need expertise | Role + instructions |

---

## 6. Ignoring Basics

**Problem**: Advanced techniques fail without clear foundation.

```
❌ Bad:
"[Complex multi-agent orchestration prompt]
 [Elaborate reasoning framework]
 [No clear output specification]"

→ Advanced technique can't compensate for unclear goals
```

**Solution**: Start with basics, add complexity only when needed.

```
✅ Good:
1. Clear task: "Generate a stock report"
2. Clear format: "Use this template: ..."
3. Clear constraints: "10-15 sentences, Thai language"
4. Then add: Chain-of-thought if reasoning needed
```

---

## 7. Outdated Techniques (2025)

Some techniques are less necessary with modern models:

| Outdated | Modern Alternative |
|----------|-------------------|
| Heavy XML tags | Natural language structure |
| Elaborate role backstories | Brief expertise statement |
| Multiple system prompts | Single consolidated prompt |
| Token-level control | Let model handle formatting |

---

## 8. Assuming Mind-Reading

**Problem**: Expecting LLM to infer unstated requirements.

```
❌ Bad:
"Make it good."
"Analyze thoroughly."
"Be professional."

→ Vague terms interpreted differently each time
```

**Solution**: Be specific about what "good" means.

```
✅ Good:
"Include:
 1. Trend direction with supporting indicator
 2. Risk level with specific volatility metric
 3. Actionable recommendation with entry point"
```

---

## Detection Checklist

Use this checklist when debugging prompt issues:

- [ ] Are numbers hardcoded in prompt? (Number leakage risk)
- [ ] Are critical instructions at the beginning? (Verbose risk)
- [ ] Are there at least 3 examples? (Cold-start risk)
- [ ] Is user input validated? (Injection risk)
- [ ] Is the prompt focused? (Over-engineering risk)
- [ ] Is only one main technique used? (Technique conflict risk)
- [ ] Are requirements explicitly stated? (Mind-reading risk)

---

## References

- [SKILL.md](SKILL.md) - Core principles
- [TECHNIQUES.md](TECHNIQUES.md) - Correct techniques
- [SECURITY.md](SECURITY.md) - Security patterns
