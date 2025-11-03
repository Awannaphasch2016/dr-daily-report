from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import operator
from datetime import datetime
import re
import os
import pandas as pd
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
from src.database import TickerDatabase
from src.news_fetcher import NewsFetcher
from src.chart_generator import ChartGenerator
from src.pdf_generator import PDFReportGenerator
from src.audio_generator import AudioGenerator
from src.faithfulness_scorer import FaithfulnessScorer
from src.completeness_scorer import CompletenessScorer
from src.reasoning_quality_scorer import ReasoningQualityScorer
try:
    from src.strategy import SMAStrategyBacktester
    HAS_STRATEGY = True
except ImportError:
    HAS_STRATEGY = False
    SMAStrategyBacktester = None

class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    ticker: str
    ticker_data: dict
    indicators: dict
    percentiles: dict  # Add percentiles field
    chart_patterns: list  # Add chart patterns field
    pattern_statistics: dict  # Add pattern statistics field
    strategy_performance: dict  # Add strategy performance field
    news: list
    news_summary: dict
    chart_base64: str  # Add chart image field (base64 PNG)
    report: str
    faithfulness_score: dict  # Add faithfulness scoring field
    audio_base64: str  # Thai audio (base64 MP3)
    audio_english_base64: str  # English audio (base64 MP3)
    error: str

class TickerAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
        self.data_fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_fetcher = NewsFetcher()
        self.chart_generator = ChartGenerator()
        self.pdf_generator = PDFReportGenerator(use_thai_font=True)
        # Initialize audio generator (optional - will skip if API keys not set)
        try:
            self.audio_generator = AudioGenerator()
        except (ValueError, Exception) as e:
            print(f"⚠️  Audio generator not available: {str(e)}")
            print("   Note: Botnoi API key required for Thai audio, ElevenLabs API key required for English audio")
            self.audio_generator = None
        self.faithfulness_scorer = FaithfulnessScorer()
        self.completeness_scorer = CompletenessScorer()
        self.reasoning_quality_scorer = ReasoningQualityScorer()
        self.db = TickerDatabase()
        self.strategy_backtester = SMAStrategyBacktester(fast_period=20, slow_period=50)
        self.ticker_map = self.data_fetcher.load_tickers()
        self.graph = self.build_graph()

    def build_graph(self):
        """Build LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("fetch_data", self.fetch_data)
        workflow.add_node("fetch_news", self.fetch_news)
        workflow.add_node("analyze_technical", self.analyze_technical)
        workflow.add_node("generate_chart", self.generate_chart)
        workflow.add_node("generate_report", self.generate_report)
        workflow.add_node("generate_audio", self.generate_audio)

        # Add edges
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "fetch_news")
        workflow.add_edge("fetch_news", "analyze_technical")
        workflow.add_edge("analyze_technical", "generate_chart")
        workflow.add_edge("generate_chart", "generate_report")
        workflow.add_edge("generate_report", "generate_audio")
        workflow.add_edge("generate_audio", END)

        return workflow.compile()

    def fetch_data(self, state: AgentState) -> AgentState:
        """Fetch ticker data from Yahoo Finance"""
        ticker = state["ticker"]

        # Get Yahoo ticker from symbol
        yahoo_ticker = self.ticker_map.get(ticker.upper())

        if not yahoo_ticker:
            state["error"] = f"ไม่พบข้อมูล ticker สำหรับ {ticker}"
            return state

        # Fetch data
        data = self.data_fetcher.fetch_ticker_data(yahoo_ticker)

        if not data:
            state["error"] = f"ไม่สามารถดึงข้อมูลสำหรับ {ticker} ({yahoo_ticker}) ได้"
            return state

        # Get additional info
        info = self.data_fetcher.get_ticker_info(yahoo_ticker)
        data.update(info)

        # Save to database
        self.db.insert_ticker_data(
            ticker, yahoo_ticker, data['date'],
            {
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume'],
                'market_cap': data.get('market_cap'),
                'pe_ratio': data.get('pe_ratio'),
                'eps': data.get('eps'),
                'dividend_yield': data.get('dividend_yield')
            }
        )

        state["ticker_data"] = data
        return state

    def fetch_news(self, state: AgentState) -> AgentState:
        """Fetch high-impact news for the ticker"""
        if state.get("error"):
            return state

        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        if not yahoo_ticker:
            state["news"] = []
            state["news_summary"] = {}
            return state

        # Fetch high-impact news (min score 40, max 5 items)
        high_impact_news = self.news_fetcher.filter_high_impact_news(
            yahoo_ticker,
            min_score=40.0,
            max_news=5
        )

        # Get news summary statistics
        news_summary = self.news_fetcher.get_news_summary(high_impact_news)

        state["news"] = high_impact_news
        state["news_summary"] = news_summary

        return state

    def analyze_technical(self, state: AgentState) -> AgentState:
        """Analyze technical indicators with percentile analysis"""
        if state.get("error"):
            return state

        ticker_data = state["ticker_data"]
        hist_data = ticker_data.get('history')

        if hist_data is None or hist_data.empty:
            state["error"] = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
            return state

        # Calculate indicators with percentiles
        result = self.technical_analyzer.calculate_all_indicators_with_percentiles(hist_data)

        if not result or not result.get('indicators'):
            state["error"] = "ไม่สามารถคำนวณ indicators ได้"
            return state

        indicators = result['indicators']
        percentiles = result.get('percentiles', {})
        chart_patterns = result.get('chart_patterns', [])
        pattern_statistics = result.get('pattern_statistics', {})

        # Calculate strategy performance
        strategy_performance = {}
        if self.strategy_backtester:
            try:
                buy_results = self.strategy_backtester.backtest_buy_only(hist_data)
                sell_results = self.strategy_backtester.backtest_sell_only(hist_data)
                
                if buy_results and sell_results:
                    strategy_performance = {
                        'buy_only': buy_results,
                        'sell_only': sell_results,
                        'last_buy_signal': self._get_last_buy_signal(hist_data),
                        'last_sell_signal': self._get_last_sell_signal(hist_data)
                    }
            except Exception as e:
                print(f"Error calculating strategy performance: {str(e)}")
                strategy_performance = {}

        # Save indicators to database
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        self.db.insert_technical_indicators(
            yahoo_ticker, ticker_data['date'], indicators
        )

        state["indicators"] = indicators
        state["percentiles"] = percentiles
        state["chart_patterns"] = chart_patterns
        state["pattern_statistics"] = pattern_statistics
        state["strategy_performance"] = strategy_performance
        return state

    def generate_chart(self, state: AgentState) -> AgentState:
        """Generate technical analysis chart"""
        if state.get("error"):
            return state

        try:
            ticker = state["ticker"]
            ticker_data = state["ticker_data"]
            indicators = state["indicators"]

            # Generate chart (90 days by default)
            chart_base64 = self.chart_generator.generate_chart(
                ticker_data=ticker_data,
                indicators=indicators,
                ticker_symbol=ticker,
                days=90
            )

            state["chart_base64"] = chart_base64
            print(f"✅ Chart generated for {ticker}")

        except Exception as e:
            print(f"⚠️  Chart generation failed: {str(e)}")
            # Don't set error - chart is optional, continue without it
            state["chart_base64"] = ""

        return state

    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM"""
        if state.get("error"):
            return state

        ticker = state["ticker"]
        ticker_data = state["ticker_data"]
        indicators = state["indicators"]
        percentiles = state.get("percentiles", {})
        chart_patterns = state.get("chart_patterns", [])
        pattern_statistics = state.get("pattern_statistics", {})
        strategy_performance = state.get("strategy_performance", {})
        news = state.get("news", [])
        news_summary = state.get("news_summary", {})

        # First pass: Generate report without strategy data to determine recommendation
        context = self.prepare_context(ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=None)
        uncertainty_score = indicators.get('uncertainty_score', 0)
        
        prompt = self._build_prompt(context, uncertainty_score, strategy_performance=None)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        initial_report = response.content

        # Extract recommendation from initial report
        recommendation = self._extract_recommendation(initial_report)
        
        # Check if strategy performance aligns with recommendation
        include_strategy = self._check_strategy_alignment(recommendation, strategy_performance)
        
        # Second pass: If aligned, regenerate with strategy data
        if include_strategy and strategy_performance:
            context_with_strategy = self.prepare_context(
                ticker, ticker_data, indicators, percentiles, news, news_summary, strategy_performance=strategy_performance
            )
            prompt_with_strategy = self._build_prompt(context_with_strategy, uncertainty_score, strategy_performance=strategy_performance)
            response = self.llm.invoke([HumanMessage(content=prompt_with_strategy)])
            report = response.content
        else:
            report = initial_report

        # Add news references at the end if news exists
        if news:
            news_references = self.news_fetcher.get_news_references(news)
            report += f"\n\n{news_references}"
        
        # Add percentile analysis at the end
        if percentiles:
            percentile_analysis = self.technical_analyzer.format_percentile_analysis(percentiles)
            report += f"\n\n{percentile_analysis}"

        # Save report to database
        yahoo_ticker = self.ticker_map.get(ticker.upper())
        self.db.save_report(
            yahoo_ticker,
            ticker_data['date'],
            {
                'report_text': report,
                'technical_summary': self.technical_analyzer.analyze_trend(indicators, indicators.get('current_price')),
                'fundamental_summary': f"P/E: {ticker_data.get('pe_ratio', 'N/A')}",
                'sector_analysis': ticker_data.get('sector', 'N/A')
            }
        )

        state["report"] = report

        # Score narrative faithfulness
        faithfulness_score = self._score_narrative_faithfulness(
            report, indicators, percentiles, news, ticker_data
        )
        state["faithfulness_score"] = faithfulness_score

        # Score narrative completeness
        completeness_score = self._score_narrative_completeness(
            report, ticker_data, indicators, percentiles, news
        )
        state["completeness_score"] = completeness_score

        # Score reasoning quality
        reasoning_quality_score = self._score_reasoning_quality(
            report, indicators, percentiles, ticker_data
        )
        state["reasoning_quality_score"] = reasoning_quality_score

        # Print all score reports
        print("\n" + self.faithfulness_scorer.format_score_report(faithfulness_score))
        print("\n" + self.completeness_scorer.format_score_report(completeness_score))
        print("\n" + self.reasoning_quality_scorer.format_score_report(reasoning_quality_score))

        return state

    def generate_audio(self, state: AgentState) -> AgentState:
        """Generate audio from report text using Botnoi Voice API (Thai) and ElevenLabs (English)"""
        if state.get("error"):
            state["audio_base64"] = ""
            state["audio_english_base64"] = ""
            return state
        
        # Skip if audio generator not available
        if not self.audio_generator:
            state["audio_base64"] = ""
            state["audio_english_base64"] = ""
            return state
        
        report = state.get("report", "")
        
        if not report:
            state["audio_base64"] = ""
            state["audio_english_base64"] = ""
            return state
        
        try:
            # Clean text for TTS (remove markdown, emojis, etc.)
            cleaned_text = self.audio_generator.clean_text_for_tts(report)
            
            # Generate Thai audio using Botnoi (native Thai TTS)
            try:
                audio_base64 = self.audio_generator.generate_audio_base64(
                    cleaned_text,
                    language='th',
                    speed=1.0
                )
                state["audio_base64"] = audio_base64
                print(f"✅ Thai audio generated successfully ({len(audio_base64):,} chars base64)")
            except Exception as e:
                print(f"⚠️  Thai audio generation failed: {str(e)}")
                state["audio_base64"] = ""
            
            # Generate English audio using ElevenLabs
            try:
                # Translate Thai report to English
                english_text = self.audio_generator.translate_to_english(cleaned_text, self.llm)
                print(f"✅ Report translated to English ({len(english_text)} characters)")
                
                # Clean English text for TTS
                cleaned_english = self.audio_generator.clean_text_for_tts(english_text)
                
                # Generate English audio using ElevenLabs
                audio_english_base64 = self.audio_generator.generate_audio_base64(
                    cleaned_english,
                    language='en'
                )
                state["audio_english_base64"] = audio_english_base64
                print(f"✅ English audio generated successfully ({len(audio_english_base64):,} chars base64)")
                
                # Save English audio file
                import base64
                audio_bytes = base64.b64decode(audio_english_base64)
                ticker = state.get("ticker", "UNKNOWN")
                audio_file = f"report_{ticker}_english.mp3"
                with open(audio_file, "wb") as f:
                    f.write(audio_bytes)
                print(f"✅ English audio saved to: {audio_file} ({len(audio_bytes)/1024:.1f} KB)")
                
            except Exception as e:
                print(f"⚠️  English audio generation failed: {str(e)}")
                state["audio_english_base64"] = ""
            
            # Optionally save report to webapp database
            self._save_to_webapp_db(state)
            
        except Exception as e:
            print(f"⚠️  Audio generation failed: {str(e)}")
            # Don't set error - audio is optional, continue without it
            state["audio_base64"] = ""
            state["audio_english_base64"] = ""
        
        return state
    
    def _save_to_webapp_db(self, state: AgentState):
        """Save report to webapp database if webapp is available"""
        webapp_url = os.getenv("WEBAPP_URL", "http://localhost:5000")
        
        try:
            import requests
            from datetime import date
            
            # Extract recommendation
            report = state.get("report", "")
            report_upper = report.upper()
            if 'แนะนำ BUY' in report or 'BUY' in report_upper:
                recommendation = 'BUY'
            elif 'แนะนำ SELL' in report or 'SELL' in report_upper:
                recommendation = 'SELL'
            else:
                recommendation = 'HOLD'
            
            report_data = {
                'ticker': state.get('ticker', '').upper(),
                'report_date': str(date.today()),
                'report_text': report,
                'chart_base64': state.get('chart_base64', ''),
                'audio_base64': state.get('audio_base64', ''),
                'audio_english_base64': state.get('audio_english_base64', ''),
                'indicators': state.get('indicators', {}),
                'percentiles': state.get('percentiles', {}),
                'news': state.get('news', []),
                'recommendation': recommendation
            }
            
            response = requests.post(
                f"{webapp_url}/api/save_report",
                json=report_data,
                timeout=10
            )
            response.raise_for_status()
            print(f"✅ Report saved to webapp database")
            
        except ImportError:
            # requests not available, skip
            pass
        except Exception as e:
            # Webapp not available or error - this is optional, don't fail
            print(f"⚠️  Could not save to webapp database: {str(e)}")
            pass

    def _build_prompt(self, context: str, uncertainty_score: float, strategy_performance: dict = None) -> str:
        """Build LLM prompt with optional strategy performance data"""
        base_intro = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers: "Should I BUY MORE?", "Should I SELL?", or "Should I HOLD?" and WHY?

Your job is to weave TECHNICAL + FUNDAMENTAL + RELATIVE + NEWS + STATISTICAL CONTEXT into a flowing narrative that tells the STORY of this stock right now.

CRITICAL NARRATIVE ELEMENTS - You MUST weave these "narrative + number + historical context" components into your story:

"""

        narrative_elements = self._build_base_prompt_section(uncertainty_score)
        strategy_section = self._build_strategy_section() if strategy_performance else ""
        structure = self._build_prompt_structure(bool(strategy_performance))
        
        return base_intro + narrative_elements + strategy_section + structure
    
    def _build_base_prompt_section(self, uncertainty_score: float) -> str:
        """Build the base narrative elements section"""
        return f"""1. **Price Uncertainty** ({uncertainty_score:.0f}/100): Sets the overall market mood
   - Low (0-25): "ตลาดเสถียรมาก" - Stable, good for positioning
   - Moderate (25-50): "ตลาดค่อนข้างเสถียร" - Normal movement
   - High (50-75): "ตลาดผันผวนสูง" - High risk, be cautious
   - Extreme (75-100): "ตลาดผันผวนรุนแรง" - Extreme risk, warn strongly
   - **IMPORTANT**: Use percentile information to add historical context (e.g., "Uncertainty 52/100 ซึ่งอยู่ในเปอร์เซ็นไทล์ 88% - แสดงว่าความไม่แน่นอนนี้สูงกว่าปกติเมื่อเทียบกับประวัติศาสตร์")

2. **Volatility (ATR %)**: The speed of price movement
   - Include the ATR% number and explain what it means
   - Example: "ATR 1.2% แสดงราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน"
   - Example: "ATR 3.8% แสดงตลาดลังเล ราคากระโดดขึ้นลง 3-5% ได้ง่าย"
   - **IMPORTANT**: Use percentile context (e.g., "ATR 1.99% อยู่ในเปอร์เซ็นไทล์ 61% - สูงกว่าค่าเฉลี่ยปกติเล็กน้อย")

3. **Buy/Sell Pressure (Price vs VWAP %)**: Who's winning - buyers or sellers?
   - Include the % above/below VWAP and explain the implication
   - Example: "ราคา 22.4% เหนือ VWAP แสดงแรงซื้อแรงมาก คนซื้อวันนี้ยอมจ่ายแพงกว่าเฉลี่ย"
   - Example: "ราคา -2.8% ต่ำกว่า VWAP แสดงแรงขายหนัก คนขายรีบขายถูกกว่าเฉลี่ย"
   - **IMPORTANT**: Use percentile to show rarity (e.g., "ราคา 5% เหนือ VWAP ซึ่งอยู่ในเปอร์เซ็นไทล์ 90% - แสดงแรงซื้อที่ผิดปกติมากในอดีต")

4. **Volume (Volume Ratio)**: Is smart money interested?
   - Include the volume ratio (e.g., 0.8x, 1.5x, 2.0x) and explain what it means
   - Example: "ปริมาณซื้อขาย 1.8x ของเฉลี่ย แสดงนักลงทุนใหญ่กำลังเคลื่อนไหว"
   - Example: "ปริมาณซื้อขาย 0.7x ของเฉลี่ย แสดงนักลงทุนเฉยๆ รอดูก่อน"
   - **IMPORTANT**: Use percentile frequency (e.g., "ปริมาณ 1.03x อยู่ในเปอร์เซ็นไทล์ 71% - สูงกว่าปกติ แต่ไม่ใช่ระดับที่ผิดปกติ")

5. **Statistical Context (Percentiles)**: Historical perspective on current values
   - CRITICAL: You MUST incorporate percentile information naturally into your narrative
   - This tells the reader: "Is this value unusual compared to history?"
   - Examples:
     * "RSI 81.12 ซึ่งอยู่ในเปอร์เซ็นไทล์ 94% - สูงมากในอดีต ควรระวังภาวะ Overbought"
     * "MACD 6.32 อยู่ในเปอร์เซ็นไทล์ 77% - สูงกว่าปกติ แสดงแรงซื้อแรงมาก"
     * "Uncertainty 52/100 อยู่ในเปอร์เซ็นไทล์ 88% - ความไม่แน่นอนนี้สูงกว่าปกติในอดีต"
   - Frequency percentages help explain rarity:
     * "RSI นี้สูงกว่า 70% ได้แค่ 28% ของเวลาในอดีต - แสดงภาวะ Overbought ที่หายาก"
     * "Volume 1.03x แต่ในอดีตเคยสูงถึง 2x ได้แค่ 1.9% ของเวลา - ปริมาณปัจจุบันยังไม่ใช่ระดับผิดปกติ"

These 5 elements (4 market conditions + statistical context) ARE the foundation of your narrative. ALWAYS include specific numbers WITH historical context (percentiles) - this is the "narrative + number + history" Damodaran style."""

    def _build_strategy_section(self) -> str:
        """Build strategy performance section"""
        return """

6. **Strategy Performance (Historical Backtesting)**: When strategy performance data is provided, USE IT to support your recommendation
   - CRITICAL: Only include strategy performance when it ALIGNS with your BUY/SELL recommendation
   - Weave strategy performance naturally into your narrative with "narrative + number" style
   - DO NOT mention what strategy was used - just present the performance as evidence
   - Examples of how to incorporate:
     * For BUY recommendation: "หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $175 และเมื่อดูจากสถิติการซื้อเท่านั้น (buy-only strategy) ในอดีต การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +15.2% โดยมี Sharpe ratio 1.2 และอัตราชนะ 62% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงต่ำและให้ผลตอบแทนดี"
     * For SELL recommendation: "หากคุณติดตามกลยุทธ์ของเรา การขายครั้งล่าสุดอยู่ที่ $180 และเมื่อดูจากสถิติการขายเท่านั้น (sell-only strategy) ในอดีต การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย +8.5% โดยมี Sharpe ratio 0.9 และอัตราชนะ 58% - แสดงว่าจุดเข้าแบบนี้มีความเสี่ยงปานกลางและให้ผลตอบแทนดี"
   - Include risk/reward metrics: "Max Drawdown -12.5% แสดงว่าในอดีต ตำแหน่งแบบนี้เสี่ยงสูงสุดที่จะขาดทุน 12.5% ก่อนจะกลับขึ้นมา"
   - Format: "หากคุณติดตามกลยุทธ์ของเรา, การซื้อ/ขายครั้งล่าสุดอยู่ที่ [price] และเมื่อดูจากสถิติการซื้อ/ขายเท่านั้น (buy-only/sell-only strategy) ในอดีต, การเข้าตำแหน่งแบบนี้ให้ผลตอบแทนเฉลี่ย [return]% โดยมี Sharpe ratio [sharpe] และอัตราชนะ [win_rate]% - แสดงว่า[interpretation]"
   - NEVER mention the strategy name (SMA crossing) - just say "กลยุทธ์ของเรา" or "strategies"
   - Use strategy data to strengthen your argument, not as standalone facts"""

    def _build_prompt_structure(self, has_strategy: bool) -> str:
        """Build the report structure section"""
        strategy_integration = "\n- If strategy performance data is provided, weave it naturally into this section to support your analysis" if has_strategy else ""
        strategy_recommendation = "\n- If strategy performance data is provided and aligns with your recommendation, include it here to strengthen your argument (e.g., 'หากคุณติดตามกลยุทธ์ของเรา การซื้อครั้งล่าสุดอยู่ที่ $X และสถิติแสดงว่า...')" if has_strategy else ""
        
        return f"""

IMPORTANT: When high-impact news [1], [2] exists in the data, reference it naturally in your story when relevant. Don't force it - only use if it meaningfully affects the narrative.

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY. MUST include: uncertainty score context + ATR% + VWAP% + volume ratio with their meanings. Include news naturally if relevant.

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 flowing paragraphs (NOT numbered lists) that explain WHY this matters to an investor. MUST continuously reference the 4 market condition elements (uncertainty, ATR, VWAP, volume) with numbers throughout. Mix technical + fundamental + relative + news seamlessly.{strategy_integration}

🎯 **ควรทำอะไรตอนนี้?**
Give ONE clear action: BUY MORE / SELL / HOLD. Explain WHY in 2-3 sentences using uncertainty score + market conditions (ATR/VWAP/volume). Reference news if it changes the decision.{strategy_recommendation}

⚠️ **ระวังอะไร?**
Warn about 1-2 key risks using the 4 market condition metrics. What volatility/pressure/volume signals should trigger concern? Keep it practical.

Rules for narrative flow:
- Tell STORIES, don't list bullet points - write like you're texting a friend investor
- CRITICAL: ALWAYS include all 4 market condition metrics (uncertainty, ATR%, VWAP%, volume ratio) with specific numbers AND percentile context throughout
- Use numbers IN sentences as evidence, not as standalone facts
- Explain WHY things matter (implication), not just WHAT they are (description)
- Mix technical + fundamental + relative + news + statistical context seamlessly - don't section them
- Reference news [1], [2] ONLY when it genuinely affects the story
- CRITICAL: When percentile data is available, USE IT to add historical context to numbers (e.g., "RSI 75 ซึ่งอยู่ในเปอร์เซ็นไทล์ 85%")
- Write under 12-15 lines total
- NO tables, NO numbered lists in the insight section, just flowing narrative

Write entirely in Thai, naturally flowing like Damodaran's style - narrative supported by numbers, not numbers with explanation."""

    def _calculate_market_conditions(self, indicators: dict) -> dict:
        """Calculate market condition metrics"""
        current_price = indicators.get('current_price', 0)
        current_volume = indicators.get('volume', 0)
        volume_sma = indicators.get('volume_sma', 0)
        uncertainty_score = indicators.get('uncertainty_score', 0)
        atr = indicators.get('atr', 0)
        vwap = indicators.get('vwap', 0)
        
        # Calculate buy/sell pressure indicators
        price_vs_vwap_pct = ((current_price - vwap) / vwap) * 100 if vwap and vwap > 0 else 0
        volume_ratio = current_volume / volume_sma if volume_sma and volume_sma > 0 else 1.0
        
        return {
            'current_price': current_price,
            'uncertainty_score': uncertainty_score,
            'atr': atr,
            'vwap': vwap,
            'price_vs_vwap_pct': price_vs_vwap_pct,
            'volume_ratio': volume_ratio
        }
    
    def _interpret_uncertainty_level(self, uncertainty_score: float) -> str:
        """Interpret uncertainty score into Thai description"""
        if uncertainty_score < 25:
            return "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
        elif uncertainty_score < 50:
            return "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
        elif uncertainty_score < 75:
            return "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
        else:
            return "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"
    
    def _interpret_volatility(self, atr: float, current_price: float) -> str:
        """Interpret ATR volatility into Thai description"""
        if atr and current_price > 0:
            atr_percent = (atr / current_price) * 100
            if atr_percent < 1:
                return f"ความผันผวนต่ำมาก (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวช้า มั่นคง"
            elif atr_percent < 2:
                return f"ความผันผวนปานกลาง (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวปกติ"
            elif atr_percent < 4:
                return f"ความผันผวนสูง (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวรุนแรง อาจขึ้นลง 3-5% ได้ง่าย"
            else:
                return f"ความผันผวนสูงมาก (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวมาก อาจขึ้นลง 5-10% ภายในวัน"
        return "ไม่สามารถวัดความผันผวนได้"
    
    def _interpret_vwap_pressure(self, price_vs_vwap_pct: float, vwap: float) -> str:
        """Interpret VWAP pressure into Thai description"""
        if price_vs_vwap_pct > 3:
            return f"แรงซื้อแรงมาก - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) คนซื้อยอมจ่ายแพงกว่าราคาเฉลี่ย แสดงความต้องการสูง"
        elif price_vs_vwap_pct > 1:
            return f"แรงซื้อดี - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) มีความต้องการซื้อเหนือกว่า"
        elif price_vs_vwap_pct > -1:
            return f"แรงซื้อขายสมดุล - ราคาใกล้เคียง VWAP ({vwap:.2f}) ตลาดยังไม่มีทิศทางชัด"
        elif price_vs_vwap_pct > -3:
            return f"แรงขายเริ่มมี - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) มีแรงกดดันขาย"
        else:
            return f"แรงขายหนัก - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) คนขายยอมขายถูกกว่าเฉลี่ย แสดงความตื่นตระหนก"
    
    def _interpret_volume(self, volume_ratio: float) -> str:
        """Interpret volume ratio into Thai description"""
        if volume_ratio > 2.0:
            return f"ปริมาณซื้อขายระเบิด {volume_ratio:.1f}x ของค่าเฉลี่ย - มีเหตุการณ์สำคัญ นักลงทุนใหญ่กำลังเคลื่อนไหว"
        elif volume_ratio > 1.5:
            return f"ปริมาณซื้อขายสูง {volume_ratio:.1f}x ของค่าเฉลี่ย - ความสนใจเพิ่มขึ้นมาก"
        elif volume_ratio > 0.7:
            return f"ปริมาณซื้อขายปกติ ({volume_ratio:.1f}x ของค่าเฉลี่ย)"
        else:
            return f"ปริมาณซื้อขายเงียบ {volume_ratio:.1f}x ของค่าเฉลี่ย - นักลงทุนไม่ค่อยสนใจ อาจรอข่าวใหม่"
    
    def _format_percentile_context(self, percentiles: dict) -> str:
        """Format percentile context for prompt"""
        if not percentiles:
            return ""
        
        context = "\n\nการวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis - เปรียบเทียบกับประวัติศาสตร์):\n"
        
        if 'rsi' in percentiles:
            rsi_stats = percentiles['rsi']
            context += f"- RSI: {rsi_stats['current_value']:.2f} (เปอร์เซ็นไทล์: {rsi_stats['percentile']:.1f}% - สูงกว่าค่าเฉลี่ย {rsi_stats['mean']:.2f})\n"
            context += f"  ความถี่ที่ RSI > 70: {rsi_stats['frequency_above_70']:.1f}% | ความถี่ที่ RSI < 30: {rsi_stats['frequency_below_30']:.1f}%\n"
        
        if 'macd' in percentiles:
            macd_stats = percentiles['macd']
            context += f"- MACD: {macd_stats['current_value']:.4f} (เปอร์เซ็นไทล์: {macd_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ MACD > 0: {macd_stats['frequency_positive']:.1f}%\n"
        
        if 'uncertainty_score' in percentiles:
            unc_stats = percentiles['uncertainty_score']
            context += f"- Uncertainty Score: {unc_stats['current_value']:.2f}/100 (เปอร์เซ็นไทล์: {unc_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ต่ำ (<25): {unc_stats['frequency_low']:.1f}% | ความถี่ที่สูง (>75): {unc_stats['frequency_high']:.1f}%\n"
        
        if 'atr_percent' in percentiles:
            atr_stats = percentiles['atr_percent']
            context += f"- ATR %: {atr_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {atr_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ความผันผวนต่ำ (<1%): {atr_stats['frequency_low_volatility']:.1f}% | ความถี่ที่ความผันผวนสูง (>4%): {atr_stats['frequency_high_volatility']:.1f}%\n"
        
        if 'price_vwap_percent' in percentiles:
            vwap_stats = percentiles['price_vwap_percent']
            context += f"- Price vs VWAP %: {vwap_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {vwap_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ราคาเหนือ VWAP >3%: {vwap_stats['frequency_above_3pct']:.1f}% | ความถี่ที่ราคาต่ำกว่า VWAP <-3%: {vwap_stats['frequency_below_neg3pct']:.1f}%\n"
        
        if 'volume_ratio' in percentiles:
            vol_stats = percentiles['volume_ratio']
            context += f"- Volume Ratio: {vol_stats['current_value']:.2f}x (เปอร์เซ็นไทล์: {vol_stats['percentile']:.1f}%)\n"
            context += f"  ความถี่ที่ปริมาณสูง (>2x): {vol_stats['frequency_high_volume']:.1f}% | ความถี่ที่ปริมาณต่ำ (<0.7x): {vol_stats['frequency_low_volume']:.1f}%\n"
        
        context += "\n**IMPORTANT**: Use these percentile values naturally in your narrative to add historical context. Don't just list them - weave them into the story!"
        return context

    def _score_narrative_faithfulness(
        self,
        report: str,
        indicators: dict,
        percentiles: dict,
        news: list,
        ticker_data: dict
    ):
        """Score narrative faithfulness to ground truth data"""
        # Calculate market conditions for ground truth
        market_conditions = self._calculate_market_conditions(indicators)

        # Prepare ground truth with additional metrics
        ground_truth = {
            'uncertainty_score': indicators.get('uncertainty_score', 0),
            'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100 if indicators.get('current_price', 0) > 0 else 0,
            'vwap_pct': market_conditions.get('price_vs_vwap_pct', 0),
            'volume_ratio': market_conditions.get('volume_ratio', 0),
        }

        # Score the narrative
        faithfulness_score = self.faithfulness_scorer.score_narrative(
            narrative=report,
            ground_truth=ground_truth,
            indicators=indicators,
            percentiles=percentiles,
            news_data=news
        )

        return faithfulness_score
    
    def _score_narrative_completeness(
        self,
        report: str,
        ticker_data: dict,
        indicators: dict,
        percentiles: dict,
        news: list
    ):
        """Score narrative completeness across analytical dimensions"""
        completeness_score = self.completeness_scorer.score_narrative(
            narrative=report,
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles,
            news_data=news
        )
        
        return completeness_score
    
    def _score_reasoning_quality(
        self,
        report: str,
        indicators: dict,
        percentiles: dict,
        ticker_data: dict
    ):
        """Score reasoning quality of narrative explanations"""
        reasoning_quality_score = self.reasoning_quality_scorer.score_narrative(
            narrative=report,
            indicators=indicators,
            percentiles=percentiles,
            ticker_data=ticker_data
        )
        
        return reasoning_quality_score
    
    def _format_fundamental_section(self, ticker_data: dict) -> str:
        """Format fundamental analysis section"""
        return f"""ข้อมูลพื้นฐาน (Fundamental Analysis):
- Market Cap: {self._format_number(ticker_data.get('market_cap'))}
- P/E Ratio: {ticker_data.get('pe_ratio', 'N/A')}
- Forward P/E: {ticker_data.get('forward_pe', 'N/A')}
- EPS: {ticker_data.get('eps', 'N/A')}
- Dividend Yield: {self._format_percent(ticker_data.get('dividend_yield'))}
- Sector: {ticker_data.get('sector', 'N/A')}
- Industry: {ticker_data.get('industry', 'N/A')}
- Revenue Growth: {self._format_percent(ticker_data.get('revenue_growth'))}
- Earnings Growth: {self._format_percent(ticker_data.get('earnings_growth'))}
- Profit Margin: {self._format_percent(ticker_data.get('profit_margin'))}"""
    
    def _format_technical_section(self, indicators: dict, current_price: float) -> str:
        """Format technical analysis section"""
        return f"""
การวิเคราะห์ทางเทคนิค (Technical Analysis):
- SMA 20: {indicators.get('sma_20', 'N/A'):.2f}
- SMA 50: {indicators.get('sma_50', 'N/A'):.2f}
- SMA 200: {indicators.get('sma_200', 'N/A'):.2f}
- RSI: {indicators.get('rsi', 'N/A'):.2f}
- MACD: {indicators.get('macd', 'N/A'):.2f}
- Signal: {indicators.get('macd_signal', 'N/A'):.2f}
- Bollinger Upper: {indicators.get('bb_upper', 'N/A'):.2f}
- Bollinger Middle: {indicators.get('bb_middle', 'N/A'):.2f}
- Bollinger Lower: {indicators.get('bb_lower', 'N/A'):.2f}

แนวโน้ม: {self.technical_analyzer.analyze_trend(indicators, current_price)}
โมเมนตัม: {self.technical_analyzer.analyze_momentum(indicators)}
MACD Signal: {self.technical_analyzer.analyze_macd(indicators)}
Bollinger: {self.technical_analyzer.analyze_bollinger(indicators)}"""
    
    def _format_news_section(self, news: list, news_summary: dict) -> str:
        """Format news section"""
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
            now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
            hours_ago = (now - timestamp).total_seconds() / 3600
            time_str = f"{int(hours_ago)}h ago" if hours_ago < 24 else f"{int(hours_ago / 24)}d ago"

            sentiment_indicator = {
                'positive': '📈 POSITIVE',
                'negative': '📉 NEGATIVE',
                'neutral': '📊 NEUTRAL'
            }.get(sentiment, '📊 NEUTRAL')

            news_text += f"[{idx}] {title}\n"
            news_text += f"    Sentiment: {sentiment_indicator} | Impact: {impact_score:.0f}/100 | {time_str}\n\n"

        return news_text
    
    def prepare_context(self, ticker: str, ticker_data: dict, indicators: dict, percentiles: dict, news: list, news_summary: dict, strategy_performance: dict = None) -> str:
        """Prepare context for LLM with uncertainty components and percentile information"""
        conditions = self._calculate_market_conditions(indicators)
        current_price = conditions['current_price']
        
        uncertainty_level = self._interpret_uncertainty_level(conditions['uncertainty_score'])
        volatility_desc = self._interpret_volatility(conditions['atr'], current_price)
        vwap_desc = self._interpret_vwap_pressure(conditions['price_vs_vwap_pct'], conditions['vwap'])
        volume_desc = self._interpret_volume(conditions['volume_ratio'])
        percentile_context = self._format_percentile_context(percentiles)
        fundamental_section = self._format_fundamental_section(ticker_data)
        technical_section = self._format_technical_section(indicators, current_price)
        news_section = self._format_news_section(news, news_summary)
        
        context = f"""
สัญลักษณ์: {ticker}
บริษัท: {ticker_data.get('company_name', ticker)}
ราคาปัจจุบัน: {current_price:.2f}
วันที่: {ticker_data.get('date')}

{fundamental_section}
{technical_section}
สภาวะตลาด (Market Condition - USE THESE IN YOUR NARRATIVE):
สถานะ: {uncertainty_level}

1. ความผันผวน (Volatility): {volatility_desc}

2. แรงซื้อ-ขาย (Buy/Sell Pressure): {vwap_desc}

3. ปริมาณการซื้อขาย (Volume): {volume_desc}
{percentile_context}
การวิเคราะห์เทียบเคียง (Relative Analysis):
- คำแนะนำนักวิเคราะห์: {ticker_data.get('recommendation', 'N/A').upper()}
- ราคาเป้าหมายเฉลี่ย: {ticker_data.get('target_mean_price', 'N/A')}
- จำนวนนักวิเคราะห์: {ticker_data.get('analyst_count', 'N/A')}
- ราคาสูงสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_high', 'N/A')}
- ราคาต่ำสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_low', 'N/A')}
{news_section}"""
        
        return context

    def _format_number(self, value):
        """Format large numbers"""
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

    def _format_percent(self, value):
        """Format percentage"""
        if value is None:
            return "N/A"
        return f"{value*100:.2f}%"

    def _get_last_buy_signal(self, hist_data):
        """Get last buy signal information"""
        try:
            df = self.strategy_backtester.detect_signals(hist_data)
            if df is None or df.empty:
                return None
            
            buy_signals = df[df['Buy_Signal'] == True]
            if buy_signals.empty:
                return None
            
            last_buy = buy_signals.iloc[-1]
            return {
                'date': last_buy.name,
                'price': float(last_buy['Close']),
                'sma_fast': float(last_buy['SMA_Fast']) if pd.notna(last_buy['SMA_Fast']) else None,
                'sma_slow': float(last_buy['SMA_Slow']) if pd.notna(last_buy['SMA_Slow']) else None
            }
        except Exception as e:
            print(f"Error getting last buy signal: {str(e)}")
            return None

    def _get_last_sell_signal(self, hist_data):
        """Get last sell signal information"""
        if not self.strategy_backtester:
            return None
        try:
            df = self.strategy_backtester.detect_signals(hist_data)
            if df is None or df.empty:
                return None
            
            sell_signals = df[df['Sell_Signal'] == True]
            if sell_signals.empty:
                return None
            
            last_sell = sell_signals.iloc[-1]
            return {
                'date': last_sell.name,
                'price': float(last_sell['Close']),
                'sma_fast': float(last_sell['SMA_Fast']) if pd.notna(last_sell['SMA_Fast']) else None,
                'sma_slow': float(last_sell['SMA_Slow']) if pd.notna(last_sell['SMA_Slow']) else None
            }
        except Exception as e:
            print(f"Error getting last sell signal: {str(e)}")
            return None

    def _extract_recommendation(self, report: str) -> str:
        """Extract BUY/SELL/HOLD recommendation from report"""
        report_upper = report.upper()
        
        # Look for BUY signals
        if 'BUY MORE' in report_upper or 'BUY' in report_upper:
            if 'แนะนำ BUY' in report or 'แนะนำ BUY MORE' in report or 'BUY MORE' in report_upper:
                return 'BUY'
        
        # Look for SELL signals
        if 'SELL' in report_upper:
            if 'แนะนำ SELL' in report or 'SELL' in report_upper:
                return 'SELL'
        
        # Default to HOLD
        return 'HOLD'

    def _check_strategy_alignment(self, recommendation: str, strategy_performance: dict) -> bool:
        """Check if strategy performance aligns with recommendation"""
        if not strategy_performance or not strategy_performance.get('buy_only') or not strategy_performance.get('sell_only'):
            return False
        
        buy_perf = strategy_performance['buy_only']
        sell_perf = strategy_performance['sell_only']
        
        # Check if we have valid performance data
        buy_return = buy_perf.get('total_return_pct', 0)
        buy_sharpe = buy_perf.get('sharpe_ratio', 0)
        buy_win_rate = buy_perf.get('win_rate', 0)
        
        sell_return = sell_perf.get('total_return_pct', 0)
        sell_sharpe = sell_perf.get('sharpe_ratio', 0)
        sell_win_rate = sell_perf.get('win_rate', 0)
        
        if recommendation == 'BUY':
            # For BUY recommendation, buy_only strategy should perform well
            # Consider aligned if: positive return OR good sharpe (>0.5) OR good win rate (>50%)
            return buy_return > 0 or buy_sharpe > 0.5 or buy_win_rate > 50
        
        elif recommendation == 'SELL':
            # For SELL recommendation, sell_only strategy should perform well
            # Consider aligned if: positive return OR good sharpe (>0.5) OR good win rate (>50%)
            return sell_return > 0 or sell_sharpe > 0.5 or sell_win_rate > 50
        
        # For HOLD, we don't include strategy data
        return False

    def analyze_ticker(self, ticker: str) -> str:
        """Main entry point to analyze ticker"""
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "chart_base64": "",
            "report": "",
            "audio_base64": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return error or report
        if final_state.get("error"):
            return f"❌ เกิดข้อผิดพลาด: {final_state['error']}"

        return final_state.get("report", "ไม่สามารถสร้างรายงานได้")

    def generate_pdf_report(self, ticker: str, output_path: str = None) -> bytes:
        """
        Generate PDF report for ticker analysis

        Args:
            ticker: Ticker symbol
            output_path: Optional path to save PDF file (if None, returns bytes)

        Returns:
            PDF bytes if output_path is None, otherwise saves to file and returns bytes
        """
        # Run analysis
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "chart_base64": "",
            "report": "",
            "audio_base64": "",
            "faithfulness_score": {},
            "completeness_score": {},
            "reasoning_quality_score": {},
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            raise ValueError(f"Analysis failed: {final_state['error']}")

        # Generate PDF
        pdf_bytes = self.pdf_generator.generate_report(
            ticker=ticker,
            ticker_data=final_state.get("ticker_data", {}),
            indicators=final_state.get("indicators", {}),
            percentiles=final_state.get("percentiles", {}),
            news=final_state.get("news", []),
            news_summary=final_state.get("news_summary", {}),
            chart_base64=final_state.get("chart_base64", ""),
            report=final_state.get("report", ""),
            output_path=output_path
        )

        return pdf_bytes
