# -*- coding: utf-8 -*-
"""
Lambda handler for static API generation.

Generates static JSON files from Aurora precomputed data and uploads to S3
for CloudFront CDN serving. Called after precompute workflow completes.

Architecture:
    Step Functions → static_api_handler → S3 → CloudFront → Frontend

This handler is invoked as the final step in the precompute workflow,
after all reports and patterns have been generated.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _validate_required_config() -> None:
    """Validate required environment variables at Lambda startup.

    Defensive programming principle: Validate configuration at startup,
    not on first use. Fails fast if critical config is missing.

    Raises:
        RuntimeError: If any required environment variable is missing
    """
    required_vars = {
        'STATIC_API_BUCKET': 'S3 bucket for static API files',
    }

    missing = {var: purpose for var, purpose in required_vars.items()
               if not os.getenv(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"All {len(required_vars)} required env vars present")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate and upload static API files to S3.

    Event format (from Step Functions):
        {
            "execution_id": "precompute-20260116-120000",
            "report_results": [...],
            "pattern_results": [...]
        }

    Args:
        event: Lambda event from Step Functions
        context: Lambda context

    Returns:
        Response dict with generation results
    """
    start_time = datetime.now()
    logger.info(f"Static API generation invoked at {start_time.isoformat()}")
    logger.info(f"Event keys: {list(event.keys())}")

    try:
        # Validate configuration
        _validate_required_config()

        # Import generator (lazy import for Lambda cold start optimization)
        from src.data.static_api_generator import StaticAPIGenerator

        # Create generator
        generator = StaticAPIGenerator()

        if not generator.is_enabled():
            return {
                'statusCode': 200,
                'body': {
                    'status': 'skipped',
                    'message': 'Static API generation disabled (STATIC_API_BUCKET not set)',
                    'execution_id': event.get('execution_id'),
                }
            }

        # Generate all static API files
        logger.info("Starting static API file generation...")
        result = generator.generate_all()

        # Optionally invalidate CloudFront cache
        cloudfront_id = os.environ.get('STATIC_API_CLOUDFRONT_ID')
        if cloudfront_id:
            logger.info(f"Invalidating CloudFront distribution {cloudfront_id}...")
            generator.invalidate_cloudfront(cloudfront_id)
            result['cloudfront_invalidated'] = True
        else:
            result['cloudfront_invalidated'] = False

        end_time = datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'statusCode': 200,
            'body': {
                'status': 'success' if result['upload_success'] else 'partial_failure',
                'message': f"Generated {result['files_generated']} static API files",
                'execution_id': event.get('execution_id'),
                'files_generated': result['files_generated'],
                'files_failed': result['files_failed'],
                'ticker_count': result.get('ticker_count', 0),
                'duration_ms': result['duration_ms'],
                'total_duration_seconds': duration_seconds,
                'cloudfront_invalidated': result.get('cloudfront_invalidated', False),
            }
        }

    except Exception as e:
        logger.error(f"Static API generation failed: {e}", exc_info=True)

        return {
            'statusCode': 500,
            'body': {
                'status': 'failed',
                'message': f'Static API generation failed: {str(e)}',
                'execution_id': event.get('execution_id'),
                'error': str(e),
            }
        }


# For local testing
if __name__ == '__main__':
    # Ensure env vars are set for local testing
    os.environ.setdefault('STATIC_API_BUCKET', 'dr-daily-report-static-api-dev')

    test_event = {
        'execution_id': 'test-local-20260116',
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
