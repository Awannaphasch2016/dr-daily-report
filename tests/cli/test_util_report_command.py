"""
Integration tests for dr util report command.

Tests the CLI command outputs clean report text, not AgentState dict.
Follows CLAUDE.md TDD principles: write failing tests first.
"""

import subprocess
import pytest


class TestUtilReportCommand:
    """Test dr util report command outputs report text only"""

    @pytest.mark.integration
    def test_util_report_outputs_report_text_not_dict(self):
        """
        Verify 'dr util report TICKER' outputs clean report text, not AgentState dict.

        CLAUDE.md Principle: Test Outcomes, Not Execution
        Contract: CLI should output user-facing report text
        """
        # Execute command
        result = subprocess.run(
            ['dr', 'util', 'report', 'DBS19'],
            capture_output=True,
            text=True,
            timeout=120
        )

        # OUTCOME TEST: Verify output is report text, not dict
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        output = result.stdout

        # DEFENSIVE: Report text should NOT contain Python dict markers
        assert not output.startswith('{'), \
            "Output should be report text, not dict starting with '{'"
        assert "'messages':" not in output, \
            "Output should not contain AgentState fields like 'messages'"
        assert "'ticker_data':" not in output, \
            "Output should not contain AgentState fields like 'ticker_data'"
        assert "'indicators':" not in output, \
            "Output should not contain AgentState fields like 'indicators'"

        # OUTCOME: Report text should contain expected content
        assert 'DBS' in output or 'รายงาน' in output, \
            "Output should contain ticker or Thai report header"

    @pytest.mark.integration
    def test_util_report_has_same_structure_as_direct_python(self):
        """
        Verify 'dr util report' output has same structure as direct Python extraction.

        CLAUDE.md Principle: Round-Trip Tests
        Contract: CLI is wrapper for agent.analyze_ticker()['report']

        Note: Cannot test exact equality due to LLM non-determinism,
        but can verify both produce valid Thai report text with same structure.
        """
        # Get CLI output
        cli_result = subprocess.run(
            ['dr', 'util', 'report', 'DBS19'],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Get direct Python output
        python_result = subprocess.run(
            ['python3', '-c',
             "from src.agent import TickerAnalysisAgent; "
             "print(TickerAnalysisAgent().analyze_ticker('DBS19')['report'])"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Both should succeed
        assert cli_result.returncode == 0
        assert python_result.returncode == 0

        # Both should be non-empty report text
        assert len(cli_result.stdout) > 1000, "CLI should output full report"
        assert len(python_result.stdout) > 1000, "Python should output full report"

        # Both should have Thai report structure (same sections)
        expected_sections = ['📖 **เรื่องราวของหุ้นตัวนี้**', '💡 **สิ่งที่คุณต้องรู้**',
                           '🎯 **ควรทำอะไรตอนนี้?**', '⚠️ **ระวังอะไร?**']
        for section in expected_sections:
            assert section in cli_result.stdout, f"CLI missing section: {section}"
            assert section in python_result.stdout, f"Python missing section: {section}"

        # Both should contain data source transparency footer
        assert '📊 **ข้อมูลที่ใช้ในการวิเคราะห์' in cli_result.stdout
        assert '📊 **ข้อมูลที่ใช้ในการวิเคราะห์' in python_result.stdout
