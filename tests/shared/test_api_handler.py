# -*- coding: utf-8 -*-
"""
Tests for API Handler (api_handler.py)

Tests ticker parameter extraction, analysis flow, error handling,
and JSON serialization.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.integrations.api_handler import api_handler, sanitize_ticker_data, sanitize_news, sanitize_dict


class TestAPIHandlerParameters:
    """Tests for API handler parameter validation"""

    def test_missing_ticker_parameter(self):
        """Test that missing ticker parameter returns 400 error"""
        event = {
            'queryStringParameters': None
        }

        result = api_handler(event, None)

        assert result['statusCode'] == 400, "Should return 400 status code"
        body = json.loads(result['body'])
        assert 'error' in body, "Should contain error message"
        assert 'ticker' in body['error'].lower() or 'parameter' in body['error'].lower()

    def test_empty_ticker_parameter(self):
        """Test that empty ticker parameter returns 400 error"""
        event = {
            'queryStringParameters': {
                'ticker': ''
            }
        }

        result = api_handler(event, None)

        assert result['statusCode'] == 400, "Should return 400 status code"
        body = json.loads(result['body'])
        assert 'error' in body, "Should contain error message"

    def test_cors_headers_present(self):
        """Test that CORS headers are included in response"""
        event = {
            'queryStringParameters': None
        }

        result = api_handler(event, None)

        headers = result.get('headers', {})
        assert 'Access-Control-Allow-Origin' in headers, "Should include CORS header"
        assert headers['Access-Control-Allow-Origin'] == '*', "CORS should allow all origins"


class TestSanitization:
    """Tests for data sanitization functions"""

    def test_sanitize_ticker_data_removes_dataframe(self):
        """Test that DataFrame is removed from ticker_data"""
        import pandas as pd

        ticker_data = {
            'date': datetime(2024, 1, 1),
            'close': 150.50,
            'open': 149.00,
            'history': pd.DataFrame({'Close': [150, 151, 152]})
        }

        sanitized = sanitize_ticker_data(ticker_data)

        assert 'history' not in sanitized, "DataFrame should be removed"
        assert sanitized['close'] == 150.50, "Other fields should be preserved"
        assert sanitized['date'] == datetime(2024, 1, 1).isoformat(), "Date should be ISO format"

    def test_sanitize_news_removes_raw_data(self):
        """Test that news items are properly sanitized"""
        news_list = [
            {
                'title': 'Test News',
                'timestamp': datetime(2024, 1, 1),
                'link': 'https://example.com',
                'raw': {'some': 'large', 'nested': 'data'}
            }
        ]

        sanitized = sanitize_news(news_list)

        assert len(sanitized) == 1, "Should have one news item"
        assert 'raw' not in sanitized[0], "Raw data should be removed"
        assert sanitized[0]['title'] == 'Test News', "Title should be preserved"
        assert isinstance(sanitized[0]['timestamp'], str), "Timestamp should be string"

    def test_sanitize_dict_converts_dates(self):
        """Test recursive dictionary sanitization"""
        data = {
            'date': datetime(2024, 1, 1),
            'nested': {
                'inner_date': datetime(2024, 1, 2)
            },
            'list': [
                {'item_date': datetime(2024, 1, 3)}
            ]
        }

        sanitized = sanitize_dict(data)

        assert isinstance(sanitized['date'], str), "Date should be ISO string"
        assert isinstance(sanitized['nested']['inner_date'], str), "Nested date should be converted"
        assert isinstance(sanitized['list'][0]['item_date'], str), "List item date should be converted"

    def test_json_serialization_after_sanitization(self):
        """Test that sanitized data can be JSON serialized"""
        import pandas as pd

        ticker_data = {
            'date': datetime(2024, 1, 1),
            'close': 150.50,
            'history': pd.DataFrame({'Close': [150, 151]})
        }

        news_list = [
            {
                'title': 'Test',
                'timestamp': datetime(2024, 1, 1),
                'raw': {'data': 'should be removed'}
            }
        ]

        sanitized_ticker = sanitize_ticker_data(ticker_data)
        sanitized_news = sanitize_news(news_list)

        # Should not raise exception
        json_str = json.dumps({
            'ticker_data': sanitized_ticker,
            'news': sanitized_news
        }, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict), "Should produce valid JSON"


class TestAPIHandlerAnalysis:
    """Tests for API handler analysis flow"""

    @pytest.fixture
    def mock_final_state(self):
        """Create mock final state from graph.invoke"""
        return {
            'ticker': 'AAPL',
            'ticker_data': {
                'date': datetime(2024, 1, 1),
                'close': 150.50,
                'market_cap': 2800000000000,
                'pe_ratio': 29.5
            },
            'indicators': {
                'sma_20': 176.20,
                'rsi': 58.3,
                'macd': 1.25
            },
            'percentiles': {},
            'news': [
                {
                    'title': 'Test News',
                    'timestamp': datetime(2024, 1, 1),
                    'sentiment': 'positive',
                    'impact_score': 75.0
                }
            ],
            'news_summary': {
                'total_count': 5,
                'dominant_sentiment': 'positive'
            },
            'chart_base64': '',
            'report': 'Test report in Thai',
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

    def test_successful_analysis(self, mock_final_state):
        """Test successful analysis flow"""
        with patch('src.integrations.api_handler.get_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.graph.invoke.return_value = mock_final_state
            mock_get_agent.return_value = mock_agent

            event = {
                'queryStringParameters': {
                    'ticker': 'AAPL'
                }
            }

            result = api_handler(event, None)

            assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
            body = json.loads(result['body'])

            assert body['ticker'] == 'AAPL', "Should return correct ticker"
            assert 'ticker_data' in body, "Should contain ticker_data"
            assert 'indicators' in body, "Should contain indicators"
            assert 'news' in body, "Should contain news"
            assert 'report' in body, "Should contain report"
            assert 'history' not in body.get('ticker_data', {}), "Should not contain DataFrame"

    def test_error_handling(self):
        """Test error handling when agent returns error"""
        with patch('src.integrations.api_handler.get_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_final_state = {
                'error': 'ไม่พบข้อมูล ticker สำหรับ INVALID'
            }
            mock_agent.graph.invoke.return_value = mock_final_state
            mock_get_agent.return_value = mock_agent

            event = {
                'queryStringParameters': {
                    'ticker': 'INVALID'
                }
            }

            result = api_handler(event, None)

            assert result['statusCode'] == 400, "Should return 400 status code"
            body = json.loads(result['body'])
            assert 'error' in body, "Should contain error message"

    def test_ticker_uppercase_conversion(self, mock_final_state):
        """Test that ticker is converted to uppercase"""
        with patch('src.integrations.api_handler.get_agent') as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.graph.invoke.return_value = mock_final_state
            mock_get_agent.return_value = mock_agent

            event = {
                'queryStringParameters': {
                    'ticker': 'aapl'  # lowercase
                }
            }

            result = api_handler(event, None)

            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['ticker'] == 'AAPL', "Ticker should be uppercase"
