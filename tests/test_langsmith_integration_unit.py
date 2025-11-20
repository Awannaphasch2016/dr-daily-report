#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for LangSmith Integration

Tests individual components of the LangSmith integration:
- Evaluator wrappers (6 metrics)
- Client initialization
- Score logging
- Data format conversion
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import Mock, patch, MagicMock
import warnings
warnings.filterwarnings('ignore')

from src.langsmith_evaluators import LangSmithEvaluators
from src.langsmith_integration import get_langsmith_client, log_evaluation_to_langsmith


class TestLangSmithEvaluators(unittest.TestCase):
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

        self.assertEqual(result['key'], 'faithfulness_score')
        self.assertAlmostEqual(result['score'], 0.85, places=2)
        self.assertIn('Numeric: 90.0%', result['comment'])
        self.assertIn('Percentile: 85.0%', result['comment'])

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

        self.assertEqual(result['key'], 'completeness_score')
        self.assertAlmostEqual(result['score'], 0.78, places=2)
        self.assertIn('Context: 85.0%', result['comment'])
        self.assertIn('Missing: 1', result['comment'])

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

        self.assertEqual(result['key'], 'reasoning_quality_score')
        self.assertAlmostEqual(result['score'], 0.82, places=2)
        self.assertIn('Clarity: 85.0%', result['comment'])

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

        self.assertEqual(result['key'], 'compliance_score')
        self.assertAlmostEqual(result['score'], 0.91, places=2)
        self.assertIn('Structure: 95.0%', result['comment'])

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

        self.assertEqual(result['key'], 'qos_score')
        self.assertAlmostEqual(result['score'], 0.74, places=2)
        self.assertIn('Latency: 19.19s', result['comment'])
        self.assertIn('DB: 5', result['comment'])

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

        self.assertEqual(result['key'], 'cost_score')
        self.assertAlmostEqual(result['score'], 0.88, places=2)
        self.assertIn('฿0.42', result['comment'])
        self.assertIn('$0.0120', result['comment'])

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

        self.assertEqual(len(results), 6)
        keys = [r['key'] for r in results]
        self.assertIn('faithfulness_score', keys)
        self.assertIn('completeness_score', keys)
        self.assertIn('reasoning_quality_score', keys)
        self.assertIn('compliance_score', keys)
        self.assertIn('qos_score', keys)
        self.assertIn('cost_score', keys)

    def test_score_normalization(self):
        """Test scores are normalized from 0-100 to 0-1 for LangSmith"""
        score_data = {'overall_score': 85.5}

        result = LangSmithEvaluators.faithfulness_evaluator(score_data)

        self.assertLessEqual(result['score'], 1.0)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertAlmostEqual(result['score'], 0.855, places=3)


class TestLangSmithClient(unittest.TestCase):
    """Test LangSmith client initialization"""

    @patch.dict(os.environ, {'LANGCHAIN_API_KEY': 'test-key'})
    @patch('src.langsmith_integration.Client')
    def test_get_client_with_api_key(self, mock_client):
        """Test client initialization with API key"""
        client = get_langsmith_client()

        self.assertIsNotNone(client)
        mock_client.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_get_client_without_api_key(self):
        """Test client initialization without API key returns None"""
        # Remove LANGCHAIN_API_KEY if it exists
        os.environ.pop('LANGCHAIN_API_KEY', None)

        client = get_langsmith_client()

        self.assertIsNone(client)

    @patch.dict(os.environ, {'LANGCHAIN_API_KEY': 'test-key'})
    @patch('src.langsmith_integration.Client')
    def test_get_client_with_exception(self, mock_client):
        """Test client initialization handles exceptions gracefully"""
        mock_client.side_effect = Exception("Connection error")

        client = get_langsmith_client()

        self.assertIsNone(client)


class TestLogEvaluationToLangSmith(unittest.TestCase):
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

        self.assertTrue(result)
        # Should call create_feedback 6 times (one per metric)
        self.assertEqual(mock_client.create_feedback.call_count, 6)

    def test_log_evaluation_with_metadata(self):
        """Test evaluation logging includes metadata"""
        mock_client = Mock()
        quality_scores = {'faithfulness': {'overall_score': 85.0}}
        performance_scores = {'qos': {'overall_score': 74.0}}

        metadata = {'date': '2025-11-19', 'mode': 'async'}

        log_evaluation_to_langsmith(
            client=mock_client,
            run_id='test-run-id',
            ticker='SIA19',
            quality_scores=quality_scores,
            performance_scores=performance_scores,
            metadata=metadata
        )

        # Verify metadata is passed to create_feedback
        call_kwargs = mock_client.create_feedback.call_args_list[0][1]
        self.assertEqual(call_kwargs['date'], '2025-11-19')
        self.assertEqual(call_kwargs['mode'], 'async')

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

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
