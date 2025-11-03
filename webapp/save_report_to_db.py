#!/usr/bin/env python3
"""
Helper script to save agent reports to the Flask webapp database
Usage: python webapp/save_report_to_db.py <ticker>
"""

import os
import sys
import json
from datetime import date
import requests

# Add parent directory to path to import agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import TickerAnalysisAgent


def save_report_to_db(ticker: str, api_url: str = "http://localhost:5000"):
    """Generate report and save to database via API"""
    print(f"Generating report for {ticker}...")
    print("=" * 80)
    
    # Initialize agent
    agent = TickerAnalysisAgent()
    
    # Generate report
    state = {'ticker': ticker, 'error': None}
    result = agent.graph.invoke(state)
    
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
        return False
    
    if not result.get('report'):
        print("❌ No report generated")
        return False
    
    # Prepare report data
    report_data = {
        'ticker': ticker.upper(),
        'report_date': str(date.today()),
        'report_text': result['report'],
        'chart_base64': result.get('chart_base64', ''),
        'audio_base64': result.get('audio_base64', ''),
        'audio_english_base64': result.get('audio_english_base64', ''),
        'indicators': result.get('indicators', {}),
        'percentiles': result.get('percentiles', {}),
        'news': result.get('news', []),
        'recommendation': result.get('recommendation', 'HOLD')
    }
    
    # Extract recommendation from report text
    report_upper = result['report'].upper()
    if 'แนะนำ BUY' in result['report'] or 'BUY' in report_upper:
        report_data['recommendation'] = 'BUY'
    elif 'แนะนำ SELL' in result['report'] or 'SELL' in report_upper:
        report_data['recommendation'] = 'SELL'
    else:
        report_data['recommendation'] = 'HOLD'
    
    # Save to database via API
    try:
        response = requests.post(
            f"{api_url}/api/save_report",
            json=report_data,
            timeout=60
        )
        response.raise_for_status()
        
        result_data = response.json()
        print(f"✅ Report saved successfully! ID: {result_data.get('id')}")
        print(f"   View at: {api_url}/report/{ticker.upper()}/{report_data['report_date']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to save to database: {str(e)}")
        print("   Make sure Flask app is running: python webapp/app.py")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python webapp/save_report_to_db.py <ticker> [api_url]")
        print("Example: python webapp/save_report_to_db.py DBS19")
        sys.exit(1)
    
    ticker = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"
    
    success = save_report_to_db(ticker, api_url)
    sys.exit(0 if success else 1)
