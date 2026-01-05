# Onboarding Checklist: Prompt Engineer + Context Engineer for LLM Report Generation

**Generated**: 2026-01-04
**Estimated Time**: 4-5 hours
**Focus Area**: Prompt Engineering & Context Engineering for Thai Financial Reports
**Target Audience**: Prompt engineer with LLM experience joining the project

---

## Phase 1: Prerequisites (30 min)

### Tools to Install

**Required** (must have):
- [ ] Python 3.11+ (`python --version`)
- [ ] Git (`git --version`)
- [ ] VS Code or PyCharm with Python extension
- [ ] AWS CLI v2 (`aws --version`) - for CloudWatch log inspection
- [ ] `jq` for JSON parsing (`jq --version`)

**Optional** (for full observability):
- [ ] Doppler CLI (`doppler --version`) - secrets management
- [ ] Node.js 18+ (for frontend inspection, `node --version`)

**Installation guides**:
- Python: https://www.python.org/downloads/
- AWS CLI: https://aws.amazon.com/cli/
- Doppler: `brew install dopplerhq/cli/doppler` (macOS)

---

### Access Required

**Critical** (cannot proceed without):
- [ ] GitHub repository access (read/write)
  - Repository: `dr-daily-report_telegram`
  - Request from: Team lead
  - Verification: `git clone <repo-url>`

- [ ] Doppler access (secrets management)
  - Project: `dr-daily-report`
  - Environments: `dev`, `local_dev`
  - Request from: DevOps
  - Verification: `doppler projects list`

**Important** (needed for actual work):
- [ ] OpenRouter API key (for GPT-4 access via OpenRouter)
  - Purpose: LLM report generation testing
  - Request from: Team lead
  - Add to: Doppler `local_dev` config as `OPENROUTER_API_KEY`

- [ ] Langfuse account (LLM observability platform)
  - Purpose: Tracing prompt executions, measuring quality scores
  - Request from: Team lead
  - Keys: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

**Optional** (nice to have):
- [ ] AWS Console access (IAM user)
  - Purpose: Inspect CloudWatch logs, Lambda invocations
  - Request from: DevOps

---

## Phase 2: Environment Setup (1 hour)

### Step 1: Clone Repository

```bash
# Clone main repository
git clone https://github.com/org/dr-daily-report_telegram.git
cd dr-daily-report_telegram

# Checkout dev branch (default branch for development)
git checkout dev

# Verify repository structure
ls -la
# Should see: src/, docs/, .claude/, prompt_templates/
```

**Expected**: Repository cloned, dev branch checked out

---

### Step 2: Install Backend Dependencies

```bash
# Create virtual environment (or use shared venv - see Principle #17)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify LLM-related packages installed
pip list | grep -E "(langchain|openai|langfuse)"
# Should see: langchain-core, langchain-openai, langfuse
```

**Expected**: All dependencies installed, no errors

**Common issue**: Package version conflicts
**Solution**: Use Python 3.11 (pinned version has compatible dependencies)

---

### Step 3: Configure Secrets (Doppler)

```bash
# Setup Doppler (run in project root)
doppler setup

# Select project: dr-daily-report
# Select config: local_dev

# Verify secrets available
doppler secrets list

# Test LLM API key access
doppler run -- echo $OPENROUTER_API_KEY
# Should show: sk-or-...
```

**Expected**: Doppler configured, secrets accessible

**Common issue**: `doppler: command not found`
**Solution**: Install Doppler CLI: `brew install dopplerhq/cli/doppler` (macOS)

---

### Step 4: Verify Prompt Templates Exist

```bash
# List prompt templates
find src/report/prompt_templates -name "*.txt"

# Should see:
# src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt

# Read template structure
cat src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt | head -50
```

**Expected**: Template file exists and contains `<system>`, `<examples>`, `<task>`, `<placeholders>`, `<data>` sections

---

### Step 5: Run Basic Test

```bash
# Run prompt builder unit tests
doppler run -- pytest tests/report/test_prompt_builder.py -v

# Should see:
# test_load_main_prompt_template PASSED
# test_build_prompt PASSED
# ... (all tests pass)
```

**Expected**: All prompt builder tests pass

**Common issue**: Import errors, module not found
**Solution**: Ensure virtual environment activated: `source venv/bin/activate`

---

## Phase 3: Core Architecture Understanding (1 hour)

### CRITICAL CONCEPT: Three-Layer Semantic Architecture

**The #1 most important concept for this role:**

The project uses a **three-layer architecture** that COMPLETELY changes how you approach prompt engineering compared to typical LLM applications.

#### Layer 1: Ground Truth Calculation (Code)

**What**: Calculate exact numeric values from raw data
**Who**: Python code in `src/analysis/` and `src/workflow/workflow_nodes.py`
**Output**: Deterministic numbers (e.g., `uncertainty_score = 42.5`, `atr_pct = 2.3`)

**Files to inspect**:
```bash
# Market condition calculations
cat src/analysis/market_analyzer.py | grep -A 10 "calculate_market_conditions"

# Technical indicators
cat src/analysis/technical_analysis.py | grep -A 10 "calculate_rsi"
```

---

#### Layer 2: Semantic State Classification (Code)

**What**: Convert numbers into categorical semantic states
**Who**: Python code in `src/analysis/semantic_state_generator.py`
**Output**: Code-enforced semantic labels (e.g., `RiskRegime.HIGH`, `MomentumState.STRONG`)

**Why this matters for prompts**: The LLM receives semantic states ("ความเสี่ยงสูง"), NOT raw numbers ("uncertainty is 75.3"). This prevents numerical hallucinations.

**Key file to read**:
```bash
# Semantic state generator (converts numbers → states)
cat src/analysis/semantic_state_generator.py | head -200
```

**Example transformation**:
```python
# Layer 1 (code): uncertainty_score = 75.3
# Layer 2 (code): RiskRegime.HIGH
# Layer 3 (LLM): "ตลาดมีความเสี่ยงสูง" (no number mentioned)
```

---

#### Layer 3: Narrative Synthesis (LLM)

**What**: LLM receives semantic context, generates narrative
**Who**: Your prompts! (`src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt`)
**Output**: Natural Thai language report bounded by semantic constraints

**Key principle for prompt engineering**:

> **"Code decides what numbers MEAN, LLM decides how meanings COMBINE"**

The LLM's role is narrative synthesis, **not numerical reasoning**.

---

### Required Reading (read in this order)

1. [ ] **`docs/adr/001-adopt-semantic-layer-architecture.md`** (15 min)
   - Why we use semantic layers (300% accuracy improvement)
   - Three-layer pattern detailed explanation
   - Historical context (why multi-stage was removed)
   - **CRITICAL**: Read this FIRST - explains entire architecture philosophy

2. [ ] **`docs/SEMANTIC_LAYER_ARCHITECTURE.md`** (10 min)
   - Implementation guide for semantic layers
   - Code examples showing layer transitions
   - Anti-patterns to avoid

3. [ ] **`.claude/CLAUDE.md`** - Core Principles section (15 min)
   - Principle #1: Defensive Programming (fail fast, validate inputs)
   - Principle #2: Progressive Evidence Strengthening (verify outputs)
   - Principle #18: Logging Discipline (storytelling pattern)
   - **Why critical**: Explains how to verify prompt outputs systematically

4. [ ] **`src/report/prompt_builder.py`** (20 min)
   - Read entire file (~540 lines, well-documented)
   - Understand placeholder injection system
   - See how context is assembled from semantic states
   - **Focus on**: `build_prompt()`, `_has_value()`, `_build_placeholder_list()`

---

## Phase 4: Prompt Engineering Patterns (1 hour)

### Pattern 1: Placeholder-Based Number Injection

**Problem**: LLMs hallucinate financial numbers when asked to "fill in" values.

**Solution**: Prompt contains `{{PLACEHOLDERS}}`, code replaces with exact values AFTER LLM generation.

**How it works**:

1. **Prompt template** (input to LLM):
```
ความไม่แน่นอน {{UNCERTAINTY}}/100 แสดงถึงความเสี่ยง{{UNCERTAINTY_LEVEL}}
ATR {{ATR_PCT}}% บอกว่าราคาแกว่งตัว{{VOLATILITY_LEVEL}}
```

2. **LLM generates** (with placeholders intact):
```
ความไม่แน่นอน {{UNCERTAINTY}}/100 แสดงถึงความเสี่ยงสูง
ATR {{ATR_PCT}}% บอกว่าราคาแกว่งตัวรุนแรง
```

3. **Code replaces placeholders** (post-processing):
```
ความไม่แน่นอน 75/100 แสดงถึงความเสี่ยงสูง
ATR 3.2% บอกว่าราคาแกว่งตัวรุนแรง
```

**Implementation files**:
```bash
# Number injection logic
cat src/report/number_injector.py | head -200

# Placeholder definitions (single source of truth)
cat src/report/number_injector.py | grep -A 50 "get_placeholder_definitions"
```

**Key insight**: The LLM never sees actual numbers, only semantic descriptions. Numbers are injected deterministically after generation.

---

### Pattern 2: Dynamic Placeholder Filtering

**Problem**: Not all data is available for every ticker (e.g., no fundamentals for crypto, no strategy data for new tickers).

**Solution**: Prompt builder filters placeholders based on actual data availability.

**How it works**:

1. **Check data availability** (code):
```python
# If pe_ratio exists in ticker_data
if self._has_value('PE_RATIO', ground_truth, indicators, percentiles, ticker_data, ...):
    fundamental_vars += "{PE_RATIO}, "
```

2. **Build dynamic placeholder list**:
```python
# Available: {PE_RATIO}, {EPS}, {MARKET_CAP}
# Unavailable: {DIVIDEND_YIELD}, {BETA}
# Result: "PE_RATIO, EPS, MARKET_CAP"
```

3. **Inject into template**:
```
Fundamentals:
{PE_RATIO}, {EPS}, {MARKET_CAP}  # Only available placeholders
```

**Why this matters**: LLM never gets confused by missing data. If placeholder not in template, LLM doesn't try to use it.

**Implementation**:
```bash
# See _build_placeholder_list() method
cat src/report/prompt_builder.py | grep -A 50 "_build_placeholder_list"

# See _has_value() method (data availability checker)
cat src/report/prompt_builder.py | grep -A 100 "_has_value"
```

---

### Pattern 3: Semantic Context Building

**Problem**: Feeding raw data to LLM leads to over-reliance on technical analysis (60%+ of report), ignoring fundamentals.

**Solution**: `ContextBuilder` assembles semantic context with balanced coverage across all data sources.

**Context structure** (`src/report/context_builder.py`):

```
SECTION 1: Semantic States (Layer 2 output)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Risk Regime: HIGH (ความเสี่ยงสูง)
Market Momentum: STRONG (โมเมนตัมแข็งแกร่ง)
Volatility Regime: MODERATE (ความผันผวนปานกลาง)

SECTION 2: Fundamental Data (factual only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Company: DBS Bank Ltd
Sector: Financial Services
Market Cap: $45.2B

SECTION 3: Technical Indicators (states, not numbers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RSI: Neutral (50-70)
MACD: Bullish crossover detected

SECTION 4: News Summary (sentiment only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recent news sentiment: Positive (3 positive, 1 neutral)
Key themes: Earnings beat expectations, dividend increase
```

**Key insight**: Context provides semantic states (Layer 2), NOT raw numbers. LLM synthesizes narrative from states.

**Implementation**:
```bash
# Context builder - read prepare_context() method
cat src/report/context_builder.py | head -250
```

---

### Pattern 4: Example-Driven Prompts (Few-Shot Learning)

**Problem**: Thai language financial reports require specific tone and structure.

**Solution**: Prompt template contains 3 detailed examples (bullish, bearish, high volatility) showing exact format.

**Template structure** (`main_prompt_v4_minimal.txt`):

```xml
<system>
You write Thai stock reports for retail investors.
Core rule: Replace ALL numbers with {{PLACEHOLDERS}}.
</system>

<examples>
Example 1 - Bullish Case (DBS19):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 **เรื่องราวของหุ้นตัวนี้**
[230 words of example narrative using placeholders]

Example 2 - Bearish Case (AAPL):
[230 words showing different narrative structure]

Example 3 - High Volatility Case (NVDA):
[230 words showing risk-focused narrative]
</examples>

<task>
Write a 250-350 word Thai stock report for {TICKER}...
</task>

<placeholders>
Risk Metrics (Core):
{RISK_METRICS}

Fundamentals:
{FUNDAMENTAL_VARIABLES}
...
</placeholders>

<data>
{CONTEXT}
</data>
```

**Key insight**: Examples teach the LLM:
- Tone: Conversational ("เหมือนคุยกับเพื่อน"), not academic
- Structure: 📖 Story → 💡 Analysis → 🎯 Action → ⚠️ Risks
- Placeholder usage: `{{UNCERTAINTY}}` not raw numbers
- Length: 250-350 words (Thai counts as ~1.2x English tokens)

---

### Pattern 5: Post-Processing Pipeline

**Problem**: LLM output needs enrichment (news citations, transparency footer, number injection).

**Solution**: Multi-stage post-processing after LLM generation.

**Pipeline stages**:

1. **LLM generation** (raw output with placeholders):
```python
response = self.llm.invoke(prompt)
report = response.content
```

2. **Number injection** (replace placeholders):
```python
report = self.number_injector.inject_deterministic_numbers(
    report, ground_truth, indicators, percentiles, ticker_data, ...
)
```

3. **News references** (add citations):
```python
if news:
    news_references = self.news_fetcher.get_news_references(news)
    report += f"\n\n{news_references}"
```

4. **Transparency footer** (data sources disclosure):
```python
transparency_footer = self.transparency_footer.generate_data_usage_footnote(state)
report += f"\n\n{transparency_footer}"
```

**Implementation**:
```bash
# Post-processing pipeline
cat src/report/report_generator_simple.py | grep -A 50 "_post_process_report"
```

---

## Phase 5: Context Engineering Patterns (45 min)

### Context Assembly Strategy

**File**: `src/report/context_builder.py`

**Key methods to understand**:

1. **`prepare_context()`** - Main entry point
   - Assembles all sections into single context string
   - Applies section presence logic (optional sections)
   - Returns semantic context for LLM

2. **Section formatters** (unified pattern via `SectionRegistry`):
   - `format_fundamental_section()` - Company basics
   - `format_technical_section()` - Indicators
   - `format_percentile_context()` - Historical context
   - `format_news_summary_section()` - News sentiment
   - Comparative, strategy, SEC filings (optional)

**Exercise: Trace context assembly**:

```bash
# Read ContextBuilder.__init__()
cat src/report/context_builder.py | grep -A 20 "def __init__"

# Read prepare_context() method
cat src/report/context_builder.py | grep -A 100 "def prepare_context"

# Understand section registry pattern
cat src/report/section_formatters.py | head -100
```

---

### Data Availability Handling

**Problem**: Not all tickers have complete data (e.g., crypto lacks fundamentals, new tickers lack historical patterns).

**Solution**: Section presence detection + fallback messages.

**Implementation**:

1. **Detect section presence** (ContextBuilder):
```python
section_presence = self.context_builder.get_section_presence(
    strategy_performance=strategy_performance,
    comparative_insights=comparative_insights,
    sec_filing_data=sec_filing_data,
    ...
)
```

2. **Conditional section inclusion**:
```python
if section_presence.get('strategy', False):
    context += self._format_strategy_section(strategy_performance)
else:
    context += "(strategy data not available for this ticker)"
```

3. **Placeholder filtering** (PromptBuilder):
```python
# Only include placeholders with actual data
if self._has_value('PE_RATIO', ticker_data, ...):
    fundamental_vars += "{PE_RATIO}, "
```

**Key insight**: Context engineering is about selective inclusion, not completeness. Missing data is acknowledged, not hidden.

---

## Phase 6: Observability & Verification (30 min)

### Langfuse Integration (LLM Tracing)

**File**: `src/integrations/langfuse_client.py`

**What it does**: Traces every LLM call with inputs, outputs, latency, costs.

**Usage pattern**:

```python
from src.evaluation import observe

@observe(name="generate_report")
def generate_report(ticker, raw_data):
    # Langfuse automatically traces:
    # - Function inputs (ticker, raw_data)
    # - LLM calls (prompt, response)
    # - Execution time
    # - Errors (if any)
    report = self.llm.invoke(prompt)
    return report
```

**View traces**:
1. Go to Langfuse dashboard: https://cloud.langfuse.com
2. Navigate to "Traces" → filter by `ticker` or `name`
3. Inspect:
   - Prompt sent to LLM (full text)
   - LLM response (raw output)
   - Token counts (input + output)
   - Latency (ms)

**Why critical for prompt engineering**: You can A/B test prompt changes and see exact impact on output quality and cost.

---

### CloudWatch Logging (Production Debugging)

**Pattern**: Narrative logging (storytelling approach)

**Example logs** (from `src/report/prompt_builder.py`):

```python
logger.info("🔨 [PromptBuilder] Building prompt from template")
logger.info(f"   📊 Input parameters:")
logger.info(f"      - Context length: {len(context)} characters")
logger.info(f"      - Strategy performance included: {has_strategy}")

logger.info("━" * 70)
logger.info("📝 TEMPLATE VARIABLE VALUES:")
logger.info(f"   {{TICKER}} = {ticker}")
logger.info(f"   {{RISK_METRICS}} = {risk_vars[:100]}...")
logger.info("━" * 70)

logger.info(f"   ✅ Final prompt built: {len(final_prompt)} chars")
```

**View logs in production**:

```bash
# Tail Lambda logs (last 5 minutes)
ENV=dev doppler run -- aws logs tail /aws/lambda/report_worker --since 5m

# Search for specific ticker
ENV=dev doppler run -- aws logs tail /aws/lambda/report_worker --since 1h | grep "AAPL"

# Filter by log level
ENV=dev doppler run -- aws logs tail /aws/lambda/report_worker --since 10m | grep "ERROR"
```

**Key insight**: Logs tell a story - you can reconstruct entire prompt generation flow from logs without code inspection.

---

### Quality Scoring System

**Files**:
- `src/scoring/faithfulness_scorer.py` - Measures hallucinations
- `src/scoring/completeness_scorer.py` - Checks required sections
- `src/scoring/compliance_scorer.py` - Validates placeholder usage
- `src/scoring/reasoning_quality_scorer.py` - Assesses logic coherence

**How scores work**:

1. **Faithfulness** (0-100): Does report cite actual data from context?
   - Checks: Numbers match ground truth, no invented facts
   - Penalty: -20 points per hallucination

2. **Completeness** (0-100): Does report cover all required sections?
   - Checks: 📖 Story, 💡 Analysis, 🎯 Action, ⚠️ Risks
   - Penalty: -25 points per missing section

3. **Compliance** (0-100): Does report use placeholders correctly?
   - Checks: No raw numbers leaked, placeholders replaced
   - Penalty: -10 points per compliance violation

4. **Reasoning Quality** (0-100): Is analysis coherent?
   - Checks: Logical flow, supported conclusions
   - Penalty: -15 points per reasoning gap

**View scores in Langfuse**:
- Scores attached to each trace as metadata
- Can filter traces by score range (e.g., "show all reports with faithfulness < 80")

---

## Phase 7: Common Pitfalls & Anti-Patterns (30 min)

### Pitfall 1: Number Leakage in Prompts

**Symptom**: LLM output contains raw numbers instead of placeholders

**Cause**: Prompt examples show actual numbers, LLM learns to output numbers directly

**Example (BAD)**:
```xml
<example>
DBS19 มีความเสี่ยง 75/100 และความผันผวน 3.2%
</example>
```

**Solution**: Always use placeholders in examples
```xml
<example>
DBS19 มีความเสี่ยง {{UNCERTAINTY}}/100 และความผันผวน {{ATR_PCT}}%
</example>
```

**Detection**: Run `src/scoring/compliance_scorer.py` - flags number leakage

---

### Pitfall 2: Over-Reliance on Technical Analysis

**Symptom**: Reports focus 60%+ on technical indicators, ignore fundamentals

**Cause**: Context provides more technical data than fundamental data

**Solution**: Balance context sections
```python
# Ensure context includes:
# - Fundamentals (30% of content)
# - Technical (30% of content)
# - News (20% of content)
# - Risk metrics (20% of content)
```

**Detection**: Manually review 10 sample reports, count sentences per category

---

### Pitfall 3: Hallucinating Missing Data

**Symptom**: LLM generates analysis for data that doesn't exist (e.g., P/E ratio for crypto)

**Cause**: Placeholder included in prompt but data not available

**Solution**: Dynamic placeholder filtering (Pattern 2)
```python
# PromptBuilder._build_placeholder_list() filters unavailable data
if not self._has_value('PE_RATIO', ticker_data):
    # Don't include {PE_RATIO} in template
    pass
```

**Prevention**: Always check `_has_value()` before adding placeholder

---

### Pitfall 4: Inconsistent Thai Tone

**Symptom**: Reports sound too formal or academic, not conversational

**Cause**: Prompt examples don't establish clear tone guidelines

**Solution**: Add tone specification to `<system>` block
```xml
<system>
You write Thai stock reports for retail investors.
Tone: Conversational (เหมือนคุยกับเพื่อน), not academic.
Avoid: Jargon, passive voice, overly complex sentences.
</system>
```

**Detection**: Manual review by native Thai speaker

---

### Pitfall 5: Ignoring Prompt Length Limits

**Symptom**: LLM truncates analysis or drops sections

**Cause**: Context + prompt exceeds model's input limit (e.g., 8K tokens for GPT-4)

**Solution**: Monitor context length before LLM call
```python
estimated_tokens = len(final_prompt) // 4  # Rough estimate
if estimated_tokens > 7000:
    logger.warning(f"Prompt too long: {estimated_tokens} tokens (limit: 8000)")
    # Truncate optional sections or summarize context
```

**Prevention**: Always log prompt length (already implemented in PromptBuilder)

---

## Phase 8: "Hello World" Tasks (30 min)

### Task 1: Read and Understand Existing Prompt Template

```bash
# Read main prompt template
cat src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt

# Questions to answer:
# 1. How many example reports are provided? (3)
# 2. What are the 4 required sections? (📖 Story, 💡 Analysis, 🎯 Action, ⚠️ Risks)
# 3. How many placeholder categories exist? (9)
# 4. What's the target word count? (250-350 words)
```

**Expected**: ✅ Template structure understood

---

### Task 2: Generate Test Report Locally

```bash
# Run simple report generation test
doppler run -- python -c "
from src.report.report_generator_simple import SimpleReportGenerator
from tests.fixtures.mock_data import get_mock_ticker_data

# Initialize generator
generator = SimpleReportGenerator()

# Generate report for test ticker
raw_data = get_mock_ticker_data('DBS19')
result = generator.generate_report('DBS19', raw_data)

print('Report generated:')
print(result['report_text'][:500])  # First 500 chars
print(f'\nGeneration time: {result[\"generation_time_ms\"]}ms')
print(f'Estimated tokens: {result[\"api_costs\"][\"estimated_input_tokens\"]}')
"
```

**Expected**: ✅ Report generates successfully, contains placeholders replaced with actual numbers

**If failed**: Check Doppler secrets configured (`OPENROUTER_API_KEY`)

---

### Task 3: Trace Prompt Execution in Langfuse

```bash
# Run report generation with Langfuse tracing
doppler run -- python scripts/test_report_with_tracing.py

# Then visit Langfuse dashboard:
# https://cloud.langfuse.com
# Navigate to: Traces → Filter by "generate_report"

# Inspect:
# - Prompt sent to LLM (full text)
# - LLM response (raw output)
# - Execution time (should be ~3-5s)
# - Token counts (input ~3000, output ~800)
```

**Expected**: ✅ Trace appears in Langfuse, full prompt visible

---

### Task 4: Make Small Prompt Change and Compare Outputs

```bash
# Create feature branch
git checkout -b prompt-test-{your-name}

# Edit prompt template (add 1 sentence to <system> block)
vim src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt

# Add after line 3:
# Use specific examples with numbers when explaining risks.

# Save and test locally
doppler run -- pytest tests/report/test_prompt_builder.py -v

# Generate report with new prompt
doppler run -- python scripts/test_report_with_tracing.py

# Compare:
# - Old trace (in Langfuse, before change)
# - New trace (in Langfuse, after change)
# - Check: Does output change as expected?
```

**Expected**: ✅ Prompt change reflected in LLM output, visible in Langfuse comparison

---

## Phase 9: Key Files to Bookmark (10 min)

### Prompt Engineering Files

- [ ] `src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt` - Main prompt template (YOU WILL EDIT THIS MOST)
- [ ] `src/report/prompt_builder.py` - Prompt assembly logic
- [ ] `src/report/number_injector.py` - Placeholder definitions and replacement
- [ ] `tests/report/test_prompt_builder.py` - Prompt builder tests
- [ ] `tests/report/test_prompt_builder_template.py` - Template validation tests

### Context Engineering Files

- [ ] `src/report/context_builder.py` - Context assembly logic (YOU WILL EDIT THIS OFTEN)
- [ ] `src/analysis/semantic_state_generator.py` - Semantic state classification (Layer 2)
- [ ] `src/report/section_formatters.py` - Section formatting utilities
- [ ] `src/analysis/market_analyzer.py` - Market condition calculations (Layer 1)

### Observability Files

- [ ] `src/integrations/langfuse_client.py` - LLM tracing integration
- [ ] `src/scoring/` - Quality scoring modules (faithfulness, completeness, compliance, reasoning)
- [ ] `src/evaluation/__init__.py` - Evaluation decorators

### Documentation

- [ ] `docs/adr/001-adopt-semantic-layer-architecture.md` - Architecture philosophy (READ FIRST)
- [ ] `docs/SEMANTIC_LAYER_ARCHITECTURE.md` - Implementation guide
- [ ] `docs/CODE_STYLE.md` - Coding standards
- [ ] `.claude/CLAUDE.md` - Core principles (especially #2 Progressive Evidence Strengthening, #18 Logging Discipline)

---

## Phase 10: First Real Task (30 min)

### Task Options (pick one)

**Option A: Improve Prompt Clarity** (Beginner)
- **Issue**: Add more explicit risk warning thresholds to prompt examples
- **Skills**: Prompt engineering, few-shot learning
- **Files**: `main_prompt_v4_minimal.txt`
- **Success criteria**: Risk warnings become more specific in generated reports

**Option B: Add New Placeholder Category** (Intermediate)
- **Issue**: Add support for ESG (Environmental, Social, Governance) metrics
- **Skills**: Placeholder system, context building, number injection
- **Files**: `number_injector.py`, `prompt_builder.py`, `context_builder.py`
- **Success criteria**: ESG data appears in reports when available

**Option C: Optimize Context Length** (Advanced)
- **Issue**: Reduce average context length by 20% without losing information
- **Skills**: Context engineering, semantic state optimization
- **Files**: `context_builder.py`, `section_formatters.py`
- **Success criteria**: Prompt tokens reduced, quality scores unchanged

---

## Completion Checklist

**Phase 1: Prerequisites**
- [ ] All tools installed and verified
- [ ] Access granted (GitHub, Doppler, OpenRouter, Langfuse)

**Phase 2: Environment**
- [ ] Repository cloned, dependencies installed
- [ ] Doppler configured, secrets accessible
- [ ] Prompt templates verified

**Phase 3: Architecture**
- [ ] Three-layer architecture understood (Layer 1: Code ground truth, Layer 2: Semantic states, Layer 3: LLM narrative)
- [ ] Required documentation read (ADR-001, SEMANTIC_LAYER_ARCHITECTURE.md, CLAUDE.md principles)
- [ ] Core files inspected (prompt_builder.py, context_builder.py, semantic_state_generator.py)

**Phase 4: Prompt Patterns**
- [ ] Placeholder-based injection understood
- [ ] Dynamic placeholder filtering understood
- [ ] Semantic context building understood
- [ ] Example-driven prompts (few-shot) understood
- [ ] Post-processing pipeline understood

**Phase 5: Context Patterns**
- [ ] Context assembly strategy understood
- [ ] Data availability handling understood
- [ ] Section presence detection understood

**Phase 6: Observability**
- [ ] Langfuse tracing tested
- [ ] CloudWatch logging inspected
- [ ] Quality scoring system understood

**Phase 7: Pitfalls**
- [ ] Number leakage anti-pattern understood
- [ ] Over-reliance on technical analysis avoided
- [ ] Hallucinating missing data prevented
- [ ] Thai tone consistency maintained
- [ ] Prompt length limits monitored

**Phase 8: Hello World**
- [ ] Prompt template read and understood
- [ ] Test report generated locally
- [ ] Trace inspected in Langfuse
- [ ] Prompt change tested and compared

**Phase 9: Files Bookmarked**
- [ ] Key files bookmarked in IDE

**Phase 10: First Task**
- [ ] Task selected and started

---

## Next Steps After Onboarding

1. **Practice prompt iterations**:
   - Change 1 variable at a time (tone, length, example count)
   - Track impact in Langfuse (output quality, token usage)
   - A/B test changes with real tickers

2. **Learn Thai financial terminology**:
   - Review existing reports in `ground_truth/` directory
   - Ask native Thai speaker for feedback on tone
   - Build personal glossary of Thai financial terms

3. **Explore advanced patterns**:
   - Multi-step reasoning (chain-of-thought)
   - Dynamic example selection (based on market conditions)
   - Adaptive prompt length (based on data availability)

4. **Join weekly reviews**:
   - LLM quality review (Fridays) - analyze worst-performing reports
   - Prompt iteration planning (Mondays) - decide what to A/B test next

---

## Resources

### Prompt Engineering

- [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering) - Best practices for Claude models
- [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering) - GPT-specific patterns
- [LangChain Prompt Templates](https://python.langchain.com/docs/modules/model_io/prompts/) - Template system we use

### Context Engineering

- [dbt Semantic Layer for LLMs](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms) - Research basis for our architecture
- [Semantic Kernel Patterns](https://github.com/microsoft/semantic-kernel) - Context building patterns

### LLM Observability

- [Langfuse Documentation](https://langfuse.com/docs) - Tracing, scoring, prompt management
- [AWS CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) - Production debugging

### Thai Language

- [Thai Stock Market Terminology](https://www.set.or.th/en/education/glossary) - SET official glossary
- Thai Financial News: [ประชาชาติธุรกิจ](https://www.prachachat.net/), [กรุงเทพธุรกิจ](https://www.bangkokbiznews.com/)

---

## Feedback Loop

**After completing onboarding**:
1. Document what was unclear or confusing (add comments to this checklist)
2. Suggest improvements to prompt templates
3. Share "aha moments" with team
4. Update this onboarding doc with lessons learned

**Improvement process**:
```bash
# Journal your experience
/journal process "onboarding experience - what was hard"

# Identify gaps in documentation
/observe behavior "onboarding pain points"

# Propose updates
/evolve  # Detects drift, suggests improvements
```

---

## See Also

- `/consolidate "semantic layer architecture"` - Deep dive into architecture concepts
- `/explain expert "three-layer pattern"` - Expert-level explanation
- `/context "prompt engineering"` - Get relevant context for prompt work
- `docs/ARCHITECTURE_INVENTORY.md` - Complete tool inventory
- `.claude/skills/README.md` - All available slash commands

---

**Questions?** Ask in #llm-engineering Slack channel or message @prompt-lead
