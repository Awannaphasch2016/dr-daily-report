# -*- coding: utf-8 -*-
"""Shared fixtures for report tests."""

import pytest
from src.report.metric_registry import _METRIC_CAPABILITIES, get_metric_registry


@pytest.fixture(autouse=True)
def init_metric_registry():
    """Initialize MetricRegistry with production-like statuses for all report tests.

    Uses autouse=True so all report tests automatically have the registry available.
    Uncertainty is deprecated (matching the migration seed).
    """
    db_statuses = {}
    for cap in _METRIC_CAPABILITIES:
        if cap.id in ('uncertainty', 'uncertainty_percentile'):
            db_statuses[cap.id] = 'deprecated'
        else:
            db_statuses[cap.id] = 'ready'

    get_metric_registry(db_statuses)
    yield
    # Reset singleton after test
    import src.report.metric_registry as mr
    mr._registry_instance = None
