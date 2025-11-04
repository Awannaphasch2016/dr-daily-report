import pytest
from playwright.sync_api import Page, expect
import time


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the Flask application"""
    return "http://127.0.0.1:5000"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
