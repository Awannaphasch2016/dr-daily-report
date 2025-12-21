# -*- coding: utf-8 -*-
"""
Lambda handler for query and debug operations (Utility Layer).

Single Responsibility: Execute SQL queries, inspect schema, and debug data.

Triggered by: Manual invocation (CI/CD, debugging)

Actions:
- query: Execute SQL queries
- describe_table: Get table schema (for CI/CD validation)
- query_precomputed: Query precomputed indicators and reports
- debug_cache: Debug cached reports
- debug_prices: Debug price data
"""

import json
import logging
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def json_converter(obj):
    """
    Convert non-JSON-serializable types to JSON-compatible types.

    Required for Aurora query results that contain:
    - datetime.date → ISO string
    - datetime.datetime → ISO string
    - decimal.Decimal → float
    - bytes → base64 string

    This prevents "Object of type date is not JSON serializable" errors
    when Lambda marshals the response.
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        import base64
        return base64.b64encode(obj).decode('utf-8')

    # Fallback - let json.dumps raise TypeError with helpful message
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def convert_for_json(data):
    """
    Recursively convert data structure to JSON-serializable types.

    Lambda runtime auto-serializes response dict to JSON, but doesn't accept
    custom converters. This function pre-processes data to ensure all types
    are JSON-compatible before returning from Lambda handler.

    Args:
        data: Dict, list, or primitive value from Aurora query

    Returns:
        JSON-serializable version of data
    """
    if isinstance(data, dict):
        return {k: convert_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_for_json(item) for item in data]
    elif isinstance(data, (date, datetime, Decimal, bytes)):
        return json_converter(data)
    else:
        return data


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle query and debug operations.

    Event format:
        {
            "action": "query|describe_table|query_precomputed|debug_cache|debug_prices",
            ...  # Action-specific parameters
        }

    Args:
        event: Lambda event with 'action' field
        context: Lambda context

    Returns:
        Response dict with query results
    """
    start_time = datetime.now()
    action = event.get('action', 'query')  # Default action

    logger.info(f"Query Tool Lambda invoked at {start_time.isoformat()}")
    logger.info(f"Action: {action}")
    logger.info(f"Event: {json.dumps(event)}")

    # Route to appropriate handler
    handlers = {
        'query': _handle_query,
        'describe_table': _handle_describe_table,
        'query_precomputed': _handle_query_precomputed,
        'debug_cache': _handle_debug_cache,
        'debug_prices': _handle_debug_prices
    }

    handler = handlers.get(action)
    if not handler:
        return {
            'statusCode': 400,
            'body': {
                'message': f'Unknown action: {action}',
                'error': f'Valid actions: {", ".join(handlers.keys())}'
            }
        }

    try:
        return handler(event, start_time)
    except Exception as e:
        logger.error(f"Query tool failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': f'Query tool action {action} failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_query(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Execute SQL query and return results.

    Args:
        event: Lambda event with required param:
            - sql: SQL query to execute (e.g., "SHOW TABLES")
        start_time: When the Lambda was invoked

    Returns:
        Response dict with query results

    Example usage:
        aws lambda invoke \\
          --function-name dr-daily-report-query-tool-dev \\
          --payload '{"action":"query","sql":"SHOW TABLES"}' \\
          /tmp/tables.json
    """
    try:
        # Lazy import
        from src.data.aurora.client import get_aurora_client

        sql = event.get('sql')
        if not sql:
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Missing required parameter: sql',
                    'error': 'Must provide SQL query'
                }
            }

        client = get_aurora_client()
        logger.info(f"Executing query: {sql[:100]}...")

        result = client.fetch_all(sql, ())

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(f"Query completed: {len(result)} rows in {duration_seconds:.2f}s")

        # Convert date/datetime objects to JSON-serializable ISO strings
        # This prevents "Object of type date is not JSON serializable" errors
        # when Lambda runtime marshals the response
        json_safe_result = convert_for_json(result)

        return {
            'statusCode': 200,
            'body': {
                'message': 'Query executed successfully',
                'sql': sql,
                'row_count': len(result),
                'results': json_safe_result,
                'duration_seconds': duration_seconds
            }
        }

    except Exception as e:
        logger.error(f"Query failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Query failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_describe_table(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Query Aurora table schema for CI/CD schema validation.

    Args:
        event: Lambda event with required param:
            - table: Table name to describe (e.g., "precomputed_reports")
        start_time: When the Lambda was invoked

    Returns:
        Response dict with schema info

    Example usage (from CI/CD):
        aws lambda invoke \\
          --function-name dr-daily-report-query-tool-dev \\
          --payload '{"action":"describe_table","table":"precomputed_reports"}' \\
          /tmp/schema.json
    """
    try:
        # Lazy import
        from src.data.aurora.client import get_aurora_client

        table_name = event.get('table')
        if not table_name:
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Missing required parameter: table',
                    'error': 'Must provide table name to describe'
                }
            }

        client = get_aurora_client()

        # Query table schema using DESCRIBE (MySQL DDL command)
        query = f"DESCRIBE {table_name}"
        logger.info(f"Querying schema for table: {table_name}")

        result = client.fetch_all(query, ())

        # Transform to dict: {column_name: {Type, Null, Key, ...}}
        schema = {}
        for row in result:
            col_name = row['Field']
            schema[col_name] = {
                'Type': row['Type'],
                'Null': row['Null'],
                'Key': row.get('Key', ''),
                'Default': row.get('Default'),
                'Extra': row.get('Extra', '')
            }

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        logger.info(f"Schema query completed: {len(schema)} columns in {table_name}")

        return {
            'statusCode': 200,
            'body': {
                'message': f'Schema retrieved for {table_name}',
                'table': table_name,
                'column_count': len(schema),
                'schema': schema,
                'duration_seconds': duration_seconds
            }
        }

    except Exception as e:
        logger.error(f"Schema query failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Schema query failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_query_precomputed(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Query precomputed indicators, percentiles, and comparative features.

    Args:
        event: Lambda event with required param:
            - symbol: Ticker symbol to query (e.g., 'DBS19')
        start_time: When the Lambda was invoked

    Returns:
        Response dict with precomputed data
    """
    try:
        # Lazy imports
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.precompute_service import PrecomputeService
        from src.data.aurora.ticker_resolver import get_ticker_resolver

        symbol = event.get('symbol')
        if not symbol:
            return {
                'statusCode': 400,
                'body': {'error': 'Missing required parameter: symbol'}
            }

        client = get_aurora_client()
        service = PrecomputeService()
        resolver = get_ticker_resolver()

        # Resolve symbol
        ticker_info = resolver.resolve(symbol)
        if not ticker_info:
            return {
                'statusCode': 404,
                'body': {'error': f'Ticker {symbol} not found'}
            }

        # Get precomputed data
        indicators = service.get_latest_indicators(symbol)
        percentiles = service.get_latest_percentiles(symbol)

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'message': f'Precomputed data retrieved for {symbol}',
                'symbol': symbol,
                'indicators': convert_for_json(indicators),
                'percentiles': convert_for_json(percentiles),
                'duration_seconds': duration_seconds
            }
        }

    except Exception as e:
        logger.error(f"Precomputed query failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Precomputed query failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_debug_cache(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Debug cached reports in precomputed_reports table.

    Args:
        event: Lambda event with optional params:
            - symbol: Check specific symbol's cached report
            - date: Date to check (default: today)
            - limit: Max reports to return (default: 10)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with cached reports info
    """
    try:
        # Lazy imports
        from src.data.aurora.client import get_aurora_client
        from src.data.aurora.precompute_service import PrecomputeService

        client = get_aurora_client()
        service = PrecomputeService()

        symbol = event.get('symbol')
        # TIMEZONE FIX: Use UTC date to match Aurora timezone (Aurora runs in UTC)
        check_date = event.get('date', str(datetime.utcnow().date()))
        limit = event.get('limit', 10)

        if symbol:
            # Check specific symbol's cached report
            cached = service.get_cached_report(symbol, date.fromisoformat(check_date))
            if cached:
                return {
                    'statusCode': 200,
                    'body': convert_for_json({
                        'message': f'Cache HIT for {symbol}',
                        'symbol': symbol,
                        'date': check_date,
                        'report_id': cached.get('id'),
                        'ticker_master_id': cached.get('ticker_master_id'),
                        'status': cached.get('status'),
                        'report_text_length': len(cached.get('report_text', '')),
                        'has_chart': bool(cached.get('chart_base64')),
                        'generated_at': cached.get('report_generated_at'),
                    })
                }
            else:
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f'Cache MISS for {symbol}',
                        'symbol': symbol,
                        'date': check_date,
                    }
                }
        else:
            # List all cached reports for the date
            query = """
                SELECT * FROM precomputed_reports
                WHERE report_date = %s
                ORDER BY id DESC
                LIMIT %s
            """
            reports = client.fetch_all(query, (check_date, limit))

            # Build report summaries
            report_summaries = []
            for r in reports:
                summary = {
                    'id': r.get('id'),
                    'symbol': r.get('symbol'),
                    'report_date': r.get('report_date'),
                    'status': r.get('status'),
                    'has_report_text': bool(r.get('report_text')),
                    'has_chart': bool(r.get('chart_base64'))
                }
                report_summaries.append(summary)

            return {
                'statusCode': 200,
                'body': convert_for_json({
                    'message': f'Found {len(report_summaries)} cached reports for {check_date}',
                    'date': check_date,
                    'count': len(report_summaries),
                    'reports': report_summaries
                })
            }

    except Exception as e:
        logger.error(f"Debug cache failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Debug cache failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


def _handle_debug_prices(event: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
    """Debug price data in prices table.

    Args:
        event: Lambda event with optional params:
            - symbol: Check specific symbol's price data
            - limit: Max rows to return (default: 10)
        start_time: When the Lambda was invoked

    Returns:
        Response dict with price data info
    """
    try:
        # Lazy import
        from src.data.aurora.client import get_aurora_client

        client = get_aurora_client()

        symbol = event.get('symbol')
        limit = event.get('limit', 10)

        if symbol:
            # Check specific symbol's price data
            query = """
                SELECT * FROM prices
                WHERE symbol = %s
                ORDER BY price_date DESC
                LIMIT %s
            """
            prices = client.fetch_all(query, (symbol, limit))

            return {
                'statusCode': 200,
                'body': convert_for_json({
                    'message': f'Found {len(prices)} price records for {symbol}',
                    'symbol': symbol,
                    'count': len(prices),
                    'prices': prices
                })
            }
        else:
            # Get summary of all price data
            summary_query = """
                SELECT
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(*) as total_records,
                    MIN(price_date) as earliest_date,
                    MAX(price_date) as latest_date
                FROM prices
            """
            summary = client.fetch_all(summary_query, ())

            return {
                'statusCode': 200,
                'body': convert_for_json({
                    'message': 'Price data summary',
                    'summary': summary[0] if summary else {}
                })
            }

    except Exception as e:
        logger.error(f"Debug prices failed: {e}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'body': {
                'message': 'Debug prices failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        }


# For local testing
if __name__ == '__main__':
    # Test query
    test_event = {
        'action': 'query',
        'sql': 'SELECT COUNT(*) as total FROM ticker_info;'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
