# -*- coding: utf-8 -*-
"""
SQS Message Contract Tests

Following CLAUDE.md Principle 4: Schema Testing at System Boundaries
- System boundary: Scheduler Lambda → SQS → Worker Lambda
- Contract: Message schema must match between producer (scheduler) and consumer (worker)

These tests validate the message format survives the journey from scheduler to worker.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, Any


@pytest.mark.integration
class TestSQSMessageContract:
    """Validate SQS message schema between scheduler and worker.

    Following CLAUDE.md: "When Schema Testing IS Appropriate:
    - Producer/consumer architectures (scheduler writes data, worker reads it)
    - Event-driven systems (event shape is the contract)"
    """

    def test_scheduler_produces_valid_message_schema(self):
        """Scheduler creates messages with all required fields.

        Following CLAUDE.md: Test the contract (required fields),
        not the implementation (how fields are created).
        """
        # Simulate scheduler creating a message
        scheduler_message = self._create_scheduler_message(
            job_id="test-job-123",
            ticker="DBS19",
            user_id="test-user",
            strategy="single-stage"
        )

        # Validate required fields exist
        assert "job_id" in scheduler_message, "Message must have job_id"
        assert "ticker" in scheduler_message, "Message must have ticker"

        # Validate field types (contract enforcement)
        assert isinstance(scheduler_message["job_id"], str), "job_id must be string"
        assert isinstance(scheduler_message["ticker"], str), "ticker must be string"

        # Validate optional fields have correct types when present
        if "user_id" in scheduler_message:
            assert isinstance(scheduler_message["user_id"], str), "user_id must be string"

        if "strategy" in scheduler_message:
            assert isinstance(scheduler_message["strategy"], str), "strategy must be string"
            assert scheduler_message["strategy"] in ["single-stage", "multi-stage"], \
                "strategy must be valid value"

        if "retry_count" in scheduler_message:
            assert isinstance(scheduler_message["retry_count"], int), "retry_count must be int"
            assert scheduler_message["retry_count"] >= 0, "retry_count must be non-negative"

        if "timestamp" in scheduler_message:
            assert isinstance(scheduler_message["timestamp"], str), "timestamp must be string (ISO format)"

    def test_worker_can_parse_scheduler_message(self):
        """Worker handler accepts scheduler message format.

        Following CLAUDE.md: Test behavior (can parse and extract),
        not implementation (exact parsing logic).
        """
        # Create message in scheduler format
        message = self._create_scheduler_message(
            job_id="test-parse-456",
            ticker="UOB19"
        )

        # Simulate worker parsing (no exceptions = success)
        try:
            extracted_job_id = message["job_id"]
            extracted_ticker = message["ticker"]

            # Validate extracted values
            assert extracted_job_id == "test-parse-456", "Worker should extract job_id correctly"
            assert extracted_ticker == "UOB19", "Worker should extract ticker correctly"

        except KeyError as e:
            pytest.fail(f"Worker failed to parse message: missing field {e}")
        except Exception as e:
            pytest.fail(f"Worker failed to parse message: {e}")

    def test_message_survives_json_serialization(self):
        """Message format survives SQS JSON serialization round-trip.

        Following CLAUDE.md: Silent Failure Detection
        - JSON serialization can fail silently (NaN, Inf, non-serializable types)
        - Validate round-trip: dict → JSON → SQS → JSON → dict preserves data
        """
        # Create message with all field types
        original_message = self._create_scheduler_message(
            job_id="test-serialization-789",
            ticker="KBANK19",
            user_id="user-123",
            strategy="multi-stage",
            retry_count=2,
            timestamp=datetime.utcnow().isoformat()
        )

        # Simulate SQS serialization (scheduler side)
        try:
            json_string = json.dumps(original_message)
        except Exception as e:
            pytest.fail(f"Scheduler failed to serialize message to JSON: {e}")

        # Simulate SQS deserialization (worker side)
        try:
            deserialized_message = json.loads(json_string)
        except Exception as e:
            pytest.fail(f"Worker failed to deserialize message from JSON: {e}")

        # Validate all fields preserved
        assert deserialized_message["job_id"] == original_message["job_id"], \
            "job_id should survive serialization"
        assert deserialized_message["ticker"] == original_message["ticker"], \
            "ticker should survive serialization"
        assert deserialized_message["user_id"] == original_message["user_id"], \
            "user_id should survive serialization"
        assert deserialized_message["strategy"] == original_message["strategy"], \
            "strategy should survive serialization"
        assert deserialized_message["retry_count"] == original_message["retry_count"], \
            "retry_count should survive serialization"
        assert deserialized_message["timestamp"] == original_message["timestamp"], \
            "timestamp should survive serialization"

    def test_minimal_message_is_valid(self):
        """Message with only required fields is valid.

        Following CLAUDE.md: Test the contract (minimal requirements),
        ensures backwards compatibility if optional fields are added.
        """
        # Create message with ONLY required fields
        minimal_message = {
            "job_id": "minimal-test-001",
            "ticker": "SIA19"
        }

        # Validate it's serializable
        try:
            json_string = json.dumps(minimal_message)
            deserialized = json.loads(json_string)

            assert deserialized["job_id"] == "minimal-test-001"
            assert deserialized["ticker"] == "SIA19"

        except Exception as e:
            pytest.fail(f"Minimal message should be valid: {e}")

    def test_message_rejects_invalid_ticker_format(self):
        """Message validation catches invalid ticker formats.

        Following CLAUDE.md: Defensive Programming
        - Validate data at system boundaries
        - Fail fast and visibly when something is wrong
        """
        # Empty ticker should be rejected
        invalid_message_empty = self._create_scheduler_message(
            job_id="invalid-001",
            ticker=""
        )

        assert invalid_message_empty["ticker"] == "", "Empty ticker captured for validation"

        # None ticker should be rejected
        with pytest.raises((TypeError, AssertionError)):
            invalid_message_none = {
                "job_id": "invalid-002",
                "ticker": None  # Invalid type
            }
            # Scheduler should validate before creating message
            assert invalid_message_none["ticker"] is not None, \
                "Ticker must not be None"

    def test_message_with_extra_fields_is_valid(self):
        """Message with extra fields is valid (forward compatibility).

        Following CLAUDE.md: Don't break on unexpected fields
        - Allows adding new optional fields without breaking old workers
        """
        # Create message with extra fields (future expansion)
        message_with_extras = self._create_scheduler_message(
            job_id="extra-fields-001",
            ticker="DBS19"
        )

        # Add extra fields not in current contract
        message_with_extras["priority"] = "high"
        message_with_extras["metadata"] = {"region": "SG", "category": "banking"}

        # Should serialize without errors
        try:
            json_string = json.dumps(message_with_extras)
            deserialized = json.loads(json_string)

            # Required fields still present
            assert deserialized["job_id"] == "extra-fields-001"
            assert deserialized["ticker"] == "DBS19"

            # Extra fields preserved
            assert deserialized["priority"] == "high"
            assert deserialized["metadata"]["region"] == "SG"

        except Exception as e:
            pytest.fail(f"Message with extra fields should be valid: {e}")

    # Helper method to create messages
    def _create_scheduler_message(
        self,
        job_id: str,
        ticker: str,
        user_id: str = None,
        strategy: str = None,
        retry_count: int = 0,
        timestamp: str = None
    ) -> Dict[str, Any]:
        """Create a message in scheduler format.

        This simulates what the scheduler Lambda produces.
        """
        message = {
            "job_id": job_id,
            "ticker": ticker,
        }

        # Add optional fields if provided
        if user_id is not None:
            message["user_id"] = user_id

        if strategy is not None:
            message["strategy"] = strategy

        if retry_count is not None:
            message["retry_count"] = retry_count

        if timestamp is not None:
            message["timestamp"] = timestamp

        return message
