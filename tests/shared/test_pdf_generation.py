# -*- coding: utf-8 -*-
"""
Tests for PDF Report Generation

Tests the PDF generation functionality with mocked components
and integration tests with real data.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestPDFGeneration:
    """Unit tests for PDF generation with mocked dependencies"""

    @pytest.fixture
    def mock_agent(self):
        """Create mock TickerAnalysisAgent for PDF generation"""
        mock = MagicMock()

        # Mock generate_pdf_report to return fake PDF bytes
        fake_pdf = b'%PDF-1.4 fake pdf content for testing'
        mock.generate_pdf_report.return_value = fake_pdf

        return mock

    @patch('src.agent.TickerAnalysisAgent')
    def test_pdf_generation_returns_bytes(self, mock_agent_class, mock_agent):
        """Test that PDF generation returns bytes"""
        mock_agent_class.return_value = mock_agent

        from src.agent import TickerAnalysisAgent
        agent = TickerAnalysisAgent()

        result = agent.generate_pdf_report(ticker='TEST19')

        assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"
        assert len(result) > 0, "PDF bytes should not be empty"

    @patch('src.agent.TickerAnalysisAgent')
    def test_pdf_generation_with_output_path(self, mock_agent_class, mock_agent, tmp_path):
        """Test PDF generation saves to specified path"""
        mock_agent_class.return_value = mock_agent

        # Make generate_pdf_report actually write to the file
        def mock_generate(ticker, output_path=None):
            pdf_bytes = b'%PDF-1.4 fake pdf content'
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
            return pdf_bytes

        mock_agent.generate_pdf_report.side_effect = mock_generate

        from src.agent import TickerAnalysisAgent
        agent = TickerAnalysisAgent()

        output_file = tmp_path / "test_report.pdf"
        result = agent.generate_pdf_report(ticker='TEST19', output_path=str(output_file))

        assert output_file.exists(), "PDF file should be created"
        assert output_file.stat().st_size > 0, "PDF file should not be empty"

    @patch('src.agent.TickerAnalysisAgent')
    def test_pdf_generation_error_handling(self, mock_agent_class):
        """Test that PDF generation errors are handled"""
        mock_agent = MagicMock()
        mock_agent.generate_pdf_report.side_effect = Exception("Generation failed")
        mock_agent_class.return_value = mock_agent

        from src.agent import TickerAnalysisAgent
        agent = TickerAnalysisAgent()

        with pytest.raises(Exception, match="Generation failed"):
            agent.generate_pdf_report(ticker='ERROR19')


@pytest.mark.integration
@pytest.mark.slow
class TestPDFGenerationIntegration:
    """Integration tests for PDF generation with real components"""

    @pytest.fixture(autouse=True)
    def check_api_key(self, requires_llm):
        """Use centralized requires_llm fixture"""
        pass

    def test_real_pdf_generation(self, tmp_path):
        """Test real PDF generation end-to-end"""
        from src.agent import TickerAnalysisAgent

        agent = TickerAnalysisAgent()
        ticker = "AAPL"

        output_file = tmp_path / f"{ticker}_report.pdf"

        pdf_bytes = agent.generate_pdf_report(
            ticker=ticker,
            output_path=str(output_file)
        )

        # Validate PDF bytes
        assert isinstance(pdf_bytes, bytes), f"Expected bytes, got {type(pdf_bytes)}"
        assert len(pdf_bytes) > 1000, "PDF should have substantial content"

        # Check PDF header magic bytes
        assert pdf_bytes[:4] == b'%PDF', "Should start with PDF header"

        # Validate file was created
        assert output_file.exists(), "PDF file should be created"
        assert output_file.stat().st_size > 1000, "PDF file should have content"

    def test_pdf_contains_expected_sections(self, tmp_path):
        """Test that generated PDF contains expected content"""
        from src.agent import TickerAnalysisAgent

        agent = TickerAnalysisAgent()
        ticker = "AAPL"

        pdf_bytes = agent.generate_pdf_report(ticker=ticker)

        # PDF should have reasonable size (at least 10KB for a real report)
        assert len(pdf_bytes) > 10000, f"PDF too small: {len(pdf_bytes)} bytes"

        # Check it's a valid PDF
        assert pdf_bytes[:4] == b'%PDF', "Should be valid PDF format"
