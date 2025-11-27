#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consistency Scorer

Evaluates logical consistency between narrative interpretations and quantitative data.
Uses LLM-as-judge to detect inconsistencies that rule-based checks might miss.

Focus areas:
- Logical consistency: Do interpretations match quantitative data?
- Internal consistency: Are there contradictions within the narrative?
- Semantic consistency: Do qualitative terms align with quantitative thresholds?
- Temporal consistency: Are time-based claims supported by data?

Note: Does NOT validate numeric accuracy (FaithfulnessScorer handles that).
      Ignores minor rounding differences (within 2%).
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyResult:
    """Result from consistency scoring"""
    overall_score: float  # 0-100
    confidence: float  # 0-100, LLM's confidence in assessment

    dimension_scores: Dict[str, float] = field(default_factory=dict)
    inconsistencies: List[str] = field(default_factory=list)
    validated_alignments: List[str] = field(default_factory=list)
    reasoning: str = ""


class ConsistencyScorer:
    """
    LLM-based consistency scorer for narrative-data alignment.

    Evaluates whether interpretations logically match the underlying data,
    without re-checking numeric accuracy (FaithfulnessScorer's job).

    Cross-validates interpretation logic from narrative against quantitative evidence.
    """

    SYSTEM_PROMPT = """คุณเป็นผู้ตรวจสอบความสอดคล้องเชิงตรรกะของรายงานการวิเคราะห์หุ้น

งานของคุณคือตรวจสอบว่าการตีความเชิงคุณภาพ (qualitative interpretations) ในรายงานสอดคล้องกับข้อมูลเชิงปริมาณ (quantitative data) หรือไม่

**สิ่งที่ต้องตรวจสอบ:**

1. **Logical Consistency (40%)**: การตีความตรงกับข้อมูล?
   - "แนวโน้มขาขึ้น" แต่ SMA_20 < SMA_50 < SMA_200 → ไม่สอดคล้อง
   - "โมเมนตัมแข็งแกร่ง" แต่ RSI = 25 (oversold) → ไม่สอดคล้อง
   - "ความผันผวนสูง" แต่ ATR = 0.5% → ไม่สอดคล้อง
   - "ปริมาณการซื้อขายแรง" แต่ volume ratio = 0.3x → ไม่สอดคล้อง

2. **Internal Consistency (30%)**: ไม่มีข้อความที่ขัดแย้งกันภายในรายงาน?
   - "แนะนำซื้อแรง... แต่ควรหลีกเลี่ยงเนื่องจากความเสี่ยงสูง" → ขัดแย้ง
   - "ราคากำลังปรับตัวขึ้น... ราคาร่วงลง" → ขัดแย้ง
   - คำแนะนำหลายทิศทาง (ซื้อ, ขาย, รอ พร้อมกัน) → ขัดแย้ง

3. **Semantic Consistency (20%)**: คำศัพท์เชิงคุณภาพตรงกับเกณฑ์เชิงปริมาณ?
   - Uncertainty: stable (0-25), moderate (25-50), high (50-75), extreme (75-100)
   - VWAP: strong_buy (≥15%), buy (≥5%), neutral (-5 to 5%), sell (≤-5%), strong_sell (≤-15%)
   - ATR: low (<2%), moderate (2-3.5%), high (>3.5%)
   - Volume: low (<0.8x), normal (0.8-1.2x), high (>1.2x)
   - RSI: oversold (<30), neutral (30-70), overbought (>70)

4. **Temporal Consistency (10%)**: ข้อความเกี่ยวกับเวลามีข้อมูลรองรับ?
   - "ราคาร่วงมา 3 เดือน" แต่มีแค่ข้อมูลวันเดียว → ไม่รองรับ
   - "ปริมาณเพิ่มขึ้นจากเมื่อวาน" แต่ไม่มีข้อมูลเปรียบเทียบ → ไม่รองรับ

**สิ่งที่ไม่ต้องตรวจสอบ (FaithfulnessScorer ทำแล้ว):**
- ตัวเลขถูกต้องหรือไม่ (เช่น RSI = 45 vs 47)
- ความแตกต่างจากการปัดเศษ (เช่น 1.28% vs 1.2814%)
- การอ้างอิงข่าวถูกต้องหรือไม่
- ข้อมูลบริษัทถูกต้องหรือไม่

**หลักการให้คะแนน:**
- 90-100 = ไม่มีความไม่สอดคล้องเลย การตีความทั้งหมดตรงกับข้อมูล
- 75-89 = มีความไม่สอดคล้องเล็กน้อย 1-2 จุด
- 60-74 = มีความไม่สอดคล้องปานกลาง 3-4 จุด
- 40-59 = มีความไม่สอดคล้องหลายจุด 5+ จุด
- 0-39 = การตีความขัดแย้งกับข้อมูลร้ายแรง

**ตอบกลับในรูปแบบ JSON:**
{
    "score": 0-100,
    "confidence": 0-100,
    "inconsistencies": ["รายการความไม่สอดคล้อง"],
    "validated_alignments": ["รายการการตีความที่ถูกต้อง"],
    "reasoning": "คำอธิบายการให้คะแนน"
}"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        Initialize consistency scorer

        Args:
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
            temperature: LLM temperature (default: 0.0 for deterministic output)
        """
        # Ensure model has openai/ prefix for OpenRouter
        model_name = f"openai/{model}" if not model.startswith("openai/") else model
        # Support both OPENROUTER_API_KEY and OPENAI_API_KEY env vars
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = model
        logger.info(f"ConsistencyScorer initialized with model={model_name}, temperature={temperature}")

    def score_narrative(
        self,
        narrative: str,
        indicators: Dict[str, Any],
        percentiles: Dict[str, Any],
        market_conditions: Dict[str, Any],
        ticker_data: Optional[Dict[str, Any]] = None
    ) -> ConsistencyResult:
        """
        Score narrative for logical consistency.

        Args:
            narrative: Generated Thai narrative text
            indicators: Technical indicators (RSI, MACD, SMA, etc.)
            percentiles: Percentile data for historical context
            market_conditions: Market metrics (uncertainty_score, atr_pct, volume_ratio, etc.)
            ticker_data: Optional company data for context

        Returns:
            ConsistencyResult with overall score and dimension breakdowns
        """
        try:
            # Build context for LLM
            context = {
                "indicators": indicators,
                "percentiles": percentiles,
                "market_conditions": market_conditions
            }
            if ticker_data:
                context["ticker_data"] = ticker_data

            context_json = json.dumps(context, indent=2, ensure_ascii=False)

            # Build prompt
            user_prompt = f"""**รายงานที่ต้องตรวจสอบ:**
{narrative}

**ข้อมูลเชิงปริมาณ (Ground Truth Data):**
```json
{context_json}
```

กรุณาตรวจสอบว่าการตีความในรายงาน (interpretations) สอดคล้องกับข้อมูลเชิงปริมาณหรือไม่
โดยเน้นที่:
1. การตีความเชิงคุณภาพตรงกับตัวเลขหรือไม่
2. ไม่มีข้อความขัดแย้งกันภายในรายงาน
3. คำศัพท์เชิงคุณภาพตรงกับเกณฑ์ที่กำหนด
4. ข้อความเกี่ยวกับเวลามีข้อมูลรองรับ

**หมายเหตุ:** อย่าตรวจสอบความถูกต้องของตัวเลข (ปัดเศษ ±2% ยอมรับได้) แต่ให้ตรวจสอบว่า**การตีความ**ตรงกับตัวเลขหรือไม่

ตอบในรูปแบบ JSON เท่านั้น"""

            # Call LLM
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)

            # Parse JSON response
            response_text = response.content.strip()

            # Extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(response_text)

            # Extract dimension scores (LLM provides overall, we calculate dimensions)
            overall_score = result_dict.get("score", 0)
            confidence = result_dict.get("confidence", 0)
            inconsistencies = result_dict.get("inconsistencies", [])
            validated_alignments = result_dict.get("validated_alignments", [])
            reasoning = result_dict.get("reasoning", "")

            # Calculate dimension scores based on inconsistency count
            # (simplified heuristic - can be enhanced)
            inconsistency_count = len(inconsistencies)

            dimension_scores = {
                "logical_consistency": max(0, 100 - inconsistency_count * 10),
                "internal_consistency": 100 if inconsistency_count == 0 else max(0, 100 - inconsistency_count * 15),
                "semantic_consistency": max(0, 100 - inconsistency_count * 12),
                "temporal_consistency": 100 if inconsistency_count == 0 else max(0, 100 - inconsistency_count * 8)
            }

            return ConsistencyResult(
                overall_score=overall_score,
                confidence=confidence,
                dimension_scores=dimension_scores,
                inconsistencies=inconsistencies,
                validated_alignments=validated_alignments,
                reasoning=reasoning
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return ConsistencyResult(
                overall_score=50.0,  # Conservative middle score on error
                confidence=0.0,
                dimension_scores={},
                inconsistencies=["Failed to parse LLM response"],
                reasoning=f"JSON parsing error: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Consistency scoring error: {e}")
            return ConsistencyResult(
                overall_score=50.0,  # Conservative middle score on error
                confidence=0.0,
                dimension_scores={},
                inconsistencies=["Scoring error occurred"],
                reasoning=f"Error: {str(e)}"
            )


if __name__ == "__main__":
    # Simple test
    scorer = ConsistencyScorer()

    test_narrative = """📖 Story: หุ้น DBS Group แสดงแนวโน้มขาขึ้นแรงด้วย RSI ที่ 25 และโมเมนตัมเชิงบวก

💡 Insights: ความผันผวนต่ำมาก ATR 0.5% แต่ควรระวังความเสี่ยงสูงมาก"""

    test_indicators = {
        "rsi": 25,
        "current_price": 53.74,
        "sma_20": 53.5,
        "sma_50": 52.2,
        "sma_200": 46.0
    }

    test_market_conditions = {
        "uncertainty_score": 55,
        "atr_pct": 0.5,
        "volume_ratio": 0.3,
        "price_vs_vwap_pct": 5.2
    }

    result = scorer.score_narrative(
        narrative=test_narrative,
        indicators=test_indicators,
        percentiles={},
        market_conditions=test_market_conditions
    )

    print(f"\n=== Consistency Test ===")
    print(f"Score: {result.overall_score}/100")
    print(f"Confidence: {result.confidence}/100")
    print(f"\nInconsistencies found: {len(result.inconsistencies)}")
    for inc in result.inconsistencies:
        print(f"  - {inc}")
    print(f"\nValidated alignments: {len(result.validated_alignments)}")
    for val in result.validated_alignments:
        print(f"  - {val}")
    print(f"\nReasoning: {result.reasoning}")
