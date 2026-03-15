# -*- coding: utf-8 -*-
"""Tests for MetricConfigRepository."""

import pytest
from unittest.mock import MagicMock
from src.data.aurora.metric_config_repository import MetricConfigRepository


class TestMetricConfigRepository:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = MetricConfigRepository(client=self.mock_client)

    def test_get_all_statuses_returns_dict(self):
        self.mock_client.fetch_all.return_value = [
            {'metric_id': 'atr_pct', 'status': 'ready'},
            {'metric_id': 'uncertainty', 'status': 'deprecated'},
        ]
        result = self.repo.get_all_statuses()
        assert result == {'atr_pct': 'ready', 'uncertainty': 'deprecated'}

    def test_get_all_statuses_caches(self):
        self.mock_client.fetch_all.return_value = [
            {'metric_id': 'rsi', 'status': 'ready'},
        ]
        # First call
        result1 = self.repo.get_all_statuses()
        # Second call should use cache
        result2 = self.repo.get_all_statuses()
        assert result1 == result2
        assert self.mock_client.fetch_all.call_count == 1

    def test_get_status_single(self):
        self.mock_client.fetch_all.return_value = [
            {'metric_id': 'rsi', 'status': 'ready'},
            {'metric_id': 'uncertainty', 'status': 'deprecated'},
        ]
        assert self.repo.get_status('rsi') == 'ready'
        assert self.repo.get_status('uncertainty') == 'deprecated'
        assert self.repo.get_status('nonexistent') is None

    def test_clear_cache(self):
        self.mock_client.fetch_all.return_value = [
            {'metric_id': 'rsi', 'status': 'ready'},
        ]
        self.repo.get_all_statuses()
        self.repo.clear_cache()
        self.mock_client.fetch_all.return_value = [
            {'metric_id': 'rsi', 'status': 'deprecated'},
        ]
        result = self.repo.get_all_statuses()
        assert result['rsi'] == 'deprecated'
        assert self.mock_client.fetch_all.call_count == 2

    def test_empty_table(self):
        self.mock_client.fetch_all.return_value = []
        result = self.repo.get_all_statuses()
        assert result == {}
