# -*- coding: utf-8 -*-
"""
Transparency Footer Generator

Generates transparency footnote showing what data sources were used/not used in report generation.
Provides explainability and builds user trust by clearly stating data availability.
"""

import logging
from typing import Dict, List, Any

from src.report.metric_registry import get_metric_registry

logger = logging.getLogger(__name__)


class TransparencyFooter:
    """Generates transparency footnote for report explainability"""

    def generate_data_usage_footnote(self, state: Dict[str, Any], strategy: str = 'single-stage') -> str:
        """
        Analyze state to determine what data was used/not used in report generation.

        Args:
            state: AgentState dict containing all data categories
            strategy: Generation strategy ('single-stage' or 'multi-stage')

        Returns:
            Formatted footnote string in Thai with:
            - ✅ Used categories with status
            - ⚠️ Unused categories with reasons
            - 🔄 Generation strategy indicator
        """
        used = []
        not_used = []

        # Check Technical Analysis
        indicators = state.get('indicators', {})
        if indicators and len(indicators) > 5:  # Basic check for meaningful indicators
            used.append("Technical Analysis (RSI, MACD, SMA, indicators): ใช้ข้อมูล 1 ปี - พร้อมใช้งาน")
        else:
            not_used.append("Technical Analysis: ไม่สามารถคำนวณ indicators ได้")

        # Check Fundamental Analysis
        ticker_data = state.get('ticker_data', {})
        has_fundamental = any([
            ticker_data.get('pe_ratio'),
            ticker_data.get('eps'),
            ticker_data.get('market_cap')
        ])
        if has_fundamental:
            metrics = []
            if ticker_data.get('pe_ratio'):
                metrics.append(f"P/E {ticker_data['pe_ratio']:.2f}")
            if ticker_data.get('eps'):
                metrics.append(f"EPS {ticker_data['eps']:.2f}")
            if ticker_data.get('market_cap'):
                # Format market cap in billions
                mc_billions = ticker_data['market_cap'] / 1e9
                metrics.append(f"Market Cap ${mc_billions:.1f}B")

            metrics_str = ", ".join(metrics[:3])  # Show max 3 metrics
            used.append(f"Fundamental Analysis ({metrics_str}): ดึงจาก Yahoo Finance - พร้อมใช้งาน")
        else:
            not_used.append("Fundamental Analysis: Yahoo Finance ไม่มีข้อมูล fundamental (P/E, EPS)")

        # Check Market Conditions
        uncertainty_ready = False
        try:
            uncertainty_ready = get_metric_registry().is_ready('uncertainty')
        except ValueError:
            pass

        uncertainty = indicators.get('uncertainty_score')
        atr_pct = (indicators.get('atr', 0) / indicators.get('current_price', 1) * 100) if indicators.get('current_price') else 0

        if uncertainty_ready and uncertainty is not None:
            used.append(f"Market Conditions (uncertainty {uncertainty:.1f}, volatility {atr_pct:.2f}%): คำนวณจากราคาและ volume - พร้อมใช้งาน")
        elif atr_pct > 0:
            used.append(f"Market Conditions (volatility {atr_pct:.2f}%): คำนวณจากราคาและ volume - พร้อมใช้งาน")
        else:
            not_used.append("Market Conditions: ไม่สามารถคำนวณ market conditions ได้")

        # Check Statistical Context (Percentiles)
        percentiles = state.get('percentiles', {})
        if percentiles and len(percentiles) > 0:
            percentile_count = len(percentiles)
            used.append(f"Statistical Context ({percentile_count} percentiles): เปรียบเทียบกับข้อมูลย้อนหลัง 1 ปี - พร้อมใช้งาน")
        else:
            not_used.append("Statistical Context: ไม่มีข้อมูลย้อนหลังเพียงพอสำหรับคำนวณ percentiles")

        # Check News & Events
        news = state.get('news', [])
        if news and len(news) > 0:
            high_impact = [n for n in news if n.get('impact_score', 0) >= 40]
            if high_impact:
                used.append(f"News & Events ({len(high_impact)} ข่าวผลกระทบสูง): ข่าวล่าสุด 7 วัน - พร้อมใช้งาน")
            else:
                used.append(f"News & Events ({len(news)} ข่าว): ข่าวล่าสุด - พร้อมใช้งาน")
        else:
            not_used.append("News & Events: ไม่พบข่าวล่าสุดจาก Yahoo Finance")

        # Check Comparative/Peer Analysis
        comp = state.get('comparative_insights', {})
        if comp and len(comp) > 0:
            similar_tickers = comp.get('similar_tickers', [])
            if similar_tickers:
                used.append(f"Comparative Analysis ({len(similar_tickers)} peer tickers): วิเคราะห์เทียบกับหุ้นในกลุ่มเดียวกัน - พร้อมใช้งาน")
            else:
                used.append("Comparative Analysis: วิเคราะห์ relative performance - พร้อมใช้งาน")
        else:
            not_used.append("Comparative Analysis: ไม่มีข้อมูล peer tickers ในกลุ่มเดียวกัน (sector ไม่ตรงหรือข้อมูลไม่เพียงพอ)")

        # Check Strategy/Backtesting Performance
        strat = state.get('strategy_performance')
        if strat and (strat.get('buy_only') or strat.get('sell_only')):
            used.append("Strategy Performance (backtesting results): ผลการทดสอบกลยุทธ์ย้อนหลัง - พร้อมใช้งาน")
        else:
            not_used.append("Strategy Performance: ระบบ backtesting ยังไม่เปิดใช้งาน (currently stubbed)")

        # Build footnote
        footnote = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        footnote += "📊 **ข้อมูลที่ใช้ในการวิเคราะห์ (Data Sources Used)**\n"
        footnote += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if used:
            footnote += "✅ **Used in Analysis:**\n"
            for item in used:
                footnote += f"- {item}\n"

        if not_used:
            footnote += "\n⚠️ **Not Used (Data Unavailable):**\n"
            for item in not_used:
                footnote += f"- {item}\n"

        # Add generation strategy
        footnote += f"\n🔄 **Generation Strategy:** {strategy.replace('-', ' ').title()}"
        if strategy == 'multi-stage':
            footnote += " (6 mini-reports → synthesis)"
        else:
            footnote += " (direct generation)"

        footnote += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        logger.info(f"Generated transparency footnote: {len(used)} used, {len(not_used)} not used")

        return footnote
