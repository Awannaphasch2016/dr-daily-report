"""PDF Worker Lambda Handler - generates PDFs for existing reports"""

import json
import logging
import os
from datetime import datetime, date
from typing import Any

from src.data.aurora.precompute_service import PrecomputeService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _validate_configuration() -> None:
    """Validate required environment variables at Lambda startup.

    Fails fast if critical configuration is missing (Principle #1: Defensive Programming).
    """
    required = {
        'AURORA_HOST': 'Aurora database connection',
        'AURORA_USER': 'Aurora user',
        'AURORA_PASSWORD': 'Aurora password',
        'PDF_BUCKET_NAME': 'PDF storage S3 bucket',
        'TZ': 'Bangkok timezone',
    }

    missing = {var: purpose for var, purpose in required.items()
               if not os.environ.get(var)}

    if missing:
        error_msg = "Missing required environment variables:\n"
        for var, purpose in missing.items():
            error_msg += f"  - {var} (needed for: {purpose})\n"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"✅ All {len(required)} required env vars present")


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for SQS PDF generation messages.

    Args:
        event: SQS event with Records containing PDF generation jobs
        context: Lambda context

    Returns:
        Success response with count of processed PDFs
    """
    # Validate configuration at startup (Principle #1)
    _validate_configuration()

    records = event.get('Records', [])
    logger.info(f"====== PDF Worker Started ======")
    logger.info(f"Processing {len(records)} PDF job(s)")

    for record in records:
        process_record(record)

    logger.info(f"✅ Processed {len(records)} PDF job(s)")
    return {'statusCode': 200, 'body': f'Processed {len(records)} PDFs'}


def process_record(record: dict) -> None:
    """Process single SQS PDF job record.

    Args:
        record: SQS record containing PDF generation job

    Raises:
        json.JSONDecodeError: If message body is invalid JSON
        KeyError: If required fields missing from message
        ValueError: If PDF generation fails or report not found
    """
    message_id = record.get('messageId', 'unknown')
    body = record.get('body', '')

    try:
        message = json.loads(body)
        report_id = message['id']
        symbol = message['symbol']
        report_text = message['report_text']
        chart_base64 = message.get('chart_base64', '')
        data_date_str = message['report_date']

        # Explicit date deserialization (Principle #4: Type System Integration)
        data_date = date.fromisoformat(data_date_str)

        logger.info(f"====== Processing PDF Job ======")
        logger.info(f"MessageId: {message_id}")
        logger.info(f"ReportId: {report_id}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Date: {data_date}")

        # Generate and upload PDF
        ps = PrecomputeService()

        logger.info(f"📄 Generating PDF for {symbol}...")
        pdf_s3_key = ps._generate_and_upload_pdf(
            symbol=symbol,
            data_date=data_date,
            report_text=report_text,
            chart_base64=chart_base64
        )

        # Defensive check (Principle #1)
        if not pdf_s3_key:
            logger.error(f"❌ PDF generation returned None for {symbol}")
            raise ValueError(f"PDF generation returned None for {symbol}")

        pdf_generated_at = datetime.now()
        logger.info(f"✅ Generated PDF: {pdf_s3_key}")

        # Update Aurora with PDF metadata
        logger.info(f"Updating report {report_id} with PDF metadata...")
        affected = ps.update_pdf_metadata(
            report_id=report_id,
            pdf_s3_key=pdf_s3_key,
            pdf_generated_at=pdf_generated_at
        )

        # Verify UPDATE succeeded (Principle #2: Progressive Evidence Strengthening)
        if affected == 0:
            logger.error(f"❌ UPDATE failed - 0 rows affected for report_id={report_id}")
            raise ValueError(f"No report found with id={report_id}")

        logger.info(f"✅ PDF job completed for {symbol} (report_id={report_id})")

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in message: {e}")
        raise
    except KeyError as e:
        logger.error(f"❌ Missing field in message: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process PDF job: {e}", exc_info=True)
        raise  # Re-raise for SQS retry/DLQ
