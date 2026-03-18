# -*- coding: utf-8 -*-
"""
Unit tests for IngestionMethodsRepository

Tests follow defensive programming principles:
- Runtime type validation
- CRUD operations
- Idempotent get_or_create
- JSON serialization for config_snapshot
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.aurora.ingestion_methods_repository import (
    IngestionMethodsRepository,
    get_ingestion_methods_repository,
)


class TestIngestionMethodsRepositoryValidation:
    """Tests for defensive validation."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = IngestionMethodsRepository(client=self.mock_client)

    def test_create_raises_on_invalid_runtime_type(self):
        with pytest.raises(ValueError, match="Invalid runtime_type"):
            self.repo.create(
                method_name='test-method',
                runtime_type='invalid_type',
            )

    def test_create_accepts_all_valid_runtime_types(self):
        self.mock_client.execute.return_value = 1
        self.mock_client.fetch_one.return_value = {'id': 1}

        for rt in ('ecs_fargate', 'lambda', 'local', 'step_functions', 'github_actions'):
            self.repo.create(method_name=f'test-{rt}', runtime_type=rt)


class TestIngestionMethodsRepositoryCreate:
    """Tests for create operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.mock_client.execute.return_value = 1
        self.mock_client.fetch_one.return_value = {'id': 42}
        self.repo = IngestionMethodsRepository(client=self.mock_client)

    def test_create_returns_id(self):
        method_id = self.repo.create(
            method_name='edinet-ecs-fargate-backfill',
            runtime_type='ecs_fargate',
            script_path='scripts/ingest_edinet_filings.py',
        )

        assert method_id == 42

    def test_create_serializes_config_snapshot_to_json(self):
        config = {"cpu": 256, "memory": 512}
        self.repo.create(
            method_name='test-method',
            runtime_type='ecs_fargate',
            config_snapshot=config,
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        # config_snapshot is the last param (index 5)
        assert params[5] == json.dumps(config)

    def test_create_passes_none_for_optional_fields(self):
        self.repo.create(
            method_name='test-method',
            runtime_type='local',
        )

        call_args = self.mock_client.execute.call_args
        params = call_args[0][1]
        assert params[0] == 'test-method'   # method_name
        assert params[1] == 'local'          # runtime_type
        assert params[2] is None             # script_path
        assert params[3] is None             # container_image
        assert params[4] is None             # description
        assert params[5] is None             # config_snapshot


class TestIngestionMethodsRepositoryGetByName:
    """Tests for get_by_name operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = IngestionMethodsRepository(client=self.mock_client)

    def test_get_by_name_returns_dict(self):
        self.mock_client.fetch_one.return_value = {
            'id': 1,
            'method_name': 'edinet-ecs-fargate-backfill',
            'runtime_type': 'ecs_fargate',
            'script_path': 'scripts/ingest_edinet_filings.py',
            'container_image': None,
            'description': 'test',
            'config_snapshot': '{"cpu": 256}',
            'is_active': True,
            'created_at': datetime(2026, 3, 16),
            'updated_at': datetime(2026, 3, 16),
        }

        result = self.repo.get_by_name('edinet-ecs-fargate-backfill')

        assert result is not None
        assert result['method_name'] == 'edinet-ecs-fargate-backfill'
        assert result['runtime_type'] == 'ecs_fargate'
        # config_snapshot should be parsed from JSON
        assert result['config_snapshot'] == {"cpu": 256}
        # datetimes should be ISO strings
        assert result['created_at'] == '2026-03-16T00:00:00'

    def test_get_by_name_returns_none_when_not_found(self):
        self.mock_client.fetch_one.return_value = None

        result = self.repo.get_by_name('nonexistent')

        assert result is None


class TestIngestionMethodsRepositoryGetOrCreate:
    """Tests for idempotent get_or_create."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = IngestionMethodsRepository(client=self.mock_client)

    def test_get_or_create_returns_existing(self):
        existing = {
            'id': 1,
            'method_name': 'test-method',
            'runtime_type': 'local',
            'script_path': None,
            'container_image': None,
            'description': None,
            'config_snapshot': None,
            'is_active': True,
            'created_at': datetime(2026, 3, 16),
            'updated_at': datetime(2026, 3, 16),
        }
        self.mock_client.fetch_one.return_value = existing

        result = self.repo.get_or_create(
            method_name='test-method',
            runtime_type='local',
        )

        assert result['id'] == 1
        # Should NOT have called execute (no INSERT)
        self.mock_client.execute.assert_not_called()

    def test_get_or_create_creates_when_not_found(self):
        # First call: get_by_name returns None (not found)
        # Second call after create: fetch_one returns the new id
        # Third call: get_by_name returns the created row
        self.mock_client.fetch_one.side_effect = [
            None,  # get_by_name: not found
            {'id': 5},  # LAST_INSERT_ID after create
            {  # get_by_name after create
                'id': 5,
                'method_name': 'new-method',
                'runtime_type': 'ecs_fargate',
                'script_path': None,
                'container_image': None,
                'description': None,
                'config_snapshot': None,
                'is_active': True,
                'created_at': datetime(2026, 3, 16),
                'updated_at': datetime(2026, 3, 16),
            },
        ]

        result = self.repo.get_or_create(
            method_name='new-method',
            runtime_type='ecs_fargate',
        )

        assert result['id'] == 5
        assert result['method_name'] == 'new-method'
        # Should have called execute once (INSERT)
        self.mock_client.execute.assert_called_once()


class TestIngestionMethodsRepositoryListActive:
    """Tests for list_active operations."""

    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = IngestionMethodsRepository(client=self.mock_client)

    def test_list_active_returns_list(self):
        self.mock_client.fetch_all.return_value = [
            {
                'id': 1,
                'method_name': 'method-a',
                'runtime_type': 'ecs_fargate',
                'script_path': None,
                'container_image': None,
                'description': None,
                'config_snapshot': None,
                'is_active': True,
                'created_at': datetime(2026, 3, 16),
                'updated_at': datetime(2026, 3, 16),
            },
        ]

        results = self.repo.list_active()

        assert len(results) == 1
        assert results[0]['method_name'] == 'method-a'

    def test_list_active_filters_by_is_active(self):
        self.mock_client.fetch_all.return_value = []

        self.repo.list_active()

        call_args = self.mock_client.fetch_all.call_args
        query = call_args[0][0]
        assert 'is_active = TRUE' in query


class TestIngestionMethodsRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repository_returns_same_instance(self):
        with patch('src.data.aurora.ingestion_methods_repository.get_aurora_client'):
            import src.data.aurora.ingestion_methods_repository as module
            module._repository_instance = None

            repo1 = get_ingestion_methods_repository()
            repo2 = get_ingestion_methods_repository()

            assert repo1 is repo2

            # Clean up
            module._repository_instance = None
