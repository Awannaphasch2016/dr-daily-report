import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# Database Configuration
SQLITE_DB_PATH = "ticker_data.db"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "ticker_reports"

# Analysis Parameters
TECHNICAL_INDICATORS = [
    "SMA_20", "SMA_50", "SMA_200",
    "RSI", "MACD", "BB_upper", "BB_lower",
    "Volume_SMA"
]

LOOKBACK_DAYS = 365

# Tickers Configuration
TICKERS_CSV_PATH = "tickers.csv"
