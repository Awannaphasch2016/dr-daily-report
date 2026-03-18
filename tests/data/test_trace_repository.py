# -*- coding: utf-8 -*-
"""Tests for TraceRepository."""

import json
import pytest
from unittest.mock import MagicMock, call
from src.data.aurora.trace_repository import TraceRepository


class TestTraceRepository:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.repo = TraceRepository(client=self.mock_client)

    def test_insert_trace_returns_id(self):
        self.mock_client.fetch_one.return_value = {'id': 42}

        trace_id = self.repo.insert_trace({
            'trace_type': 'report_generation',
            'model_id': 'openai/gpt-4o',
            'prompt_version': 'v4.2',
            'agent_type': 'single-stage',
            'release': 'abc123f',
            'trace_provider': 'langfuse',
            'trace_external_id': None,
            'context': {'symbol': 'AAPL', 'report_date': '2026-03-17'},
            'status': 'completed',
        })

        assert trace_id == 42
        self.mock_client.execute.assert_called_once()
        self.mock_client.fetch_one.assert_called_once()

    def test_insert_trace_serializes_context_json(self):
        self.mock_client.fetch_one.return_value = {'id': 1}
        context = {'symbol': 'AAPL', 'report_date': '2026-03-17'}

        self.repo.insert_trace({
            'trace_type': 'report_generation',
            'context': context,
        })

        # Verify context was JSON-serialized in params
        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]  # second positional arg = params tuple
        # context is the 8th param (index 7)
        assert params[7] == json.dumps(context)

    def test_insert_trace_handles_null_context(self):
        self.mock_client.fetch_one.return_value = {'id': 1}

        self.repo.insert_trace({
            'trace_type': 'sgx_ingestion',
            'context': None,
        })

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        assert params[7] is None  # context param

    def test_insert_trace_defaults_status_to_completed(self):
        self.mock_client.fetch_one.return_value = {'id': 1}

        self.repo.insert_trace({'trace_type': 'report_generation'})

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        assert params[8] == 'completed'  # status param

    def test_insert_scores_returns_count(self):
        scores = {
            'faithfulness': {
                'value': 85.0,
                'scorer_type': 'rule',
                'scorer_version': '1.0',
                'sub_scores': {'numeric_accuracy': 92, 'percentile_accuracy': 78},
                'config': None,
                'comment': 'numeric_accuracy=92.0, percentile_accuracy=78.0',
            },
            'completeness': {
                'value': 72.0,
                'scorer_type': 'rule',
                'scorer_version': '1.0',
                'sub_scores': {'context': 80, 'analysis_dim': 75},
                'config': None,
                'comment': None,
            },
            'placeholder_compliance': {
                'value': 95.5,
                'scorer_type': 'computed',
                'scorer_version': '1.0',
                'sub_scores': {'injected': 42, 'unresolved': 2, 'orphan': 0},
                'config': None,
                'comment': 'injected=42, unresolved=2, orphan=0',
            },
        }

        count = self.repo.insert_scores(trace_id=42, scores=scores)

        assert count == 3
        assert self.mock_client.execute.call_count == 3

    def test_insert_scores_serializes_sub_scores_json(self):
        scores = {
            'faithfulness': {
                'value': 85.0,
                'sub_scores': {'numeric': 92, 'percentile': 78},
            },
        }

        self.repo.insert_scores(trace_id=1, scores=scores)

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        # sub_scores is the 6th param (index 5)
        assert params[5] == json.dumps({'numeric': 92, 'percentile': 78})

    def test_insert_scores_handles_null_sub_scores(self):
        scores = {
            'test_score': {
                'value': 50.0,
                'sub_scores': None,
                'config': None,
            },
        }

        self.repo.insert_scores(trace_id=1, scores=scores)

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        assert params[5] is None  # sub_scores
        assert params[6] is None  # config

    def test_insert_scores_empty_dict_returns_zero(self):
        count = self.repo.insert_scores(trace_id=1, scores={})
        assert count == 0
        self.mock_client.execute.assert_not_called()

    def test_insert_trace_with_scores_end_to_end(self):
        self.mock_client.fetch_one.return_value = {'id': 99}

        trace = {
            'trace_type': 'report_generation',
            'model_id': 'openai/gpt-4o',
            'context': {'symbol': 'DBS'},
        }
        scores = {
            'faithfulness': {'value': 85.0, 'scorer_type': 'rule', 'scorer_version': '1.0'},
            'completeness': {'value': 72.0, 'scorer_type': 'rule', 'scorer_version': '1.0'},
        }

        trace_id = self.repo.insert_trace_with_scores(trace, scores)

        assert trace_id == 99
        # 1 trace insert + 2 score inserts = 3 execute calls
        assert self.mock_client.execute.call_count == 3

    def test_insert_trace_with_scores_no_scores(self):
        self.mock_client.fetch_one.return_value = {'id': 10}

        trace_id = self.repo.insert_trace_with_scores(
            {'trace_type': 'api_request'},
            scores={},
        )

        assert trace_id == 10
        # Only 1 trace insert, no score inserts
        assert self.mock_client.execute.call_count == 1

    def test_insert_scores_defaults_scorer_type_and_version(self):
        scores = {
            'test_score': {'value': 50.0},
        }

        self.repo.insert_scores(trace_id=1, scores=scores)

        execute_args = self.mock_client.execute.call_args
        params = execute_args[0][1]
        assert params[3] == 'rule'  # scorer_type default
        assert params[4] == '1.0'  # scorer_version default
