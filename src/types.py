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
    error: str
    strategy: str  # Report generation strategy: 'single-stage' or 'multi-stage'
