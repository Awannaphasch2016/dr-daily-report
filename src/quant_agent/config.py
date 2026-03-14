"""QuantAgent configuration."""

import os
from dataclasses import dataclass


@dataclass
class QuantAgentConfig:
    """Configuration for the QuantAgent inner loop.

    Attributes:
        beta: Quality score threshold (0-100). Loop exits when aggregate score >= beta.
        max_iterations: Maximum Writer/Judge iterations before returning best result.
        timeout_budget_seconds: Max time allowed for the inner loop.
        deep_judge_model: LLM model for DeepJudge feedback (cost-efficient model).
        writer_model: LLM model for Writer report generation.
    """
    beta: float = 75.0
    max_iterations: int = 3
    timeout_budget_seconds: float = 90.0
    deep_judge_model: str = "openai/gpt-4o-mini"
    writer_model: str = "openai/gpt-4o"

    @classmethod
    def from_env(cls) -> "QuantAgentConfig":
        """Load configuration from environment variables with defaults."""
        return cls(
            beta=float(os.environ.get("QUANT_AGENT_BETA", "75.0")),
            max_iterations=int(os.environ.get("QUANT_AGENT_MAX_ITERATIONS", "3")),
            timeout_budget_seconds=float(os.environ.get("QUANT_AGENT_TIMEOUT_BUDGET", "90.0")),
            deep_judge_model=os.environ.get("QUANT_AGENT_JUDGE_MODEL", "openai/gpt-4o-mini"),
            writer_model=os.environ.get("QUANT_AGENT_WRITER_MODEL", "openai/gpt-4o"),
        )
