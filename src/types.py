"""Shared type definitions for the ticker analysis agent"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import HumanMessage, AIMessage
import operator


class AgentState(TypedDict):
    """State dictionary for LangGraph workflow"""
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    ticker: str
    ticker_data: dict
    indicators: dict
    percentiles: dict  # Add percentiles field
    chart_patterns: list  # Add chart patterns field
    pattern_statistics: dict  # Add pattern statistics field
    strategy_performance: dict  # Add strategy performance field
    news: list
    news_summary: dict
    comparative_data: dict
    comparative_insights: dict
    chart_base64: str  # Add chart image field (base64 PNG)
    report: str
    faithfulness_score: dict  # Add faithfulness scoring field
    completeness_score: dict  # Add completeness scoring field
    reasoning_quality_score: dict  # Add reasoning quality scoring field
    compliance_score: dict  # Add compliance scoring field
    qos_score: dict  # Add QoS scoring field
    cost_score: dict  # Add cost scoring field
    timing_metrics: dict  # Add timing metrics field
    api_costs: dict  # Add API costs field
    database_metrics: dict  # Add database metrics field
    user_facing_scores: dict  # Add user-facing investment scores (0-10 scale)
    sec_filing_data: dict  # SEC EDGAR filing data (10-K, 10-Q, etc.)
    financial_markets_data: dict  # Chart patterns, candlestick patterns, support/resistance from Financial Markets MCP
    portfolio_insights: dict  # Portfolio allocation, diversification, risk metrics from Portfolio Manager MCP
    alpaca_data: dict  # Real-time quotes, options chain, market data from Alpaca MCP
    error: str
    strategy: str  # Report generation strategy: 'single-stage' or 'multi-stage'


# Raw data fields needed for report regeneration (subset of AgentState)
RAW_DATA_FIELDS = [
    'ticker',
    'ticker_data',
    'indicators',
    'percentiles',
    'chart_patterns',
    'pattern_statistics',
    'strategy_performance',
    'news',
    'news_summary',
    'comparative_data',
    'comparative_insights',
    'sec_filing_data',
    'financial_markets_data',
    'portfolio_insights',
    'alpaca_data',
]


def extract_raw_data_for_storage(state: dict) -> dict:
    """
    Extract raw data fields from AgentState for caching.

    These fields are sufficient to regenerate reports without API calls.
    Excludes derived fields (report, scores, metrics) and internal state (messages, error).

    Args:
        state: AgentState dict from workflow execution

    Returns:
        Dict containing only raw data fields

    Example:
        >>> agent_state = agent.analyze_ticker('DBS19')
        >>> raw_data = extract_raw_data_for_storage(agent_state)
        >>> # Later, regenerate report from raw_data without API calls
    """
    # Default to {} for dicts, [] for lists
    defaults = {
        'news': [],
        'chart_patterns': [],
    }

    return {
        field: state.get(field, defaults.get(field, {}))
        for field in RAW_DATA_FIELDS
    }
