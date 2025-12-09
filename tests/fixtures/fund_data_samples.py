"""
Test fixtures for Fund Data Sync ETL integration tests.

Based on comprehensive schema validation of real S3 data (2025-12-09):
- Encoding: ASCII (100% confidence)
- Columns: 8 UPPERCASE columns (D_TRADE, STOCK, TICKER, COL_CODE, VALUE_NUMERIC, VALUE_TEXT, SOURCE, UPDATED_AT)
- Total rows: 5,474 (39 unique stocks, 7 COL_CODEs)
- VALUE_NUMERIC: 79.5% populated, range -270.95 to 123,504.55
- VALUE_TEXT: 14.3% populated, 29 unique values
- SOURCE: 0% populated (always empty)
- UPDATED_AT: 100% populated

This ensures test fixtures accurately represent production data.
"""

from decimal import Decimal
from datetime import date


# Sample CSV content matching real SQL Server export schema
# CRITICAL: UPPERCASE column names (SQL Server export pattern)
SAMPLE_CSV_UPPERCASE = """D_TRADE,STOCK,TICKER,COL_CODE,VALUE_NUMERIC,VALUE_TEXT,SOURCE,UPDATED_AT
2025-12-09,DBS19,DBSM.SI,FY1_DIV_YIELD,4.22456920511395,,,2025-12-09 08:01:06
2025-12-09,DBS19,DBSM.SI,FY1_PE,14.32,,,2025-12-09 08:01:06
2025-12-09,DBS19,DBSM.SI,SECTOR,,Banking,,2025-12-09 08:01:06
2025-12-09,NVDA19,NVDA,FY1_DIV_YIELD,0.05,,,2025-12-09 08:01:06
2025-12-09,NVDA19,NVDA,FY1_EPS,15.23,,,2025-12-09 08:01:06
"""

# Sample with mixed numeric and text values (reflects real 79.5% / 14.3% distribution)
SAMPLE_CSV_MIXED_VALUES = """D_TRADE,STOCK,TICKER,COL_CODE,VALUE_NUMERIC,VALUE_TEXT,SOURCE,UPDATED_AT
2025-12-09,DBS19,DBSM.SI,FY1_DIV_YIELD,4.22456920511395,,,2025-12-09 08:01:06
2025-12-09,DBS19,DBSM.SI,SECTOR,,Banking,,2025-12-09 08:01:06
2025-12-09,DBS19,DBSM.SI,RATING,,Buy,,2025-12-09 08:01:06
2025-12-09,TENCENT19,0700.HK,FY1_DIV_YIELD,0.743964296494557,,,2025-12-09 08:01:06
2025-12-09,TENCENT19,0700.HK,SECTOR,,Interactive Media & Services,,2025-12-09 08:01:06
2025-12-09,TENCENT19,0700.HK,FY1_PE,19.6493026985685,,,2025-12-09 08:01:06
"""

# Invalid CSV - missing required columns (for error testing)
INVALID_CSV_MISSING_COLUMNS = """D_TRADE,STOCK,VALUE_NUMERIC
2025-12-09,DBS19,4.22
2025-12-09,NVDA19,15.23
"""

# Invalid CSV - malformed date (for error testing)
INVALID_CSV_BAD_DATE = """D_TRADE,STOCK,TICKER,COL_CODE,VALUE_NUMERIC,VALUE_TEXT,SOURCE,UPDATED_AT
invalid-date,DBS19,DBSM.SI,FY1_DIV_YIELD,4.22,,,2025-12-09 08:01:06
2025-12-09,NVDA19,NVDA,FY1_EPS,15.23,,,2025-12-09 08:01:06
"""

# Empty CSV (only header, no data rows - for error testing)
EMPTY_CSV = """D_TRADE,STOCK,TICKER,COL_CODE,VALUE_NUMERIC,VALUE_TEXT,SOURCE,UPDATED_AT
"""

# CSV with extreme numeric values (from real data range: -270.95 to 123,504.55)
SAMPLE_CSV_EXTREME_VALUES = """D_TRADE,STOCK,TICKER,COL_CODE,VALUE_NUMERIC,VALUE_TEXT,SOURCE,UPDATED_AT
2025-12-09,TEST01,TEST.SI,LOSS,-270.95,,,2025-12-09 08:01:06
2025-12-09,TEST02,TEST2.SI,HIGH_VALUE,123504.55,,,2025-12-09 08:01:06
2025-12-09,TEST03,TEST3.SI,ZERO,0,,,2025-12-09 08:01:06
2025-12-09,TEST04,TEST4.SI,SMALL,0.001,,,2025-12-09 08:01:06
"""


# Expected parsed records (for validation in tests)
EXPECTED_DBS19_RECORDS = [
    {
        'd_trade': date(2025, 12, 9),
        'stock': 'DBS19',
        'ticker': 'DBSM.SI',
        'col_code': 'FY1_DIV_YIELD',
        'value_numeric': Decimal('4.22456920511395'),
        'value_text': None,
        's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_test.csv'
    },
    {
        'd_trade': date(2025, 12, 9),
        'stock': 'DBS19',
        'ticker': 'DBSM.SI',
        'col_code': 'FY1_PE',
        'value_numeric': Decimal('14.32'),
        'value_text': None,
        's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_test.csv'
    },
    {
        'd_trade': date(2025, 12, 9),
        'stock': 'DBS19',
        'ticker': 'DBSM.SI',
        'col_code': 'SECTOR',
        'value_numeric': None,
        'value_text': 'Banking',
        's3_source_key': 'raw/sql_server/fund_data/2025-12-09/fund_data_test.csv'
    }
]


def get_sample_s3_event(bucket_name: str, s3_key: str) -> dict:
    """Generate mock S3 ObjectCreated event.

    Matches AWS S3 event structure for ObjectCreated:Put events.

    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key

    Returns:
        S3 event dict matching AWS event structure

    Example:
        >>> event = get_sample_s3_event('data-lake-dev', 'raw/fund_data.csv')
        >>> event['Records'][0]['eventName']
        'ObjectCreated:Put'
    """
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "ap-southeast-1",
                "eventTime": "2025-12-09T08:38:29.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {
                    "principalId": "AWS:AIDAI123456789"
                },
                "requestParameters": {
                    "sourceIPAddress": "203.0.113.1"
                },
                "responseElements": {
                    "x-amz-request-id": "ABC123",
                    "x-amz-id-2": "XYZ789"
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "fund-data-csv-upload",
                    "bucket": {
                        "name": bucket_name,
                        "ownerIdentity": {
                            "principalId": "A1234567890"
                        },
                        "arn": f"arn:aws:s3:::{bucket_name}"
                    },
                    "object": {
                        "key": s3_key,
                        "size": 381109,
                        "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                        "sequencer": "0061C5F4E5D8B9E123"
                    }
                }
            }
        ]
    }


def get_sample_sqs_message(bucket_name: str, s3_key: str, message_id: str = "msg-001") -> dict:
    """Generate mock SQS message containing S3 event.

    Matches AWS SQS message structure when S3 sends to SQS queue.

    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key
        message_id: SQS message ID

    Returns:
        SQS message dict for Lambda handler

    Example:
        >>> msg = get_sample_sqs_message('bucket', 'file.csv', 'msg-123')
        >>> msg['messageId']
        'msg-123'
    """
    import json

    s3_event = get_sample_s3_event(bucket_name, s3_key)

    return {
        "messageId": message_id,
        "receiptHandle": f"receipt-{message_id}",
        "body": json.dumps(s3_event),
        "attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1733739509000",
            "SenderId": "AIDAIT2UOQQY3AUEKVGXU",
            "ApproximateFirstReceiveTimestamp": "1733739509000"
        },
        "messageAttributes": {},
        "md5OfBody": "d41d8cd98f00b204e9800998ecf8427e",
        "eventSource": "aws:sqs",
        "eventSourceARN": "arn:aws:sqs:ap-southeast-1:123456789012:fund-data-sync-dev",
        "awsRegion": "ap-southeast-1"
    }


def get_sample_sqs_event(bucket_name: str, s3_key: str) -> dict:
    """Generate mock SQS event with Records list.

    Matches AWS Lambda event structure when triggered by SQS.

    Args:
        bucket_name: S3 bucket name
        s3_key: S3 object key

    Returns:
        SQS event dict for Lambda handler with Records list

    Example:
        >>> event = get_sample_sqs_event('bucket', 'file.csv')
        >>> len(event['Records'])
        1
    """
    return {
        "Records": [get_sample_sqs_message(bucket_name, s3_key)]
    }
