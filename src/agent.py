from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import operator
from datetime import datetime
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
from src.database import TickerDatabase
from src.news_fetcher import NewsFetcher

class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    ticker: str
    ticker_data: dict
    indicators: dict
    percentiles: dict  # Add percentiles field
    news: list
    news_summary: dict
    report: str
    error: str

class TickerAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
        self.data_fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.news_fetcher = NewsFetcher()
        self.db = TickerDatabase()
        self.ticker_map = self.data_fetcher.load_tickers()
        self.graph = self.build_graph()

    def build_graph(self):
        """Build LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("fetch_data", self.fetch_data)
        workflow.add_node("fetch_news", self.fetch_news)
        workflow.add_node("analyze_technical", self.analyze_technical)
        workflow.add_node("generate_report", self.generate_report)

        # Add edges
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "fetch_news")
        workflow.add_edge("fetch_news", "analyze_technical")
        workflow.add_edge("analyze_technical", "generate_report")
        workflow.add_edge("generate_report", END)

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

        # Save indicators to database
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        self.db.insert_technical_indicators(
            yahoo_ticker, ticker_data['date'], indicators
        )

        state["indicators"] = indicators
        state["percentiles"] = percentiles
        return state

    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM"""
        if state.get("error"):
            return state

        ticker = state["ticker"]
        ticker_data = state["ticker_data"]
        indicators = state["indicators"]
        percentiles = state.get("percentiles", {})
        news = state.get("news", [])
        news_summary = state.get("news_summary", {})

        # Prepare context for LLM
        context = self.prepare_context(ticker, ticker_data, indicators, percentiles, news, news_summary)

        # Get uncertainty score for context
        uncertainty_score = indicators.get('uncertainty_score', 0)

        # Generate report using LLM
        prompt = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers: "Should I BUY MORE?", "Should I SELL?", or "Should I HOLD?" and WHY?

Your job is to weave TECHNICAL + FUNDAMENTAL + RELATIVE + NEWS + STATISTICAL CONTEXT into a flowing narrative that tells the STORY of this stock right now.

CRITICAL NARRATIVE ELEMENTS - You MUST weave these "narrative + number + historical context" components into your story:

1. **Price Uncertainty** ({uncertainty_score:.0f}/100): Sets the overall market mood
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

These 5 elements (4 market conditions + statistical context) ARE the foundation of your narrative. ALWAYS include specific numbers WITH historical context (percentiles) - this is the "narrative + number + history" Damodaran style.

IMPORTANT: When high-impact news [1], [2] exists in the data, reference it naturally in your story when relevant. Don't force it - only use if it meaningfully affects the narrative.

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY. MUST include: uncertainty score context + ATR% + VWAP% + volume ratio with their meanings. Include news naturally if relevant.

Example (with news):
"Apple กำลังอยู่ในโมเมนต์ที่น่าสนใจ - ตลาดเสถียร (ความไม่แน่นอน 22/100 อยู่ในเปอร์เซ็นไทล์ 15% - ต่ำมากในอดีต) ATR แค่ 1.2% (เปอร์เซ็นไทล์ 25%) ราคาเคลื่อนไหวช้ามั่นคง นักลงทุนเห็นตรงกัน แต่ราคา 2.4% เหนือ VWAP (เปอร์เซ็นไทล์ 60%) แสดงแรงซื้อชนะ ปริมาณซื้อขาย 1.3x ของเฉลี่ย (เปอร์เซ็นไทล์ 65%) แสดงนักลงทุนสนใจเพิ่มขึ้น หลังข่าวผลประกอบการที่เกินคาด [1]"

Example (without news):
"Tesla อยู่ในภาวะที่น่ากังวล - ตลาดผันผวนสูง (ความไม่แน่นอน 68/100 อยู่ในเปอร์เซ็นไทล์ 85% - สูงมากในอดีต) ATR 3.8% (เปอร์เซ็นไทล์ 80%) แสดงราคากระโดดขึ้นลง 3-5% ได้ง่าย ราคา -2.1% ต่ำกว่า VWAP (เปอร์เซ็นไทล์ 20%) แสดงแรงขายหนัก แต่ปริมาณซื้อขาย 0.9x ของเฉลี่ย (เปอร์เซ็นไทล์ 45%) แสดงยังไม่มีการขายระห่ำ"

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 flowing paragraphs (NOT numbered lists) that explain WHY this matters to an investor. MUST continuously reference the 4 market condition elements (uncertainty, ATR, VWAP, volume) with numbers throughout. Mix technical + fundamental + relative + news seamlessly.

Example flow (notice how volatility/pressure/volume are woven throughout):
"ราคากำลังขึ้นแรง - ทะลุ SMA ทั้ง 3 เส้น ($175 vs $172 vs $168) และที่สำคัญความผันผวนต่ำ ATR 1.2% (เปอร์เซ็นไทล์ 25% - ต่ำมากในอดีต) แสดงว่านักลงทุนเห็นตรงกัน ไม่มีใครรีบขายออก ราคา 2.4% เหนือ VWAP (เปอร์เซ็นไทล์ 60%) ยืนยันแรงซื้อชนะ เหมาะสะสมระยะยาว

แต่ระวัง - P/E 28 แพงขึ้นจากเดิม และแม้ปริมาณซื้อขาย 1.4x ของเฉลี่ย (เปอร์เซ็นไทล์ 75%) แสดงความสนใจเพิ่มขึ้น แต่ถ้า ATR พุ่งเกิน 2% พร้อมแรงขายเข้ามา (ราคาต่ำกว่า VWAP) หลังจากนักวิเคราะห์ดาวน์เกรด [2] ราคาจะปรับฐานลงเร็ว

นักวิเคราะห์ให้ราคาเป้า $180 สูงกว่าปัจจุบัน $175 และในขณะที่ความไม่แน่นอนยังต่ำ (22/100 อยู่ในเปอร์เซ็นไทล์ 15% - ต่ำมากในอดีต) การถือหุ้นในช่วงนี้มีความเสี่ยงน้อย"

🎯 **ควรทำอะไรตอนนี้?**
Give ONE clear action: BUY MORE / SELL / HOLD. Explain WHY in 2-3 sentences using uncertainty score + market conditions (ATR/VWAP/volume). Reference news if it changes the decision.

Example:
"แนะนำ BUY - ความไม่แน่นอนต่ำ (22/100) ATR 1.2% ตลาดเสถียร ราคา 2.4% เหนือ VWAP แสดงแรงซื้อชนะ ปริมาณซื้อขาย 1.3x แสดงนักลงทุนสนใจ หลังผลประกอบการดี [1] เหมาะเข้าซื้อสะสม ตั้ง stop-loss ที่ $170"

⚠️ **ระวังอะไร?**
Warn about 1-2 key risks using the 4 market condition metrics. What volatility/pressure/volume signals should trigger concern? Keep it practical.

Example:
"ระวังถ้า ATR พุ่งเกิน 2% (จากปัจจุบัน 1.2%) พร้อมราคาตก ต่ำกว่า VWAP และปริมาณซื้อขายระเบิด >2x แสดงตลาดตื่นตระหนก ราคาอาจทะลุ stop-loss ที่ $170 ลงไปถึง $165 ได้"

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

BAD (missing market condition numbers):
"ตลาดผันผวน ราคาขึ้น กำไรดี"

BAD (too mechanical, numbers without meaning):
"ATR = 2.5. VWAP = 450. Volume = 1.3x. ข่าว [1] บอกว่ากำไรขึ้น"

BAD (missing percentile context):
"RSI 75 แสดงภาวะ Overbought" (missing "อยู่ในเปอร์เซ็นไทล์ 85% - สูงมากในอดีต")

GOOD (narrative + number + historical context):
"ความไม่แน่นอน 45/100 (เปอร์เซ็นไทล์ 50% - ปานกลาง) แสดงตลาดผันผวนพอสมควร ATR 2.5% (เปอร์เซ็นไทล์ 60%) ราคาอาจแกว่ง 2-3% ได้ง่าย แต่ราคา 461 เหนือ VWAP 450 ถึง 2.4% (เปอร์เซ็นไทล์ 55%) แสดงแรงซื้อชนะ ปริมาณซื้อขาย 1.3x ของเฉลี่ย (เปอร์เซ็นไทล์ 65%) ยืนยันนักลงทุนสนใจเพิ่มขึ้น โดยเฉพาะหลังข่าวกำไรเกินคาด [1]"

Write entirely in Thai, naturally flowing like Damodaran's style - narrative supported by numbers, not numbers with explanation."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        report = response.content

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
        return state

    def prepare_context(self, ticker, ticker_data, indicators, percentiles=None, news=None, news_summary=None):
        """Prepare context for LLM with uncertainty components and percentile information"""
        current_price = indicators.get('current_price', 0)
        current_volume = indicators.get('volume', 0)
        volume_sma = indicators.get('volume_sma', 0)

        # Get uncertainty score and its components
        uncertainty_score = indicators.get('uncertainty_score', 0)
        atr = indicators.get('atr', 0)
        vwap = indicators.get('vwap', 0)

        # Calculate buy/sell pressure indicators
        if vwap and vwap > 0:
            price_vs_vwap_pct = ((current_price - vwap) / vwap) * 100
        else:
            price_vs_vwap_pct = 0

        if volume_sma and volume_sma > 0:
            volume_ratio = current_volume / volume_sma
        else:
            volume_ratio = 1.0

        # Interpret uncertainty level (don't show score, just interpretation)
        if uncertainty_score < 25:
            uncertainty_level = "ตลาดเสถียรมาก - แรงซื้อขายสมดุล เหมาะสำหรับการวางแผนระยะยาว"
        elif uncertainty_score < 50:
            uncertainty_level = "ตลาดค่อนข้างเสถียร - มีความเคลื่อนไหวปกติ เหมาะสำหรับการลงทุนทั่วไป"
        elif uncertainty_score < 75:
            uncertainty_level = "ตลาดผันผวนสูง - แรงซื้อขายไม่สมดุล ต้องระวังการเปลี่ยนทิศทางอย่างกะทันหัน"
        else:
            uncertainty_level = "ตลาดผันผวนรุนแรง - แรงซื้อขายชนกันหนัก เหมาะสำหรับมืออาชีพเท่านั้น"

        # Interpret volatility (ATR) as percentage
        if atr and current_price > 0:
            atr_percent = (atr / current_price) * 100
            if atr_percent < 1:
                volatility_desc = f"ความผันผวนต่ำมาก (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวช้า มั่นคง"
            elif atr_percent < 2:
                volatility_desc = f"ความผันผวนปานกลาง (ATR {atr_percent:.2f}%) - ราคาเคลื่อนไหวปกติ"
            elif atr_percent < 4:
                volatility_desc = f"ความผันผวนสูง (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวรุนแรง อาจขึ้นลง 3-5% ได้ง่าย"
            else:
                volatility_desc = f"ความผันผวนสูงมาก (ATR {atr_percent:.2f}%) - ราคาแกว่งตัวมาก อาจขึ้นลง 5-10% ภายในวัน"
        else:
            volatility_desc = "ไม่สามารถวัดความผันผวนได้"

        # Interpret buy/sell pressure from VWAP
        if price_vs_vwap_pct > 3:
            vwap_desc = f"แรงซื้อแรงมาก - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) คนซื้อยอมจ่ายแพงกว่าราคาเฉลี่ย แสดงความต้องการสูง"
        elif price_vs_vwap_pct > 1:
            vwap_desc = f"แรงซื้อดี - ราคา {price_vs_vwap_pct:.1f}% เหนือ VWAP ({vwap:.2f}) มีความต้องการซื้อเหนือกว่า"
        elif price_vs_vwap_pct > -1:
            vwap_desc = f"แรงซื้อขายสมดุล - ราคาใกล้เคียง VWAP ({vwap:.2f}) ตลาดยังไม่มีทิศทางชัด"
        elif price_vs_vwap_pct > -3:
            vwap_desc = f"แรงขายเริ่มมี - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) มีแรงกดดันขาย"
        else:
            vwap_desc = f"แรงขายหนัก - ราคา {abs(price_vs_vwap_pct):.1f}% ต่ำกว่า VWAP ({vwap:.2f}) คนขายยอมขายถูกกว่าเฉลี่ย แสดงความตื่นตระหนก"

        # Interpret volume
        if volume_ratio > 2.0:
            volume_desc = f"ปริมาณซื้อขายระเบิด {volume_ratio:.1f}x ของค่าเฉลี่ย - มีเหตุการณ์สำคัญ นักลงทุนใหญ่กำลังเคลื่อนไหว"
        elif volume_ratio > 1.5:
            volume_desc = f"ปริมาณซื้อขายสูง {volume_ratio:.1f}x ของค่าเฉลี่ย - ความสนใจเพิ่มขึ้นมาก"
        elif volume_ratio > 0.7:
            volume_desc = f"ปริมาณซื้อขายปกติ ({volume_ratio:.1f}x ของค่าเฉลี่ย)"
        else:
            volume_desc = f"ปริมาณซื้อขายเงียบ {volume_ratio:.1f}x ของค่าเฉลี่ย - นักลงทุนไม่ค่อยสนใจ อาจรอข่าวใหม่"

        # Add percentile context if available
        percentile_context = ""
        if percentiles:
            percentile_context = "\n\nการวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis - เปรียบเทียบกับประวัติศาสตร์):\n"
            if 'rsi' in percentiles:
                rsi_stats = percentiles['rsi']
                percentile_context += f"- RSI: {rsi_stats['current_value']:.2f} (เปอร์เซ็นไทล์: {rsi_stats['percentile']:.1f}% - สูงกว่าค่าเฉลี่ย {rsi_stats['mean']:.2f})\n"
            if 'uncertainty_score' in percentiles:
                unc_stats = percentiles['uncertainty_score']
                percentile_context += f"- Uncertainty Score: {unc_stats['current_value']:.2f}/100 (เปอร์เซ็นไทล์: {unc_stats['percentile']:.1f}%)\n"
            if 'atr_percent' in percentiles:
                atr_stats = percentiles['atr_percent']
                percentile_context += f"- ATR %: {atr_stats['current_value']:.2f}% (เปอร์เซ็นไทล์: {atr_stats['percentile']:.1f}%)\n"
            if 'volume_ratio' in percentiles:
                vol_stats = percentiles['volume_ratio']
                percentile_context += f"- Volume Ratio: {vol_stats['current_value']:.2f}x (เปอร์เซ็นไทล์: {vol_stats['percentile']:.1f}%)\n"

        context = f"""
สัญลักษณ์: {ticker}
บริษัท: {ticker_data.get('company_name', ticker)}
ราคาปัจจุบัน: {current_price:.2f}
วันที่: {ticker_data.get('date')}

ข้อมูลพื้นฐาน (Fundamental Analysis):
- Market Cap: {self._format_number(ticker_data.get('market_cap'))}
- P/E Ratio: {ticker_data.get('pe_ratio', 'N/A')}
- Forward P/E: {ticker_data.get('forward_pe', 'N/A')}
- EPS: {ticker_data.get('eps', 'N/A')}
- Dividend Yield: {self._format_percent(ticker_data.get('dividend_yield'))}
- Sector: {ticker_data.get('sector', 'N/A')}
- Industry: {ticker_data.get('industry', 'N/A')}
- Revenue Growth: {self._format_percent(ticker_data.get('revenue_growth'))}
- Earnings Growth: {self._format_percent(ticker_data.get('earnings_growth'))}
- Profit Margin: {self._format_percent(ticker_data.get('profit_margin'))}

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
Bollinger: {self.technical_analyzer.analyze_bollinger(indicators)}

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
"""

        # Add news section if news exists
        if news and len(news) > 0:
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
                if hours_ago < 24:
                    time_str = f"{int(hours_ago)}h ago"
                else:
                    days_ago = int(hours_ago / 24)
                    time_str = f"{days_ago}d ago"

                sentiment_indicator = {
                    'positive': '📈 POSITIVE',
                    'negative': '📉 NEGATIVE',
                    'neutral': '📊 NEUTRAL'
                }.get(sentiment, '📊 NEUTRAL')

                news_text += f"[{idx}] {title}\n"
                news_text += f"    Sentiment: {sentiment_indicator} | Impact: {impact_score:.0f}/100 | {time_str}\n\n"

            context += news_text

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

    def analyze_ticker(self, ticker: str) -> str:
        """Main entry point to analyze ticker"""
        initial_state = {
            "messages": [],
            "ticker": ticker,
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "news": [],
            "news_summary": {},
            "report": "",
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return error or report
        if final_state.get("error"):
            return f"❌ เกิดข้อผิดพลาด: {final_state['error']}"

        return final_state.get("report", "ไม่สามารถสร้างรายงานได้")
