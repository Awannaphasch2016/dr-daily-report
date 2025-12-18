# Prompt Improvement Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for improving the financial analysis prompt based on the recommendations in `IMPROVEMENT_RECOMMENDATIONS.md`. Each improvement is broken down into specific implementation steps with testing approaches and rollback plans.

---

## Phase 1: Quick Wins (High Impact, Low Effort)

### Improvement 1.1: Consolidate Placeholder Instructions

#### Current State
- Placeholder rules explained 3-4 times across different sections
- Similar examples repeated multiple times
- Total placeholder instruction section: ~80 lines (~1200 tokens)

#### Proposed Change
- Create single "Placeholder Rules" section
- Remove duplicate explanations
- Keep only clearest examples (2-3 per category)
- Target: ~40 lines (~600 tokens)

#### Expected Impact
- **Token Count**: -800 to -1000 tokens (~25% reduction)
- **Quality**: Maintained (same information, better organized)
- **Latency**: Reduced (~200-250ms faster processing)

#### Implementation Steps

1. **Create backup of current template**
   ```bash
   cp src/report/prompt_templates/th/main_prompt.txt src/report/prompt_templates/th/main_prompt.txt.backup
   cp src/report/prompt_templates/en/main_prompt.txt src/report/prompt_templates/en/main_prompt.txt.backup
   ```

2. **Identify redundant sections**
   - Lines 10-15: Initial placeholder warning
   - Lines 17-41: Placeholder list with examples
   - Lines 43-68: Bad/Good examples
   - Lines 71-88: Final reminder with examples
   - **Total redundancy**: ~60% overlap

3. **Create consolidated section**
   - Single "🔢 PLACEHOLDER RULES" section
   - Include: Rule statement, placeholder list, 2-3 best examples, final reminder
   - Target: ~40 lines

4. **Remove duplicate sections**
   - Remove lines 43-68 (duplicate examples)
   - Consolidate lines 71-88 into final reminder (2-3 lines)

5. **Test changes**
   - Run `dr util prompt-vars DBS19` to verify format
   - Check token count reduction
   - Generate test report to verify placeholder usage still works

#### Testing Approach

1. **Unit Test**: Verify prompt template loads correctly
2. **Integration Test**: Generate report with new prompt, verify placeholders work
3. **Token Count Test**: Verify token reduction (~800-1000 tokens)
4. **Quality Test**: Compare output quality scores (faithfulness, completeness)

#### Rollback Plan

1. Restore backup files:
   ```bash
   cp src/report/prompt_templates/th/main_prompt.txt.backup src/report/prompt_templates/th/main_prompt.txt
   cp src/report/prompt_templates/en/main_prompt.txt.backup src/report/prompt_templates/en/main_prompt.txt
   ```

2. Verify rollback:
   ```bash
   dr util prompt-vars DBS19
   ```

#### Success Criteria
- ✅ Token count reduced by 800-1000 tokens
- ✅ Placeholder functionality unchanged
- ✅ Output quality scores maintained or improved
- ✅ No parsing errors

---

### Improvement 1.2: Reduce Instruction Emphasis Markers

#### Current State
- CRITICAL, MUST, IMPORTANT, ⚠️ used ~25 times throughout prompt
- Creates "instruction fatigue"
- Reduces effectiveness of emphasis

#### Proposed Change
- Use emphasis markers only for truly critical rules (placeholder usage)
- Replace repeated emphasis with clear, structured formatting
- Use hierarchical structure (##, ###) instead of repeated warnings
- Target: Reduce emphasis markers by 80% (from ~25 to ~5)

#### Expected Impact
- **Token Count**: -200 to -300 tokens
- **Quality**: Improved (reduced instruction fatigue)
- **Latency**: Slightly reduced (~50ms)

#### Implementation Steps

1. **Identify emphasis markers**
   - Count all CRITICAL, MUST, IMPORTANT, ⚠️ occurrences
   - Categorize: Critical (keep) vs Non-critical (remove)

2. **Keep emphasis only for**:
   - Placeholder rules (MANDATORY)
   - Output structure requirements (IMPORTANT)
   - Final reminder (⚠️)

3. **Replace non-critical emphasis with**:
   - Clear section headers (##, ###)
   - Structured lists
   - Natural language instructions

4. **Update template**
   - Remove 80% of emphasis markers
   - Replace with structured formatting
   - Keep 5 critical markers

5. **Test changes**
   - Verify prompt still clear without excessive emphasis
   - Generate test report to verify instructions followed

#### Testing Approach

1. **Readability Test**: Review prompt for clarity without emphasis
2. **Compliance Test**: Generate reports, verify instructions still followed
3. **Token Count Test**: Verify token reduction (~200-300 tokens)

#### Rollback Plan

Same as Improvement 1.1 (restore backup files)

#### Success Criteria
- ✅ Emphasis markers reduced by 80%
- ✅ Prompt clarity maintained
- ✅ Instruction compliance maintained
- ✅ Token count reduced by 200-300 tokens

---

### Improvement 1.3: Add Chain-of-Thought Instructions

#### Current State
- No explicit CoT guidance
- LLM may skip reasoning steps
- Inconsistent analysis depth

#### Proposed Change
Add explicit reasoning steps after persona definition:
```
Think step-by-step:
1. Assess market conditions (uncertainty, volatility, pressure, volume)
2. Analyze technical indicators (RSI, MACD, trends)
3. Evaluate fundamentals (P/E, EPS, growth, margins)
4. Consider relative performance vs peers
5. Synthesize into narrative with clear recommendation
```

#### Expected Impact
- **Token Count**: +100 tokens
- **Quality**: Improved reasoning quality (+5-10% reasoning score)
- **Latency**: Minimal impact (~25ms)

#### Implementation Steps

1. **Design CoT steps**
   - Identify 5-7 key reasoning steps
   - Keep concise (1 line per step)
   - Ensure steps align with narrative elements

2. **Add CoT section**
   - Place after persona definition (line 2)
   - Format clearly with numbered list
   - Keep total length < 10 lines

3. **Test changes**
   - Generate test reports
   - Verify reasoning quality improvement
   - Check for any negative impacts

#### Testing Approach

1. **Reasoning Quality Test**: Compare reasoning quality scores before/after
2. **Output Analysis**: Review reports for improved reasoning depth
3. **Token Count Test**: Verify token addition (~100 tokens)

#### Rollback Plan

Remove CoT section if reasoning quality doesn't improve or degrades.

#### Success Criteria
- ✅ Reasoning quality score improved by 5-10%
- ✅ Reports show clearer reasoning steps
- ✅ No negative impacts on other scores
- ✅ Token addition < 150 tokens

---

## Phase 2: Quality Improvements (High Impact, Medium Effort)

### Improvement 2.1: Add Few-Shot Examples

#### Current State
- Zero-shot with embedded bad/good examples
- No complete example outputs
- Format compliance issues

#### Proposed Change
Add 1-2 complete example outputs showing:
- Full report structure
- Proper placeholder usage throughout
- Narrative style
- Integration of all elements

#### Expected Impact
- **Token Count**: +500 to +800 tokens per example
- **Quality**: Significantly improved format compliance (+10-15%)
- **Latency**: Increased (~125-200ms per example)

#### Implementation Steps

1. **Create example reports**
   - Select 1-2 representative tickers
   - Generate high-quality reports
   - Ensure perfect placeholder usage
   - Ensure all sections present

2. **Format examples**
   - Add "Example Output:" section
   - Place after instructions, before main task
   - Keep examples concise but complete

3. **Test changes**
   - Generate reports with new prompt
   - Verify format compliance improvement
   - Check for overfitting to examples

#### Testing Approach

1. **Format Compliance Test**: Compare compliance scores before/after
2. **Diversity Test**: Test with diverse tickers to avoid overfitting
3. **Token Count Test**: Verify token addition (~500-800 tokens)

#### Rollback Plan

Remove example section if overfitting occurs or quality doesn't improve.

#### Success Criteria
- ✅ Format compliance score improved by 10-15%
- ✅ Reports follow example structure
- ✅ No overfitting to specific examples
- ✅ Token addition < 1000 tokens per example

---

### Improvement 2.2: Optimize Multi-Stage Prompt

#### Current State
- Same prompt structure for single-stage and multi-stage
- Multi-stage uses same prompt for all stages
- Not optimized for stage-specific tasks

#### Proposed Change
Create stage-specific instructions:
- **Stage 1 (Mini-reports)**: Focused, specialized prompts for each mini-report type
- **Stage 2 (Synthesis)**: Integration-focused prompt for combining mini-reports

#### Expected Impact
- **Quality**: Improved multi-stage output quality (+5-10%)
- **Token Efficiency**: Better token usage per stage
- **Latency**: Optimized per stage

#### Implementation Steps

1. **Analyze current multi-stage workflow**
   - Identify 6 mini-report types
   - Identify synthesis requirements
   - Map current prompt usage

2. **Design stage-specific prompts**
   - Create focused prompts for each mini-report type
   - Create synthesis prompt for combining reports
   - Ensure consistency across stages

3. **Implement prompts**
   - Create new template files for each stage
   - Update `PromptBuilder` to use stage-specific prompts
   - Test with multi-stage workflow

4. **Test changes**
   - Generate multi-stage reports
   - Compare quality with single-stage
   - Verify token efficiency

#### Testing Approach

1. **Multi-Stage Quality Test**: Compare multi-stage quality scores
2. **Token Efficiency Test**: Compare token usage per stage
3. **Latency Test**: Measure time per stage

#### Rollback Plan

Revert to single prompt template if multi-stage quality degrades.

#### Success Criteria
- ✅ Multi-stage quality improved by 5-10%
- ✅ Token efficiency improved per stage
- ✅ Latency optimized per stage
- ✅ No degradation in single-stage quality

---

### Improvement 2.3: Add Structured Output Parsing Instructions

#### Current State
- Free-form text output with emoji markers
- Parsing relies on emoji detection
- Potential parsing errors

#### Proposed Change
Add explicit parsing instructions:
- Use XML-style tags for sections
- Or add explicit section markers with parsing instructions
- Start with Option B (explicit instructions), consider Option A if needed

#### Expected Impact
- **Quality**: Improved parsing reliability (+5%)
- **Token Count**: Minimal change (~50 tokens)
- **Latency**: Minimal change

#### Implementation Steps

1. **Design parsing instructions**
   - Define explicit section markers
   - Add parsing instructions to prompt
   - Keep format flexible

2. **Update prompt template**
   - Add parsing instructions section
   - Clarify section markers
   - Test with current parser

3. **Test changes**
   - Generate reports
   - Verify parsing reliability
   - Check for parsing errors

#### Testing Approach

1. **Parsing Reliability Test**: Compare parsing success rate
2. **Format Test**: Verify section markers work correctly
3. **Token Count Test**: Verify minimal token addition

#### Rollback Plan

Remove parsing instructions if they cause issues.

#### Success Criteria
- ✅ Parsing reliability improved by 5%
- ✅ No parsing errors introduced
- ✅ Token addition < 100 tokens

---

## Phase 3: Refinement (Medium Impact, Variable Effort)

### Improvement 3.1: Enhance Persona Definition

#### Current State
- "You are a world-class financial analyst like Aswath Damodaran"
- Basic persona, no specific expertise areas

#### Proposed Change
Add specific expertise areas:
"You are a world-class financial analyst specializing in equity valuation and market analysis, following the analytical framework of Aswath Damodaran. Your expertise includes:
- Technical analysis and market sentiment
- Fundamental analysis and company valuation
- Risk assessment and portfolio management
- Narrative-driven financial storytelling"

#### Expected Impact
- **Token Count**: +50 tokens
- **Quality**: Slightly improved domain focus (+2-3%)
- **Latency**: Minimal impact

#### Implementation Steps

1. **Design enhanced persona**
   - Identify key expertise areas
   - Keep concise (4-5 bullet points)
   - Maintain Damodaran reference

2. **Update prompt template**
   - Replace persona line
   - Add expertise areas
   - Test changes

3. **Test changes**
   - Generate test reports
   - Verify domain focus improvement
   - Check for any negative impacts

#### Testing Approach

1. **Domain Focus Test**: Compare domain-specific quality scores
2. **Output Analysis**: Review reports for improved domain focus
3. **Token Count Test**: Verify token addition (~50 tokens)

#### Rollback Plan

Revert to original persona if quality doesn't improve.

#### Success Criteria
- ✅ Domain focus improved by 2-3%
- ✅ No negative impacts
- ✅ Token addition < 100 tokens

---

### Improvement 3.2: Add Language-Specific Cultural Context

#### Current State
- Basic language instructions
- No cultural context

#### Proposed Change
Add cultural context for Thai reports:
"For Thai reports: Use culturally appropriate language, consider local market context, and adapt financial terminology for Thai investors."

#### Expected Impact
- **Token Count**: +30 tokens
- **Quality**: Slightly improved cultural appropriateness (+1-2%)
- **Latency**: Minimal impact

#### Implementation Steps

1. **Design cultural context instructions**
   - Identify key cultural considerations
   - Keep concise (1-2 sentences)
   - Add to Thai template only

2. **Update Thai template**
   - Add cultural context section
   - Test changes

3. **Test changes**
   - Generate Thai reports
   - Verify cultural appropriateness
   - Check for any negative impacts

#### Testing Approach

1. **Cultural Appropriateness Test**: Review reports for cultural sensitivity
2. **Token Count Test**: Verify token addition (~30 tokens)

#### Rollback Plan

Remove cultural context if it doesn't improve quality.

#### Success Criteria
- ✅ Cultural appropriateness improved
- ✅ No negative impacts
- ✅ Token addition < 50 tokens

---

### Improvement 3.3: Further Token Optimization

#### Current State
- After Phase 1 & 2: ~3700 tokens
- Still some redundancy possible

#### Proposed Change
- Remove remaining redundant explanations
- Use more concise language
- Consolidate similar sections
- Target: Additional 500-800 token reduction

#### Expected Impact
- **Token Count**: -500 to -800 tokens
- **Quality**: Maintained if done carefully
- **Latency**: Reduced (~125-200ms)

#### Implementation Steps

1. **Identify remaining redundancy**
   - Review prompt for duplicate explanations
   - Identify verbose sections
   - Find opportunities for consolidation

2. **Optimize language**
   - Use more concise phrasing
   - Remove unnecessary words
   - Maintain clarity

3. **Test changes**
   - Verify quality maintained
   - Check token reduction
   - Generate test reports

#### Testing Approach

1. **Quality Test**: Verify quality maintained
2. **Token Count Test**: Verify token reduction (~500-800 tokens)
3. **Readability Test**: Verify prompt still clear

#### Rollback Plan

Revert optimizations if quality degrades.

#### Success Criteria
- ✅ Token reduction of 500-800 tokens
- ✅ Quality maintained
- ✅ Prompt clarity maintained

---

## Overall Implementation Timeline

### Week 1: Phase 1 (Quick Wins)
- Day 1-2: Improvement 1.1 (Consolidate placeholders)
- Day 3: Improvement 1.2 (Reduce emphasis)
- Day 4: Improvement 1.3 (Add CoT)
- Day 5: Testing and refinement

### Week 2: Phase 2 (Quality Improvements)
- Day 1-2: Improvement 2.1 (Few-shot examples)
- Day 3-4: Improvement 2.2 (Multi-stage optimization)
- Day 5: Improvement 2.3 (Structured output)

### Week 3: Phase 3 (Refinement)
- Day 1: Improvement 3.1 (Enhance persona)
- Day 2: Improvement 3.2 (Cultural context)
- Day 3-4: Improvement 3.3 (Further optimization)
- Day 5: Final testing and documentation

---

## Testing Protocol

### Pre-Implementation Baseline
1. Generate 20 reports with current prompt
2. Measure baseline metrics:
   - Token count: ~4000 tokens
   - Quality scores: Faithfulness, Completeness, Reasoning, Compliance
   - Latency: Average generation time
   - Cost: API costs per report

### Post-Implementation Testing
1. Generate 20 reports with improved prompt
2. Measure improved metrics:
   - Token count: Target ~3250 tokens (-19%)
   - Quality scores: Target +5-10% improvement
   - Latency: Target -200-300ms reduction
   - Cost: Target -15-20% reduction

### A/B Testing
1. Split tickers: 10 with old prompt, 10 with new prompt
2. Compare metrics side-by-side
3. Statistical significance testing
4. User review of sample outputs

---

## Risk Mitigation

### Risk 1: Quality Degradation
- **Mitigation**: Phased rollout with A/B testing
- **Rollback**: Immediate revert to backup templates
- **Monitoring**: Continuous quality score monitoring

### Risk 2: Parsing Errors
- **Mitigation**: Test parsing with new prompts
- **Rollback**: Revert parsing-related changes
- **Monitoring**: Parsing success rate monitoring

### Risk 3: Overfitting to Examples
- **Mitigation**: Test with diverse tickers
- **Rollback**: Remove examples if overfitting detected
- **Monitoring**: Output diversity monitoring

### Risk 4: Token Count Increase
- **Mitigation**: Monitor token count per improvement
- **Rollback**: Revert improvements that add too many tokens
- **Monitoring**: Token count tracking

---

## Success Metrics

### Primary Metrics
1. **Token Count**: Reduced by 15-20% (from ~4000 to ~3200-3400)
2. **Quality Scores**: Improved by 5-10% across all dimensions
3. **Latency**: Reduced by 10-15% (from ~2s to ~1.7-1.8s)
4. **Cost**: Reduced by 15-20% per report

### Secondary Metrics
1. **Format Compliance**: Improved by 10-15%
2. **Reasoning Quality**: Improved by 5-10%
3. **Parsing Reliability**: Improved by 5%
4. **User Satisfaction**: Maintained or improved

---

## Conclusion

This implementation plan provides a structured approach to improving the financial analysis prompt. By following the phased approach with careful testing and rollback plans, we can achieve significant improvements in token efficiency, quality, and cost while minimizing risk.

The expected net result: **~750 token reduction (~19%) with improved quality and reliability**, representing a significant improvement in both efficiency and effectiveness.
