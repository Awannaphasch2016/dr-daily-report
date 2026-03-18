# -*- coding: utf-8 -*-
"""
Unit tests for MopsFilingsRepository
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.mops_filings_repository import (
    MopsFilingsRepository,
    get_mops_filings_repository,
)


class TestMopsFilingsRepositoryValidation:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = MopsFilingsRepository(client=self.mock_client)

    def test_upsert_raises_on_missing_required_fields(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert({'ticker_id': 1})

    def test_upsert_identifies_specific_missing_fields(self):
        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert({'filename': '202312_0050_AI3.pdf'})

        error_msg = str(exc_info.value)
        assert 'stock_code' in error_msg
        assert 'report_year' in error_msg
        assert 'raw_data' in error_msg

    def test_upsert_accepts_all_required_fields(self):
        self.mock_client.execute.return_value = 1
        self.repo.upsert({
            'filename': '202312_0050_AI3.pdf', 'stock_code': '0050',
            'report_year': 2023, 'report_type': 'financial_statement',
            'raw_data': {'key': 'value'},
        })


class TestMopsFilingsRepositoryUpsert:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = MopsFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1, 'symbol': 'TAIWAN19',
            'filename': '202312_0050_AI3.pdf', 'stock_code': '0050',
            'filing_date': '2023-12-31', 'report_year': 2023,
            'report_type': 'financial_statement', 'report_period': 'annual',
            'mtype': 'A', 'dtype': 'AI3',
            'company_name': 'Yuanta/P-shares Taiwan Top 50 ETF',
            'title': 'Annual Consolidated Financial Statements 2023',
            'file_url': 'https://doc.twse.com.tw/pdf/test.pdf',
            'pdf_s3_key': None,
            'raw_data': {'full': 'response'}, 'acquisition_id': 99,
        }

    def test_upsert_returns_rowcount(self):
        assert self.repo.upsert(self.valid_filing) == 1

    def test_upsert_correct_16_element_params_tuple(self):
        self.repo.upsert(self.valid_filing)

        params = self.mock_client.execute.call_args[0][1]
        assert len(params) == 16
        assert params[0] == 1                                           # ticker_id
        assert params[1] == 'TAIWAN19'                                  # symbol
        assert params[2] == '202312_0050_AI3.pdf'                       # filename
        assert params[3] == '0050'                                      # stock_code
        assert params[4] == '2023-12-31'                                # filing_date
        assert params[5] == 2023                                        # report_year
        assert params[6] == 'financial_statement'                       # report_type
        assert params[7] == 'annual'                                    # report_period
        assert params[8] == 'A'                                         # mtype
        assert params[9] == 'AI3'                                       # dtype
        assert params[10] == 'Yuanta/P-shares Taiwan Top 50 ETF'        # company_name
        assert params[11] == 'Annual Consolidated Financial Statements 2023'  # title
        assert 'test.pdf' in params[12]                                 # file_url
        assert params[13] is None                                       # pdf_s3_key
        assert params[14] == json.dumps({'full': 'response'})           # raw_data
        assert params[15] == 99                                         # acquisition_id

    def test_upsert_serializes_raw_data(self):
        self.repo.upsert(self.valid_filing)
        params = self.mock_client.execute.call_args[0][1]
        assert isinstance(params[14], str)
        assert json.loads(params[14]) == {'full': 'response'}

    def test_upsert_optional_fields_default_to_none(self):
        self.repo.upsert({
            'filename': 'test.pdf', 'stock_code': '0050',
            'report_year': 2023, 'report_type': 'annual_report',
            'raw_data': {},
        })
        params = self.mock_client.execute.call_args[0][1]
        assert params[0] is None    # ticker_id
        assert params[1] is None    # symbol
        assert params[4] is None    # filing_date
        assert params[7] is None    # report_period
        assert params[8] is None    # mtype
        assert params[10] is None   # company_name
        assert params[13] is None   # pdf_s3_key
        assert params[15] is None   # acquisition_id


class TestMopsFilingsRepositoryBatchUpsert:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = MopsFilingsRepository(client=self.mock_client)

    def test_batch_upsert_raises_on_empty(self):
        with pytest.raises(ValueError, match="Cannot upsert empty"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total(self):
        filings = [
            {'filename': f'file_{i}.pdf', 'stock_code': '0050',
             'report_year': 2023, 'report_type': 'annual_report', 'raw_data': {}}
            for i in range(3)
        ]
        assert self.repo.batch_upsert(filings) == 3

    def test_batch_upsert_stamps_acquisition_id(self):
        filings = [
            {'filename': f'file_{i}.pdf', 'stock_code': '0050',
             'report_year': 2023, 'report_type': 'annual_report', 'raw_data': {}}
            for i in range(2)
        ]
        self.repo.batch_upsert(filings, acquisition_id=99)
        for f in filings:
            assert f['acquisition_id'] == 99


class TestMopsFilingsRepositoryQuery:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = MopsFilingsRepository(client=self.mock_client)

    def test_get_filings_for_symbol(self):
        self.repo.get_filings_for_symbol('TAIWAN19')
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'symbol = %s' in query
        assert params == ('TAIWAN19',)

    def test_get_filings_for_stock_code(self):
        self.repo.get_filings_for_stock_code('0050')
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'stock_code = %s' in query
        assert params == ('0050',)

    def test_get_latest_filings(self):
        self.repo.get_latest_filings('TAIWAN19', days=365)
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'DATE_SUB(NOW(), INTERVAL %s DAY)' in query
        assert params == ('TAIWAN19', 365)

    def test_get_filings_by_acquisition(self):
        self.repo.get_filings_by_acquisition(42)
        params = self.mock_client.fetch_all.call_args[0][1]
        assert params == (42,)

    def test_parses_raw_data_json(self):
        self.mock_client.fetch_all.return_value = [{
            'id': 1, 'ticker_id': 1, 'symbol': 'TAIWAN19',
            'filename': '202312_0050_AI3.pdf', 'stock_code': '0050',
            'filing_date': date(2023, 12, 31), 'report_year': 2023,
            'report_type': 'financial_statement', 'report_period': 'annual',
            'mtype': 'A', 'dtype': 'AI3',
            'company_name': 'Taiwan 50 ETF', 'title': 'test',
            'file_url': None, 'pdf_s3_key': None,
            'raw_data': '{"key": "value"}',
            'acquisition_id': 1,
            'fetched_at': datetime(2026, 3, 16),
            'created_at': datetime(2026, 3, 16),
            'updated_at': datetime(2026, 3, 16),
        }]
        results = self.repo.get_filings_for_symbol('TAIWAN19')
        assert isinstance(results[0]['raw_data'], dict)
        assert results[0]['filing_date'] == '2023-12-31'


class TestMopsFilingsRepositoryRowToDict:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = MopsFilingsRepository(client=self.mock_client)

    def test_parses_raw_data(self):
        row = {'raw_data': '{"k":"v"}', 'filing_date': None,
               'fetched_at': None, 'created_at': None, 'updated_at': None}
        assert isinstance(self.repo._row_to_dict(row)['raw_data'], dict)

    def test_converts_dates(self):
        row = {'raw_data': '{}', 'filing_date': date(2023, 12, 31),
               'fetched_at': datetime(2026, 3, 16, 9, 0),
               'created_at': None, 'updated_at': None}
        result = self.repo._row_to_dict(row)
        assert result['filing_date'] == '2023-12-31'
        assert result['fetched_at'] == '2026-03-16T09:00:00'

    def test_handles_none(self):
        row = {'raw_data': '{}', 'filing_date': date(2023, 12, 31),
               'fetched_at': None, 'created_at': None, 'updated_at': None}
        assert self.repo._row_to_dict(row)['fetched_at'] is None


class TestMopsFilingsRepositorySingleton:

    def test_singleton(self):
        with patch('src.data.aurora.mops_filings_repository.get_aurora_client'):
            import src.data.aurora.mops_filings_repository as mod
            mod._repository_instance = None
            r1 = get_mops_filings_repository()
            r2 = get_mops_filings_repository()
            assert r1 is r2
            mod._repository_instance = None
