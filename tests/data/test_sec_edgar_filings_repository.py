# -*- coding: utf-8 -*-
"""
Unit tests for SecEdgarFilingsRepository
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.sec_edgar_filings_repository import (
    SecEdgarFilingsRepository,
    get_sec_edgar_filings_repository,
)


class TestSecEdgarFilingsRepositoryValidation:
    """Tests for defensive validation."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = SecEdgarFilingsRepository(client=self.mock_client)

    def test_upsert_raises_on_missing_required_fields(self):
        invalid_filing = {'ticker_id': 1, 'symbol': 'NVDA19'}

        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert(invalid_filing)

    def test_upsert_identifies_specific_missing_fields(self):
        partial_filing = {
            'accession_number': '0000320193-24-000123',
            # Missing: cik, filing_date, raw_data
        }

        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert(partial_filing)

        error_msg = str(exc_info.value)
        assert 'cik' in error_msg
        assert 'filing_date' in error_msg
        assert 'raw_data' in error_msg

    def test_upsert_accepts_all_required_fields(self):
        self.mock_client.execute.return_value = 1

        valid_filing = {
            'accession_number': '0000320193-24-000123',
            'cik': '320193',
            'filing_date': '2024-11-01',
            'raw_data': {'key': 'value'},
        }

        self.repo.upsert(valid_filing)


class TestSecEdgarFilingsRepositoryUpsert:
    """Tests for upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = SecEdgarFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1,
            'symbol': 'NVDA19',
            'accession_number': '0001045810-24-000123',
            'cik': '1045810',
            'form_type': '10-K',
            'filing_date': '2024-11-01',
            'report_date': '2024-10-31',
            'acceptance_datetime': '2024-11-01 16:05:25',
            'company_name': 'NVIDIA CORP',
            'title': 'Annual Report',
            'primary_document': 'nvda-20241031.htm',
            'primary_doc_url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/nvda-20241031.htm',
            'filing_index_url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581024000123/',
            'pdf_s3_key': None,
            'raw_data': {'full': 'response'},
            'acquisition_id': 99,
        }

    def test_upsert_returns_rowcount(self):
        rowcount = self.repo.upsert(self.valid_filing)
        assert rowcount == 1

    def test_upsert_returns_2_on_duplicate(self):
        self.mock_client.execute.return_value = 2
        rowcount = self.repo.upsert(self.valid_filing)
        assert rowcount == 2

    def test_upsert_correct_16_element_params_tuple(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert len(params) == 16
        assert params[0] == 1                                    # ticker_id
        assert params[1] == 'NVDA19'                             # symbol
        assert params[2] == '0001045810-24-000123'               # accession_number
        assert params[3] == '1045810'                            # cik
        assert params[4] == '10-K'                               # form_type
        assert params[5] == '2024-11-01'                         # filing_date
        assert params[6] == '2024-10-31'                         # report_date
        assert params[7] == '2024-11-01 16:05:25'                # acceptance_datetime
        assert params[8] == 'NVIDIA CORP'                        # company_name
        assert params[9] == 'Annual Report'                      # title
        assert params[10] == 'nvda-20241031.htm'                 # primary_document
        assert 'nvda-20241031.htm' in params[11]                 # primary_doc_url
        assert params[12] is not None                            # filing_index_url
        assert params[13] is None                                # pdf_s3_key
        assert params[14] == json.dumps({'full': 'response'})    # raw_data
        assert params[15] == 99                                  # acquisition_id

    def test_upsert_serializes_raw_data_dict_to_json(self):
        self.repo.upsert(self.valid_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert isinstance(params[14], str)
        assert json.loads(params[14]) == {'full': 'response'}

    def test_upsert_optional_fields_default_to_none(self):
        minimal_filing = {
            'accession_number': '0000320193-24-000123',
            'cik': '320193',
            'filing_date': '2024-11-01',
            'raw_data': {'key': 'value'},
        }

        self.repo.upsert(minimal_filing)

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]

        assert params[0] is None    # ticker_id
        assert params[1] is None    # symbol
        assert params[4] is None    # form_type
        assert params[6] is None    # report_date
        assert params[7] is None    # acceptance_datetime
        assert params[8] is None    # company_name
        assert params[10] is None   # primary_document
        assert params[11] is None   # primary_doc_url
        assert params[12] is None   # filing_index_url
        assert params[13] is None   # pdf_s3_key
        assert params[15] is None   # acquisition_id


class TestSecEdgarFilingsRepositoryBatchUpsert:
    """Tests for batch upsert operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = SecEdgarFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'accession_number': '0000320193-24-000123',
            'cik': '320193',
            'filing_date': '2024-11-01',
            'form_type': '10-K',
            'raw_data': {'key': 'value'},
        }

    def test_batch_upsert_raises_on_empty_list(self):
        with pytest.raises(ValueError, match="Cannot upsert empty filings list"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total_rowcount(self):
        filings = [
            {**self.valid_filing, 'accession_number': f'0000320193-24-{i:06d}'}
            for i in range(3)
        ]
        total = self.repo.batch_upsert(filings)
        assert total == 3

    def test_batch_upsert_stamps_acquisition_id(self):
        filings = [
            {**self.valid_filing, 'accession_number': f'0000320193-24-{i:06d}'}
            for i in range(2)
        ]
        self.repo.batch_upsert(filings, acquisition_id=99)
        for filing in filings:
            assert filing['acquisition_id'] == 99


class TestSecEdgarFilingsRepositoryQuery:
    """Tests for query operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = SecEdgarFilingsRepository(client=self.mock_client)

    def test_get_filings_for_symbol_basic(self):
        self.repo.get_filings_for_symbol('NVDA19')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'symbol = %s' in query
        assert params == ('NVDA19',)

    def test_get_filings_for_symbol_with_form_type(self):
        self.repo.get_filings_for_symbol('NVDA19', form_type='10-K')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'form_type = %s' in query
        assert params == ('NVDA19', '10-K')

    def test_get_filings_for_cik_basic(self):
        self.repo.get_filings_for_cik('1045810')

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'cik = %s' in query
        assert params == ('1045810',)

    def test_get_latest_filings(self):
        self.repo.get_latest_filings('NVDA19', days=7)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'DATE_SUB(NOW(), INTERVAL %s DAY)' in query
        assert params == ('NVDA19', 7)

    def test_get_filings_by_acquisition(self):
        self.repo.get_filings_by_acquisition(42)

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert 'acquisition_id = %s' in query
        assert params == (42,)

    def test_get_filings_parses_raw_data_json(self):
        mock_row = {
            'id': 1, 'ticker_id': 1, 'symbol': 'NVDA19',
            'accession_number': '0001045810-24-000123', 'cik': '1045810',
            'form_type': '10-K',
            'filing_date': date(2024, 11, 1),
            'report_date': date(2024, 10, 31),
            'acceptance_datetime': datetime(2024, 11, 1, 16, 5),
            'company_name': 'NVIDIA', 'title': 'Annual Report',
            'primary_document': 'nvda.htm', 'primary_doc_url': None,
            'filing_index_url': None, 'pdf_s3_key': None,
            'raw_data': '{"key": "value"}', 'acquisition_id': 1,
            'fetched_at': datetime(2024, 11, 1),
            'created_at': datetime(2024, 11, 1),
            'updated_at': datetime(2024, 11, 1),
        }
        self.mock_client.fetch_all.return_value = [mock_row]

        results = self.repo.get_filings_for_symbol('NVDA19')

        assert len(results) == 1
        assert isinstance(results[0]['raw_data'], dict)
        assert results[0]['filing_date'] == '2024-11-01'
        assert results[0]['report_date'] == '2024-10-31'


class TestSecEdgarFilingsRepositoryRowToDict:
    """Tests for _row_to_dict() conversion."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = SecEdgarFilingsRepository(client=self.mock_client)

    def test_parses_raw_data_json(self):
        row = {
            'raw_data': '{"key": "value"}',
            'filing_date': None, 'report_date': None,
            'acceptance_datetime': None,
            'fetched_at': None, 'created_at': None, 'updated_at': None,
        }
        result = self.repo._row_to_dict(row)
        assert isinstance(result['raw_data'], dict)

    def test_converts_datetime_to_isoformat(self):
        row = {
            'raw_data': '{}',
            'filing_date': date(2024, 11, 1),
            'report_date': date(2024, 10, 31),
            'acceptance_datetime': datetime(2024, 11, 1, 16, 5),
            'fetched_at': datetime(2024, 11, 1),
            'created_at': datetime(2024, 11, 1),
            'updated_at': datetime(2024, 11, 1),
        }
        result = self.repo._row_to_dict(row)
        assert result['filing_date'] == '2024-11-01'
        assert result['report_date'] == '2024-10-31'
        assert result['acceptance_datetime'] == '2024-11-01T16:05:00'

    def test_handles_none_timestamps(self):
        row = {
            'raw_data': '{}',
            'filing_date': date(2024, 11, 1),
            'report_date': None, 'acceptance_datetime': None,
            'fetched_at': None, 'created_at': None, 'updated_at': None,
        }
        result = self.repo._row_to_dict(row)
        assert result['report_date'] is None
        assert result['acceptance_datetime'] is None


class TestSecEdgarFilingsRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        with patch('src.data.aurora.sec_edgar_filings_repository.get_aurora_client'):
            import src.data.aurora.sec_edgar_filings_repository as module
            module._repository_instance = None

            repo1 = get_sec_edgar_filings_repository()
            repo2 = get_sec_edgar_filings_repository()

            assert repo1 is repo2

            module._repository_instance = None
