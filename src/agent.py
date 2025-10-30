from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import operator
from datetime import datetime
from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
from src.database import TickerDatabase

class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    ticker: str
    ticker_data: dict
    indicators: dict
    report: str
    error: str

class TickerAnalysisAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
        self.data_fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.db = TickerDatabase()
        self.ticker_map = self.data_fetcher.load_tickers()
        self.graph = self.build_graph()

    def build_graph(self):
        """Build LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("fetch_data", self.fetch_data)
        workflow.add_node("analyze_technical", self.analyze_technical)
        workflow.add_node("generate_report", self.generate_report)

        # Add edges
        workflow.set_entry_point("fetch_data")
        workflow.add_edge("fetch_data", "analyze_technical")
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

    def analyze_technical(self, state: AgentState) -> AgentState:
        """Analyze technical indicators"""
        if state.get("error"):
            return state

        ticker_data = state["ticker_data"]
        hist_data = ticker_data.get('history')

        if hist_data is None or hist_data.empty:
            state["error"] = "ไม่มีข้อมูลประวัติสำหรับการวิเคราะห์"
            return state

        # Calculate indicators
        indicators = self.technical_analyzer.calculate_all_indicators(hist_data)

        if not indicators:
            state["error"] = "ไม่สามารถคำนวณ indicators ได้"
            return state

        # Save indicators to database
        yahoo_ticker = self.ticker_map.get(state["ticker"].upper())
        self.db.insert_technical_indicators(
            yahoo_ticker, ticker_data['date'], indicators
        )

        state["indicators"] = indicators
        return state

    def generate_report(self, state: AgentState) -> AgentState:
        """Generate Thai language report using LLM"""
        if state.get("error"):
            return state

        ticker = state["ticker"]
        ticker_data = state["ticker_data"]
        indicators = state["indicators"]

        # Prepare context for LLM
        context = self.prepare_context(ticker, ticker_data, indicators)

        # Generate report using LLM
        prompt = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, tell stories with data.

Data:
{context}

Write a narrative-driven report covering TECHNICAL + FUNDAMENTAL + RELATIVE analysis.

Use the Market Condition components (volatility, buy/sell pressure, volume) as NARRATIVE ELEMENTS throughout your analysis.

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Start with market condition, then weave in technical trend and fundamental story in 2-3 sentences.

Example:
"Honda กำลังในช่วงที่น่าสนใจ - ตลาดเสถียร ATR แค่ 2% ราคาเคลื่อนไหวช้า ทะลุ SMA 200 ขึ้นมา (1,583 vs 1,341) แสดงว่าแรงซื้อกลับมา แต่กำไรลด 42% ต้องระวัง"

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 insights combining ALL THREE analysis types:

1. TECHNICAL + MARKET CONDITION:
"ราคากำลังขึ้นแรง - ทะลุ SMA ทั้ง 3 เส้น ($461 vs $439 vs $405) และที่สำคัญ ATR แค่ 1.2% ความผันผวนต่ำ แรงซื้อขายสมดุล หมายความว่าทุกคนเห็นตรงกัน ไม่มีใครรีบขายออก เหมาะสะสมระยะยาว"

2. FUNDAMENTAL + BUY/SELL PRESSURE:
"แต่ระวัง - P/E 322 แพงมาก และแรงซื้อเริ่มอ่อนแรง ราคา 2.5% เหนือ VWAP แสดงว่าคนซื้อวันนี้จ่ายแพงกว่าเฉลี่ย ถ้ากำไรไตรมาสหน้าไม่ดี คนจะรีบขายทันที"

3. RELATIVE + VOLUME:
"นักวิเคราะห์ให้ราคาเป้า $395 ต่ำกว่าราคาปัจจุบัน $461 และปริมาณซื้อขายเงียบ 0.7x ของค่าเฉลี่ย แสดงว่านักลงทุนใหญ่ไม่กล้าเข้า รอดูก่อน"

4. TECHNICAL + VOLATILITY + FUNDAMENTAL:
"RSI 59 ยังไม่ถึงโซนซื้อเกิน แต่ความผันผวนเริ่มพุ่ง ATR 3.8% แสดงว่าตลาดเริ่มลังเล รายได้โต 11% แต่กำไรลด 37% ต้นทุนพุ่งเร็วกว่ารายได้"

🎯 **ควรทำอะไรตอนนี้?**
Give clear action (BUY MORE / SELL / HOLD) based on ALL analysis + market condition:

"แนะนำ HOLD - ตลาดเสถียร ราคาในเทรนด์ขาขึ้น แต่ P/E สูงเกินไป และปริมาณซื้อขายเงียบ แสดงว่านักลงทุนระมัดระวัง อย่ารีบซื้อเพิ่ม รอกำไรไตรมาสหน้าก่อน"

⚠️ **ระวังอะไร?**
Warn about risks from volatility + volume + fundamentals:

"ระวังถ้าความผันผวนพุ่งขึ้น (ATR เกิน 4%) พร้อมกับปริมาณซื้อขายระเบิด (>2x) แสดงว่ามีข่าวใหญ่ ราคาจะเปลี่ยนแรงและเร็ว ตั้ง stop-loss ไว้ 5-7%"

Rules:
- ALWAYS use volatility/ATR, buy/sell pressure/VWAP, and volume IN your narratives
- Combine technical + fundamental + relative analysis
- NO raw numbers alone - always explain what they MEAN
- Write flowing Thai, not bullet points
- Keep under 12 lines total

BAD: "ATR = 2.5"
GOOD: "ATR 2.5% แสดงว่าราคาแกว่งตัวปานกลาง อาจขึ้นลง 2-3% ได้ง่าย ตั้ง stop-loss ให้กว้าง"

BAD: "VWAP = 450, Price = 461"
GOOD: "ราคา 461 เหนือ VWAP 450 ถึง 2.4% หมายความว่าคนซื้อวันนี้จ่ายแพงกว่าราคาเฉลี่ย แสดงแรงซื้อดี"

BAD: "Volume ratio = 1.8"
GOOD: "ปริมาณซื้อขายสูง 1.8x ของค่าเฉลี่ย แสดงว่าความสนใจเพิ่มขึ้น มีเงินเข้ามาเยอะ"

Write entirely in Thai, naturally flowing."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        report = response.content

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

    def prepare_context(self, ticker, ticker_data, indicators):
        """Prepare context for LLM with uncertainty components"""
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

การวิเคราะห์เทียบเคียง (Relative Analysis):
- คำแนะนำนักวิเคราะห์: {ticker_data.get('recommendation', 'N/A').upper()}
- ราคาเป้าหมายเฉลี่ย: {ticker_data.get('target_mean_price', 'N/A')}
- จำนวนนักวิเคราะห์: {ticker_data.get('analyst_count', 'N/A')}
- ราคาสูงสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_high', 'N/A')}
- ราคาต่ำสุด 52 สัปดาห์: {ticker_data.get('fifty_two_week_low', 'N/A')}
"""
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
            "report": "",
            "error": ""
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return error or report
        if final_state.get("error"):
            return f"❌ เกิดข้อผิดพลาด: {final_state['error']}"

        return final_state.get("report", "ไม่สามารถสร้างรายงานได้")
