#!/usr/bin/env python3
"""Test Yahoo Finance API directly for DBS19 (D05.SI) fundamental data"""

import yfinance as yf
import requests
import json

def test_yfinance_info(ticker):
    """Test yfinance stock.info for fundamental data"""
    print(f"\n{'='*80}")
    print(f"Testing yfinance stock.info for {ticker}")
    print(f"{'='*80}")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        print(f"\n✅ Successfully fetched info for {ticker}")
        print(f"\n📊 Fundamental Data:")
        print(f"   Company Name: {info.get('longName', 'N/A')}")
        print(f"   Short Name: {info.get('shortName', 'N/A')}")
        print(f"   Market Cap: {info.get('marketCap', 'N/A')}")
        print(f"   P/E Ratio (Trailing): {info.get('trailingPE', 'N/A')}")
        print(f"   P/E Ratio (Forward): {info.get('forwardPE', 'N/A')}")
        print(f"   EPS (Trailing): {info.get('trailingEps', 'N/A')}")
        print(f"   EPS (Forward): {info.get('forwardEps', 'N/A')}")
        print(f"   Dividend Yield: {info.get('dividendYield', 'N/A')}")
        print(f"   Sector: {info.get('sector', 'N/A')}")
        print(f"   Industry: {info.get('industry', 'N/A')}")
        print(f"   Revenue Growth: {info.get('revenueGrowth', 'N/A')}")
        print(f"   Earnings Growth: {info.get('earningsGrowth', 'N/A')}")
        print(f"   Profit Margin: {info.get('profitMargins', 'N/A')}")
        
        # Show all keys available
        print(f"\n📋 All available keys in info ({len(info)} keys):")
        for key in sorted(info.keys()):
            value = info.get(key)
            if value is not None and value != '':
                print(f"   - {key}: {value}")
        
        return info
    except Exception as e:
        print(f"\n❌ Error fetching info: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None

def test_direct_yahoo_api(ticker):
    """Test direct Yahoo Finance API call for fundamental data"""
    print(f"\n{'='*80}")
    print(f"Testing direct Yahoo Finance API for {ticker}")
    print(f"{'='*80}")
    
    # Yahoo Finance quote endpoint
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    
    modules = [
        "summaryProfile",
        "summaryDetail",
        "assetProfile",
        "financialData",
        "defaultKeyStatistics",
        "calendarEvents",
        "secFilings",
        "upgradeDowngradeHistory",
        "institutionOwnership",
        "fundOwnership",
        "majorDirectHolders",
        "majorHolders",
        "insiderTransactions",
        "insiderHolders",
        "netSharePurchaseActivity",
        "earnings",
        "earningsHistory",
        "earningsTrend",
        "industryTrend",
        "indexTrend",
        "sectorTrend"
    ]
    
    params = {
        "modules": ",".join(modules),
        "region": "US",
        "lang": "en-US"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        print(f"\n🌐 Calling: {url}")
        print(f"   Modules: {len(modules)} modules")
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('quoteSummary', {}).get('result', [])
            
            if result and len(result) > 0:
                quote_data = result[0]
                
                print(f"\n✅ Successfully fetched quote summary")
                print(f"\n📊 Available Modules:")
                for module in quote_data.keys():
                    print(f"   - {module}")
                
                # Extract key fundamental data
                print(f"\n📈 Fundamental Data from Direct API:")
                
                # Summary Profile
                summary_profile = quote_data.get('summaryProfile', {})
                if summary_profile:
                    print(f"\n   Summary Profile:")
                    print(f"      Company Name: {summary_profile.get('longName', 'N/A')}")
                    print(f"      Sector: {summary_profile.get('sector', 'N/A')}")
                    print(f"      Industry: {summary_profile.get('industry', 'N/A')}")
                    print(f"      Full Time Employees: {summary_profile.get('fullTimeEmployees', 'N/A')}")
                    print(f"      Website: {summary_profile.get('website', 'N/A')}")
                
                # Summary Detail
                summary_detail = quote_data.get('summaryDetail', {})
                if summary_detail:
                    print(f"\n   Summary Detail:")
                    print(f"      Market Cap: {summary_detail.get('marketCap', {}).get('raw', 'N/A')}")
                    print(f"      P/E Ratio (Trailing): {summary_detail.get('trailingPE', {}).get('raw', 'N/A')}")
                    print(f"      P/E Ratio (Forward): {summary_detail.get('forwardPE', {}).get('raw', 'N/A')}")
                    print(f"      EPS (Trailing): {summary_detail.get('trailingEps', {}).get('raw', 'N/A')}")
                    print(f"      Dividend Yield: {summary_detail.get('dividendYield', {}).get('raw', 'N/A')}")
                    print(f"      Beta: {summary_detail.get('beta', {}).get('raw', 'N/A')}")
                
                # Financial Data
                financial_data = quote_data.get('financialData', {})
                if financial_data:
                    print(f"\n   Financial Data:")
                    print(f"      Total Revenue: {financial_data.get('totalRevenue', {}).get('raw', 'N/A')}")
                    print(f"      Revenue Per Share: {financial_data.get('revenuePerShare', {}).get('raw', 'N/A')}")
                    print(f"      Profit Margin: {financial_data.get('profitMargins', {}).get('raw', 'N/A')}")
                    print(f"      Operating Margin: {financial_data.get('operatingMargins', {}).get('raw', 'N/A')}")
                    print(f"      Return on Assets: {financial_data.get('returnOnAssets', {}).get('raw', 'N/A')}")
                    print(f"      Return on Equity: {financial_data.get('returnOnEquity', {}).get('raw', 'N/A')}")
                
                # Default Key Statistics
                default_key_stats = quote_data.get('defaultKeyStatistics', {})
                if default_key_stats:
                    print(f"\n   Key Statistics:")
                    print(f"      Market Cap: {default_key_stats.get('marketCap', {}).get('raw', 'N/A')}")
                    print(f"      Enterprise Value: {default_key_stats.get('enterpriseValue', {}).get('raw', 'N/A')}")
                    print(f"      P/E Ratio: {default_key_stats.get('trailingPE', {}).get('raw', 'N/A')}")
                    print(f"      Forward P/E: {default_key_stats.get('forwardPE', {}).get('raw', 'N/A')}")
                    print(f"      PEG Ratio: {default_key_stats.get('pegRatio', {}).get('raw', 'N/A')}")
                    print(f"      Price to Book: {default_key_stats.get('priceToBook', {}).get('raw', 'N/A')}")
                
                return quote_data
            else:
                print(f"\n⚠️  No result data in response")
                print(f"   Response: {json.dumps(data, indent=2)[:500]}")
                return None
        else:
            print(f"\n❌ API returned status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error calling direct API: {e}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None

if __name__ == "__main__":
    ticker = "D05.SI"  # DBS19 maps to D05.SI
    
    print(f"\n🔍 Testing Fundamental Data Fetching for {ticker} (DBS19)")
    print(f"{'='*80}")
    
    # Test 1: yfinance stock.info
    yfinance_info = test_yfinance_info(ticker)
    
    # Test 2: Direct Yahoo Finance API
    direct_api_data = test_direct_yahoo_api(ticker)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"yfinance stock.info: {'✅ Success' if yfinance_info else '❌ Failed'}")
    print(f"Direct Yahoo API: {'✅ Success' if direct_api_data else '❌ Failed'}")
    
    if yfinance_info:
        print(f"\n📊 Key Fundamental Values from yfinance:")
        print(f"   Market Cap: {yfinance_info.get('marketCap', 'N/A')}")
        print(f"   P/E Ratio: {yfinance_info.get('trailingPE', 'N/A')}")
        print(f"   EPS: {yfinance_info.get('trailingEps', 'N/A')}")
        print(f"   Sector: {yfinance_info.get('sector', 'N/A')}")
        print(f"   Industry: {yfinance_info.get('industry', 'N/A')}")
