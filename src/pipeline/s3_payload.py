"""S3 intermediate payload storage for pipeline phases.

Stores serialized AgentState between PreProcess → Generation → PostProcess.
Required because Step Functions has a 256KB payload limit and serialized
AgentState is 300-500KB (chart_base64 alone is 100-200KB).

Pattern:
    PreProcess writes to s3://{bucket}/pipeline/{execution_id}/state.json
    Generation and PostProcess read from that key
"""

import json
import logging
import os

import boto3

from src.utils.serialization import make_json_serializable

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def get_pipeline_bucket() -> str:
    """Get S3 bucket name for pipeline intermediate storage."""
    bucket = os.getenv('DATA_LAKE_BUCKET')
    if not bucket:
        raise ValueError("DATA_LAKE_BUCKET environment variable not set")
    return bucket


def build_s3_key(execution_id: str, filename: str = "state.json") -> str:
    """Build S3 key for pipeline intermediate payload."""
    return f"pipeline/{execution_id}/{filename}"


def write_payload(execution_id: str, data: dict) -> str:
    """Write serialized payload to S3.

    Args:
        execution_id: Unique pipeline execution ID
        data: Dict to serialize and store

    Returns:
        S3 key where payload was written
    """
    bucket = get_pipeline_bucket()
    key = build_s3_key(execution_id)

    serializable = make_json_serializable(data)
    body = json.dumps(serializable, ensure_ascii=False)

    client = _get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode('utf-8'),
        ContentType='application/json',
    )

    size_kb = len(body) / 1024
    logger.info(f"Wrote pipeline payload: s3://{bucket}/{key} ({size_kb:.1f} KB)")
    return key


def read_payload(s3_key: str) -> dict:
    """Read serialized payload from S3.

    Args:
        s3_key: S3 key to read from

    Returns:
        Deserialized dict
    """
    bucket = get_pipeline_bucket()
    client = _get_s3_client()

    response = client.get_object(Bucket=bucket, Key=s3_key)
    body = response['Body'].read().decode('utf-8')
    data = json.loads(body)

    size_kb = len(body) / 1024
    logger.info(f"Read pipeline payload: s3://{bucket}/{s3_key} ({size_kb:.1f} KB)")
    return data
