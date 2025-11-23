#!/usr/bin/env python3
"""
Direct test script that bypasses ticker mapping for testing any ticker
"""

import sys
import os
from src.data.data_fetcher import DataFetcher
from src.analysis.technical_analysis import TechnicalAnalyzer
from src.data.database import TickerDatabase
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def test_ticker_direct(ticker_symbol):
    """Test any ticker directly without ticker mapping"""
    print("=" * 80)
    print(f"Testing Ticker: {ticker_symbol}")
    print("=" * 80)
    print()

    # Initialize components
    print("🔧 Initializing components...")
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.7,
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )

    # Fetch data
    print(f"📊 Fetching data for {ticker_symbol}...")
    data = fetcher.fetch_ticker_data(ticker_symbol)

    if not data:
        print(f"❌ Failed to fetch data for {ticker_symbol}")
        return

    print(f"✅ Data fetched successfully!")
    print(f"   Company: {data.get('company_name', 'N/A')}")
    print(f"   Price: ${data['close']:.2f}")
    print(f"   Sector: {data.get('sector', 'N/A')}")
    print()

    # Get additional info
    print("📈 Fetching additional information...")
    info = fetcher.get_ticker_info(ticker_symbol)
    data.update(info)

    # Calculate indicators
    print("🔍 Calculating technical indicators...")
    hist_data = data.get('history')
    indicators = analyzer.calculate_all_indicators(hist_data)

    if not indicators:
        print("❌ Failed to calculate indicators")
        return

    print("✅ Indicators calculated successfully!")
    print(f"   SMA 20: ${indicators['sma_20']:.2f}")
    print(f"   RSI: {indicators['rsi']:.2f}")
    print(f"   MACD: {indicators['macd']:.2f}")
    print()

    # Prepare context
    print("🤖 Generating AI report...")
    current_price = indicators.get('current_price', 0)

    context = f"""
สัญลักษณ์: {ticker_symbol}
บริษัท: {data.get('company_name', ticker_symbol)}
ราคาปัจจุบัน: ${current_price:.2f}
วันที่: {data.get('date')}

ข้อมูลพื้นฐาน:
- Market Cap: {format_number(data.get('market_cap'))}
- P/E Ratio: {data.get('pe_ratio', 'N/A')}
- Forward P/E: {data.get('forward_pe', 'N/A')}
- EPS: {data.get('eps', 'N/A')}
- Dividend Yield: {format_percent(data.get('dividend_yield'))}
- Sector: {data.get('sector', 'N/A')}
- Industry: {data.get('industry', 'N/A')}

การวิเคราะห์ทางเทคนิค:
- SMA 20: ${indicators.get('sma_20', 0):.2f}
- SMA 50: ${indicators.get('sma_50', 0):.2f}
- SMA 200: ${indicators.get('sma_200', 0):.2f}
- RSI: {indicators.get('rsi', 0):.2f}
- MACD: {indicators.get('macd', 0):.2f}
- Signal: {indicators.get('macd_signal', 0):.2f}
- Bollinger Upper: ${indicators.get('bb_upper', 0):.2f}
- Bollinger Middle: ${indicators.get('bb_middle', 0):.2f}
- Bollinger Lower: ${indicators.get('bb_lower', 0):.2f}

แนวโน้ม: {analyzer.analyze_trend(indicators, current_price)}
โมเมนตัม: {analyzer.analyze_momentum(indicators)}
MACD Signal: {analyzer.analyze_macd(indicators)}
Bollinger: {analyzer.analyze_bollinger(indicators)}

ความเห็นนักวิเคราะห์:
- คำแนะนำ: {data.get('recommendation', 'N/A').upper() if data.get('recommendation') else 'N/A'}
- ราคาเป้าหมายเฉลี่ย: ${data.get('target_mean_price', 'N/A')}
- จำนวนนักวิเคราะห์: {data.get('analyst_count', 'N/A')}

ช่วงราคา 52 สัปดาห์:
- สูงสุด: ${data.get('fifty_two_week_high', 0):.2f}
- ต่ำสุด: ${data.get('fifty_two_week_low', 0):.2f}

การเติบโต:
- Revenue Growth: {format_percent(data.get('revenue_growth'))}
- Earnings Growth: {format_percent(data.get('earnings_growth'))}
- Profit Margin: {format_percent(data.get('profit_margin'))}
"""

    # Generate report
    prompt = f"""คุณเป็นนักวิเคราะห์การเงินที่เชี่ยวชาญในการวิเคราะห์หุ้น สร้างรายงานวิเคราะห์หุ้นในภาษาไทยที่ครอบคลุมและเข้าใจง่าย

ข้อมูลหุ้น:
{context}

สร้างรายงานที่ประกอบด้วย:

📊 **ภาพรวม**
- ชื่อบริษัทและสัญลักษณ์
- ราคาปัจจุบัน และการเปลี่ยนแปลง
- ข้อมูลพื้นฐาน (Market Cap, P/E, EPS)

📈 **การวิเคราะห์ทางเทคนิค**
- แนวโน้มราคา (Trend Analysis)
- ตัวชี้วัดโมเมนตัม (RSI, MACD)
- Bollinger Bands และความผันผวน
- ปริมาณการซื้อขาย

💼 **การวิเคราะห์พื้นฐาน**
- อัตราส่วนการเงิน
- การเติบโตของรายได้และกำไร
- เงินปันผล
- การประเมินมูลค่า

🎯 **ความเห็นนักวิเคราะห์**
- คำแนะนำจากนักวิเคราะห์
- ราคาเป้าหมาย
- จำนวนนักวิเคราะห์

📌 **สรุปและข้อเสนอแนะ**
- Key Insights สำคัญ
- โอกาสและความเสี่ยง
- ข้อควรระวัง

ใช้ภาษาไทยที่เข้าใจง่าย มีข้อมูลครบถ้วน และเป็นประโยชน์สำหรับนักลงทุน ใช้ emoji เพื่อให้อ่านง่าย"""

    response = llm.invoke([HumanMessage(content=prompt)])
    report = response.content

    print("=" * 80)
    print("REPORT OUTPUT:")
    print("=" * 80)
    print()
    print(report)
    print()
    print("=" * 80)
    print("✅ Test complete!")
    print("=" * 80)

def format_number(value):
    """Format large numbers"""
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    elif value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    else:
        return f"${value:,.0f}"

def format_percent(value):
    """Format percentage"""
    if value is None:
        return "N/A"
    return f"{value*100:.2f}%"

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    test_ticker_direct(ticker)
