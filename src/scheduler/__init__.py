# -*- coding: utf-8 -*-
"""
Scheduler package for scheduled ticker data fetching.

This package provides Lambda handlers and services for
pre-fetching Yahoo Finance ticker data on a schedule.

NOTE: Do NOT add side-effect imports here. Every Lambda whose handler
lives under src.scheduler.* runs this file at cold-start init, so any
import added here is paid by every cold start. Callers that need
TickerFetcher must import it directly:
    from src.scheduler.ticker_fetcher import TickerFetcher
"""
