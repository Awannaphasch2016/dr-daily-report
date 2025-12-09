# MCP Integration for Enhanced Financial Report Generation

**Status**: Research Complete, Implementation Pending
**Created**: 2025-12-10
**Purpose**: Enhance LLM-powered financial reports using Model Context Protocol (MCP) servers
**Target Phase**: Post-Infrastructure Setup (after Fund Data Sync deployment)

---

## Executive Summary

This document outlines research findings on integrating MCP (Model Context Protocol) servers to enhance the quality and depth of AI-generated financial reports in the Daily Report system.

**Key Findings:**
- **15 MCP servers** identified across two categories:
  - **7 Infrastructure MCPs**: For development workflow enhancement (Claude Code agent)
  - **8 Financial Analysis MCPs**: For LLM report generation enhancement (GPT-4o/Claude pipeline)
- **Primary Integration Point**: LangGraph workflow nodes in report generation pipeline
- **Expected Impact**: Richer fundamental analysis, real-time market data, backtesting capabilities, portfolio analytics

**Critical Distinction:**
- Infrastructure MCPs → Used by **Claude Code agent** (this IDE assistant)
- Financial MCPs → Used by **the app's LLM pipeline** (OpenRouter → GPT-4o/Claude generating reports for end users)

---

## What is MCP?

Model Context Protocol (MCP) is an open standard that enables AI systems to integrate with external data sources and tools through a unified interface.

**For this project:**
```
Traditional Flow:
  LangGraph Node → yfinance API → Parse JSON → LLM Prompt

MCP-Enhanced Flow:
  LangGraph Node → MCP Server (Alpaca/SEC EDGAR/Alpha Vantage) → Structured Data → LLM Prompt
```

**Benefits:**
- Structured data retrieval vs custom API parsing
- Richer data sources (10-K filings, options data, economic indicators)
- Standardized integration pattern across multiple data providers
- Better error handling and rate limiting

---

## Part 1: Infrastructure MCPs (For Development Workflow)

These MCPs enhance the Claude Code agent's ability to work with our infrastructure. They are NOT used by the report generation pipeline.

### Quick Reference

| MCP Server | Priority | Use Case | Provider |
|------------|----------|----------|----------|
| AWS Terraform MCP | 🔥 Immediate | Terraform validation, debugging | AWS Labs (Official) |
| CloudWatch MCP | 🔥 Immediate | Log analysis, debugging | AWS Labs (Official) |
| MySQL/Aurora MCP | 🔥 High | Database queries, schema validation | Community |
| HashiCorp Vault MCP | 🔥 High | Secret management, IAM policies | HashiCorp (Official) |
| GitHub MCP | ⚡ Medium | PR management, CI/CD monitoring | Configured |
| AWS MCP | ⚡ Medium | Resource management, IAM | Configured |
| Docker MCP | ⚡ Medium | Dockerfile optimization | Community |

**Configuration**: See `/home/anak/.claude/plans/shimmering-munching-knuth.md` for detailed setup instructions and `.cursor/mcp.json` configuration templates.

**Note**: User explicitly stated infrastructure MCPs will be configured AFTER infrastructure setup is complete.

---

## Part 2: Financial Analysis MCPs (For LLM Report Generation)

These MCPs will be integrated into the app's LangGraph workflow to enhance financial reports generated for end users.

### Overview

**Current Report Generation Architecture:**
```
User Request (Telegram/LINE)
  ↓
Workflow Orchestrator (LangGraph)
  ↓
┌─────────────────────────────────────┐
│ Data Collection Nodes:              │
│ - yfinance (price history)          │
│ - Manual fundamentals lookup        │
│ - News scraping (limited)           │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ Analysis Nodes:                     │
│ - Technical indicators (pandas)     │
│ - Fundamental ratios (manual calc)  │
│ - Peer comparison (correlation)     │
└─────────────────────────────────────┘
  ↓
LLM Report Generation (OpenRouter → GPT-4o/Claude)
  ↓
Thai Language Report (LINE/Telegram Bot)
```

**MCP-Enhanced Architecture:**
```
User Request
  ↓
Workflow Orchestrator
  ↓
┌──────────────────────────────────────┐
│ MCP-Enhanced Data Collection:        │
│ - Alpaca MCP (real-time + options)   │
│ - SEC EDGAR MCP (10-K/10-Q filings)  │
│ - Alpha Vantage MCP (FX, econ data)  │
│ - yfinance (backup/supplement)       │
└──────────────────────────────────────┘
  ↓
┌──────────────────────────────────────┐
│ MCP-Enhanced Analysis:               │
│ - QuantConnect MCP (backtesting)     │
│ - Financial Markets MCP (strategies) │
│ - Portfolio Manager MCP (analytics)  │
│ - MonteWalk MCP (risk assessment)    │
└──────────────────────────────────────┘
  ↓
LLM Report Generation (with enriched context)
  ↓
Enhanced Thai Language Report
```

---

### 1. Alpaca Trading API MCP Server ⭐⭐⭐

**Source**: [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server)
**Provider**: Alpaca Markets (Official)
**Priority**: High - Real-time market data

**Capabilities:**
- Real-time stock/crypto price data (WebSocket + REST)
- Options chain data (implied volatility, Greeks: delta, gamma, theta, vega)
- Level 2 order book depth
- Historical bars at multiple timeframes (1min, 5min, 1hour, 1day)
- Paper trading API for strategy validation

**Data Enhancement Examples:**

Before (yfinance only):
> "NVDA closed at $495.23, up 2.1% today."

After (Alpaca MCP):
> "NVDA closed at $495.23 (+2.1%). Options market shows implied volatility at 35% (elevated), with traders positioning for potential 20% price swing in next month. Call/put ratio of 1.4 suggests bullish sentiment. Real-time order book shows strong support at $490 level with 15,000 shares bid."

**Integration Point:**
```python
# src/workflow/nodes/data_collection.py

async def fetch_market_data_enhanced(state: AgentState) -> AgentState:
    ticker = state['ticker']

    # Primary: Alpaca MCP for real-time data
    try:
        alpaca_data = await mcp_client.call_tool(
            "alpaca",
            "get_latest_bars",
            {"symbol": ticker, "timeframe": "1Day"}
        )

        # Get options data if available
        options_data = await mcp_client.call_tool(
            "alpaca",
            "get_option_chain",
            {"symbol": ticker}
        )

        state['market_data'] = {
            'bars': alpaca_data,
            'options': options_data,
            'source': 'alpaca_mcp'
        }
    except Exception as e:
        # Fallback to yfinance
        logger.warning(f"Alpaca MCP failed: {e}, falling back to yfinance")
        state['market_data'] = fetch_yfinance_fallback(ticker)

    return state
```

**Cost Considerations:**
- Free tier: Real-time data for US stocks (15-minute delay for options)
- Paid tier: $99/month for real-time everything + unlimited API calls
- Paper trading: Always free

---

### 2. SEC EDGAR MCP Server ⭐⭐⭐

**Source**: [stefanoamorelli/sec-edgar-mcp](https://github.com/stefanoamorelli/sec-edgar-mcp)
**Provider**: Community (Multiple implementations available)
**Priority**: High - Fundamental analysis depth

**Capabilities:**
- 10-K/10-Q annual and quarterly reports (full text + XBRL data)
- 8-K current reports (material events, earnings)
- Form 4 insider trading filings (officers, directors, 10%+ shareholders)
- Earnings call transcripts (management commentary, Q&A)
- Direct XBRL tag extraction (exact financial metrics, no parsing errors)

**Data Enhancement Examples:**

Before (manual fundamentals lookup):
> "NVDA reported strong Q3 results with revenue growth."

After (SEC EDGAR MCP):
> "Per NVDA's 10-Q filed Nov 20, 2024: Data Center revenue $30.8B (+112% YoY), now 87% of total revenue (up from 78% last year). Operating margin expanded from 32% to 47%. Management cited 'insatiable demand for AI compute' in earnings call. Risk factors (Item 1A) highlight supply chain constraints for H100 GPUs. Insider activity: CEO Jensen Huang sold 100,000 shares on Nov 15 at $450 (Form 4 filing)."

**Integration Point:**
```python
# src/workflow/nodes/fundamental_analysis.py

async def analyze_fundamentals_enhanced(state: AgentState) -> AgentState:
    ticker = state['ticker']

    # Fetch latest 10-Q filing
    filing_data = await mcp_client.call_tool(
        "sec_edgar",
        "get_latest_filing",
        {
            "ticker": ticker,
            "form_type": "10-Q",
            "include_xbrl": True
        }
    )

    # Extract specific XBRL tags for exact metrics
    revenue = filing_data['xbrl']['RevenueFromContractWithCustomerExcludingAssessedTax']
    operating_margin = filing_data['xbrl']['OperatingIncomeLossMargin']

    # Get insider trading activity
    insider_trades = await mcp_client.call_tool(
        "sec_edgar",
        "get_insider_trades",
        {"ticker": ticker, "days_back": 90}
    )

    state['fundamental_data'] = {
        'filing': filing_data,
        'metrics': {'revenue': revenue, 'op_margin': operating_margin},
        'insider_activity': insider_trades
    }

    return state
```

**Cost Considerations:**
- SEC EDGAR API: Completely free (public data)
- Rate limits: 10 requests/second per IP
- No authentication required

**Note for Thai Stocks:**
SEC EDGAR only covers US-listed companies. For Thai SET stocks (DBS19, MWG19), this provides comparative analysis against US peers or ADRs.

---

### 3. Alpha Vantage MCP Server ⭐⭐⭐

**Source**: [Official Alpha Vantage MCP](https://mcp.alphavantage.co/)
**Provider**: Alpha Vantage (Official)
**Priority**: High - yfinance replacement + macro data

**Capabilities:**
- Stock time series (intraday, daily, weekly, monthly)
- Foreign exchange rates (USD/THB critical for Thai stocks)
- Cryptocurrencies (BTC, ETH)
- Technical indicators (computed server-side: RSI, MACD, Bollinger Bands)
- Economic indicators via FRED (Federal Reserve data: interest rates, GDP, unemployment)

**Why Better Than yfinance:**
| yfinance | Alpha Vantage MCP |
|----------|-------------------|
| Web scraping (fragile) | Official API (stable) |
| No FX rates | Real-time FX (USD/THB) |
| No macro data | FRED economic indicators |
| Rate limits unclear | 500 calls/day (free), 1200/min (paid) |
| Community maintained | Officially supported |

**Data Enhancement Examples:**

Before (yfinance only):
> "DBS19 trades on Singapore Exchange in SGD."

After (Alpha Vantage MCP):
> "DBS19: SGD 35.20 → THB 931.28 (USD/THB: 33.45, -0.3% today). Currency headwind from THB strength. Federal Reserve held rates at 5.25% (per FRED data), supporting regional currencies vs USD. SGD/THB cross-rate implications for Thai investors."

**Integration Point:**
```python
# src/workflow/nodes/data_collection.py

async def enrich_with_macro_context(state: AgentState) -> AgentState:
    # Get USD/THB exchange rate for Thai investors
    fx_rate = await mcp_client.call_tool(
        "alpha_vantage",
        "get_fx_rate",
        {"from_currency": "USD", "to_currency": "THB"}
    )

    # Get Federal Reserve interest rate (macro context)
    fed_rate = await mcp_client.call_tool(
        "alpha_vantage",
        "get_fred_data",
        {"indicator": "FEDFUNDS"}  # Federal Funds Rate
    )

    # Get technical indicators computed server-side
    rsi = await mcp_client.call_tool(
        "alpha_vantage",
        "get_rsi",
        {"symbol": state['ticker'], "interval": "daily", "time_period": 14}
    )

    state['macro_context'] = {
        'fx_usd_thb': fx_rate,
        'fed_rate': fed_rate,
        'rsi': rsi
    }

    return state
```

**Cost Considerations:**
- Free tier: 500 API calls/day (25/day for some endpoints)
- Premium: $49.99/month for 1200 calls/min
- Strategy: Use for FX rates + macro data, supplement yfinance for price history

---

### 4. QuantConnect MCP Server ⭐⭐

**Source**: [taylorwilsdon/quantconnect-mcp](https://github.com/taylorwilsdon/quantconnect-mcp)
**Provider**: Community (Taylor Wilsdon)
**Priority**: Medium - Advanced backtesting

**Capabilities:**
- Institutional-grade backtesting engine (QuantConnect LEAN)
- Multi-asset support (equities, forex, crypto, futures, options)
- Alternative data (sentiment analysis, satellite imagery, web traffic)
- Statistical arbitrage tools (cointegration tests, PCA, pairs trading)
- Portfolio optimization (Markowitz, Black-Litterman, risk parity)

**Data Enhancement Examples:**

Before (no backtesting):
> "RSI shows oversold signal - potential buying opportunity."

After (QuantConnect MCP):
> "RSI oversold signal detected. Historical backtest of RSI(14) < 30 strategy on DBS19 (2019-2024): 15.2% annual return, 62% win rate, Sharpe ratio 1.4, max drawdown -12%. Strategy outperformed buy-and-hold by 7.3% annually. Note: 2024 performance degraded (Sharpe 0.9) suggesting regime change."

**Integration Point:**
```python
# src/workflow/nodes/technical_analysis.py

async def backtest_strategy(state: AgentState) -> AgentState:
    ticker = state['ticker']
    indicators = state['indicators']  # RSI, MACD, etc.

    # Define strategy based on technical signals
    if indicators['rsi'] < 30:  # Oversold
        # Backtest RSI mean reversion strategy
        backtest_results = await mcp_client.call_tool(
            "quantconnect",
            "run_backtest",
            {
                "algorithm": "RSIMeanReversion",
                "symbol": ticker,
                "start_date": "2019-01-01",
                "end_date": "2024-12-31",
                "parameters": {"rsi_period": 14, "oversold_threshold": 30}
            }
        )

        state['backtest'] = {
            'strategy': 'RSI Mean Reversion',
            'returns': backtest_results['total_return'],
            'sharpe': backtest_results['sharpe_ratio'],
            'max_drawdown': backtest_results['max_drawdown'],
            'win_rate': backtest_results['win_rate']
        }

    return state
```

**Cost Considerations:**
- Free tier: Limited backtests, 1-year history
- Premium: $20/month for unlimited backtests, full history, live trading
- Alternative: Self-host LEAN engine (free, but requires setup)

---

### 5. Financial Markets Analysis MCP ⭐⭐

**Source**: [olonok69/mcp_financial_markets_analysis_tool](https://lobehub.com/mcp/olonok69-mcp_financial_markets_analysis_tool)
**Provider**: Community (olonok69)
**Priority**: Medium - Technical strategy validation

**Capabilities:**
- Pre-built technical analysis strategies (50+ indicators)
- Multi-indicator confluence scoring (signal strength aggregation)
- Risk-adjusted return metrics (Sharpe, Sortino, Calmar ratios)
- Strategy backtesting with transaction costs
- Walk-forward optimization (avoid overfitting)

**Data Enhancement Examples:**

Before (single indicator):
> "MACD shows bullish crossover."

After (Financial Markets MCP):
> "MACD bullish crossover confirmed by multiple signals: RSI(14) at 45 (neutral-bullish), price above 50-day MA, volume 1.3x average. **Confluence score: 8/10** (strong buy signal). Historical backtest of this signal combination: 68% win rate, average gain +4.2%, Sortino ratio 2.1 (downside risk-adjusted). Signal valid for 5-7 day holding period."

**Integration Point:**
```python
# src/workflow/nodes/technical_analysis.py

async def analyze_signal_confluence(state: AgentState) -> AgentState:
    indicators = state['indicators']

    # Calculate multi-indicator confluence
    confluence = await mcp_client.call_tool(
        "financial_markets",
        "calculate_confluence",
        {
            "indicators": indicators,
            "price_data": state['ticker_data'],
            "strategy": "momentum_breakout"
        }
    )

    # Get risk-adjusted metrics
    performance = await mcp_client.call_tool(
        "financial_markets",
        "backtest_strategy",
        {
            "strategy": "momentum_breakout",
            "symbol": state['ticker'],
            "period": "1y"
        }
    )

    state['technical_analysis'] = {
        'confluence_score': confluence['score'],  # 0-10
        'signal_strength': confluence['strength'],  # weak/medium/strong
        'sharpe_ratio': performance['sharpe'],
        'sortino_ratio': performance['sortino'],
        'win_rate': performance['win_rate']
    }

    return state
```

**Cost Considerations:**
- Open source, free to use
- Self-hosted or cloud deployment
- No external API costs

---

### 6. Investment Portfolio Manager MCP ⭐⭐

**Source**: [ikhyunAn/MCP_InvestmentPortfolio](https://github.com/ikhyunAn/MCP_InvestmentPortfolio)
**Provider**: Community (ikhyunAn)
**Priority**: Medium - Portfolio-level insights (future feature)

**Capabilities:**
- Portfolio construction and tracking
- Diversification analysis (correlation matrix, concentration risk)
- Rebalancing recommendations (threshold, periodic, tactical)
- Tax-loss harvesting opportunities
- Performance attribution (factor exposure, sector allocation)

**Data Enhancement Examples:**

Before (single-stock analysis):
> "DBS19 shows strong fundamentals - consider buying."

After (Portfolio Manager MCP):
> "DBS19 fundamental rating: 8/10. **Portfolio impact analysis**: Your current portfolio is 35% financials (15% overweight vs target). Adding DBS19 would increase correlation with existing OCBC19 holdings to 0.75 (high). **Recommendation**: Consider selling 50% OCBC19 position before adding DBS19 to maintain diversification. Alternative: Equal-weight DBS19, UOB19, OCBC19 for broader financial sector exposure."

**Integration Point:**
```python
# src/workflow/nodes/portfolio_analysis.py (FUTURE FEATURE)

async def analyze_portfolio_impact(state: AgentState) -> AgentState:
    ticker = state['ticker']
    user_portfolio = state.get('user_portfolio', [])  # From user profile

    if user_portfolio:
        # Analyze correlation with existing holdings
        portfolio_analysis = await mcp_client.call_tool(
            "portfolio_manager",
            "analyze_new_position",
            {
                "portfolio": user_portfolio,
                "new_ticker": ticker,
                "allocation_pct": 10  # Proposed allocation
            }
        )

        state['portfolio_impact'] = {
            'diversification_score': portfolio_analysis['div_score'],
            'correlation_increase': portfolio_analysis['corr_delta'],
            'sector_concentration': portfolio_analysis['sector_weight'],
            'recommendation': portfolio_analysis['action']  # buy/hold/rebalance
        }

    return state
```

**Cost Considerations:**
- Open source, free
- Future feature for Telegram Mini App (portfolio tracking UI)

**Note**: This is a future enhancement. Current system focuses on single-stock analysis.

---

### 7. MonteWalk Quantitative Trading MCP ⭐

**Source**: [MonteWalk MCP](https://www.pulsemcp.com/servers/n-lia-montewalk)
**Provider**: Community
**Priority**: Low - Advanced risk assessment (premium feature)

**Capabilities:**
- Monte Carlo simulations (10,000+ scenarios)
- Value at Risk (VaR) calculations (95%, 99% confidence intervals)
- Expected Shortfall (CVaR) - tail risk assessment
- Scenario analysis (bull/bear/sideways market projections)
- Portfolio stress testing (2008 crisis, COVID crash simulations)

**Data Enhancement Examples:**

Before (no risk quantification):
> "DBS19 has moderate volatility."

After (MonteWalk MCP):
> "Monte Carlo simulation (10,000 runs, 90-day horizon): 95% confidence interval [SGD 32.50 - SGD 38.90]. Median outcome: SGD 35.80 (+1.7%). **Value at Risk (95%)**: Maximum 1-day loss of SGD -1.85 (-5.3%). **Stress test**: In 2008-style crisis scenario (based on historical correlations), expected decline of -28%. In COVID crash scenario: -18% (financial sector resilience improved since 2020)."

**Integration Point:**
```python
# src/workflow/nodes/risk_analysis.py (FUTURE FEATURE - PREMIUM)

async def assess_risk_scenarios(state: AgentState) -> AgentState:
    ticker = state['ticker']
    price_history = state['ticker_data']

    # Run Monte Carlo simulation
    monte_carlo = await mcp_client.call_tool(
        "montewalk",
        "run_monte_carlo",
        {
            "symbol": ticker,
            "simulations": 10000,
            "days": 90,
            "method": "geometric_brownian_motion"
        }
    )

    # Calculate VaR
    var_95 = await mcp_client.call_tool(
        "montewalk",
        "calculate_var",
        {
            "returns": price_history['returns'],
            "confidence_level": 0.95,
            "horizon_days": 1
        }
    )

    # Stress test scenarios
    stress_test = await mcp_client.call_tool(
        "montewalk",
        "stress_test",
        {
            "symbol": ticker,
            "scenarios": ["2008_crisis", "covid_crash", "interest_rate_shock"]
        }
    )

    state['risk_assessment'] = {
        'monte_carlo': monte_carlo,
        'var_95': var_95,
        'stress_test': stress_test
    }

    return state
```

**Cost Considerations:**
- Likely paid service (pricing not publicly listed)
- Resource-intensive (10,000 simulations)
- Suitable for premium/pro tier users

---

### 8. Pandas/Time Series MCP ⭐

**Source**: [alistairwalsh/pandas MCP](https://www.pulsemcp.com/servers/alistairwalsh-pandas)
**Provider**: Community (Alistair Walsh)
**Priority**: Low - Development/debugging tool

**Capabilities:**
- DataFrame manipulation via natural language
- Time series resampling and interpolation
- Statistical analysis (correlation, regression, hypothesis tests)
- Data cleaning and preprocessing

**Use Case:**
Primarily for interactive debugging and ad-hoc analysis during development, not production report generation.

**Example:**
- "Show correlation matrix for tech stocks in my dataset"
- "Resample hourly data to daily OHLC bars"
- "Find outliers in price data using z-score > 3"

**Integration**: Development only, not production workflow.

---

## Implementation Roadmap

### Phase 0: Infrastructure Setup (CURRENT)
**Goal**: Deploy Fund Data Sync ETL, validate dev environment
**Timeline**: In progress
**Deliverables**:
- ✅ Fund Data Sync Lambda deployed
- ✅ S3 → SQS → Lambda → Aurora pipeline functional
- ⬜ Manual UI validation completed

---

### Phase 1: Core Financial MCPs (Weeks 1-2)

**Goal**: Integrate foundational data sources (Alpaca, SEC EDGAR, Alpha Vantage)

**Tasks:**
1. **Setup MCP Infrastructure**
   - Install MCP client library in LangGraph environment
   - Configure MCP servers for Alpaca, SEC EDGAR, Alpha Vantage
   - Test connectivity and authentication

2. **Modify LangGraph Workflow**
   - Update `src/workflow/nodes/data_collection.py` to call MCPs
   - Implement fallback chain: MCP → yfinance → cached data
   - Add MCP response parsing and validation

3. **Update Report Templates**
   - Modify LLM prompts to utilize enriched MCP data
   - Add sections for options data, insider trades, FX rates
   - Update transparency footer to credit MCP data sources

4. **Testing**
   - Integration tests: MCP calls → data retrieval → LLM generation
   - Validate report quality improvement
   - Test fallback mechanisms

**Success Criteria:**
- Reports include real-time options data (Alpaca)
- Fundamental analysis cites 10-K/10-Q filings (SEC EDGAR)
- Thai stock reports show USD/THB FX context (Alpha Vantage)

---

### Phase 2: Advanced Analysis MCPs (Weeks 3-4)

**Goal**: Add backtesting and portfolio analytics (QuantConnect, Financial Markets, Portfolio Manager)

**Tasks:**
1. **Integrate Backtesting**
   - Add QuantConnect MCP to technical analysis nodes
   - Implement strategy backtesting for common signals (RSI, MACD)
   - Display backtest results in report recommendations section

2. **Multi-Indicator Confluence**
   - Integrate Financial Markets MCP for signal scoring
   - Calculate confluence scores for technical signals
   - Add risk-adjusted return metrics (Sharpe, Sortino)

3. **Portfolio Analysis (Optional)**
   - Design user portfolio tracking schema in DynamoDB
   - Integrate Portfolio Manager MCP for diversification analysis
   - Add portfolio impact section to reports (Telegram Mini App only)

**Success Criteria:**
- Technical analysis includes backtested win rates
- Signal strength scores (1-10) based on multi-indicator confluence
- Portfolio-level recommendations (for users with tracked portfolios)

---

### Phase 3: Risk Assessment (Weeks 5-6, Premium Feature)

**Goal**: Add Monte Carlo simulations and stress testing (MonteWalk MCP)

**Tasks:**
1. **Risk Simulation**
   - Integrate MonteWalk MCP for Monte Carlo simulations
   - Calculate VaR and Expected Shortfall
   - Run stress tests against historical crisis scenarios

2. **Premium Tier Gating**
   - Add subscription tier check before risk analysis
   - Design paywall for premium features
   - Update pricing page with risk analysis highlights

3. **Report Enhancements**
   - Add "Risk Assessment" section to premium reports
   - Include scenario projections and probability distributions
   - Display stress test results with historical context

**Success Criteria:**
- Premium users receive Monte Carlo projections
- VaR calculations accurate vs historical volatility
- Stress tests use realistic crisis scenarios

---

### Phase 4: Optimization & Monitoring (Ongoing)

**Goal**: Monitor MCP performance, cost, and quality impact

**Metrics to Track:**
- **Cost**: MCP API usage vs budget
- **Latency**: Report generation time (before/after MCP)
- **Quality**: User ratings, report completeness scores
- **Reliability**: MCP uptime, fallback frequency

**Optimization:**
- Cache MCP responses (10-K filings valid for 90 days)
- Batch MCP calls where possible
- Implement circuit breakers for failing MCPs
- A/B test MCP vs non-MCP reports

---

## Integration Architecture

### LangGraph Workflow Modification

**Current Architecture:**
```python
# src/workflow/report_workflow.py

workflow = StateGraph(AgentState)

# Existing nodes
workflow.add_node("fetch_data", fetch_ticker_data)
workflow.add_node("technical_analysis", analyze_technical)
workflow.add_node("fundamental_analysis", analyze_fundamental)
workflow.add_node("generate_report", generate_report)

# Linear flow
workflow.set_entry_point("fetch_data")
workflow.add_edge("fetch_data", "technical_analysis")
workflow.add_edge("technical_analysis", "fundamental_analysis")
workflow.add_edge("fundamental_analysis", "generate_report")
```

**MCP-Enhanced Architecture:**
```python
# src/workflow/report_workflow_enhanced.py

from src.integrations.mcp_client import MCPClient

# Initialize MCP client (singleton)
mcp_client = MCPClient()

workflow = StateGraph(AgentState)

# Enhanced nodes with MCP integration
workflow.add_node("fetch_data_mcp", fetch_ticker_data_with_mcp)
workflow.add_node("technical_analysis_mcp", analyze_technical_with_backtesting)
workflow.add_node("fundamental_analysis_mcp", analyze_fundamental_with_filings)
workflow.add_node("risk_analysis_mcp", assess_risk_scenarios)  # New node
workflow.add_node("generate_report", generate_enhanced_report)

# Enhanced flow with conditional risk analysis
workflow.set_entry_point("fetch_data_mcp")
workflow.add_edge("fetch_data_mcp", "technical_analysis_mcp")
workflow.add_edge("technical_analysis_mcp", "fundamental_analysis_mcp")

# Conditional: Add risk analysis for premium users
workflow.add_conditional_edges(
    "fundamental_analysis_mcp",
    lambda state: "risk_analysis_mcp" if state.get("user_tier") == "premium" else "generate_report",
    {
        "risk_analysis_mcp": "risk_analysis_mcp",
        "generate_report": "generate_report"
    }
)
workflow.add_edge("risk_analysis_mcp", "generate_report")
```

### MCP Client Implementation

```python
# src/integrations/mcp_client.py

from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """Singleton MCP client for calling external MCP servers."""

    _instance: Optional['MCPClient'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Initialize MCP server connections
        self.servers = {
            'alpaca': AlpacaMCPServer(api_key=os.getenv('ALPACA_API_KEY')),
            'sec_edgar': SECEdgarMCPServer(),
            'alpha_vantage': AlphaVantageMCPServer(api_key=os.getenv('ALPHAVANTAGE_API_KEY')),
            'quantconnect': QuantConnectMCPServer(api_key=os.getenv('QC_API_KEY')),
            'financial_markets': FinancialMarketsMCPServer(),
            'portfolio_manager': PortfolioManagerMCPServer(),
            'montewalk': MonteWalkMCPServer(api_key=os.getenv('MONTEWALK_API_KEY'))
        }
        self._initialized = True

    async def call_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Call MCP server tool with timeout and error handling.

        Args:
            server: MCP server name ('alpaca', 'sec_edgar', etc.)
            tool: Tool name within server
            params: Tool parameters
            timeout: Request timeout in seconds

        Returns:
            Tool response data

        Raises:
            MCPServerError: If MCP call fails
        """
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")

        try:
            logger.info(f"Calling {server}.{tool} with params: {params}")

            # Call with timeout
            result = await asyncio.wait_for(
                self.servers[server].call_tool(tool, params),
                timeout=timeout
            )

            logger.info(f"{server}.{tool} returned successfully")
            return result

        except asyncio.TimeoutError:
            logger.error(f"{server}.{tool} timed out after {timeout}s")
            raise MCPServerError(f"MCP timeout: {server}.{tool}")
        except Exception as e:
            logger.error(f"{server}.{tool} failed: {e}")
            raise MCPServerError(f"MCP call failed: {server}.{tool} - {e}")

class MCPServerError(Exception):
    """Exception raised when MCP server call fails."""
    pass
```

### Enhanced Data Collection Node

```python
# src/workflow/nodes/data_collection_enhanced.py

async def fetch_ticker_data_with_mcp(state: AgentState) -> AgentState:
    """
    Enhanced data collection using MCP servers with fallback chain.

    Fallback chain: Alpaca MCP → yfinance → S3 cache
    """
    ticker = state['ticker']
    mcp_client = MCPClient()

    # Try Alpaca MCP first (real-time data)
    try:
        logger.info(f"Fetching {ticker} from Alpaca MCP")
        alpaca_data = await mcp_client.call_tool(
            'alpaca',
            'get_latest_bars',
            {'symbol': ticker, 'timeframe': '1Day', 'limit': 365}
        )

        # Get options data if available
        try:
            options_data = await mcp_client.call_tool(
                'alpaca',
                'get_option_chain',
                {'symbol': ticker}
            )
            alpaca_data['options'] = options_data
        except MCPServerError:
            logger.warning(f"No options data for {ticker}")
            alpaca_data['options'] = None

        state['ticker_data'] = alpaca_data
        state['data_source'] = 'alpaca_mcp'

    except MCPServerError as e:
        # Fallback to yfinance
        logger.warning(f"Alpaca MCP failed: {e}, falling back to yfinance")
        try:
            yf_data = fetch_yfinance_data(ticker)
            state['ticker_data'] = yf_data
            state['data_source'] = 'yfinance'
        except Exception as yf_error:
            # Final fallback to S3 cache
            logger.error(f"yfinance failed: {yf_error}, using cached data")
            cached_data = s3_data_lake.get_cached_ticker_data(ticker)
            if not cached_data:
                state['error'] = f"All data sources failed for {ticker}"
                return state
            state['ticker_data'] = cached_data
            state['data_source'] = 's3_cache'

    # Enrich with FX rates (Alpha Vantage MCP)
    try:
        fx_rate = await mcp_client.call_tool(
            'alpha_vantage',
            'get_fx_rate',
            {'from_currency': 'USD', 'to_currency': 'THB'}
        )
        state['fx_usd_thb'] = fx_rate['rate']
    except MCPServerError:
        logger.warning("Failed to fetch FX rate, using default")
        state['fx_usd_thb'] = 33.5  # Default fallback

    return state
```

---

## Cost Analysis

### Monthly Cost Estimates (Production)

| MCP Server | Tier | Monthly Cost | Requests/Day | Notes |
|------------|------|--------------|--------------|-------|
| **Alpaca** | Free | $0 | Unlimited | 15-min delay on options |
| **Alpaca** | Pro | $99 | Unlimited | Real-time everything |
| **SEC EDGAR** | Free | $0 | ~500 | Public API, rate limited |
| **Alpha Vantage** | Free | $0 | 500 total | 25/day for some endpoints |
| **Alpha Vantage** | Premium | $49.99 | 75,000 | 1200/min rate limit |
| **QuantConnect** | Free | $0 | Limited | 1-year backtest history |
| **QuantConnect** | Premium | $20 | Unlimited | Full history, live trading |
| **Financial Markets** | Free | $0 | Self-hosted | Open source |
| **Portfolio Manager** | Free | $0 | Self-hosted | Open source |
| **MonteWalk** | Unknown | TBD | Unknown | Likely paid, pricing unclear |

**Recommended Starting Configuration (Free Tier):**
- Alpaca: Free tier (delay acceptable for most use cases)
- SEC EDGAR: Free (public data)
- Alpha Vantage: Free tier (500 calls/day = ~50 reports if using 10 calls/report)
- QuantConnect: Free tier (limited backtesting)
- Self-hosted: Financial Markets, Portfolio Manager

**Total: $0/month (within free tier limits)**

**Scaling to Paid (100 reports/day):**
- Alpaca Pro: $99 (real-time options data)
- Alpha Vantage Premium: $49.99 (10,000 calls/day)
- QuantConnect Premium: $20 (unlimited backtests)
- MonteWalk: Estimate $50/month

**Total: ~$220/month (premium tier, 100 reports/day)**

---

## Risk Mitigation

### 1. MCP Server Downtime
**Risk**: MCP server outage breaks report generation
**Mitigation**:
- Implement fallback chain (MCP → yfinance → S3 cache)
- Cache MCP responses (10-K filings, historical data)
- Circuit breaker pattern (auto-disable failing MCPs)
- Degraded mode: Generate reports without MCP enhancements

### 2. Rate Limiting
**Risk**: Exceed free tier limits, reports fail
**Mitigation**:
- Monitor API usage via CloudWatch metrics
- Implement request throttling (max N calls/minute)
- Cache aggressively (DynamoDB + S3)
- Upgrade to paid tiers when approaching limits

### 3. Cost Overruns
**Risk**: Unexpected API charges
**Mitigation**:
- Set CloudWatch billing alarms ($50, $100, $200 thresholds)
- Implement daily budget quotas per MCP server
- Auto-disable paid MCPs if budget exceeded
- Monthly cost review and optimization

### 4. Data Quality Issues
**Risk**: MCP returns incorrect/stale data
**Mitigation**:
- Validate MCP responses (schema checks, sanity tests)
- Cross-reference multiple sources (Alpaca vs yfinance)
- Add data freshness timestamps
- User feedback loop (report quality ratings)

### 5. Privacy/Compliance
**Risk**: MCP servers log user queries, data leakage
**Mitigation**:
- Review MCP server privacy policies
- Prefer self-hosted MCPs where possible
- Anonymize user identifiers in MCP calls
- GDPR compliance audit for EU users

---

## Success Metrics

### Quantitative Metrics
- **Report Quality Score**: Before/after MCP integration (baseline: 7.2/10)
- **Data Freshness**: Average data age (target: <15 minutes vs current 1-hour)
- **Report Completeness**: % reports with fundamental data (target: 90% vs current 40%)
- **Backtesting Coverage**: % reports with strategy validation (target: 80% from 0%)
- **Cost Per Report**: API costs per generated report (target: <$0.10)

### Qualitative Metrics
- **User Feedback**: Post-report ratings (target: 4.5/5 stars)
- **Feature Usage**: % users engaging with enhanced sections
- **Churn Reduction**: Premium tier retention improvement
- **Support Tickets**: Reduction in "data inaccurate" complaints

### Technical Metrics
- **MCP Uptime**: Availability of MCP integrations (target: 99.5%)
- **Fallback Frequency**: How often fallback chain is used (target: <5%)
- **Latency Impact**: Report generation time increase (acceptable: +2s)
- **Error Rate**: MCP-related errors (target: <0.1% of reports)

---

## References

### Official Documentation
- [Alpaca Trading API Docs](https://alpaca.markets/docs/)
- [SEC EDGAR Developer Resources](https://www.sec.gov/developer)
- [Alpha Vantage API Documentation](https://www.alphavantage.co/documentation/)
- [QuantConnect Documentation](https://www.quantconnect.com/docs/)

### MCP Server Repositories
- [Alpaca MCP Server](https://github.com/alpacahq/alpaca-mcp-server)
- [SEC EDGAR MCP](https://github.com/stefanoamorelli/sec-edgar-mcp)
- [Alpha Vantage MCP](https://mcp.alphavantage.co/)
- [QuantConnect MCP](https://github.com/taylorwilsdon/quantconnect-mcp)
- [Financial Markets MCP](https://lobehub.com/mcp/olonok69-mcp_financial_markets_analysis_tool)
- [Portfolio Manager MCP](https://github.com/ikhyunAn/MCP_InvestmentPortfolio)
- [MonteWalk MCP](https://www.pulsemcp.com/servers/n-lia-montewalk)

### MCP Protocol
- [Model Context Protocol Specification](https://github.com/modelcontextprotocol/specification)
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)
- [MCP Servers Directory](https://mcpservers.org/)

### Project-Specific
- [MCP Infrastructure Plan](../../.claude/plans/shimmering-munching-knuth.md) - Infrastructure MCPs for dev workflow
- [Code Style Guide](../CODE_STYLE.md#workflow-state-management-patterns) - LangGraph patterns
- [Deployment Guide](../deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) - CI/CD integration

---

## Appendix: MCP Call Examples

### Example 1: Fetch Real-Time Market Data (Alpaca)

```python
# Get latest price bars with volume
bars = await mcp_client.call_tool(
    'alpaca',
    'get_latest_bars',
    {
        'symbol': 'NVDA',
        'timeframe': '1Day',
        'limit': 365  # 1 year of daily bars
    }
)

# Response structure:
{
    'bars': [
        {
            'timestamp': '2024-12-09T00:00:00Z',
            'open': 494.12,
            'high': 498.35,
            'low': 492.80,
            'close': 495.23,
            'volume': 45823100
        },
        # ... 364 more days
    ]
}
```

### Example 2: Fetch SEC 10-Q Filing (SEC EDGAR)

```python
# Get latest quarterly report
filing = await mcp_client.call_tool(
    'sec_edgar',
    'get_latest_filing',
    {
        'ticker': 'NVDA',
        'form_type': '10-Q',
        'include_xbrl': True
    }
)

# Response structure:
{
    'filing_date': '2024-11-20',
    'period_end': '2024-10-31',
    'url': 'https://www.sec.gov/Archives/edgar/data/1045810/...',
    'xbrl': {
        'RevenueFromContractWithCustomerExcludingAssessedTax': 30800000000,
        'OperatingIncomeLoss': 14500000000,
        'NetIncomeLoss': 12100000000,
        # ... hundreds of other XBRL tags
    },
    'text_sections': {
        'risk_factors': '... supply chain constraints ...',
        'md_and_a': '... management discussion ...'
    }
}
```

### Example 3: Backtest Trading Strategy (QuantConnect)

```python
# Backtest RSI mean reversion strategy
backtest = await mcp_client.call_tool(
    'quantconnect',
    'run_backtest',
    {
        'algorithm': 'RSIMeanReversion',
        'symbol': 'DBS.SI',  # Singapore-listed DBS
        'start_date': '2020-01-01',
        'end_date': '2024-12-31',
        'parameters': {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'position_size': 0.1  # 10% of portfolio per trade
        }
    }
)

# Response structure:
{
    'total_return': 0.152,  # 15.2% over period
    'annual_return': 0.038,  # 3.8% annualized
    'sharpe_ratio': 1.4,
    'sortino_ratio': 2.1,
    'max_drawdown': -0.12,  # -12%
    'win_rate': 0.62,  # 62% winning trades
    'total_trades': 87,
    'avg_win': 0.042,  # 4.2% average gain
    'avg_loss': -0.028,  # -2.8% average loss
    'profit_factor': 2.1  # (total wins / total losses)
}
```

---

**Document Status**: ✅ Research Complete
**Next Action**: Implement Phase 1 (Core Financial MCPs) after infrastructure setup completes
**Owner**: Development Team
**Last Updated**: 2025-12-10
