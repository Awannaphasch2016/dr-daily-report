# -*- coding: utf-8 -*-
"""Shared fixtures for shared tests."""

import pytest
from src.report.metric_registry import _METRIC_CAPABILITIES, get_metric_registry


@pytest.fixture(autouse=True)
def init_metric_registry_for_shared():
    """Initialize MetricRegistry for shared tests.

    Uncertainty is deprecated (matching production).
    """
    db_statuses = {}
    for cap in _METRIC_CAPABILITIES:
        if cap.id in ('uncertainty', 'uncertainty_percentile'):
            db_statuses[cap.id] = 'deprecated'
        else:
            db_statuses[cap.id] = 'ready'

    get_metric_registry(db_statuses)
    yield
    import src.report.metric_registry as mr
    mr._registry_instance = None
