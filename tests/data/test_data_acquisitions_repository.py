# -*- coding: utf-8 -*-
"""
Unit tests for DataAcquisitionsRepository (Principle #19: Cross-Boundary Testing)

Tests follow defensive programming principles:
- Validation of enum values and required fields
- Lifecycle state transitions (start → complete/fail)
- SQL parameter ordering
- JSON serialization / datetime conversion
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.data_acquisitions_repository import (
    ALLOWED_SOURCE_TYPES,
    ALLOWED_STATUSES,
    DataAcquisitionsRepository,
    get_data_acquisitions_repository,
)


class TestDataAcquisitionsRepositoryValidation:
    """Tests for defensive validation (Principle #1)."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.mock_client.fetch_one.return_value = {'id': 1}
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_start_run_rejects_invalid_source_type(self):
        with pytest.raises(ValueError, match="Invalid source_type"):
            self.repo.start_run(
                source_table='sgx_filings',
                source_type='invalid_type',
                source_name='test_script',
            )

    def test_start_run_accepts_all_allowed_source_types(self):
        for source_type in ALLOWED_SOURCE_TYPES:
            self.repo.start_run(
                source_table='sgx_filings',
                source_type=source_type,
                source_name='test_script',
            )

    def test_complete_run_rejects_invalid_status(self):
        with pytest.raises(ValueError, match="must be 'success' or 'partial'"):
            self.repo.complete_run(
                acquisition_id=1,
                records_fetched=10,
                records_upserted=5,
                status='running',
            )

    def test_complete_run_accepts_success(self):
        self.repo.complete_run(
            acquisition_id=1,
            records_fetched=10,
            records_upserted=5,
            status='success',
        )

    def test_complete_run_accepts_partial(self):
        self.repo.complete_run(
            acquisition_id=1,
            records_fetched=10,
            records_upserted=5,
            status='partial',
        )

    def test_complete_run_raises_on_not_found(self):
        self.mock_client.execute.return_value = 0

        with pytest.raises(ValueError, match="not found"):
            self.repo.complete_run(
                acquisition_id=999,
                records_fetched=10,
                records_upserted=5,
            )

    def test_fail_run_raises_on_not_found(self):
        self.mock_client.execute.return_value = 0

        with pytest.raises(ValueError, match="not found"):
            self.repo.fail_run(
                acquisition_id=999,
                error_message='test error',
            )

    def test_get_runs_rejects_invalid_source_type_filter(self):
        with pytest.raises(ValueError, match="Invalid source_type"):
            self.repo.get_runs(source_type='bad_type')

    def test_get_runs_rejects_invalid_status_filter(self):
        with pytest.raises(ValueError, match="Invalid status"):
            self.repo.get_runs(status='bad_status')


class TestDataAcquisitionsRepositoryStartRun:
    """Tests for start_run() SQL and params."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.mock_client.fetch_one.return_value = {'id': 42}
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_start_run_returns_acquisition_id(self):
        result = self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='test_script',
        )
        assert result == 42

    def test_start_run_calls_execute_with_correct_params(self):
        self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='sgx_fin_reports',
            source_version='v1',
            artifact_s3_key='scripts/data-acquisition/sgx/v1.py',
            artifact_checksum='abc123',
            endpoint_url='https://api.sgx.com/financialreports/v1.0',
            endpoint_version='v1.0',
            description='Test run',
            parameters={'pagesize': 250},
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert params[0] == 'sgx_filings'
        assert params[1] == 'script'
        assert params[2] == 'sgx_fin_reports'
        assert params[3] == 'v1'
        assert params[4] == 'scripts/data-acquisition/sgx/v1.py'
        assert params[5] == 'abc123'
        assert params[6] == 'https://api.sgx.com/financialreports/v1.0'
        assert params[7] == 'v1.0'
        assert params[8] == 'Test run'
        assert params[9] == json.dumps({'pagesize': 250})

    def test_start_run_serializes_parameters_to_json(self):
        self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='test',
            parameters={'key': 'value', 'num': 42},
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[9] == json.dumps({'key': 'value', 'num': 42})

    def test_start_run_passes_none_when_no_parameters(self):
        self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='test',
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[9] is None

    def test_start_run_calls_execute_with_commit_true(self):
        self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='test',
        )

        call_args = self.mock_client.execute.call_args
        assert call_args[1].get('commit') is True

    def test_start_run_optional_fields_default_to_none(self):
        self.repo.start_run(
            source_table='sgx_filings',
            source_type='script',
            source_name='test',
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        # source_version, artifact_s3_key, artifact_checksum,
        # endpoint_url, endpoint_version, description, parameters
        for i in range(3, 10):
            assert params[i] is None, f"param[{i}] should be None"


class TestDataAcquisitionsRepositoryCompleteRun:
    """Tests for complete_run()."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_complete_run_calls_execute_with_correct_params(self):
        self.repo.complete_run(
            acquisition_id=42,
            records_fetched=100,
            records_upserted=50,
            status='success',
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params == (100, 50, 'success', 42)

    def test_complete_run_defaults_status_to_success(self):
        self.repo.complete_run(
            acquisition_id=1,
            records_fetched=10,
            records_upserted=5,
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[2] == 'success'


class TestDataAcquisitionsRepositoryFailRun:
    """Tests for fail_run()."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_fail_run_calls_execute_with_correct_params(self):
        self.repo.fail_run(
            acquisition_id=42,
            error_message='Connection timeout',
            records_fetched=100,
            records_upserted=50,
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params == ('Connection timeout', 100, 50, 42)

    def test_fail_run_defaults_records_to_zero(self):
        self.repo.fail_run(
            acquisition_id=42,
            error_message='Error',
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params == ('Error', 0, 0, 42)


class TestDataAcquisitionsRepositoryQuery:
    """Tests for get_runs() query method."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_get_runs_no_filters(self):
        self.repo.get_runs()

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'WHERE' not in query
        assert params == (50,)  # default limit

    def test_get_runs_filters_by_source_table(self):
        self.repo.get_runs(source_table='sgx_filings')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'source_table = %s' in query
        assert params == ('sgx_filings', 50)

    def test_get_runs_filters_by_multiple_fields(self):
        self.repo.get_runs(
            source_table='sgx_filings',
            source_type='script',
            source_name='test',
            status='success',
        )

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'source_table = %s' in query
        assert 'source_type = %s' in query
        assert 'source_name = %s' in query
        assert 'status = %s' in query
        assert params == ('sgx_filings', 'script', 'test', 'success', 50)

    def test_get_runs_custom_limit(self):
        self.repo.get_runs(limit=10)

        call_args = self.mock_client.fetch_all.call_args
        params = call_args[0][1]
        assert params == (10,)


class TestDataAcquisitionsRepositoryRowToDict:
    """Tests for _row_to_dict() conversion."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = DataAcquisitionsRepository(client=self.mock_client)

    def test_parses_json_parameters(self):
        row = {
            'id': 1,
            'parameters': '{"key": "value"}',
            'started_at': None,
            'completed_at': None,
            'created_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert isinstance(result['parameters'], dict)
        assert result['parameters']['key'] == 'value'

    def test_leaves_non_string_parameters(self):
        row = {
            'id': 1,
            'parameters': {'already': 'parsed'},
            'started_at': None,
            'completed_at': None,
            'created_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['parameters'] == {'already': 'parsed'}

    def test_converts_datetime_to_isoformat(self):
        dt = datetime(2026, 3, 14, 8, 30, 0)
        row = {
            'id': 1,
            'parameters': None,
            'started_at': dt,
            'completed_at': dt,
            'created_at': dt,
        }

        result = self.repo._row_to_dict(row)

        assert result['started_at'] == '2026-03-14T08:30:00'
        assert result['completed_at'] == '2026-03-14T08:30:00'
        assert result['created_at'] == '2026-03-14T08:30:00'

    def test_handles_none_timestamps(self):
        row = {
            'id': 1,
            'parameters': None,
            'started_at': datetime(2026, 3, 14),
            'completed_at': None,  # running job
            'created_at': datetime(2026, 3, 14),
        }

        result = self.repo._row_to_dict(row)

        assert result['completed_at'] is None


class TestDataAcquisitionsRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        with patch('src.data.aurora.data_acquisitions_repository.get_aurora_client'):
            import src.data.aurora.data_acquisitions_repository as module
            module._repository_instance = None

            repo1 = get_data_acquisitions_repository()
            repo2 = get_data_acquisitions_repository()

            assert repo1 is repo2

            # Clean up
            module._repository_instance = None
