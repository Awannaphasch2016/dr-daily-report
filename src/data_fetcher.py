import yfinance as yf
import pandas as pd
import os
import logging
import requests
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        pass

    def fetch_via_direct_api(self, ticker, period="1y"):
        """Fetch historical data directly from Yahoo Finance API (fallback when yfinance fails)"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        
        # Map period to range
        period_map = {"1y": "1y", "6mo": "6mo", "3mo": "3mo", "1mo": "1mo", "5d": "5d", "1d": "1d"}
        range_param = period_map.get(period, "1y")
        params = {"interval": "1d", "range": range_param}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            logger.info(f"🌐 Fetching via direct Yahoo API for {ticker}")
            print(f"🌐 Fetching via direct Yahoo API for {ticker}")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                chart = data.get('chart', {})
                result = chart.get('result', [])
                
                if result and len(result) > 0:
                    timestamps = result[0].get('timestamp', [])
                    quote = result[0].get('indicators', {}).get('quote', [{}])[0]
                    opens = quote.get('open', [])
                    highs = quote.get('high', [])
                    lows = quote.get('low', [])
                    closes = quote.get('close', [])
                    volumes = quote.get('volume', [])
                    
                    # Convert to DataFrame
                    df_data = []
                    for i, ts in enumerate(timestamps):
                        if closes[i] is not None:  # Only include rows with valid close price
                            df_data.append({
                                'Open': opens[i] if i < len(opens) and opens[i] is not None else closes[i],
                                'High': highs[i] if i < len(highs) and highs[i] is not None else closes[i],
                                'Low': lows[i] if i < len(lows) and lows[i] is not None else closes[i],
                                'Close': closes[i],
                                'Volume': volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                            })
                    
                    if df_data:
                        hist = pd.DataFrame(df_data)
                        hist.index = pd.to_datetime([datetime.fromtimestamp(ts) for ts in timestamps[:len(df_data)]])
                        logger.info(f"   ✅ Direct API fetched {len(hist)} rows")
                        print(f"   ✅ Direct API fetched {len(hist)} rows")
                        return hist
                    
            logger.warning(f"   ⚠️  Direct API returned {response.status_code} or no data")
            print(f"   ⚠️  Direct API returned {response.status_code} or no data")
            return None
        except Exception as e:
            logger.error(f"   ❌ Direct API error: {e}")
            print(f"   ❌ Direct API error: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None

    def test_yahoo_api_direct(self, ticker):
        """Test direct Yahoo Finance API call for debugging"""
        hist = self.fetch_via_direct_api(ticker)
        if hist is not None and not hist.empty:
            return True, len(hist)
        return False, 0

    def fetch_ticker_data(self, ticker, period="1y"):
        """Fetch ticker data from Yahoo Finance"""
        try:
            logger.info(f"🔍 Fetching data for {ticker} (period={period})")
            print(f"🔍 Fetching data for {ticker} (period={period})")
            stock = yf.Ticker(ticker)

            # Step 1: Get historical data first (this usually works)
            logger.info(f"📊 Fetching historical data for {ticker}...")
            print(f"📊 Fetching historical data for {ticker}...")
            
            # Debug: Test direct API first
            api_works, api_count = self.test_yahoo_api_direct(ticker)
            if not api_works:
                logger.warning(f"⚠️  Direct API test failed for {ticker}, but continuing with yfinance...")
                print(f"⚠️  Direct API test failed for {ticker}, but continuing with yfinance...")
            
            # Try with retry logic
            hist = None
            yfinance_failed = False
            for attempt in range(3):
                try:
                    hist = stock.history(period=period)
                    if not hist.empty:
                        break
                    # If empty, mark as failed and retry
                    yfinance_failed = True
                    if attempt < 2:
                        logger.warning(f"⚠️  Attempt {attempt+1} returned empty data for {ticker}, retrying...")
                        print(f"⚠️  Attempt {attempt+1} returned empty data for {ticker}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        logger.warning(f"⚠️  yfinance returned empty data after 3 attempts, trying direct API fallback...")
                        print(f"⚠️  yfinance returned empty data after 3 attempts, trying direct API fallback...")
                        hist = None  # Ensure hist is None for fallback check
                        break
                except Exception as hist_error:
                    yfinance_failed = True
                    hist = None  # Ensure hist is None on exception
                    if attempt < 2:
                        logger.warning(f"⚠️  Attempt {attempt+1} failed for {ticker}: {hist_error}, retrying...")
                        print(f"⚠️  Attempt {attempt+1} failed for {ticker}: {hist_error}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        logger.warning(f"⚠️  yfinance failed after 3 attempts, trying direct API fallback...")
                        print(f"⚠️  yfinance failed after 3 attempts, trying direct API fallback...")
                        break

            # Fallback to direct API if yfinance failed or returned empty
            if (hist is None or hist.empty):
                if yfinance_failed:
                    logger.info(f"🔄 Falling back to direct API for {ticker}")
                    print(f"🔄 Falling back to direct API for {ticker}")
                    hist = self.fetch_via_direct_api(ticker, period)
                else:
                    # This shouldn't happen, but just in case
                    logger.warning(f"⚠️  yfinance didn't fail but returned no data, trying direct API...")
                    print(f"⚠️  yfinance didn't fail but returned no data, trying direct API...")
                    hist = self.fetch_via_direct_api(ticker, period)

            if hist is None or hist.empty:
                logger.warning(f"⚠️  No historical data found for {ticker}")
                print(f"⚠️  No historical data found for {ticker}")
                return None

            logger.info(f"✅ Got {len(hist)} days of historical data for {ticker}")
            print(f"✅ Got {len(hist)} days of historical data for {ticker}")
            
            # Get latest data
            latest = hist.iloc[-1]
            latest_date = hist.index[-1].date()
            logger.info(f"📅 Latest data date: {latest_date}, Close: {latest['Close']:.2f}")
            print(f"📅 Latest data date: {latest_date}, Close: {latest['Close']:.2f}")

            # Step 2: Get fundamental data (this often fails in Lambda)
            info = {}
            try:
                logger.info(f"📈 Fetching info data for {ticker}...")
                print(f"📈 Fetching info data for {ticker}...")
                info = stock.info
                logger.info(f"✅ Got info data for {ticker}: company={info.get('longName', 'N/A')}")
                print(f"✅ Got info data for {ticker}: company={info.get('longName', 'N/A')}")
            except Exception as info_error:
                # Info failure is non-fatal - we can still return historical data
                logger.warning(f"⚠️  Failed to get ticker info for {ticker}: {str(info_error)}")
                logger.warning(f"   Error type: {type(info_error).__name__}")
                print(f"⚠️  Failed to get ticker info for {ticker}: {str(info_error)}")
                print(f"   Error type: {type(info_error).__name__}")
                # Continue with empty info dict - historical data is more important

            data = {
                'date': latest_date,
                'open': latest['Open'],
                'high': latest['High'],
                'low': latest['Low'],
                'close': latest['Close'],
                'volume': latest['Volume'],
                'market_cap': info.get('marketCap') if info else None,
                'pe_ratio': info.get('trailingPE') if info else None,
                'eps': info.get('trailingEps') if info else None,
                'dividend_yield': info.get('dividendYield') if info else None,
                'sector': info.get('sector') if info else None,
                'industry': info.get('industry') if info else None,
                'company_name': info.get('longName', ticker) if info else ticker,
                'history': hist
            }

            logger.info(f"✅ Successfully fetched data for {ticker}")
            print(f"✅ Successfully fetched data for {ticker}")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching data for {ticker}: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            print(f"❌ Error fetching data for {ticker}: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            print(f"   Traceback: {traceback.format_exc()}")
            return None

    def fetch_historical_data(self, ticker, days=365):
        """Fetch historical data for technical analysis"""
        try:
            logger.info(f"🔍 Fetching {days} days of historical data for {ticker}")
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                logger.warning(f"⚠️  No historical data found for {ticker}")
                return None
                
            logger.info(f"✅ Got {len(hist)} days of historical data for {ticker}")
            return hist
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {ticker}: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    def get_ticker_info(self, ticker):
        """Get comprehensive ticker information"""
        try:
            logger.info(f"🔍 Fetching ticker info for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info

            logger.info(f"✅ Got ticker info for {ticker}: company={info.get('longName', 'N/A')}")
            return {
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'profit_margin': info.get('profitMargins'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'target_mean_price': info.get('targetMeanPrice'),
                'recommendation': info.get('recommendationKey'),
                'analyst_count': info.get('numberOfAnalystOpinions'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'current_price': info.get('currentPrice'),
                'beta': info.get('beta')
            }
        except Exception as e:
            logger.warning(f"⚠️  Error getting ticker info for {ticker}: {str(e)}")
            logger.warning(f"   Error type: {type(e).__name__}")
            return {}

    def load_tickers(self, csv_path='data/tickers.csv'):
        """Load supported tickers from CSV"""
        try:
            # Try Lambda path first (root level), then fallback to data/ path
            if os.path.exists('tickers.csv'):
                csv_path = 'tickers.csv'
            elif not os.path.exists(csv_path):
                # Try data/tickers.csv as fallback
                csv_path = 'data/tickers.csv'
            
            df = pd.read_csv(csv_path)
            ticker_map = dict(zip(df['Symbol'], df['Ticker']))
            logger.info(f"✅ Loaded {len(ticker_map)} tickers from {csv_path}")
            return ticker_map
        except Exception as e:
            logger.error(f"❌ Error loading tickers: {str(e)}")
            return {}
