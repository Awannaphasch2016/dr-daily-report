# -*- coding: utf-8 -*-
"""
Lambda handler for daily webhook health checks.

Single Responsibility: Probe configured endpoints, record results to Aurora.
Triggered by: EventBridge Scheduler (daily 5 AM Bangkok)

Status classification:
    healthy  — expected HTTP code + latency below threshold
    degraded — expected HTTP code but latency above threshold
    down     — wrong HTTP code, timeout, or connection error
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

import boto3
import pymysql
import requests as http_requests

from src.data.aurora.table_names import WEBHOOK_HEALTH_CHECKS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoint configuration
# ---------------------------------------------------------------------------
ENDPOINTS = [
    {
        'name': 'line_webhook',
        'url_env': 'LINE_WEBHOOK_URL',
        'method': 'POST',
        'headers': {'Content-Type': 'application/json'},
        'body': '{}',
        'expect_code': 200,
        'timeout_s': 10,
        'latency_threshold_ms': 5000,
    },
]


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup."""
    required_vars = {
        'AURORA_HOST': 'Aurora database host',
        'AURORA_USER': 'Aurora database user',
        'AURORA_PASSWORD': 'Aurora database password',
        'AURORA_DATABASE': 'Aurora database name',
        'TZ': 'Bangkok timezone for date handling',
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


# ---------------------------------------------------------------------------
# Health check logic
# ---------------------------------------------------------------------------
def _check_endpoint(endpoint: Dict) -> Dict:
    """Probe a single endpoint and return the result."""
    name = endpoint['name']
    url = os.getenv(endpoint['url_env'], '')

    if not url:
        logger.error(f"Env var {endpoint['url_env']} not set for endpoint {name}")
        return {
            'endpoint': name,
            'url': f"MISSING:{endpoint['url_env']}",
            'status': 'down',
            'http_code': 0,
            'latency_ms': 0,
            'body_valid': False,
            'error_msg': f"Environment variable {endpoint['url_env']} not configured",
        }

    logger.info(f"Checking endpoint: {name} -> {url}")

    try:
        start = time.monotonic()
        resp = http_requests.request(
            method=endpoint['method'],
            url=url,
            headers=endpoint.get('headers', {}),
            data=endpoint.get('body', ''),
            timeout=endpoint['timeout_s'],
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        http_code = resp.status_code
        body_valid = http_code == endpoint['expect_code']

        if http_code != endpoint['expect_code']:
            status = 'down'
            error_msg = f"Expected {endpoint['expect_code']}, got {http_code}"
        elif latency_ms > endpoint['latency_threshold_ms']:
            status = 'degraded'
            error_msg = f"Latency {latency_ms}ms exceeds threshold {endpoint['latency_threshold_ms']}ms"
        else:
            status = 'healthy'
            error_msg = None

        logger.info(f"  {name}: {status} (code={http_code}, latency={latency_ms}ms)")

        return {
            'endpoint': name,
            'url': url,
            'status': status,
            'http_code': http_code,
            'latency_ms': latency_ms,
            'body_valid': body_valid,
            'error_msg': error_msg,
        }

    except http_requests.Timeout:
        logger.error(f"  {name}: timeout after {endpoint['timeout_s']}s")
        return {
            'endpoint': name,
            'url': url,
            'status': 'down',
            'http_code': 0,
            'latency_ms': endpoint['timeout_s'] * 1000,
            'body_valid': False,
            'error_msg': f"Timeout after {endpoint['timeout_s']}s",
        }

    except http_requests.ConnectionError as e:
        logger.error(f"  {name}: connection error: {e}")
        return {
            'endpoint': name,
            'url': url,
            'status': 'down',
            'http_code': 0,
            'latency_ms': 0,
            'body_valid': False,
            'error_msg': f"Connection error: {e}",
        }

    except Exception as e:
        logger.error(f"  {name}: unexpected error: {e}")
        return {
            'endpoint': name,
            'url': url,
            'status': 'down',
            'http_code': 0,
            'latency_ms': 0,
            'body_valid': False,
            'error_msg': str(e),
        }


def _store_result(conn, check_time: datetime, result: Dict) -> None:
    """INSERT one health check result into Aurora."""
    sql = f"""
        INSERT INTO {WEBHOOK_HEALTH_CHECKS}
            (check_time, endpoint, url, status, http_code, latency_ms, body_valid, error_msg)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, (
            check_time,
            result['endpoint'],
            result['url'],
            result['status'],
            result['http_code'],
            result['latency_ms'],
            result['body_valid'],
            result.get('error_msg'),
        ))
    conn.commit()


def _alert_sns(unhealthy: List[Dict]) -> None:
    """Publish alert to SNS if any endpoints are not healthy."""
    topic_arn = os.getenv('SNS_TOPIC_ARN')
    if not topic_arn:
        logger.warning("SNS_TOPIC_ARN not set — skipping alert")
        return

    lines = ["Webhook Health Check Alert\n"]
    for r in unhealthy:
        lines.append(f"  {r['endpoint']}: {r['status']} (code={r['http_code']}, "
                     f"latency={r['latency_ms']}ms)")
        if r.get('error_msg'):
            lines.append(f"    Error: {r['error_msg']}")

    message = "\n".join(lines)
    subject = f"[CRITICAL] Webhook health check failure ({len(unhealthy)} endpoint(s))"

    try:
        sns = boto3.client('sns', region_name='ap-southeast-1')
        sns.publish(TopicArn=topic_arn, Subject=subject[:100], Message=message)
        logger.info(f"SNS alert sent to {topic_arn}")
    except Exception as e:
        logger.error(f"Failed to publish SNS alert: {e}")


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Probe all configured endpoints and record results.

    Returns:
        Summary dict with per-endpoint status and overall health.
    """
    _validate_required_config()

    check_time = datetime.now()
    logger.info(f"Webhook health check starting at {check_time.isoformat()}")

    # Probe all endpoints
    results = [_check_endpoint(ep) for ep in ENDPOINTS]

    # Store results in Aurora
    conn = pymysql.connect(
        host=os.environ['AURORA_HOST'],
        user=os.environ['AURORA_USER'],
        password=os.environ['AURORA_PASSWORD'],
        database=os.environ['AURORA_DATABASE'],
        port=int(os.environ.get('AURORA_PORT', 3306)),
    )
    try:
        for result in results:
            _store_result(conn, check_time, result)
        logger.info(f"Stored {len(results)} health check result(s) in Aurora")
    finally:
        conn.close()

    # Alert on unhealthy endpoints
    unhealthy = [r for r in results if r['status'] != 'healthy']
    if unhealthy:
        logger.warning(f"{len(unhealthy)} unhealthy endpoint(s) detected")
        _alert_sns(unhealthy)

    summary = {
        'check_time': check_time.isoformat(),
        'total_endpoints': len(results),
        'healthy': sum(1 for r in results if r['status'] == 'healthy'),
        'degraded': sum(1 for r in results if r['status'] == 'degraded'),
        'down': sum(1 for r in results if r['status'] == 'down'),
        'results': results,
    }

    logger.info(f"Health check complete: {summary['healthy']}/{summary['total_endpoints']} healthy")
    return summary


if __name__ == '__main__':
    os.environ.setdefault('TZ', 'Asia/Bangkok')
    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2, default=str))
