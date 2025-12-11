# MCP Infrastructure Verification Checklist

**Purpose**: Verify AWS services availability and pricing for MCP infrastructure  
**Status**: In Progress  
**Created**: 2025-01-15

---

## Phase 1: AgentCore Gateway Verification

### 1.1 Availability Check

- [ ] **Check GA Status**
  ```bash
  # Check AWS documentation for AgentCore Gateway GA announcement
  # Expected: Generally Available (GA) or Preview status
  # Action: Review AWS Bedrock release notes
  ```
  **Status**: ⏳ Pending  
  **Notes**: Need to verify if AgentCore Gateway is GA or still in preview

- [ ] **Verify Region Availability**
  ```bash
  # Check if AgentCore Gateway is available in ap-southeast-1
  aws bedrock list-foundation-models --region ap-southeast-1
  # Check AgentCore-specific endpoints
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify ap-southeast-1 support

- [ ] **Check MCP Protocol Support**
  ```bash
  # Verify protocolType="MCP" is supported
  # Review AWS documentation for MCP protocol compatibility
  ```
  **Status**: ⏳ Pending  
  **Notes**: Confirm MCP protocol is natively supported

---

### 1.2 Pricing Verification

- [ ] **Check Free Tier Availability**
  ```bash
  # Review AWS pricing page for AgentCore Gateway
  # Expected: Free tier similar to API Gateway (1M requests/month)
  ```
  **Status**: ⏳ Pending  
  **Notes**: Need to verify actual pricing model

- [ ] **Calculate Expected Costs**
  ```bash
  # Estimate based on expected usage:
  # - Reports per day: 50-100
  # - MCP calls per report: 5-10
  # - Total MCP calls/day: 250-1000
  # - Monthly: 7,500 - 30,000 calls
  ```
  **Status**: ⏳ Pending  
  **Notes**: Calculate if within free tier

- [ ] **Compare with Custom Gateway**
  ```bash
  # Custom gateway costs:
  # - API Gateway: $3.50 per million requests
  # - Lambda: $0.20 per million requests
  # - Total: ~$0.10 per 1000 requests
  ```
  **Status**: ⏳ Pending  
  **Notes**: Compare AgentCore Gateway vs custom solution

---

### 1.3 LangGraph Integration Verification

- [ ] **Test MultiServerMCPClient**
  ```python
  # Verify LangChain MultiServerMCPClient works with AgentCore Gateway
  from langchain_mcp import MultiServerMCPClient
  
  client = MultiServerMCPClient(
      gateway_url="https://agentcore-gateway.aws.amazon.com/mcp",
      api_key="..."
  )
  
  tools = client.list_tools()
  assert len(tools) > 0
  ```
  **Status**: ⏳ Pending  
  **Notes**: Create test script to verify integration

- [ ] **Verify Response Format**
  ```python
  # Test tool calling format compatibility
  result = client.call_tool("sec_edgar", "get_latest_filing", {"ticker": "NVDA"})
  assert isinstance(result, dict)
  assert "filing_data" in result
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify response structure matches LangGraph expectations

- [ ] **Test with OpenRouter**
  ```python
  # Verify AgentCore Gateway works with non-Bedrock agents
  # Current stack uses OpenRouter, not Bedrock
  ```
  **Status**: ⏳ Pending  
  **Notes**: Critical - need to verify non-Bedrock compatibility

---

## Phase 2: MCP Server Deployment Verification

### 2.1 SEC EDGAR MCP Server

- [ ] **Deploy Lambda Function**
  ```bash
  # Create Lambda function for SEC EDGAR MCP server
  # Source: https://github.com/stefanoamorelli/sec-edgar-mcp
  ```
  **Status**: ⏳ Pending  
  **Notes**: Deploy as Lambda function URL or API Gateway endpoint

- [ ] **Test Basic Functionality**
  ```python
  # Test SEC EDGAR MCP server
  import requests
  
  response = requests.post(
      "https://lambda-url.execute-api.ap-southeast-1.amazonaws.com/mcp",
      json={
          "method": "tools/call",
          "params": {
              "name": "get_latest_filing",
              "arguments": {"ticker": "NVDA", "form_type": "10-Q"}
          }
      }
  )
  assert response.status_code == 200
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify SEC EDGAR API access (free, no API key)

- [ ] **Register with AgentCore Gateway**
  ```bash
  # Register SEC EDGAR MCP server as target in AgentCore Gateway
  aws bedrock-agentcore create-gateway-target \
      --gateway-id <gateway-id> \
      --target-type lambda \
      --target-arn <lambda-arn> \
      --protocol-type MCP
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify registration process

---

### 2.2 Alpaca MCP Server

- [ ] **Get Free API Key**
  ```bash
  # Sign up for Alpaca free tier
  # URL: https://alpaca.markets/
  # Free tier: Real-time data with 15-min delay on options
  ```
  **Status**: ⏳ Pending  
  **Notes**: Store API key in Secrets Manager

- [ ] **Deploy Lambda Function**
  ```bash
  # Create Lambda function for Alpaca MCP server
  # Source: https://github.com/alpacahq/alpaca-mcp-server
  ```
  **Status**: ⏳ Pending  
  **Notes**: Configure with Secrets Manager for API key

- [ ] **Test Market Data Retrieval**
  ```python
  # Test Alpaca MCP server
  response = requests.post(
      "https://lambda-url.execute-api.ap-southeast-1.amazonaws.com/mcp",
      json={
          "method": "tools/call",
          "params": {
              "name": "get_latest_bars",
              "arguments": {"symbol": "NVDA", "timeframe": "1Day", "limit": 30}
          }
      }
  )
  assert response.status_code == 200
  data = response.json()
  assert "bars" in data
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify free tier data access

---

### 2.3 Financial Markets MCP Server

- [ ] **Deploy Self-Hosted Server**
  ```bash
  # Deploy Financial Markets MCP server as Lambda
  # Source: https://lobehub.com/mcp/olonok69-mcp_financial_markets_analysis_tool
  # Note: Self-hosted, no external API needed
  ```
  **Status**: ⏳ Pending  
  **Notes**: Package as Lambda function

- [ ] **Test Technical Analysis**
  ```python
  # Test Financial Markets MCP server
  response = requests.post(
      "https://lambda-url.execute-api.ap-southeast-1.amazonaws.com/mcp",
      json={
          "method": "tools/call",
          "params": {
              "name": "calculate_confluence",
              "arguments": {
                  "indicators": {"rsi": 45, "macd": "bullish"},
                  "price_data": {...}
              }
          }
      }
  )
  assert response.status_code == 200
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify technical analysis calculations

---

## Phase 3: Infrastructure Services Verification

### 3.1 SQS Queue Setup

- [ ] **Create Standard Queue**
  ```bash
  aws sqs create-queue \
      --queue-name dr-daily-report-mcp-calls-dev \
      --attributes '{
          "VisibilityTimeout": "300",
          "MessageRetentionPeriod": "345600"
      }'
  ```
  **Status**: ⏳ Pending  
  **Notes**: Standard queue for async MCP calls

- [ ] **Create Dead-Letter Queue**
  ```bash
  aws sqs create-queue \
      --queue-name dr-daily-report-mcp-calls-dlq-dev \
      --attributes '{
          "MessageRetentionPeriod": "1209600"
      }'
  ```
  **Status**: ⏳ Pending  
  **Notes**: DLQ for failed MCP calls (14-day retention)

- [ ] **Configure Redrive Policy**
  ```bash
  aws sqs set-queue-attributes \
      --queue-url <main-queue-url> \
      --attributes '{
          "RedrivePolicy": "{\"deadLetterTargetArn\":\"<dlq-arn>\",\"maxReceiveCount\":3}"
      }'
  ```
  **Status**: ⏳ Pending  
  **Notes**: Auto-redrive failed messages to DLQ after 3 attempts

- [ ] **Test Queue Integration**
  ```python
  import boto3
  sqs = boto3.client('sqs')
  
  # Send test message
  response = sqs.send_message(
      QueueUrl=queue_url,
      MessageBody=json.dumps({
          'tool': 'sec_edgar',
          'method': 'get_latest_filing',
          'params': {'ticker': 'NVDA'}
      })
  )
  assert 'MessageId' in response
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify SQS → Lambda trigger works

---

### 3.2 Secrets Manager Setup

- [ ] **Store Alpaca API Key**
  ```bash
  aws secretsmanager create-secret \
      --name dr-daily-report-alpaca-api-key-dev \
      --secret-string '{"api_key": "...", "api_secret": "..."}'
  ```
  **Status**: ⏳ Pending  
  **Notes**: Store Alpaca credentials securely

- [ ] **Test Secret Retrieval**
  ```python
  import boto3
  secrets = boto3.client('secretsmanager')
  
  response = secrets.get_secret_value(
      SecretId='dr-daily-report-alpaca-api-key-dev'
  )
  assert 'SecretString' in response
  credentials = json.loads(response['SecretString'])
  assert 'api_key' in credentials
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify Lambda can access secrets

- [ ] **Configure IAM Permissions**
  ```bash
  # Add Secrets Manager permissions to Lambda execution role
  aws iam attach-role-policy \
      --role-name dr-daily-report-lambda-execution-role \
      --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify least-privilege access

---

### 3.3 X-Ray Tracing Setup

- [ ] **Enable X-Ray on Lambda**
  ```bash
  aws lambda update-function-configuration \
      --function-name dr-daily-report-mcp-sec-edgar-dev \
      --tracing-config Mode=Active
  ```
  **Status**: ⏳ Pending  
  **Notes**: Enable X-Ray tracing for MCP Lambda functions

- [ ] **Test Trace Collection**
  ```python
  from aws_xray_sdk.core import xray_recorder
  
  @xray_recorder.capture('mcp_call')
  def call_mcp_server(tool_name, params):
      # MCP call logic
      pass
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify traces appear in X-Ray console

- [ ] **Verify Service Map**
  ```bash
  # Check X-Ray service map shows:
  # LangGraph Agent → AgentCore Gateway → MCP Servers
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify end-to-end tracing

---

## Phase 4: Integration Testing

### 4.1 End-to-End MCP Call Test

- [ ] **Test Complete Flow**
  ```python
  # Test: LangGraph Agent → AgentCore Gateway → SEC EDGAR MCP → Response
  from src.agent import TickerAnalysisAgent
  
  agent = TickerAnalysisAgent()
  
  # Mock MCP call in workflow
  state = {
      "ticker": "NVDA",
      "messages": []
  }
  
  # Call MCP-enhanced workflow node
  result = agent.workflow_nodes.fetch_sec_filing(state)
  
  assert "sec_filing_data" in result
  assert result["sec_filing_data"]["ticker"] == "NVDA"
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify complete integration works

- [ ] **Test Error Handling**
  ```python
  # Test fallback when MCP server fails
  # Expected: Falls back to yfinance or cached data
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify graceful degradation

- [ ] **Test Performance**
  ```python
  import time
  
  start = time.time()
  result = agent.workflow_nodes.fetch_sec_filing(state)
  elapsed = time.time() - start
  
  assert elapsed < 5.0  # MCP call should complete in <5 seconds
  ```
  **Status**: ⏳ Pending  
  **Notes**: Verify acceptable latency

---

### 4.2 Cost Monitoring

- [ ] **Set Up CloudWatch Billing Alarms**
  ```bash
  aws cloudwatch put-metric-alarm \
      --alarm-name mcp-infrastructure-cost-alert \
      --alarm-description "Alert when MCP infrastructure costs exceed $10/month" \
      --metric-name EstimatedCharges \
      --namespace AWS/Billing \
      --statistic Maximum \
      --period 86400 \
      --evaluation-periods 1 \
      --threshold 10.0 \
      --comparison-operator GreaterThanThreshold
  ```
  **Status**: ⏳ Pending  
  **Notes**: Monitor costs vs free tier limits

- [ ] **Track Service Usage**
  ```bash
  # Monitor:
  # - AgentCore Gateway requests
  # - Lambda invocations (MCP servers)
  # - SQS messages
  # - Secrets Manager API calls
  # - X-Ray traces
  ```
  **Status**: ⏳ Pending  
  **Notes**: Set up CloudWatch dashboards

---

## Verification Results Summary

### Completed ✅
- None yet

### In Progress ⏳
- All verification tasks pending

### Blocked ❌
- None

### Notes
- Need to verify AgentCore Gateway GA status first
- Pricing verification depends on AWS documentation
- Integration testing requires deployed infrastructure

---

## Next Actions

1. **Immediate**: Check AWS Bedrock documentation for AgentCore Gateway availability
2. **Week 1**: Deploy SEC EDGAR MCP server as proof of concept
3. **Week 2**: Test AgentCore Gateway integration (if available)
4. **Week 3**: Complete cost analysis and comparison

---

**Last Updated**: 2025-01-15  
**Owner**: Development Team
