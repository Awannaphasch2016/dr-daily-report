# MCP Infrastructure Proof of Concept Implementation Plan

**Purpose**: Step-by-step guide to implement MCP infrastructure proof of concept  
**Timeline**: 2-3 weeks  
**Status**: Planning  
**Created**: 2025-01-15

---

## Overview

This document provides a concrete implementation plan for building a proof of concept MCP infrastructure that integrates with our existing LangGraph agent.

**Goal**: Deploy a working MCP gateway with at least one MCP server (SEC EDGAR) and verify integration with LangGraph workflow.

---

## Prerequisites

### AWS Account Setup
- [ ] AWS account with Bedrock access (if using AgentCore Gateway)
- [ ] IAM permissions for Lambda, SQS, Secrets Manager, X-Ray
- [ ] Region: `ap-southeast-1` (Singapore)

### Development Environment
- [ ] Python 3.11+ installed
- [ ] AWS CLI configured (`aws configure`)
- [ ] Terraform installed (for infrastructure)
- [ ] Docker installed (for Lambda container images)

### API Keys
- [ ] Alpaca API key (free tier) - https://alpaca.markets/
- [ ] (Optional) Alpha Vantage API key - https://www.alphavantage.co/

---

## Phase 1: Deploy SEC EDGAR MCP Server (Week 1)

### Step 1.1: Create Lambda Function

**Objective**: Deploy SEC EDGAR MCP server as Lambda function

**Implementation:**

1. **Create Lambda deployment package:**
   ```bash
   mkdir -p mcp_servers/sec_edgar
   cd mcp_servers/sec_edgar
   
   # Clone or copy SEC EDGAR MCP server code
   git clone https://github.com/stefanoamorelli/sec-edgar-mcp.git .
   
   # Install dependencies
   pip install -r requirements.txt -t .
   
   # Create deployment package
   zip -r sec-edgar-mcp.zip .
   ```

2. **Create Lambda function via Terraform:**
   ```hcl
   # terraform/mcp_servers/sec_edgar.tf
   resource "aws_lambda_function" "sec_edgar_mcp" {
     function_name = "${var.project_name}-mcp-sec-edgar-${var.environment}"
     role          = aws_iam_role.mcp_server_lambda.arn
     handler       = "index.handler"
     runtime       = "python3.11"
     timeout       = 30
     memory_size   = 256
     
     filename         = "sec-edgar-mcp.zip"
     source_code_hash = filebase64sha256("sec-edgar-mcp.zip")
     
     environment {
       variables = {
         MCP_SERVER_NAME = "sec-edgar"
       }
     }
     
     tracing_config {
       mode = "Active"  # Enable X-Ray
     }
     
     tags = {
       App         = "telegram-api"
       Component   = "mcp-server"
       MCP_Server  = "sec-edgar"
     }
   }
   
   resource "aws_lambda_function_url" "sec_edgar_mcp" {
     function_name      = aws_lambda_function.sec_edgar_mcp.function_name
     authorization_type = "AWS_IAM"
     
     cors {
       allow_credentials = true
       allow_origins     = ["*"]
       allow_methods     = ["POST"]
       allow_headers     = ["*"]
       max_age           = 300
     }
   }
   ```

3. **Deploy:**
   ```bash
   cd terraform
   terraform init
   terraform plan -var-file=envs/dev/terraform.tfvars
   terraform apply -var-file=envs/dev/terraform.tfvars
   ```

**Success Criteria:**
- ✅ Lambda function deployed successfully
- ✅ Function URL accessible
- ✅ Can invoke MCP endpoint via HTTP POST

**Testing:**
```bash
# Test SEC EDGAR MCP server
curl -X POST https://<function-url>.lambda-url.ap-southeast-1.on.aws/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_latest_filing",
      "arguments": {
        "ticker": "NVDA",
        "form_type": "10-Q"
      }
    },
    "id": 1
  }'
```

---

### Step 1.2: Test SEC EDGAR MCP Server

**Objective**: Verify SEC EDGAR MCP server works correctly

**Test Cases:**

1. **Get Latest Filing:**
   ```python
   # tests/mcp/test_sec_edgar.py
   import pytest
   import requests
   import os
   
   @pytest.mark.integration
   def test_get_latest_filing():
       """Test SEC EDGAR MCP server - get latest 10-Q filing"""
       function_url = os.getenv('SEC_EDGAR_MCP_URL')
       
       response = requests.post(
           f"{function_url}/mcp",
           json={
               "jsonrpc": "2.0",
               "method": "tools/call",
               "params": {
                   "name": "get_latest_filing",
                   "arguments": {
                       "ticker": "NVDA",
                       "form_type": "10-Q"
                   }
               },
               "id": 1
           },
           timeout=30
       )
       
       assert response.status_code == 200
       data = response.json()
       assert "result" in data
       assert "filing_date" in data["result"]
       assert "xbrl" in data["result"]
   ```

2. **List Available Tools:**
   ```python
   @pytest.mark.integration
   def test_list_tools():
       """Test SEC EDGAR MCP server - list available tools"""
       function_url = os.getenv('SEC_EDGAR_MCP_URL')
       
       response = requests.post(
           f"{function_url}/mcp",
           json={
               "jsonrpc": "2.0",
               "method": "tools/list",
               "id": 1
           },
           timeout=10
       )
       
       assert response.status_code == 200
       data = response.json()
       assert "result" in data
       assert "tools" in data["result"]
       assert len(data["result"]["tools"]) > 0
   ```

**Success Criteria:**
- ✅ All test cases pass
- ✅ SEC EDGAR API accessible (free, no API key)
- ✅ Response format matches MCP protocol

---

## Phase 2: Integrate with LangGraph (Week 2)

### Step 2.1: Create MCP Client Wrapper

**Objective**: Create Python client for calling MCP servers

**Implementation:**

```python
# src/integrations/mcp_client.py
"""
MCP Client for calling MCP servers from LangGraph workflow.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for calling MCP servers via HTTP."""
    
    def __init__(self):
        """Initialize MCP client with server URLs from environment."""
        self.servers = {
            'sec_edgar': os.getenv('SEC_EDGAR_MCP_URL'),
            'alpaca': os.getenv('ALPACA_MCP_URL'),
            'financial_markets': os.getenv('FINANCIAL_MARKETS_MCP_URL'),
        }
        self.timeout = int(os.getenv('MCP_TIMEOUT', '30'))
    
    def call_tool(
        self,
        server: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call MCP server tool.
        
        Args:
            server: MCP server name ('sec_edgar', 'alpaca', etc.)
            tool_name: Tool name to call
            arguments: Tool arguments
            timeout: Request timeout (default: self.timeout)
            
        Returns:
            Tool response data
            
        Raises:
            ValueError: If server not found
            requests.RequestException: If HTTP request fails
        """
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")
        
        server_url = self.servers[server]
        if not server_url:
            raise ValueError(f"MCP server URL not configured: {server}")
        
        request_timeout = timeout or self.timeout
        
        logger.info(f"Calling MCP tool: {server}.{tool_name}")
        
        try:
            response = requests.post(
                f"{server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                },
                timeout=request_timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                raise ValueError(f"MCP error: {data['error']}")
            
            return data.get("result", {})
            
        except requests.Timeout:
            logger.error(f"MCP call timed out: {server}.{tool_name}")
            raise
        except requests.RequestException as e:
            logger.error(f"MCP call failed: {server}.{tool_name} - {e}")
            raise
    
    def list_tools(self, server: str) -> list:
        """List available tools for an MCP server."""
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")
        
        server_url = self.servers[server]
        if not server_url:
            raise ValueError(f"MCP server URL not configured: {server}")
        
        try:
            response = requests.post(
                f"{server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                raise ValueError(f"MCP error: {data['error']}")
            
            return data.get("result", {}).get("tools", [])
            
        except requests.RequestException as e:
            logger.error(f"Failed to list tools: {server} - {e}")
            raise


# Singleton instance
_mcp_client: Optional[MCPClient] = None


@lru_cache(maxsize=1)
def get_mcp_client() -> MCPClient:
    """Get singleton MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
```

---

### Step 2.2: Add MCP-Enhanced Workflow Node

**Objective**: Add workflow node that uses SEC EDGAR MCP server

**Implementation:**

```python
# src/workflow/workflow_nodes.py

# Add to WorkflowNodes class:

def fetch_sec_filing(self, state: AgentState) -> AgentState:
    """
    Fetch SEC filing data using SEC EDGAR MCP server.
    
    Falls back to manual lookup if MCP call fails.
    """
    self._log_node_start("fetch_sec_filing", state)
    
    if state.get("error"):
        self._log_node_skip("fetch_sec_filing", state, "Previous error in workflow")
        return state
    
    ticker = state["ticker"]
    
    # Only fetch SEC filings for US-listed stocks
    # For Thai/Singapore stocks, skip this node
    yahoo_ticker = self.ticker_map.get(ticker.upper())
    if not yahoo_ticker or not yahoo_ticker.endswith(('.US', '')):
        logger.info(f"Skipping SEC filing for non-US ticker: {ticker}")
        state["sec_filing_data"] = {}
        self._log_node_skip("fetch_sec_filing", state, "Non-US ticker")
        return state
    
    try:
        from src.integrations.mcp_client import get_mcp_client
        mcp_client = get_mcp_client()
        
        logger.info(f"Fetching SEC filing for {ticker} via MCP")
        
        # Call SEC EDGAR MCP server
        filing_data = mcp_client.call_tool(
            server='sec_edgar',
            tool_name='get_latest_filing',
            arguments={
                'ticker': yahoo_ticker.replace('.US', ''),
                'form_type': '10-Q'  # Quarterly report
            }
        )
        
        state["sec_filing_data"] = filing_data
        self._log_node_success("fetch_sec_filing", state, {
            'filing_date': filing_data.get('filing_date'),
            'form_type': filing_data.get('form_type')
        })
        
    except Exception as e:
        logger.warning(f"SEC EDGAR MCP failed: {e}, skipping SEC filing")
        state["sec_filing_data"] = {}
        self._log_node_skip("fetch_sec_filing", state, f"MCP error: {str(e)}")
    
    return state
```

**Update Workflow Graph:**

```python
# src/agent.py

def build_graph(self):
    """Build LangGraph workflow with MCP-enhanced nodes."""
    workflow = StateGraph(AgentState)
    
    # Existing nodes
    workflow.add_node("fetch_data", self.workflow_nodes.fetch_data)
    workflow.add_node("fetch_news", self.workflow_nodes.fetch_news)
    workflow.add_node("analyze_technical", self.workflow_nodes.analyze_technical)
    
    # NEW: MCP-enhanced node
    workflow.add_node("fetch_sec_filing", self.workflow_nodes.fetch_sec_filing)
    
    # Rest of nodes...
    workflow.add_node("generate_report", self.workflow_nodes.generate_report)
    
    # Update edges
    workflow.set_entry_point("fetch_data")
    workflow.add_edge("fetch_data", "fetch_news")
    workflow.add_edge("fetch_news", "analyze_technical")
    workflow.add_edge("analyze_technical", "fetch_sec_filing")  # NEW
    workflow.add_edge("fetch_sec_filing", "generate_report")  # Updated
    
    return workflow.compile()
```

---

### Step 2.3: Update Report Generation to Use SEC Filing Data

**Objective**: Enhance report generation with SEC filing data

**Implementation:**

```python
# src/report/context_builder.py

def prepare_context(
    self,
    ticker: str,
    ticker_data: dict,
    indicators: dict,
    percentiles: dict,
    news: list,
    news_summary: dict,
    strategy_performance: Optional[dict] = None,
    comparative_insights: Optional[dict] = None,
    sec_filing_data: Optional[dict] = None  # NEW parameter
) -> dict:
    """Prepare context for LLM report generation."""
    context = {
        # Existing context...
        'ticker': ticker,
        'ticker_data': ticker_data,
        'indicators': indicators,
        # ...
    }
    
    # Add SEC filing data if available
    if sec_filing_data:
        context['sec_filing'] = {
            'filing_date': sec_filing_data.get('filing_date'),
            'form_type': sec_filing_data.get('form_type'),
            'revenue': sec_filing_data.get('xbrl', {}).get('RevenueFromContractWithCustomerExcludingAssessedTax'),
            'operating_income': sec_filing_data.get('xbrl', {}).get('OperatingIncomeLoss'),
            'net_income': sec_filing_data.get('xbrl', {}).get('NetIncomeLoss'),
            'risk_factors': sec_filing_data.get('text_sections', {}).get('risk_factors', ''),
        }
    
    return context
```

**Update Workflow Node:**

```python
# src/workflow/workflow_nodes.py

def generate_report(self, state: AgentState) -> AgentState:
    """Generate report with SEC filing data if available."""
    # ... existing code ...
    
    sec_filing_data = state.get("sec_filing_data", {})
    
    context = self.context_builder.prepare_context(
        ticker, ticker_data, indicators, percentiles, news, news_summary,
        strategy_performance=strategy_performance,
        comparative_insights=comparative_insights,
        sec_filing_data=sec_filing_data  # NEW
    )
    
    # ... rest of report generation ...
```

---

## Phase 3: Add Resilience Patterns (Week 3)

### Step 3.1: Implement SQS Async Pattern

**Objective**: Add async MCP call pattern using SQS

**Implementation:**

```python
# src/integrations/mcp_async.py
"""
Async MCP call pattern using SQS.
"""
import json
import boto3
import os
import logging
from typing import Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)

sqs_client = boto3.client('sqs')
MCP_QUEUE_URL = os.getenv('MCP_QUEUE_URL')


def queue_mcp_call(
    server: str,
    tool_name: str,
    arguments: Dict[str, Any],
    callback_state: Optional[Dict] = None
) -> str:
    """
    Queue MCP call for async processing.
    
    Returns:
        Request ID for tracking
    """
    request_id = str(uuid4())
    
    message = {
        'request_id': request_id,
        'server': server,
        'tool_name': tool_name,
        'arguments': arguments,
        'callback_state': callback_state or {}
    }
    
    sqs_client.send_message(
        QueueUrl=MCP_QUEUE_URL,
        MessageBody=json.dumps(message)
    )
    
    logger.info(f"Queued MCP call: {server}.{tool_name} (request_id: {request_id})")
    return request_id
```

**Create SQS Worker Lambda:**

```python
# src/lambda_handlers/mcp_worker.py
"""
Lambda worker for processing async MCP calls from SQS.
"""
import json
import logging
from src.integrations.mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """Process SQS messages containing MCP call requests."""
    mcp_client = get_mcp_client()
    
    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            
            request_id = message['request_id']
            server = message['server']
            tool_name = message['tool_name']
            arguments = message['arguments']
            
            logger.info(f"Processing MCP call: {server}.{tool_name} (request_id: {request_id})")
            
            # Call MCP server
            result = mcp_client.call_tool(
                server=server,
                tool_name=tool_name,
                arguments=arguments
            )
            
            # Store result (DynamoDB, S3, or return to caller)
            # Implementation depends on callback pattern
            
            logger.info(f"MCP call completed: {request_id}")
            
        except Exception as e:
            logger.error(f"Failed to process MCP call: {e}")
            # Message will be retried or sent to DLQ
            raise
    
    return {'statusCode': 200}
```

---

### Step 3.2: Add Circuit Breaker Pattern

**Objective**: Prevent cascading failures when MCP servers are down

**Implementation:**

```python
# src/integrations/mcp_circuit_breaker.py
"""
Circuit breaker pattern for MCP servers.
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker for MCP server calls."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count: Dict[str, int] = {}
        self.circuit_open: Dict[str, datetime] = {}
    
    def call(self, server: str, func, *args, **kwargs):
        """Call function with circuit breaker protection."""
        # Check if circuit is open
        if server in self.circuit_open:
            open_time = self.circuit_open[server]
            if datetime.now() - open_time < timedelta(seconds=self.timeout):
                logger.warning(f"Circuit breaker OPEN for {server}, skipping call")
                raise CircuitBreakerOpenError(f"Circuit breaker open for {server}")
            else:
                # Timeout expired, attempt to close circuit
                logger.info(f"Attempting to close circuit for {server}")
                del self.circuit_open[server]
                self.failure_count[server] = 0
        
        # Attempt call
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            self.failure_count[server] = 0
            return result
        except Exception as e:
            # Failure - increment count
            self.failure_count[server] = self.failure_count.get(server, 0) + 1
            logger.warning(f"MCP call failed for {server}: {e} (failures: {self.failure_count[server]})")
            
            # Open circuit if threshold reached
            if self.failure_count[server] >= self.failure_threshold:
                self.circuit_open[server] = datetime.now()
                logger.error(f"Circuit breaker OPENED for {server}")
            
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
```

**Usage:**

```python
# src/integrations/mcp_client.py

from src.integrations.mcp_circuit_breaker import CircuitBreaker

circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def call_tool(self, server: str, tool_name: str, arguments: Dict[str, Any]):
    """Call MCP tool with circuit breaker protection."""
    def _call():
        # Actual MCP call logic
        response = requests.post(...)
        return response.json()
    
    try:
        return circuit_breaker.call(server, _call)
    except CircuitBreakerOpenError:
        # Fallback to alternative data source
        logger.warning(f"Circuit breaker open for {server}, using fallback")
        return self._fallback_data_source(server, tool_name, arguments)
```

---

## Testing Strategy

### Unit Tests
- [ ] Test MCP client wrapper
- [ ] Test circuit breaker logic
- [ ] Test SQS async pattern

### Integration Tests
- [ ] Test SEC EDGAR MCP server deployment
- [ ] Test LangGraph workflow with MCP node
- [ ] Test error handling and fallbacks

### End-to-End Tests
- [ ] Test complete report generation with SEC filing data
- [ ] Test performance under load
- [ ] Test cost monitoring

---

## Success Criteria

### Phase 1 (SEC EDGAR MCP Server)
- ✅ Lambda function deployed and accessible
- ✅ Can retrieve SEC filings via MCP protocol
- ✅ Response format matches expectations

### Phase 2 (LangGraph Integration)
- ✅ Workflow node successfully calls SEC EDGAR MCP
- ✅ Report generation includes SEC filing data
- ✅ Fallback works when MCP server unavailable

### Phase 3 (Resilience)
- ✅ SQS async pattern implemented
- ✅ Circuit breaker prevents cascading failures
- ✅ Cost monitoring in place

---

## Rollback Plan

If MCP integration causes issues:

1. **Disable MCP Node**: Remove `fetch_sec_filing` node from workflow graph
2. **Revert Code**: Git revert to pre-MCP commit
3. **Keep Infrastructure**: Leave Lambda functions deployed (no cost if unused)
4. **Document Issues**: Record problems for future iteration

---

## Next Steps After POC

1. **Add More MCP Servers**: Alpaca, Financial Markets
2. **Evaluate AgentCore Gateway**: If available, migrate to managed gateway
3. **Optimize Costs**: Monitor usage and optimize caching
4. **Scale Testing**: Test with production load

---

**Last Updated**: 2025-01-15  
**Owner**: Development Team
