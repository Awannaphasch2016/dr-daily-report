"""
Application Configuration

Configuration follows Principle #23 (Configuration Variation Axis):
- Secrets/Environment-specific → Doppler env vars (os.getenv)
- Static values → Python constants (no env var)

See: .claude/CLAUDE.md#23-configuration-variation-axis
"""
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# API Keys (Doppler - secrets)
# =============================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# =============================================================================
# Database Configuration (mixed - some env-specific, some static)
# =============================================================================
SQLITE_DB_PATH = "data/ticker_data.db"  # Static - same everywhere
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")  # Env-specific
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))  # Env-specific
QDRANT_COLLECTION = "ticker_reports"  # Static - same everywhere

# =============================================================================
# Analysis Parameters (Static - never vary)
# =============================================================================
TECHNICAL_INDICATORS = [
    "SMA_20", "SMA_50", "SMA_200",
    "RSI", "MACD", "BB_upper", "BB_lower",
    "Volume_SMA"
]

LOOKBACK_DAYS = 365

# Tickers Configuration
TICKERS_CSV_PATH = "data/tickers.csv"

# =============================================================================
# Langfuse Tracing Constants (Static - never vary)
# Per Principle #23: Values that never change = Python constants
# =============================================================================

# Trace names (root-level traces)
class TRACE_NAMES:
    """Root-level trace names for @observe decorator."""
    ANALYZE_TICKER = "analyze_ticker"
    TEST_SCORING = "test_scoring"


# Observation/span names (nested under traces)
class OBSERVATION_NAMES:
    """Span names for workflow nodes."""
    FETCH_DATA = "fetch_data"
    ANALYZE_TECHNICAL = "analyze_technical"
    GENERATE_CHART = "generate_chart"
    GENERATE_REPORT = "generate_report"
    FETCH_COMPARATIVE_DATA = "fetch_comparative_data"
    ANALYZE_COMPARATIVE_INSIGHTS = "analyze_comparative_insights"
    GENERATE_SINGLESTAGE = "generate_singlestage"


# Quality score names
class SCORE_NAMES:
    """Quality score names pushed to Langfuse."""
    FAITHFULNESS = "faithfulness"
    COMPLETENESS = "completeness"
    REASONING_QUALITY = "reasoning_quality"
    COMPLIANCE = "compliance"
    CONSISTENCY = "consistency"

    @classmethod
    def all(cls) -> list[str]:
        """Return all score names as list."""
        return [
            cls.FAITHFULNESS,
            cls.COMPLETENESS,
            cls.REASONING_QUALITY,
            cls.COMPLIANCE,
            cls.CONSISTENCY,
        ]


# Default tag values
class TRACE_TAGS:
    """Standard tag values for trace filtering."""
    REPORT_GENERATION = "report_generation"
    TEST = "test"
    CLI = "cli"
    API = "api"
    SCHEDULED = "scheduled"


# Default user (for development/testing)
DEFAULT_USER_ID = "anak"
