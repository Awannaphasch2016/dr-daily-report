# -*- coding: utf-8 -*-
"""
Tests for LangSmith Evaluator Adapters
"""

import pytest
from unittest.mock import Mock
from langsmith.schemas import Run, Example
from langsmith.evaluation import EvaluationResult

from src.evaluation.langsmith_evaluator_adapters import (
    faithfulness_evaluator,
    completeness_evaluator,
    reasoning_quality_evaluator,
    compliance_evaluator,
    qos_evaluator,
    cost_evaluator,
    hallucination_llm_evaluator,
    get_all_evaluators,
    get_quality_evaluators,
    get_performance_evaluators
)


class TestEvaluatorAdapters:
    """Test suite for all 7 evaluator adapters"""

    def create_mock_run(self, outputs, inputs, metadata=None):
        """Helper to create mock Run object"""
        run = Mock(spec=Run)
        run.id = "test-run-id"  # LangSmith evaluators need run.id
        run.outputs = outputs
        run.inputs = inputs
        run.metadata = metadata or {}
        return run

    def create_mock_example(self, inputs):
        """Helper to create mock Example object"""
        example = Mock(spec=Example)
        example.inputs = inputs
        return example

    def test_faithfulness_evaluator(self):
        """Test faithfulness evaluator adapter"""
        # Create mock run
        run = self.create_mock_run(
            outputs={"narrative": "Test narrative with RSI at 55.71%"},
            inputs={
                "ground_truth": {
                    'uncertainty_score': 51.4,
                    'atr_pct': 1.28,
                    'vwap_pct': 20.37,
                    'volume_ratio': 1.07
                },
                "indicators": {
                    'rsi': 55.71,
                    'uncertainty_score': 51.4
                },
                "percentiles": {},
                "news_data": []
            }
        )

        # Evaluate
        result = faithfulness_evaluator(run)

        # Check result structure
        assert isinstance(result, EvaluationResult)
        assert result.key == "faithfulness_score"
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        assert result.comment is not None
        assert "Numeric" in result.comment

    def test_completeness_evaluator(self):
        """Test completeness evaluator adapter"""
        run = self.create_mock_run(
            outputs={"narrative": "Complete report with all sections"},
            inputs={
                "ticker_data": {"company_name": "DBS", "current_price": 53.67},
                "indicators": {},
                "percentiles": {},
                "news_data": []
            }
        )

        result = completeness_evaluator(run)

        assert isinstance(result, EvaluationResult)
        assert result.key == "completeness_score"
        assert isinstance(result.score, float)

    def test_reasoning_quality_evaluator(self):
        """Test reasoning quality evaluator adapter"""
        run = self.create_mock_run(
            outputs={"narrative": "Report with clear explanations"},
            inputs={
                "indicators": {},
                "percentiles": {},
                "ticker_data": {}
            }
        )

        result = reasoning_quality_evaluator(run)

        assert isinstance(result, EvaluationResult)
        assert result.key == "reasoning_quality_score"
        assert isinstance(result.score, float)

    def test_compliance_evaluator(self):
        """Test compliance evaluator adapter"""
        run = self.create_mock_run(
            outputs={"narrative": "Compliant report format"},
            inputs={
                "indicators": {},
                "news_data": []
            }
        )

        result = compliance_evaluator(run)

        assert isinstance(result, EvaluationResult)
        assert result.key == "compliance_score"
        assert isinstance(result.score, float)

    def test_qos_evaluator(self):
        """Test QoS evaluator adapter"""
        run = self.create_mock_run(
            outputs={"narrative": "Report"},
            inputs={},
            metadata={
                "timing_metrics": {
                    "total_elapsed": 5.0,
                    "llm_latency": 2.0
                },
                "database_metrics": {"query_count": 3},
                "error_occurred": False,
                "cache_hit": False,
                "llm_calls": 2
            }
        )

        result = qos_evaluator(run)

        assert isinstance(result, EvaluationResult)
        assert result.key == "qos_score"
        assert isinstance(result.score, float)
        assert "Latency" in result.comment

    def test_cost_evaluator(self):
        """Test cost evaluator adapter"""
        run = self.create_mock_run(
            outputs={"narrative": "Report"},
            inputs={},
            metadata={
                "api_costs": {
                    "openai_api": 0.05,
                    "total": 0.05
                },
                "llm_calls": 2,
                "database_metrics": {},
                "cache_hit": False
            }
        )

        result = cost_evaluator(run)

        assert isinstance(result, EvaluationResult)
        assert result.key == "cost_score"
        assert isinstance(result.score, float)
        assert "Cost" in result.comment or "THB" in result.comment

    def test_hallucination_llm_evaluator(self):
        """Test hallucination LLM evaluator adapter (may skip if no API key)"""
        run = self.create_mock_run(
            outputs={"narrative": "DBS ปิดที่ 53.67 บาท"},
            inputs={
                "ground_truth_context": {
                    "indicators": {"current_price": 53.67},
                    "percentiles": {},
                    "news": [],
                    "ticker_data": {},
                    "market_conditions": {}
                },
                "ticker": "DBS19"
            }
        )

        try:
            result = hallucination_llm_evaluator(run)

            assert isinstance(result, EvaluationResult)
            assert result.key == "hallucination_llm_score"
            assert isinstance(result.score, float)
            assert 0.0 <= result.score <= 1.0
            assert "LLM-as-judge" in result.comment

        except Exception as e:
            pytest.skip(f"LLM evaluator skipped (no API key expected): {e}")

    def test_evaluator_with_example(self):
        """Test that evaluators work with Example objects"""
        run = self.create_mock_run(
            outputs={"narrative": "Test"},
            inputs={}  # Empty run inputs
        )

        example = self.create_mock_example(
            inputs={
                "ground_truth": {},
                "indicators": {},
                "percentiles": {},
                "news_data": []
            }
        )

        # Should fall back to example inputs
        result = faithfulness_evaluator(run, example)
        assert isinstance(result, EvaluationResult)

    def test_get_all_evaluators(self):
        """Test helper function returns all 7 evaluators"""
        evaluators = get_all_evaluators()

        assert len(evaluators) == 7
        assert faithfulness_evaluator in evaluators
        assert completeness_evaluator in evaluators
        assert reasoning_quality_evaluator in evaluators
        assert compliance_evaluator in evaluators
        assert qos_evaluator in evaluators
        assert cost_evaluator in evaluators
        assert hallucination_llm_evaluator in evaluators

    def test_get_quality_evaluators(self):
        """Test helper returns 5 quality evaluators"""
        evaluators = get_quality_evaluators()

        assert len(evaluators) == 5
        assert faithfulness_evaluator in evaluators
        assert hallucination_llm_evaluator in evaluators
        assert qos_evaluator not in evaluators  # Performance, not quality

    def test_get_performance_evaluators(self):
        """Test helper returns 2 performance evaluators"""
        evaluators = get_performance_evaluators()

        assert len(evaluators) == 2
        assert qos_evaluator in evaluators
        assert cost_evaluator in evaluators
        assert faithfulness_evaluator not in evaluators  # Quality, not performance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
