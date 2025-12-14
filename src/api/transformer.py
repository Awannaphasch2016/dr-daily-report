"""Transform AgentState to API response format"""

import re
from datetime import datetime
from typing import Literal, Optional
import logging

from src.types import AgentState
from src.formatters.pdf_storage import PDFStorage
from .models import (
    ReportResponse,
    SummarySections,
    TechnicalMetric,
    FundamentalMetric,
    Fundamentals,
    NewsItem,
    OverallSentiment,
    UncertaintyScore,
    Risk,
    Peer,
    GenerationMetadata,
    PriceDataPoint,
    ProjectionBand,
    ScoringMetric
)
from .peer_selector import get_peer_selector_service

logger = logging.getLogger(__name__)

# PDF storage singleton
_pdf_storage: Optional[PDFStorage] = None


def get_pdf_storage() -> PDFStorage:
    """Get or create PDFStorage singleton"""
    global _pdf_storage
    if _pdf_storage is None:
        _pdf_storage = PDFStorage()
    return _pdf_storage


class ResponseTransformer:
    """Transform AgentState to spec-compliant API responses"""

    def __init__(self):
        self.pdf_storage = get_pdf_storage()

    def _get_pdf_url(self, state: AgentState, ticker: str) -> Optional[str]:
        """Generate S3 presigned URL for PDF report if available

        Checks for PDF object key in state or constructs expected key.

        Args:
            state: AgentState that may contain pdf_object_key
            ticker: Ticker symbol for constructing key

        Returns:
            Presigned URL string or None if PDF not available
        """
        if not self.pdf_storage.is_available():
            logger.debug("PDF storage not available - skipping presigned URL")
            return None

        try:
            # Check if PDF key is in state (from workflow that generated PDF)
            pdf_key = state.get("pdf_object_key")

            if pdf_key:
                # Generate presigned URL for existing PDF
                url = self.pdf_storage.get_presigned_url(pdf_key)
                logger.info(f"Generated presigned URL for existing PDF: {pdf_key}")
                return url

            # No PDF in state - could optionally generate one here
            # For now, return None (PDF generation happens in workflow)
            logger.debug(f"No PDF object key in state for {ticker}")
            return None

        except Exception as e:
            logger.warning(f"Failed to generate PDF presigned URL for {ticker}: {e}")
            return None

    async def transform_report(self, state: AgentState, ticker_info: dict) -> ReportResponse:
        """Transform AgentState to ReportResponse

        Args:
            state: AgentState from LangGraph workflow
            ticker_info: Ticker info from TickerService

        Returns:
            ReportResponse matching API spec
        """
        ticker_data = state.get("ticker_data", {})
        indicators = state.get("indicators", {})
        percentiles = state.get("percentiles", {})
        news = state.get("news", [])
        report_text = state.get("report", "")

        # Basic info
        ticker = state.get("ticker", "")
        company_name = ticker_info.get("company_name", ticker_data.get("company_name", ""))
        price = float(ticker_data.get("close", 0))

        # Calculate price change
        open_price = float(ticker_data.get("open", price))
        price_change_pct = ((price - open_price) / open_price * 100) if open_price > 0 else 0.0

        currency = ticker_info.get("currency", "USD")

        # Extract timestamp from ticker_data if available
        ticker_timestamp = ticker_data.get("timestamp") or ticker_data.get("date")
        if ticker_timestamp:
            if isinstance(ticker_timestamp, str):
                try:
                    as_of = datetime.fromisoformat(ticker_timestamp.replace("Z", "+00:00"))
                except ValueError:
                    as_of = datetime.now()
            elif isinstance(ticker_timestamp, datetime):
                as_of = ticker_timestamp
            else:
                as_of = datetime.now()
        else:
            as_of = datetime.now()

        # Extract stance and confidence from report
        stance_info = self._extract_stance(report_text, indicators, percentiles)

        # Build summary sections
        summary_sections = self._extract_summary_sections(report_text)

        # Build technical metrics
        technical_metrics = self._build_technical_metrics(indicators, percentiles)

        # Build fundamentals
        fundamentals = self._build_fundamentals(ticker_data)

        # Build news items
        news_items = self._build_news_items(news)

        # Calculate overall sentiment
        overall_sentiment = self._calculate_overall_sentiment(news_items)

        # Build risk assessment
        risk = self._build_risk(indicators, percentiles, report_text)

        # Build peers with correlation analysis
        peers = []
        try:
            peer_service = get_peer_selector_service()
            peer_infos = await peer_service.find_peers_async(
                target_ticker=ticker,
                limit=5,
                period='3mo',
                min_correlation=0.3
            )
            peers = [peer_service.to_api_peer(p) for p in peer_infos]
            logger.info(f"Found {len(peers)} peers for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to fetch peers for {ticker}: {e}")
            peers = []

        # Data sources
        data_sources = [
            "Yahoo Finance - price, volume, fundamentals",
            "Internal dataset - technical percentiles",
            "News - curated feeds with impact scoring"
        ]

        # PDF report URL - generate presigned URL if PDF exists
        pdf_report_url = self._get_pdf_url(state, ticker)

        # Generation metadata
        generation_metadata = GenerationMetadata(
            agent_version="v1.0.0",
            strategy=state.get("strategy", "multi_stage_analysis"),
            generated_at=datetime.now(),
            cache_hit=state.get("cache_hit", False)  # Track if report was from cache
        )

        # Build price history with portfolio metrics
        initial_investment = 1000.0  # Default $1000
        price_history_dicts = self._build_price_history(ticker_data, initial_investment)
        price_history = [PriceDataPoint(**point) for point in price_history_dicts]

        # Build 7-day projections
        projections_dicts = self._build_projections(ticker_data, initial_investment)
        projections = [ProjectionBand(**proj) for proj in projections_dicts]

        # Build scores (key_scores and all_scores)
        scores = self._build_scores(state)
        key_scores = scores.get('key_scores', [])
        all_scores = scores.get('all_scores', [])

        return ReportResponse(
            ticker=ticker,
            company_name=company_name,
            price=price,
            price_change_pct=price_change_pct,
            currency=currency,
            as_of=as_of,
            stance=stance_info["stance"],
            estimated_upside_pct=stance_info.get("upside_pct"),
            confidence=stance_info["confidence"],
            investment_horizon=stance_info["horizon"],
            narrative_report=report_text,
            summary_sections=summary_sections,
            technical_metrics=technical_metrics,
            fundamentals=fundamentals,
            news_items=news_items,
            overall_sentiment=overall_sentiment,
            risk=risk,
            peers=peers,
            price_history=price_history,
            projections=projections,
            initial_investment=initial_investment,
            key_scores=key_scores,
            all_scores=all_scores,
            data_sources=data_sources,
            pdf_report_url=pdf_report_url,
            generation_metadata=generation_metadata
        )

    def _extract_stance(self, report_text: str, indicators: dict, percentiles: dict) -> dict:
        """Extract investment stance from report text

        Uses keyword analysis and technical indicators to determine stance
        """
        # Thai keywords for stance detection
        bullish_keywords = [
            "น่าสนใจ", "แนวโน้มดี", "ปัจจัยบวก", "โอกาส", "เติบโต",
            "แข็งแกร่ง", "สูงขึ้น", "เพิ่มขึ้น", "บวก"
        ]
        bearish_keywords = [
            "ความเสี่ยง", "ระวัง", "อ่อนแอ", "ลดลง", "ปัจจัยลบ",
            "กังวล", "ผันผวน", "ลบ", "แรงขาย"
        ]

        # Count sentiment keywords
        bullish_count = sum(1 for kw in bullish_keywords if kw in report_text)
        bearish_count = sum(1 for kw in bearish_keywords if kw in report_text)

        # Check technical indicators
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)

        # Determine stance
        if bullish_count > bearish_count and rsi < 70:
            stance = "bullish"
        elif bearish_count > bullish_count or rsi > 80:
            stance = "bearish"
        else:
            stance = "neutral"

        # Determine confidence based on signal strength
        signal_strength = abs(bullish_count - bearish_count)
        if signal_strength >= 5:
            confidence = "high"
        elif signal_strength >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Extract investment horizon from report text
        horizon = self._extract_horizon(report_text)

        # Estimated upside (placeholder - needs price target model)
        upside_pct = None

        return {
            "stance": stance,
            "confidence": confidence,
            "horizon": horizon,
            "upside_pct": upside_pct
        }

    def _extract_horizon(self, report_text: str) -> str:
        """Extract investment horizon from report text

        Looks for Thai keywords indicating short, medium, or long-term outlook.

        Args:
            report_text: Report text in Thai

        Returns:
            Investment horizon string (e.g., "1-3 months", "6-12 months", "1-2 years")
        """
        # Short-term indicators (1-3 months)
        short_term_keywords = [
            "ระยะสั้น", "1-3 เดือน", "สัปดาห์", "เดือนหน้า",
            "short term", "short-term", "เทรดรายวัน", "swing trade"
        ]

        # Medium-term indicators (6-12 months)
        medium_term_keywords = [
            "ระยะกลาง", "6-12 เดือน", "ครึ่งปี", "medium term",
            "mid-term", "ไตรมาส", "Q1", "Q2", "Q3", "Q4"
        ]

        # Long-term indicators (1-2+ years)
        long_term_keywords = [
            "ระยะยาว", "1-2 ปี", "หลายปี", "long term", "long-term",
            "ลงทุนยาว", "ถือยาว", "dividend", "ปันผล"
        ]

        report_lower = report_text.lower()

        short_count = sum(1 for kw in short_term_keywords if kw in report_lower)
        medium_count = sum(1 for kw in medium_term_keywords if kw in report_lower)
        long_count = sum(1 for kw in long_term_keywords if kw in report_lower)

        # Determine horizon based on keyword matches
        if short_count > medium_count and short_count > long_count:
            return "1-3 months"
        elif long_count > medium_count and long_count > short_count:
            return "1-2 years"
        else:
            # Default to medium-term
            return "6-12 months"

    def _extract_summary_sections(self, report_text: str) -> SummarySections:
        """Extract summary bullets from report text"""
        # Parse Thai report sections
        # Sections are typically marked with emoji headers

        key_takeaways = []
        price_drivers = []
        risks_to_watch = []

        # Split into sections
        lines = report_text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if '📊' in line or 'ข้อมูลสำคัญ' in line or '**สรุป' in line:
                current_section = 'takeaways'
            elif '💡' in line or 'ปัจจัยขับเคลื่อนราคา' in line or '**ปัจจัย' in line:
                current_section = 'drivers'
            elif '⚠' in line or 'ความเสี่ยง' in line or '**ความเสี่ยง' in line:
                current_section = 'risks'
            # Collect bullet points
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                bullet = line.lstrip('-•* ').strip()
                if current_section == 'takeaways':
                    key_takeaways.append(bullet)
                elif current_section == 'drivers':
                    price_drivers.append(bullet)
                elif current_section == 'risks':
                    risks_to_watch.append(bullet)

        # Fallback: extract first few sentences if no bullets found
        if not key_takeaways:
            sentences = re.split(r'[.!?]\s+', report_text)
            key_takeaways = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]

        return SummarySections(
            key_takeaways=key_takeaways[:5],  # Max 5 items
            price_drivers=price_drivers[:5],
            risks_to_watch=risks_to_watch[:5]
        )

    def _build_technical_metrics(self, indicators: dict, percentiles: dict) -> list[TechnicalMetric]:
        """Build technical metrics array from indicators and percentiles"""
        metrics = []

        # Mapping of indicators to categories and explanations
        indicator_map = {
            'rsi': {
                'name': 'RSI',
                'category': 'momentum',
                'explanation_template': 'RSI at {value:.1f} is at {percentile:.0f}th percentile. {status_desc}'
            },
            'macd': {
                'name': 'MACD',
                'category': 'momentum',
                'explanation_template': 'MACD at {value:.2f} shows {status_desc}'
            },
            'sma_20': {
                'name': 'SMA 20',
                'category': 'trend',
                'explanation_template': '20-day moving average at {value:.2f}. {status_desc}'
            },
            'sma_50': {
                'name': 'SMA 50',
                'category': 'trend',
                'explanation_template': '50-day moving average at {value:.2f}. {status_desc}'
            },
            'sma_200': {
                'name': 'SMA 200',
                'category': 'trend',
                'explanation_template': '200-day moving average at {value:.2f}. {status_desc}'
            },
            'atr_percent': {
                'name': 'ATR %',
                'category': 'volatility',
                'explanation_template': 'Volatility at {value:.2f}%. {status_desc}'
            },
            'volume_ratio': {
                'name': 'Volume Ratio',
                'category': 'liquidity',
                'explanation_template': 'Volume is {value:.2f}x average. {status_desc}'
            }
        }

        for indicator_key, config in indicator_map.items():
            value = indicators.get(indicator_key)
            if value is None:
                continue

            percentile_key = f"{indicator_key}_percentile"
            percentile_data = percentiles.get(percentile_key, {})
            percentile_value = percentile_data.get("percentile", 50.0)

            # Determine status based on indicator type and percentile
            status, status_desc = self._determine_indicator_status(
                indicator_key, value, percentile_value
            )

            # Format explanation
            explanation = config['explanation_template'].format(
                value=value,
                percentile=percentile_value,
                status_desc=status_desc
            )

            metrics.append(TechnicalMetric(
                name=config['name'],
                value=float(value),
                percentile=float(percentile_value),
                category=config['category'],
                status=status,
                explanation=explanation
            ))

        return metrics

    def _determine_indicator_status(
        self, indicator_key: str, value: float, percentile: float
    ) -> tuple[Literal["bullish", "bearish", "neutral", "elevated_risk"], str]:
        """Determine status and description for an indicator"""

        # RSI logic
        if indicator_key == 'rsi':
            if value > 70:
                return ("bearish", "Overbought territory")
            elif value < 30:
                return ("bullish", "Oversold territory")
            elif percentile > 60:
                return ("bullish", "Above average momentum")
            elif percentile < 40:
                return ("bearish", "Below average momentum")
            else:
                return ("neutral", "Neutral momentum")

        # MACD logic
        elif indicator_key == 'macd':
            if value > 0 and percentile > 50:
                return ("bullish", "Positive momentum")
            elif value < 0 and percentile < 50:
                return ("bearish", "Negative momentum")
            else:
                return ("neutral", "Mixed signals")

        # SMA logic (trend)
        elif 'sma' in indicator_key:
            if percentile > 60:
                return ("bullish", "Strong uptrend")
            elif percentile < 40:
                return ("bearish", "Downtrend")
            else:
                return ("neutral", "Ranging")

        # ATR (volatility)
        elif indicator_key == 'atr_percent':
            if percentile > 70:
                return ("elevated_risk", "High volatility")
            elif percentile < 30:
                return ("neutral", "Low volatility")
            else:
                return ("neutral", "Normal volatility")

        # Volume
        elif indicator_key == 'volume_ratio':
            if value > 1.5:
                return ("bullish", "High volume surge")
            elif value < 0.5:
                return ("bearish", "Low volume")
            else:
                return ("neutral", "Average volume")

        return ("neutral", "")

    def _build_fundamentals(self, ticker_data: dict) -> Fundamentals:
        """Build fundamentals from ticker data"""
        valuation = []
        growth = []
        profitability = []

        # Valuation metrics
        pe_ratio = ticker_data.get("pe_ratio")
        if pe_ratio:
            valuation.append(FundamentalMetric(
                name="P/E Ratio",
                value=float(pe_ratio),
                percentile=None,  # Requires sector peer data for comparison
                comment="Price to earnings ratio"
            ))

        market_cap = ticker_data.get("market_cap")
        if market_cap:
            valuation.append(FundamentalMetric(
                name="Market Cap",
                value=float(market_cap),
                percentile=None,
                comment=f"Market capitalization"
            ))

        # Growth metrics (from yfinance if available)
        revenue_growth = ticker_data.get("revenue_growth") or ticker_data.get("revenueGrowth")
        if revenue_growth is not None:
            growth.append(FundamentalMetric(
                name="Revenue Growth",
                value=float(revenue_growth) * 100,  # Convert to percentage
                percentile=None,
                comment=f"{float(revenue_growth) * 100:.1f}% YoY revenue growth"
            ))

        earnings_growth = ticker_data.get("earnings_growth") or ticker_data.get("earningsGrowth")
        if earnings_growth is not None:
            growth.append(FundamentalMetric(
                name="Earnings Growth",
                value=float(earnings_growth) * 100,  # Convert to percentage
                percentile=None,
                comment=f"{float(earnings_growth) * 100:.1f}% YoY earnings growth"
            ))

        # Profitability metrics
        eps = ticker_data.get("eps")
        if eps:
            profitability.append(FundamentalMetric(
                name="EPS",
                value=float(eps),
                percentile=None,
                comment="Earnings per share"
            ))

        dividend_yield = ticker_data.get("dividend_yield")
        if dividend_yield:
            profitability.append(FundamentalMetric(
                name="Dividend Yield",
                value=float(dividend_yield),
                percentile=None,
                comment=f"{dividend_yield:.2f}% dividend yield"
            ))

        return Fundamentals(
            valuation=valuation,
            growth=growth,
            profitability=profitability
        )

    def _build_fundamentals_from_cache(self, report_json: dict) -> Fundamentals:
        """Build fundamentals from cached report_json.

        Cached reports from the API worker store the complete ReportResponse,
        which includes a pre-built 'fundamentals' object. Use that directly
        instead of trying to rebuild from raw ticker_data.

        Args:
            report_json: The cached report's report_json field

        Returns:
            Fundamentals object with valuation, growth, and profitability metrics
        """
        # Check if pre-built fundamentals exists in the cached response
        cached_fundamentals = report_json.get('fundamentals')
        if cached_fundamentals and isinstance(cached_fundamentals, dict):
            # Convert cached dict to FundamentalMetric objects
            valuation = [
                FundamentalMetric(**m) if isinstance(m, dict) else m
                for m in cached_fundamentals.get('valuation', [])
            ]
            growth = [
                FundamentalMetric(**m) if isinstance(m, dict) else m
                for m in cached_fundamentals.get('growth', [])
            ]
            profitability = [
                FundamentalMetric(**m) if isinstance(m, dict) else m
                for m in cached_fundamentals.get('profitability', [])
            ]

            logger.debug(f"Using pre-built fundamentals: {len(valuation)} valuation, "
                        f"{len(growth)} growth, {len(profitability)} profitability metrics")

            return Fundamentals(
                valuation=valuation,
                growth=growth,
                profitability=profitability
            )

        # Fallback: Try to build from ticker_data if available
        ticker_data = report_json.get('ticker_data', {})
        if ticker_data:
            logger.debug("Falling back to building fundamentals from ticker_data")
            return self._build_fundamentals(ticker_data)

        # No fundamentals data available
        logger.warning("No fundamentals data available in cached report")
        return Fundamentals(valuation=[], growth=[], profitability=[])

    def _build_news_items(self, news: list) -> list[NewsItem]:
        """Build news items with sentiment"""
        items = []

        for news_item in news[:10]:  # Limit to 10 most recent
            # Extract timestamp
            timestamp = news_item.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()

            # Get impact score and convert to sentiment
            impact_score = news_item.get("impact_score", 50.0)
            sentiment_label, sentiment_score = self._impact_to_sentiment(impact_score)

            items.append(NewsItem(
                title=news_item.get("title", ""),
                url=news_item.get("link", ""),
                source=news_item.get("publisher", "Unknown"),
                published_at=timestamp,
                sentiment_label=sentiment_label,
                sentiment_score=sentiment_score
            ))

        return items

    def _impact_to_sentiment(self, impact_score: float) -> tuple[Literal["positive", "neutral", "negative"], float]:
        """Convert impact score to sentiment label and score"""
        # Impact score is 0-100, where higher = more impactful
        # Convert to sentiment assuming high impact = positive
        if impact_score >= 70:
            return ("positive", min(impact_score / 100, 1.0))
        elif impact_score >= 40:
            return ("neutral", 0.5)
        else:
            return ("negative", 1.0 - (impact_score / 100))

    def _calculate_overall_sentiment(self, news_items: list[NewsItem]) -> OverallSentiment:
        """Calculate aggregated sentiment percentages"""
        if not news_items:
            return OverallSentiment(positive_pct=33.3, neutral_pct=33.3, negative_pct=33.3)

        positive_count = sum(1 for item in news_items if item.sentiment_label == "positive")
        neutral_count = sum(1 for item in news_items if item.sentiment_label == "neutral")
        negative_count = sum(1 for item in news_items if item.sentiment_label == "negative")
        total = len(news_items)

        return OverallSentiment(
            positive_pct=round(positive_count / total * 100, 1),
            neutral_pct=round(neutral_count / total * 100, 1),
            negative_pct=round(negative_count / total * 100, 1)
        )

    def _build_risk(self, indicators: dict, percentiles: dict, report_text: str) -> Risk:
        """Build risk assessment"""
        # Get uncertainty score
        uncertainty_value = indicators.get("uncertainty_score", 50.0)
        uncertainty_percentile_data = percentiles.get("uncertainty_score_percentile", {})
        uncertainty_percentile = uncertainty_percentile_data.get("percentile", 50.0)

        # Get ATR for volatility
        atr_percent = indicators.get("atr_percent", 1.0)
        atr_percentile_data = percentiles.get("atr_percent_percentile", {})
        atr_percentile = atr_percentile_data.get("percentile", 50.0)

        # Determine risk level
        if uncertainty_percentile > 70 or atr_percentile > 70:
            risk_level = "high"
        elif uncertainty_percentile > 40 and atr_percentile > 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Map ATR percentile to 0-10 volatility score
        volatility_score = round(atr_percentile / 10, 1)

        # Extract risk bullets from report
        risk_bullets = self._extract_risk_bullets(report_text)

        return Risk(
            risk_level=risk_level,
            volatility_score=volatility_score,
            uncertainty_score=UncertaintyScore(
                value=uncertainty_value,
                percentile=uncertainty_percentile
            ),
            risk_bullets=risk_bullets
        )

    def _extract_risk_bullets(self, report_text: str) -> list[str]:
        """Extract risk points from report"""
        risks = []

        # Look for risk section
        lines = report_text.split('\n')
        in_risk_section = False

        for line in lines:
            line = line.strip()
            if '⚠' in line or 'ความเสี่ยง' in line or '**ความเสี่ยง' in line:
                in_risk_section = True
                continue
            elif in_risk_section and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                risk_bullet = line.lstrip('-•* ').strip()
                risks.append(risk_bullet)
            elif in_risk_section and line.startswith('##'):
                # New section started
                break

        # Fallback risks if none found
        if not risks:
            risks = [
                "Market volatility may impact price movements",
                "General market risks apply"
            ]

        return risks[:5]  # Max 5 risks

    def _build_price_history(self, ticker_data: dict, initial_investment: float) -> list:
        """Build price history with portfolio metrics

        Args:
            ticker_data: Ticker data from state
            initial_investment: Initial portfolio value

        Returns:
            List of PriceDataPoint dicts with return_pct and portfolio_nav
        """
        from src.analysis.projection_calculator import ProjectionCalculator
        import pandas as pd

        history_df = ticker_data.get("history")
        if history_df is None or (isinstance(history_df, pd.DataFrame) and history_df.empty):
            logger.debug("No history data available for price_history")
            return []

        # Convert DataFrame to OHLCV dicts
        ohlcv_data = []
        for date_idx, row in history_df.iterrows():
            ohlcv_data.append({
                'date': date_idx.strftime('%Y-%m-%d') if hasattr(date_idx, 'strftime') else str(date_idx),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': int(row.get('Volume', 0))
            })

        # Enhance with portfolio metrics
        calc = ProjectionCalculator(initial_investment=initial_investment)
        enhanced = calc.enhance_historical_data(ohlcv_data)

        logger.info(f"Built price history with {len(enhanced)} data points")
        return enhanced

    def _build_projections(self, ticker_data: dict, initial_investment: float) -> list:
        """Build 7-day projections

        Args:
            ticker_data: Ticker data from state
            initial_investment: Initial portfolio value

        Returns:
            List of ProjectionBand dicts
        """
        from src.analysis.projection_calculator import ProjectionCalculator
        import pandas as pd

        history_df = ticker_data.get("history")
        if history_df is None or (isinstance(history_df, pd.DataFrame) and history_df.empty):
            logger.debug("No history data available for projections")
            return []

        # Extract close prices and dates
        close_prices = history_df['Close'].tolist()

        # Handle DataFrame index - can be datetime or numeric
        from datetime import datetime, timedelta
        dates = []
        for i, date_idx in enumerate(history_df.index):
            if hasattr(date_idx, 'strftime'):
                # Datetime index - use strftime
                dates.append(date_idx.strftime('%Y-%m-%d'))
            elif isinstance(date_idx, (int, float)):
                # Numeric index - calculate date from today going backwards
                days_ago = len(history_df) - i - 1
                date_obj = datetime.now() - timedelta(days=days_ago)
                dates.append(date_obj.strftime('%Y-%m-%d'))
            else:
                # Fallback: use str but log warning
                logger.warning(f"Unexpected DataFrame index type: {type(date_idx)} - {date_idx}")
                dates.append(str(date_idx))

        # Calculate projections
        calc = ProjectionCalculator(initial_investment=initial_investment)
        projections = calc.calculate_projections(close_prices, dates, days_ahead=7)

        logger.info(f"Generated {len(projections)} day projections")
        return projections

    def _build_scores(self, state: AgentState) -> dict:
        """Build key_scores (top 3) and all_scores from user_facing_scores

        Args:
            state: AgentState with user_facing_scores

        Returns:
            Dict with 'key_scores' and 'all_scores' lists
        """
        from .models import ScoringMetric

        scores_data = state.get("user_facing_scores", {})

        if not scores_data:
            logger.debug("No user_facing_scores in state")
            return {'key_scores': [], 'all_scores': []}

        # Convert dict to ScoringMetric objects
        all_scores = []
        for category, score_dict in scores_data.items():
            all_scores.append(ScoringMetric(
                category=score_dict.get('category', category),
                score=float(score_dict.get('score', 0)),
                max_score=10.0,
                rationale=score_dict.get('rationale', '')
            ))

        # Sort by score descending
        all_scores_sorted = sorted(all_scores, key=lambda x: x.score, reverse=True)

        # Top 3 scores
        key_scores = all_scores_sorted[:3]

        logger.info(f"Built {len(all_scores)} scores, top 3: {[s.category for s in key_scores]}")

        return {
            'key_scores': key_scores,
            'all_scores': all_scores
        }

    async def transform_cached_report(
        self,
        cached_report: dict,
        ticker_info: dict
    ) -> ReportResponse:
        """Transform cached report from Aurora to ReportResponse

        Uses the new schema columns:
        - 'date' (data date) instead of 'report_date'
        - 'report_generated_at' instead of 'computed_at'
        - 'pdf_s3_key' for PDF URL generation
        - 'pdf_presigned_url' for cached presigned URL

        Args:
            cached_report: Cached report from precomputed_reports table
            ticker_info: Ticker info from TickerService

        Returns:
            ReportResponse matching API spec
        """
        import json

        ticker = cached_report.get('symbol', '')
        report_text = cached_report.get('report_text', '')
        report_json = cached_report.get('report_json')

        # Parse report_json if it's a string
        if isinstance(report_json, str):
            try:
                report_json = json.loads(report_json)
            except json.JSONDecodeError:
                report_json = {}

        report_json = report_json or {}

        # Extract data from cached report
        company_name = ticker_info.get('company_name', '')
        price = float(report_json.get('price', 0) or 0)
        currency = ticker_info.get('currency', 'USD')

        # Calculate price change (from report_json or default)
        price_change_pct = float(report_json.get('price_change_pct', 0) or 0)

        # Extract timestamp - prefer new 'report_generated_at', fall back to 'computed_at'
        timestamp = (
            cached_report.get('report_generated_at') or
            cached_report.get('computed_at')
        )
        if timestamp:
            if isinstance(timestamp, str):
                try:
                    as_of = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    as_of = datetime.now()
            elif isinstance(timestamp, datetime):
                as_of = timestamp
            else:
                as_of = datetime.now()
        else:
            as_of = datetime.now()

        # Extract indicators and percentiles from report_json
        indicators = report_json.get('indicators', {})
        percentiles = report_json.get('percentiles', {})

        # Extract key_scores and all_scores from cached report_json
        # Aurora stores scores as 'key_scores' (array), not 'user_facing_scores' (dict)
        # This matches the fix applied to rankings_service.py earlier today
        key_scores_raw = report_json.get('key_scores', [])
        all_scores_raw = report_json.get('all_scores', [])

        # Convert to ScoringMetric objects if they're dicts
        if key_scores_raw and isinstance(key_scores_raw, list):
            key_scores = [
                ScoringMetric(**s) if isinstance(s, dict) else s
                for s in key_scores_raw[:3]  # Top 3
            ]
        else:
            key_scores = []

        if all_scores_raw and isinstance(all_scores_raw, list):
            all_scores = [
                ScoringMetric(**s) if isinstance(s, dict) else s
                for s in all_scores_raw
            ]
        else:
            all_scores = []

        logger.debug(f"Extracted {len(key_scores)} key_scores and {len(all_scores)} all_scores from cached report")

        # Extract stance and confidence from report
        stance_info = self._extract_stance(report_text, indicators, percentiles)

        # Build summary sections
        summary_sections = self._extract_summary_sections(report_text)

        # Build technical metrics
        technical_metrics = self._build_technical_metrics(indicators, percentiles)

        # Build fundamentals - use pre-built from report_json if available
        fundamentals = self._build_fundamentals_from_cache(report_json)

        # Build news items from report_json
        news = report_json.get('news', [])
        news_items = self._build_news_items(news)

        # Calculate overall sentiment
        overall_sentiment = self._calculate_overall_sentiment(news_items)

        # Build risk assessment
        risk = self._build_risk(indicators, percentiles, report_text)

        # Extract peers from cached report_json if available
        # No performance penalty since data already exists in Aurora
        peers_raw = report_json.get('peers', [])
        if peers_raw and isinstance(peers_raw, list):
            peers = [
                Peer(**p) if isinstance(p, dict) else p
                for p in peers_raw[:5]  # Max 5 peers
            ]
            logger.debug(f"Extracted {len(peers)} peers from cached report")
        else:
            peers = []

        # Data sources
        data_sources = [
            "Yahoo Finance - price, volume, fundamentals",
            "Internal dataset - technical percentiles",
            "Precomputed cache - instant retrieval"
        ]

        # Chart URL from cached report
        chart_base64 = cached_report.get('chart_base64', '')

        # ================================================================
        # PDF URL handling - use stored presigned URL or generate new one
        # ================================================================
        pdf_report_url = self._get_pdf_url_from_cached_report(cached_report)

        # Generation metadata - mark as cache hit
        generation_metadata = GenerationMetadata(
            agent_version="v1.0.0",
            strategy=cached_report.get('strategy', 'multi-stage'),
            generated_at=as_of,
            cache_hit=True  # Mark as cache hit
        )

        # Extract price_history and projections from cached report_json
        # These fields are essential for chart display in the modal
        price_history_raw = report_json.get('price_history', [])
        projections_raw = report_json.get('projections', [])
        initial_investment = report_json.get('initial_investment', 1000.0)

        # Convert to Pydantic models if they're dicts
        price_history = [
            PriceDataPoint(**p) if isinstance(p, dict) else p
            for p in price_history_raw
        ]

        projections = [
            ProjectionBand(**p) if isinstance(p, dict) else p
            for p in projections_raw
        ]

        logger.debug(f"Extracted {len(price_history)} price_history points and {len(projections)} projections")

        return ReportResponse(
            ticker=ticker,
            company_name=company_name,
            price=price,
            price_change_pct=price_change_pct,
            currency=currency,
            as_of=as_of,
            stance=stance_info["stance"],
            estimated_upside_pct=stance_info.get("upside_pct"),
            confidence=stance_info["confidence"],
            investment_horizon=stance_info["horizon"],
            narrative_report=report_text,
            summary_sections=summary_sections,
            technical_metrics=technical_metrics,
            fundamentals=fundamentals,
            news_items=news_items,
            overall_sentiment=overall_sentiment,
            risk=risk,
            peers=peers,
            price_history=price_history,
            projections=projections,
            initial_investment=initial_investment,
            key_scores=key_scores,
            all_scores=all_scores,
            data_sources=data_sources,
            pdf_report_url=pdf_report_url,
            generation_metadata=generation_metadata
        )

    def _get_pdf_url_from_cached_report(self, cached_report: dict) -> Optional[str]:
        """Get PDF URL from cached report, using stored presigned URL if valid.

        Priority:
        1. Use stored pdf_presigned_url if not expired
        2. Generate new presigned URL from pdf_s3_key
        3. Return None if no PDF available

        Args:
            cached_report: Cached report dict with PDF columns

        Returns:
            Presigned URL string or None
        """
        # Check for stored presigned URL
        stored_url = cached_report.get('pdf_presigned_url')
        expires_at = cached_report.get('pdf_url_expires_at')

        if stored_url and expires_at:
            # Check if URL is still valid
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    expires_at = None

            if expires_at and isinstance(expires_at, datetime):
                if expires_at > datetime.now():
                    logger.debug(f"Using stored presigned URL (expires: {expires_at})")
                    return stored_url
                else:
                    logger.debug(f"Stored presigned URL expired at {expires_at}")

        # Try to generate new presigned URL from pdf_s3_key
        pdf_s3_key = cached_report.get('pdf_s3_key')
        if pdf_s3_key:
            try:
                if self.pdf_storage.is_available():
                    url = self.pdf_storage.get_presigned_url(pdf_s3_key)
                    logger.info(f"Generated new presigned URL for: {pdf_s3_key}")

                    # Optionally update the cached URL in database (async)
                    # This is done by precompute_service.update_pdf_presigned_url()

                    return url
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for {pdf_s3_key}: {e}")

        return None


# Global transformer instance
_transformer: ResponseTransformer | None = None


def get_transformer() -> ResponseTransformer:
    """Get or create global transformer instance"""
    global _transformer
    if _transformer is None:
        _transformer = ResponseTransformer()
    return _transformer
