# -*- coding: utf-8 -*-
"""
Unit Tests for LangSmith Integration

Tests individual components of the LangSmith integration:
- Evaluator wrappers (6 metrics)
- Client initialization
- Score logging
- Data format conversion
"""

import os
import pytest
from unittest.mock import Mock, patch
import warnings
warnings.filterwarnings('ignore')

from src.evaluation.langsmith_evaluators import LangSmithEvaluators
from src.evaluation.langsmith_integration import get_langsmith_client, log_evaluation_to_langsmith


class TestLangSmithEvaluators:
    """Test evaluator wrappers for all 6 metrics"""

    def test_faithfulness_evaluator(self):
        """Test faithfulness evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 85.0,
            'numeric_accuracy': 90.0,
            'percentile_accuracy': 85.0,
            'news_citation_accuracy': 80.0,
            'interpretation_accuracy': 87.0,
            'violations': []
        }

        result = LangSmithEvaluators.faithfulness_evaluator(score_data)

        assert result['key'] == 'faithfulness_score'
        assert abs(result['score'] - 0.85) < 0.01
        assert 'Numeric: 90.0%' in result['comment']
        assert 'Percentile: 85.0%' in result['comment']

    def test_completeness_evaluator(self):
        """Test completeness evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 78.0,
            'context_completeness': 85.0,
            'analysis_dimensions': 75.0,
            'temporal_completeness': 80.0,
            'actionability': 75.0,
            'narrative_structure': 80.0,
            'quantitative_context': 75.0,
            'missing_elements': ['fundamental']
        }

        result = LangSmithEvaluators.completeness_evaluator(score_data)

        assert result['key'] == 'completeness_score'
        assert abs(result['score'] - 0.78) < 0.01
        assert 'Context: 85.0%' in result['comment']
        assert 'Missing: 1' in result['comment']

    def test_reasoning_quality_evaluator(self):
        """Test reasoning quality evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 82.0,
            'clarity': 85.0,
            'coverage': 80.0,
            'specificity': 85.0,
            'alignment': 80.0,
            'minimality': 75.0,
            'consistency': 85.0,
            'issues': [],
            'strengths': ['clear', 'specific']
        }

        result = LangSmithEvaluators.reasoning_quality_evaluator(score_data)

        assert result['key'] == 'reasoning_quality_score'
        assert abs(result['score'] - 0.82) < 0.01
        assert 'Clarity: 85.0%' in result['comment']

    def test_compliance_evaluator(self):
        """Test compliance evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 91.0,
            'structure_compliance': 95.0,
            'content_compliance': 90.0,
            'format_compliance': 90.0,
            'length_compliance': 85.0,
            'language_compliance': 95.0,
            'citation_compliance': 90.0,
            'violations': []
        }

        result = LangSmithEvaluators.compliance_evaluator(score_data)

        assert result['key'] == 'compliance_score'
        assert abs(result['score'] - 0.91) < 0.01
        assert 'Structure: 95.0%' in result['comment']

    def test_qos_evaluator(self):
        """Test QoS evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 74.0,
            'latency_score': 70.0,
            'determinism_score': 85.0,
            'reliability_score': 75.0,
            'resource_efficiency_score': 70.0,
            'scalability_score': 75.0,
            'total_latency': 19.19,
            'db_queries': 5,
            'llm_calls': 1
        }

        result = LangSmithEvaluators.qos_evaluator(score_data)

        assert result['key'] == 'qos_score'
        assert abs(result['score'] - 0.74) < 0.01
        assert 'Latency: 19.19s' in result['comment']
        assert 'DB: 5' in result['comment']

    def test_cost_evaluator(self):
        """Test cost evaluator converts to LangSmith format"""
        score_data = {
            'overall_score': 88.0,
            'total_cost_thb': 0.42,
            'llm_cost_usd': 0.012,
            'input_tokens': 2284,
            'output_tokens': 2575,
            'total_tokens': 4859,
            'llm_calls': 1
        }

        result = LangSmithEvaluators.cost_evaluator(score_data)

        assert result['key'] == 'cost_score'
        assert abs(result['score'] - 0.88) < 0.01
        assert '฿0.42' in result['comment']
        assert '$0.0120' in result['comment']

    def test_evaluate_all(self):
        """Test evaluate_all returns all 6 metrics"""
        quality_scores = {
            'faithfulness': {'overall_score': 85.0},
            'completeness': {'overall_score': 78.0},
            'reasoning_quality': {'overall_score': 82.0},
            'compliance': {'overall_score': 91.0}
        }

        performance_scores = {
            'qos': {'overall_score': 74.0, 'total_latency': 19.19},
            'cost': {'overall_score': 88.0, 'total_cost_thb': 0.42}
        }

        results = LangSmithEvaluators.evaluate_all(quality_scores, performance_scores)

        assert len(results) == 6
        keys = [r['key'] for r in results]
        assert 'faithfulness_score' in keys
        assert 'completeness_score' in keys
        assert 'reasoning_quality_score' in keys
        assert 'compliance_score' in keys
        assert 'qos_score' in keys
        assert 'cost_score' in keys

    def test_score_normalization(self):
        """Test scores are normalized from 0-100 to 0-1 for LangSmith"""
        score_data = {'overall_score': 85.5}

        result = LangSmithEvaluators.faithfulness_evaluator(score_data)

        assert result['score'] <= 1.0
        assert result['score'] >= 0.0
        assert abs(result['score'] - 0.855) < 0.001


class TestLangSmithClient:
    """Test LangSmith client initialization"""

    @patch.dict(os.environ, {'LANGSMITH_API_KEY': 'test-key'})
    @patch('src.evaluation.langsmith_integration.Client')
    def test_get_client_with_api_key(self, mock_client):
        """Test client initialization with API key"""
        client = get_langsmith_client()

        assert client is not None
        mock_client.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_get_client_without_api_key(self):
        """Test client initialization without API key returns None"""
        # Remove LANGSMITH_API_KEY if it exists
        os.environ.pop('LANGSMITH_API_KEY', None)

        client = get_langsmith_client()

        assert client is None

    @patch.dict(os.environ, {'LANGSMITH_API_KEY': 'test-key'})
    @patch('src.evaluation.langsmith_integration.Client')
    def test_get_client_with_exception(self, mock_client):
        """Test client initialization handles exceptions gracefully"""
        mock_client.side_effect = Exception("Connection error")

        client = get_langsmith_client()

        assert client is None


class TestLogEvaluationToLangSmith:
    """Test evaluation logging to LangSmith"""

    def test_log_evaluation_success(self):
        """Test successful evaluation logging"""
        mock_client = Mock()
        quality_scores = {
            'faithfulness': {'overall_score': 85.0},
            'completeness': {'overall_score': 78.0},
            'reasoning_quality': {'overall_score': 82.0},
            'compliance': {'overall_score': 91.0}
        }
        performance_scores = {
            'qos': {'overall_score': 74.0},
            'cost': {'overall_score': 88.0}
        }

        result = log_evaluation_to_langsmith(
            client=mock_client,
            run_id='test-run-id-123',
            ticker='SIA19',
            quality_scores=quality_scores,
            performance_scores=performance_scores
        )

        assert result is True
        # Should call create_feedback 6 times (one per metric)
        assert mock_client.create_feedback.call_count == 6

    def test_log_evaluation_with_metadata(self):
        """Test evaluation logging accepts metadata parameter"""
        mock_client = Mock()
        quality_scores = {'faithfulness': {'overall_score': 85.0}}
        performance_scores = {'qos': {'overall_score': 74.0}}

        metadata = {'date': '2025-11-19', 'mode': 'async'}

        # Should not raise when metadata is passed
        result = log_evaluation_to_langsmith(
            client=mock_client,
            run_id='test-run-id',
            ticker='SIA19',
            quality_scores=quality_scores,
            performance_scores=performance_scores,
            metadata=metadata
        )

        # Verify evaluations were logged
        assert result is True
        # create_feedback should be called for each evaluation (faithfulness, qos)
        assert mock_client.create_feedback.call_count == 2

    def test_log_evaluation_handles_exception(self):
        """Test evaluation logging handles exceptions gracefully"""
        mock_client = Mock()
        mock_client.create_feedback.side_effect = Exception("API error")

        quality_scores = {'faithfulness': {'overall_score': 85.0}}
        performance_scores = {}

        result = log_evaluation_to_langsmith(
            client=mock_client,
            run_id='test-run-id',
            ticker='SIA19',
            quality_scores=quality_scores,
            performance_scores=performance_scores
        )

        assert result is False
