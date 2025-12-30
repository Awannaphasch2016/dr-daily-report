---
name: onboard
description: Generate personalized onboarding checklist for new developers
accepts_args: true
arg_schema:
  - name: focus_area
    required: false
    description: "Optional focus: backend, frontend, infrastructure, deployment, testing (default: all)"
composition:
  - skill: research
---

# /onboard - Developer Onboarding Checklist Generator

**Purpose**: Generate personalized onboarding checklist by analyzing codebase structure, setup requirements, and common pitfalls

**Category**: Developer Experience

**When to use**:
- New developer joining project (full onboarding)
- Switching focus areas (backend → frontend)
- After long absence from project (re-onboarding)
- Onboarding contractor or intern (focused checklist)

**Core Principle**: "Onboarding should be systematic, documented, and include learned lessons"

---

## Usage

```bash
# Full onboarding (all areas)
/onboard

# Backend-focused (Python, AWS, APIs)
/onboard backend

# Frontend-focused (React, TypeScript, Telegram Mini App)
/onboard frontend

# Infrastructure-focused (Terraform, AWS, deployment)
/onboard infrastructure

# Deployment-focused (CI/CD, multi-environment)
/onboard deployment

# Testing-focused (pytest, Vitest, E2E)
/onboard testing
```

---

## Output Structure

### Onboarding Checklist Template

```markdown
# Onboarding Checklist: {Focus Area}

**Generated**: 2025-12-28
**Estimated Time**: {X} hours
**Target Audience**: {New developer/Contractor/Intern}

---

## Phase 1: Prerequisites (30 min)

### Tools to Install

**Required** (must have):
- [ ] Python 3.11+ (`python --version`)
- [ ] Node.js 18+ (`node --version`)
- [ ] Docker Desktop (`docker --version`)
- [ ] AWS CLI v2 (`aws --version`)
- [ ] Git (`git --version`)

**Optional** (focus-specific):

{If backend}:
- [ ] PyCharm or VS Code with Python extension
- [ ] `pytest` (`pip install pytest`)

{If frontend}:
- [ ] VS Code with ESLint, Prettier, TypeScript extensions
- [ ] npm or pnpm (`npm --version`)

{If infrastructure}:
- [ ] Terraform CLI (`terraform --version`)
- [ ] AWS Console access (request from DevOps)

{If deployment}:
- [ ] GitHub CLI (`gh --version`)
- [ ] Doppler CLI (`doppler --version`)

{If testing}:
- [ ] Playwright (`npx playwright --version`)
- [ ] Chrome/Chromium browser

**Installation guides**:
- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/
- Docker: https://www.docker.com/products/docker-desktop/
- AWS CLI: https://aws.amazon.com/cli/
- Terraform: https://www.terraform.io/downloads

---

### Access Required

**Critical** (cannot proceed without):
- [ ] GitHub repository access (read/write)
  - Repository: `dr-daily-report_telegram`
  - Request from: Team lead
  - Verification: `git clone https://github.com/org/dr-daily-report_telegram.git`

- [ ] Doppler access (secrets management)
  - Project: `dr-daily-report`
  - Environments: dev, staging (prod after 1 week)
  - Request from: DevOps
  - Verification: `doppler projects list`

**Important** (needed for actual work):
- [ ] AWS Console access (IAM user with capability-based policies)
  - Capabilities: See `docs/deployment/PERMISSIONS_REQUIRED.md`
  - Request from: DevOps
  - Verification: `aws s3 ls` (should show buckets)

- [ ] OpenAI API key (development, not production)
  - Purpose: Local testing of report generation
  - Request from: Team lead
  - Add to: `.env.local` file

**Optional** (nice to have):
- [ ] Langfuse account (LLM observability)
- [ ] Datadog/CloudWatch access (monitoring)

---

## Phase 2: Environment Setup (1 hour)

### Step 1: Clone Repository

```bash
# Clone main repository
git clone https://github.com/org/dr-daily-report_telegram.git
cd dr-daily-report_telegram

# Checkout dev branch (default branch for development)
git checkout dev

# Verify repository structure
ls -la
# Should see: src/, frontend/, terraform/, docs/, .claude/
```

**Expected**: Repository cloned, dev branch checked out

---

### Step 2: Install Backend Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(langchain|openai|fastapi|pandas)"
```

**Expected**: All dependencies installed, no errors

**Common issue**: scikit-learn build fails
**Solution**: Use Python 3.11 (pinned version has pre-built wheels)

---

### Step 3: Install Frontend Dependencies (if frontend focus)

```bash
cd frontend/twinbar

# Install dependencies
npm install

# Verify installation
npm list --depth=0

# Should see: react@19.2.0, zustand@5.0.9, tailwindcss@4.1.17
```

**Expected**: Dependencies installed, no vulnerabilities

---

### Step 4: Configure Secrets (Doppler)

```bash
# Setup Doppler (run in project root)
doppler setup

# Select project: dr-daily-report
# Select config: dev

# Verify secrets available
doppler secrets list

# Test secret access
doppler run -- echo $OPENAI_API_KEY
# Should show: sk-...
```

**Expected**: Doppler configured, secrets accessible

**Common issue**: `doppler: command not found`
**Solution**: Install Doppler CLI: `brew install dopplerhq/cli/doppler` (macOS)

---

### Step 5: Verify Setup

```bash
# Run backend tests
dr test unit
# Should see: All tests pass

# Start dev server
dr dev
# Should start on: http://localhost:8000

# Test API endpoint (in new terminal)
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

**Expected**: Tests pass, dev server starts, health check works

**Common issue**: Import errors, module not found
**Solution**: Ensure virtual environment activated: `source venv/bin/activate`

---

## Phase 3: Required Reading (30 min)

**Essential** (read in order):

1. [ ] **`.claude/CLAUDE.md`** (15 min)
   - Core principles (Defensive Programming, Multi-Layer Verification, Aurora-First)
   - Read sections: Core Principles, Extension Points
   - Why critical: Explains WHY we do things, not just HOW

2. [ ] **`docs/PROJECT_CONVENTIONS.md`** (10 min)
   - Directory structure, naming patterns, CLI commands
   - Read sections: Directory Structure, CLI Commands, Extension Points
   - Why critical: Find files quickly, understand organization

3. [ ] **`docs/README.md`** (5 min)
   - Documentation index, quick links
   - Skim: Get overview of what docs exist
   - Why critical: Know where to look when stuck

**Focus-Specific Reading**:

{If backend}:
4. [ ] **`.claude/skills/testing-workflow/`** (10 min)
   - Testing anti-patterns, tier system, round-trip tests
5. [ ] **`docs/DATABASE_MIGRATIONS.md`** (10 min)
   - Reconciliation migrations, immutability principle
6. [ ] **`docs/CODE_STYLE.md#error-handling-patterns`** (5 min)
   - State-based vs exceptions, when to use each

{If frontend}:
4. [ ] **`docs/frontend/UI_PRINCIPLES.md`** (15 min)
   - React patterns, state management (Zustand), property-based testing
5. [ ] **`frontend/twinbar/README.md`** (5 min)
   - Telegram Mini App setup, development workflow
6. [ ] **`spec/telegram_miniapp_prd.md`** (10 min)
   - Product requirements, features, user flows

{If infrastructure}:
4. [ ] **`docs/AWS_SETUP.md`** (10 min)
   - IAM permissions, capability-based policies
5. [ ] **`terraform/TAGGING_POLICY.md`** (5 min)
   - AWS resource tagging standards
6. [ ] **`docs/deployment/MULTI_ENV.md`** (10 min)
   - Multi-environment deployment (dev/staging/prod)

{If deployment}:
4. [ ] **`docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`** (15 min)
   - Step-by-step deployment process
5. [ ] **`.claude/skills/deployment/`** (10 min)
   - Zero-downtime deployment, immutable artifacts
6. [ ] **`docs/deployment/PERMISSIONS_REQUIRED.md`** (5 min)
   - IAM policies for deployment

{If testing}:
4. [ ] **`.claude/skills/testing-workflow/`** (15 min)
   - Testing patterns, anti-patterns, tier system
5. [ ] **`docs/testing/E2E_TESTING.md`** (10 min)
   - Playwright E2E tests, browser automation
6. [ ] **`docs/testing/TESTING_GUIDE.md`** (5 min)
   - How to run tests, test organization

---

## Phase 4: Common Pitfalls (know these)

### Pitfall 1: Lambda Timeout in Local Testing

**Symptom**: Tests pass locally, fail in Lambda with timeout error

**Cause**: Local dev has no timeout limit, Lambda times out at 30-60s

**Solution**: Use Lambda Runtime Interface Emulator (RIE)
```bash
dr test lambda  # Uses Docker + RIE, simulates Lambda environment
```

**Prevention**: Run `dr test lambda` before deploying

---

### Pitfall 2: Missing Doppler Secrets

**Symptom**: `KeyError: 'OPENAI_API_KEY'` or similar

**Cause**: Doppler not configured or not running in Doppler context

**Solution**:
```bash
# Ensure Doppler configured
doppler setup

# Always run commands with Doppler prefix
doppler run -- dr dev
doppler run -- pytest
```

**Prevention**: Add to shell profile: `alias dr='doppler run -- dr'`

---

### Pitfall 3: Aurora Connection Refused (Local)

**Symptom**: `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")`

**Cause**: Aurora is in private VPC, not accessible from local machine

**Solution**: Development uses mocked data, not actual Aurora
```python
# Tests use pytest fixtures with mock data
# See: tests/conftest.py for database mocks
```

**Prevention**: Read "Loud Mock Pattern" in `.claude/CLAUDE.md`

---

### Pitfall 4: Frontend CORS Errors

**Symptom**: `Cross-Origin Request Blocked` in browser console

**Cause**: Vite dev server (port 5173) calling API (port 8000)

**Solution**: Vite proxy already configured
```typescript
// vite.config.ts
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

**Prevention**: Use `/api/*` paths in frontend, not `http://localhost:8000/*`

---

### Pitfall 5: Terraform State Lock

**Symptom**: `Error acquiring state lock` when running `terraform apply`

**Cause**: Previous terraform run crashed without releasing DynamoDB lock

**Solution**:
```bash
# Check lock status
aws dynamodb get-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"dr-daily-report/terraform.tfstate"}}'

# Force unlock (use with caution!)
terraform force-unlock {lock-id}
```

**Prevention**: Always Ctrl+C gracefully (lets Terraform cleanup)

---

### Pitfall 6: Git Hooks Failure (Pre-Commit)

**Symptom**: `git commit` fails with "pre-commit hook failed"

**Cause**: Code doesn't pass linting, formatting, or type checks

**Solution**:
```bash
# Run checks manually
dr check format  # Format code
dr check lint    # Lint code
dr check syntax  # Type check

# Then commit
git commit -m "message"
```

**Prevention**: Run `dr check all` before committing

---

### Pitfall 7: Docker Build Fails (Lambda Image)

**Symptom**: `ERROR: failed to solve: process "/bin/sh -c pip install" did not complete`

**Cause**: Package dependencies incompatible with Lambda Python runtime

**Solution**: Use requirements.txt with pinned versions
```bash
# requirements.txt already has compatible versions
# Don't upgrade without testing in Lambda RIE
```

**Prevention**: Test Docker build before pushing: `dr build`

---

### Pitfall 8: Vite Build Fails (TypeScript Errors)

**Symptom**: `npm run build` fails with TypeScript errors

**Cause**: TypeScript strict mode catches issues that dev mode ignores

**Solution**:
```bash
# Fix TypeScript errors
npm run build
# Read errors, fix types

# Verify fix
npm run build
# Should complete with no errors
```

**Prevention**: Run `npm run build` locally before pushing

---

## Phase 5: "Hello World" Tasks (30 min)

**Purpose**: Verify setup works end-to-end

### Task 1: Run Unit Tests

```bash
# Run all unit tests
dr test unit

# Should see:
# - Test discovery (finds ~50+ tests)
# - All tests pass (green checkmarks)
# - Coverage report (optional)
```

**Expected**: ✅ All tests pass

**If failed**: Check Python version (should be 3.11+), virtual environment activated

---

### Task 2: Start Development Server

```bash
# Start backend dev server
dr dev

# Should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete

# In browser, navigate to:
# http://localhost:8000/docs  (FastAPI Swagger UI)
```

**Expected**: ✅ API docs load, endpoints visible

**If failed**: Check port 8000 not already in use: `lsof -i :8000`

---

### Task 3: Deploy to Dev Environment

```bash
# Create feature branch
git checkout -b onboarding-test-{your-name}

# Make trivial change (add comment to README)
echo "# Onboarding test by {your-name}" >> README.md

# Commit change
git add README.md
git commit -m "test: Onboarding deployment verification"

# Push to GitHub (triggers CI/CD)
git push origin onboarding-test-{your-name}

# Monitor GitHub Actions
gh run watch --repo org/dr-daily-report_telegram

# Expected: Workflow completes in ~8 minutes
```

**Expected**: ✅ GitHub Actions deploy to dev, all checks pass

**If failed**: Check GitHub Actions logs for errors

---

### Task 4: Verify Deployment (Multi-Layer)

```bash
# Layer 1: HTTP Status Code
curl -i https://api-dev.example.com/health
# Expected: HTTP/1.1 200 OK

# Layer 2: Response Payload
curl https://api-dev.example.com/health | jq
# Expected: {"status": "healthy", "version": "..."}

# Layer 3: CloudWatch Logs
ENV=dev doppler run -- aws logs tail /aws/lambda/report_worker --since 5m
# Expected: No ERROR or CRITICAL level logs
```

**Expected**: ✅ All 3 verification layers pass (status, payload, logs)

**If failed**: Check CloudWatch for errors, review deployment logs

---

## Phase 6: Key Concepts to Internalize (15 min)

### Concept 1: Aurora-First Data Architecture

**Principle**: Aurora is the source of truth, data precomputed nightly

**Implications**:
- APIs are read-only (no data fetching from external APIs)
- If data missing in Aurora, API fails fast (HTTP 404)
- No fallback to slow external APIs (ensures consistent performance)

**Example**:
```python
# ❌ Bad: Fallback to external API
def get_ticker_data(ticker: str):
    data = aurora.query(ticker)
    if not data:
        data = yfinance_api.fetch(ticker)  # SLOW!
    return data

# ✅ Good: Fail fast
def get_ticker_data(ticker: str):
    data = aurora.query(ticker)
    if not data:
        raise HTTPException(404, f"Ticker {ticker} not found")
    return data
```

---

### Concept 2: Multi-Layer Verification

**Principle**: Execution success ≠ Operational success

**Layers**:
1. **HTTP Status Code** (weakest) - Request completed
2. **Response Payload** (stronger) - Contains expected data
3. **CloudWatch Logs** (strongest) - No errors during execution

**Example**:
```bash
# ❌ Bad: Only check status
curl -I https://api.example.com/report/AAPL  # 200 OK (but might have failed internally!)

# ✅ Good: All 3 layers
curl -i https://api.example.com/report/AAPL  # 1. Status
curl https://api.example.com/report/AAPL | jq '.report_data'  # 2. Payload
aws logs tail /aws/lambda/report_worker --since 1m | grep ERROR  # 3. Logs
```

---

### Concept 3: Defensive Programming

**Principle**: Fail fast and visibly when something is wrong

**Patterns**:
- Validate configuration at startup (not on first use)
- Explicitly detect operation failures (rowcount, status codes)
- No silent fallbacks or default values
- Never assume data exists without validating

**Example**:
```python
# ❌ Bad: Silent failure
def save_report(report_id, data):
    db.execute("UPDATE reports SET data=? WHERE id=?", data, report_id)
    # If report_id doesn't exist, nothing happens (silent failure!)

# ✅ Good: Fail fast
def save_report(report_id, data):
    result = db.execute("UPDATE reports SET data=? WHERE id=?", data, report_id)
    if result.rowcount == 0:
        raise ValueError(f"Report {report_id} not found")  # Explicit failure!
```

---

### Concept 4: Error Handling Duality

**Principle**: Different error handling for workflows vs utilities

**Patterns**:
- **Workflow nodes**: State-based error propagation (collect all errors)
- **Utility functions**: Raise descriptive exceptions (fail fast)

**Example**:
```python
# Workflow node (state-based)
def process_tickers(state):
    errors = []
    for ticker in state["tickers"]:
        try:
            process_ticker(ticker)
        except Exception as e:
            errors.append(f"{ticker}: {e}")
    state["errors"] = errors  # Collect all errors
    return state

# Utility function (exceptions)
def process_ticker(ticker):
    if not ticker:
        raise ValueError("Ticker cannot be empty")  # Fail fast
    # ... process ticker
```

---

## Phase 7: First Real Task (pick one)

### Backend Task
**Issue**: `good-first-issue` label on GitHub
**Example**: "Add input validation to ticker endpoint"
**Skills**: Python, FastAPI, Pydantic, pytest

### Frontend Task
**Issue**: `good-first-issue` + `frontend` label
**Example**: "Add loading skeleton to portfolio page"
**Skills**: React, TypeScript, Tailwind CSS, Vitest

### Infrastructure Task
**Issue**: `good-first-issue` + `infrastructure` label
**Example**: "Add CloudWatch alarm for Lambda errors"
**Skills**: Terraform, AWS CloudWatch, HCL

---

## Completion Checklist

**Phase 1: Prerequisites**
- [ ] All tools installed and verified
- [ ] Access granted (GitHub, Doppler, AWS)

**Phase 2: Environment**
- [ ] Repository cloned, dependencies installed
- [ ] Dev server starts, tests pass
- [ ] Doppler configured, secrets accessible

**Phase 3: Reading**
- [ ] Core principles understood (CLAUDE.md)
- [ ] Documentation structure known (README.md)
- [ ] Focus-specific docs read

**Phase 4: Pitfalls**
- [ ] Common pitfalls reviewed
- [ ] Solutions understood

**Phase 5: Hello World**
- [ ] Unit tests pass
- [ ] Dev server works
- [ ] Deployed to dev successfully
- [ ] Multi-layer verification completed

**Phase 6: Concepts**
- [ ] Aurora-First understood
- [ ] Multi-Layer Verification practiced
- [ ] Defensive Programming examples reviewed
- [ ] Error Handling Duality understood

**Phase 7: First Task**
- [ ] Issue selected
- [ ] Work started

---

## Next Steps After Onboarding

1. **Join team meetings**:
   - Daily standup (async in Slack)
   - Weekly architecture review (if backend/infrastructure)
   - Biweekly demo (show what you built)

2. **Set up monitoring**:
   - CloudWatch bookmarks (Lambda functions, Aurora)
   - Langfuse dashboard (LLM quality scores)
   - GitHub notifications (PR reviews, mentions)

3. **Read related documentation**:
   - `docs/ARCHITECTURE_INVENTORY.md` - All tools/services in use
   - ADRs (`docs/adr/`) - Why we made certain decisions
   - Deployment guides (`docs/deployment/`)

4. **Practice workflows**:
   - Create observation: `/observe execution "completed task"`
   - Journal decision: `/journal architecture "why I chose X"`
   - Use slash commands: `/list-commands` to see all available

---

## Resources

### Documentation
- [Architecture Inventory](../docs/ARCHITECTURE_INVENTORY.md) - All tools/services
- [Quick Start](../docs/QUICKSTART.md) - 5-minute setup guide
- [Project Conventions](../docs/PROJECT_CONVENTIONS.md) - Patterns and structure
- [Code Style Guide](../docs/CODE_STYLE.md) - Coding standards

### Skills
- [Testing Workflow](./../skills/testing-workflow/) - Testing patterns
- [Deployment](./../skills/deployment/) - Deployment best practices
- [Error Investigation](./../skills/error-investigation/) - Debugging patterns

### Tools
- `/list-cli` - List all dr CLI commands
- `/list-commands` - List all slash commands
- `/context "task"` - Get relevant context for task
- `/onboard {focus}` - Re-run onboarding for specific area

---

## Feedback Loop

**After completing onboarding**:
1. Document what was unclear or confusing
2. Suggest improvements to onboarding process
3. Update this command with lessons learned
4. Journal your experience: `/journal process "onboarding experience"`

**Improvement process**:
```bash
/observe behavior "onboarding experience - what was hard"
/journal process "onboarding improvements needed"
/evolve  # Detects drift, proposes updates to onboarding docs
```

---

## See Also

- `/explore` - Discover tools and patterns in codebase
- `/consolidate` - Understand specific concepts
- `/runbook deployment` - Operational deployment procedure
- `docs/ARCHITECTURE_INVENTORY.md` - Complete tool inventory
- `.claude/CLAUDE.md` - Core principles and patterns
```

---

## Examples

### Example 1: Full Onboarding

```bash
/onboard
```

**Output**: Complete checklist covering all areas (backend, frontend, infrastructure, deployment, testing)

**Duration**: 3-4 hours total
- Phase 1: 30 min (prerequisites)
- Phase 2: 1 hour (environment setup)
- Phase 3: 30 min (reading)
- Phase 4: 15 min (pitfalls)
- Phase 5: 30 min (hello world tasks)
- Phase 6: 15 min (key concepts)
- Phase 7: 30 min+ (first real task)

---

### Example 2: Backend-Focused Onboarding

```bash
/onboard backend
```

**Output**: Filtered checklist focusing on:
- Python, FastAPI, Aurora, pytest
- Backend-specific reading (testing-workflow, database migrations)
- Backend "Hello World" (run tests, start API server)
- Backend first task (API endpoint addition)

**Duration**: 2 hours

---

### Example 3: Frontend-Focused Onboarding

```bash
/onboard frontend
```

**Output**: Filtered checklist focusing on:
- React, TypeScript, Tailwind CSS, Zustand
- Frontend-specific reading (UI_PRINCIPLES.md, Telegram SDK)
- Frontend "Hello World" (run Vite dev server, component tests)
- Frontend first task (add UI component)

**Duration**: 2 hours

---

## Anti-Patterns

### ❌ Using /onboard for Quick Reference

**Bad**: Already onboarded, just need to remember command
**Good**: Use `docs/README.md` quick links or `dr --help`

**Why bad**: Onboarding generates long checklist, overwhelming for simple lookups

---

### ❌ Re-Running /onboard Daily

**Bad**: Running `/onboard` every day for reference
**Good**: Bookmark `docs/ARCHITECTURE_INVENTORY.md`, `PROJECT_CONVENTIONS.md`

**Why bad**: Onboarding is one-time process, not daily reference

---

### ❌ Skipping Required Reading

**Bad**: Jump straight to coding without reading CLAUDE.md
**Good**: Read core principles first, understand WHY

**Why bad**: Will violate principles unknowingly, code reviews will request changes

---

## See Also

- `/list-commands` - All available slash commands
- `/list-cli` - All dr CLI commands
- `/context "task"` - Get task-specific context
- `/runbook deployment` - Deployment operational procedure
- `docs/ARCHITECTURE_INVENTORY.md` - Complete tool inventory
