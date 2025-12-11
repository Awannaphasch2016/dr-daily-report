# MCP Local Testing Guide

Guide for testing MCP (Model Context Protocol) server integration locally before deployment.

---

## Overview

This guide covers:
1. **Running MCP server locally** - FastAPI server mimicking Lambda Function URL
2. **Testing MCP integration** - Verifying SEC filing data appears in generated reports
3. **Running test suites** - Unit, integration, and E2E tests

---

## Prerequisites

```bash
# Install dependencies
just setup

# Set environment variables (REQUIRED for SEC API)
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"
# Or use Terraform format:
# export SEC_EDGAR_USER_AGENT="dr-daily-report/1.0 (contact: support@dr-daily-report.com)"

# Optional - defaults to localhost
export SEC_EDGAR_MCP_URL="http://localhost:8002"
export OPENROUTER_API_KEY="your-key-here"  # Required for E2E tests
```

### SEC EDGAR API Requirements

**⚠️ IMPORTANT:** SEC EDGAR API requires a User-Agent header identifying your application.

**User-Agent Format:**
- Format: `"AppName (contact@email.com)"` or `"AppName contact@email.com"`
- Must identify app/organization and contact email
- SEC uses this for rate limiting and abuse prevention

**Rate Limiting:**
- ~10 requests/second
- 403/404 errors usually mean User-Agent missing or SEC blocking

**Why This Matters:**
- Without proper User-Agent, SEC API returns 404 (not found)
- MCP server reads `SEC_EDGAR_USER_AGENT` from environment
- Must be set **before** starting MCP server

---

## Quick Start

### 1. Automated Setup and Test (Recommended)

**Use the automated script for complete setup and validation:**

```bash
# Set User-Agent (REQUIRED)
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Run full test suite
./scripts/setup_and_test_mcp.sh

# Or skip report generation test (faster)
./scripts/setup_and_test_mcp.sh --skip-report-test
```

**What this does:**
1. ✅ Tests SEC EDGAR API connectivity
2. ✅ Starts MCP server with proper environment
3. ✅ Tests MCP server endpoints (tools/list, tools/call)
4. ✅ Optionally tests report generation with MCP

### 2. Manual Start Local MCP Server

**Option A: Using helper script (recommended)**
```bash
# Set User-Agent (REQUIRED)
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Start server
./scripts/start_mcp_server_local.sh

# Or with custom port
./scripts/start_mcp_server_local.sh --port 8000
```

**Option B: Direct Python script**
```bash
# Set User-Agent (REQUIRED)
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Start FastAPI server on http://localhost:8002
python scripts/run_mcp_server_local.py

# Or with custom port
python scripts/run_mcp_server_local.py --port 8001
```

**What this does:**
- Runs `src/mcp_servers/sec_edgar_handler.py` Lambda handler locally
- Converts FastAPI requests ↔ Lambda events/responses
- Mimics AWS Lambda Function URL behavior
- Reads `SEC_EDGAR_USER_AGENT` from environment

**Verify server is running:**
```bash
curl http://localhost:8002/health
# Should return: {"status": "healthy", "service": "local-mcp-server"}
```

### 3. Test MCP Integration

**Option A: Using test script (recommended)**
```bash
# Test with local MCP server
python scripts/test_mcp_local.py --ticker AAPL --mcp-url http://localhost:8000/mcp

# Test with deployed MCP server (dev environment)
python scripts/test_mcp_local.py --ticker AAPL --mcp-url $SEC_EDGAR_MCP_URL

# Test multi-stage strategy
python scripts/test_mcp_local.py --ticker AAPL --strategy multi-stage
```

**Option B: Using pytest**
```bash
# Run all MCP tests
pytest tests/integration/test_mcp_sec_edgar.py -v
pytest tests/integration/test_mcp_report_generation.py -v
pytest tests/integration/test_mcp_e2e_report.py -v

# Run specific test
pytest tests/integration/test_mcp_e2e_report.py::test_generated_report_contains_sec_filing_info -v
```

---

## Test Suites

### Tier 1: Unit Tests (Context Builder)

**File:** `tests/shared/test_mcp_context_integration.py`

**Purpose:** Verify `ContextBuilder` correctly formats SEC filing data into LLM prompt.

**Run:**
```bash
pytest tests/shared/test_mcp_context_integration.py -v
```

**Key Tests:**
- `test_context_builder_includes_sec_filing_section` - Verifies SEC section appears in context
- `test_format_sec_filing_section_includes_all_fields` - Tests formatting of form type, date, XBRL, risk factors
- `test_context_builder_excludes_sec_section_when_data_empty` - Ensures graceful handling of missing data

**Sabotage Verification:**
```bash
# Temporarily break ContextBuilder, verify test fails
pytest tests/shared/test_mcp_context_integration.py::TestSabotageVerification -v
```

---

### Tier 2: Integration Tests (Workflow)

**File:** `tests/integration/test_mcp_report_generation.py`

**Purpose:** Verify SEC filing data flows from workflow node → context builder → LLM prompt.

**Run:**
```bash
pytest tests/integration/test_mcp_report_generation.py -v
```

**Key Tests:**
- `test_workflow_fetches_sec_filing_via_mcp` - Mocks `MCPClient`, verifies `fetch_sec_filing` node calls MCP
- `test_context_builder_receives_sec_filing_data` - Mocks `ContextBuilder`, verifies it receives SEC data
- `test_llm_prompt_contains_sec_filing_data` - Mocks LLM, verifies prompt includes SEC filing info
- `test_workflow_handles_mcp_unavailable_gracefully` - Verifies graceful degradation when MCP is down

**Mocking Strategy:**
- `MCPClient` is mocked to return sample SEC filing data
- `ContextBuilder` is mocked to capture arguments
- `ChatOpenAI` is mocked to capture prompt text

---

### Tier 3: E2E Tests (Real LLM)

**File:** `tests/integration/test_mcp_e2e_report.py`

**Purpose:** Verify SEC filing data appears in **actual generated report text** using real LLM.

**Prerequisites:**
```bash
export SEC_EDGAR_MCP_URL="http://localhost:8000/mcp"  # Or deployed URL
export OPENROUTER_API_KEY="your-key-here"  # Required!
```

**Run:**
```bash
# Run with local MCP server
pytest tests/integration/test_mcp_e2e_report.py -v

# Run with deployed MCP server
SEC_EDGAR_MCP_URL=$SEC_EDGAR_MCP_URL pytest tests/integration/test_mcp_e2e_report.py -v
```

**Key Tests:**
- `test_generated_report_contains_sec_filing_info` - Generates report for 'AAPL', asserts SEC keywords appear
- `test_report_missing_sec_data_when_mcp_unavailable` - Temporarily disables MCP, verifies graceful degradation

**What Gets Tested:**
- Real `TickerAnalysisAgent` initialization
- Real MCP server HTTP calls (local or deployed)
- Real LLM (OpenRouter) report generation
- Assertions on **actual report text** (not mocked)

**Cost:** ~$0.01-0.05 per test run (LLM API calls)

---

## Local MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Server (scripts/run_mcp_server_local.py)          │
│                                                             │
│  POST /mcp                                                  │
│    ↓                                                        │
│  convert_fastapi_to_lambda_event()                          │
│    ↓                                                        │
│  Lambda Handler (src/mcp_servers/sec_edgar_handler.py)     │
│    ↓                                                        │
│  SECEdgarClient.fetch_latest_filing()                      │
│    ↓                                                        │
│  convert_lambda_to_fastapi_response()                      │
│    ↓                                                        │
│  JSON-RPC 2.0 Response                                     │
└─────────────────────────────────────────────────────────────┘
```

**Request Flow:**
1. FastAPI receives POST request to `/mcp`
2. Converts FastAPI `Request` → Lambda `event` dict
3. Calls Lambda handler (same code as deployed)
4. Converts Lambda `response` dict → FastAPI `Response`
5. Returns JSON-RPC 2.0 response

**Why This Works:**
- Same Lambda handler code runs locally and in AWS
- Request/response conversion bridges FastAPI ↔ Lambda formats
- No code changes needed for local vs deployed testing

---

## Testing Workflow

### Development Workflow

```bash
# 1. Start local MCP server (terminal 1)
python scripts/run_mcp_server_local.py

# 2. Run unit tests (terminal 2)
pytest tests/shared/test_mcp_context_integration.py -v

# 3. Run integration tests (terminal 2)
pytest tests/integration/test_mcp_report_generation.py -v

# 4. Run E2E test (terminal 2) - requires OPENROUTER_API_KEY
pytest tests/integration/test_mcp_e2e_report.py::test_generated_report_contains_sec_filing_info -v

# 5. Manual test with CLI (terminal 2)
python scripts/test_mcp_local.py --ticker AAPL --mcp-url http://localhost:8000/mcp
```

### CI/CD Workflow

```bash
# Pre-deployment: Run all tests
pytest tests/shared/test_mcp_context_integration.py -v
pytest tests/integration/test_mcp_report_generation.py -v

# Post-deployment: Run E2E with deployed MCP server
SEC_EDGAR_MCP_URL=$DEPLOYED_URL pytest tests/integration/test_mcp_e2e_report.py -v
```

---

## Troubleshooting

### MCP Server Won't Start

**Error:** `ModuleNotFoundError: No module named 'src'`
```bash
# Solution: Run from project root
cd /home/anak/dev/dr-daily-report_report_generation
python scripts/run_mcp_server_local.py
```

**Error:** `Address already in use`
```bash
# Solution: Use different port
python scripts/run_mcp_server_local.py --port 8001
```

**Error:** `⚠️ SEC_EDGAR_USER_AGENT not set`
```bash
# Solution: Set User-Agent before starting server
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"
python scripts/run_mcp_server_local.py
```

**Error:** SEC API returns 403/404
```bash
# Cause: Missing or invalid User-Agent header
# Solution: Verify User-Agent format
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Test SEC API directly
curl -H "User-Agent: DR-Daily-Report-ResearchBot (anak@yourcompany.com)" \
  https://data.sec.gov/files/company_tickers.json | head -50

# Should return JSON with company tickers
# If 403/404: Check User-Agent format or SEC rate limiting
```

### E2E Tests Fail

**Error:** `SEC_EDGAR_MCP_URL not set`
```bash
# Solution: Set environment variable (use base URL, not /mcp endpoint)
export SEC_EDGAR_MCP_URL="http://localhost:8002"
pytest tests/integration/test_mcp_e2e_report.py -v
```

**Error:** `SEC_EDGAR_USER_AGENT not set`
```bash
# Solution: Set User-Agent before running tests
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"
export SEC_EDGAR_MCP_URL="http://localhost:8002"
pytest tests/integration/test_mcp_e2e_report.py -v
```

**Error:** `OPENROUTER_API_KEY not set`
```bash
# Solution: Set API key (required for real LLM calls)
export OPENROUTER_API_KEY="your-key-here"
pytest tests/integration/test_mcp_e2e_report.py -v
```

**Error:** `AssertionError: Report does not contain SEC filing keywords`
```bash
# Possible causes:
# 1. MCP server not running (check http://localhost:8002/health)
# 2. SEC_EDGAR_USER_AGENT not set (SEC API returns 404)
# 3. SEC EDGAR API unavailable (check SEC EDGAR website)
# 4. Ticker has no SEC filings (try 'AAPL' instead of 'NVDA19')
# 5. LLM didn't include SEC info (check report text manually)

# Debug steps:
# 1. Test SEC API directly
curl -H "User-Agent: DR-Daily-Report-ResearchBot (anak@yourcompany.com)" \
  https://data.sec.gov/files/company_tickers.json | head -50

# 2. Test MCP server directly
curl -X POST http://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'

# 3. Check MCP server logs
tail -f /tmp/mcp_server.log
```

### Integration Tests Fail

**Error:** `Mock assertion failed`
```bash
# Solution: Check mock setup matches actual code
# - Verify MCPClient method names match
# - Verify ContextBuilder method signatures match
# - Check mock return values match expected types
```

---

## Test Data

### Sample SEC Filing Data Structure

```python
{
    "filing_date": "2025-01-15",
    "form_type": "10-K",
    "xbrl_metrics": {
        "total_revenue": 394328000000,
        "net_income": 99803000000,
        "total_assets": 352755000000
    },
    "risk_factors": [
        "Competition in technology industry",
        "Regulatory changes",
        "Supply chain disruptions"
    ]
}
```

### Test Tickers

**US Tickers (have SEC filings):**
- `AAPL` - Apple Inc. (always has filings)
- `MSFT` - Microsoft Corporation
- `GOOGL` - Alphabet Inc.

**Thai Tickers (no SEC filings):**
- `NVDA19` - NVDR (Thai ETF)
- `DBS19` - DBS SET50 ETF
- `MWG19` - Minor Group

**Note:** E2E tests use `AAPL` because it reliably has SEC filings.

---

## Advanced Usage

### Custom MCP Server Port

```bash
# Start server on custom port
python scripts/run_mcp_server_local.py --port 9000

# Test with custom port
python scripts/test_mcp_local.py --ticker AAPL --mcp-url http://localhost:9000/mcp
```

### Debugging MCP Requests

**Enable verbose logging:**
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Run test script
python scripts/test_mcp_local.py --ticker AAPL --mcp-url http://localhost:8000/mcp
```

**Inspect HTTP requests:**
```bash
# Use curl to test MCP server directly
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

### Testing Multiple Tickers

```bash
# Test multiple tickers in sequence
for ticker in AAPL MSFT GOOGL; do
  echo "Testing $ticker..."
  python scripts/test_mcp_local.py --ticker $ticker --mcp-url http://localhost:8000/mcp
done
```

---

## SEC EDGAR API Setup

### User-Agent Format Requirements

SEC EDGAR API requires a User-Agent header identifying your application:

**Required Format:**
- `"AppName (contact@email.com)"` - Recommended format
- `"AppName contact@email.com"` - Alternative format

**Examples:**
```bash
# Recommended format
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Terraform format (used in AWS deployment)
export SEC_EDGAR_USER_AGENT="dr-daily-report/1.0 (contact: support@dr-daily-report.com)"
```

**Why This Matters:**
- SEC uses User-Agent for rate limiting and abuse prevention
- Missing User-Agent → 404 (not found) errors
- Invalid format → 403 (forbidden) errors
- Must be set **before** starting MCP server

### Testing SEC API Connectivity

**Test SEC API directly:**
```bash
# Set User-Agent
export SEC_EDGAR_USER_AGENT="DR-Daily-Report-ResearchBot (anak@yourcompany.com)"

# Test connectivity
curl -H "User-Agent: $SEC_EDGAR_USER_AGENT" \
  https://data.sec.gov/files/company_tickers.json | head -50

# Expected: JSON response with company tickers
# If 403/404: Check User-Agent format or SEC rate limiting
```

**Rate Limiting:**
- ~10 requests/second
- If rate limited, wait a few seconds and retry
- 403 errors may indicate IP ban (rare)

### MCP Server Environment Variables

**Required:**
- `SEC_EDGAR_USER_AGENT` - User-Agent string for SEC API

**Optional:**
- `MCP_SERVER_PORT` - Port to run server on (default: 8002)
- `MCP_SERVER_HOST` - Host to bind to (default: 127.0.0.1)
- `SEC_EDGAR_MCP_URL` - MCP server URL (for clients, use base URL: `http://localhost:8002`)

**Note:** MCP client appends `/mcp` to the base URL automatically.

## See Also

- [MCP Implementation Status](MCP_IMPLEMENTATION_STATUS.md) - Overall MCP integration status
- [MCP Deployment Guide](MCP_DEPLOYMENT_GUIDE.md) - Deploying MCP servers to AWS
- [Testing Guide](../TESTING_GUIDE.md) - General testing patterns and principles
- [TDD Principles](../.cursor/rules/principles.mdc#testing-guidelines) - Test-driven development guidelines
