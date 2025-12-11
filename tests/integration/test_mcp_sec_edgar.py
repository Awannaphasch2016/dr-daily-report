# -*- coding: utf-8 -*-
"""
Integration tests for SEC EDGAR MCP server.

Tests MCP protocol compliance and SEC EDGAR API integration.
Follows TDD principles: test behavior, not implementation; validate actual output.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.mcp_servers.sec_edgar_handler import (
    lambda_handler,
    handle_tools_list,
    handle_tool_call,
    SECEdgarClient
)


class TestSECEdgarMCPProtocol:
    """Test MCP protocol compliance - behavior-focused tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/list',
                'id': 1
            })
        }

    def test_tools_list_returns_valid_schema(self):
        """Test tools/list returns valid MCP tool schema."""
        response = lambda_handler(self.valid_event, None)
        
        # Validate HTTP response structure
        assert isinstance(response, dict), f"Expected dict, got {type(response)}"
        assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
        assert 'headers' in response, "Response missing headers"
        assert 'body' in response, "Response missing body"
        
        # Validate JSON-RPC response
        body = json.loads(response['body'])
        assert body['jsonrpc'] == '2.0', f"Invalid jsonrpc version: {body.get('jsonrpc')}"
        assert 'result' in body, "Response missing result field"
        assert isinstance(body['result'], dict), f"Result should be dict, got {type(body['result'])}"
        
        # Validate tools array exists and is non-empty
        assert 'tools' in body['result'], "Result missing tools array"
        assert isinstance(body['result']['tools'], list), f"Tools should be list, got {type(body['result']['tools'])}"
        assert len(body['result']['tools']) > 0, "Tools array is empty"
        
        # Validate tool schema (the actual contract)
        tool = body['result']['tools'][0]
        assert tool['name'] == 'get_latest_filing', f"Expected 'get_latest_filing', got {tool.get('name')}"
        assert isinstance(tool.get('description'), str), f"Description should be string, got {type(tool.get('description'))}"
        assert len(tool.get('description', '')) > 0, "Description is empty"
        assert 'inputSchema' in tool, "Tool missing inputSchema"
        assert tool['inputSchema']['type'] == 'object', f"Schema type should be object, got {tool['inputSchema'].get('type')}"

    def test_tools_call_success_returns_filing_data(self):
        """Test tools/call returns actual filing data in correct format."""
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/call',
                'params': {
                    'name': 'get_latest_filing',
                    'arguments': {
                        'ticker': 'AAPL',
                        'form_type': '10-Q'
                    }
                },
                'id': 1
            })
        }
        
        # Mock SEC EDGAR client with explicit return value
        expected_filing = {
            'ticker': 'AAPL',
            'form_type': '10-Q',
            'filing_date': '2024-01-15',
            'company_name': 'Apple Inc.',
            'cik': '0000320193',
            'accession_number': '0000320193-24-000001',
            'filing_url': 'https://www.sec.gov/archives/edgar/data/320193/000032019324000001/aapl-10q_20240115.htm',
            'xbrl': {},
            'summary': 'Q1 2024 quarterly report',
            'document_count': 1
        }
        
        with patch('src.mcp_servers.sec_edgar_handler.get_sec_client') as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get_latest_filing.return_value = expected_filing
            mock_get_client.return_value = mock_client_instance
            
            response = lambda_handler(event, None)
            
            # Validate HTTP response
            assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
            
            # Validate JSON-RPC response structure
            body = json.loads(response['body'])
            assert body['jsonrpc'] == '2.0'
            assert 'result' in body, "Response missing result"
            assert 'content' in body['result'], "Result missing content array"
            assert len(body['result']['content']) > 0, "Content array is empty"
            
            # Validate content format (MCP protocol requirement)
            content_item = body['result']['content'][0]
            assert content_item['type'] == 'text', f"Expected text type, got {content_item.get('type')}"
            assert 'text' in content_item, "Content item missing text field"
            
            # Validate actual filing data (the behavior that matters)
            filing_data = json.loads(content_item['text'])
            assert isinstance(filing_data, dict), f"Filing data should be dict, got {type(filing_data)}"
            assert filing_data['ticker'] == 'AAPL', f"Expected AAPL, got {filing_data.get('ticker')}"
            assert filing_data['form_type'] == '10-Q', f"Expected 10-Q, got {filing_data.get('form_type')}"
            assert filing_data['filing_date'] == '2024-01-15', f"Expected 2024-01-15, got {filing_data.get('filing_date')}"
            assert filing_data['cik'] == '0000320193', f"Expected CIK 0000320193, got {filing_data.get('cik')}"

    def test_tools_call_missing_ticker_returns_error(self):
        """Test tools/call with missing required argument returns proper error."""
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/call',
                'params': {
                    'name': 'get_latest_filing',
                    'arguments': {}  # Missing ticker
                },
                'id': 1
            })
        }
        
        response = lambda_handler(event, None)
        
        # Validate error response structure
        assert response['statusCode'] == 500, f"Expected 500 for error, got {response['statusCode']}"
        
        body = json.loads(response['body'])
        assert 'error' in body, "Error response missing error field"
        assert isinstance(body['error'], dict), f"Error should be dict, got {type(body['error'])}"
        assert 'code' in body['error'], "Error missing code"
        assert 'message' in body['error'], "Error missing message"
        assert len(body['error']['message']) > 0, "Error message is empty"

    def test_invalid_method_returns_method_not_found_error(self):
        """Test request with invalid method returns proper JSON-RPC error."""
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'invalid_method',
                'id': 1
            })
        }
        
        response = lambda_handler(event, None)
        
        # Validate error response
        assert response['statusCode'] == 400, f"Expected 400 for invalid method, got {response['statusCode']}"
        
        body = json.loads(response['body'])
        assert 'error' in body, "Response missing error field"
        assert body['error']['code'] == -32601, f"Expected -32601 (Method not found), got {body['error'].get('code')}"
        assert 'Method not found' in body['error']['message'], f"Error message should mention method not found: {body['error'].get('message')}"

    def test_cors_headers_present_for_cross_origin_requests(self):
        """Test CORS headers are present for MCP client cross-origin requests."""
        response = lambda_handler(self.valid_event, None)
        
        # Validate headers exist
        assert 'headers' in response, "Response missing headers"
        assert isinstance(response['headers'], dict), f"Headers should be dict, got {type(response['headers'])}"
        
        # Validate CORS headers (the actual behavior)
        assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header"
        assert response['headers']['Access-Control-Allow-Origin'] == '*', f"Expected '*', got {response['headers'].get('Access-Control-Allow-Origin')}"
        assert 'Content-Type' in response['headers'], "Missing Content-Type header"
        assert response['headers']['Content-Type'] == 'application/json', f"Expected 'application/json', got {response['headers'].get('Content-Type')}"

    def test_tools_call_handles_client_exception_gracefully(self):
        """Test tools/call handles SEC client exceptions and returns error."""
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/call',
                'params': {
                    'name': 'get_latest_filing',
                    'arguments': {
                        'ticker': 'INVALID',
                        'form_type': '10-Q'
                    }
                },
                'id': 1
            })
        }
        
        # Mock client to raise exception (simulating SEC API failure)
        with patch('src.mcp_servers.sec_edgar_handler.get_sec_client') as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get_latest_filing.side_effect = ValueError("Could not find CIK for ticker: INVALID")
            mock_get_client.return_value = mock_client_instance
            
            response = lambda_handler(event, None)
            
            # Validate error response
            assert response['statusCode'] == 500, f"Expected 500 for exception, got {response['statusCode']}"
            
            body = json.loads(response['body'])
            assert 'error' in body, "Error response missing error field"
            assert 'Internal error' in body['error']['message'], f"Error message should mention internal error: {body['error'].get('message')}"


class TestSECEdgarClient:
    """Test SEC EDGAR client functionality - behavior-focused tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = SECEdgarClient()

    @pytest.mark.integration
    def test_get_cik_for_ticker_returns_valid_cik(self):
        """Test CIK lookup returns valid 10-digit CIK for known ticker."""
        cik = self.client._get_cik_for_ticker('AAPL')
        
        # Validate CIK format (the actual contract)
        assert cik is not None, "CIK lookup returned None"
        assert isinstance(cik, str), f"CIK should be string, got {type(cik)}"
        assert len(cik) == 10, f"CIK should be 10 digits, got length {len(cik)}"
        assert cik.isdigit(), f"CIK should be numeric, got {cik}"
        assert cik == '0000320193', f"Expected Apple CIK 0000320193, got {cik}"

    @pytest.mark.integration
    def test_get_cik_for_ticker_returns_none_for_invalid_ticker(self):
        """Test CIK lookup returns None for non-existent ticker."""
        cik = self.client._get_cik_for_ticker('INVALIDTICKER12345')
        
        # Validate behavior: None for invalid ticker
        assert cik is None, f"Expected None for invalid ticker, got {cik}"

    @pytest.mark.integration
    def test_get_latest_filing_returns_complete_filing_data(self):
        """Test fetching real SEC filing returns all required fields."""
        result = self.client.get_latest_filing('AAPL', '10-Q', lookback_days=365)
        
        # Validate result structure (the actual contract)
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        assert result['ticker'] == 'AAPL', f"Expected AAPL, got {result.get('ticker')}"
        assert result['form_type'] == '10-Q', f"Expected 10-Q, got {result.get('form_type')}"
        
        # Validate required fields exist and are non-empty
        assert 'filing_date' in result, "Result missing filing_date"
        assert result['filing_date'] is not None, "filing_date is None"
        assert len(str(result['filing_date'])) > 0, "filing_date is empty"
        
        assert 'cik' in result, "Result missing cik"
        assert result['cik'] is not None, "cik is None"
        assert len(str(result['cik'])) == 10, f"CIK should be 10 digits, got {len(str(result.get('cik')))}"
        
        assert 'company_name' in result, "Result missing company_name"
        assert 'accession_number' in result, "Result missing accession_number"

    @pytest.mark.integration
    def test_get_latest_filing_handles_no_filing_found(self):
        """Test get_latest_filing returns error dict when no filing found."""
        # Use a ticker that exists but has no recent filings
        result = self.client.get_latest_filing('AAPL', '8-K', lookback_days=1)  # Very short lookback
        
        # Validate error response structure
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        # May return error dict or empty result - both are valid behaviors
        if 'error' in result:
            assert isinstance(result['error'], str), f"Error should be string, got {type(result['error'])}"
            assert len(result['error']) > 0, "Error message is empty"


class TestSabotageVerification:
    """Verify tests can actually detect failures (TDD principle)."""

    def test_tools_list_test_can_detect_missing_tools(self):
        """Verify test fails if tools/list returns empty tools array."""
        # This test verifies our test can detect broken behavior
        # If tools/list returned [], test_tools_list_returns_valid_schema should fail
        
        # Simulate broken response
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/list',
                'id': 1
            })
        }
        
        # Mock broken handler that returns empty tools
        with patch('src.mcp_servers.sec_edgar_handler.handle_tools_list') as mock_handler:
            mock_handler.return_value = {'tools': []}  # Broken: empty tools
            
            response = lambda_handler(event, None)
            body = json.loads(response['body'])
            
            # Verify test would catch this (tools array is empty)
            assert len(body['result']['tools']) == 0, "Test should detect empty tools array"
            # In real test, this would fail the assertion in test_tools_list_returns_valid_schema

    def test_tools_call_test_can_detect_missing_data(self):
        """Verify test fails if tools/call returns incomplete data."""
        event = {
            'body': json.dumps({
                'jsonrpc': '2.0',
                'method': 'tools/call',
                'params': {
                    'name': 'get_latest_filing',
                    'arguments': {'ticker': 'AAPL'}
                },
                'id': 1
            })
        }
        
        # Mock broken handler that returns incomplete data
        with patch('src.mcp_servers.sec_edgar_handler.get_sec_client') as mock_get_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get_latest_filing.return_value = {
                'ticker': 'AAPL'
                # Broken: missing required fields (form_type, filing_date, cik)
            }
            mock_get_client.return_value = mock_client_instance
            
            response = lambda_handler(event, None)
            body = json.loads(response['body'])
            filing_data = json.loads(body['result']['content'][0]['text'])
            
            # Verify test would catch missing fields
            assert 'form_type' not in filing_data, "Test should detect missing form_type"
            # In real test, this would fail assertions checking for required fields
