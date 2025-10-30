import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

class DataFetcher:
    def __init__(self):
        pass

    def fetch_ticker_data(self, ticker, period="1y"):
        """Fetch ticker data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)

            # Get historical data
            hist = stock.history(period=period)

            if hist.empty:
                return None

            # Get latest data
            latest = hist.iloc[-1]
            latest_date = hist.index[-1].date()

            # Get fundamental data
            info = stock.info

            data = {
                'date': latest_date,
                'open': latest['Open'],
                'high': latest['High'],
                'low': latest['Low'],
                'close': latest['Close'],
                'volume': latest['Volume'],
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'eps': info.get('trailingEps'),
                'dividend_yield': info.get('dividendYield'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'company_name': info.get('longName', ticker),
                'history': hist
            }

            return data
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def fetch_historical_data(self, ticker, days=365):
        """Fetch historical data for technical analysis"""
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            hist = stock.history(start=start_date, end=end_date)

            return hist
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {str(e)}")
            return None

    def get_ticker_info(self, ticker):
        """Get comprehensive ticker information"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

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
            print(f"Error getting ticker info for {ticker}: {str(e)}")
            return {}

    def load_tickers(self, csv_path='data/tickers.csv'):
        """Load supported tickers from CSV"""
        try:
            df = pd.read_csv(csv_path)
            return dict(zip(df['Symbol'], df['Ticker']))
        except Exception as e:
            print(f"Error loading tickers: {str(e)}")
            return {}
