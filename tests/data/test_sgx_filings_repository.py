# -*- coding: utf-8 -*-
"""
Unit tests for SgxFilingsRepository (Principle #19: Cross-Boundary Testing)

Tests follow defensive programming principles:
- Required field validation
- Upsert SQL parameter ordering
- JSON serialization / datetime conversion
- Batch operations
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.sgx_filings_repository import (
    SgxFilingsRepository,
    get_sgx_filings_repository,
)


class TestSgxFilingsRepositoryValidation:
    """Tests for defensive validation (Principle #1)."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = SgxFilingsRepository(client=self.mock_client)

    def test_upsert_raises_on_missing_required_fields(self):
        invalid_filing = {
            'ticker_id': 1,
            'symbol': 'DBS19',
            # Missing: ann_id, broadcast_date_time, title, raw_data
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert(invalid_filing)

    def test_upsert_identifies_specific_missing_fields(self):
        partial_filing = {
            'ann_id': 'ABC123',
            # Missing: broadcast_date_time, title, raw_data
        }

        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert(partial_filing)

        error_msg = str(exc_info.value)
        assert 'broadcast_date_time' in error_msg
        assert 'title' in error_msg
        assert 'raw_data' in error_msg

    def test_upsert_accepts_all_required_fields(self):
        self.mock_client.execute.return_value = 1

        valid_filing = {
            'ticker_id': 1,
            'symbol': 'DBS19',
            'ann_id': 'ABC123',
            'broadcast_date_time': '2026-03-14 08:30:00',
            'title': 'Annual Report',
            'raw_data': {'key': 'value'},
        }

        # Should not raise — category_code/subcategory_code are optional
        self.repo.upsert(valid_filing)


class TestSgxFilingsRepositoryUpsert:
    """Tests for upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = SgxFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1,
            'symbol': 'DBS19',
            'ann_id': 'ABC123',
            'broadcast_date_time': '2026-03-14 08:30:00',
            'category_code': 'ANNC',
            'subcategory_code': 'ANNC09',
            'subcategory_name': 'Annual Reports',
            'title': 'Quarterly Results',
            'issuer_name': 'DBS Group Holdings',
            'stock_code': 'D05',
            'attachment_url': 'https://example.com/report.pdf',
            'sgx_url': 'https://www.sgx.com/announcements',
            'raw_data': {'full': 'response'},
            'acquisition_id': 99,
        }

    def test_upsert_returns_rowcount(self):
        rowcount = self.repo.upsert(self.valid_filing)

        assert isinstance(rowcount, int)
        assert rowcount == 1

    def test_upsert_returns_2_on_duplicate_key_update(self):
        self.mock_client.execute.return_value = 2

        rowcount = self.repo.upsert(self.valid_filing)

        assert rowcount == 2

    def test_upsert_correct_15_element_params_tuple(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert len(params) == 15
        assert params[0] == 1                               # ticker_id
        assert params[1] == 'DBS19'                         # symbol
        assert params[2] == 'ABC123'                        # ann_id
        assert params[3] == '2026-03-14 08:30:00'           # broadcast_date_time
        assert params[4] == 'ANNC'                          # category_code
        assert params[5] == 'ANNC09'                        # subcategory_code
        assert params[6] == 'Annual Reports'                # subcategory_name
        assert params[7] == 'Quarterly Results'             # title
        assert params[8] == 'DBS Group Holdings'            # issuer_name
        assert params[9] == 'D05'                           # stock_code
        assert params[10] == 'https://example.com/report.pdf'  # attachment_url
        assert params[11] is None                           # attachment_s3_key
        assert params[12] == 'https://www.sgx.com/announcements'  # sgx_url
        assert params[13] == json.dumps({'full': 'response'})  # raw_data
        assert params[14] == 99                             # acquisition_id

    def test_upsert_serializes_raw_data_dict_to_json(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        raw_data_param = params[13]

        assert isinstance(raw_data_param, str)
        assert json.loads(raw_data_param) == {'full': 'response'}

    def test_upsert_passes_raw_data_string_as_is(self):
        filing = {**self.valid_filing, 'raw_data': '{"already": "serialized"}'}

        self.repo.upsert(filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[13] == '{"already": "serialized"}'

    def test_upsert_optional_fields_default_to_none(self):
        """Filing with only required fields -- optional fields should be None."""
        minimal_filing = {
            'ann_id': 'ABC123',
            'broadcast_date_time': '2026-03-14 08:30:00',
            'title': 'Annual Report',
            'raw_data': {'key': 'value'},
        }

        self.repo.upsert(minimal_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert params[0] is None   # ticker_id
        assert params[1] is None   # symbol
        assert params[4] is None   # category_code (now uses .get())
        assert params[5] is None   # subcategory_code (now uses .get())
        assert params[6] is None   # subcategory_name
        assert params[8] is None   # issuer_name
        assert params[9] is None   # stock_code
        assert params[10] is None  # attachment_url
        assert params[11] is None  # attachment_s3_key
        assert params[12] is None  # sgx_url
        assert params[14] is None  # acquisition_id


class TestSgxFilingsRepositoryBatchUpsert:
    """Tests for batch upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = SgxFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1,
            'symbol': 'DBS19',
            'ann_id': 'ABC123',
            'broadcast_date_time': '2026-03-14 08:30:00',
            'category_code': 'ANNC',
            'subcategory_code': 'ANNC09',
            'title': 'Quarterly Results',
            'raw_data': {'key': 'value'},
        }

    def test_batch_upsert_raises_on_empty_list(self):
        with pytest.raises(ValueError, match="Cannot upsert empty filings list"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total_rowcount(self):
        filings = [
            {**self.valid_filing, 'ann_id': f'ID{i}'}
            for i in range(3)
        ]

        total = self.repo.batch_upsert(filings)

        assert total == 3

    def test_batch_upsert_stamps_acquisition_id(self):
        filings = [
            {**self.valid_filing, 'ann_id': f'ID{i}'}
            for i in range(2)
        ]

        self.repo.batch_upsert(filings, acquisition_id=99)

        for filing in filings:
            assert filing['acquisition_id'] == 99

    def test_batch_upsert_respects_batch_size(self):
        filings = [
            {**self.valid_filing, 'ann_id': f'ID{i}'}
            for i in range(5)
        ]

        self.repo.batch_upsert(filings, batch_size=2)

        # Each filing triggers one upsert call
        assert self.mock_client.execute.call_count == 5


class TestSgxFilingsRepositoryQuery:
    """Tests for query operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = SgxFilingsRepository(client=self.mock_client)

    def test_get_filings_for_symbol_basic(self):
        self.repo.get_filings_for_symbol('DBS19')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'symbol = %s' in query
        assert params == ('DBS19',)

    def test_get_filings_for_symbol_with_date_range(self):
        self.repo.get_filings_for_symbol(
            'DBS19',
            date_from='2026-01-01',
            date_to='2026-03-14',
        )

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'broadcast_date_time >= %s' in query
        assert 'broadcast_date_time <= %s' in query
        assert params == ('DBS19', '2026-01-01', '2026-03-14')

    def test_get_filings_for_symbol_with_subcategory_filter(self):
        self.repo.get_filings_for_symbol('DBS19', subcategory_code='ANNC09')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'subcategory_code = %s' in query
        assert params == ('DBS19', 'ANNC09')

    def test_get_filings_for_symbol_parses_raw_data_json(self):
        mock_row = {
            'id': 1,
            'ticker_id': 1,
            'symbol': 'DBS19',
            'ann_id': 'ABC123',
            'broadcast_date_time': datetime(2026, 3, 14, 8, 30),
            'category_code': 'ANNC',
            'subcategory_code': 'ANNC09',
            'subcategory_name': None,
            'title': 'Annual Report',
            'issuer_name': 'DBS',
            'stock_code': 'D05',
            'attachment_url': None,
            'sgx_url': None,
            'raw_data': '{"key": "value"}',
            'acquisition_id': 1,
            'fetched_at': datetime(2026, 3, 14),
            'created_at': datetime(2026, 3, 14),
            'updated_at': datetime(2026, 3, 14),
        }
        self.mock_client.fetch_all.return_value = [mock_row]

        results = self.repo.get_filings_for_symbol('DBS19')

        assert len(results) == 1
        assert isinstance(results[0]['raw_data'], dict)
        assert results[0]['raw_data']['key'] == 'value'

    def test_get_latest_filings(self):
        self.repo.get_latest_filings('DBS19', days=7)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'DATE_SUB(NOW(), INTERVAL %s DAY)' in query
        assert params == ('DBS19', 7)

    def test_get_filings_by_acquisition(self):
        self.repo.get_filings_by_acquisition(42)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'acquisition_id = %s' in query
        assert params == (42,)


class TestSgxFilingsRepositoryRowToDict:
    """Tests for _row_to_dict() conversion."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = SgxFilingsRepository(client=self.mock_client)

    def test_parses_raw_data_json(self):
        row = {
            'raw_data': '{"key": "value"}',
            'broadcast_date_time': None,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert isinstance(result['raw_data'], dict)
        assert result['raw_data']['key'] == 'value'

    def test_leaves_dict_raw_data_unchanged(self):
        row = {
            'raw_data': {'already': 'parsed'},
            'broadcast_date_time': None,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['raw_data'] == {'already': 'parsed'}

    def test_converts_datetime_to_isoformat(self):
        dt = datetime(2026, 3, 14, 8, 30, 0)
        row = {
            'raw_data': '{}',
            'broadcast_date_time': dt,
            'fetched_at': dt,
            'created_at': dt,
            'updated_at': dt,
        }

        result = self.repo._row_to_dict(row)

        assert result['broadcast_date_time'] == '2026-03-14T08:30:00'
        assert result['fetched_at'] == '2026-03-14T08:30:00'

    def test_converts_date_to_isoformat(self):
        d = date(2026, 3, 14)
        row = {
            'raw_data': '{}',
            'broadcast_date_time': d,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['broadcast_date_time'] == '2026-03-14'

    def test_handles_none_timestamps(self):
        row = {
            'raw_data': '{}',
            'broadcast_date_time': datetime(2026, 3, 14),
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['fetched_at'] is None
        assert result['created_at'] is None
        assert result['updated_at'] is None


class TestSgxFilingsRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        with patch('src.data.aurora.sgx_filings_repository.get_aurora_client'):
            import src.data.aurora.sgx_filings_repository as module
            module._repository_instance = None

            repo1 = get_sgx_filings_repository()
            repo2 = get_sgx_filings_repository()

            assert repo1 is repo2

            # Clean up
            module._repository_instance = None
