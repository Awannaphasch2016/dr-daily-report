# Implied Rules/Policy/Constraints for Ticker Reports

## Summary of Compliance Rules Derived from Codebase Analysis

Based on analysis of `agent.py` prompts and existing scorers, here are the **implied rules/policy/constraints** that ticker reports must follow:

---

## 1. STRUCTURAL FORMAT REQUIREMENTS

### Section Structure (CRITICAL)
Reports **MUST** have exactly 4 sections with specific emojis:

1. **📖 เรื่องราวของหุ้นตัวนี้** (Story Section)
   - **Length**: 2-3 sentences
   - **Required Content**: MUST include uncertainty score context + ATR% + VWAP% + volume ratio with their meanings
   - **Optional**: Include news naturally if relevant

2. **💡 สิ่งที่คุณต้องรู้** (Insights Section)
   - **Length**: 3-4 flowing paragraphs
   - **Format**: NOT numbered lists, NO tables
   - **Required Content**: MUST continuously reference the 4 market condition elements (uncertainty, ATR, VWAP, volume) with numbers throughout
   - **Style**: Mix technical + fundamental + relative + news seamlessly

3. **🎯 ควรทำอะไรตอนนี้?** (Recommendation Section)
   - **Length**: 2-3 sentences
   - **Required**: ONE clear action: BUY MORE / SELL / HOLD
   - **Required**: Explain WHY using uncertainty score + market conditions (ATR/VWAP/volume)
   - **Optional**: Reference news if it changes the decision

4. **⚠️ ระวังอะไร?** (Risk Section)
   - **Length**: 1-2 key risks
   - **Required**: Warn about risks using the 4 market condition metrics
   - **Focus**: What volatility/pressure/volume signals should trigger concern

### Overall Length Constraint
- **Total**: Under 12-15 lines total

---

## 2. CONTENT REQUIREMENTS

### Mandatory Content Elements (CRITICAL)

1. **All 4 Market Condition Metrics** (MUST appear throughout narrative)
   - Uncertainty score (with context)
   - ATR% (with percentile context)
   - VWAP% (with percentile context)
   - Volume ratio (with percentile context)

2. **Percentile Context** (CRITICAL when data available)
   - MUST use percentile data when available
   - Format: "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%"
   - Must be woven naturally into narrative, not just listed

3. **Specific Numbers** (MUST include)
   - All numbers must include specific values
   - Must include percentile context for numbers
   - Numbers should be IN sentences as evidence, not standalone facts

4. **News References** (When applicable)
   - Reference news [1], [2] ONLY when it genuinely affects the story
   - Don't force it if not relevant
   - Format: [1], [2], [3] citations

### Strategy Performance Rules (When Data Provided)

1. **Alignment Requirement**: ONLY include strategy performance when it ALIGNS with BUY/SELL recommendation
2. **Format Requirement**: Must follow specific format:
   - "หากคุณติดตามกลยุทธ์ของเรา, การซื้อ/ขายครั้งล่าสุดอยู่ที่ [price] และเมื่อดูจากสถิติการซื้อ/ขายเท่านั้น (buy-only/sell-only strategy) ในอดีต..."
3. **Prohibited**: NEVER mention strategy name (SMA crossing) - just say "กลยุทธ์ของเรา" or "strategies"
4. **Purpose**: Use to strengthen argument, not as standalone facts

---

## 3. STYLE REQUIREMENTS

### Narrative Style (CRITICAL)
- **Format**: Tell STORIES, don't list bullet points
- **Tone**: Write like texting a friend investor
- **Style**: Narrative supported by numbers, not numbers with explanation
- **Language**: Write entirely in Thai
- **Flow**: Mix technical + fundamental + relative + news + statistical context seamlessly - don't section them

### Explanation Requirements
- **Focus**: Explain WHY things matter (implication), not just WHAT they are (description)
- **Integration**: Use numbers IN sentences as evidence, not as standalone facts

---

## 4. PROHIBITED ELEMENTS

### Format Prohibitions
- ❌ **NO tables** in any section
- ❌ **NO numbered lists** in the insight section (💡)
- ❌ **NO bullet points** (use flowing narrative instead)

### Content Prohibitions
- ❌ **NO strategy name mention** (e.g., "SMA crossing") - only generic references
- ❌ **NO forced news references** - only when genuinely relevant
- ❌ **NO standalone numbers** - must be in sentences with context

---

## 5. LANGUAGE REQUIREMENTS

- **Language**: Write entirely in Thai
- **Style**: Naturally flowing like Damodaran's style
- **Tone**: Professional but conversational (like texting a friend investor)

---

## 6. QUALITY STANDARDS

### Required Elements Checklist
- [ ] All 4 sections present (📖, 💡, 🎯, ⚠️)
- [ ] All 4 market condition metrics included (uncertainty, ATR%, VWAP%, volume ratio)
- [ ] All metrics include percentile context when available
- [ ] Recommendation is ONE clear action (BUY/SELL/HOLD)
- [ ] Recommendation includes WHY explanation
- [ ] Risk section warns about 1-2 key risks
- [ ] Total length under 12-15 lines
- [ ] Written entirely in Thai
- [ ] Narrative style (not lists/tables)
- [ ] News references follow format [1], [2] when relevant
- [ ] Strategy performance only included if aligned with recommendation

---

## Proposed Compliance Score Dimensions

Based on these rules, I propose **Compliance Score** should check:

1. **Structure Compliance** (30%): All 4 sections present with correct format
2. **Content Compliance** (25%): All required content elements present
3. **Format Compliance** (15%): No prohibited elements (tables, lists, etc.)
4. **Length Compliance** (10%): Meets length requirements
5. **Language Compliance** (10%): Written in Thai, proper style
6. **Citation Compliance** (10%): News citations follow format [1], [2]

---

## Questions for Validation

1. **Structure**: Should we penalize if sections are present but in wrong order?
2. **Length**: Is "12-15 lines" strict or flexible? Should we check word count instead?
3. **Content**: Should we verify that ALL 4 metrics appear in each required section, or just somewhere in the report?
4. **Strategy**: Should compliance check that strategy format matches exactly, or just that it's present when data exists?
5. **News**: Should we check that news citations are valid (not [5] when only 3 news items exist)?
6. **Language**: Should we detect if report is NOT in Thai, or assume it always is?

Please confirm if this understanding is correct before I implement the Compliance Scorer!
