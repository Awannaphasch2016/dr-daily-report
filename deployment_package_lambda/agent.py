from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import operator
from datetime import datetime
from data_fetcher import DataFetcher
from technical_analysis import TechnicalAnalyzer
from database import TickerDatabase

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
        prompt = f"""You are a world-class financial analyst like Aswath Damodaran. Write in Thai, but think like him - tell stories with data, don't just list numbers.

Data:
{context}

Write a narrative-driven report that answers: "Should I BUY MORE?", "Should I SELL?", or "Should I HOLD LONGER?" and WHY?

Structure (in Thai):

📖 **เรื่องราวของหุ้นตัวนี้**
Write 2-3 sentences telling the STORY of what's happening with this stock. Examples:
- "Tesla กำลังติดกับดัก - ราคาทะยานเพราะความฝัน แต่กำไรกำลังหดตัว 37% ทำให้ P/E พุ่งสูงถึง 322 เท่า นี่คือสัญญาณที่ต้องระวัง"
- "Honda กำลังอยู่ในภาวะที่น่าสนใจ - ราคาเพิ่งทะลุแนว SMA 200 ขึ้นมา (1,583 vs 1,341) แสดงว่ามีแรงซื้อกลับมา แต่กำไรลด 42% ทำให้ต้องระมัดระวัง"

💡 **สิ่งที่คุณต้องรู้**
Write 3-4 key insights as STORIES with numbers as evidence:

Example for uptrend:
"ราคากำลังขึ้นแรง - ทะลุเส้น SMA 20, 50 และ 200 ไปหมดแล้ว ($461 vs $439 vs $405 vs $336) แสดงว่านักลงทุนกำลังเชื่อมั่น เหมาะกับคนที่ถืออยู่แล้วให้ถือต่อ"

Example for valuation concern:
"แต่ตลาดกำลังจ่ายแพงมาก - P/E อยู่ที่ 322 เทียบกับค่าเฉลี่ยอุตสาหกรรมที่ 15-20 นั่นหมายความว่าถ้ากำไรโตไม่ได้ตามคาด ราคาจะปรับลงแรง"

Example for earnings problem:
"มีปัญหาใหญ่ที่กำไร - รายได้โต 11% แต่กำไรลด 37% นั่นบอกว่าต้นทุนพุ่งสูงกว่ารายได้ที่เข้ามา ซึ่งไม่ใช่สัญญาณดีเลย"

🎯 **ควรทำอะไรตอนนี้?**
Tell them clearly: BUY MORE / SELL / HOLD LONGER and give 2-3 reasons

Example:
"แนะนำ HOLD - อย่ารีบขายเพราะราคายังขึ้น แต่อย่าซื้อเพิ่มเพราะราคาแพงเกินไป ($461 vs target $395) รอให้กำไรกลับมาดีขึ้นก่อน"

⚠️ **ระวังอะไร?**
Tell them what to watch out for and WHY it matters

Example:
"ระวังถ้ากำไรไตรมาสหน้ายังลดต่อ - ราคาอาจปรับลงแรงเพราะตอนนี้ตลาดจ่ายแพงมากบนความหวัง ถ้าความหวังแตก เงินจะออกไว"

Rules:
- Tell STORIES, don't list bullet points
- Use numbers IN sentences as evidence
- Explain WHY things matter, not just WHAT they are
- Write like you're texting a friend investor advice
- Keep it under 12 lines total
- NO tables, NO bullet point lists, just flowing narrative

BAD: "RSI = 59.04"
GOOD: "RSI อยู่ที่ 59 ยังไม่ถึงโซนซื้อมากเกินไป (70) แสดงว่ายังมีที่ว่างให้ราคาขึ้นได้อีก"

BAD: "P/E = 322"
GOOD: "P/E สูงลิ่ว 322 เท่า แปลว่าต้องโตอีกหลายปีถึงจะคุ้มค่า ความเสี่ยงสูงมาก"

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

แนวโน้ม: {self.technical_analyzer.analyze_trend(indicators, current_price)}
โมเมนตัม: {self.technical_analyzer.analyze_momentum(indicators)}
MACD Signal: {self.technical_analyzer.analyze_macd(indicators)}
Bollinger: {self.technical_analyzer.analyze_bollinger(indicators)}

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
