# -*- coding: utf-8 -*-
"""
Hallucination Scorer using LLM-as-Judge

Cross-validates faithfulness scorer using LLM to detect hallucinations.
Provides semantic validation that complements rule-based checking.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


@dataclass
class HallucinationScore:
    """Container for hallucination scoring results"""
    overall_score: float  # 0-100 (100 = no hallucinations)
    confidence: float  # 0-100 (LLM's confidence in assessment)
    hallucinations: List[str]  # Detected hallucinations
    validated_claims: List[str]  # Verified accurate claims
    llm_reasoning: str  # LLM's explanation


class HallucinationScorer:
    """
    LLM-as-judge hallucination detector

    Uses ChatGPT to validate that ALL claims in the narrative are supported
    by the ground truth context. Provides semantic validation that catches
    subtle hallucinations that rule-based checks might miss.

    Cross-validates FaithfulnessScorer results.
    """

    SYSTEM_PROMPT = """คุณเป็นผู้ตรวจสอบความถูกต้องของรายงานการวิเคราะห์หุ้น

งานของคุณคือตรวจสอบว่ารายงานที่สร้างโดย AI มีข้อมูลที่ไม่ถูกต้องหรือไม่สอดคล้องกับข้อมูลต้นฉบับหรือไม่ (hallucination)

หลักการตรวจสอบ:
1. ตัวเลขทุกตัวต้องตรงกับข้อมูลต้นฉบับ (ราคา, เปอร์เซ็นต์, อัตราส่วน)
2. วันที่และช่วงเวลาต้องถูกต้อง
3. ข่าวสารที่อ้างอิงต้องมีอยู่จริงในข้อมูล
4. การตีความเชิงคุณภาพต้องสอดคล้องกับตัวเลขเชิงปริมาณ
5. บริษัท, ภาคธุรกิจ, และข้อมูลพื้นฐานต้องถูกต้อง

ให้คะแนน:
- 100 = ไม่มีข้อมูลผิดพลาดเลย ทุกข้อความสอดคล้องกับข้อมูลต้นฉบับ
- 80-99 = มีความไม่แม่นยำเล็กน้อยที่ไม่สำคัญ
- 60-79 = มีข้อมูลผิดพลาดบางส่วน
- 40-59 = มีข้อมูลผิดพลาดหลายจุด
- 0-39 = มีข้อมูลผิดพลาดร้ายแรง

ตอบกลับในรูปแบบ JSON:
{
    "score": 0-100,
    "confidence": 0-100,
    "hallucinations": ["รายการข้อมูลที่ผิดพลาด"],
    "validated_claims": ["รายการข้อมูลที่ถูกต้อง"],
    "reasoning": "คำอธิบายการให้คะแนน"
}"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        Initialize hallucination scorer

        Args:
            model: OpenAI model to use (default: gpt-4o-mini for cost efficiency)
            temperature: LLM temperature (0.0 for deterministic)
        """
        self.model = model
        self.temperature = temperature

        # Initialize LLM
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, hallucination scoring will fail")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )

    def score_narrative(
        self,
        narrative: str,
        ground_truth_context: Dict,
        ticker: str = None
    ) -> HallucinationScore:
        """
        Score narrative for hallucinations using LLM-as-judge

        Args:
            narrative: Generated Thai narrative text
            ground_truth_context: Complete context data including:
                - indicators: Technical indicators
                - percentiles: Percentile data
                - news: News items
                - ticker_data: Company data
                - market_conditions: Market metrics
            ticker: Optional ticker symbol for context

        Returns:
            HallucinationScore object with LLM assessment
        """
        try:
            # Format ground truth context as readable JSON
            context_json = json.dumps(
                ground_truth_context,
                ensure_ascii=False,
                indent=2
            )

            # Build evaluation prompt
            user_prompt = f"""กรุณาตรวจสอบรายงานนี้เทียบกับข้อมูลต้นฉบับ

**รายงานที่ต้องตรวจสอบ:**
{narrative}

**ข้อมูลต้นฉบับ (Ground Truth):**
```json
{context_json}
```

{f"**หุ้น:** {ticker}" if ticker else ""}

กรุณาตรวจสอบว่ารายงานมีข้อความที่ไม่ถูกต้องหรือไม่สอดคล้องกับข้อมูลต้นฉบับหรือไม่ ให้ความสำคัญกับ:
1. ตัวเลขต่างๆ (ราคา, RSI, MACD, ATR, volume ratio, etc.)
2. เปอร์เซ็นไทล์และการตีความ
3. ข่าวสารที่อ้างอิง
4. ข้อมูลบริษัท (ชื่อ, ภาคธุรกิจ)

ตอบในรูปแบบ JSON เท่านั้น"""

            # Call LLM
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm.invoke(messages)
            response_text = response.content.strip()

            # Parse JSON response
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            result = json.loads(response_text)

            # Extract fields
            score = float(result.get("score", 0))
            confidence = float(result.get("confidence", 50))
            hallucinations = result.get("hallucinations", [])
            validated_claims = result.get("validated_claims", [])
            reasoning = result.get("reasoning", "")

            # Log results
            logger.info(f"Hallucination score: {score}/100 (confidence: {confidence}%)")
            if hallucinations:
                logger.warning(f"Detected {len(hallucinations)} hallucinations")
                for h in hallucinations[:3]:  # Log first 3
                    logger.warning(f"  - {h}")

            return HallucinationScore(
                overall_score=score,
                confidence=confidence,
                hallucinations=hallucinations,
                validated_claims=validated_claims,
                llm_reasoning=reasoning
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response_text[:500]}")

            # Return conservative score
            return HallucinationScore(
                overall_score=50.0,
                confidence=0.0,
                hallucinations=["JSON parsing error - unable to validate"],
                validated_claims=[],
                llm_reasoning=f"Error: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Hallucination scoring failed: {e}")

            # Return conservative score
            return HallucinationScore(
                overall_score=50.0,
                confidence=0.0,
                hallucinations=[f"Scoring error: {str(e)}"],
                validated_claims=[],
                llm_reasoning=f"Error: {str(e)}"
            )

    def validate_against_faithfulness(
        self,
        llm_score: HallucinationScore,
        rule_based_score: float
    ) -> Dict[str, any]:
        """
        Compare LLM-as-judge results with rule-based faithfulness score

        Args:
            llm_score: HallucinationScore from LLM
            rule_based_score: Score from FaithfulnessScorer (0-100)

        Returns:
            Dict with agreement analysis
        """
        # Calculate agreement
        score_diff = abs(llm_score.overall_score - rule_based_score)

        if score_diff <= 10:
            agreement = "strong"
            confidence = "high"
        elif score_diff <= 20:
            agreement = "moderate"
            confidence = "medium"
        else:
            agreement = "weak"
            confidence = "low"

        return {
            "agreement": agreement,
            "confidence": confidence,
            "score_difference": score_diff,
            "llm_score": llm_score.overall_score,
            "rule_based_score": rule_based_score,
            "recommendation": (
                "Both scorers agree - high confidence" if agreement == "strong"
                else "Scores diverge - manual review recommended" if agreement == "weak"
                else "Moderate agreement - acceptable"
            )
        }
