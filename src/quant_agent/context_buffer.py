"""In-memory context buffer for Writer/Judge iteration exchanges."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JudgeVerdict:
    """Structured feedback from DeepJudge."""
    weaknesses: List[str]
    revision_instructions: List[str]

    def format_for_writer(self) -> str:
        """Format verdict as revision guidance for the Writer."""
        lines = []
        for i, (weakness, instruction) in enumerate(
            zip(self.weaknesses, self.revision_instructions), 1
        ):
            lines.append(f"- Weakness {i}: {weakness}")
            lines.append(f"  Fix: {instruction}")
        return "\n".join(lines)


@dataclass
class IterationRecord:
    """Record of a single Writer/Judge iteration."""
    iteration: int
    report: str
    score: float
    feedback: Optional[JudgeVerdict] = None


@dataclass
class ContextBuffer:
    """Accumulates Writer/Judge exchanges within a single report generation.

    The buffer is ephemeral — lives only for one ticker's report generation.
    No persistence, no cross-run learning.
    """
    records: List[IterationRecord] = field(default_factory=list)

    def add(self, iteration: int, report: str, score: float,
            feedback: Optional[JudgeVerdict] = None) -> None:
        """Add an iteration record to the buffer."""
        self.records.append(IterationRecord(
            iteration=iteration, report=report,
            score=score, feedback=feedback
        ))

    def has_feedback(self) -> bool:
        """Check if there is any judge feedback available."""
        return len(self.records) > 0 and self.records[-1].feedback is not None

    def latest_feedback(self) -> Optional[JudgeVerdict]:
        """Get the most recent judge feedback."""
        if not self.records:
            return None
        return self.records[-1].feedback

    def format_revision_guidance(self, target_score: float) -> str:
        """Format accumulated feedback as revision guidance for the Writer.

        Args:
            target_score: The beta threshold the report needs to reach.

        Returns:
            Formatted string to append to the Writer's prompt.
        """
        if not self.has_feedback():
            return ""

        latest = self.records[-1]
        lines = [
            "REVISION GUIDANCE (from quality review of your previous attempt):",
            f"- Previous score: {latest.score:.0f}/100 (target: >={target_score:.0f})",
        ]

        if latest.feedback:
            lines.append(latest.feedback.format_for_writer())

        return "\n".join(lines)
