# -*- coding: utf-8 -*-
"""
Tests for API Handler

Unit tests for the API handler endpoint functionality.
"""

import json
import base64
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAPIHandler:
    """Tests for API handler functionality"""

    @pytest.fixture
    def mock_final_state(self):
        """Create mock final state that graph.invoke returns"""
        return {
            'messages': [],
            'ticker': 'TEST19',
            'ticker_data': {
                'company_name': 'Test Company',
                'close': 150.0,
                'change': 2.5,
                'change_percent': 1.5
            },
            'indicators': {
                'rsi': 55.0,
                'macd': 2.5,
                'sma_20': 145.0,
                'sma_50': 140.0
            },
            'percentiles': {
                'current_percentile': 75.0
            },
            'news': [
                {'title': 'Test News', 'url': 'https://example.com'}
            ],
            'news_summary': {'summary': 'Test summary'},
            'chart_base64': 'iVBORw0KGgoAAAANSUhEUg==',
            'report': 'Test report content in Thai',
            'faithfulness_score': {},
            'completeness_score': {},
            'reasoning_quality_score': {},
            'compliance_score': {},
            'qos_score': {},
            'cost_score': {},
            'timing_metrics': {},
            'api_costs': {},
            'database_metrics': {},
            'error': ''
        }

    @pytest.fixture
    def mock_agent(self, mock_final_state):
        """Create mock TickerAnalysisAgent with proper graph.invoke"""
        mock = MagicMock()
        mock.graph.invoke.return_value = mock_final_state
        return mock

    def test_missing_ticker_returns_400(self):
        """Test that missing ticker parameter returns 400"""
        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': {},
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
        body = json.loads(response['body'])
        assert 'error' in body, "Response should contain 'error' key"

    def test_empty_ticker_returns_400(self):
        """Test that empty ticker parameter returns 400"""
        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': {'ticker': ''},
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"

    def test_null_query_params_returns_400(self):
        """Test that null queryStringParameters returns 400"""
        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': None,
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"

    def test_successful_analysis(self, mock_agent):
        """Test successful ticker analysis"""
        with patch('src.integrations.api_handler.get_agent') as mock_get_agent:
            mock_get_agent.return_value = mock_agent

            from src.integrations.api_handler import api_handler

            event = {
                'queryStringParameters': {'ticker': 'TEST19'},
                'headers': {},
                'body': None
            }

            response = api_handler(event, None)

            assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"

            body = json.loads(response['body'])
            assert 'ticker' in body, "Response should contain 'ticker'"
            assert body['ticker'] == 'TEST19'
            assert 'report' in body, "Response should contain 'report'"

    @patch('src.integrations.api_handler.get_agent')
    def test_analysis_error_returns_500(self, mock_get_agent):
        """Test that analysis errors return 500"""
        mock_agent = MagicMock()
        mock_agent.analyze_ticker_full.side_effect = Exception("Test error")
        mock_get_agent.return_value = mock_agent

        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': {'ticker': 'ERROR19'},
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
        body = json.loads(response['body'])
        assert 'error' in body

    def test_cors_headers_present(self):
        """Test that CORS headers are included in response"""
        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': {},
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        headers = response.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers, "CORS header missing"
        assert headers['Access-Control-Allow-Origin'] == '*'

    def test_ticker_uppercase_conversion(self, mock_final_state):
        """Test that ticker is converted to uppercase"""
        from src.integrations.api_handler import api_handler

        with patch('src.integrations.api_handler.get_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.graph.invoke.return_value = mock_final_state
            mock_get_agent.return_value = mock_agent

            event = {
                'queryStringParameters': {'ticker': 'test19'},
                'headers': {},
                'body': None
            }

            response = api_handler(event, None)

            # Response should be successful
            assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"

            # Verify the ticker in response is uppercase
            body = json.loads(response['body'])
            assert body['ticker'] == 'TEST19', f"Expected uppercase ticker, got {body.get('ticker')}"


class TestAPIHandlerSanitization:
    """Tests for data sanitization in API handler"""

    def test_sanitize_skips_history_dataframe(self):
        """Test that history DataFrame is skipped"""
        from src.integrations.api_handler import sanitize_ticker_data
        import pandas as pd

        data = {
            'close': 150.5,
            'history': pd.DataFrame({'Close': [100, 101, 102]})  # DataFrame to skip
        }
        result = sanitize_ticker_data(data)

        assert 'history' not in result, "history DataFrame should be skipped"
        assert result['close'] == 150.5

    def test_sanitize_handles_datetime(self):
        """Test that datetime values are converted to ISO format"""
        from src.integrations.api_handler import sanitize_ticker_data
        from datetime import datetime

        now = datetime.now()
        data = {'timestamp': now}
        result = sanitize_ticker_data(data)

        assert isinstance(result['timestamp'], str), "datetime should be converted to string"
        assert 'T' in result['timestamp'], "Should be ISO format"

    def test_sanitize_handles_regular_values(self):
        """Test that regular values pass through"""
        from src.integrations.api_handler import sanitize_ticker_data

        data = {
            'name': 'Test Company',
            'price': 150.5,
            'volume': 1000000
        }
        result = sanitize_ticker_data(data)

        assert result['name'] == 'Test Company'
        assert result['price'] == 150.5
        assert result['volume'] == 1000000


@pytest.mark.integration
@pytest.mark.slow
class TestAPIHandlerIntegration:
    """Integration tests for API handler with real agent"""

    @pytest.fixture(autouse=True)
    def check_api_key(self, requires_llm):
        """Use centralized requires_llm fixture"""
        pass

    def test_real_ticker_analysis(self):
        """Test real ticker analysis end-to-end"""
        from src.integrations.api_handler import api_handler

        event = {
            'queryStringParameters': {'ticker': 'AAPL'},
            'headers': {},
            'body': None
        }

        response = api_handler(event, None)

        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"

        body = json.loads(response['body'])
        assert 'ticker' in body
        assert 'report' in body
        assert 'indicators' in body
        assert len(body['report']) > 100, "Report should have substantial content"
