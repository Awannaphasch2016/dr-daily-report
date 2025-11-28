"""Job service for async report generation

Manages job lifecycle in DynamoDB for async report generation pattern.
Jobs track status: pending -> in_progress -> completed/failed
"""

import os
import json
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(BaseModel):
    """Job model for async report generation"""
    job_id: str = Field(..., description="Unique job identifier")
    ticker: str = Field(..., description="Ticker symbol")
    status: str = Field(..., description="Job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Processing end timestamp")
    result: Optional[dict] = Field(None, description="Report result when completed")
    error: Optional[str] = Field(None, description="Error message when failed")


class JobNotFoundError(Exception):
    """Raised when job is not found in DynamoDB"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class JobService:
    """Service for managing async report jobs in DynamoDB"""

    def __init__(self, table_name: str | None = None, use_local: bool = False):
        """Initialize job service

        Args:
            table_name: DynamoDB table name (defaults to env var)
            use_local: If True, use local DynamoDB for testing
        """
        if table_name is None:
            table_name = os.getenv(
                "JOBS_TABLE_NAME",
                "dr-daily-report-telegram-jobs-dev"
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

    def _generate_job_id(self) -> str:
        """Generate unique job ID with prefix"""
        return f"rpt_{uuid.uuid4().hex[:12]}"

    def create_job(self, ticker: str) -> Job:
        """Create a new pending job

        Args:
            ticker: Ticker symbol for the report

        Returns:
            Job instance with pending status
        """
        ticker_upper = ticker.upper()
        job_id = self._generate_job_id()
        created_at = datetime.now()
        ttl = int((created_at + timedelta(hours=24)).timestamp())

        item = {
            'job_id': job_id,
            'ticker': ticker_upper,
            'status': JobStatus.PENDING.value,
            'created_at': created_at.isoformat(),
            'ttl': ttl
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Created job {job_id} for ticker {ticker_upper}")

            return Job(
                job_id=job_id,
                ticker=ticker_upper,
                status=JobStatus.PENDING.value,
                created_at=created_at
            )

        except Exception as e:
            logger.error(f"Failed to create job for {ticker_upper}: {e}")
            raise

    def get_job(self, job_id: str) -> Job:
        """Get job by ID

        Args:
            job_id: Job identifier

        Returns:
            Job instance

        Raises:
            JobNotFoundError: If job doesn't exist
        """
        try:
            response = self.table.get_item(Key={'job_id': job_id})

            if 'Item' not in response:
                raise JobNotFoundError(job_id)

            item = response['Item']

            # Parse result JSON if present
            result = None
            if item.get('result'):
                try:
                    result = json.loads(item['result'])
                except (json.JSONDecodeError, TypeError):
                    result = item['result']

            return Job(
                job_id=item['job_id'],
                ticker=item['ticker'],
                status=item['status'],
                created_at=datetime.fromisoformat(item['created_at']),
                started_at=datetime.fromisoformat(item['started_at']) if item.get('started_at') else None,
                finished_at=datetime.fromisoformat(item['finished_at']) if item.get('finished_at') else None,
                result=result,
                error=item.get('error')
            )

        except JobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            raise

    def start_job(self, job_id: str) -> None:
        """Mark job as in_progress

        Args:
            job_id: Job identifier
        """
        started_at = datetime.now()

        try:
            self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, started_at = :started_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': JobStatus.IN_PROGRESS.value,
                    ':started_at': started_at.isoformat()
                }
            )
            logger.info(f"Started job {job_id}")

        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            raise

    def complete_job(self, job_id: str, result: dict) -> None:
        """Mark job as completed with result

        Args:
            job_id: Job identifier
            result: Report result dictionary
        """
        finished_at = datetime.now()
        result_json = json.dumps(result, ensure_ascii=False, default=str)

        try:
            self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, finished_at = :finished_at, #result = :result',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#result': 'result'
                },
                ExpressionAttributeValues={
                    ':status': JobStatus.COMPLETED.value,
                    ':finished_at': finished_at.isoformat(),
                    ':result': result_json
                }
            )
            logger.info(f"Completed job {job_id}")

        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            raise

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed with error message

        Args:
            job_id: Job identifier
            error: Error message
        """
        finished_at = datetime.now()

        try:
            self.table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, finished_at = :finished_at, #error = :error',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#error': 'error'
                },
                ExpressionAttributeValues={
                    ':status': JobStatus.FAILED.value,
                    ':finished_at': finished_at.isoformat(),
                    ':error': error
                }
            )
            logger.info(f"Failed job {job_id}: {error}")

        except Exception as e:
            logger.error(f"Failed to mark job {job_id} as failed: {e}")
            raise


# Global job service instance
_job_service: JobService | None = None


def get_job_service(use_local: bool | None = None) -> JobService:
    """Get or create global job service instance

    Args:
        use_local: If True, use local DynamoDB for testing.
                   If None, checks USE_LOCAL_DYNAMODB env var.

    Returns:
        JobService instance
    """
    global _job_service
    if _job_service is None:
        # Check environment variable if use_local not explicitly set
        if use_local is None:
            use_local = os.getenv('USE_LOCAL_DYNAMODB', 'false').lower() == 'true'

        _job_service = JobService(use_local=use_local)
    return _job_service
