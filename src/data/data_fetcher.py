import yfinance as yf
import pandas as pd
import os
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class DataFetcher:
    """Fetches ticker data from Yahoo Finance API.
    
    All methods are symbol-type invariant - they accept any symbol format
    (DR symbols like 'DBS19', Yahoo symbols like 'D05.SI', etc.) and
    automatically resolve to Yahoo Finance format before making API calls.
    """
    
    def __init__(self):
        pass
    
    def _resolve_to_yahoo_symbol(self, symbol: str) -> str:
        """Resolve any symbol format to Yahoo Finance symbol.
        
        This method ensures symbol-type invariance - all Yahoo Finance API
        calls use resolved symbols, preventing "No price data" errors.
        
        Args:
            symbol: Ticker symbol in any format (DR, Yahoo, etc.)
            
        Returns:
            Yahoo Finance symbol (e.g., 'D05.SI' for 'DBS19')
            
        Raises:
            ValueError: If symbol cannot be resolved and is not already a valid Yahoo symbol
            
        Example:
            >>> fetcher = DataFetcher()
            >>> fetcher._resolve_to_yahoo_symbol('DBS19')
            'D05.SI'
            >>> fetcher._resolve_to_yahoo_symbol('NVDA')
            'NVDA'
        """
        try:
            from src.data.aurora.ticker_resolver import get_ticker_resolver
            
            resolver = get_ticker_resolver()
            ticker_info = resolver.resolve(symbol)
            
            if ticker_info and ticker_info.yahoo_symbol:
                yahoo_symbol = ticker_info.yahoo_symbol
                if yahoo_symbol != symbol:
                    logger.debug(f"Resolved symbol {symbol} -> {yahoo_symbol}")
                return yahoo_symbol
            else:
                # Fallback: assume it's already a Yahoo symbol
                logger.debug(f"Symbol {symbol} not resolved, using as-is (assuming Yahoo format)")
                return symbol
                
        except Exception as e:
            # If resolver fails, log warning but don't fail - might be a new ticker
            logger.warning(f"Symbol resolution failed for {symbol}: {e}, using as-is")
            return symbol

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
                        # Add Date column for reference but keep integer index to avoid Timestamp serialization issues
                        hist['Date'] = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps[:len(df_data)]]
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
        """Fetch ticker data from Yahoo Finance.
        
        Symbol-type invariant: Accepts any symbol format (DR, Yahoo, etc.)
        and automatically resolves to Yahoo Finance format before API calls.
        
        Args:
            ticker: Ticker symbol in any format (e.g., 'DBS19' or 'D05.SI')
            period: Data period (default: '1y')
            
        Returns:
            Dict with ticker data including history, fundamentals, etc.
            
        Raises:
            ValueError: If no historical data is returned
        """
        # Resolve symbol to Yahoo Finance format (symbol-type invariant)
        yahoo_ticker = self._resolve_to_yahoo_symbol(ticker)
        
        try:
            logger.info(f"🔍 Fetching data for {ticker} -> {yahoo_ticker} (period={period})")
            print(f"🔍 Fetching data for {ticker} -> {yahoo_ticker} (period={period})")
            stock = yf.Ticker(yahoo_ticker)

            # Step 1: Get historical data first (this usually works)
            logger.info(f"📊 Fetching historical data for {yahoo_ticker}...")
            print(f"📊 Fetching historical data for {yahoo_ticker}...")
            
            # Debug: Test direct API first (use resolved Yahoo symbol)
            api_works, api_count = self.test_yahoo_api_direct(yahoo_ticker)
            if not api_works:
                logger.warning(f"⚠️  Direct API test failed for {yahoo_ticker}, but continuing with yfinance...")
                print(f"⚠️  Direct API test failed for {yahoo_ticker}, but continuing with yfinance...")
            
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
                        logger.warning(f"⚠️  Attempt {attempt+1} returned empty data for {yahoo_ticker}, retrying...")
                        print(f"⚠️  Attempt {attempt+1} returned empty data for {yahoo_ticker}, retrying...")
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
                        logger.warning(f"⚠️  Attempt {attempt+1} failed for {yahoo_ticker}: {hist_error}, retrying...")
                        print(f"⚠️  Attempt {attempt+1} failed for {yahoo_ticker}: {hist_error}, retrying...")
                        time.sleep(2)
                        continue
                    else:
                        logger.warning(f"⚠️  yfinance failed after 3 attempts, trying direct API fallback...")
                        print(f"⚠️  yfinance failed after 3 attempts, trying direct API fallback...")
                        break

            # Fallback to direct API if yfinance failed or returned empty (use resolved Yahoo symbol)
            if (hist is None or hist.empty):
                if yfinance_failed:
                    logger.info(f"🔄 Falling back to direct API for {yahoo_ticker}")
                    print(f"🔄 Falling back to direct API for {yahoo_ticker}")
                    hist = self.fetch_via_direct_api(yahoo_ticker, period)
                else:
                    # This shouldn't happen, but just in case
                    logger.warning(f"⚠️  yfinance didn't fail but returned no data, trying direct API...")
                    print(f"⚠️  yfinance didn't fail but returned no data, trying direct API...")
                    hist = self.fetch_via_direct_api(yahoo_ticker, period)

            if hist is None or hist.empty:
                error_msg = f"No historical data returned for {ticker} (resolved to {yahoo_ticker}, period={period})"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"✅ Got {len(hist)} days of historical data for {yahoo_ticker}")
            print(f"✅ Got {len(hist)} days of historical data for {yahoo_ticker}")

            # Get latest data BEFORE converting index
            latest = hist.iloc[-1]
            latest_date = hist.index[-1].date() if hasattr(hist.index[-1], 'date') else hist.index[-1]
            logger.info(f"📅 Latest data date: {latest_date}, Close: {latest['Close']:.2f}")
            print(f"📅 Latest data date: {latest_date}, Close: {latest['Close']:.2f}")

            # Convert DatetimeIndex to integer index with Date column to avoid Timestamp serialization issues
            if isinstance(hist.index, pd.DatetimeIndex):
                hist = hist.reset_index()
                hist.rename(columns={'index': 'Date'}, inplace=True)
                # Convert Date column to strings
                hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')

            # Step 2: Get fundamental data (this often fails in Lambda)
            # First, try to get company name from chart API meta (more reliable)
            # Initialize with Yahoo ticker as fallback
            company_name_from_meta = yahoo_ticker
            try:
                # Try to get meta from a quick chart API call (use resolved Yahoo symbol)
                chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
                chart_params = {"interval": "1d", "range": "1d"}
                chart_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                chart_response = requests.get(chart_url, params=chart_params, headers=chart_headers, timeout=5)
                if chart_response.status_code == 200:
                    chart_data = chart_response.json()
                    chart_result = chart_data.get('chart', {}).get('result', [])
                    if chart_result and len(chart_result) > 0:
                        meta = chart_result[0].get('meta', {})
                        company_name_from_meta = meta.get('longName', yahoo_ticker)
                        logger.info(f"   ✅ Got company name from chart API: {company_name_from_meta}")
                        print(f"   ✅ Got company name from chart API: {company_name_from_meta}")
            except Exception as meta_error:
                logger.debug(f"   Could not get company name from chart API: {meta_error}")
                # Keep default value (yahoo_ticker)
                pass
            
            info = {}
            info_fetch_success = False
            for info_attempt in range(3):
                try:
                    logger.info(f"📈 Fetching info data for {yahoo_ticker} (attempt {info_attempt + 1}/3)...")
                    print(f"📈 Fetching info data for {yahoo_ticker} (attempt {info_attempt + 1}/3)...")
                    info = stock.info
                    
                    # Validate that we got actual data (not empty dict)
                    if info and isinstance(info, dict) and len(info) > 0:
                        # Check if we have at least one key indicator
                        if 'longName' in info or 'marketCap' in info or 'trailingPE' in info:
                            logger.info(f"✅ Got info data for {yahoo_ticker}: company={info.get('longName', 'N/A')}, marketCap={info.get('marketCap', 'N/A')}, pe={info.get('trailingPE', 'N/A')}")
                            print(f"✅ Got info data for {yahoo_ticker}: company={info.get('longName', 'N/A')}, marketCap={info.get('marketCap', 'N/A')}, pe={info.get('trailingPE', 'N/A')}")
                            info_fetch_success = True
                            break
                        else:
                            logger.warning(f"⚠️  Info data appears empty or invalid (no key fields) for {yahoo_ticker}")
                            print(f"⚠️  Info data appears empty or invalid (no key fields) for {yahoo_ticker}")
                    else:
                        logger.warning(f"⚠️  Info data is empty dict for {yahoo_ticker}")
                        print(f"⚠️  Info data is empty dict for {yahoo_ticker}")
                    
                    # If we got here, info fetch didn't succeed, retry
                    if info_attempt < 2:
                        logger.info(f"   Retrying info fetch in 2 seconds...")
                        print(f"   Retrying info fetch in 2 seconds...")
                        time.sleep(2)
                        info = {}  # Reset for retry
                        
                except Exception as info_error:
                    # Info failure is non-fatal - we can still return historical data
                    error_type = type(info_error).__name__
                    error_msg = str(info_error)
                    
                    # Check if this is a known transient Yahoo Finance API error
                    is_transient_error = (
                        'JSONDecodeError' in error_type or 
                        'Expecting value' in error_msg or
                        'ConnectionError' in error_type or
                        'Timeout' in error_type
                    )
                    
                    if info_attempt < 2:
                        # Retry attempt - log more briefly for transient errors
                        if is_transient_error:
                            logger.info(f"⚠️  Yahoo Finance API transient error (attempt {info_attempt + 1}/3): {error_type} - will retry...")
                            print(f"⚠️  Yahoo Finance API transient error (attempt {info_attempt + 1}/3): {error_type} - will retry...")
                        else:
                            logger.warning(f"⚠️  Failed to get ticker info for {yahoo_ticker} (attempt {info_attempt + 1}/3): {error_msg}")
                            logger.warning(f"   Error type: {error_type}")
                            print(f"⚠️  Failed to get ticker info for {yahoo_ticker} (attempt {info_attempt + 1}/3): {error_msg}")
                            print(f"   Error type: {error_type}")
                        
                        logger.info(f"   Retrying info fetch in 2 seconds...")
                        print(f"   Retrying info fetch in 2 seconds...")
                        time.sleep(2)
                        info = {}  # Reset for retry
                    else:
                        # Final attempt failed - log full details
                        logger.warning(f"⚠️  All info fetch attempts failed for {yahoo_ticker}")
                        logger.warning(f"   Final error: {error_type}: {error_msg}")
                        print(f"⚠️  All info fetch attempts failed for {yahoo_ticker}")
                        print(f"   Final error: {error_type}: {error_msg}")
                        
                        # Only log full traceback for non-transient errors or if debugging is needed
                        if not is_transient_error:
                            import traceback
                            logger.debug(f"   Full traceback: {traceback.format_exc()}")
                        
                        logger.info(f"   Continuing without fundamental data (historical data still available)")
                        print(f"   Continuing without fundamental data (historical data still available)")
                        info = {}
            
            if not info_fetch_success:
                logger.warning(f"⚠️  Could not fetch fundamental data for {yahoo_ticker} after 3 attempts - continuing with historical data only")
                print(f"⚠️  Could not fetch fundamental data for {yahoo_ticker} after 3 attempts - continuing with historical data only")

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
                'company_name': info.get('longName', company_name_from_meta) if info else company_name_from_meta,
                'history': hist
            }
            
            # Log extracted fundamental values
            logger.info(f"📊 Extracted fundamental data for {yahoo_ticker}:")
            logger.info(f"   Market Cap: {data['market_cap']}")
            logger.info(f"   P/E Ratio: {data['pe_ratio']}")
            logger.info(f"   EPS: {data['eps']}")
            logger.info(f"   Dividend Yield: {data['dividend_yield']}")
            logger.info(f"   Sector: {data['sector']}")
            logger.info(f"   Industry: {data['industry']}")
            logger.info(f"   Company Name: {data['company_name']}")
            print(f"📊 Extracted fundamental data for {yahoo_ticker}:")
            print(f"   Market Cap: {data['market_cap']}")
            print(f"   P/E Ratio: {data['pe_ratio']}")
            print(f"   EPS: {data['eps']}")
            print(f"   Dividend Yield: {data['dividend_yield']}")
            print(f"   Sector: {data['sector']}")
            print(f"   Industry: {data['industry']}")
            print(f"   Company Name: {data['company_name']}")

            logger.info(f"✅ Successfully fetched data for {ticker} -> {yahoo_ticker}")
            print(f"✅ Successfully fetched data for {ticker} -> {yahoo_ticker}")
            return data
        except Exception as e:
            logger.error(f"❌ Error fetching data for {ticker} (resolved to {yahoo_ticker}): {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            print(f"❌ Error fetching data for {ticker} (resolved to {yahoo_ticker}): {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            print(f"   Traceback: {traceback.format_exc()}")
            raise  # Re-raise exception (fail fast, don't return None silently)

    def fetch_historical_data(self, ticker, days=365):
        """Fetch historical data for technical analysis.
        
        Symbol-type invariant: Accepts any symbol format and resolves to Yahoo Finance format.
        
        Args:
            ticker: Ticker symbol in any format
            days: Number of days of historical data (default: 365)
            
        Returns:
            DataFrame with historical OHLCV data, or None if fetch fails
            
        Raises:
            ValueError: If no historical data is returned
        """
        # Resolve symbol to Yahoo Finance format (symbol-type invariant)
        yahoo_ticker = self._resolve_to_yahoo_symbol(ticker)
        
        try:
            logger.info(f"🔍 Fetching {days} days of historical data for {ticker} -> {yahoo_ticker}")
            stock = yf.Ticker(yahoo_ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            hist = stock.history(start=start_date, end=end_date)

            if hist.empty:
                error_msg = f"No historical data found for {ticker} (resolved to {yahoo_ticker})"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Convert DatetimeIndex to integer index with Date column to avoid Timestamp serialization issues
            if isinstance(hist.index, pd.DatetimeIndex):
                hist = hist.reset_index()
                hist.rename(columns={'index': 'Date'}, inplace=True)
                # Convert Date column to strings
                hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')

            logger.info(f"✅ Got {len(hist)} days of historical data for {yahoo_ticker}")
            return hist
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {ticker} (resolved to {yahoo_ticker}): {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            raise  # Re-raise exception (fail fast, don't return None silently)

    def get_ticker_info(self, ticker):
        """Get comprehensive ticker information.
        
        Symbol-type invariant: Accepts any symbol format and resolves to Yahoo Finance format.
        
        Args:
            ticker: Ticker symbol in any format
            
        Returns:
            Dict with ticker information, or empty dict if fetch fails
        """
        # Resolve symbol to Yahoo Finance format (symbol-type invariant)
        yahoo_ticker = self._resolve_to_yahoo_symbol(ticker)
        
        try:
            logger.info(f"🔍 Fetching ticker info for {ticker} -> {yahoo_ticker}")
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            logger.info(f"✅ Got ticker info for {yahoo_ticker}: company={info.get('longName', 'N/A')}")
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
            logger.warning(f"⚠️  Error getting ticker info for {ticker} (resolved to {yahoo_ticker}): {str(e)}")
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
