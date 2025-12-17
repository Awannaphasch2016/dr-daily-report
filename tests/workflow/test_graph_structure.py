"""
Test graph structure compilation and validation.

Verifies that the parallel workflow graph compiles without errors.
"""

import pytest
from unittest.mock import MagicMock
from src.agent import TickerAnalysisAgent


class TestGraphStructure:
    """Test graph structure compilation"""

    def test_graph_compiles_without_errors(self):
        """Verify the parallel workflow graph compiles successfully"""
        # Mock environment variables
        import os
        os.environ['OPENROUTER_API_KEY'] = 'test-key'

        try:
            # Initialize agent (this compiles the graph)
            agent = TickerAnalysisAgent()

            # ASSERT: Graph compiled successfully
            assert agent.graph is not None, "Graph should compile"

            # Verify graph has expected nodes
            # Note: LangGraph doesn't expose node list directly, but we can verify it compiled
            assert hasattr(agent, 'workflow_nodes'), "Should have workflow nodes"

        except Exception as e:
            pytest.fail(f"Graph compilation failed: {e}")

    def test_all_sink_nodes_registered(self):
        """Verify all 3 sink nodes are registered in workflow"""
        import os
        os.environ['OPENROUTER_API_KEY'] = 'test-key'

        agent = TickerAnalysisAgent()

        # Verify sink methods exist on workflow_nodes
        assert hasattr(agent.workflow_nodes, 'merge_fundamental_data'), \
            "Should have merge_fundamental_data sink"
        assert hasattr(agent.workflow_nodes, 'merge_fund_tech_data'), \
            "Should have merge_fund_tech_data sink"
        assert hasattr(agent.workflow_nodes, 'merge_all_pipelines'), \
            "Should have merge_all_pipelines sink"

    def test_refactored_nodes_return_dict(self):
        """Verify refactored nodes have dict return type annotation"""
        import os
        os.environ['OPENROUTER_API_KEY'] = 'test-key'

        agent = TickerAnalysisAgent()
        workflow_nodes = agent.workflow_nodes

        # Check return type annotations
        import inspect

        refactored_methods = [
            'fetch_news',
            'fetch_alpaca_data',
            'fetch_financial_markets_data',
            'fetch_sec_filing',
            'fetch_portfolio_insights',
            'fetch_comparative_data'
        ]

        for method_name in refactored_methods:
            method = getattr(workflow_nodes, method_name)
            sig = inspect.signature(method)

            # ASSERT: Return annotation is dict
            assert sig.return_annotation == dict, \
                f"{method_name} should return dict, not {sig.return_annotation}"

    def test_sink_nodes_return_dict(self):
        """Verify sink nodes have dict return type annotation"""
        import os
        os.environ['OPENROUTER_API_KEY'] = 'test-key'

        agent = TickerAnalysisAgent()
        workflow_nodes = agent.workflow_nodes

        import inspect

        sink_methods = [
            'merge_fundamental_data',
            'merge_fund_tech_data',
            'merge_all_pipelines'
        ]

        for method_name in sink_methods:
            method = getattr(workflow_nodes, method_name)
            sig = inspect.signature(method)

            # ASSERT: Return annotation is dict
            assert sig.return_annotation == dict, \
                f"{method_name} should return dict, not {sig.return_annotation}"
