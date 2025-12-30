# Architecture Inventory

**Purpose**: Complete inventory of tools, services, and APIs currently in use across the DR Daily Report project

**Last Updated**: 2025-12-28

---

## 1. External APIs

### Financial Data
- **yfinance** (v0.2.40+)
  - Purpose: Historical price data, OHLCV, technical indicators
  - Usage: Daily data fetching for 46 tickers
  - Cost: Free (Yahoo Finance API)

- **Twinbar API**
  - Purpose: Real-time quotes, fundamental data
  - Usage: Supplementary data source
  - Cost: Custom integration

### AI/LLM Services
- **OpenAI API** (SDK v1.0.0+)
  - Models: GPT-4, GPT-3.5-turbo
  - Purpose: Natural language report generation
  - Usage: Core report generation workflow
  - Cost: $0.03/1K tokens (GPT-4)

- **Langfuse** (v2.0.0+)
  - Purpose: LLM observability, quality scoring
  - Usage: 5-dimension scoring (Faithfulness, Completeness, Reasoning Quality, Compliance, QoS)
  - Cost: Free tier (self-hosted option available)

---

## 2. AWS Services (15+)

### Compute
- **Lambda**
  - Functions: `report_worker`, `ticker_fetcher`, `telegram_api`
  - Configuration: 512-1024MB memory, 30-60s timeout
  - Purpose: Serverless compute for all backend logic
  - Cost: Pay-per-invocation

- **ECS Fargate** (planned)
  - Purpose: Fund data sync (Docker containers)
  - Status: Future implementation

### Storage
- **S3**
  - Buckets: Data lake (historical data), dependencies (pip cache), frontend (static hosting)
  - Usage: Historical price storage, Lambda dependency layer cache, Telegram Mini App hosting
  - Cost: ~$0.023/GB/month

- **ECR**
  - Repositories: `telegram-api`, `fund-data-sync`
  - Purpose: Docker image registry for Lambda container images
  - Cost: ~$0.10/GB/month

### Database
- **Aurora MySQL** (Serverless v2)
  - Purpose: Source of truth for all data
  - Schema: 46 tickers, precomputed metrics, scoring results
  - Configuration: Auto-scaling 0.5-2 ACUs
  - Cost: ~$0.12/ACU-hour + storage

- **DynamoDB** (planned)
  - Purpose: Session management, caching layer
  - Usage: Telegram job tracking, cached reports
  - Cost: On-demand pricing

### Networking
- **API Gateway** (REST API)
  - Purpose: HTTP endpoint for Telegram webhooks
  - Integration: Lambda proxy integration
  - Cost: $1/million requests

- **CloudFront**
  - Purpose: CDN for Telegram Mini App static assets
  - Configuration: HTTPS only, compression enabled
  - Cost: ~$0.085/GB transfer

### Observability
- **CloudWatch**
  - Logs: All Lambda functions, API Gateway
  - Metrics: Invocations, errors, duration
  - Alarms: Error rate > 5%, latency p99 > 10s
  - Cost: ~$0.50/GB ingestion

### Orchestration
- **EventBridge**
  - Schedules: Nightly ticker data fetch (cron)
  - Purpose: Trigger Lambda functions on schedule
  - Cost: Free tier covers usage

### CI/CD
- **CodeBuild**
  - Purpose: Docker image builds for ECR
  - Usage: Triggered by GitHub Actions
  - Cost: ~$0.005/build minute

### Security
- **Secrets Manager**
  - Secrets: OpenAI API key, database credentials, Langfuse API key
  - Rotation: Manual (no auto-rotation)
  - Cost: $0.40/secret/month + $0.05/10K API calls

### Infrastructure
- **IAM**
  - Policies: Capability-based (6 policy groups)
  - Roles: Lambda execution roles, GitHub Actions OIDC
  - Purpose: Fine-grained permission management

- **VPC**
  - Subnets: Private (Aurora), Public (NAT Gateway)
  - Security Groups: Database access, Lambda egress
  - Purpose: Network isolation for Aurora

---

## 3. Python Libraries (25+)

### LLM/Agent Framework
- **LangGraph** (v0.2.0+) - Workflow orchestration
- **LangChain** (v0.2.0+) - LLM application framework
- **langchain-openai** (v0.1.0+) - OpenAI integration
- **langchain-core** (v0.2.0+) - Core abstractions
- **openai** (v1.0.0+) - OpenAI SDK
- **langfuse** (v2.0.0+) - LLM observability

### Data Science
- **pandas** (v2.0.0+) - DataFrame operations
- **numpy** (v1.24.0+) - Numerical computing
- **scipy** (v1.11.0+) - Scientific computing
- **scikit-learn** (v1.5.2) - Machine learning (pinned for Lambda wheels)
- **networkx** (v3.0+) - Graph analysis
- **matplotlib** (v3.7.0+) - Plotting

### Financial Analysis
- **yfinance** (v0.2.40+) - Yahoo Finance data
- **ta** (v0.11.0+) - Technical analysis indicators
- **qdrant-client** (v1.9.0+) - Vector database client

### Web Framework
- **FastAPI** (v0.109.0+) - Modern async web framework
- **Pydantic** (v2.5.0+) - Data validation
- **Uvicorn** (v0.27.0+) - ASGI server
- **Mangum** (v0.17.0+) - Lambda adapter for ASGI
- **slowapi** (v0.1.9+) - Rate limiting

### Database
- **PyMySQL** (v1.1.0+) - MySQL driver for Aurora
- **boto3** (v1.34.0+) - AWS SDK for Python

### Report Generation
- **reportlab** (v4.0.0+) - PDF generation
- **openpyxl** (v3.1.0+) - Excel file generation

### Testing
- **pytest** (v7.0.0+) - Test framework
- **moto** - AWS service mocking
- **radon** (v6.0.0+) - Code complexity analysis

### Utilities
- **python-dotenv** (v1.0.0+) - Environment variable loading
- **requests** (v2.31.0+) - HTTP client
- **flask** (v3.0.0+) - Development server

---

## 4. Frontend Technologies (20+)

### Core Framework
- **React** (v19.2.0) - UI library
- **TypeScript** (v5.9.3) - Type-safe JavaScript
- **Vite** (v7.2.4) - Build tool and dev server

### UI Components
- **Tailwind CSS** (v4.1.17) - Utility-first CSS framework
- **@tailwindcss/vite** (v4.1.17) - Vite plugin for Tailwind
- **@headlessui/react** (v2.2.9) - Unstyled accessible components
- **@heroicons/react** (v2.2.0) - SVG icon library

### Charting
- **Recharts** (v3.5.1) - Composable charting library
- Purpose: Portfolio performance, ticker charts, historical data visualization

### State Management
- **Zustand** (v5.0.9) - Lightweight state management
- Purpose: Global app state (user preferences, selected tickers, theme)

### Data Fetching
- **@tanstack/react-query** (v5.90.12) - Server state management
- Purpose: API data fetching, caching, synchronization

### Telegram Integration
- **@tma.js/sdk-react** (v3.0.11) - Telegram Mini App SDK
- Purpose: Access Telegram features (user info, theme, haptics, cloud storage)

### Testing
- **Vitest** (v4.0.15) - Unit test framework
- **@vitest/ui** (v4.0.15) - Test UI
- **@testing-library/react** (v16.3.0) - Component testing utilities
- **@testing-library/jest-dom** (v6.9.1) - Custom matchers
- **jsdom** (v27.3.0) - DOM implementation for testing
- **fast-check** (v4.4.0) - Property-based testing

### Development Tools
- **ESLint** (v9.39.1) - Linting
- **typescript-eslint** (v8.46.4) - TypeScript ESLint rules
- **eslint-plugin-react-hooks** (v7.0.1) - React Hooks linting
- **eslint-plugin-react-refresh** (v0.4.24) - React Refresh linting
- **@vitejs/plugin-react** (v5.1.1) - React plugin for Vite

---

## 5. Infrastructure as Code

### Terraform
- **Provider**: AWS (hashicorp/aws)
- **Modules**: Lambda, Aurora, S3, API Gateway, CloudFront, IAM, VPC, DynamoDB
- **State**: S3 backend with DynamoDB locking
- **Purpose**: Provision and manage all AWS infrastructure
- **Structure**: Modular design with reusable modules

### Tagging
- **Policy**: All resources tagged with `App`, `Environment`, `ManagedBy`
- **Purpose**: Cost allocation, resource organization, multi-app architecture
- **Reference**: See `terraform/TAGGING_POLICY.md`

---

## 6. Development Tools

### CLI Tools
- **dr CLI**
  - Implementation: Python Click framework
  - Groups: dev, test, build, deploy, clean, check, util (7 groups)
  - Purpose: Unified command interface (HOW layer)
  - Example: `dr test unit`, `dr deploy dev`, `dr build`

- **Justfile**
  - Purpose: Intent layer (WHEN/WHY)
  - Pattern: Recipes call `dr` commands
  - Example: `just test` → `dr test all`

### Version Control
- **Git** - Source control
- **GitHub** - Remote repository
- **GitHub Actions** - CI/CD automation
  - Workflows: Test, build, deploy (dev/staging/prod)
  - Deployment: ~8 min (dev), ~10 min (staging), ~12 min (prod)

### Secrets Management
- **Doppler**
  - Purpose: Environment variable and secrets management
  - Environments: dev, staging, prod
  - Usage: `doppler run -- {command}`

### Container Tools
- **Docker Desktop** - Local container runtime
- **Docker Compose** - Multi-container applications
- Purpose: Local development, Lambda container images

### Cloud Development
- **AWS CLI** (v2) - AWS service management
- **Terraform CLI** - Infrastructure provisioning

### Code Quality
- **pytest** - Python testing
- **radon** - Complexity analysis
- **ESLint** - JavaScript linting
- **TypeScript** - Type checking

---

## Quick Reference Table

| Category | Count | Primary Tools |
|----------|-------|---------------|
| External APIs | 4 | OpenAI, yfinance, Twinbar, Langfuse |
| AWS Services | 15+ | Lambda, Aurora, S3, API Gateway, CloudFront, DynamoDB |
| Python Libraries | 25+ | LangChain, LangGraph, FastAPI, pandas, pytest |
| Frontend Libraries | 20+ | React, Zustand, TanStack Query, Recharts, Tailwind CSS |
| Infrastructure | 1 | Terraform (AWS Provider) |
| Development Tools | 8+ | dr CLI, Justfile, Git, GitHub Actions, Doppler, Docker |

---

## Architecture Patterns

### Multi-App Architecture
- **LINE Bot**: Chat-based interface (maintenance mode)
- **Telegram Mini App**: Web dashboard (active development)
- **Shared Backend**: Identical core logic, separated via AWS tags

### Data Flow
```
User → Telegram Mini App (React)
  ↓
API Gateway → Lambda (FastAPI)
  ↓
Aurora MySQL (source of truth)
  ↓
S3 Data Lake (historical data)
```

### Deployment Pipeline
```
Git push → GitHub Actions
  ↓
Docker build → ECR
  ↓
Terraform apply → Lambda update
  ↓
Multi-layer verification (status, payload, CloudWatch)
```

---

## Technology Decisions

### Why Aurora MySQL?
- Source of truth philosophy
- Precomputed nightly data (46 tickers)
- Read-only APIs (fail-fast if data missing)
- Consistent performance

### Why Zustand over Redux?
- Simplicity (100 lines vs 500+ lines)
- Hooks-based (familiar to team)
- Bundle size: 1KB vs 8KB
- Sufficient for current complexity

### Why FastAPI?
- Native async/await support
- Automatic OpenAPI docs
- Pydantic data validation
- Lambda integration via Mangum

### Why Terraform?
- Infrastructure as Code (version controlled)
- Modular design (reusable components)
- State management (S3 + DynamoDB locking)
- AWS provider maturity

---

## Adding New Tools

**Process**:
1. Update this inventory document
2. Add to `PROJECT_CONVENTIONS.md` technology stack section
3. Pin version in `requirements.txt` (Python) or `package.json` (frontend)
4. Update Terraform if infrastructure is required
5. Journal the decision: `/journal architecture "Why we chose {tool}"`
6. Update relevant skill documentation if pattern changes

**Example**:
```bash
# Adding new Python library
echo "new-library>=1.0.0" >> requirements.txt
pip install -r requirements.txt

# Document decision
/journal architecture "Added new-library for {purpose} because {rationale}"

# Update inventory
# Edit this file and PROJECT_CONVENTIONS.md
```

---

## Deprecation & Migration

### Legacy (Maintenance Mode)
- **LINE Bot integration**
  - Status: Feature-frozen, bug fixes only
  - Reason: Focusing on Telegram Mini App
  - Migration: Not planned

### Planned Migrations
- **DynamoDB → Aurora** (under consideration)
  - Goal: Simplify stack (single database)
  - Blocker: DynamoDB performance for caching
  - Decision: Pending performance analysis

- **SQLAlchemy adoption** (under consideration)
  - Goal: ORM for type-safe database access
  - Blocker: Additional complexity
  - Decision: Pending team consensus

---

## Tool Version Philosophy

### Pinning Strategy
- **Exact pins** (scikit-learn==1.5.2): When Lambda wheels are critical
- **Major version** (pandas>=2.0.0,<3.0.0): Allow minor/patch updates
- **Caret** (React ^19.2.0): npm semantic versioning

### Update Cadence
- **Security patches**: Immediate (Dependabot)
- **Minor versions**: Quarterly review
- **Major versions**: Planned migration with testing

---

## Cost Breakdown (Estimated)

| Category | Monthly Cost (dev) | Monthly Cost (prod) |
|----------|-------------------|---------------------|
| Lambda | ~$5 | ~$50 |
| Aurora MySQL | ~$10 | ~$80 |
| S3 + CloudFront | ~$5 | ~$20 |
| DynamoDB | ~$1 | ~$10 |
| OpenAI API | ~$20 | ~$200 |
| Secrets Manager | ~$2 | ~$5 |
| Other AWS | ~$5 | ~$15 |
| **Total** | **~$48** | **~$380** |

*Estimates based on current usage patterns. Actual costs may vary.*

---

## Related Documentation

- [Project Conventions](PROJECT_CONVENTIONS.md) - Directory structure, naming patterns, CLI commands
- [Technology Stack ADRs](adr/README.md) - Architecture Decision Records
- [Deployment Guide](deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md) - Step-by-step deployment
- [AWS Setup](AWS_SETUP.md) - IAM permissions and configuration
- [Tagging Policy](../terraform/TAGGING_POLICY.md) - AWS resource tagging standards

---

## Verification Commands

**Check Python dependencies**:
```bash
cat requirements.txt
pip list | grep -E "(langchain|openai|fastapi|pandas)"
```

**Check frontend dependencies**:
```bash
cat frontend/twinbar/package.json
cd frontend/twinbar && npm list --depth=0
```

**Check AWS resources**:
```bash
# Lambda functions
aws lambda list-functions --query 'Functions[*].FunctionName'

# S3 buckets
aws s3 ls

# Aurora clusters
aws rds describe-db-clusters --query 'DBClusters[*].DBClusterIdentifier'
```

**Check Terraform state**:
```bash
cd terraform
terraform state list | head -20
```

---

**Maintained by**: Development team
**Update frequency**: Quarterly or when adding/removing major tools
**Last review**: 2025-12-28
