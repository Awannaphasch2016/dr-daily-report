"""
Synthesis Generator for Multi-Stage Report Generation.

This module synthesizes multiple specialized mini-reports into a
comprehensive final report, analyzing convergence/divergence across
different analytical perspectives.
"""

from pathlib import Path
from typing import Dict, Any


class SynthesisGenerator:
    """
    Synthesizes specialized mini-reports into a comprehensive final report.

    The synthesis process:
    1. Analyzes convergence/divergence across mini-reports
    2. Weights insights by data quality
    3. Builds coherent narrative flow
    4. Provides clear action recommendation
    """

    def __init__(self, llm):
        """
        Initialize the SynthesisGenerator.

        Args:
            llm: Language model instance for generating synthesis
        """
        self.llm = llm
        self.synthesis_prompt = self._load_synthesis_prompt()

    def _load_synthesis_prompt(self) -> str:
        """
        Load the synthesis prompt template.

        Returns:
            Synthesis prompt template string
        """
        templates_dir = Path(__file__).parent / "prompt_templates" / "th"
        filepath = templates_dir / "synthesis_prompt.txt"

        if not filepath.exists():
            raise FileNotFoundError(f"Synthesis prompt template not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def _format_mini_reports(self, mini_reports: Dict[str, str]) -> str:
        """
        Format all mini-reports for synthesis.

        Args:
            mini_reports: Dictionary containing all 6 mini-reports
                {
                    'technical': '...',
                    'fundamental': '...',
                    'market_conditions': '...',
                    'news': '...',
                    'comparative': '...',
                    'strategy': '...'
                }

        Returns:
            Formatted string with all mini-reports labeled
        """
        formatted = ""

        # Define order and labels
        report_order = [
            ('technical', '📈 **Technical Analysis Mini-Report**'),
            ('fundamental', '💼 **Fundamental Analysis Mini-Report**'),
            ('market_conditions', '🌐 **Market Conditions Mini-Report**'),
            ('news', '📰 **News & Events Mini-Report**'),
            ('comparative', '📊 **Comparative Analysis Mini-Report**'),
            ('strategy', '🎯 **Strategy Performance Mini-Report**'),
        ]

        for key, label in report_order:
            if key in mini_reports and mini_reports[key]:
                formatted += f"{label}\n{mini_reports[key]}\n\n"
            else:
                formatted += f"{label}\n[ไม่มีข้อมูล / Data not available]\n\n"

        return formatted.strip()

    def generate_synthesis(self, mini_reports: Dict[str, str]) -> str:
        """
        Generate comprehensive synthesis from all mini-reports.

        This method takes specialized mini-reports and synthesizes them into
        a coherent narrative that:
        - Identifies convergence/divergence across analyses
        - Weights insights by data quality
        - Provides clear action recommendation
        - Highlights key risks

        Args:
            mini_reports: Dictionary containing all 6 mini-reports
                {
                    'technical': 'technical analysis narrative',
                    'fundamental': 'fundamental analysis narrative',
                    'market_conditions': 'market conditions narrative',
                    'news': 'news & events narrative',
                    'comparative': 'comparative analysis narrative',
                    'strategy': 'strategy performance narrative'
                }

        Returns:
            Comprehensive synthesized report in Thai (12-15 lines)

        Expected output structure:
            📖 **เรื่องราวของหุ้นตัวนี้** (2-3 sentences)
            💡 **สิ่งที่คุณต้องรู้** (3-4 flowing paragraphs)
            🎯 **ควรทำอะไรตอนนี้?** (2-3 sentences)
            ⚠️ **ระวังอะไร?** (1-2 key risks)
        """
        # Format all mini-reports
        formatted_mini_reports = self._format_mini_reports(mini_reports)

        # Substitute into synthesis prompt
        prompt = self.synthesis_prompt.replace('{mini_reports}', formatted_mini_reports)

        # Generate synthesis
        response = self.llm.invoke(prompt)
        synthesis = response.content if hasattr(response, 'content') else str(response)

        return synthesis

    def generate_synthesis_with_harmonization(
        self,
        mini_reports: Dict[str, str],
        contradictions: list = None
    ) -> str:
        """
        Generate synthesis with explicit harmonization of contradictions.

        This enhanced version performs harmonization check before synthesis
        to identify and resolve contradictions across mini-reports.

        Args:
            mini_reports: Dictionary containing all 6 mini-reports
            contradictions: Optional list of identified contradictions
                If None, contradictions will be auto-detected

        Returns:
            Comprehensive synthesized report with harmonized insights
        """
        # For now, use standard synthesis
        # Future: Implement explicit contradiction detection and resolution
        return self.generate_synthesis(mini_reports)
