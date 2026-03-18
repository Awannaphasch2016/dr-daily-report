# -*- coding: utf-8 -*-
"""
Unit tests for HkexFilingsRepository
"""

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.hkex_filings_repository import (
    HkexFilingsRepository,
    get_hkex_filings_repository,
)


class TestHkexFilingsRepositoryValidation:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = HkexFilingsRepository(client=self.mock_client)

    def test_upsert_raises_on_missing_required_fields(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            self.repo.upsert({'ticker_id': 1})

    def test_upsert_identifies_specific_missing_fields(self):
        with pytest.raises(ValueError) as exc_info:
            self.repo.upsert({'news_id': 'N123'})

        error_msg = str(exc_info.value)
        assert 'stock_code' in error_msg
        assert 'filing_date' in error_msg
        assert 'raw_data' in error_msg

    def test_upsert_accepts_all_required_fields(self):
        self.mock_client.execute.return_value = 1
        self.repo.upsert({
            'news_id': 'N123', 'stock_code': '00700',
            'filing_date': '2026-03-15', 'raw_data': {'key': 'value'},
        })


class TestHkexFilingsRepositoryUpsert:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = HkexFilingsRepository(client=self.mock_client)

        self.valid_filing = {
            'ticker_id': 1, 'symbol': 'TENCENT19',
            'news_id': 'N202503150001', 'stock_code': '00700',
            'filing_date': '2026-03-15', 'date_time': '15/03/2026 16:30',
            'category_code': '40000', 'subcategory_code': '40100',
            'stock_name': 'TENCENT', 'title': 'Annual Report 2025',
            'long_text': 'Full annual report', 'file_link': '/listedco/test.pdf',
            'file_url': 'https://www1.hkexnews.hk/listedco/test.pdf',
            'file_type': 'pdf', 'pdf_s3_key': None,
            'raw_data': {'full': 'response'}, 'acquisition_id': 99,
        }

    def test_upsert_returns_rowcount(self):
        assert self.repo.upsert(self.valid_filing) == 1

    def test_upsert_correct_17_element_params_tuple(self):
        self.repo.upsert(self.valid_filing)

        params = self.mock_client.execute.call_args[0][1]
        assert len(params) == 17
        assert params[0] == 1                                      # ticker_id
        assert params[1] == 'TENCENT19'                            # symbol
        assert params[2] == 'N202503150001'                        # news_id
        assert params[3] == '00700'                                # stock_code
        assert params[4] == '2026-03-15'                           # filing_date
        assert params[5] == '15/03/2026 16:30'                     # date_time
        assert params[6] == '40000'                                # category_code
        assert params[7] == '40100'                                # subcategory_code
        assert params[8] == 'TENCENT'                              # stock_name
        assert params[9] == 'Annual Report 2025'                   # title
        assert params[10] == 'Full annual report'                  # long_text
        assert params[11] == '/listedco/test.pdf'                  # file_link
        assert 'test.pdf' in params[12]                            # file_url
        assert params[13] == 'pdf'                                 # file_type
        assert params[14] is None                                  # pdf_s3_key
        assert params[15] == json.dumps({'full': 'response'})      # raw_data
        assert params[16] == 99                                    # acquisition_id

    def test_upsert_serializes_raw_data(self):
        self.repo.upsert(self.valid_filing)
        params = self.mock_client.execute.call_args[0][1]
        assert isinstance(params[15], str)
        assert json.loads(params[15]) == {'full': 'response'}

    def test_upsert_optional_fields_default_to_none(self):
        self.repo.upsert({
            'news_id': 'N123', 'stock_code': '00700',
            'filing_date': '2026-03-15', 'raw_data': {},
        })
        params = self.mock_client.execute.call_args[0][1]
        assert params[0] is None    # ticker_id
        assert params[1] is None    # symbol
        assert params[5] is None    # date_time
        assert params[6] is None    # category_code
        assert params[8] is None    # stock_name
        assert params[9] is None    # title
        assert params[14] is None   # pdf_s3_key
        assert params[16] is None   # acquisition_id


class TestHkexFilingsRepositoryBatchUpsert:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.repo = HkexFilingsRepository(client=self.mock_client)

    def test_batch_upsert_raises_on_empty(self):
        with pytest.raises(ValueError, match="Cannot upsert empty"):
            self.repo.batch_upsert([])

    def test_batch_upsert_returns_total(self):
        filings = [
            {'news_id': f'N{i}', 'stock_code': '00700',
             'filing_date': '2026-03-15', 'raw_data': {}}
            for i in range(3)
        ]
        assert self.repo.batch_upsert(filings) == 3

    def test_batch_upsert_stamps_acquisition_id(self):
        filings = [
            {'news_id': f'N{i}', 'stock_code': '00700',
             'filing_date': '2026-03-15', 'raw_data': {}}
            for i in range(2)
        ]
        self.repo.batch_upsert(filings, acquisition_id=99)
        for f in filings:
            assert f['acquisition_id'] == 99


class TestHkexFilingsRepositoryQuery:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.fetch_all.return_value = []
        self.repo = HkexFilingsRepository(client=self.mock_client)

    def test_get_filings_for_symbol(self):
        self.repo.get_filings_for_symbol('TENCENT19')
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'symbol = %s' in query
        assert params == ('TENCENT19',)

    def test_get_filings_for_stock_code(self):
        self.repo.get_filings_for_stock_code('00700')
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'stock_code = %s' in query
        assert params == ('00700',)

    def test_get_latest_filings(self):
        self.repo.get_latest_filings('TENCENT19', days=7)
        query = self.mock_client.fetch_all.call_args[0][0]
        params = self.mock_client.fetch_all.call_args[0][1]
        assert 'DATE_SUB(NOW(), INTERVAL %s DAY)' in query
        assert params == ('TENCENT19', 7)

    def test_get_filings_by_acquisition(self):
        self.repo.get_filings_by_acquisition(42)
        params = self.mock_client.fetch_all.call_args[0][1]
        assert params == (42,)

    def test_parses_raw_data_json(self):
        self.mock_client.fetch_all.return_value = [{
            'id': 1, 'ticker_id': 1, 'symbol': 'TENCENT19',
            'news_id': 'N1', 'stock_code': '00700',
            'filing_date': date(2026, 3, 15), 'date_time': '15/03/2026',
            'category_code': None, 'subcategory_code': None,
            'stock_name': 'TENCENT', 'title': 'test', 'long_text': None,
            'file_link': None, 'file_url': None, 'file_type': None,
            'pdf_s3_key': None, 'raw_data': '{"key": "value"}',
            'acquisition_id': 1,
            'fetched_at': datetime(2026, 3, 15),
            'created_at': datetime(2026, 3, 15),
            'updated_at': datetime(2026, 3, 15),
        }]
        results = self.repo.get_filings_for_symbol('TENCENT19')
        assert isinstance(results[0]['raw_data'], dict)
        assert results[0]['filing_date'] == '2026-03-15'


class TestHkexFilingsRepositoryRowToDict:

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = HkexFilingsRepository(client=self.mock_client)

    def test_parses_raw_data(self):
        row = {'raw_data': '{"k":"v"}', 'filing_date': None,
               'fetched_at': None, 'created_at': None, 'updated_at': None}
        assert isinstance(self.repo._row_to_dict(row)['raw_data'], dict)

    def test_converts_dates(self):
        row = {'raw_data': '{}', 'filing_date': date(2026, 3, 15),
               'fetched_at': datetime(2026, 3, 15, 9, 0),
               'created_at': None, 'updated_at': None}
        result = self.repo._row_to_dict(row)
        assert result['filing_date'] == '2026-03-15'
        assert result['fetched_at'] == '2026-03-15T09:00:00'

    def test_handles_none(self):
        row = {'raw_data': '{}', 'filing_date': date(2026, 3, 15),
               'fetched_at': None, 'created_at': None, 'updated_at': None}
        assert self.repo._row_to_dict(row)['fetched_at'] is None


class TestHkexFilingsRepositorySingleton:

    def test_singleton(self):
        with patch('src.data.aurora.hkex_filings_repository.get_aurora_client'):
            import src.data.aurora.hkex_filings_repository as mod
            mod._repository_instance = None
            r1 = get_hkex_filings_repository()
            r2 = get_hkex_filings_repository()
            assert r1 is r2
            mod._repository_instance = None
