"""Get Report List Lambda Handler - queries Aurora for reports needing PDFs"""

import logging
import os
from datetime import date
from typing import Any, Dict

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


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Query Aurora for reports needing PDF generation.

    Args:
        event: Lambda event (can contain 'report_date' for specific date)
        context: Lambda context

    Returns:
        {
            "reports": [
                {
                    "id": 123,
                    "symbol": "D05.SI",
                    "report_text": "...",
                    "chart_base64": "...",
                    "report_date": "2026-01-03"
                },
                ...
            ]
        }
    """
    # Validate configuration at startup (Principle #1)
    _validate_configuration()

    logger.info("====== Get Report List Lambda Started ======")

    try:
        # Get report date from event or use today (Bangkok timezone)
        report_date_str = event.get('report_date')
        if report_date_str:
            report_date = date.fromisoformat(report_date_str)
            logger.info(f"Using explicit report_date from event: {report_date}")
        else:
            # Use today's date in Bangkok timezone (Principle #16)
            from zoneinfo import ZoneInfo
            from datetime import datetime
            bangkok_tz = ZoneInfo("Asia/Bangkok")
            report_date = datetime.now(bangkok_tz).date()
            logger.info(f"Using today's Bangkok date: {report_date}")

        logger.info(f"Querying reports needing PDFs for date: {report_date}")

        # Query Aurora
        ps = PrecomputeService()
        reports = ps.get_reports_needing_pdfs(report_date, limit=50)

        logger.info(f"✅ Found {len(reports)} reports needing PDFs")

        # Serialize dates for JSON (Principle #4: Type System Integration)
        serialized_reports = []
        for report in reports:
            serialized_report = dict(report)
            # Convert date to string for JSON serialization
            if 'report_date' in serialized_report and isinstance(serialized_report['report_date'], date):
                serialized_report['report_date'] = serialized_report['report_date'].isoformat()
            serialized_reports.append(serialized_report)

        return {
            "reports": serialized_reports
        }

    except Exception as e:
        logger.error(f"❌ Failed to query reports: {e}", exc_info=True)
        raise
