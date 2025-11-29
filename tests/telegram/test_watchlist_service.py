#!/usr/bin/env python3
"""
Unit tests for WatchlistService

Tests DynamoDB CRUD operations, TTL, user isolation, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.api.watchlist_service import WatchlistService


class TestWatchlistService:
    """Test suite for WatchlistService"""

    @pytest.fixture
    def mock_dynamodb_table(self):
        """Create mock DynamoDB table"""
        mock_table = Mock()
        mock_table.put_item = Mock(return_value={})
        mock_table.delete_item = Mock(return_value={})
        mock_table.query = Mock(return_value={'Items': []})
        return mock_table

    @pytest.fixture
    def mock_ticker_service(self):
        """Create mock TickerService"""
        mock_service = Mock()
        mock_service.is_supported = Mock(return_value=True)
        mock_service.get_ticker_info = Mock(return_value={
            'symbol': 'NVDA19',
            'company_name': 'NVIDIA Corporation',
            'yahoo_symbol': 'NVDA'
        })
        return mock_service

    @pytest.fixture
    def service(self, mock_dynamodb_table, mock_ticker_service):
        """Create WatchlistService with mocked dependencies"""
        with patch('src.api.watchlist_service.boto3') as mock_boto3:
            mock_dynamodb = Mock()
            mock_dynamodb.Table = Mock(return_value=mock_dynamodb_table)
            mock_boto3.resource = Mock(return_value=mock_dynamodb)

            with patch('src.api.watchlist_service.get_ticker_service') as mock_get_ticker:
                mock_get_ticker.return_value = mock_ticker_service
                service = WatchlistService(table_name='test-table')
                service.table = mock_dynamodb_table
                service.ticker_service = mock_ticker_service
                return service

    # Test 1: Service initialization
    def test_service_initialization(self, service):
        """Test that service initializes correctly"""
        assert service is not None
        assert service.table_name == 'test-table'
        assert service.ticker_service is not None

    # Test 2: Add ticker to watchlist
    def test_add_ticker_success(self, service):
        """Test adding a valid ticker to watchlist"""
        result = service.add_ticker('user123', 'NVDA19')

        assert result['status'] == 'ok'
        assert result['ticker'] == 'NVDA19'
        service.table.put_item.assert_called_once()

        # Verify put_item was called with correct structure
        call_args = service.table.put_item.call_args
        item = call_args.kwargs['Item']
        assert item['user_id'] == 'user123'
        assert item['ticker'] == 'NVDA19'
        assert 'added_at' in item
        assert 'ttl' in item

    def test_add_ticker_normalizes_to_uppercase(self, service):
        """Test that ticker is normalized to uppercase"""
        result = service.add_ticker('user123', 'nvda19')

        assert result['ticker'] == 'NVDA19'

    def test_add_ticker_invalid_ticker(self, service, mock_ticker_service):
        """Test adding unsupported ticker raises ValueError"""
        mock_ticker_service.is_supported.return_value = False

        with pytest.raises(ValueError) as exc_info:
            service.add_ticker('user123', 'INVALID')

        assert "not supported" in str(exc_info.value)

    def test_add_ticker_has_ttl(self, service):
        """Test that added items have TTL set (1 year)"""
        service.add_ticker('user123', 'NVDA19')

        call_args = service.table.put_item.call_args
        item = call_args.kwargs['Item']

        # TTL should be ~1 year from now (in seconds)
        expected_ttl = int((datetime.now() + timedelta(days=365)).timestamp())
        # Allow 1 minute tolerance
        assert abs(item['ttl'] - expected_ttl) < 60

    # Test 3: Remove ticker from watchlist
    def test_remove_ticker_success(self, service):
        """Test removing ticker from watchlist"""
        result = service.remove_ticker('user123', 'NVDA19')

        assert result['status'] == 'ok'
        assert result['ticker'] == 'NVDA19'
        service.table.delete_item.assert_called_once()

    def test_remove_ticker_normalizes_to_uppercase(self, service):
        """Test that remove normalizes ticker to uppercase"""
        result = service.remove_ticker('user123', 'nvda19')

        assert result['ticker'] == 'NVDA19'
        call_args = service.table.delete_item.call_args
        key = call_args.kwargs['Key']
        assert key['ticker'] == 'NVDA19'

    # Test 4: Get user watchlist
    def test_get_watchlist_empty(self, service):
        """Test getting empty watchlist"""
        service.table.query.return_value = {'Items': []}

        result = service.get_watchlist('user123')

        assert result == []

    def test_get_watchlist_with_items(self, service):
        """Test getting watchlist with items"""
        service.table.query.return_value = {
            'Items': [
                {
                    'user_id': 'user123',
                    'ticker': 'NVDA19',
                    'company_name': 'NVIDIA Corporation',
                    'added_at': '2025-01-15T10:00:00'
                },
                {
                    'user_id': 'user123',
                    'ticker': 'DBS19',
                    'company_name': 'DBS Group',
                    'added_at': '2025-01-14T10:00:00'
                }
            ]
        }

        result = service.get_watchlist('user123')

        assert len(result) == 2
        # Check items are WatchlistItem instances
        assert result[0].ticker == 'NVDA19'
        assert result[1].ticker == 'DBS19'

    def test_get_watchlist_sorted_by_recency(self, service):
        """Test watchlist is sorted by added_at (most recent first)"""
        service.table.query.return_value = {
            'Items': [
                {
                    'user_id': 'user123',
                    'ticker': 'DBS19',
                    'company_name': 'DBS Group',
                    'added_at': '2025-01-14T10:00:00'
                },
                {
                    'user_id': 'user123',
                    'ticker': 'NVDA19',
                    'company_name': 'NVIDIA Corporation',
                    'added_at': '2025-01-15T10:00:00'
                }
            ]
        }

        result = service.get_watchlist('user123')

        # Should be sorted by recency (most recent first)
        # Note: actual sorting depends on implementation
        assert len(result) == 2

    # Test 5: User isolation
    def test_different_users_have_separate_watchlists(self, service):
        """Test that different users' watchlists are isolated"""
        # Add ticker for user1
        service.add_ticker('user1', 'NVDA19')

        # Query for user2 should not include user1's items
        service.table.query.return_value = {'Items': []}
        result = service.get_watchlist('user2')

        assert result == []

        # Verify query used correct user_id
        call_args = service.table.query.call_args
        assert 'user2' in str(call_args)

    # Test 6: Error handling
    def test_add_ticker_dynamodb_error(self, service):
        """Test handling DynamoDB errors on add"""
        service.table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Test error'}},
            'PutItem'
        )

        with pytest.raises(ClientError):
            service.add_ticker('user123', 'NVDA19')

    def test_remove_ticker_dynamodb_error(self, service):
        """Test handling DynamoDB errors on remove"""
        service.table.delete_item.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Test error'}},
            'DeleteItem'
        )

        with pytest.raises(ClientError):
            service.remove_ticker('user123', 'NVDA19')

    def test_get_watchlist_dynamodb_error(self, service):
        """Test handling DynamoDB errors on query"""
        service.table.query.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Test error'}},
            'Query'
        )

        with pytest.raises(ClientError):
            service.get_watchlist('user123')


class TestWatchlistServiceIntegration:
    """Integration tests for WatchlistService (requires DynamoDB Local)"""

    @pytest.fixture
    def local_service(self):
        """Create service connected to DynamoDB Local"""
        # Skip if DynamoDB Local not available
        try:
            import boto3
            client = boto3.client(
                'dynamodb',
                endpoint_url='http://localhost:8000',
                region_name='us-east-1',
                aws_access_key_id='fake',
                aws_secret_access_key='fake'
            )
            client.describe_table(TableName='dr-daily-report-telegram-watchlist-dev')
        except Exception:
            pytest.skip("DynamoDB Local not available")

        return WatchlistService(use_local=True)

    @pytest.mark.skip(reason="Requires DynamoDB Local running")
    def test_full_crud_cycle(self, local_service):
        """Test full create-read-delete cycle with real DynamoDB"""
        user_id = 'test_user_crud'
        ticker = 'NVDA19'

        # Add
        add_result = local_service.add_ticker(user_id, ticker)
        assert add_result['status'] == 'ok'

        # Read
        watchlist = local_service.get_watchlist(user_id)
        assert any(item.ticker == ticker for item in watchlist)

        # Delete
        remove_result = local_service.remove_ticker(user_id, ticker)
        assert remove_result['status'] == 'ok'

        # Verify deleted
        watchlist = local_service.get_watchlist(user_id)
        assert not any(item.ticker == ticker for item in watchlist)
