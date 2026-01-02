# -*- coding: utf-8 -*-
"""
PDF Report Generator for Ticker Analysis

Generates professional PDF reports with:
1. Title
2. Quick Summary
3. Chart with pattern/indicator annotations
4. Narrative story ("narrative + number" style)
5. News references
6. Scoring metrics
"""

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from io import BytesIO
import base64
from datetime import datetime
from typing import Optional


class PDFReportGenerator:
    """Generate professional PDF reports for ticker analysis"""

    def __init__(self, use_thai_font: bool = True):
        """
        Initialize PDF generator

        Args:
            use_thai_font: Whether to load Thai font support
        """
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self.use_thai_font = use_thai_font

        # Register Thai font
        self.thai_font = 'Helvetica'  # Default fallback
        if use_thai_font:
            try:
                import os
                font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')

                # Register Sarabun Thai font
                sarabun_regular = os.path.join(font_dir, 'Sarabun-Regular.ttf')
                sarabun_bold = os.path.join(font_dir, 'Sarabun-Bold.ttf')

                if os.path.exists(sarabun_regular):
                    pdfmetrics.registerFont(TTFont('Sarabun', sarabun_regular))
                    self.thai_font = 'Sarabun'
                    print("✅ Thai font (Sarabun) registered successfully")

                if os.path.exists(sarabun_bold):
                    pdfmetrics.registerFont(TTFont('Sarabun-Bold', sarabun_bold))
                    print("✅ Thai bold font (Sarabun-Bold) registered successfully")
                else:
                    print("⚠️  Thai font files not found, using Helvetica (Thai characters may not display)")

            except Exception as e:
                print(f"⚠️  Warning: Could not register Thai font: {e}")
                print("   Thai characters may not display correctly")

        # Define custom styles
        self._setup_custom_styles()

        # Color scheme
        self.primary_color = HexColor('#1f77b4')  # Blue
        self.success_color = HexColor('#2ca02c')  # Green
        self.warning_color = HexColor('#ff7f0e')  # Orange
        self.danger_color = HexColor('#d62728')   # Red
        self.neutral_color = HexColor('#7f7f7f')  # Gray

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Determine font names (use Thai font if available)
        font_regular = self.thai_font
        font_bold = 'Sarabun-Bold' if self.thai_font == 'Sarabun' else 'Helvetica-Bold'

        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=HexColor('#1f77b4'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=font_bold
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=HexColor('#555555'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=font_regular
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=HexColor('#1f77b4'),
            spaceAfter=10,
            spaceBefore=15,
            fontName=font_bold
        ))

        # Heading2 style for subsections
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=HexColor('#333333'),
            spaceAfter=8,
            spaceBefore=10,
            fontName=font_bold
        ))

        # Body style (Thai-compatible)
        self.styles.add(ParagraphStyle(
            name='ThaiBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            fontName=font_regular,
            spaceAfter=10
        ))

        # Metric style
        self.styles.add(ParagraphStyle(
            name='Metric',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            fontName=font_regular,
            leftIndent=10
        ))

        # Small text style
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=HexColor('#666666'),
            fontName=font_regular
        ))

    def generate_report(self,
                       ticker: str,
                       ticker_data: dict,
                       indicators: dict,
                       percentiles: dict,
                       news: list,
                       news_summary: dict,
                       chart_base64: str,
                       report: str,
                       output_path: Optional[str] = None) -> bytes:
        """
        Generate comprehensive PDF report

        Args:
            ticker: Ticker symbol
            ticker_data: Ticker fundamental data
            indicators: Technical indicators
            percentiles: Percentile analysis
            news: News articles list
            news_summary: News summary statistics
            chart_base64: Base64-encoded chart PNG
            report: Generated narrative report
            output_path: Optional path to save PDF file

        Returns:
            PDF bytes if output_path is None, otherwise saves to file
        """
        # Create PDF buffer
        buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # Build story (content elements)
        story = []

        # 1. Title Section
        story.extend(self._build_title_section(ticker, ticker_data))

        # 2. Quick Summary
        story.extend(self._build_quick_summary(ticker_data, indicators, percentiles, news_summary))

        # 3. Chart with annotations
        story.extend(self._build_chart_section(chart_base64, indicators, percentiles))

        # 4. Narrative Story
        story.extend(self._build_narrative_section(report))

        # 5. News References
        story.extend(self._build_news_section(news))

        # 6. Scoring Section
        story.extend(self._build_scoring_section(indicators, percentiles, ticker_data))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"✅ PDF report saved to: {output_path}")

        return pdf_bytes

    def _build_title_section(self, ticker: str, ticker_data: dict) -> list:
        """Build title section with company info"""
        elements = []

        # Main title
        company_name = ticker_data.get('company_name', ticker)
        title = f"{company_name} ({ticker})"
        elements.append(Paragraph(title, self.styles['CustomTitle']))

        # Subtitle with sector and date
        sector = ticker_data.get('sector', 'N/A')
        industry = ticker_data.get('industry', 'N/A')
        date = ticker_data.get('date', datetime.now().strftime('%Y-%m-%d'))

        subtitle = f"{sector} | {industry}<br/><font size=10>Analysis Date: {date}</font>"
        elements.append(Paragraph(subtitle, self.styles['Subtitle']))

        elements.append(Spacer(1, 15))

        return elements

    def _build_quick_summary(self, ticker_data: dict, indicators: dict,
                            percentiles: dict, news_summary: dict) -> list:
        """Build quick summary section"""
        elements = []

        # Section header
        elements.append(Paragraph("📊 Quick Summary", self.styles['SectionHeader']))

        # Get key metrics
        current_price = ticker_data.get('close', indicators.get('current_price', 0))
        pe_ratio = ticker_data.get('pe_ratio', 'N/A')
        market_cap = ticker_data.get('market_cap', 0)
        rsi = indicators.get('rsi', 0)
        recommendation = ticker_data.get('recommendation', 'N/A')

        # Format market cap
        if market_cap:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.2f}B"
            else:
                market_cap_str = f"${market_cap/1e6:.2f}M"
        else:
            market_cap_str = "N/A"

        # RSI status
        rsi_status = "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Normal")
        rsi_color = self.danger_color if rsi > 70 else (self.success_color if rsi < 30 else self.neutral_color)

        # News sentiment
        dominant_sentiment = news_summary.get('dominant_sentiment', 'neutral').upper()
        sentiment_color = self.success_color if dominant_sentiment == 'POSITIVE' else (
            self.danger_color if dominant_sentiment == 'NEGATIVE' else self.neutral_color
        )

        # Create summary table (wrap formatted values in Paragraph for HTML rendering)
        summary_data = [
            ['Price', Paragraph(f'<b>${current_price:.2f}</b>', self.styles['Normal'])],
            ['Market Cap', market_cap_str],
            ['P/E Ratio', f'{pe_ratio:.2f}' if isinstance(pe_ratio, (int, float)) else str(pe_ratio)],
            ['RSI', Paragraph(f'<font color="{rsi_color}">{rsi:.2f} ({rsi_status})</font>', self.styles['Normal'])],
            ['Analyst Rating', recommendation.upper() if recommendation else 'N/A'],
            ['News Sentiment', Paragraph(f'<font color="{sentiment_color}">{dominant_sentiment}</font>', self.styles['Normal'])]
        ]

        table = Table(summary_data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, HexColor('#fafafa')])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 15))

        return elements

    def _build_chart_section(self, chart_base64: str, indicators: dict, percentiles: dict) -> list:
        """Build chart section with pattern/indicator annotations"""
        elements = []

        # Section header
        elements.append(Paragraph("📈 Technical Analysis Chart", self.styles['SectionHeader']))

        # Add chart if available
        if chart_base64:
            try:
                # Decode base64 chart
                chart_bytes = base64.b64decode(chart_base64)
                chart_buffer = BytesIO(chart_bytes)

                # Add chart image (resize to fit page width)
                chart_img = Image(chart_buffer, width=6.5*inch, height=4.64*inch)
                elements.append(chart_img)

            except Exception as e:
                print(f"Error adding chart to PDF: {e}")
                elements.append(Paragraph(
                    "<i>Chart unavailable</i>",
                    self.styles['SmallText']
                ))
        else:
            elements.append(Paragraph(
                "<i>Chart not generated</i>",
                self.styles['SmallText']
            ))

        elements.append(Spacer(1, 10))

        # Add key indicator annotations
        elements.append(Paragraph("<b>Key Indicators:</b>", self.styles['Metric']))

        # Get key indicators with percentile context
        annotations = []

        if 'rsi' in indicators:
            rsi_val = indicators['rsi']
            rsi_pct = percentiles.get('rsi', {}).get('percentile', 0)
            rsi_desc = f"RSI: {rsi_val:.2f} (Percentile: {rsi_pct:.1f}%)"
            annotations.append(rsi_desc)

        if 'macd' in indicators:
            macd_val = indicators['macd']
            macd_signal = indicators.get('macd_signal', 0)
            macd_trend = "Bullish" if macd_val > macd_signal else "Bearish"
            macd_desc = f"MACD: {macd_val:.2f} vs Signal {macd_signal:.2f} ({macd_trend})"
            annotations.append(macd_desc)

        if 'sma_20' in indicators and 'sma_50' in indicators:
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            sma_trend = "Golden Cross" if sma20 > sma50 else "Death Cross"
            annotations.append(f"SMA Trend: {sma_trend}")

        for annotation in annotations:
            elements.append(Paragraph(f"• {annotation}", self.styles['Metric']))

        elements.append(Spacer(1, 15))

        return elements

    def _build_narrative_section(self, report: str) -> list:
        """Build narrative story section"""
        elements = []

        # Section header
        elements.append(Paragraph("📖 Investment Analysis", self.styles['SectionHeader']))

        # Split report into sections (identified by emoji headers)
        sections = self._parse_report_sections(report)

        for section_title, section_content in sections:
            if section_title:
                # Add section title
                elements.append(Paragraph(section_title, self.styles['CustomHeading2']))

            # Add section content
            # Clean up the content for PDF (remove markdown, preserve line breaks)
            cleaned_content = section_content.replace('\n', '<br/>')
            elements.append(Paragraph(cleaned_content, self.styles['ThaiBody']))
            elements.append(Spacer(1, 10))

        return elements

    def _parse_report_sections(self, report: str) -> list:
        """Parse report into sections based on emoji headers"""
        sections = []

        # Common section markers in Thai reports
        markers = [
            '📖 **เรื่องราวของหุ้นตัวนี้**',
            '💡 **สิ่งที่คุณต้องรู้**',
            '🎯 **ควรทำอะไรตอนนี้?**',
            '⚠️ **ระวังอะไร?**',
            '📎 **แหล่งข้อมูลข่าว:**',
            '📊 **การวิเคราะห์เปอร์เซ็นไทล์'
        ]

        # Split by markers
        current_section = ""
        current_title = ""

        lines = report.split('\n')

        for line in lines:
            # Check if line is a section marker
            is_marker = False
            for marker in markers:
                if marker in line:
                    # Save previous section
                    if current_section.strip():
                        sections.append((current_title, current_section.strip()))

                    # Start new section
                    current_title = line.strip()
                    current_section = ""
                    is_marker = True
                    break

            if not is_marker:
                current_section += line + '\n'

        # Add last section
        if current_section.strip():
            sections.append((current_title, current_section.strip()))

        # If no sections found, treat entire report as one section
        if not sections:
            sections.append(("", report))

        return sections

    def _build_news_section(self, news: list) -> list:
        """Build news references section"""
        elements = []

        if not news or len(news) == 0:
            return elements

        # Section header
        elements.append(Paragraph("📰 News References", self.styles['SectionHeader']))

        # Build news table
        news_data = [['#', 'Title', 'Sentiment', 'Impact']]

        for idx, news_item in enumerate(news, 1):
            title = news_item.get('title', 'Untitled')[:60]  # Truncate long titles
            sentiment = news_item.get('sentiment', 'neutral').upper()
            impact_score = news_item.get('impact_score', 0)

            # Color code sentiment (wrap in Paragraph for HTML rendering)
            if sentiment == 'POSITIVE':
                sentiment_colored = Paragraph(f'<font color="{self.success_color}">📈 {sentiment}</font>', self.styles['Normal'])
            elif sentiment == 'NEGATIVE':
                sentiment_colored = Paragraph(f'<font color="{self.danger_color}">📉 {sentiment}</font>', self.styles['Normal'])
            else:
                sentiment_colored = Paragraph(f'<font color="{self.neutral_color}">📊 {sentiment}</font>', self.styles['Normal'])

            news_data.append([
                f'[{idx}]',
                title,
                sentiment_colored,
                f'{impact_score:.0f}/100'
            ])

        table = Table(news_data, colWidths=[0.5*inch, 3.5*inch, 1.2*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Sarabun-Bold' if self.thai_font == 'Sarabun' else 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#fafafa')])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 15))

        return elements

    def _build_scoring_section(self, indicators: dict, percentiles: dict, ticker_data: dict) -> list:
        """Build comprehensive scoring section"""
        elements = []

        # Section header
        elements.append(Paragraph("🎯 Investment Scoring", self.styles['SectionHeader']))

        # Calculate scores
        scores = self._calculate_scores(indicators, percentiles, ticker_data)

        # Overall score (weighted average)
        overall_score = (
            scores['technical'] * 0.35 +
            scores['fundamental'] * 0.25 +
            scores['momentum'] * 0.25 +
            scores['sentiment'] * 0.15
        )

        # Overall score with color
        score_color = self._get_score_color(overall_score)
        score_grade = self._get_score_grade(overall_score)

        elements.append(Paragraph(
            f'<b>Overall Investment Score: <font color="{score_color}" size=16>{overall_score:.1f}/100</font> ({score_grade})</b>',
            self.styles['ThaiBody']
        ))
        elements.append(Spacer(1, 10))

        # Detailed scores table
        score_data = [
            ['Category', 'Score', 'Weight', 'Grade'],
            ['Technical Analysis', f"{scores['technical']:.1f}/100", '35%', self._get_score_grade(scores['technical'])],
            ['Fundamental Strength', f"{scores['fundamental']:.1f}/100", '25%', self._get_score_grade(scores['fundamental'])],
            ['Momentum Indicators', f"{scores['momentum']:.1f}/100", '25%', self._get_score_grade(scores['momentum'])],
            ['News Sentiment', f"{scores['sentiment']:.1f}/100", '15%', self._get_score_grade(scores['sentiment'])]
        ]

        table = Table(score_data, colWidths=[2.2*inch, 1.5*inch, 1*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Sarabun-Bold' if self.thai_font == 'Sarabun' else 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#fafafa')])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))

        # Score interpretation
        interpretation = self._get_score_interpretation(overall_score)
        elements.append(Paragraph(f"<i>{interpretation}</i>", self.styles['SmallText']))

        elements.append(Spacer(1, 15))

        # Add disclaimer
        elements.append(Paragraph(
            "<i><font size=8>Disclaimer: This report is for informational purposes only and does not constitute investment advice. "
            "Please conduct your own research and consult with a financial advisor before making investment decisions.</font></i>",
            self.styles['SmallText']
        ))

        return elements

    def _calculate_technical_score(self, indicators: dict) -> int:
        """Calculate technical analysis score based on RSI and MACD"""
        score = 50

        # RSI scoring: Ideal RSI 40-60 (score 100), penalize extremes
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if 40 <= rsi <= 60:
                score += 20
            elif 30 <= rsi <= 70:
                score += 10
            else:
                score -= 10

        # MACD scoring: Bullish crossover adds points
        if 'macd' in indicators and 'macd_signal' in indicators:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            score += 15 if macd > signal else -10

        return max(0, min(100, score))

    def _calculate_fundamental_score(self, ticker_data: dict) -> int:
        """Calculate fundamental analysis score based on P/E ratio and profit margin"""
        score = 50

        # P/E ratio scoring
        pe_ratio = ticker_data.get('pe_ratio')
        if pe_ratio and isinstance(pe_ratio, (int, float)):
            if 10 <= pe_ratio <= 25:
                score += 20  # Reasonable valuation
            elif pe_ratio < 10:
                score += 10  # Undervalued
            elif pe_ratio > 40:
                score -= 15  # Overvalued

        # Profit margin scoring
        profit_margin = ticker_data.get('profit_margin')
        if profit_margin and isinstance(profit_margin, (int, float)):
            if profit_margin > 0.20:
                score += 15  # High margin
            elif profit_margin > 0.10:
                score += 10  # Good margin

        return max(0, min(100, score))

    def _calculate_momentum_score(self, percentiles: dict) -> int:
        """Calculate momentum score based on RSI and volume percentiles"""
        score = 50

        # RSI percentile scoring
        if 'rsi' in percentiles:
            rsi_pct = percentiles['rsi'].get('percentile', 50)
            if 40 <= rsi_pct <= 60:
                score += 15  # Neutral momentum
            elif rsi_pct > 70:
                score += 10  # Strong momentum
            elif rsi_pct < 30:
                score -= 10  # Weak momentum

        # Volume ratio percentile scoring
        if 'volume_ratio' in percentiles:
            vol_pct = percentiles['volume_ratio'].get('percentile', 50)
            if vol_pct > 70:
                score += 10  # High volume interest

        return max(0, min(100, score))

    def _calculate_scores(self, indicators: dict, percentiles: dict, ticker_data: dict) -> dict:
        """Calculate category scores (0-100)"""
        return {
            'technical': self._calculate_technical_score(indicators),
            'fundamental': self._calculate_fundamental_score(ticker_data),
            'momentum': self._calculate_momentum_score(percentiles),
            'sentiment': 60  # Neutral default (placeholder for news_summary)
        }

    def _get_score_color(self, score: float) -> str:
        """Get color based on score"""
        if score >= 75:
            return self.success_color
        elif score >= 60:
            return HexColor('#90EE90')  # Light green
        elif score >= 40:
            return self.warning_color
        else:
            return self.danger_color

    def _get_score_grade(self, score: float) -> str:
        """Get letter grade based on score"""
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 45:
            return 'D+'
        elif score >= 40:
            return 'D'
        else:
            return 'F'

    def _get_score_interpretation(self, score: float) -> str:
        """Get interpretation text based on overall score"""
        if score >= 75:
            return "Strong investment opportunity. Favorable conditions across multiple factors."
        elif score >= 60:
            return "Good investment potential. Most indicators are positive."
        elif score >= 50:
            return "Moderate investment opportunity. Mixed signals - proceed with caution."
        elif score >= 40:
            return "Below average investment opportunity. Consider alternative options."
        else:
            return "Weak investment opportunity. High risk or unfavorable conditions."


# =============================================================================
# Standalone Function for Scheduled Workflows
# =============================================================================

def generate_pdf(report_text: str, ticker: str, chart_base64: str) -> Optional[bytes]:
    """Generate a simple PDF report from narrative text and chart.

    This is a lightweight wrapper for scheduled workflows that only have
    the final report text and chart, without intermediate structured data.

    Args:
        report_text: Complete narrative report text
        ticker: Ticker symbol
        chart_base64: Base64-encoded chart image

    Returns:
        PDF bytes or None if generation fails
    """
    try:
        # Create PDF buffer
        buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # Build story (content elements)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            textColor=HexColor('#1f77b4'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"Daily Report: {ticker}", title_style))
        story.append(Spacer(1, 12))

        # Date
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#555555'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))
        story.append(Spacer(1, 20))

        # Chart (if available)
        if chart_base64:
            try:
                # Decode base64 to bytes
                chart_data = base64.b64decode(chart_base64)
                chart_buffer = BytesIO(chart_data)

                # Add chart image (fit to page width with margin)
                img = Image(chart_buffer, width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 20))
            except Exception as e:
                # Chart failed - continue without it
                pass

        # Report text
        body_style = ParagraphStyle(
            name='Body',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        )

        # Split report into paragraphs and add each
        for paragraph in report_text.split('\n\n'):
            if paragraph.strip():
                # Clean and format paragraph (preserve line breaks as <br/>)
                cleaned = paragraph.strip().replace('\n', '<br/>')
                story.append(Paragraph(cleaned, body_style))
                story.append(Spacer(1, 10))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        return None
