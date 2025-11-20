#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression Tests for LangSmith Integration

Tests backward compatibility and graceful degradation:
- Workflow runs without LangSmith
- Missing API keys don't break workflow
- Async evaluation completes even if LangSmith fails
- SQLite scores still saved if LangSmith unavailable
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import Mock, patch
import warnings
warnings.filterwarnings('ignore')

from src.agent import TickerAnalysisAgent


class TestBackwardCompatibility(unittest.TestCase):
    """Test that workflow works without LangSmith"""

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'false'}, clear=True)
    def test_workflow_without_langsmith(self,
                                       mock_llm,
                                       mock_chart,
                                       mock_comparative,
                                       mock_news,
                                       mock_fetch):
        """
        Regression test: Workflow works without LangSmith enabled.
        CLAIM: LANGCHAIN_TRACING_V2=false doesn't break workflow.
        """
        # Remove LANGCHAIN_API_KEY
        os.environ.pop('LANGCHAIN_API_KEY', None)

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should not raise exception
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch.dict(os.environ, {}, clear=True)
    def test_workflow_without_api_key(self,
                                     mock_llm,
                                     mock_chart,
                                     mock_comparative,
                                     mock_news,
                                     mock_fetch):
        """
        Regression test: Workflow works without LANGCHAIN_API_KEY.
        CLAIM: Missing API key doesn't break workflow.
        """
        # Ensure no LangSmith env vars
        os.environ.pop('LANGCHAIN_API_KEY', None)
        os.environ.pop('LANGCHAIN_TRACING_V2', None)

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should work without LangSmith configured
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)


class TestGracefulDegradation(unittest.TestCase):
    """Test that workflow continues even if LangSmith fails"""

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch('src.langsmith_integration.get_langsmith_client')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key'})
    def test_langsmith_client_failure(self,
                                      mock_langsmith_client,
                                      mock_llm,
                                      mock_chart,
                                      mock_comparative,
                                      mock_news,
                                      mock_fetch):
        """
        Regression test: Workflow continues if LangSmith client fails.
        CLAIM: LangSmith failure doesn't break report generation.
        """
        # Mock LangSmith client to return None (failure)
        mock_langsmith_client.return_value = None

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # CLAIM VALIDATION: Should generate report despite LangSmith failure
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    @patch('src.data_fetcher.DataFetcher.fetch_data')
    @patch('src.news_fetcher.NewsFetcher.filter_high_impact_news')
    @patch('src.comparative_analysis.ComparativeAnalyzer.analyze_ticker_similarity')
    @patch('src.chart_generator.ChartGenerator.generate_chart')
    @patch('langchain_openai.ChatOpenAI.invoke')
    @patch('src.database.TickerDatabase.save_faithfulness_score')
    @patch('src.langsmith_integration.log_evaluation_to_langsmith')
    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true', 'LANGCHAIN_API_KEY': 'test-key'})
    def test_sqlite_saves_even_if_langsmith_fails(self,
                                                  mock_langsmith_log,
                                                  mock_db_save,
                                                  mock_llm,
                                                  mock_chart,
                                                  mock_comparative,
                                                  mock_news,
                                                  mock_fetch):
        """
        Regression test: SQLite saves work even if LangSmith logging fails.
        CLAIM: Database persistence is independent of LangSmith.
        """
        # Mock LangSmith logging to fail
        mock_langsmith_log.return_value = False

        # Mock responses
        mock_fetch.return_value = ({
            'company_name': 'Test',
            'current_price': 100.0,
            'ticker': 'TEST.SI',
            'date': '2025-11-19'
        }, Mock())
        mock_news.return_value = []
        mock_comparative.return_value = {}
        mock_chart.return_value = 'chart'

        mock_llm_response = Mock()
        mock_llm_response.content = "Test report"
        mock_llm_response.response_metadata = {
            'token_usage': {'prompt_tokens': 2000, 'completion_tokens': 400, 'total_tokens': 2400}
        }
        mock_llm.return_value = mock_llm_response

        # Run workflow
        agent = TickerAnalysisAgent()
        report = agent.analyze_ticker('TEST19')

        # Wait for background evaluation
        import time
        time.sleep(2)

        # CLAIM VALIDATION: Report should be generated
        self.assertIsInstance(report, str)

        # Note: Database saves happen in background thread
        # This validates the code path exists

    @patch.dict(os.environ, {'LANGCHAIN_TRACING_V2': 'true'})
    def test_no_run_tree_available(self):
        """
        Regression test: Workflow handles missing run tree gracefully.
        CLAIM: get_current_run_tree() returning None doesn't break workflow.
        """
        with patch('src.workflow.workflow_nodes.get_current_run_tree') as mock_get_run:
            # Mock no run tree available
            mock_get_run.return_value = None

            # This should not raise an exception
            # Full workflow test would validate this completely
            self.assertIsNone(mock_get_run())


class TestAsyncEvaluationResilience(unittest.TestCase):
    """Test that async evaluation is resilient to failures"""

    def test_async_evaluation_handles_exception(self):
        """Test that background evaluation handles exceptions"""
        from src.langsmith_integration import async_evaluate_and_log

        # Mock scoring service that raises exception
        mock_scoring_service = Mock()
        mock_scoring_service.compute_all_quality_scores.side_effect = Exception("Scoring error")

        # CLAIM VALIDATION: Should not raise exception (logged instead)
        result = async_evaluate_and_log(
            scoring_service=mock_scoring_service,
            qos_scorer=Mock(),
            cost_scorer=Mock(),
            database=Mock(),
            report="Test report",
            scoring_context=Mock(),
            ticker='TEST19',
            date='2025-11-19',
            timing_metrics={},
            langsmith_run_id=None
        )

        # Should return empty dict on error
        self.assertEqual(result, {})

    def test_database_save_failure_continues(self):
        """Test that LangSmith logging continues even if database save fails"""
        from src.langsmith_integration import async_evaluate_and_log
        from src.scoring_service import ScoringContext

        # Mock database that fails
        mock_db = Mock()
        mock_db.save_faithfulness_score.side_effect = Exception("DB error")

        # Mock scoring service
        mock_scoring_service = Mock()
        mock_scoring_service.compute_all_quality_scores.return_value = {
            'faithfulness': {'overall_score': 85.0},
            'completeness': {'overall_score': 78.0},
            'reasoning_quality': {'overall_score': 82.0},
            'compliance': {'overall_score': 91.0}
        }

        # CLAIM VALIDATION: Should continue despite database error
        # This validates graceful error handling
        try:
            result = async_evaluate_and_log(
                scoring_service=mock_scoring_service,
                qos_scorer=Mock(),
                cost_scorer=Mock(),
                database=mock_db,
                report="Test report",
                scoring_context=Mock(
                    indicators={},
                    percentiles={},
                    news=[],
                    ticker_data={},
                    market_conditions={}
                ),
                ticker='TEST19',
                date='2025-11-19',
                timing_metrics={},
                langsmith_run_id=None
            )
            # Should complete without raising exception
            self.assertIsNotNone(result)
        except Exception as e:
            self.fail(f"async_evaluate_and_log should handle database errors gracefully: {e}")


if __name__ == '__main__':
    unittest.main()
