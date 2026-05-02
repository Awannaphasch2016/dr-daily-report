"""Data-only LangGraph pipeline — fetches all data without report generation.

Builds the same graph as TickerAnalysisAgent but stops at merge_all_pipelines
(no generate_report node). Used by PreProcess Lambda to collect all raw data
before passing to a Generation strategy Lambda.
"""

import logging
import os

from langgraph.graph import StateGraph, END

from src.types import AgentState, create_initial_state

logger = logging.getLogger(__name__)


def build_data_only_graph(workflow_nodes, agent) -> 'CompiledGraph':
    """Build LangGraph with only data-fetching nodes (no generate_report).

    Reuses the same WorkflowNodes instance and routing logic as TickerAnalysisAgent,
    but the graph ends after merge_all_pipelines instead of flowing to generate_report.

    Args:
        workflow_nodes: Initialized WorkflowNodes instance
        agent: TickerAnalysisAgent instance (for routing methods)

    Returns:
        Compiled LangGraph ready for invocation
    """
    workflow = StateGraph(AgentState)

    # Add all data nodes (same as agent.py build_graph)
    workflow.add_node("fetch_data", workflow_nodes.fetch_data)

    # Fundamental fetch nodes (6 parallel)
    workflow.add_node("fetch_news", workflow_nodes.fetch_news)
    workflow.add_node("fetch_alpaca_data", workflow_nodes.fetch_alpaca_data)
    workflow.add_node("fetch_financial_markets_data", workflow_nodes.fetch_financial_markets_data)
    workflow.add_node("fetch_sec_filing", workflow_nodes.fetch_sec_filing)
    workflow.add_node("fetch_portfolio_insights", workflow_nodes.fetch_portfolio_insights)
    workflow.add_node("fetch_comparative_data", workflow_nodes.fetch_comparative_data)

    # Technical pipeline node
    workflow.add_node("analyze_technical", workflow_nodes.analyze_technical)

    # Chart pipeline node
    workflow.add_node("generate_chart", workflow_nodes.generate_chart)

    # Sink nodes
    workflow.add_node("merge_fundamental_data", workflow_nodes.merge_fundamental_data)
    workflow.add_node("merge_fund_tech_data", workflow_nodes.merge_fund_tech_data)
    workflow.add_node("merge_all_pipelines", workflow_nodes.merge_all_pipelines)

    # Analysis nodes (parallel wave 2)
    workflow.add_node("score_user_facing", workflow_nodes.score_user_facing)
    workflow.add_node("analyze_comparative_insights", workflow_nodes.analyze_comparative_insights)

    # ========== GRAPH STRUCTURE (same as agent.py minus generate_report) ==========
    workflow.set_entry_point("fetch_data")

    # PIPELINE 1: Technical
    workflow.add_edge("fetch_data", "analyze_technical")

    # PIPELINE 2: Fundamental - Fan out to 6 parallel fetches
    workflow.add_edge("fetch_data", "fetch_news")
    workflow.add_edge("fetch_data", "fetch_alpaca_data")
    workflow.add_edge("fetch_data", "fetch_financial_markets_data")
    workflow.add_edge("fetch_data", "fetch_sec_filing")
    workflow.add_edge("fetch_data", "fetch_portfolio_insights")
    workflow.add_edge("fetch_data", "fetch_comparative_data")

    # SINK 1: Merge 6 fundamental fetches
    workflow.add_edge("fetch_news", "merge_fundamental_data")
    workflow.add_edge("fetch_alpaca_data", "merge_fundamental_data")
    workflow.add_edge("fetch_financial_markets_data", "merge_fundamental_data")
    workflow.add_edge("fetch_sec_filing", "merge_fundamental_data")
    workflow.add_edge("fetch_portfolio_insights", "merge_fundamental_data")
    workflow.add_edge("fetch_comparative_data", "merge_fundamental_data")

    # SINK 2: Merge fundamental + technical
    workflow.add_edge("merge_fundamental_data", "merge_fund_tech_data")
    workflow.add_edge("analyze_technical", "merge_fund_tech_data")

    # PARALLEL WAVE 2: score + insights + chart
    workflow.add_edge("merge_fund_tech_data", "score_user_facing")
    workflow.add_edge("merge_fund_tech_data", "analyze_comparative_insights")
    workflow.add_edge("merge_fund_tech_data", "generate_chart")

    # SINK 3: Merge all pipelines → END (no generate_report)
    workflow.add_edge("score_user_facing", "merge_all_pipelines")
    workflow.add_edge("analyze_comparative_insights", "merge_all_pipelines")
    workflow.add_edge("generate_chart", "merge_all_pipelines")

    # End after merge (data collection complete)
    workflow.add_edge("merge_all_pipelines", END)

    return workflow.compile()


def run_data_pipeline(ticker: str, model: str = None, data_date: str = "") -> dict:
    """Run the data-only pipeline for a ticker.

    Creates a TickerAnalysisAgent, builds a data-only graph (no generate_report),
    and returns the final state with all data fields populated.

    Args:
        ticker: DR symbol (e.g. "DBS19")
        model: Optional LLM model (used for agent init, not for generation here)
        data_date: ISO date string or "" for today

    Returns:
        Final AgentState dict with all data fields populated

    Raises:
        RuntimeError: If data pipeline returns an error
    """
    from src.agent import TickerAnalysisAgent

    agent = TickerAnalysisAgent(model=model)
    data_graph = build_data_only_graph(agent.workflow_nodes, agent)

    initial_state = create_initial_state(ticker, data_date=data_date)
    final_state = data_graph.invoke(initial_state)

    if final_state.get("error"):
        raise RuntimeError(f"Data pipeline error for {ticker}: {final_state['error']}")

    return final_state
