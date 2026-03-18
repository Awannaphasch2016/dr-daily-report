# -*- coding: utf-8 -*-
"""Trace Repository — stores provenance and scores for any workload type.

Vendor-agnostic trace storage: WHO produced output, WHAT it scored,
and WHERE the full trace lives (Langfuse, LangSmith, etc.).
"""

import json
import logging
from typing import Any, Dict, Optional

from src.data.aurora.client import get_aurora_client
from src.data.aurora.table_names import TRACES, TRACE_SCORES

logger = logging.getLogger(__name__)


class TraceRepository:
    """Repository for traces and trace_scores tables."""

    def __init__(self, client=None):
        self.client = client or get_aurora_client()

    def insert_trace(self, trace: Dict[str, Any]) -> int:
        """Insert a trace row.

        Args:
            trace: Dict with keys: trace_type, model_id, prompt_version,
                   agent_type, release, trace_provider, trace_external_id,
                   input_tokens, output_tokens, cost_usd, calc_version,
                   context, status, error_message

        Returns:
            Inserted trace ID.
        """
        query = f"""
            INSERT INTO {TRACES} (
                trace_type, model_id, prompt_version, agent_type, `release`,
                trace_provider, trace_external_id,
                input_tokens, output_tokens, cost_usd, calc_version,
                context, status, error_message
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
        """

        context_json = json.dumps(trace.get('context')) if trace.get('context') else None

        params = (
            trace['trace_type'],
            trace.get('model_id'),
            trace.get('prompt_version'),
            trace.get('agent_type'),
            trace.get('release'),
            trace.get('trace_provider'),
            trace.get('trace_external_id'),
            trace.get('input_tokens'),
            trace.get('output_tokens'),
            trace.get('cost_usd'),
            trace.get('calc_version'),
            context_json,
            trace.get('status', 'completed'),
            trace.get('error_message'),
        )

        self.client.execute(query, params, commit=True)
        result = self.client.fetch_one("SELECT LAST_INSERT_ID() as id")
        trace_id = result['id']
        logger.debug(f"Inserted trace id={trace_id} type={trace['trace_type']}")
        return trace_id

    def insert_scores(self, trace_id: int, scores: Dict[str, Dict[str, Any]]) -> int:
        """Insert scores for a trace.

        Args:
            trace_id: Parent trace ID.
            scores: {score_name: {value, scorer_type, scorer_version,
                     sub_scores, config, comment}}

        Returns:
            Number of rows inserted.
        """
        if not scores:
            return 0

        query = f"""
            INSERT INTO {TRACE_SCORES} (
                trace_id, score_name, score_value,
                scorer_type, scorer_version,
                sub_scores, config, comment
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s, %s
            )
        """

        count = 0
        for name, entry in scores.items():
            sub_scores_json = json.dumps(entry.get('sub_scores')) if entry.get('sub_scores') else None
            config_json = json.dumps(entry.get('config')) if entry.get('config') else None

            params = (
                trace_id,
                name,
                entry['value'],
                entry.get('scorer_type', 'rule'),
                entry.get('scorer_version', '1.0'),
                sub_scores_json,
                config_json,
                entry.get('comment'),
            )

            self.client.execute(query, params, commit=True)
            count += 1

        logger.debug(f"Inserted {count} scores for trace_id={trace_id}")
        return count

    def insert_trace_with_scores(self, trace: Dict[str, Any], scores: Dict[str, Dict[str, Any]]) -> int:
        """Insert trace and its scores in one call.

        Args:
            trace: Trace data dict (see insert_trace).
            scores: Scores dict (see insert_scores).

        Returns:
            Inserted trace ID.
        """
        trace_id = self.insert_trace(trace)
        if scores:
            self.insert_scores(trace_id, scores)
        return trace_id


# Singleton
_instance: Optional[TraceRepository] = None


def get_trace_repository() -> TraceRepository:
    """Get singleton TraceRepository instance."""
    global _instance
    if _instance is None:
        _instance = TraceRepository()
    return _instance
