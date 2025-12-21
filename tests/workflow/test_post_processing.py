"""
Test post-processing pipeline for report generation (Thai only).

Tests the _post_process_report_workflow() method that centralizes:
1. Ground truth calculation
2. Number injection ({{PLACEHOLDER}} → exact values)
3. News references
4. Transparency footer

Note: Percentile analysis step removed (Thai reports don't show it).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.workflow.workflow_nodes import WorkflowNodes
from src.types import AgentState


class TestPostProcessingWorkflow:
    """Test _post_process_report_workflow() method"""

    def setup_method(self):
        """Initialize WorkflowNodes with mocked dependencies"""
        # Create mocks for all required dependencies
        self.market_analyzer = Mock()
        self.number_injector = Mock()
        self.news_fetcher = Mock()

        # Configure mock default return values
        self.market_analyzer.calculate_market_conditions.return_value = {
            'price_vs_vwap_pct': 0.0,
            'volume_ratio': 1.0
        }
        # number_injector returns input unchanged by default (will be overridden in tests)
        self.number_injector.inject_deterministic_numbers.side_effect = lambda report, *args, **kwargs: report
        self.news_fetcher.get_news_references.return_value = "📎 **แหล่งข้อมูลข่าว:**\n[1] Test"

        # Initialize WorkflowNodes with mocks
        self.nodes = WorkflowNodes(
            data_fetcher=Mock(),
            technical_analyzer=Mock(),
            news_fetcher=self.news_fetcher,
            chart_generator=Mock(),
            strategy_backtester=Mock(),
            strategy_analyzer=Mock(),
            comparative_analyzer=Mock(),
            llm=Mock(),
            context_builder=Mock(),
            prompt_builder=Mock(),
            market_analyzer=self.market_analyzer,
            number_injector=self.number_injector,
            cost_scorer=Mock(),
            scoring_service=Mock(),
            qos_scorer=Mock(),
            faithfulness_scorer=Mock(),
            completeness_scorer=Mock(),
            reasoning_quality_scorer=Mock(),
            compliance_scorer=Mock(),
            ticker_map=Mock(),
            db_query_count_ref=Mock()
        )

    def test_post_process_includes_all_components(self):
        """Verify all post-processing steps are applied"""
        # Given: Raw report with placeholders
        raw_report = "Price: {{CURRENT_PRICE}} THB, RSI: {{RSI}}"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 123.45,
                'rsi': 65.3,
                'uncertainty_score': 50.0,
                'atr': 1.5,
                'vwap': 120.0
            },
            'percentiles': {},
            'ticker_data': {},
            'comparative_insights': {},
            'news': [
                {
                    'title': 'Test News',
                    'url': 'https://example.com/news1',
                    'source': 'Test Source'
                }
            ]
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: Verify all components were called (integration test)
        self.market_analyzer.calculate_market_conditions.assert_called_once_with(state['indicators'])
        self.number_injector.inject_deterministic_numbers.assert_called_once()
        self.news_fetcher.get_news_references.assert_called_once_with(state['news'])

        # Then: Transparency footer added
        assert 'ข้อมูลที่ใช้ในการวิเคราะห์' in result, "Transparency footer should be present"

    def test_post_process_handles_empty_news(self):
        """Graceful degradation when no news available"""
        # Given: State with no news
        raw_report = "Price: {{CURRENT_PRICE}} THB"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 123.45,
                'uncertainty_score': 50.0,
                'atr': 1.5,
                'vwap': 120.0
            },
            'percentiles': {},
            'ticker_data': {},
            'comparative_insights': {},
            'news': []  # Empty news
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: Verify methods were called (integration test)
        self.number_injector.inject_deterministic_numbers.assert_called_once()
        self.news_fetcher.get_news_references.assert_not_called()  # No news!
        # Footer added
        assert 'ข้อมูลที่ใช้ในการวิเคราะห์' in result

    def test_post_process_handles_missing_ticker_data(self):
        """Test graceful handling when ticker_data missing"""
        raw_report = "P/E Ratio: {{PE_RATIO}}"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 123.45,
                'uncertainty_score': 50.0,
                'atr': 1.5,
                'vwap': 120.0
            },
            'percentiles': {},
            # ticker_data missing
            'comparative_insights': {},
            'news': []
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: Verify number_injector was called with empty dict for ticker_data
        call_args = self.number_injector.inject_deterministic_numbers.call_args
        # call_args[0] is tuple of positional args, index 4 is ticker_data (5th arg)
        assert call_args[0][4] == {}, "Should pass empty dict for missing ticker_data"

    def test_post_process_calculates_ground_truth_correctly(self):
        """Test that ground truth values are calculated from indicators"""
        raw_report = "Uncertainty: {{UNCERTAINTY}}, ATR%: {{ATR_PCT}}"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 100.0,
                'uncertainty_score': 45.5,
                'atr': 2.0,  # 2.0 / 100.0 = 2%
                'vwap': 98.0,
                'volume_ratio': 1.5
            },
            'percentiles': {},
            'ticker_data': {},
            'comparative_insights': {},
            'news': []
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: Verify ground truth was calculated and passed to number_injector
        call_args = self.number_injector.inject_deterministic_numbers.call_args
        ground_truth = call_args[0][1]  # Second positional arg
        assert ground_truth['uncertainty_score'] == 45.5
        assert ground_truth['atr_pct'] == 2.0  # 2.0 / 100.0 * 100
        assert 'vwap_pct' in ground_truth
        assert 'volume_ratio' in ground_truth

    def test_post_process_no_percentile_section(self):
        """Test that percentile section is NOT added (Thai reports)"""
        raw_report = "Test report"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 123.45,
                'rsi': 65.3,
                'uncertainty_score': 50.0,
                'atr': 1.5,
                'vwap': 120.0
            },
            'percentiles': {
                'rsi': {
                    'current_value': 65.3,
                    'percentile': 75.2
                }
            },  # Percentiles present but should NOT be displayed
            'ticker_data': {},
            'comparative_insights': {},
            'news': []
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: No percentile section added
        assert 'Percentile Analysis' not in result
        assert 'เปอร์เซ็นไทล์' not in result

    def test_post_process_preserves_thai_content(self):
        """Test that Thai content is preserved correctly"""
        raw_report = "ราคาปัจจุบัน: {{CURRENT_PRICE}} บาท, RSI อยู่ที่ {{RSI}}"

        state = {
            'ticker': 'DBS19',
            'indicators': {
                'current_price': 123.45,
                'rsi': 65.3,
                'uncertainty_score': 50.0,
                'atr': 1.5,
                'vwap': 120.0
            },
            'percentiles': {},
            'ticker_data': {},
            'comparative_insights': {},
            'news': []
        }

        # When: Post-process called
        result = self.nodes._post_process_report_workflow(
            raw_report, state, state['indicators']
        )

        # Then: Thai content preserved (mock returns input unchanged)
        assert 'ราคาปัจจุบัน' in result
        assert 'บาท' in result
        assert 'RSI อยู่ที่' in result
        # Verify footer is in Thai
        assert 'ข้อมูลที่ใช้ในการวิเคราะห์' in result
