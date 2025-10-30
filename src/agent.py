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

        # Get uncertainty score for prompt guidance
        uncertainty_score = indicators.get('uncertainty_score', 0)

        # Generate report using LLM
        prompt = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers: "Should I BUY MORE?", "Should I SELL?", or "Should I HOLD LONGER?" and WHY?

CRITICAL: Use the Uncertainty Score ({uncertainty_score:.1f}/100) to guide your narrative tone and recommendation:
- Low (0-25): "ตลาดเสถียร" - Good for positioning/accumulating, emphasize stability
- Moderate (25-50): "ผันผวนพอสมควร" - Caution advised, watch for signals
- High (50-75): "ผันผวนสูง" - High risk, only for experienced traders
- Extreme (75-100): "ผันผวนรุนแรง" - Warn strongly about timing risk

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY. INCLUDE uncertainty context naturally:

Low Uncertainty Example:
"Tesla อยู่ในจังหวะที่น่าสนใจ - ตลาดเสถียร (Uncertainty 22/100) ราคาทะลุ SMA ทั้ง 3 เส้น แสดงว่านักลงทุนกำลังกลับมาอย่างมั่นคง"

High Uncertainty Example:
"Tesla อยู่ในโซนอันตราย - ตลาดผันผวนสูง (Uncertainty 68/100) ราคาพุ่งขึ้นแรงแต่ ATR สูงบอกว่าอาจปรับลงไวเหมือนกัน"

Extreme Uncertainty Example:
"Tesla อยู่ในภาวะสับวุ่น - ตลาดผันผวนรุนแรง (Uncertainty 82/100) ราคากระโดดขึ้นลงทุกวัน แรงซื้อแรงขายชนกันหนัก"

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 key insights as STORIES. WEAVE IN uncertainty implications:

Low Uncertainty + Uptrend:
"ราคากำลังขึ้นแข็งแกร่งและมั่นคง - ทะลุเส้น SMA 20, 50 และ 200 ($461 vs $439 vs $405) และความผันผวนต่ำ (22/100) หมายความว่าทุกคนเห็นตรงกัน เหมาะสะสมระยะยาว"

High Uncertainty + Valuation:
"ระวัง - ตลาดจ่ายแพง P/E 322 และความผันผวนสูง (68/100) ถ้ากำไรไม่ดีตามคาด ราคาจะปรับลงแรงและเร็วมาก"

Extreme Uncertainty + VWAP:
"ราคาเหนือ VWAP แสดงว่าแรงซื้อชนะ แต่ความผันผวนรุนแรง (85/100) และ ATR พุ่งสูง ถึงราคาขึ้นก็ขึ้นแรงลงก็ลงไว ต้องมี stop-loss แน่น"

🎯 **ควรทำอะไรตอนนี้?**
Tell them clearly: BUY MORE / SELL / HOLD LONGER. FACTOR IN uncertainty:

Low Uncertainty: "แนะนำ BUY MORE - ตลาดเสถียร ราคาในเทรนด์ขาขึ้น ความผันผวนต่ำทำให้ความเสี่ยงน้อย"

High Uncertainty: "แนะนำ HOLD และรอดู - ถึงราคาจะขึ้น แต่ความผันผวนสูงทำให้จับจังหวะยาก อย่ารีบซื้อเพิ่ม"

Extreme Uncertainty: "แนะนำ SELL ครึ่งหรือ HOLD แน่น - ความผันผวนรุนแรงเกินไป ถ้ายังถือต้องมี stop-loss 5-7%"

⚠️ **ระวังอะไร?**
Emphasize uncertainty-related risks:

Low: "ระวังถ้าความผันผวนพุ่งขึ้นเกิน 40-50 แสดงว่าตลาดเริ่มลังเล อาจเป็นสัญญาณเปลี่ยนทิศ"

High: "ระวังความผันผวนนี้มาก - Uncertainty 68/100 หมายความว่าราคาอาจกระโดด 5-10% ได้ง่าย ตั้ง stop-loss ให้กว้าง"

Extreme: "อย่าเล่นกับไฟ - Uncertainty 85/100 นี่คือโซนที่มืออาชีพยังระวัง ราคาพุ่งขึ้นลงได้ 10-20% ในไม่กี่วัน"

Rules:
- Tell STORIES, don't list bullet points
- ALWAYS mention Uncertainty Score naturally and explain what it means
- Use numbers IN sentences as evidence
- Explain WHY things matter, not just WHAT they are
- Write like texting a friend investor advice
- Keep under 12 lines total
- NO tables, NO bullet lists, just flowing narrative

BAD: "Uncertainty Score = 68.5"
GOOD: "ตลาดผันผวนสูง (68/100) แสดงว่าราคาอาจกระโดด 5-10% ได้ง่าย ไม่เหมาะกับคนนอนไม่หลับ"

BAD: "VWAP = 450"
GOOD: "ราคา 461 เหนือ VWAP 450 หมายความว่าคนซื้อวันนี้จ่ายแพงกว่าคนซื้อเฉลี่ย แสดงแรงซื้อแข็งแกร่ง"

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
        """Prepare context for LLM"""
        current_price = indicators.get('current_price', 0)

        # Get uncertainty score interpretation
        uncertainty_score = indicators.get('uncertainty_score', 0)
        uncertainty_analysis = self.technical_analyzer.analyze_uncertainty(indicators)

        context = f"""
สัญลักษณ์: {ticker}
บริษัท: {ticker_data.get('company_name', ticker)}
ราคาปัจจุบัน: {current_price:.2f}
วันที่: {ticker_data.get('date')}

ข้อมูลพื้นฐาน:
- Market Cap: {self._format_number(ticker_data.get('market_cap'))}
- P/E Ratio: {ticker_data.get('pe_ratio', 'N/A')}
- Forward P/E: {ticker_data.get('forward_pe', 'N/A')}
- EPS: {ticker_data.get('eps', 'N/A')}
- Dividend Yield: {self._format_percent(ticker_data.get('dividend_yield'))}
- Sector: {ticker_data.get('sector', 'N/A')}
- Industry: {ticker_data.get('industry', 'N/A')}

การวิเคราะห์ทางเทคนิค:
- SMA 20: {indicators.get('sma_20', 'N/A'):.2f}
- SMA 50: {indicators.get('sma_50', 'N/A'):.2f}
- SMA 200: {indicators.get('sma_200', 'N/A'):.2f}
- RSI: {indicators.get('rsi', 'N/A'):.2f}
- MACD: {indicators.get('macd', 'N/A'):.2f}
- Signal: {indicators.get('macd_signal', 'N/A'):.2f}
- Bollinger Upper: {indicators.get('bb_upper', 'N/A'):.2f}
- Bollinger Middle: {indicators.get('bb_middle', 'N/A'):.2f}
- Bollinger Lower: {indicators.get('bb_lower', 'N/A'):.2f}
- VWAP: {indicators.get('vwap', 'N/A'):.2f}
- ATR: {indicators.get('atr', 'N/A'):.4f}

แนวโน้ม: {self.technical_analyzer.analyze_trend(indicators, current_price)}
โมเมนตัม: {self.technical_analyzer.analyze_momentum(indicators)}
MACD Signal: {self.technical_analyzer.analyze_macd(indicators)}
Bollinger: {self.technical_analyzer.analyze_bollinger(indicators)}

ความไม่แน่นอนของราคา (Pricing Uncertainty):
{uncertainty_analysis}

ความเห็นนักวิเคราะห์:
- คำแนะนำ: {ticker_data.get('recommendation', 'N/A').upper()}
- ราคาเป้าหมายเฉลี่ย: {ticker_data.get('target_mean_price', 'N/A')}
- จำนวนนักวิเคราะห์: {ticker_data.get('analyst_count', 'N/A')}

ช่วงราคา 52 สัปดาห์:
- สูงสุด: {ticker_data.get('fifty_two_week_high', 'N/A')}
- ต่ำสุด: {ticker_data.get('fifty_two_week_low', 'N/A')}

การเติบโต:
- Revenue Growth: {self._format_percent(ticker_data.get('revenue_growth'))}
- Earnings Growth: {self._format_percent(ticker_data.get('earnings_growth'))}
- Profit Margin: {self._format_percent(ticker_data.get('profit_margin'))}
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
