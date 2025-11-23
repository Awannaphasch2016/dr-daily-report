#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for eval_component.py

Regression tests to ensure all imports and initializations work correctly.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEvalComponentImports:
    """Test that all imports in eval_component.py work correctly."""

    def test_all_module_imports_work(self):
        """Test that all required modules can be imported."""
        # These imports should not raise ImportError
        from src.workflow.workflow_nodes import WorkflowNodes
        from src.database import TickerDatabase
        from src.data_fetcher import DataFetcher
        from src.technical_analysis import TechnicalAnalyzer
        from src.news_fetcher import NewsFetcher
        from src.chart_generator import ChartGenerator
        from src.strategy import SMAStrategyBacktester
        from src.analysis import StrategyAnalyzer, MarketAnalyzer
        from src.comparative_analysis import ComparativeAnalyzer
        from src.report import PromptBuilder, ContextBuilder, NumberInjector
        from src.cost_scorer import CostScorer
        from langchain_openai import ChatOpenAI
        from src.scoring_service import ScoringService
        from src.qos_scorer import QoSScorer
        from src.faithfulness_scorer import FaithfulnessScorer
        from src.completeness_scorer import CompletenessScorer
        from src.reasoning_quality_scorer import ReasoningQualityScorer
        from src.compliance_scorer import ComplianceScorer
        from src.formatters import DataFormatter

        # If we got here, all imports succeeded
        assert True

    def test_eval_component_script_can_be_imported(self):
        """Test that eval_component.py can be imported without errors."""
        from scripts import eval_component
        assert hasattr(eval_component, 'target_report_generation')
        assert hasattr(eval_component, 'run_component_evaluation')

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('src.workflow.workflow_nodes.WorkflowNodes')
    @patch('src.database.TickerDatabase')
    @patch('src.data_fetcher.DataFetcher')
    def test_target_report_generation_initialization(
        self,
        mock_data_fetcher_class,
        mock_db_class,
        mock_workflow_nodes_class
    ):
        """Test that target_report_generation can initialize all dependencies."""
        from scripts.eval_component import target_report_generation

        # Mock all the dependencies
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        mock_data_fetcher = Mock()
        mock_data_fetcher.load_tickers.return_value = {'TEST': 'TEST.BK'}
        mock_data_fetcher_class.return_value = mock_data_fetcher

        mock_nodes = Mock()
        mock_nodes.generate_report.return_value = {
            "report": "Test report",
            "error": None
        }
        mock_workflow_nodes_class.return_value = mock_nodes

        # Call the function
        inputs = {
            "ticker": "TEST",
            "date": "2025-11-23",
            "indicators": {},
            "ticker_data": {}
        }

        result = target_report_generation(inputs)

        # Verify it returns expected structure
        assert "narrative" in result
        assert mock_workflow_nodes_class.called


class TestEvalComponentCorrectInitialization:
    """Test that classes are initialized with correct parameters."""

    def test_data_fetcher_no_args(self):
        """DataFetcher should be initialized without arguments."""
        from src.data_fetcher import DataFetcher
        # Should not raise TypeError
        fetcher = DataFetcher()
        assert fetcher is not None

    def test_strategy_analyzer_needs_backtester(self):
        """StrategyAnalyzer requires strategy_backtester argument."""
        from src.strategy import SMAStrategyBacktester
        from src.analysis import StrategyAnalyzer

        backtester = SMAStrategyBacktester()
        # Should not raise TypeError
        analyzer = StrategyAnalyzer(backtester)
        assert analyzer is not None

    def test_comparative_analyzer_no_args(self):
        """ComparativeAnalyzer should be initialized without arguments."""
        from src.comparative_analysis import ComparativeAnalyzer
        # Should not raise TypeError
        analyzer = ComparativeAnalyzer()
        assert analyzer is not None

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_scoring_service_no_args(self):
        """ScoringService should be initialized without arguments."""
        from src.scoring_service import ScoringService
        # Should not raise TypeError
        service = ScoringService()
        assert service is not None

    def test_context_builder_requires_args(self):
        """ContextBuilder requires market_analyzer, data_formatter, technical_analyzer."""
        from src.report import ContextBuilder
        from src.analysis import MarketAnalyzer
        from src.formatters import DataFormatter
        from src.technical_analysis import TechnicalAnalyzer

        market_analyzer = MarketAnalyzer()
        data_formatter = DataFormatter()
        technical_analyzer = TechnicalAnalyzer()

        # Should not raise TypeError
        builder = ContextBuilder(market_analyzer, data_formatter, technical_analyzer)
        assert builder is not None


class TestEvalComponentWorkflowNodesParams:
    """Test that WorkflowNodes is initialized with all required parameters."""

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    @patch('src.workflow.workflow_nodes.WorkflowNodes.__init__')
    @patch('src.workflow.workflow_nodes.WorkflowNodes.generate_report')
    def test_workflow_nodes_gets_all_required_params(self, mock_gen, mock_init):
        """Test that WorkflowNodes receives all required parameters."""
        mock_init.return_value = None
        mock_gen.return_value = {"report": "test", "error": None}

        from scripts.eval_component import target_report_generation

        inputs = {
            "ticker": "TEST",
            "date": "2025-11-23",
            "indicators": {},
            "ticker_data": {}
        }

        try:
            target_report_generation(inputs)
        except:
            pass  # We're only checking that __init__ was called correctly

        # Verify WorkflowNodes.__init__ was called with db_query_count_ref
        assert mock_init.called
        call_kwargs = mock_init.call_args[1]
        assert 'db_query_count_ref' in call_kwargs
        assert isinstance(call_kwargs['db_query_count_ref'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
