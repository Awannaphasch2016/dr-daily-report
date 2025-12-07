# Documentation Index

Complete documentation for DR Daily Report Telegram Mini App.

---

## Getting Started

- [Quick Start](QUICKSTART.md) - 5-minute setup guide
- [CLI Reference](cli.md) - Complete command guide
- [AWS Setup](AWS_SETUP.md) - IAM permissions and configuration

---

## Development

- [Architecture](.claude/CLAUDE.md) - Principles, patterns, and architectural decisions
- [API Contract](../spec/API_CONTRACT.md) - Backend/frontend API specification
- [Testing Guide](testing/TESTING_GUIDE.md) - How to run tests
- [E2E Testing](testing/E2E_TESTING.md) - Playwright browser tests

---

## Deployment

- [Deployment Runbook](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) - Step-by-step deployment guide
- [Permissions Required](deployment/PERMISSIONS_REQUIRED.md) - Complete IAM policy reference
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

## Reference

### Scoring System
- [Faithfulness Scoring](architecture/scoring/FAITHFULNESS_SCORING.md)
- [Completeness Scoring](architecture/scoring/COMPLETENESS_SCORING.md)
- [Reasoning Quality Scoring](architecture/scoring/REASONING_QUALITY_SCORING.md)
- [Compliance Scoring](architecture/scoring/COMPLIANCE_SCORING.md)
- [QoS Scoring](architecture/scoring/QOS_SCORING.md)

### Infrastructure
- [Tagging Policy](../terraform/TAGGING_POLICY.md) - AWS resource tagging standards
- [API Implementation](../src/api/README.md) - FastAPI implementation guide

### Features
- [News Feature](features/NEWS_FEATURE.md)
- [LangSmith Integration](features/LANGSMITH_INTEGRATION.md)

---

## Product Documentation

- [Telegram Mini App PRD](../spec/telegram_miniapp_prd.md) - Product requirements
- [Evaluation Setup](architecture/EVALUATION_SETUP.md) - Quality evaluation framework
- [Bot Reasoning Design](architecture/BOT_REASONING_DESIGN.md) - LLM reasoning patterns

---

## Quick Links

| Task | Documentation |
|------|--------------|
| First-time setup | [Quick Start](QUICKSTART.md) |
| Deploy to production | [Deployment Runbook](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) |
| Fix deployment error | [Troubleshooting](TROUBLESHOOTING.md) |
| Write E2E test | [E2E Testing](testing/E2E_TESTING.md) |
| Understand architecture | [CLAUDE.md](.claude/CLAUDE.md) |
| Check API contract | [API_CONTRACT.md](../spec/API_CONTRACT.md) |

---

## Contributing

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for:
- Code organization principles
- Testing guidelines
- Deployment workflow
- When to update CLAUDE.md vs docs/
