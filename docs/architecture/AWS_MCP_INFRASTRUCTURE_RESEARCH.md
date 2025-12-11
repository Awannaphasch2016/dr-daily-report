# AWS Infrastructure for MCP-Based LLM Report Generation

**Status**: Research Complete, Verification Pending  
**Created**: 2025-01-15  
**Purpose**: Identify AWS services and patterns for production-ready MCP infrastructure  
**Related Docs**: 
- [MCP Financial Analysis Integration](../report-generation/mcp-financial-analysis-integration.md) - MCP server selection
- [AWS MCP Comparison](../AWS_MCP_COMPARISON.md) - Development workflow MCPs

---

## Executive Summary

This document identifies AWS services and architectural patterns for building a production-ready MCP (Model Context Protocol) infrastructure that:

1. **Manages multiple MCP servers** (SEC EDGAR, Alpaca, Financial Markets, etc.)
2. **Provides non-linear services** (error handling, buffering, retries, circuit breaking)
3. **Integrates with LangChain/LangGraph** (current framework)
4. **Works with Amazon Bedrock** (Claude/Nova models) - optional migration path
5. **Minimizes cost** (prefer serverless, managed services, free tiers)

**Key Finding**: Amazon Bedrock AgentCore Gateway provides a fully managed MCP gateway solution, eliminating the need for custom MCP infrastructure.

---

## Current Architecture Context

### Existing Stack
- **LangGraph**: Workflow orchestration (Lambda-based)
- **OpenRouter**: LLM provider (GPT-4o)
- **Lambda**: Agent runtime
- **Data Sources**: yfinance, news APIs (direct integration)

### Target MCP Integration
```
LangGraph Agent (Lambda)
  ↓ (MCP client)
MCP Gateway (AWS managed or custom)
  ↓
Multiple MCP Servers:
  - SEC EDGAR MCP (free, no API key)
  - Alpaca MCP (free tier)
  - Financial Markets MCP (self-hosted)
  - Custom Lambda tools
```

---

## Key AWS Services for MCP Infrastructure

### 1. Amazon Bedrock AgentCore Gateway (MCP-Native) ⭐⭐⭐

**What it is:**
- **Fully managed MCP gateway** that exposes a single MCP endpoint
- Fans out to multiple tools/APIs/Lambdas and existing MCP servers
- Protocol-aware: speaks MCP natively (`protocolType="MCP"`)

**Key Features:**
- **Single MCP endpoint** for your agent (no need to manage multiple connections)
- **Tool discovery**: Agents call `list_tools` and get union view of all tools
- **Auth**: Inbound (Cognito/OAuth2) + Outbound (AgentCore Identity for API keys)
- **Scaling**: AWS handles infrastructure scaling automatically

**Cost:**
- **Pricing model**: Pay-per-request (similar to API Gateway)
- **Free tier**: Likely available (need to verify current pricing)
- **Cost-effective**: No infrastructure to manage

**Integration with LangChain/LangGraph:**
- ✅ **Official support**: AWS docs show examples with LangChain/LangGraph using `MultiServerMCPClient`
- ✅ **Direct integration**: Point LangGraph agent at Gateway MCP URL
- ✅ **No code changes**: Existing LangGraph workflows work as-is

**Use Case for Our Project:**
```
LangGraph Agent (OpenRouter → GPT-4o)
  ↓
AgentCore Gateway (MCP endpoint)
  ↓
Multiple MCP Servers:
  - SEC EDGAR MCP (free, no API key)
  - Alpaca MCP (free tier)
  - Financial Markets MCP (self-hosted)
  - Custom Lambda tools
```

**Verification Needed:**
- [ ] Check AgentCore Gateway pricing (free tier availability)
- [ ] Verify LangGraph integration examples
- [ ] Test MCP protocol compatibility
- [ ] Check if it works with non-Bedrock agents (we use OpenRouter)

**References:**
- AWS Bedrock AgentCore Documentation (verify GA status)
- LangChain AgentCore Gateway integration guide

---

### 2. Amazon Bedrock AgentCore Runtime

**What it is:**
- **Managed runtime for agents** (serverless-ish)
- First-class MCP integration: deploy MCP servers directly onto AgentCore Runtime
- Supports multiple frameworks: LangGraph, LangChain, Strands, CrewAI

**Key Features:**
- **Deploy MCP servers**: Package FastMCP server as Docker image → ECR → AgentCore Runtime
- **Agent hosting**: Run your LangGraph agent on AgentCore Runtime
- **Observability**: Built-in traces, debugging, metrics for agents and gateways
- **Memory**: AgentCore Memory (managed memory layer) with LangGraph integration

**Cost:**
- **Pricing**: Likely pay-per-invocation (similar to Lambda)
- **Free tier**: Need to verify
- **Cost-effective**: No EC2/ECS to manage

**Integration with LangGraph:**
- ✅ **Official support**: AWS blog posts show LangGraph + AgentCore Runtime
- ✅ **Memory integration**: AgentCore Memory works with LangGraph
- ✅ **Framework-agnostic**: Can run LangGraph agents alongside other frameworks

**Use Case for Our Project:**
- **Option A**: Keep agent on Lambda, use AgentCore Gateway only
- **Option B**: Migrate agent to AgentCore Runtime (more AWS-native)

**Verification Needed:**
- [ ] Check AgentCore Runtime pricing
- [ ] Verify LangGraph deployment process
- [ ] Test with OpenRouter (not just Bedrock models)
- [ ] Compare cost vs Lambda

---

### 3. Strands Agents (AWS Native Framework)

**What it is:**
- **Open-source AI agent SDK** from AWS (Python/TypeScript)
- **Model-first design**: Built specifically for Bedrock (but supports other providers)
- **Production-ready**: Used internally at AWS (Amazon Q Developer, Glue, etc.)

**Key Features:**
- **Built-in MCP support**: Native MCP integration (streamable HTTP transport)
- **AgentCore integration**: Deploys smoothly onto Bedrock AgentCore
- **Strongly-typed**: Type-safe agent definitions
- **AWS-native**: Deep integration with AWS services

**Cost:**
- **Free**: Open-source (Apache 2.0 license)
- **Infrastructure**: Runs on AgentCore Runtime or Lambda (pay-per-use)

**Comparison with LangGraph:**
| Feature | LangGraph | Strands |
|---------|-----------|---------|
| **Orchestration** | Graph-based (DAG) | Model-first (agent-centric) |
| **MCP Support** | Via AgentCore Gateway | Built-in native |
| **AWS Integration** | Good (via Bedrock) | Excellent (designed for AWS) |
| **Multi-agent** | Excellent (supervisor patterns) | Good (can orchestrate) |
| **Ecosystem** | Large (LangChain tools) | Smaller (AWS-focused) |

**Use Case for Our Project:**
- **Hybrid approach**: Use LangGraph for report generation workflow, Strands for AWS-native tools
- **Future migration**: Consider Strands if we want deeper AWS integration

**Verification Needed:**
- [ ] Review Strands documentation
- [ ] Test MCP integration
- [ ] Compare with LangGraph for our use case
- [ ] Check migration path from LangGraph

---

## AWS Services for Non-Linear Orchestration

### 4.1 Amazon SQS (Buffering & Decoupling)

**What it is:**
- **Message queue** for decoupling agent from MCP servers
- **Standard queues**: Virtually unlimited throughput, at-least-once delivery
- **FIFO queues**: Strict ordering, exactly-once processing
- **Dead-letter queues (DLQs)**: Auto-collect failed messages

**Use Case:**
- **Buffer MCP calls**: Agent writes tool call to SQS → Worker processes → Results back to agent
- **Rate limiting**: Prevent hammering MCP servers during high load
- **Error handling**: Failed calls go to DLQ for debugging

**Cost:**
- **Free tier**: 1 million requests/month free
- **After free tier**: $0.40 per million requests
- **Very cost-effective**: Perfect for our use case

**Integration:**
- ✅ **LangGraph**: Can integrate SQS as async tool execution layer
- ✅ **Lambda**: Native integration (SQS → Lambda trigger)
- ✅ **Step Functions**: Can invoke SQS as part of workflow

**Implementation Pattern:**
```python
# Async MCP call pattern
def call_mcp_async(tool_name: str, params: dict):
    """Queue MCP call for async processing"""
    sqs_client.send_message(
        QueueUrl=os.getenv('MCP_QUEUE_URL'),
        MessageBody=json.dumps({
            'tool': tool_name,
            'params': params,
            'request_id': str(uuid.uuid4())
        })
    )
    return {'status': 'queued', 'request_id': request_id}
```

---

### 4.2 AWS Step Functions (Workflow Orchestration)

**What it is:**
- **Serverless workflow orchestration**
- **Built-in retries**: Exponential backoff, max attempts, jitter
- **Error handling**: Catch blocks for specific error types
- **Service integrations**: Lambda, HTTP, ECS, Bedrock, SQS

**Use Case:**
- **Multi-step MCP calls**: Orchestrate "fetch SEC filing → analyze → fetch options → synthesize"
- **Retry logic**: Automatic retries with backoff for failed MCP calls
- **Compensation**: Rollback actions if workflow fails partway

**Cost:**
- **Free tier**: 4,000 state transitions/month free
- **After free tier**: $0.025 per 1,000 state transitions
- **Cost-effective**: For complex workflows

**Integration:**
- ✅ **LangGraph**: Can call Step Functions as a tool
- ✅ **AgentCore Gateway**: Can have Step Functions as a target
- ✅ **MCP servers**: Step Functions can orchestrate multiple MCP calls

**Implementation Pattern:**
```json
{
  "Comment": "Multi-step MCP workflow",
  "StartAt": "FetchSECFiling",
  "States": {
    "FetchSECFiling": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:mcp-sec-edgar",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Next": "FetchOptionsData"
    },
    "FetchOptionsData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:mcp-alpaca",
      "Next": "SynthesizeReport"
    }
  }
}
```

---

### 4.3 Amazon EventBridge Pipes (Event Processing)

**What it is:**
- **Event processing pipeline**: Source → Filter → Enrich → Target
- **Filtering**: Only forward subset of messages based on patterns
- **Enrichment**: Call Lambda/HTTP to add context before invoking target
- **Non-linear**: Complex decisions without custom dispatcher

**Use Case:**
- **MCP call routing**: Filter tool calls → Enrich with context → Route to appropriate MCP server
- **Pre-processing**: Add metadata, validate requests before hitting MCP servers
- **Post-processing**: Transform MCP responses before returning to agent

**Cost:**
- **Free tier**: 14 million custom events/month free
- **After free tier**: $1.00 per million custom events
- **Very cost-effective**: For event-driven MCP routing

**Integration:**
- ✅ **SQS**: Can use SQS as source
- ✅ **Lambda**: Can trigger Lambda workers
- ✅ **Step Functions**: Can trigger state machines

---

### 4.4 AWS Lambda Powertools (Resilience & Observability)

**What it is:**
- **Serverless best-practice utilities** (Python/TypeScript)
- **Idempotency**: Prevent duplicate processing of retries
- **Logging**: Structured logging with CloudWatch integration
- **Tracing**: X-Ray integration for distributed tracing
- **Metrics**: Custom CloudWatch metrics
- **Circuit breaker**: Pattern for failing services

**Use Case:**
- **MCP worker resilience**: Idempotent MCP calls, circuit breaking for failing servers
- **Observability**: Structured logs, traces, metrics for MCP calls
- **Error handling**: Graceful degradation when MCP servers fail

**Cost:**
- **Free**: Open-source library (no AWS cost)
- **Infrastructure**: Runs on Lambda (pay-per-use)

**Integration:**
- ✅ **Lambda**: Native integration
- ✅ **LangGraph**: Can use in Lambda workers that LangGraph calls
- ✅ **MCP servers**: Use in MCP server Lambda functions

**Implementation Pattern:**
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.circuit_breaker import CircuitBreaker

logger = Logger()
tracer = Tracer()
metrics = Metrics()

circuit_breaker = CircuitBreaker(name="alpaca-mcp", failure_threshold=5)

@circuit_breaker
@tracer.capture_lambda_handler
def call_alpaca_mcp(ticker: str):
    """Call Alpaca MCP with circuit breaker"""
    metrics.add_metric(name="MCPCalls", unit="Count", value=1)
    # ... MCP call logic
```

---

### 4.5 Amazon API Gateway (Front Door & Throttling)

**What it is:**
- **Managed API front door**
- **Throttling**: Account-level, per-API, per-stage, per-client throttling
- **Request validation**: JSON schema validation
- **Caching**: Endpoint caching for idempotent reads
- **Auth**: JWT verification, API keys

**Use Case:**
- **MCP gateway front door**: Put API Gateway in front of AgentCore Gateway or custom MCP gateway
- **Rate limiting**: Protect MCP servers from bursty agent requests
- **Caching**: Cache SEC EDGAR filings (valid for 90 days) to reduce MCP calls

**Cost:**
- **Free tier**: 1 million API calls/month free (first 12 months)
- **After free tier**: $3.50 per million API calls
- **Cost-effective**: For high-volume MCP gateways

**Integration:**
- ✅ **AgentCore Gateway**: Can front AgentCore Gateway with API Gateway
- ✅ **Lambda**: Can proxy to Lambda-based MCP servers
- ✅ **LangGraph**: Agent can call API Gateway endpoint

---

### 4.6 AWS Secrets Manager (Credential Management)

**What it is:**
- **Managed secrets storage**
- **Automatic rotation**: Rotate API keys on schedule
- **IAM-based access**: Tight access control
- **Audit logging**: CloudTrail integration

**Use Case:**
- **MCP API keys**: Store Alpaca, Alpha Vantage API keys securely
- **Rotation**: Auto-rotate keys to prevent expiration
- **Access control**: Only Lambda workers can access secrets

**Cost:**
- **Free tier**: 10,000 API calls/month free
- **After free tier**: $0.40 per 10,000 API calls
- **Cost-effective**: For credential management

**Integration:**
- ✅ **Lambda**: Native integration (boto3 Secrets Manager)
- ✅ **AgentCore Identity**: Can use Secrets Manager as credential source
- ✅ **MCP servers**: Lambda-based MCP servers can fetch secrets

---

### 4.7 AWS X-Ray (Distributed Tracing)

**What it is:**
- **Distributed tracing** for end-to-end request flows
- **Service map**: Visualize agent → MCP Gateway → MCP servers → databases
- **Performance insights**: Identify bottlenecks

**Use Case:**
- **MCP call tracing**: See full path: LangGraph agent → AgentCore Gateway → SEC EDGAR MCP → Response
- **Performance debugging**: Identify slow MCP servers
- **Error tracking**: See where failures occur in MCP chain

**Cost:**
- **Free tier**: 100,000 traces/month free
- **After free tier**: $5.00 per million traces
- **Cost-effective**: For observability

**Integration:**
- ✅ **Lambda**: Native X-Ray integration
- ✅ **API Gateway**: X-Ray tracing enabled
- ✅ **LangGraph**: Can instrument LangGraph calls

---

## Recommended Architecture for Our Project

### Phase 1: Minimal Viable MCP Infrastructure (Free/Low-Cost)

**Components:**
1. **AgentCore Gateway** (MCP front door)
   - Single MCP endpoint for LangGraph agent
   - Routes to SEC EDGAR, Alpaca, Financial Markets MCP servers
   - **Cost**: Pay-per-request (likely free tier available)

2. **Lambda-based MCP Servers**
   - SEC EDGAR MCP (no API key needed)
   - Alpaca MCP (free API key)
   - Financial Markets MCP (self-hosted logic)
   - **Cost**: Lambda free tier (1M requests/month)

3. **SQS Queues** (Buffering)
   - Standard queue for async MCP calls
   - DLQ for failed calls
   - **Cost**: Free tier (1M requests/month)

4. **Secrets Manager** (API Keys)
   - Store Alpaca API keys
   - **Cost**: Free tier (10K API calls/month)

5. **X-Ray** (Tracing)
   - Distributed tracing for MCP calls
   - **Cost**: Free tier (100K traces/month)

**Total Monthly Cost**: **~$0** (within free tiers for moderate usage)

**Architecture Diagram:**
```
LangGraph Agent (Lambda)
  ↓ HTTP/HTTPS
AgentCore Gateway (MCP endpoint)
  ↓
┌─────────────────────────────────┐
│ Lambda MCP Servers:             │
│ - SEC EDGAR MCP                  │
│ - Alpaca MCP                     │
│ - Financial Markets MCP         │
└─────────────────────────────────┘
  ↓ (async calls)
SQS Queue → Lambda Workers
  ↓ (failed calls)
DLQ (for debugging)
```

---

### Phase 2: Enhanced Resilience (Add Step Functions)

**Additional Components:**
1. **Step Functions** (Workflow Orchestration)
   - Multi-step MCP call workflows
   - Automatic retries with backoff
   - **Cost**: Free tier (4K state transitions/month)

2. **EventBridge Pipes** (Event Processing)
   - Filter/enrich MCP calls
   - **Cost**: Free tier (14M events/month)

3. **API Gateway** (Front Door)
   - Rate limiting, caching
   - **Cost**: Free tier (1M API calls/month, first year)

**Total Monthly Cost**: **~$0-5** (within free tiers)

---

### Phase 3: Full Production (Add AgentCore Runtime)

**Additional Components:**
1. **AgentCore Runtime** (Agent Hosting)
   - Migrate LangGraph agent to AgentCore Runtime
   - Managed memory, observability
   - **Cost**: Pay-per-invocation (need to verify pricing)

2. **AgentCore Memory** (Managed Memory)
   - Cross-session memory for agents
   - **Cost**: Pay-per-use (need to verify pricing)

**Total Monthly Cost**: **~$10-50** (depending on usage)

---

## Integration Strategy: LangGraph + Bedrock + MCP

### Current Stack:
- **LangGraph**: Workflow orchestration
- **OpenRouter**: LLM provider (GPT-4o)
- **Lambda**: Agent runtime

### Recommended Integration:

**Option A: Keep OpenRouter, Add AgentCore Gateway** (Recommended)
```
LangGraph Agent (Lambda)
  ↓ (MCP client)
AgentCore Gateway (MCP endpoint)
  ↓
MCP Servers (SEC EDGAR, Alpaca, Financial Markets)
```

**Benefits:**
- ✅ No code changes to LangGraph workflow
- ✅ Single MCP endpoint (easier management)
- ✅ AWS handles scaling, auth, routing
- ✅ Keep OpenRouter (no vendor lock-in)

**Option B: Migrate to Bedrock, Use AgentCore Runtime**
```
LangGraph Agent (AgentCore Runtime)
  ↓ (Bedrock Converse API)
Claude/Nova (Bedrock)
  ↓ (MCP via AgentCore Gateway)
MCP Servers
```

**Benefits:**
- ✅ Deeper AWS integration
- ✅ Managed memory, observability
- ✅ Potentially lower cost (Bedrock vs OpenRouter)
- ❌ Vendor lock-in to Bedrock

**Recommendation**: **Start with Option A** (AgentCore Gateway + OpenRouter), migrate to Option B if Bedrock proves cost-effective.

---

## Implementation Plan

### Phase 1: Research & Verification (Week 1)

**Tasks:**
1. **Verify AgentCore Gateway Availability**
   - [ ] Check if AgentCore Gateway is GA (generally available)
   - [ ] Verify pricing (free tier availability)
   - [ ] Test MCP protocol compatibility
   - [ ] Verify LangGraph integration examples

2. **Test Free MCP Servers**
   - [ ] Deploy SEC EDGAR MCP server (Lambda)
   - [ ] Test Alpaca MCP with free API key
   - [ ] Verify Financial Markets MCP deployment

3. **Cost Analysis**
   - [ ] Calculate AWS service costs for expected usage
   - [ ] Compare AgentCore Gateway vs custom MCP gateway
   - [ ] Estimate Lambda costs for MCP servers

**Deliverables:**
- Verification report with pricing details
- Proof of concept: SEC EDGAR MCP server deployed
- Cost comparison spreadsheet

---

### Phase 2: Proof of Concept (Week 2-3)

**Tasks:**
1. **Deploy AgentCore Gateway**
   - [ ] Create Gateway with MCP protocol
   - [ ] Register SEC EDGAR MCP as target
   - [ ] Register Alpaca MCP as target
   - [ ] Test `list_tools` endpoint

2. **Integrate with LangGraph**
   - [ ] Update LangGraph agent to use AgentCore Gateway MCP endpoint
   - [ ] Test tool calling via Gateway
   - [ ] Verify response format compatibility

3. **Add Resilience**
   - [ ] Implement SQS buffering for async MCP calls
   - [ ] Add DLQ for failed calls
   - [ ] Implement circuit breaker pattern (DynamoDB)

**Deliverables:**
- Working AgentCore Gateway integration
- LangGraph workflow using MCP tools
- SQS async pattern implementation

---

### Phase 3: Production Deployment (Week 4-5)

**Tasks:**
1. **Add Observability**
   - [ ] Enable X-Ray tracing
   - [ ] Add CloudWatch metrics
   - [ ] Set up alarms for MCP failures

2. **Optimize Costs**
   - [ ] Implement caching (API Gateway cache for SEC EDGAR)
   - [ ] Batch MCP calls where possible
   - [ ] Monitor usage vs free tier limits

3. **Documentation**
   - [ ] Document MCP server deployment process
   - [ ] Document AgentCore Gateway configuration
   - [ ] Update deployment runbook

**Deliverables:**
- Production-ready MCP infrastructure
- Monitoring dashboards
- Updated deployment documentation

---

## Cost Summary

**Phase 1 (Minimal Viable):**
- AgentCore Gateway: ~$0 (free tier expected)
- Lambda (MCP servers): $0 (1M requests/month free)
- SQS: $0 (1M requests/month free)
- Secrets Manager: $0 (10K API calls/month free)
- X-Ray: $0 (100K traces/month free)
- **Total: $0/month** (within free tiers)

**Phase 2 (Enhanced):**
- Step Functions: $0 (4K state transitions/month free)
- EventBridge Pipes: $0 (14M events/month free)
- API Gateway: $0 (1M API calls/month free, first year)
- **Total: $0-5/month** (within free tiers)

**Phase 3 (Full Production):**
- AgentCore Runtime: ~$10-50/month (need to verify)
- AgentCore Memory: ~$5-20/month (need to verify)
- **Total: ~$15-75/month** (depending on usage)

---

## Key Decisions Needed

1. **AgentCore Gateway vs Custom MCP Gateway**
   - **AgentCore Gateway**: Managed, AWS-native, easier
   - **Custom Gateway**: More control, potentially lower cost
   - **Recommendation**: Start with AgentCore Gateway, migrate if needed

2. **OpenRouter vs Bedrock**
   - **OpenRouter**: Current stack, no vendor lock-in
   - **Bedrock**: Deeper AWS integration, potentially lower cost
   - **Recommendation**: Keep OpenRouter initially, test Bedrock pricing

3. **LangGraph vs Strands**
   - **LangGraph**: Current stack, large ecosystem
   - **Strands**: AWS-native, better MCP integration
   - **Recommendation**: Keep LangGraph, consider Strands for AWS-native tools

4. **Lambda vs AgentCore Runtime**
   - **Lambda**: Current stack, pay-per-use
   - **AgentCore Runtime**: Managed, better observability
   - **Recommendation**: Start with Lambda, migrate to AgentCore Runtime if beneficial

---

## Next Steps

1. **Verify AgentCore Gateway Availability**
   - Check AWS documentation for GA status
   - Test MCP protocol compatibility
   - Verify pricing

2. **Create Proof of Concept**
   - Deploy SEC EDGAR MCP server (Lambda)
   - Test AgentCore Gateway integration
   - Verify LangGraph compatibility

3. **Update Implementation Plan**
   - Incorporate AWS services into MCP integration plan
   - Update cost estimates
   - Add AWS-specific deployment steps

---

## References

### AWS Documentation
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html) - Verify GA status
- [AgentCore Gateway](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html) - MCP gateway docs
- [AgentCore Runtime](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-runtime.html) - Runtime hosting
- [Strands Agents](https://github.com/aws/strands-agents) - AWS native framework

### MCP Protocol
- [Model Context Protocol Specification](https://github.com/modelcontextprotocol/specification)
- [LangChain MCP Integration](https://python.langchain.com/docs/integrations/mcp/) - Verify compatibility

### Related Project Docs
- [MCP Financial Analysis Integration](../report-generation/mcp-financial-analysis-integration.md) - MCP server selection
- [Deployment Workflow](../deployment/WORKFLOW.md) - Current deployment patterns
- [Lambda Best Practices](../deployment/LAMBDA_BEST_PRACTICES.md) - Serverless patterns

---

**Research Status**: ✅ Complete  
**Next Action**: Verify AgentCore Gateway availability and create proof of concept  
**Owner**: Development Team  
**Last Updated**: 2025-01-15
