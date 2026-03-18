# -*- coding: utf-8 -*-
"""
Unit tests for EdinetFilingsRepository

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

from src.data.aurora.edinet_filings_repository import (
    EdinetFilingsRepository,
    get_edinet_filings_repository,
)


class TestEdinetFilingsRepositoryValidation:
    """Tests for defensive validation (Principle #1)."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = EdinetFilingsRepository(client=self.mock_client)

    def test_upsert_raises_on_missing_required_fields(self):
        invalid_filing = {
            'ticker_id': 1,
            'symbol': 'NINTENDO19',
            # Missing: doc_id, filing_date, raw_data
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert(invalid_filing)

    def test_upsert_identifies_specific_missing_fields(self):
        partial_filing = {
            'doc_id': 'S100ABC1',
            # Missing: filing_date, raw_data
        }

        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert(partial_filing)

        error_msg = str(exc_info.value)
        assert 'filing_date' in error_msg
        assert 'raw_data' in error_msg

    def test_upsert_accepts_all_required_fields(self):
        self.mock_client.execute.return_value = 1

        valid_filing = {
            'doc_id': 'S100ABC1',
            'filing_date': '2026-03-15',
            'raw_data': {'key': 'value'},
        }

        # Should not raise
        self.repo.upsert(valid_filing)


class TestEdinetFilingsRepositoryUpsert:
    """Tests for upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = EdinetFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1,
            'symbol': 'NINTENDO19',
            'doc_id': 'S100ABC1',
            'edinet_code': 'E02116',
            'sec_code': '79740',
            'filing_date': '2026-03-15',
            'submit_date_time': '2026-03-15 09:00:00',
            'doc_type_code': '120',
            'doc_description': 'Annual Securities Report',
            'filer_name': 'Nintendo Co., Ltd.',
            'title': 'Annual Securities Report',
            'period_start': '2025-04-01',
            'period_end': '2026-03-31',
            'xbrl_flag': True,
            'pdf_flag': True,
            'english_doc_flag': True,
            'pdf_url': 'https://api.edinet-fsa.go.jp/api/v2/documents/S100ABC1?type=2',
            'pdf_s3_key': None,
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

    def test_upsert_correct_20_element_params_tuple(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert len(params) == 20
        assert params[0] == 1                                # ticker_id
        assert params[1] == 'NINTENDO19'                     # symbol
        assert params[2] == 'S100ABC1'                       # doc_id
        assert params[3] == 'E02116'                         # edinet_code
        assert params[4] == '79740'                          # sec_code
        assert params[5] == '2026-03-15'                     # filing_date
        assert params[6] == '2026-03-15 09:00:00'            # submit_date_time
        assert params[7] == '120'                            # doc_type_code
        assert params[8] == 'Annual Securities Report'       # doc_description
        assert params[9] == 'Nintendo Co., Ltd.'             # filer_name
        assert params[10] == 'Annual Securities Report'      # title
        assert params[11] == '2025-04-01'                    # period_start
        assert params[12] == '2026-03-31'                    # period_end
        assert params[13] is True                            # xbrl_flag
        assert params[14] is True                            # pdf_flag
        assert params[15] is True                            # english_doc_flag
        assert 'S100ABC1' in params[16]                      # pdf_url (contains doc_id)
        assert params[17] is None                            # pdf_s3_key
        assert params[18] == json.dumps({'full': 'response'})  # raw_data
        assert params[19] == 99                              # acquisition_id

    def test_upsert_serializes_raw_data_dict_to_json(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        raw_data_param = params[18]

        assert isinstance(raw_data_param, str)
        assert json.loads(raw_data_param) == {'full': 'response'}

    def test_upsert_passes_raw_data_string_as_is(self):
        filing = {**self.valid_filing, 'raw_data': '{"already": "serialized"}'}

        self.repo.upsert(filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[18] == '{"already": "serialized"}'

    def test_upsert_optional_fields_default_to_none(self):
        """Filing with only required fields -- optional fields should be None/False."""
        minimal_filing = {
            'doc_id': 'S100ABC1',
            'filing_date': '2026-03-15',
            'raw_data': {'key': 'value'},
        }

        self.repo.upsert(minimal_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert params[0] is None    # ticker_id
        assert params[1] is None    # symbol
        assert params[3] is None    # edinet_code
        assert params[4] is None    # sec_code
        assert params[6] is None    # submit_date_time
        assert params[7] is None    # doc_type_code
        assert params[8] is None    # doc_description
        assert params[9] is None    # filer_name
        assert params[10] is None   # title
        assert params[11] is None   # period_start
        assert params[12] is None   # period_end
        assert params[13] is False  # xbrl_flag
        assert params[14] is False  # pdf_flag
        assert params[15] is False  # english_doc_flag
        assert params[16] is None   # pdf_url
        assert params[17] is None   # pdf_s3_key
        assert params[19] is None   # acquisition_id


class TestEdinetFilingsRepositoryBatchUpsert:
    """Tests for batch upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = EdinetFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'doc_id': 'S100ABC1',
            'filing_date': '2026-03-15',
            'doc_type_code': '120',
            'raw_data': {'key': 'value'},
        }

    def test_batch_upsert_raises_on_empty_list(self):
        with pytest.raises(ValueError, match="Cannot upsert empty filings list"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total_rowcount(self):
        filings = [
            {**self.valid_filing, 'doc_id': f'S100{i:04d}'}
            for i in range(3)
        ]

        total = self.repo.batch_upsert(filings)

        assert total == 3

    def test_batch_upsert_stamps_acquisition_id(self):
        filings = [
            {**self.valid_filing, 'doc_id': f'S100{i:04d}'}
            for i in range(2)
        ]

        self.repo.batch_upsert(filings, acquisition_id=99)

        for filing in filings:
            assert filing['acquisition_id'] == 99

    def test_batch_upsert_respects_batch_size(self):
        filings = [
            {**self.valid_filing, 'doc_id': f'S100{i:04d}'}
            for i in range(5)
        ]

        self.repo.batch_upsert(filings, batch_size=2)

        # Each filing triggers one upsert call
        assert self.mock_client.execute.call_count == 5


class TestEdinetFilingsRepositoryQuery:
    """Tests for query operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = EdinetFilingsRepository(client=self.mock_client)

    def test_get_filings_for_date_basic(self):
        self.repo.get_filings_for_date('2026-03-15')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'filing_date = %s' in query
        assert params == ('2026-03-15',)

    def test_get_filings_for_date_with_doc_type(self):
        self.repo.get_filings_for_date('2026-03-15', doc_type_code='120')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'doc_type_code = %s' in query
        assert params == ('2026-03-15', '120')

    def test_get_filings_for_symbol_basic(self):
        self.repo.get_filings_for_symbol('NINTENDO19')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'symbol = %s' in query
        assert params == ('NINTENDO19',)

    def test_get_filings_for_symbol_with_date_range(self):
        self.repo.get_filings_for_symbol(
            'NINTENDO19',
            date_from='2026-01-01',
            date_to='2026-03-15',
        )

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'filing_date >= %s' in query
        assert 'filing_date <= %s' in query
        assert params == ('NINTENDO19', '2026-01-01', '2026-03-15')

    def test_get_filings_for_symbol_with_doc_type_filter(self):
        self.repo.get_filings_for_symbol('NINTENDO19', doc_type_code='120')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'doc_type_code = %s' in query
        assert params == ('NINTENDO19', '120')

    def test_get_filings_parses_raw_data_json(self):
        mock_row = {
            'id': 1,
            'ticker_id': 1,
            'symbol': 'NINTENDO19',
            'doc_id': 'S100ABC1',
            'edinet_code': 'E02116',
            'sec_code': '79740',
            'filing_date': date(2026, 3, 15),
            'submit_date_time': datetime(2026, 3, 15, 9, 0),
            'doc_type_code': '120',
            'doc_description': 'Annual Report',
            'filer_name': 'Nintendo',
            'title': 'Annual Report',
            'period_start': date(2025, 4, 1),
            'period_end': date(2026, 3, 31),
            'xbrl_flag': True,
            'pdf_flag': True,
            'english_doc_flag': True,
            'pdf_url': None,
            'pdf_s3_key': None,
            'raw_data': '{"key": "value"}',
            'acquisition_id': 1,
            'fetched_at': datetime(2026, 3, 15),
            'created_at': datetime(2026, 3, 15),
            'updated_at': datetime(2026, 3, 15),
        }
        self.mock_client.fetch_all.return_value = [mock_row]

        results = self.repo.get_filings_for_symbol('NINTENDO19')

        assert len(results) == 1
        assert isinstance(results[0]['raw_data'], dict)
        assert results[0]['raw_data']['key'] == 'value'

    def test_get_latest_filings(self):
        self.repo.get_latest_filings('NINTENDO19', days=7)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'DATE_SUB(NOW(), INTERVAL %s DAY)' in query
        assert params == ('NINTENDO19', 7)

    def test_get_filings_by_acquisition(self):
        self.repo.get_filings_by_acquisition(42)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'acquisition_id = %s' in query
        assert params == (42,)


class TestEdinetFilingsRepositoryRowToDict:
    """Tests for _row_to_dict() conversion."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = EdinetFilingsRepository(client=self.mock_client)

    def test_parses_raw_data_json(self):
        row = {
            'raw_data': '{"key": "value"}',
            'filing_date': None,
            'submit_date_time': None,
            'period_start': None,
            'period_end': None,
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
            'filing_date': None,
            'submit_date_time': None,
            'period_start': None,
            'period_end': None,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['raw_data'] == {'already': 'parsed'}

    def test_converts_datetime_to_isoformat(self):
        dt = datetime(2026, 3, 15, 9, 0, 0)
        row = {
            'raw_data': '{}',
            'filing_date': date(2026, 3, 15),
            'submit_date_time': dt,
            'period_start': date(2025, 4, 1),
            'period_end': date(2026, 3, 31),
            'fetched_at': dt,
            'created_at': dt,
            'updated_at': dt,
        }

        result = self.repo._row_to_dict(row)

        assert result['filing_date'] == '2026-03-15'
        assert result['submit_date_time'] == '2026-03-15T09:00:00'
        assert result['period_start'] == '2025-04-01'
        assert result['period_end'] == '2026-03-31'

    def test_converts_date_to_isoformat(self):
        d = date(2026, 3, 15)
        row = {
            'raw_data': '{}',
            'filing_date': d,
            'submit_date_time': None,
            'period_start': None,
            'period_end': None,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['filing_date'] == '2026-03-15'

    def test_handles_none_timestamps(self):
        row = {
            'raw_data': '{}',
            'filing_date': date(2026, 3, 15),
            'submit_date_time': None,
            'period_start': None,
            'period_end': None,
            'fetched_at': None,
            'created_at': None,
            'updated_at': None,
        }

        result = self.repo._row_to_dict(row)

        assert result['submit_date_time'] is None
        assert result['period_start'] is None
        assert result['period_end'] is None
        assert result['fetched_at'] is None


class TestEdinetFilingsRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        with patch('src.data.aurora.edinet_filings_repository.get_aurora_client'):
            import src.data.aurora.edinet_filings_repository as module
            module._repository_instance = None

            repo1 = get_edinet_filings_repository()
            repo2 = get_edinet_filings_repository()

            assert repo1 is repo2

            # Clean up
            module._repository_instance = None
