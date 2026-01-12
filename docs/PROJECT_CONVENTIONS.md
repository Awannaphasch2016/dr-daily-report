# Project Conventions

**Purpose**: Centralized reference for project structure, naming patterns, CLI commands, and extension points.

This document contains factual information about how the codebase is organized. For architectural principles and patterns, see [CLAUDE.md](../.claude/CLAUDE.md). For coding style guidelines, see [CODE_STYLE.md](CODE_STYLE.md).

---

## Table of Contents

- [Directory Structure](#directory-structure)
- [Naming Conventions](#naming-conventions)
  - [Versioning Standards](#versioning-standards)
- [CLI Commands](#cli-commands)
- [Module Organization](#module-organization)
- [Extension Points](#extension-points)
- [Python Environment Management](#python-environment-management)
- [File Locations Reference](#file-locations-reference)

---

## Directory Structure

**High-level organization:**

```
dr-daily-report_telegram/
├── .claude/                   # Claude Code configuration
│   ├── skills/               # Executable workflows and checklists
│   └── CLAUDE.md             # Development contract (ground truth)
├── data/                      # Local data files (CSV, SQLite)
├── db/migrations/             # Aurora MySQL schema migrations
├── docs/                      # Comprehensive documentation
│   ├── adr/                  # Architecture Decision Records
│   ├── deployment/           # Deployment guides and runbooks
│   ├── features/             # Feature-specific documentation
│   └── frontend/             # UI/UX principles
├── dr_cli/                    # CLI implementation (dr command)
├── fonts/                     # Thai fonts for PDF generation
├── frontend/twinbar/          # Telegram Mini App (React + TypeScript)
├── scripts/                   # Utility scripts (migrations, testing)
├── src/                       # Application source code
│   ├── agent.py              # Main LangGraph agent
│   ├── analysis/             # Semantic state generation
│   ├── api/                  # Telegram REST API (FastAPI)
│   ├── data/                 # Data fetching and caching
│   ├── formatters/           # Chart and PDF generation
│   ├── integrations/         # External services (LINE, MCP)
│   ├── lambda_handlers/      # AWS Lambda entry points
│   ├── report/               # Report generation logic
│   ├── scheduler/            # Precompute scheduler handlers
│   ├── scoring/              # Quality scoring metrics
│   ├── utils/                # Shared utilities
│   └── workflow/             # LangGraph workflow nodes
├── terraform/                 # Infrastructure as Code
│   ├── envs/                 # Environment-specific configs
│   ├── modules/              # Reusable Terraform modules
│   └── policies/             # OPA policy tests
├── tests/                     # Test suite (pytest)
│   ├── conftest.py           # Shared fixtures ONLY
│   ├── shared/               # Agent, workflow, data tests
│   ├── telegram/             # Telegram API tests
│   ├── line_bot/             # LINE Bot tests (legacy)
│   ├── e2e/                  # Playwright browser tests
│   ├── integration/          # External API tests
│   └── infrastructure/       # S3, DynamoDB, Aurora tests
└── justfile                   # Task runner (intent layer)
```

**Domain-Driven Structure Philosophy:**

Modules are organized by **business domain** (agent, data, workflow, api), not technical layer (models, services, controllers). This:
- Encapsulates each domain with clear boundaries
- Avoids God objects and cross-cutting concerns
- Makes it easy to find code related to a feature

---

## Naming Conventions

### Files
- `snake_case.py` - All Python files
- `test_*.py` - Test files (prefix with `test_`)
- `*.md` - Documentation (Markdown)

### Classes
- `PascalCase` - Class names
  - Examples: `TickerAnalysisAgent`, `MiniReportGenerator`, `DataFetcher`

### Functions and Methods
- `snake_case()` - All functions and methods
  - Examples: `fetch_ticker_data()`, `generate_report()`, `calculate_score()`
- `_snake_case()` - Private methods (prefix with underscore)
  - Examples: `_validate_input()`, `_format_output()`

### Constants
- `UPPER_SNAKE_CASE` - Module-level constants
  - Examples: `LOOKBACK_DAYS = 365`, `DEFAULT_STRATEGY = "multi-stage"`

### Type Definitions
- `PascalCase` - TypedDict classes
  - Examples: `AgentState`, `ReportMetadata`, `TickerData`

### Environment Variables
- `UPPER_SNAKE_CASE` - All environment variables
  - Examples: `AURORA_HOST`, `OPENROUTER_API_KEY`, `PDF_BUCKET_NAME`

### Versioning Standards

Every deployed artifact must be traceable to its source code commit. Use the appropriate versioning format based on context:

| Context | Purpose | Format | Example |
|---------|---------|--------|---------|
| **Release** | What version is running? | `{env}-{semver\|branch}-{sha}` | `prd-v1.2.3-abc1234` |
| **Artifact** | Which build is this? | Timestamp or digest | `v20251201182404` |
| **Algorithm** | Which logic version? | SemVer | `computation_version: 2.0` |

**Component-specific versioning**:

| Component | Version Type | Location | Set By |
|-----------|-------------|----------|--------|
| Lambda functions | Artifact | Docker image tag | CI/CD |
| Langfuse traces | Release | `LANGFUSE_RELEASE` env var | CI/CD |
| Data Lake computations | Algorithm | `computation_version` field | Code |
| Frontend (twinbar) | Release | `package.json` version | Manual |
| API responses | Release | `agent_version` field | Code |
| Git releases | Release | Tags `v*.*.*` | Manual |

**CI/CD automation** (required for Release versions):
```yaml
# GitHub Actions example
- name: Set Release Version
  run: |
    SHORT_SHA="${GITHUB_SHA::7}"
    if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
      RELEASE="prd-${{ github.ref_name }}-${SHORT_SHA}"
    elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      RELEASE="stg-main-${SHORT_SHA}"
    else
      RELEASE="dev-dev-${SHORT_SHA}"
    fi
    echo "LANGFUSE_RELEASE=${RELEASE}" >> $GITHUB_ENV
```

**Anti-patterns**:
- ❌ Environment-only versioning (`dev`, `prd`) - no traceability
- ❌ Manual version updates in Doppler - forgotten, out of sync
- ❌ Different formats for same context - confusion

See [CLAUDE.md Principle #22](../.claude/CLAUDE.md#22-llm-observability-discipline) for Langfuse-specific versioning.

---

## CLI Commands

The project uses a **two-layer CLI design**:

1. **Justfile** (Intent Layer) - Describes WHEN/WHY to run commands
   - Recipe names like `pre-commit`, `test-changes`, `ship-it`
   - Human-readable descriptions

2. **dr CLI** (Implementation Layer) - Explicit syntax for HOW
   - Clean, consistent commands like `dr dev server`, `dr test file`
   - Good `--help` system

### Top 15 Most-Used Commands

#### Development

```bash
# Start local development server
just dev                  # Shortcut: justfile recipe
dr dev server             # Explicit: dr CLI command

# Python shell with imports
just shell
dr dev shell

# Install dependencies
just setup
dr dev install
```

#### Testing

```bash
# Quick test (changed files only)
just test-changes         # Git diff-based selection

# Full test suite
just test
dr test all

# Deploy gate (run before deploy)
just test-deploy          # Tier 1: unit + mocked

# Specific test file
dr test file tests/telegram/test_rankings_service.py

# Test tiers
pytest --tier=0           # Unit tests only
pytest --tier=2           # + Integration tests
pytest --tier=3           # + Smoke tests
pytest --tier=4           # + E2E tests
```

#### Code Quality

```bash
# Format code
just format               # Black formatter

# Lint check
just lint                 # Ruff linter

# Pre-commit checks (format + lint + test)
just pre-commit

# Syntax check
just check
dr check syntax
```

#### Utilities

```bash
# Generate ticker report (local)
just report DBS19
dr utils report DBS19

# Project statistics
just stats

# Directory tree
just tree

# Clean build artifacts
dr clean build
dr clean cache
```

#### Deployment

```bash
# Deploy to dev (requires AWS credentials)
git push origin dev       # Triggers GitHub Actions

# Promote to staging
gh pr create --base main --head dev
gh pr merge

# Deploy to production
git tag v1.2.0
git push origin v1.2.0
```

For complete CLI reference, see [docs/cli.md](cli.md).

---

## Module Organization

**Standard module template:**

```python
# -*- coding: utf-8 -*-  # For files with Thai content
"""
Module description.

Detailed explanation of module purpose and key components.
"""

# 1. Standard library imports
import logging
import json
from datetime import datetime
from pathlib import Path

# 2. Third-party imports
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

# 3. Local imports
from src.types import AgentState
from src.data.data_fetcher import DataFetcher


# Module-level constants
LOOKBACK_DAYS = 365
DEFAULT_STRATEGY = "multi-stage"

# Module-level logger
logger = logging.getLogger(__name__)


class MainClass:
    """Class description."""

    def __init__(self, dependencies):
        """Initialize with dependencies."""
        self.dependency = dependencies

    def public_method(self, param: Type) -> ReturnType:
        """Public method with full docstring."""
        pass

    def _private_method(self, param: Type) -> ReturnType:
        """Private helper method (brief docstring)."""
        pass
```

**Import Order (enforced by isort):**

1. **Standard library** - `import logging`, `from datetime import datetime`
2. **Third-party packages** - `import pandas`, `from langchain_core import messages`
3. **Local imports** - `from src.types import AgentState`, `from src.data import DataFetcher`

**Why This Order:**
- Standard library is always available (least likely to change)
- Third-party dependencies are external (may upgrade)
- Local imports are internal (most likely to change)

---

## Extension Points

The codebase has **four primary extension points**, each with specific integration requirements:

### 1. Adding Scoring Metrics

**Location**: `src/scoring/`

**Pattern:**
1. Create scorer class in `src/scoring/<metric>_scorer.py`
2. Implement `score()` method returning dict with `{'score': float, 'feedback': str, 'passed': bool}`
3. Integrate into `src/workflow/workflow_nodes.py`
4. Extend `AgentState` TypedDict in `src/types.py` (if needed)
5. Run validation tests to ensure scoring contract

**Example:**
```python
# src/scoring/my_metric_scorer.py
class MyMetricScorer:
    def score(self, state: AgentState) -> Dict[str, Any]:
        return {
            'score': 0.85,
            'feedback': 'Detailed feedback...',
            'passed': True
        }
```

**Tests**: `tests/scoring/test_my_metric_scorer.py`

**See**: [Code Style Guide](CODE_STYLE.md#module-organization-pattern)

### 2. Adding CLI Commands

**Location**: `dr_cli/commands/`

**Pattern:**
1. Create command module in `dr_cli/commands/<group>.py`
2. Use Click decorators for command structure
3. Add Justfile recipe for intent layer (WHEN/WHY)
4. Test with `--help` flag

**Example:**
```python
# dr_cli/commands/utils.py
import click

@click.command()
@click.argument('ticker')
def report(ticker: str):
    """Generate ticker report."""
    # Implementation
```

**Justfile recipe:**
```makefile
# Generate ticker report (intent: quick local testing)
report TICKER:
    dr utils report {{TICKER}}
```

**Two-Layer Design:**
- **Justfile**: Intent-based recipes (WHEN/WHY - e.g., `pre-commit`, `test-changes`)
- **dr CLI**: Explicit syntax (HOW - e.g., `dr test file`, `dr dev server`)

**See**: [CLI Architecture](cli.md#architecture)

### 3. Extending State (AgentState TypedDict)

**Location**: `src/types.py`

**Pattern:**
1. Update `AgentState` TypedDict definition
2. Add workflow node that populates the field
3. Ensure field is JSON-serializable (for Lambda responses)

**Example:**
```python
# src/types.py
class AgentState(TypedDict):
    ticker: str
    ticker_data: Dict[str, Any]
    my_new_field: Optional[Dict[str, Any]]  # Add here
```

**Constraints:**
- All state fields must be JSON-serializable (NumPy types require conversion)
- Use `Optional[T]` for fields that may not exist
- Document field purpose in docstring

**See**: [Workflow State Management](CODE_STYLE.md#workflow-state-management-patterns)

### 4. Adding API Endpoints

**Location**: `src/api/`

**Pattern:**
1. Create service singleton in `src/api/<service>_service.py`
2. Define Pydantic models for request/response in `src/api/models.py`
3. Add FastAPI route in `src/api/app.py`
4. Write integration tests in `tests/telegram/`

**Example:**
```python
# src/api/my_service.py
class MyService:
    def __init__(self):
        # Singleton initialization
        pass

    def get_data(self, ticker: str) -> Dict[str, Any]:
        # Sync method for LangGraph
        pass

    async def get_data_async(self, ticker: str) -> Dict[str, Any]:
        # Async method for FastAPI
        return self.get_data(ticker)

# Singleton instance
my_service = MyService()
```

**Async/Sync Dual Methods:**
- LangGraph workflows require **sync** methods
- FastAPI endpoints require **async** methods
- Pattern: Implement sync first, wrap in async for API

**See**: [API Architecture Patterns](CODE_STYLE.md#telegram-api-architecture-patterns)

---

## Python Environment Management

**Virtual Environment**: Shared venv via symlink to parent project (`dr-daily-report`)

**Setup**:
```bash
# Activate shared virtual environment (via symlink)
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install DR CLI in editable mode
pip install -e .
```

**Verification**: `dr dev verify` checks venv integrity

**Why shared venv**:
- **Consistency**: All 4 repositories use identical package versions
- **Disk efficiency**: 75% savings (500MB shared vs 2GB isolated)
- **Simplicity**: One venv to manage across ecosystem
- **Development speed**: Updates immediately available to all projects

**Troubleshooting**:
```bash
# Check if venv is symlink
ls -la venv
# Should show: venv -> ../dr-daily-report/venv

# Verify Python path
which python
# Should point to: .../dr-daily-report/venv/bin/python

# If symlink broken, create isolated venv (fallback)
rm venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**See**: [CLAUDE.md Principle #18](../.claude/CLAUDE.md#18-shared-virtual-environment-pattern) for complete details and rationale

---

## File Locations Reference

**Where to find key components:**

### Configuration
- **Environment variables**: Managed via Doppler (environment isolation container - holds ALL env-specific config, not just secrets)
- **Doppler → Terraform**: `TF_VAR_*` prefixed secrets in Doppler become Terraform variables
- **AWS infrastructure**: `terraform/` (IaC definitions)
- **Environment configs**: `terraform/envs/{dev,staging,prod}/` (static values that don't vary by env)
- **Lambda settings**: `terraform/*_lambda.tf` files
- See [Doppler Config Guide](deployment/DOPPLER_CONFIG.md) and [CLAUDE.md Principle #23](../.claude/CLAUDE.md#23-configuration-variation-axis)

### Tests
- **Shared tests** (agent, workflow, data): `tests/shared/`
- **Telegram API tests**: `tests/telegram/`
- **LINE Bot tests**: `tests/line_bot/` (mark with `@pytest.mark.legacy`)
- **E2E browser tests**: `tests/e2e/` (require Playwright)
- **Integration tests**: `tests/integration/` (external APIs)
- **Infrastructure tests**: `tests/infrastructure/` (S3, DynamoDB, Aurora)
- **Test fixtures**: `tests/conftest.py` (shared fixtures ONLY)

### Workflows
- **LangGraph agent**: `src/agent.py` (main entry point)
- **Workflow nodes**: `src/workflow/workflow_nodes.py`
- **Semantic state generation**: `src/analysis/semantic_state_generator.py`

### Documentation
- **Architecture decisions**: `docs/adr/` (ADRs)
- **Deployment guides**: `docs/deployment/`
- **Feature docs**: `docs/features/`
- **API reference**: `docs/API_USAGE.md`
- **Database migrations**: `docs/DATABASE_MIGRATIONS.md`

### Database
- **Migration files**: `db/migrations/` (numbered SQL files)
- **Migration scripts**: `scripts/run_aurora_migration*.py`
- **Schema validation**: `scripts/validate_aurora_schema.py`

### Lambda Handlers
- **Telegram API**: `src/telegram_lambda_handler.py`
- **Report worker**: `src/report_worker_handler.py`
- **Scheduler**: `src/scheduler/*_handler.py`
- **Fund data sync**: `src/lambda_handlers/fund_data_sync_handler.py`

---

## See Also

- [CLAUDE.md](../.claude/CLAUDE.md) - Development contract (ground truth)
- [CODE_STYLE.md](CODE_STYLE.md) - Coding style and patterns
- [docs/cli.md](cli.md) - Complete CLI reference
- [docs/README.md](README.md) - Documentation index
- [docs/QUICKSTART.md](QUICKSTART.md) - Getting started guide
