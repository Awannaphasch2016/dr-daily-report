# ADR-002: Use OpenRouter as LLM Proxy

**Status:** ✅ Accepted
**Date:** 2024-01 (Sprint 1)
**Deciders:** Development Team

## Context

The project requires LLM capabilities for Thai language financial report generation. Initial implementation used direct OpenAI API integration.

### Pain Points with Direct OpenAI API

- **Cost Tracking**: No built-in dashboard showing per-request costs
- **Usage Monitoring**: Difficult to track token consumption across requests
- **API Key Management**: Requires OpenAI account, API key rotation is manual
- **Model Switching**: Changing models (GPT-4o → Claude → Gemini) requires code changes
- **Rate Limiting**: Must implement custom rate limit handling

## Decision

Use OpenRouter (https://openrouter.ai) as an LLM proxy instead of direct OpenAI API integration.

### Implementation

```python
# src/agent.py
self.llm = ChatOpenAI(
    model="openai/gpt-4o",
    base_url="https://openrouter.ai/api/v1",  # OpenRouter proxy
    api_key=os.getenv("OPENROUTER_API_KEY")  # Not OPENAI_API_KEY
)
```

### Configuration

- Store `OPENROUTER_API_KEY` in Doppler secrets
- Use LangChain's `ChatOpenAI` class (compatible with OpenRouter)
- Specify model via `model="openai/gpt-4o"` format

## Consequences

### Positive

- ✅ **Cost Tracking**: OpenRouter dashboard shows per-request costs automatically
- ✅ **Usage Monitoring**: Real-time token consumption tracking
- ✅ **API Key Rotation**: Single OpenRouter key works for all models
- ✅ **Multi-Model Support**: Switch models by changing string (no code changes)
- ✅ **Rate Limit Management**: OpenRouter handles rate limiting across providers
- ✅ **Unified Billing**: Single invoice for all LLM providers

### Negative

- ❌ **Latency Overhead**: ~50ms additional latency per request (proxy hop)
- ❌ **Service Dependency**: Adds OpenRouter as a critical dependency
- ❌ **Vendor Lock-in**: Switching from OpenRouter requires code changes
- ❌ **Cost Markup**: OpenRouter charges small markup over provider rates

### Neutral

- Same LangChain interface (compatible with existing code)
- No changes to prompt engineering or response handling

## Alternatives Considered

### Alternative 1: Direct OpenAI API

**Why Rejected:**
- Cost tracking requires custom implementation
- No unified dashboard for multiple models
- Manual API key management per provider

### Alternative 2: LiteLLM Proxy (Self-Hosted)

**Why Rejected:**
- Requires maintaining infrastructure
- No built-in cost dashboard
- Team must handle rate limiting manually

### Alternative 3: Multiple Direct Integrations

**Why Rejected:**
- Separate API keys for each provider
- Custom code for each provider's API
- No unified monitoring

## References

- OpenRouter Documentation: https://openrouter.ai/docs
- LangChain ChatOpenAI: https://python.langchain.com/docs/integrations/chat/openai
- Environment: `OPENROUTER_API_KEY` in Doppler

## Decision Drivers

1. **Cost Visibility**: Dashboard crucial for production cost management
2. **Developer Experience**: Single API key simplifies development
3. **Flexibility**: Easy model switching enables experimentation

## Trade-Off Analysis

**Latency (50ms) vs Monitoring Benefits:**
- Report generation takes ~5,000ms total
- 50ms overhead = 1% of total time
- Cost tracking benefit > 1% latency cost

**Verdict:** Monitoring benefits outweigh latency cost.
