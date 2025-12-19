# Daily Report LINE Bot for Financial Tickers

LINE Bot สำหรับรายงานวิเคราะห์หุ้นแบบครอบคลุมในภาษาไทย สำหรับ Day Traders และนักลงทุน

## Features

### LINE Bot (Legacy)
- 📊 การวิเคราะห์ทางเทคนิค (Technical Analysis)
- 💼 การวิเคราะห์พื้นฐาน (Fundamental Analysis)
- 🤖 AI-Powered Thai Language Reports
- Chat-based interface via LINE Messaging API

### Telegram Mini App (Active Development)
- 📈 Interactive prediction market UI with charts
- 🎯 Market movers rankings (top gainers/losers, volume surge)
- 💼 Comprehensive ticker analysis with stance indicators
- 📊 Professional chart visualization (price history + projections)
- ⭐ User watchlist management
- 🔍 Fast ticker search and autocomplete
- Web-based dashboard via Telegram WebApp

## Architecture

```
User (LINE) -> API Gateway -> Lambda Function
                                |
                                v
                         [LangGraph Agent]
                                |
                    +-----------+-----------+
                    |           |           |
                 YFinance    OpenAI    Qdrant
                 (Data)      (LLM)    (Vector DB)
                                |
                            SQLite
                          (Cache DB)
```

## Tech Stack

- **Python 3.11+**
- **YFinance**: ดึงข้อมูลหุ้นจาก Yahoo Finance
- **LangGraph**: Agent orchestration และ workflow
- **LangChain + OpenRouter**: สร้างรายงานภาษาไทย
- **SQLite**: Cache สำหรับข้อมูลหุ้นและรายงาน
- **Aurora MySQL**: Primary data store for reports (precomputed nightly via Step Function). User APIs read from Aurora only; no external API fallback on miss.
- **AWS Lambda**: Serverless deployment

## Project Structure

```
dr-daily-report_telegram/
├── src/
│   ├── integrations/          # LINE bot, Lambda handlers
│   ├── agent.py               # LangGraph agent logic
│   ├── workflow/              # Workflow nodes
│   ├── data/                  # Data fetching, caching, Aurora
│   ├── analysis/              # Technical, comparative analysis
│   ├── report/                # Report generation
│   ├── api/                   # Telegram Mini App API (FastAPI)
│   └── scoring/               # Quality scoring
├── frontend/twinbar/          # Telegram Mini App UI (React)
├── terraform/                 # Infrastructure as Code
├── tests/                     # Test suite
├── justfile                   # Intent-based command recipes
└── README.md                  # This file
```

See `.claude/CLAUDE.md` for complete architecture documentation.

## Setup

### 1. Install DR CLI (Recommended)

The DR CLI provides a unified interface for all repository operations with excellent discoverability and help system.

```bash
# Install the CLI in editable mode
pip install -e .

# Verify installation
dr --help

# Or use the justfile
just setup
```

**Quick Start:**
```bash
# Start development server
just dev

# Run tests
just test-changes

# Deploy to production
just ship-it
```

See [CLI Documentation](docs/cli.md) for complete guide.

### 2. Install Dependencies (Alternative)

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

The CLI integrates with Doppler via the `--doppler` flag:

```bash
# Run commands with doppler environment
dr --doppler dev server
dr --doppler test
```

Manual doppler usage:
```bash
doppler run --project dr-daily-report-telegram --config dev --command env
```

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key
- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API access token
- `LINE_CHANNEL_SECRET`: LINE channel secret

Check environment status:
```bash
dr check env
```

### 4. Setup MCP Tools (Optional but Recommended)

Enable AWS MCP tools in Cursor IDE for enhanced AWS integration:

```bash
just setup-mcp
```

Or manually:
```bash
# Windows
.\scripts\setup-mcp.ps1

# Linux/macOS
./scripts/setup-mcp.sh
```

See [MCP Setup Guide](docs/MCP_SETUP.md) for detailed instructions.

### 5. Local Testing

Using the CLI:
```bash
dr dev server           # Start Flask server
dr --doppler dev server # With environment variables
```

Or using justfile:
```bash
just dev
```

Legacy method:
```bash
python lambda_handler.py
```

## Deployment

### Using the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh
```

This will create `lambda_deployment.zip` ready for upload to AWS Lambda.

### Manual AWS Lambda Setup:

1. Create new Lambda function
2. Upload `lambda_deployment.zip`
3. Set handler: `lambda_handler.lambda_handler`
4. Configure environment variables:
   - `OPENAI_API_KEY`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
5. Set timeout: 60 seconds (minimum)
6. Set memory: 512 MB (minimum)
7. Add API Gateway trigger
8. Configure LINE webhook URL to API Gateway endpoint

## Usage

### LINE Bot Commands

Simply send the ticker symbol to the bot:

```
DBS19
```

The bot will respond with a comprehensive Thai language report including:
- ภาพรวมของหุ้น
- การวิเคราะห์ทางเทคนิค
- การวิเคราะห์พื้นฐาน
- ความเห็นนักวิเคราะห์
- สรุปและข้อเสนอแนะ

### Supported Tickers

See `tickers.csv` for the full list of supported tickers. Examples:
- DBS19 -> D05.SI (DBS Bank)
- UOB19 -> U11.SI (UOB Bank)
- TENCENT19 -> 0700.HK (Tencent)
- NINTENDO19 -> 7974.T (Nintendo)

## Development

### DR CLI - Two-Layer System

The repository uses a two-layer command interface:

**Justfile (Intent Layer)**: Intent-based recipes that describe WHEN and WHY to run commands
- `just dev` - Start development server
- `just pre-commit` - Run before committing
- `just ship-it` - Complete deployment workflow

**DR CLI (Syntax Layer)**: Clean, explicit syntax with comprehensive help
- `dr dev server` - Run development server
- `dr test` - Run all tests
- `dr build` - Create Lambda package

This design makes commands:
- **Discoverable**: `dr --help` and `dr <command> --help` show all options
- **Explicit**: Clear syntax that both humans and AI agents can use
- **Composable**: Commands can be chained for custom workflows

See [CLI Documentation](docs/cli.md) for complete reference.

### Common Development Workflows

**First time setup:**
```bash
just setup              # Install dependencies
just dev                # Start server
```

**Daily development:**
```bash
just daily              # Pull, setup, test
just test-changes       # Test recent changes
just pre-commit         # Before committing
```

**Testing:**
```bash
dr test                 # All tests
dr test line follow     # LINE bot tests
dr test file test_agent.py  # Specific file
just test-ticker AAPL   # Integration test
```

**Deployment:**
```bash
just pre-deploy         # Pre-deployment checks
just ship-it            # Build and deploy
```

### Adding New Tickers

1. Update `tickers.csv` with new ticker mappings
2. Format: `SYMBOL,YAHOO_TICKER`

### Modifying Analysis

- **Technical Indicators**: Edit `technical_analysis.py`
- **Report Template**: Edit prompt in `agent.py -> generate_report()`
- **Data Sources**: Modify `data_fetcher.py`

### Database Schema

**ticker_data**: Price and fundamental data
**technical_indicators**: Calculated technical indicators
**reports**: Generated reports cache

## Cost Considerations

- **AWS Lambda**: Pay per invocation (~$0.20 per million requests)
- **OpenAI API**: ~$0.001 per report (GPT-4 Mini)
- **YFinance**: Free
- **Qdrant**: In-memory mode (free)

## Performance

- Cold start: ~3-5 seconds
- Warm execution: ~2-10 seconds (depending on data freshness)
- Report generation: ~2-5 seconds
- Caching: Reports are cached in SQLite for faster repeated queries

## Limitations

- Yahoo Finance data availability varies by market
- Some tickers may have incomplete fundamental data
- Reports are in Thai language only
- Rate limits apply to YFinance and OpenAI APIs

## Troubleshooting

### Bot not responding
- Check Lambda logs in CloudWatch
- Verify environment variables are set
- Check LINE webhook URL configuration

### Missing data for ticker
- Verify ticker symbol in `tickers.csv`
- Check if Yahoo Finance has data for the ticker
- Try the Yahoo ticker directly on finance.yahoo.com

### Timeout errors
- Increase Lambda timeout setting
- Check if YFinance is responsive
- Consider caching strategy

## Future Enhancements

- [x] Historical trend charts ✅ (See Chart Visualization feature)
- [ ] Sector comparison analysis
- [ ] Multi-ticker comparison charts
- [ ] Alert notifications
- [ ] Portfolio tracking
- [ ] Backtesting capabilities
- [ ] Interactive charts (Plotly/Bokeh)

## License

MIT License

## Support

For issues or questions, please create an issue in the repository.
