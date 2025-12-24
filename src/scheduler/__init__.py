# -*- coding: utf-8 -*-
"""
Scheduler package for scheduled ticker data fetching.

This package provides Lambda handlers and services for
pre-fetching Yahoo Finance ticker data on a schedule.
"""

from src.scheduler.ticker_fetcher import TickerFetcher

__all__ = ['TickerFetcher']
# Deploy trigger Wed Dec 24 10:55:23 +07 2025
