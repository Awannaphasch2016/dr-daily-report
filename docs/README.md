# Documentation Index

Complete documentation for DR Daily Report Telegram Mini App.

---

## Documentation Structure

This project uses a tiered documentation system:

- **Authoritative Docs** (`docs/features/`, `docs/deployment/`) - Permanent, maintained documentation for production systems
- **Temporary Analysis** (`docs/tmp/`) - WIP docs, analysis notes, implementation summaries (not maintained)
- **Archived Context** (`docs/archive/`) - Completed migration docs, historical context (reference only)

---

## Getting Started

- [Quick Start](QUICKSTART.md) - 5-minute setup guide
- [CLI Reference](cli.md) - Complete command guide
- [AWS Setup](AWS_SETUP.md) - IAM permissions and configuration
- [AWS Operations](AWS_OPERATIONS.md) - Quick reference for AWS service commands (EC2, Aurora, Lambda)

---

## Development

- [Architecture](../.claude/CLAUDE.md) - Principles, patterns, and architectural decisions
- [Codebase Investigation](CODEBASE_INVESTIGATION.md) - System architecture deep-dive
- [API Contract](../spec/API_CONTRACT.md) - Backend/frontend API specification
- [UI Principles](frontend/UI_PRINCIPLES.md) - React/TypeScript patterns, state management, property-based testing
- [Testing Guide](testing/TESTING_GUIDE.md) - How to run tests
- [E2E Testing](testing/E2E_TESTING.md) - Playwright browser tests
- [Database Migrations](DATABASE_MIGRATIONS.md) - Schema management and migration patterns

---

## Deployment

- [Deployment Runbook](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) - Step-by-step deployment guide
- [S3 Deployment](deployment/S3_DEPLOYMENT.md) - S3 caching, dependency loading, data lake
- [Permissions Required](deployment/PERMISSIONS_REQUIRED.md) - Complete IAM policy reference
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

---

## Features

### Report Quality & Scoring
- [Scoring System](features/SCORING_SYSTEM.md) - Comprehensive 5-dimension quality scoring (Faithfulness, Completeness, Reasoning Quality, Compliance, QoS)

### Infrastructure Integration
- [PDF Generation](features/PDF_GENERATION.md) - PDF report generation and storage
- [MCP Integration](features/MCP_INTEGRATION.md) - Model Context Protocol server integration
- [News Feature](features/NEWS_FEATURE.md) - News data integration

---

## Reference

### Infrastructure
- [Tagging Policy](../terraform/TAGGING_POLICY.md) - AWS resource tagging standards
- [API Implementation](../src/api/README.md) - FastAPI implementation guide
- [Type System Integration](TYPE_SYSTEM_INTEGRATION.md) - Cross-system type compatibility patterns

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
| Configure S3 caching | [S3 Deployment](deployment/S3_DEPLOYMENT.md) |
| Fix deployment error | [Troubleshooting](TROUBLESHOOTING.md) |
| Write E2E test | [E2E Testing](testing/E2E_TESTING.md) |
| Understand architecture | [CLAUDE.md](../.claude/CLAUDE.md) |
| Check API contract | [API_CONTRACT.md](../spec/API_CONTRACT.md) |
| Understand scoring system | [Scoring System](features/SCORING_SYSTEM.md) |
| Set up MCP servers | [MCP Integration](features/MCP_INTEGRATION.md) |
| Generate PDFs | [PDF Generation](features/PDF_GENERATION.md) |

---

## Contributing

See [.claude/CLAUDE.md](../.claude/CLAUDE.md) for:
- Code organization principles
- Testing guidelines
- Deployment workflow
- When to update CLAUDE.md vs docs/

---

## Archive & Temporary Docs

- **Archive** (`docs/archive/`) - Completed migrations, historical context
  - IAM AssumeRole migration docs
  - Terraform migration summaries

- **Temporary** (`docs/tmp/`) - Analysis notes, implementation summaries, WIP docs
  - Analysis documents (validation, fixes, implementation summaries)
  - Duplicate/superseded documentation (PDF, MCP, Scoring, S3)
  - Reference only - not maintained
