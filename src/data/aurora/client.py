# -*- coding: utf-8 -*-
"""
Aurora MySQL Client

Connection management for Aurora MySQL Serverless v2 with:
- Connection pooling for Lambda warm starts
- Secrets Manager integration for credentials
- Automatic reconnection handling
"""

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

import boto3
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)

# Module-level singleton for connection reuse
_aurora_client: Optional['AuroraClient'] = None


def get_aurora_client() -> 'AuroraClient':
    """Get or create global Aurora client singleton.

    Returns:
        AuroraClient: Singleton instance for database operations

    Example:
        >>> client = get_aurora_client()
        >>> with client.get_connection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT 1")
    """
    global _aurora_client
    if _aurora_client is None:
        _aurora_client = AuroraClient()
    return _aurora_client


class AuroraClient:
    """Aurora MySQL connection client with connection pooling.

    Attributes:
        host: Database hostname
        port: Database port
        database: Database name
        user: Database username

    Example:
        >>> client = AuroraClient()
        >>> with client.get_connection() as conn:
        ...     with conn.cursor() as cursor:
        ...         cursor.execute("SELECT * FROM ticker_info LIMIT 10")
        ...         results = cursor.fetchall()
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 3306,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secret_arn: Optional[str] = None,
    ):
        """Initialize Aurora client.

        Args:
            host: Database host (or env AURORA_HOST)
            port: Database port (default 3306)
            database: Database name (or env AURORA_DATABASE)
            user: Database user (or env AURORA_USER)
            password: Database password (or env AURORA_PASSWORD)
            secret_arn: AWS Secrets Manager ARN for credentials (or env AURORA_SECRET_ARN)
        """
        self.secret_arn = secret_arn or os.environ.get('AURORA_SECRET_ARN')

        # If secret ARN provided, fetch credentials from Secrets Manager
        if self.secret_arn:
            credentials = self._get_credentials_from_secrets_manager()
            self.host = credentials.get('host')
            self.port = credentials.get('port', 3306)
            self.database = credentials.get('database')
            self.user = credentials.get('username')
            self.password = credentials.get('password')
        else:
            # Use provided values or environment variables
            self.host = host or os.environ.get('AURORA_HOST')
            self.port = port or int(os.environ.get('AURORA_PORT', '3306'))
            self.database = database or os.environ.get('AURORA_DATABASE', 'ticker_data')
            self.user = user or os.environ.get('AURORA_USER', 'admin')
            self.password = password or os.environ.get('AURORA_PASSWORD')

        # Connection pool (simple list for Lambda)
        self._connection: Optional[pymysql.Connection] = None

        logger.info(f"Aurora client initialized for {self.host}:{self.port}/{self.database}")

    def _get_credentials_from_secrets_manager(self) -> Dict[str, Any]:
        """Fetch database credentials from AWS Secrets Manager.

        Returns:
            Dict with host, port, database, username, password
        """
        client = boto3.client('secretsmanager')
        try:
            response = client.get_secret_value(SecretId=self.secret_arn)
            secret = json.loads(response['SecretString'])
            logger.info(f"Fetched credentials from Secrets Manager: {self.secret_arn}")
            return secret
        except Exception as e:
            logger.error(f"Failed to fetch credentials from Secrets Manager: {e}")
            raise

    def _create_connection(self) -> pymysql.Connection:
        """Create a new database connection.

        Returns:
            pymysql.Connection: New database connection

        Raises:
            pymysql.Error: If connection fails
        """
        if not self.host:
            raise ValueError("Aurora host not configured. Set AURORA_HOST or AURORA_SECRET_ARN")

        if not self.password:
            raise ValueError("Aurora password not configured. Set AURORA_PASSWORD or AURORA_SECRET_ARN")

        logger.info(f"Creating connection to Aurora: {self.host}:{self.port}/{self.database}")

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
        )

    @contextmanager
    def get_connection(self) -> Generator[pymysql.Connection, None, None]:
        """Get a database connection (reuses existing if valid).

        Yields:
            pymysql.Connection: Database connection

        Example:
            >>> with client.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT 1")
        """
        # Check if existing connection is valid
        connection_valid = False
        if self._connection is not None:
            try:
                self._connection.ping(reconnect=True)
                connection_valid = True
            except pymysql.Error:
                logger.warning("Existing connection invalid, creating new one")
                try:
                    self._connection.close()
                except Exception:
                    pass
                self._connection = None

        # Create new connection if needed
        if not connection_valid:
            self._connection = self._create_connection()

        try:
            yield self._connection
        except Exception:
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass
            raise
        # Don't close - keep for reuse in Lambda

    def execute(
        self,
        query: str,
        params: Optional[tuple] = None,
        commit: bool = True
    ) -> int:
        """Execute a single query (INSERT, UPDATE, DELETE).

        Args:
            query: SQL query string
            params: Query parameters
            commit: Whether to commit after execution

        Returns:
            Number of affected rows

        Example:
            >>> client.execute(
            ...     "INSERT INTO ticker_info (symbol, display_name) VALUES (%s, %s)",
            ...     ('NVDA', 'NVIDIA')
            ... )
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if commit:
                    conn.commit()
                return cursor.rowcount

    def execute_many(
        self,
        query: str,
        params_list: list,
        commit: bool = True
    ) -> int:
        """Execute query with multiple parameter sets (batch insert).

        Args:
            query: SQL query string
            params_list: List of parameter tuples
            commit: Whether to commit after execution

        Returns:
            Number of affected rows

        Example:
            >>> client.execute_many(
            ...     "INSERT INTO daily_prices (symbol, price_date, close) VALUES (%s, %s, %s)",
            ...     [('NVDA', '2025-01-01', 150.0), ('NVDA', '2025-01-02', 152.0)]
            ... )
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                if commit:
                    conn.commit()
                return cursor.rowcount

    def fetch_one(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Dict with column names as keys, or None if not found

        Example:
            >>> result = client.fetch_one(
            ...     "SELECT * FROM ticker_info WHERE symbol = %s",
            ...     ('NVDA',)
            ... )
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()

    def fetch_all(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> list:
        """Fetch all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dicts with column names as keys

        Example:
            >>> results = client.fetch_all(
            ...     "SELECT * FROM ticker_info WHERE market = %s",
            ...     ('us_market',)
            ... )
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def close(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
                logger.info("Aurora connection closed")
            except Exception as e:
                logger.warning(f"Error closing Aurora connection: {e}")
            finally:
                self._connection = None

    def health_check(self) -> Dict[str, Any]:
        """Check database connectivity.

        Returns:
            Dict with status and details

        Example:
            >>> health = client.health_check()
            >>> print(health['status'])  # 'healthy' or 'unhealthy'
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 as health, NOW() as server_time")
                    result = cursor.fetchone()
                    return {
                        'status': 'healthy',
                        'host': self.host,
                        'database': self.database,
                        'server_time': str(result['server_time']) if result else None
                    }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'host': self.host,
                'database': self.database,
                'error': str(e)
            }
