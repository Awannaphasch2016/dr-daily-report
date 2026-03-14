"""QuantAgent multi-agent report generation module.

Implements the inner loop from QuantAgent (arXiv:2402.03755):
Writer generates report → Judge scores + reviews → Writer revises → repeat
until quality threshold met or max iterations reached.
"""

from src.quant_agent.inner_loop import QuantAgentReportGenerator, InnerLoopResult
from src.quant_agent.config import QuantAgentConfig

__all__ = ["QuantAgentReportGenerator", "InnerLoopResult", "QuantAgentConfig"]
