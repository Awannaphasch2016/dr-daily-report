"""Pydantic models for API requests and responses"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Search Models
# ============================================================================

class SearchResult(BaseModel):
    """Single search result item"""
    ticker: str = Field(..., description="Ticker symbol (e.g., NVDA19)")
    company_name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Exchange (e.g., NASDAQ, SET)")
    currency: str = Field(..., description="Currency code (USD, THB, etc.)")
    type: Literal["equity", "etf", "fund"] = Field(default="equity", description="Security type")


class SearchResponse(BaseModel):
    """Search endpoint response"""
    results: list[SearchResult] = Field(..., description="List of matching tickers")


# ============================================================================
# Report Models
# ============================================================================

class SummarySections(BaseModel):
    """Summary sections of the report"""
    key_takeaways: list[str] = Field(default_factory=list, description="Key takeaway bullets")
    price_drivers: list[str] = Field(default_factory=list, description="Price driver bullets")
    risks_to_watch: list[str] = Field(default_factory=list, description="Risk bullet points")


class TechnicalMetric(BaseModel):
    """Single technical indicator"""
    name: str = Field(..., description="Indicator name (e.g., RSI, MACD)")
    value: float = Field(..., description="Current value")
    percentile: float = Field(..., description="Percentile rank (0-100)")
    category: Literal["momentum", "trend", "volatility", "liquidity"] = Field(..., description="Indicator category")
    status: Literal["bullish", "bearish", "neutral", "elevated_risk"] = Field(..., description="Signal status")
    explanation: str = Field(..., description="Brief explanation of current value")


class FundamentalMetric(BaseModel):
    """Single fundamental metric"""
    name: str = Field(..., description="Metric name (e.g., P/E, ROE)")
    value: float = Field(..., description="Current value")
    percentile: Optional[float] = Field(None, description="Percentile rank if available")
    comment: str = Field(default="", description="Brief comment or interpretation")


class Fundamentals(BaseModel):
    """Fundamental metrics grouped by category"""
    valuation: list[FundamentalMetric] = Field(default_factory=list, description="Valuation metrics")
    growth: list[FundamentalMetric] = Field(default_factory=list, description="Growth metrics")
    profitability: list[FundamentalMetric] = Field(default_factory=list, description="Profitability metrics")


class NewsItem(BaseModel):
    """Single news article"""
    title: str = Field(..., description="News headline")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source/publisher")
    published_at: datetime = Field(..., description="Publication timestamp")
    sentiment_label: Literal["positive", "neutral", "negative"] = Field(..., description="Sentiment classification")
    sentiment_score: float = Field(..., ge=0.0, le=1.0, description="Sentiment score (0-1)")


class OverallSentiment(BaseModel):
    """Aggregated news sentiment"""
    positive_pct: float = Field(..., ge=0, le=100, description="Percentage positive news")
    neutral_pct: float = Field(..., ge=0, le=100, description="Percentage neutral news")
    negative_pct: float = Field(..., ge=0, le=100, description="Percentage negative news")


class UncertaintyScore(BaseModel):
    """Uncertainty score with percentile"""
    value: float = Field(..., description="Uncertainty score (0-100)")
    percentile: float = Field(..., description="Percentile rank")


class Risk(BaseModel):
    """Risk assessment"""
    risk_level: Literal["low", "medium", "high"] = Field(..., description="Overall risk level")
    volatility_score: float = Field(..., description="Volatility score")
    uncertainty_score: UncertaintyScore = Field(..., description="Uncertainty metrics")
    risk_bullets: list[str] = Field(default_factory=list, description="Key risk points")


class Peer(BaseModel):
    """Peer comparison"""
    ticker: str = Field(..., description="Peer ticker symbol")
    company_name: str = Field(..., description="Peer company name")
    estimated_upside_pct: Optional[float] = Field(None, description="Estimated upside percentage")
    stance: Literal["bullish", "bearish", "neutral"] = Field(..., description="Investment stance")
    valuation_label: Literal["cheap", "fair", "expensive"] = Field(..., description="Valuation assessment")


class GenerationMetadata(BaseModel):
    """Report generation metadata"""
    agent_version: str = Field(default="v1.0.0", description="Agent version")
    strategy: str = Field(..., description="Analysis strategy used")
    generated_at: datetime = Field(..., description="Generation timestamp")
    cache_hit: bool = Field(default=False, description="Whether result was cached")


class ReportResponse(BaseModel):
    """Full ticker report response"""
    # Basic info
    ticker: str = Field(..., description="Ticker symbol")
    company_name: str = Field(..., description="Company name")
    price: float = Field(..., description="Current price")
    price_change_pct: float = Field(..., description="Day change percentage")
    currency: str = Field(..., description="Currency code")
    as_of: datetime = Field(..., description="Data timestamp")

    # Investment stance
    stance: Literal["bullish", "bearish", "neutral"] = Field(..., description="Investment stance")
    estimated_upside_pct: Optional[float] = Field(None, description="Estimated upside/downside")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    investment_horizon: str = Field(..., description="Investment time horizon")

    # Full narrative report (Thai language)
    narrative_report: str = Field(
        default="",
        description="Full Thai language narrative report with analysis and recommendations"
    )

    # Report sections
    summary_sections: SummarySections = Field(..., description="Summary bullets")
    technical_metrics: list[TechnicalMetric] = Field(..., description="Technical indicators")
    fundamentals: Fundamentals = Field(..., description="Fundamental metrics")
    news_items: list[NewsItem] = Field(..., description="Related news")
    overall_sentiment: OverallSentiment = Field(..., description="Aggregated sentiment")
    risk: Risk = Field(..., description="Risk assessment")
    peers: list[Peer] = Field(default_factory=list, description="Peer comparisons")

    # Additional data
    data_sources: list[str] = Field(..., description="Data sources used")
    pdf_report_url: Optional[str] = Field(None, description="PDF report URL")
    generation_metadata: GenerationMetadata = Field(..., description="Generation info")


# ============================================================================
# Rankings Models
# ============================================================================

class RankedTicker(BaseModel):
    """Single ranked ticker in market movers"""
    ticker: str = Field(..., description="Ticker symbol")
    company_name: str = Field(..., description="Company name")
    price: float = Field(..., description="Current price")
    price_change_pct: float = Field(..., description="Day change percentage")
    currency: str = Field(..., description="Currency code")
    stance: Optional[Literal["bullish", "bearish", "neutral"]] = Field(None, description="Investment stance")
    estimated_upside_pct: Optional[float] = Field(None, description="Estimated upside")
    risk_level: Optional[Literal["low", "medium", "high"]] = Field(None, description="Risk level")


class RankingsResponse(BaseModel):
    """Rankings endpoint response"""
    category: Literal["top_gainers", "top_losers", "volume_surge", "trending"] = Field(..., description="Ranking category")
    as_of: datetime = Field(..., description="Data timestamp")
    tickers: list[RankedTicker] = Field(..., description="Ranked ticker list")


# ============================================================================
# Watchlist Models
# ============================================================================

class WatchlistItem(BaseModel):
    """Single watchlist item"""
    ticker: str = Field(..., description="Ticker symbol")
    company_name: str = Field(..., description="Company name")
    added_at: datetime = Field(..., description="When added to watchlist")


class WatchlistResponse(BaseModel):
    """Watchlist GET response"""
    tickers: list[WatchlistItem] = Field(..., description="Watchlist items")


class WatchlistAddRequest(BaseModel):
    """Watchlist POST request"""
    ticker: str = Field(..., description="Ticker symbol to add")


class WatchlistOperationResponse(BaseModel):
    """Watchlist POST/DELETE response"""
    status: Literal["ok"] = Field(default="ok", description="Operation status")
    ticker: str = Field(..., description="Affected ticker")


# ============================================================================
# Error Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Additional error details"""
    ticker: Optional[str] = Field(None, description="Related ticker if applicable")
    field: Optional[str] = Field(None, description="Related field if applicable")


class ErrorResponse(BaseModel):
    """Standardized error response"""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[ErrorDetail] = Field(None, description="Additional error details")


class ErrorEnvelope(BaseModel):
    """Error response envelope"""
    error: ErrorResponse = Field(..., description="Error details")


# ============================================================================
# Async Job Models
# ============================================================================

class JobSubmitResponse(BaseModel):
    """Response for POST /report/{ticker} - job submission

    Status can be:
    - 'pending': New async job created, poll status endpoint for result
    - 'completed': Cache hit, job_id is prefixed with 'cached_', result available immediately
    """
    job_id: str = Field(..., description="Unique job identifier (prefixed with 'cached_' for cache hits)")
    status: Literal["pending", "completed"] = Field(default="pending", description="Job status: 'pending' for new jobs, 'completed' for cache hits")


class JobStatusResponse(BaseModel):
    """Response for GET /report/status/{job_id} - job status check"""
    job_id: str = Field(..., description="Unique job identifier")
    ticker: str = Field(..., description="Ticker symbol")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Processing end timestamp")
    result: Optional[dict] = Field(None, description="Report result when completed")
    error: Optional[str] = Field(None, description="Error message when failed")
