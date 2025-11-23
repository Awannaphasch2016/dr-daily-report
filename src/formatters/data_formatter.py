# -*- coding: utf-8 -*-
"""
Data Formatter

Centralized formatting for all data types used in reports and prompts.
Extracted from agent.py to improve maintainability and reusability.

This module handles:
- Number formatting (M, B, T notation)
- Percentage formatting
- Section formatting (fundamental, technical, news, etc.)
- Percentile context formatting
- Comparative insights formatting
"""

from datetime import datetime
from typing import List, Dict, Optional


class DataFormatter:
    """Formats data for display in reports and prompts"""

    def format_number(self, value) -> str:
        """
        Format large numbers with M, B, T notation

        Args:
            value: Numeric value to format

        Returns:
            Formatted string (e.g., "1.50B", "250.00M", "N/A")

        Examples:
            >>> formatter = DataFormatter()
            >>> formatter.format_number(1500000000)
            '1.50B'
            >>> formatter.format_number(250000000)
            '250.00M'
            >>> formatter.format_number(None)
            'N/A'
        """
        if value is None:
            return "N/A"
        if value >= 1e12:
            return f"{value/1e12:.2f}T"
        elif value >= 1e9:
            return f"{value/1e9:.2f}B"
        elif value >= 1e6:
            return f"{value/1e6:.2f}M"
        else:
            return f"{value:,.0f}"

    def format_percent(self, value) -> str:
        """
        Format percentage values

        Args:
            value: Decimal value (e.g., 0.05 for 5%)

        Returns:
            Formatted percentage string (e.g., "5.00%", "N/A")

        Examples:
            >>> formatter = DataFormatter()
            >>> formatter.format_percent(0.05)
            '5.00%'
            >>> formatter.format_percent(None)
            'N/A'
        """
        if value is None:
            return "N/A"
        return f"{value*100:.2f}%"

    def format_fundamental_section(self, ticker_data: dict) -> str:
        """
        Format fundamental analysis section

        Args:
            ticker_data: Dictionary with fundamental data
                Keys: market_cap, pe_ratio, forward_pe, eps, dividend_yield,
                      sector, industry, revenue_growth, earnings_growth, profit_margin

        Returns:
            Formatted fundamental section string (Thai)
        """
        return f"""ข้อมูลพื้นฐาน (Fundamental Analysis):
- Market Cap: {self.format_number(ticker_data.get('market_cap'))}
- P/E Ratio: {ticker_data.get('pe_ratio', 'N/A')}
- Forward P/E: {ticker_data.get('forward_pe', 'N/A')}
- EPS: {ticker_data.get('eps', 'N/A')}
- Dividend Yield: {self.format_percent(ticker_data.get('dividend_yield'))}
- Sector: {ticker_data.get('sector', 'N/A')}
- Industry: {ticker_data.get('industry', 'N/A')}
- Revenue Growth: {self.format_percent(ticker_data.get('revenue_growth'))}
- Earnings Growth: {self.format_percent(ticker_data.get('earnings_growth'))}
- Profit Margin: {self.format_percent(ticker_data.get('profit_margin'))}"""

    def format_technical_section(self, indicators: dict, current_price: float, technical_analyzer=None) -> str:
        """
        Format technical analysis section

        Args:
            indicators: Dictionary with technical indicators
            current_price: Current stock price
            technical_analyzer: Optional TechnicalAnalyzer instance for trend analysis

        Returns:
            Formatted technical section string (Thai)
        """
        def format_value(value, default='N/A'):
            """Format a numeric value or return default"""
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):.2f}"
            except (ValueError, TypeError):
                return default
        
        section = f"""
การวิเคราะห์ทางเทคนิค (Technical Analysis):
- SMA 20: {format_value(indicators.get('sma_20'))}
- SMA 50: {format_value(indicators.get('sma_50'))}
- SMA 200: {format_value(indicators.get('sma_200'))}
- RSI: {format_value(indicators.get('rsi'))}
- MACD: {format_value(indicators.get('macd'))}
- Signal: {format_value(indicators.get('macd_signal'))}
- Bollinger Upper: {format_value(indicators.get('bb_upper'))}
- Bollinger Middle: {format_value(indicators.get('bb_middle'))}
- Bollinger Lower: {format_value(indicators.get('bb_lower'))}"""

        # Add trend analysis if analyzer is provided
        if technical_analyzer:
            section += f"""

แนวโน้ม: {technical_analyzer.analyze_trend(indicators, current_price)}
โมเมนตัม: {technical_analyzer.analyze_momentum(indicators)}
MACD Signal: {technical_analyzer.analyze_macd(indicators)}
Bollinger: {technical_analyzer.analyze_bollinger(indicators)}"""

        return section

    def format_news_section(self, news: List[dict], news_summary: dict) -> str:
        """
        Format news section with high-impact news

        Args:
            news: List of news items with title, sentiment, impact_score, timestamp
            news_summary: Dictionary with summary statistics

        Returns:
            Formatted news section string (Thai)
        """
        if not news or len(news) == 0:
            return ""

        news_text = "\n\nข่าวสำคัญที่มีผลกระทบสูง (High-Impact News):\n"
        news_text += f"จำนวนข่าวทั้งหมด: {news_summary.get('total_count', 0)}\n"
        news_text += f"ข่าวดี: {news_summary.get('positive_count', 0)} | "
        news_text += f"ข่าวลบ: {news_summary.get('negative_count', 0)} | "
        news_text += f"เป็นกลาง: {news_summary.get('neutral_count', 0)}\n"
        news_text += f"แนวโน้มโดยรวม: {news_summary.get('dominant_sentiment', 'neutral').upper()}\n"
        news_text += f"มีข่าวใหม่ล่าสุด (< 24 ชม): {'YES' if news_summary.get('has_recent_news') else 'NO'}\n\n"

        for idx, news_item in enumerate(news, 1):
            title = news_item.get('title', '')
            sentiment = news_item.get('sentiment', 'neutral')
            impact_score = news_item.get('impact_score', 0)
            timestamp = news_item.get('timestamp')

            # Calculate time ago
            if timestamp:
                # Handle both datetime objects and ISO format strings
                if isinstance(timestamp, str):
                    from dateutil import parser
                    timestamp = parser.isoparse(timestamp)

                now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
                hours_ago = (now - timestamp).total_seconds() / 3600
                time_str = f"{int(hours_ago)}h ago" if hours_ago < 24 else f"{int(hours_ago / 24)}d ago"
            else:
                time_str = "Unknown"

            sentiment_indicator = {
                'positive': '📈 POSITIVE',
                'negative': '📉 NEGATIVE',
                'neutral': '📊 NEUTRAL'
            }.get(sentiment, '📊 NEUTRAL')

            news_text += f"[{idx}] {title}\n"
            news_text += f"    Sentiment: {sentiment_indicator} | Impact: {impact_score:.0f}/100 | {time_str}\n\n"

        return news_text

    def format_percentile_context(self, percentiles: dict) -> str:
        """
        Format percentile context for prompt

        Args:
            percentiles: Dictionary with percentile data for various metrics

        Returns:
            Formatted percentile analysis string (Thai)
        """
        if not percentiles:
            return ""

        context = "\n\nการวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis - เปรียบเทียบกับประวัติศาสตร์):\n"

        if 'rsi' in percentiles:
            rsi_stats = percentiles['rsi']
            context += f"- RSI: {rsi_stats['current_value']:.2f} (เปอร์เซ็นไทล์: {rsi_stats['percentile']:.1f}%"
            if 'mean' in rsi_stats:
                context += f" - สูงกว่าค่าเฉลี่ย {rsi_stats['mean']:.2f}"
            context += ")\n"
            if 'frequency_above_70' in rsi_stats and 'frequency_below_30' in rsi_stats:
                context += f"  ความถี่ที่ RSI > 70: {rsi_stats['frequency_above_70']:.1f}% | ความถี่ที่ RSI < 30: {rsi_stats['frequency_below_30']:.1f}%\n"

        if 'macd' in percentiles:
            macd_stats = percentiles['macd']
            context += f"- MACD: {macd_stats['current_value']:.4f} (เปอร์เซ็นไทล์: {macd_stats['percentile']:.1f}%)\n"
            if 'frequency_positive' in macd_stats:
                context += f"  ความถี่ที่ MACD > 0: {macd_stats['frequency_positive']:.1f}%\n"

        if 'uncertainty_score' in percentiles:
            unc_stats = percentiles['uncertainty_score']
            context += f"- Uncertainty Score: {unc_stats['current_value']:.2f}/100 (เปอร์เซ็นไทล์: {unc_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ต่ำ (<25): {unc_stats['frequency_low']:.1f}% | ความถี่ที่สูง (>75): {unc_stats['frequency_high']:.1f}%\n"

        if 'atr_percent' in percentiles:
            atr_stats = percentiles['atr_percent']
            context += f"- ATR %: {atr_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {atr_stats['percentile']:.1f}%)\n"
            if 'frequency_low_volatility' in atr_stats and 'frequency_high_volatility' in atr_stats:
                context += f"  ความถี่ที่ความผันผวนต่ำ (<1%): {atr_stats['frequency_low_volatility']:.1f}% | ความถี่ที่ความผันผวนสูง (>4%): {atr_stats['frequency_high_volatility']:.1f}%\n"

        if 'price_vwap_percent' in percentiles:
            vwap_stats = percentiles['price_vwap_percent']
            context += f"- Price vs VWAP %: {vwap_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {vwap_stats['percentile']:.1f}%)\n"
            if 'frequency_above_3pct' in vwap_stats and 'frequency_below_neg3pct' in vwap_stats:
                context += f"  ความถี่ที่ราคาเหนือ VWAP >3%: {vwap_stats['frequency_above_3pct']:.1f}% | ความถี่ที่ราคาต่ำกว่า VWAP <-3%: {vwap_stats['frequency_below_neg3pct']:.1f}%\n"

        if 'volume_ratio' in percentiles:
            vol_stats = percentiles['volume_ratio']
            context += f"- Volume Ratio: {vol_stats['current_value']:.2f}x (เปอร์เซ็นไทล์: {vol_stats['percentile']:.1f}%)\n"
            if 'frequency_high_volume' in vol_stats and 'frequency_low_volume' in vol_stats:
                context += f"  ความถี่ที่ปริมาณสูง (>2x): {vol_stats['frequency_high_volume']:.1f}% | ความถี่ที่ปริมาณต่ำ (<0.7x): {vol_stats['frequency_low_volume']:.1f}%\n"

        context += "\n**IMPORTANT**: Use these percentile values naturally in your narrative to add historical context. Don't just list them - weave them into the story!"
        return context

    def format_comparative_insights(self, ticker: str, insights: dict) -> str:
        """
        Format comparative insights for narrative context

        Args:
            ticker: Ticker symbol
            insights: Dictionary with comparative analysis results

        Returns:
            Formatted comparative insights string (Thai)
        """
        if not insights:
            return ""

        lines = []

        # Similar tickers
        if 'similar_tickers' in insights and insights['similar_tickers']:
            similar = insights['similar_tickers']
            ticker_list = ", ".join([f"{t[0]} (correlation {t[1]:.2f})" for t in similar[:3]])
            lines.append(f"- หุ้นที่เคลื่อนไหวคล้ายกัน: {ticker_list}")

            if 'avg_correlation' in insights and insights['avg_correlation'] is not None:
                avg_corr = insights['avg_correlation']
                lines.append(f"- ความสัมพันธ์เฉลี่ยกับหุ้นอื่น: {avg_corr:.2f}")

        # Cluster membership
        if 'cluster_id' in insights and 'cluster_members' in insights:
            members = insights['cluster_members']
            if members:
                members_str = ", ".join(members[:3])
                lines.append(f"- อยู่ในกลุ่มเดียวกันกับ: {members_str}")

        # Feature comparisons
        if 'volatility_vs_peers' in insights:
            vol_data = insights['volatility_vs_peers']
            if vol_data.get('current') is not None and vol_data.get('peer_avg') is not None:
                current_vol = vol_data['current']
                peer_avg = vol_data['peer_avg']
                diff_pct = ((current_vol - peer_avg) / peer_avg * 100) if peer_avg > 0 else 0
                if abs(diff_pct) > 5:  # Only mention if significant difference
                    direction = "สูงกว่า" if diff_pct > 0 else "ต่ำกว่า"
                    lines.append(f"- ความผันผวน {direction}ค่าเฉลี่ยของหุ้นอื่น {abs(diff_pct):.1f}% (ปัจจุบัน: {current_vol:.2f}% vs ค่าเฉลี่ย: {peer_avg:.2f}%)")

        if 'return_vs_peers' in insights:
            return_data = insights['return_vs_peers']
            if return_data.get('current') is not None and return_data.get('peer_avg') is not None:
                current_ret = return_data['current']
                peer_avg = return_data['peer_avg']
                diff_pct = ((current_ret - peer_avg) / abs(peer_avg) * 100) if abs(peer_avg) > 0.01 else 0
                if abs(diff_pct) > 10:  # Only mention if significant difference
                    direction = "สูงกว่า" if diff_pct > 0 else "ต่ำกว่า"
                    lines.append(f"- ผลตอบแทน {direction}ค่าเฉลี่ยของหุ้นอื่น {abs(diff_pct):.1f}% (ปัจจุบัน: {current_ret:.2f}% vs ค่าเฉลี่ย: {peer_avg:.2f}%)")

        if 'volatility_rank' in insights:
            rank_data = insights['volatility_rank']
            position = rank_data['position']
            total = rank_data['total']
            percentile = (position / total * 100) if total > 0 else 0
            lines.append(f"- อันดับความผันผวน: {position}/{total} (เปอร์เซ็นไทล์ {percentile:.0f}%)")

        return "\n".join(lines) if lines else ""


# Example usage and testing
if __name__ == "__main__":
    formatter = DataFormatter()

    # Test number formatting
    print("Number Formatting:")
    print(f"  {formatter.format_number(1500000000)} (expected: 1.50B)")
    print(f"  {formatter.format_number(250000000)} (expected: 250.00M)")
    print(f"  {formatter.format_number(None)} (expected: N/A)")

    # Test percent formatting
    print("\nPercent Formatting:")
    print(f"  {formatter.format_percent(0.05)} (expected: 5.00%)")
    print(f"  {formatter.format_percent(None)} (expected: N/A)")

    # Test fundamental section
    print("\nFundamental Section:")
    ticker_data = {
        'market_cap': 1500000000,
        'pe_ratio': 25.5,
        'eps': 3.50,
        'sector': 'Technology'
    }
    print(formatter.format_fundamental_section(ticker_data))
