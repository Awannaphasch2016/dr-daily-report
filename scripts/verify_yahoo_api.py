"""
Test Yahoo Finance API calls directly
This helps debug why yfinance fails in Lambda
"""
import requests
import json
import yfinance as yf

def test_yahoo_api_direct(ticker):
    """Test direct Yahoo Finance API call"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"interval": "1d", "range": "1y"}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return {
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'data_points': 0,
            'error': None if response.status_code == 200 else response.text[:200]
        }
    except Exception as e:
        return {
            'status_code': None,
            'success': False,
            'data_points': 0,
            'error': str(e)
        }

def test_yfinance(ticker):
    """Test yfinance library"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        return {
            'success': not hist.empty,
            'data_points': len(hist),
            'latest_close': float(hist['Close'].iloc[-1]) if not hist.empty else None,
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'data_points': 0,
            'latest_close': None,
            'error': str(e)
        }

if __name__ == "__main__":
    ticker = "D05.SI"
    print(f"Testing {ticker}")
    print("\n1. Direct API call:")
    direct_result = test_yahoo_api_direct(ticker)
    print(json.dumps(direct_result, indent=2))
    
    print("\n2. yfinance call:")
    yf_result = test_yfinance(ticker)
    print(json.dumps(yf_result, indent=2))
