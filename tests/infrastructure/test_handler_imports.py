"""Test that all Lambda handlers can be imported and have correct structure.

This test layer catches import errors BEFORE deployment:
- Missing handler files
- Incorrect import paths
- Missing handler() function
- Import-time errors (circular imports, syntax in imported modules)

Tier 0 test - runs in PR checks (~10 seconds, zero AWS calls)
"""

import importlib
import pytest
from pathlib import Path


class TestHandlerImports:
    """Validate handler module structure before deployment."""

    @pytest.mark.parametrize("handler_module", [
        "src.report_worker_handler",
        "src.telegram_lambda_handler",
        "src.lambda_handler",
        "src.scheduler.ticker_fetcher_handler",
        "src.scheduler.query_tool_handler",
        "src.scheduler.precompute_controller_handler",
    ])
    def test_handler_module_exists(self, handler_module):
        """GIVEN handler module path
        WHEN attempting to import
        THEN module should exist and be importable
        """
        try:
            mod = importlib.import_module(handler_module)
            assert mod is not None, f"{handler_module} imported as None"
        except ImportError as e:
            pytest.fail(f"Failed to import {handler_module}: {e}")

    @pytest.mark.parametrize("handler_module,function_name", [
        ("src.report_worker_handler", "handler"),
        ("src.telegram_lambda_handler", "handler"),
        ("src.lambda_handler", "lambda_handler"),
        ("src.scheduler.ticker_fetcher_handler", "lambda_handler"),
        ("src.scheduler.query_tool_handler", "lambda_handler"),
        ("src.scheduler.precompute_controller_handler", "lambda_handler"),
    ])
    def test_handler_function_exists(self, handler_module, function_name):
        """GIVEN handler module
        WHEN checking for handler/lambda_handler function
        THEN function should exist and be callable
        """
        mod = importlib.import_module(handler_module)
        assert hasattr(mod, function_name), f"{handler_module} missing {function_name}() function"
        assert callable(getattr(mod, function_name)), f"{handler_module}.{function_name} is not callable"

    def test_report_worker_handler_structure(self):
        """GIVEN report_worker_handler
        WHEN checking critical imports
        THEN all dependencies should be available

        This test would have caught the v116 import error.
        """
        from src.report_worker_handler import (
            handler,
            process_record,
            _validate_required_config,
        )

        # Verify functions are callable
        assert callable(handler), "handler() is not callable"
        assert callable(process_record), "process_record() is not callable"
        assert callable(_validate_required_config), "_validate_required_config() is not callable"

    def test_handler_file_locations(self):
        """GIVEN expected handler file paths
        WHEN checking filesystem
        THEN all handler files should exist
        """
        handlers = [
            "src/report_worker_handler.py",
            "src/telegram_lambda_handler.py",
            "src/lambda_handler.py",
            "src/scheduler/ticker_fetcher_handler.py",
            "src/scheduler/query_tool_handler.py",
            "src/scheduler/precompute_controller_handler.py",
        ]

        repo_root = Path(__file__).parent.parent.parent
        for handler_path in handlers:
            full_path = repo_root / handler_path
            assert full_path.exists(), f"Handler file not found: {handler_path}"
            assert full_path.stat().st_size > 0, f"Handler file is empty: {handler_path}"
