# PromptOS Infrastructure Overview

**Date**: 2026-01-09
**Purpose**: Comprehensive overview of the PromptOS architecture in the daily report generation system

---

## What is PromptOS?

**PromptOS** is the "operating system" layer that orchestrates how prompts are assembled, versioned, routed, and executed for LLM-based report generation. It acts as the coordination layer between:

1. **Data Layer**: Raw market data, technical indicators, news articles
2. **Semantic Layer**: Context assembly and state classification (3-layer architecture)
3. **LLM Layer**: Prompt templates and language model execution
4. **Output Layer**: Post-processing and validation

**Current Status**: ~80% implemented, missing coordination/orchestration layer

---

## Core Architecture: Three-Layer Semantic Pattern

The foundation of PromptOS is the **Three-Layer Semantic Architecture**:

```
Layer 1: Numeric Ground Truth (numbers.py)
         ↓
Layer 2: Semantic State Classification (context_builder.py)
         ↓
Layer 3: LLM Narrative Synthesis (prompt_builder.py → LLM)
```

### Layer 1: Numeric Ground Truth
- **File**: `src/report/number_injector.py`
- **Purpose**: Single source of truth for 60+ metrics
- **Pattern**: Define calculations once, use everywhere
- **Categories**: Risk, momentum, trend, volatility, volume, fundamentals, comparative, strategy, percentiles

**Example**:
```python
ground_truth = {
    'uncertainty_score': 65,
    'atr_pct': 2.3,
    'volume_ratio': 1.8,
    'rsi': 58
}
```

### Layer 2: Semantic State Classification
- **File**: `src/report/context_builder.py`
- **Purpose**: Convert numbers → semantic states (e.g., 65 → "ค่อนข้างสูง")
- **Components**: `SemanticStateGenerator`, `MarketAnalyzer`, `TechnicalAnalyzer`

**Example**:
```python
semantic_states = {
    'market_phase': 'การปรับตัวหลังขาขึ้น',
    'risk_state': 'ความเสี่ยงปานกลาง-สูง',
    'trend_state': 'แนวโน้มขาขึ้นแต่อ่อนแรง'
}
```

### Layer 3: LLM Narrative Synthesis
- **File**: `src/report/prompt_builder.py`
- **Purpose**: Assemble complete prompt from semantic context
- **Pattern**: Dynamic placeholder filtering (only include available data)

**Example**:
```
<data>
ราคา: {{CURRENT_PRICE}} บาท ({{PRICE_CHANGE_PCT}}%)
ความเสี่ยง: {{UNCERTAINTY}}/100 แสดงถึงความเสี่ยง{{UNCERTAINTY_LEVEL}}
RSI: {{RSI}} บอกว่าหุ้น{{RSI_STATE}}
</data>
```

---

## Workflow: User Intent → Report Output

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User Intent (MISSING - Proposed Phase 1)                    │
│    - Detect intent type: daily_report | trend_analysis | ...   │
│    - Route to appropriate template                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Data Fetching (✅ COMPLETE)                                  │
│    - Aurora: src/data/aurora/aurora_client.py                   │
│    - Cached nightly (46 tickers)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Context Assembly (✅ COMPLETE)                               │
│    - ContextBuilder.prepare_context()                           │
│    - Semantic state generation (Layer 2)                        │
│    - Dynamic placeholder filtering                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Prompt Assembly (✅ COMPLETE)                                │
│    - PromptBuilder.build_prompt()                               │
│    - Template selection (currently hardcoded to v4_minimal)     │
│    - Placeholder list injection                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. LLM Execution (✅ COMPLETE)                                  │
│    - OpenRouter (GPT-4o)                                        │
│    - Langfuse tracing (@observe decorator)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Response Validation (MISSING - Proposed Phase 2)            │
│    - Check all {{PLACEHOLDERS}} replaced                        │
│    - Verify factual accuracy (numbers match ground truth)       │
│    - Validate structure (required sections present)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Post-Processing (✅ COMPLETE)                                │
│    - NumberInjector.inject_deterministic_numbers()              │
│    - News reference injection                                   │
│    - Transparency footer                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Existing Infrastructure (80% Complete)

### ✅ Component 1: Prompt Assembly
**File**: `src/report/prompt_builder.py` (540 lines)

**Key Methods**:
- `build_prompt()` - Main assembly method
- `_has_value()` - Check data availability
- `_build_placeholder_list()` - Dynamic filtering

**What it does**:
1. Loads template from `src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt`
2. Filters placeholders based on available data (e.g., only include `{{STRATEGY_*}}` if backtest data exists)
3. Injects semantic context from Layer 2
4. Returns complete prompt ready for LLM

**Code Location**: `src/report/prompt_builder.py:89-187`

---

### ✅ Component 2: Context Assembly
**File**: `src/report/context_builder.py` (563 lines)

**Key Method**: `prepare_context()`

**What it does**:
1. Converts numeric indicators → semantic states
2. Assembles multi-domain context (price, news, comparative, strategy)
3. Handles optional data gracefully (MCP sources, portfolio insights)

**Example Output**:
```python
{
    'market_phase': 'การปรับตัวหลังขาขึ้น',
    'risk_state': 'ความเสี่ยงปานกลาง-สูง',
    'trend_narrative': 'แนวโน้มขาขึ้นแต่อ่อนแรง',
    'volume_state': 'ปริมาณซื้อขายเพิ่มขึ้น',
    'news_sentiment': 'ข่าวเชิงบวกเกี่ยวกับกำไรเพิ่มขึ้น',
    'comparative_position': 'แข็งแกร่งกว่ากลุ่ม',
    'strategy_signal': 'Bullish Reversal (ความมั่นใจสูง)'
}
```

**Code Location**: `src/report/context_builder.py:52-194`

---

### ✅ Component 3: Number Injection
**File**: `src/report/number_injector.py` (200+ lines)

**Key Method**: `inject_deterministic_numbers()`

**What it does**:
1. Defines 60+ placeholder calculations (single source of truth)
2. Replaces `{{PLACEHOLDERS}}` with exact values post-LLM generation
3. Prevents hallucination (LLM never sees actual numbers)

**Placeholder Categories**:
- **Risk**: `{{UNCERTAINTY}}`, `{{ATR_PCT}}`, `{{VOLATILITY_LEVEL}}`
- **Momentum**: `{{RSI}}`, `{{RSI_STATE}}`, `{{MOMENTUM}}`
- **Trend**: `{{TREND_DIRECTION}}`, `{{TREND_STRENGTH}}`, `{{MA20_DISTANCE}}`
- **Volume**: `{{VOLUME_RATIO}}`, `{{VOLUME_STATE}}`
- **Fundamentals**: `{{CURRENT_PRICE}}`, `{{PRICE_CHANGE_PCT}}`, `{{PE_RATIO}}`
- **Comparative**: `{{PEER_RANK}}`, `{{VS_GROUP_PCT}}`
- **Strategy**: `{{WIN_RATE}}`, `{{AVG_PROFIT}}`, `{{SHARPE_RATIO}}`
- **Percentiles**: `{{P_CURRENT_PRICE}}`, `{{P_VOLUME}}`, `{{P_RSI}}`

**Code Location**: `src/report/number_injector.py:20-200`

---

### ✅ Component 4: LLM Integration
**File**: `src/report/report_generator_simple.py` (311 lines)

**Key Method**: `generate_report()`

**What it does**:
1. Coordinates entire workflow (context → prompt → LLM → post-process)
2. Uses OpenRouter for LLM calls (GPT-4o)
3. Decorated with `@observe` for Langfuse tracing

**Flow**:
```python
raw_data → context_builder.prepare_context()
         → prompt_builder.build_prompt()
         → llm.invoke(prompt)
         → number_injector.inject_deterministic_numbers()
         → add news references + transparency footer
```

**Code Location**: `src/report/report_generator_simple.py:58-282`

---

### ✅ Component 5: Observability (Langfuse)
**File**: `src/integrations/langfuse_client.py` (113 lines)

**Key Functions**:
- `get_langfuse_client()` - Singleton client
- `observe()` - Tracing decorator
- `flush()` - Ensure traces sent before Lambda shutdown

**What it traces**:
- Full prompt text (with all variables injected)
- LLM response (raw output)
- Token counts (input/output for cost estimation)
- Latency (execution time)

**Usage**:
```python
from src.evaluation import observe

@observe(name="generate_report")
def generate_report(ticker, raw_data):
    # Automatic tracing of entire function
    ...
```

**Configuration** (Doppler secrets in `dev_local`):
- `LANGFUSE_PUBLIC_KEY`: pk-lf-ba2ed2a6-3d2e-4673-a356-547d5a5b70c8
- `LANGFUSE_SECRET_KEY`: sk-lf-ecd07e27-f565-4242-9e27-96bb2336b608
- `LANGFUSE_HOST`: https://us.cloud.langfuse.com

**Code Location**: `src/integrations/langfuse_client.py:23-98`

---

### ✅ Component 6: Prompt Templates
**File**: `src/report/prompt_templates/th/single-stage/main_prompt_v4_minimal.txt`

**Structure**:
```xml
<system>
คุณเป็นนักวิเคราะห์หุ้นไทย...

กฎสำคัญ:
1. แทนที่ตัวเลขทั้งหมดด้วย {{PLACEHOLDERS}}
2. ใช้ภาษาเรียบง่าย ไม่เป็นทางการเกินไป
3. มุ่งเน้นความเข้าใจมากกว่าความยาว
</system>

<examples>
<!-- 3 few-shot examples with placeholders -->
</examples>

<task>
เขียนรายงานวิเคราะห์หุ้น {ticker} โดยใช้โครงสร้าง:
📖 เรื่องราวของหุ้นตัวนี้
💡 สิ่งที่คุณต้องรู้
🎯 ควรทำอะไรตอนนี้?
⚠️ ระวังอะไร?
</task>

<placeholders>
{placeholder_list}  <!-- Dynamically injected -->
</placeholders>

<data>
{context}  <!-- Semantic states from Layer 2 -->
</data>
```

**Key Feature**: Few-shot examples teach LLM to use placeholders consistently

---

## Missing Components (20% - Orchestration Layer)

### ❌ Component 1: Intent Detection (Proposed Phase 1)
**Status**: Not implemented
**Purpose**: Route user requests to appropriate templates/workflows

**Example Intent Types**:
- `daily_report` → Use `main_prompt_v4_minimal.txt`
- `trend_analysis` → Use `trend_focus_prompt.txt`
- `risk_assessment` → Use `risk_analysis_prompt.txt`
- `comparative_analysis` → Use `peer_comparison_prompt.txt`

**Proposed Implementation**:
```python
# File: src/prompt_os/intent_detector.py
class IntentDetector:
    def detect(self, user_request: str, context: dict) -> Intent:
        """Classify user intent from request string."""
        # Use keyword matching or simple LLM call
        if "trend" in user_request.lower():
            return Intent.TREND_ANALYSIS
        elif "risk" in user_request.lower():
            return Intent.RISK_ASSESSMENT
        else:
            return Intent.DAILY_REPORT
```

**Estimated Size**: ~50 lines

---

### ❌ Component 2: Template Router (Proposed Phase 1)
**Status**: Currently hardcoded to `main_prompt_v4_minimal.txt`
**Purpose**: Select template based on intent + user preferences

**Proposed Implementation**:
```python
# File: src/prompt_os/template_router.py
class TemplateRouter:
    def route(self, intent: Intent, user_prefs: dict) -> Template:
        """Select appropriate template based on intent and preferences."""
        template_map = {
            Intent.DAILY_REPORT: 'main_prompt_v4_minimal.txt',
            Intent.TREND_ANALYSIS: 'trend_focus_prompt.txt',
            Intent.RISK_ASSESSMENT: 'risk_analysis_prompt.txt'
        }

        template_path = template_map[intent]
        version = user_prefs.get('prompt_version', 'v4')

        return Template.load(template_path, version)
```

**Estimated Size**: ~50 lines

---

### ❌ Component 3: Prompt Versioning (Proposed Phase 2)
**Status**: Not implemented (templates not version-controlled)
**Purpose**: A/B test prompts, track performance, rollback if needed

**Proposed Structure**:
```
src/report/prompt_templates/th/single-stage/
├── main_prompt_v3_verbose.txt      (archived)
├── main_prompt_v4_minimal.txt      (current default)
├── main_prompt_v5_experimental.txt (testing)
└── metadata/
    ├── v3_metadata.json  # Performance metrics
    ├── v4_metadata.json
    └── v5_metadata.json
```

**Metadata Example**:
```json
{
    "version": "v4",
    "created": "2025-12-15",
    "author": "prompt_engineer",
    "status": "production",
    "performance": {
        "avg_quality_score": 8.2,
        "avg_generation_time_ms": 3500,
        "hallucination_rate": 0.02
    }
}
```

**Estimated Size**: ~100 lines (versioning logic + metadata management)

---

### ❌ Component 4: Response Validation (Proposed Phase 2)
**Status**: Not implemented
**Purpose**: Verify LLM output before post-processing

**Validation Checks**:
1. **Placeholder Check**: All numbers replaced with `{{PLACEHOLDERS}}`?
2. **Factual Accuracy**: When placeholders injected, do numbers match ground truth?
3. **Structure Check**: Required sections present (📖, 💡, 🎯, ⚠️)?
4. **Length Check**: Within acceptable range (not too short/long)?
5. **Hallucination Check**: No unsupported claims?

**Proposed Implementation**:
```python
# File: src/prompt_os/response_validator.py
class ResponseValidator:
    def validate(self, report: str, ground_truth: dict) -> ValidationResult:
        """Validate LLM response before post-processing."""
        issues = []

        # Check 1: Placeholders used?
        if re.search(r'\b\d+\.?\d*\b', report):  # Raw number found
            issues.append("Raw numbers found (should use placeholders)")

        # Check 2: Structure present?
        required_sections = ['📖', '💡', '🎯', '⚠️']
        missing = [s for s in required_sections if s not in report]
        if missing:
            issues.append(f"Missing sections: {missing}")

        # Check 3: Length reasonable?
        line_count = len(report.split('\n'))
        if line_count < 10:
            issues.append("Report too short")
        elif line_count > 25:
            issues.append("Report too long")

        return ValidationResult(valid=len(issues) == 0, issues=issues)
```

**Estimated Size**: ~100 lines

---

### ❌ Component 5: User Preferences (Proposed Phase 3)
**Status**: Not implemented
**Purpose**: Customize reports per user (tone, detail level, language)

**Preference Schema**:
```python
{
    'user_id': 'user123',
    'language': 'th',  # Thai
    'tone': 'casual',  # casual | formal | technical
    'detail_level': 'minimal',  # minimal | moderate | detailed
    'prompt_version': 'v4',
    'include_strategy': True,
    'include_news': True,
    'preferred_sections': ['📖', '💡', '🎯', '⚠️']
}
```

**Proposed Implementation**:
```python
# File: src/prompt_os/user_preferences.py
class UserPreferenceManager:
    def get_preferences(self, user_id: str) -> UserPreferences:
        """Load user preferences from database."""
        prefs = self.db.query(f"SELECT * FROM user_prefs WHERE user_id = '{user_id}'")
        return UserPreferences(**prefs) if prefs else UserPreferences.default()

    def apply_to_context(self, context: dict, prefs: UserPreferences) -> dict:
        """Modify context based on user preferences."""
        if not prefs.include_strategy:
            context.pop('strategy_signal', None)

        if prefs.detail_level == 'minimal':
            context['max_lines'] = 15
        elif prefs.detail_level == 'detailed':
            context['max_lines'] = 30

        return context
```

**Estimated Size**: ~150 lines (CRUD + application logic)

---

## Proposed Implementation Strategy (3 Phases)

### Phase 1: Intent Detection + Template Routing (~100 lines)
**Timeline**: Week 1
**Goal**: Dynamic template selection based on user intent

**Files to Create**:
- `src/prompt_os/intent_detector.py` (50 lines)
- `src/prompt_os/template_router.py` (50 lines)

**Integration Point**: Modify `report_generator_simple.py:115` to call router instead of hardcoding template

**Test Strategy**:
- Unit tests for intent classification (10 example requests)
- Integration test: Generate reports with different intents

---

### Phase 2: Versioning + Validation (~200 lines)
**Timeline**: Week 2
**Goal**: Track prompt performance, validate responses

**Files to Create**:
- `src/prompt_os/template_versioner.py` (100 lines)
- `src/prompt_os/response_validator.py` (100 lines)
- `src/report/prompt_templates/metadata/` (directory + JSON files)

**Integration Point**: Add validation step in `report_generator_simple.py:189` before post-processing

**Test Strategy**:
- Validation tests with deliberately broken responses
- Versioning tests with metadata CRUD operations

---

### Phase 3: User Preferences (~150 lines)
**Timeline**: Week 3
**Goal**: Personalize reports per user

**Files to Create**:
- `src/prompt_os/user_preferences.py` (150 lines)
- Database migration for `user_preferences` table

**Integration Point**: Load preferences in `report_generator_simple.py:94` and apply to context

**Test Strategy**:
- Preference CRUD operations
- Report generation with different preference combinations

---

## Key Design Patterns

### Pattern 1: Dynamic Placeholder Filtering
**Problem**: LLM hallucinates when asked to use placeholders for unavailable data

**Solution**: Only inject placeholders for available data sources

**Implementation**: `src/report/prompt_builder.py:215-281`

**Example**:
```python
# If no strategy backtest data:
available_placeholders = [
    '{{CURRENT_PRICE}}',
    '{{RSI}}',
    '{{UNCERTAINTY}}'
]
# Excludes: {{WIN_RATE}}, {{SHARPE_RATIO}}, etc.

# If strategy data exists:
available_placeholders = [
    '{{CURRENT_PRICE}}',
    '{{RSI}}',
    '{{UNCERTAINTY}}',
    '{{WIN_RATE}}',      # Now included
    '{{SHARPE_RATIO}}'   # Now included
]
```

---

### Pattern 2: Graceful Degradation
**Problem**: External data sources (MCP, portfolio insights) may be unavailable

**Solution**: All optional data wrapped in `if has_value()` checks

**Implementation**: `src/report/context_builder.py:96-194`

**Example**:
```python
# Optional MCP data
if mcp_data and self._has_value(mcp_data.get('chart_patterns')):
    context['chart_patterns'] = self._format_chart_patterns(mcp_data)
else:
    # Continue without chart patterns (don't fail)
    pass

# Optional portfolio insights
if portfolio_insights and self._has_value(portfolio_insights.get('holdings')):
    context['portfolio_context'] = self._format_portfolio(portfolio_insights)
```

---

### Pattern 3: Placeholder-Based Number Injection
**Problem**: LLMs hallucinate numbers (e.g., RSI = 45 when actual is 62)

**Solution**: LLM generates text with `{{PLACEHOLDERS}}`, code replaces post-generation

**Implementation**: `src/report/number_injector.py:20-200`

**Example**:
```
LLM Output:
"RSI อยู่ที่ {{RSI}} บอกว่าหุ้น{{RSI_STATE}}"

After Injection:
"RSI อยู่ที่ 62 บอกว่าหุ้นเข้าสู่โซนขายมากเกินไป"
```

**Benefits**:
- 100% factual accuracy (numbers from ground truth)
- LLM focuses on narrative structure (not calculations)
- Easy to update numbers without regenerating entire report

---

## File Structure

```
src/
├── report/
│   ├── prompt_builder.py           # ✅ Prompt assembly (540 lines)
│   ├── context_builder.py          # ✅ Semantic state generation (563 lines)
│   ├── number_injector.py          # ✅ Placeholder definitions (200+ lines)
│   ├── report_generator_simple.py  # ✅ Main workflow (311 lines)
│   ├── transparency_footer.py      # ✅ Data usage footnote
│   └── prompt_templates/
│       └── th/single-stage/
│           ├── main_prompt_v4_minimal.txt      # ✅ Current production template
│           ├── main_prompt_v3_verbose.txt      # ✅ Archived version
│           └── metadata/                        # ❌ Not created yet
│               ├── v3_metadata.json
│               └── v4_metadata.json
│
├── prompt_os/                       # ❌ Not created yet (proposed Phase 1-3)
│   ├── __init__.py
│   ├── intent_detector.py          # Phase 1: Intent classification
│   ├── template_router.py          # Phase 1: Template selection
│   ├── template_versioner.py       # Phase 2: Version management
│   ├── response_validator.py       # Phase 2: Output validation
│   └── user_preferences.py         # Phase 3: Personalization
│
├── integrations/
│   └── langfuse_client.py          # ✅ Observability (113 lines)
│
├── analysis/
│   ├── market_analyzer.py          # ✅ Market conditions
│   └── technical_analysis.py       # ✅ Technical indicators
│
├── formatters/
│   └── data_formatter.py           # ✅ Number formatting
│
└── evaluation/
    └── __init__.py                 # ✅ Re-exports observe() from langfuse_client
```

---

## Technology Stack

### LLM Provider
- **OpenRouter** (https://openrouter.ai/api/v1)
- **Model**: GPT-4o (`openai/gpt-4o`)
- **Temperature**: 0.8 (creative but controlled)

### Observability
- **Langfuse** (https://us.cloud.langfuse.com)
- **SDK**: `langfuse>=2.0.0` (currently 3.3.4 installed)
- **Pattern**: `@observe` decorator for automatic tracing

### Prompt Templates
- **Format**: Plain text with XML-like tags (`<system>`, `<examples>`, `<task>`)
- **Language**: Thai (th)
- **Few-shot**: 3 examples per template

### Data Sources
- **Primary**: Aurora MySQL (cached nightly)
- **Optional**: MCP servers, portfolio insights, SEC filings

---

## Configuration (Doppler)

### Project Structure
- **Project**: `rag-chatbot-worktree`
- **Config**: `dev_local` (for local development)
- **Inherits from**: `dev` (shared development secrets)

### Required Secrets
```bash
# LLM Provider
OPENROUTER_API_KEY=sk-or-v1-...

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com

# Database
AURORA_HOST=...
AURORA_DB_NAME=...
AURORA_USER=...
AURORA_PASSWORD=...

# Timezone
TZ=Asia/Bangkok
```

---

## Observability Dashboard

### Langfuse Traces
**URL**: https://us.cloud.langfuse.com

**What you can see**:
1. **Full prompt text** (with all variables injected)
2. **LLM response** (raw output before post-processing)
3. **Token counts** (input/output for cost estimation)
4. **Latency** (execution time)
5. **Trace hierarchy** (nested function calls)

**Filter by**:
- Trace name (e.g., `generate_report`, `generate_singlestage`)
- Time range
- User ID (if configured)
- Tags/metadata

**Use cases**:
- **Prompt experimentation**: Compare multiple prompt versions side-by-side
- **Quality debugging**: Identify which prompts produce best/worst outputs
- **Cost tracking**: Monitor token usage trends
- **Performance monitoring**: Track generation latency over time

---

## Performance Characteristics

### Current Metrics (from validation testing):

**Report Generation**:
- **Total time**: ~4-6 seconds (cold start), ~2-3 seconds (warm)
- **LLM latency**: ~2-3 seconds (GPT-4o)
- **Post-processing**: ~500ms (number injection + footer)
- **Token usage**: ~2000-3000 input, ~800-1200 output

**Context Assembly**:
- **Time**: <100ms (pure computation, no API calls)
- **Memory**: Minimal (small dictionaries)

**Placeholder Injection**:
- **Time**: <50ms (60+ regex replacements)
- **Accuracy**: 100% (deterministic calculations)

---

## Cost Analysis

### Per Report (Estimated)

**LLM Costs** (OpenRouter pricing for GPT-4o):
- Input: 2500 tokens × $5/1M = $0.0125
- Output: 1000 tokens × $15/1M = $0.015
- **Total per report**: ~$0.03

**Infrastructure Costs**:
- Aurora queries: Negligible (cached data)
- Lambda execution: <$0.001 per invocation
- Langfuse tracing: Free tier (up to 50k traces/month)

**Monthly Cost (1000 reports/day)**:
- LLM: 1000 × $0.03 × 30 = $900
- Infrastructure: ~$30
- **Total**: ~$930/month

---

## Key Insights

### What Makes This "PromptOS"?

1. **Separation of Concerns**: Numeric calculations (Layer 1) separate from semantic interpretation (Layer 2) separate from narrative generation (Layer 3)

2. **Dynamic Adaptation**: Prompt adjusts based on available data (placeholder filtering prevents hallucination)

3. **Observability-First**: Every LLM call traced automatically for prompt experimentation

4. **Placeholder Pattern**: LLM never sees actual numbers, focuses on narrative structure

5. **Graceful Degradation**: Missing optional data doesn't break workflow

6. **Template Modularity**: Easy to add new templates for different report types

### What's Missing?

1. **Orchestration Layer**: No intent detection or template routing (currently hardcoded)

2. **Version Management**: Templates not version-controlled with performance tracking

3. **Validation**: No automated checks for LLM output quality

4. **Personalization**: No user-specific customization

5. **A/B Testing**: No infrastructure for comparing prompt variants

---

## Next Steps for Implementation

### Phase 1: Basic Orchestration (Week 1)
**Goal**: Dynamic template selection based on user intent

**Tasks**:
1. Create `IntentDetector` (keyword-based classification)
2. Create `TemplateRouter` (map intent → template)
3. Modify `report_generator_simple.py` to use router
4. Write unit tests for intent detection
5. Test with 3 intent types: daily_report, trend_analysis, risk_assessment

**Expected Outcome**: Users can request different report types

---

### Phase 2: Quality Assurance (Week 2)
**Goal**: Track prompt versions and validate outputs

**Tasks**:
1. Create `TemplateVersioner` (metadata management)
2. Create `ResponseValidator` (output checks)
3. Add validation step to generation workflow
4. Create metadata files for existing templates (v3, v4)
5. Write validation tests with deliberately broken outputs

**Expected Outcome**: Each prompt version tracked with performance metrics, bad outputs caught before delivery

---

### Phase 3: Personalization (Week 3)
**Goal**: Customize reports per user

**Tasks**:
1. Design `user_preferences` database schema
2. Create migration for new table
3. Create `UserPreferenceManager` (CRUD operations)
4. Integrate preferences into context assembly
5. Test with 3 preference profiles: minimal, moderate, detailed

**Expected Outcome**: Each user gets reports tailored to their preferences

---

## FAQ

### Q: Why use placeholders instead of giving LLM actual numbers?
**A**: LLMs hallucinate numbers frequently. Placeholder pattern guarantees 100% factual accuracy while letting LLM focus on narrative structure.

### Q: Why three layers (Layer 1, 2, 3)?
**A**: Separation of concerns. Layer 1 = ground truth (never changes), Layer 2 = interpretation (semantic states), Layer 3 = narrative (creative synthesis). Each layer has single responsibility.

### Q: Why is prompt template hardcoded to `v4_minimal`?
**A**: Historical reasons. Originally only one template. Template router (Phase 1) will make this dynamic.

### Q: Can I add a new metric (e.g., Bollinger Bands)?
**A**: Yes. Add to Layer 1 (`number_injector.py` placeholders), Layer 2 (`context_builder.py` semantic state), update prompt template to use new placeholder.

### Q: How do I experiment with different prompts?
**A**:
1. Copy `main_prompt_v4_minimal.txt` → `main_prompt_v5_experiment.txt`
2. Edit new file
3. Change `template_name` in code (currently hardcoded line 115)
4. Generate reports
5. Compare traces in Langfuse dashboard

### Q: What if LLM output is garbage?
**A**: Currently no automated validation. Response validator (Phase 2) will catch bad outputs. Manual workaround: Check Langfuse traces, identify issue, update prompt, regenerate.

### Q: How do I add support for English reports?
**A**:
1. Create `src/report/prompt_templates/en/single-stage/main_prompt_v1_en.txt`
2. Update `PromptBuilder.__init__()` to accept `language` parameter
3. Use parameter to select language folder
4. Add English semantic states to `context_builder.py`

---

## References

### Documentation
- **Onboarding Guide**: `docs/ONBOARDING_PROMPT_ENGINEER.md` (Phase 1-10 checklist)
- **CLAUDE.md**: `.claude/CLAUDE.md` (Core principles, especially Principle #18 Logging Discipline)

### Code Files
- **Prompt Assembly**: `src/report/prompt_builder.py:89-187`
- **Context Assembly**: `src/report/context_builder.py:52-194`
- **Number Injection**: `src/report/number_injector.py:20-200`
- **Report Generation**: `src/report/report_generator_simple.py:58-282`
- **Observability**: `src/integrations/langfuse_client.py:23-98`

### Validation Reports
- **Langfuse Setup**: `.claude/validations/2026-01-04-langfuse-keys-copied-to-dev-local.md`
- **Langfuse Testing**: `.claude/validations/2026-01-04-langfuse-configured-for-prompt-experimentation.md`

---

## Conclusion

**PromptOS** is 80% implemented. The core infrastructure (3-layer architecture, placeholder pattern, observability) is production-ready. Missing components are orchestration/coordination layers (intent detection, template routing, validation, preferences).

**Current state**: Single template, hardcoded workflow, no version tracking
**Desired state**: Multi-template system with intent-based routing, version management, quality validation, and user personalization

**Incremental path**: 3 phases (Intent + Routing → Versioning + Validation → Preferences) adding ~450 lines total over 3 weeks.

**Key strength**: Existing infrastructure is solid. Missing pieces are thin coordination layers, not fundamental architecture changes.
