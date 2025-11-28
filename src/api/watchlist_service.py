"""Watchlist service for DynamoDB operations"""

import os
import boto3
from datetime import datetime, timedelta
from typing import Optional
import logging

from .models import WatchlistItem
from .ticker_service import get_ticker_service

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for managing user watchlists in DynamoDB"""

    def __init__(self, table_name: str | None = None, use_local: bool = False):
        """Initialize watchlist service

        Args:
            table_name: DynamoDB table name (defaults to env var)
            use_local: If True, use local DynamoDB for testing
        """
        if table_name is None:
            table_name = os.getenv(
                "WATCHLIST_TABLE_NAME",
                "dr-daily-report-telegram-watchlist-dev"
            )

        self.table_name = table_name

        # Configure DynamoDB client
        if use_local:
            # For local testing with DynamoDB Local
            # Uses credentials from environment (doppler provides these)
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url='http://localhost:8000',
                region_name='ap-southeast-1'
            )
        else:
            # Production AWS DynamoDB
            self.dynamodb = boto3.resource('dynamodb')

        self.table = self.dynamodb.Table(table_name)
        self.ticker_service = get_ticker_service()

    def add_ticker(self, user_id: str, ticker: str) -> dict:
        """Add ticker to user's watchlist

        Args:
            user_id: Telegram user ID
            ticker: Ticker symbol (e.g., NVDA19)

        Returns:
            Dict with operation result

        Raises:
            ValueError: If ticker is not supported
        """
        # Validate ticker
        ticker_upper = ticker.upper()
        if not self.ticker_service.is_supported(ticker_upper):
            raise ValueError(f"Ticker '{ticker}' is not supported")

        # Get ticker info
        ticker_info = self.ticker_service.get_ticker_info(ticker_upper)
        company_name = ticker_info['company_name']

        # Add to DynamoDB
        item = {
            'user_id': user_id,
            'ticker': ticker_upper,
            'company_name': company_name,
            'added_at': datetime.now().isoformat(),
            'ttl': int((datetime.now() + timedelta(days=365)).timestamp())  # 1 year TTL
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Added {ticker_upper} to watchlist for user {user_id}")
            return {'status': 'ok', 'ticker': ticker_upper}

        except Exception as e:
            logger.error(f"Failed to add {ticker_upper} to watchlist: {e}")
            raise

    def remove_ticker(self, user_id: str, ticker: str) -> dict:
        """Remove ticker from user's watchlist

        Args:
            user_id: Telegram user ID
            ticker: Ticker symbol

        Returns:
            Dict with operation result
        """
        ticker_upper = ticker.upper()

        try:
            self.table.delete_item(
                Key={
                    'user_id': user_id,
                    'ticker': ticker_upper
                }
            )
            logger.info(f"Removed {ticker_upper} from watchlist for user {user_id}")
            return {'status': 'ok', 'ticker': ticker_upper}

        except Exception as e:
            logger.error(f"Failed to remove {ticker_upper} from watchlist: {e}")
            raise

    def get_watchlist(self, user_id: str) -> list[WatchlistItem]:
        """Get user's complete watchlist

        Args:
            user_id: Telegram user ID

        Returns:
            List of WatchlistItem objects
        """
        try:
            response = self.table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':uid': user_id
                }
            )

            items = []
            for item in response.get('Items', []):
                items.append(WatchlistItem(
                    ticker=item['ticker'],
                    company_name=item['company_name'],
                    added_at=datetime.fromisoformat(item['added_at'])
                ))

            # Sort by most recently added
            items.sort(key=lambda x: x.added_at, reverse=True)

            logger.info(f"Retrieved {len(items)} watchlist items for user {user_id}")
            return items

        except Exception as e:
            logger.error(f"Failed to get watchlist for user {user_id}: {e}")
            raise

    def is_in_watchlist(self, user_id: str, ticker: str) -> bool:
        """Check if ticker is in user's watchlist

        Args:
            user_id: Telegram user ID
            ticker: Ticker symbol

        Returns:
            True if ticker is in watchlist
        """
        ticker_upper = ticker.upper()

        try:
            response = self.table.get_item(
                Key={
                    'user_id': user_id,
                    'ticker': ticker_upper
                }
            )
            return 'Item' in response

        except Exception as e:
            logger.error(f"Failed to check watchlist status: {e}")
            return False

    def get_watchlist_count(self, user_id: str) -> int:
        """Get count of tickers in user's watchlist

        Args:
            user_id: Telegram user ID

        Returns:
            Number of tickers in watchlist
        """
        try:
            response = self.table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':uid': user_id
                },
                Select='COUNT'
            )
            return response['Count']

        except Exception as e:
            logger.error(f"Failed to get watchlist count: {e}")
            return 0


# Global watchlist service instance
_watchlist_service: WatchlistService | None = None


def get_watchlist_service(use_local: bool | None = None) -> WatchlistService:
    """Get or create global watchlist service instance

    Args:
        use_local: If True, use local DynamoDB for testing.
                   If None, checks USE_LOCAL_DYNAMODB env var.

    Returns:
        WatchlistService instance
    """
    global _watchlist_service
    if _watchlist_service is None:
        # Check environment variable if use_local not explicitly set
        if use_local is None:
            use_local = os.getenv('USE_LOCAL_DYNAMODB', 'false').lower() == 'true'

        _watchlist_service = WatchlistService(use_local=use_local)
    return _watchlist_service
