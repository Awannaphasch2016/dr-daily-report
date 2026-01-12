# Shared Virtual Environment Pattern Guide

**Principle**: Principle #17 in CLAUDE.md
**Category**: Development Environment, Dependency Management
**Abstraction**: [architecture-2026-01-02-shared-venv-pattern.md](../../.claude/abstractions/architecture-2026-01-02-shared-venv-pattern.md)

---

## Overview

**Context**: This project is part of a four-repository ecosystem (`dr-daily-report`, `dr-daily-report_telegram`, `dr-daily-report_media`, `dr-daily-report_news`) sharing common dependencies.

**Pattern**: Use symlinked virtual environment to parent project for dependency consistency, eliminating version conflicts and reducing disk usage by 75%.

---

## Core Insight

Multiple related repositories share a single Python virtual environment via symlink:
- **Consistency**: All projects use identical package versions (impossible to have conflicts)
- **Disk efficiency**: 75% savings (500MB shared vs 2GB isolated)
- **Simplicity**: One venv to manage, not four
- **Development speed**: Updates immediately available across all projects

---

## Project Structure

```
/home/anak/dev/
  ├── dr-daily-report/           # Parent project (contains actual venv)
  │   └── venv/                  # Actual virtual environment (500MB)
  │       ├── bin/python
  │       ├── lib/python3.11/
  │       └── ...
  │
  ├── dr-daily-report_telegram/  # This project (symlink to parent venv)
  │   └── venv -> ../dr-daily-report/venv  # Symlink
  │
  ├── dr-daily-report_media/     # Media processing (symlink)
  │   └── venv -> ../dr-daily-report/venv
  │
  └── dr-daily-report_news/      # News fetcher (symlink)
      └── venv -> ../dr-daily-report/venv
```

---

## Setup Workflow

### Verify Symlink Exists

```bash
# Check symlink status
ls -la venv

# Expected output:
# lrwxrwxrwx  1 anak anak  23 Nov 27 17:39 venv -> ../dr-daily-report/venv
```

### Activate Virtual Environment

```bash
# Activate via symlink (works transparently)
source venv/bin/activate

# Verify activation
which python
# Expected: /home/anak/dev/dr-daily-report_telegram/venv/bin/python
# (resolves to parent venv via symlink)

# Verify packages installed
pip list
# Shows all shared packages from parent venv
```

### Verify DR CLI Available

```bash
# DR CLI should be installed in shared venv
dr --help

# If not found:
pip install -e .  # Installs to shared venv
```

---

## Verification Checklist

Before starting development, verify shared venv setup:

```markdown
- [ ] Symlink exists: `ls -la venv` shows `-> ../dr-daily-report/venv`
- [ ] Target exists: `ls -la ../dr-daily-report/venv/` shows venv structure
- [ ] Activation works: `source venv/bin/activate` succeeds
- [ ] Python path correct: `which python` points to parent venv
- [ ] DR CLI available: `dr --help` works
- [ ] Packages installed: `pip list` shows expected dependencies
```

---

## Fallback: Create Isolated venv

If parent venv missing or broken:

```bash
# 1. Remove broken symlink
rm venv

# 2. Create isolated venv
python -m venv venv

# 3. Activate
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install DR CLI
pip install -e .

# 6. Verify
which python  # Should show local venv, not parent
dr --help     # Should work
```

**When to use fallback**:
- Parent project not cloned (`../dr-daily-report/` doesn't exist)
- Parent venv broken or incomplete
- Need isolated environment for testing

---

## Why Shared venv Works

### Benefit 1: Dependency Consistency

**Problem (isolated venvs)**:
```
dr-daily-report:          pandas==2.0.0, numpy==1.24.0
dr-daily-report_telegram: pandas==1.5.3, numpy==1.24.0  # Conflict!
```

**Solution (shared venv)**:
```
All projects:             pandas==2.0.0, numpy==1.24.0  # Always in sync
```

### Benefit 2: Disk Efficiency

**Isolated venvs** (4 projects):
```
dr-daily-report/venv:          500MB
dr-daily-report_telegram/venv: 500MB
dr-daily-report_media/venv:    500MB
dr-daily-report_news/venv:     500MB
Total:                         2GB
```

**Shared venv** (symlinks):
```
dr-daily-report/venv:          500MB  (actual)
dr-daily-report_telegram/venv: 0KB    (symlink)
dr-daily-report_media/venv:    0KB    (symlink)
dr-daily-report_news/venv:     0KB    (symlink)
Total:                         500MB  (75% savings)
```

### Benefit 3: Simplified Management

**Update dependencies** (one command):
```bash
# In any project
cd dr-daily-report_telegram/
source venv/bin/activate
pip install --upgrade pandas

# Immediately available in ALL projects
cd ../dr-daily-report_media/
source venv/bin/activate
python -c "import pandas; print(pandas.__version__)"  # New version!
```

---

## Common Scenarios

### Scenario 1: Installing New Package

```bash
# Install in any project (writes to shared venv)
cd dr-daily-report_telegram/
source venv/bin/activate
pip install requests

# Immediately available in sibling projects
cd ../dr-daily-report_media/
source venv/bin/activate
python -c "import requests"  # Works!
```

### Scenario 2: Updating requirements.txt

```bash
# Update requirements in parent project
cd dr-daily-report/
echo "requests==2.31.0" >> requirements.txt

# Install to shared venv
source venv/bin/activate
pip install -r requirements.txt

# Available in all sibling projects immediately
cd ../dr-daily-report_telegram/
source venv/bin/activate
pip list | grep requests  # Shows 2.31.0
```

### Scenario 3: Broken Symlink

```bash
# Symptom: venv activation fails
source venv/bin/activate
# bash: venv/bin/activate: No such file or directory

# Diagnosis: Check symlink
ls -la venv
# lrwxrwxrwx venv -> ../dr-daily-report/venv  (red = broken)

# Fix: Verify parent venv exists
ls -la ../dr-daily-report/venv/
# If missing, create it in parent project

# If parent project not cloned, use fallback
rm venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Integration with CI/CD

### GitHub Actions

**Pattern**: CI creates fresh venv (not shared):

```yaml
# .github/workflows/test.yml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'

- name: Create virtual environment
  run: python -m venv venv

- name: Install dependencies
  run: |
    source venv/bin/activate
    pip install -r requirements.txt
```

**Why**: CI environments are ephemeral (no sibling projects), shared venv not available.

### Local Development

**Pattern**: Use shared venv via symlink:

```bash
# Local (shared venv)
source venv/bin/activate  # Via symlink to parent
pytest tests/

# CI (isolated venv)
python -m venv venv       # Fresh venv
source venv/bin/activate
pytest tests/
```

---

## Anti-Patterns

### ❌ Creating Isolated venv Without Understanding Pattern

**Problem**: Breaks shared environment, creates dependency drift

```bash
# BAD: Create local venv without checking symlink
python -m venv venv  # Overwrites symlink!

# Result: Now isolated from other projects
# - Different package versions possible
# - Disk usage increased
# - Updates don't propagate
```

**Solution**: Check `ls -la venv` first, understand symlink pattern

---

### ❌ Installing to System Python

**Problem**: Pollutes system, no isolation

```bash
# BAD: Install without activating venv
pip install pandas  # Installs to system Python

# Result:
# - System Python polluted
# - Version conflicts with system packages
# - Permissions issues (sudo required)
```

**Solution**: Always `source venv/bin/activate` first

---

### ❌ Assuming venv Exists

**Problem**: Commands fail silently

```bash
# BAD: Assume venv exists
source venv/bin/activate  # Fails if symlink broken
pytest tests/             # Uses wrong Python!

# GOOD: Verify first
ls -la venv || echo "venv missing or broken"
```

---

### ❌ Installing Dependencies Without Activating

**Problem**: Installs to wrong location

```bash
# BAD: Install without activation
pip install -r requirements.txt  # Where does this go?

# GOOD: Activate first
source venv/bin/activate
which pip  # Verify: should show venv/bin/pip
pip install -r requirements.txt
```

---

## Related Pattern: Doppler Config Inheritance

Similar "share instead of duplicate" philosophy:

**Shared Virtual Environment** (development dependencies):
- Parent venv contains packages
- Sibling projects symlink to parent
- Updates propagate automatically

**Doppler Config Inheritance** (deployment secrets):
- `dev` config contains shared secrets
- `local_dev` inherits from `dev` (cross-environment)
- Updates propagate automatically

See [Principle #13: Secret Management Discipline](../../.claude/principles/configuration-principles.md)

---

## When to Apply

✅ **Use shared venv when**:
- Multiple related repositories
- Share majority of dependencies
- Development across multiple projects
- Want consistent package versions
- Want to save disk space

✅ **Use isolated venv when**:
- Single repository
- Different dependency versions needed
- Testing dependency updates in isolation
- Parent project not available

❌ **Don't use shared venv when**:
- Projects have conflicting dependency versions
- Need to test different Python versions
- Security concerns (untrusted sibling projects)

---

## Rationale

**Why shared virtual environment matters**:

Traditional approach (isolated venvs per project) creates:
- **Version drift**: Projects diverge in package versions over time
- **Disk waste**: Same packages installed 4 times
- **Update overhead**: Must update dependencies in 4 places
- **Debugging confusion**: "Works in project A, fails in project B" due to version differences

**Shared venv via symlink eliminates these issues**:
- **Impossible to have version conflicts**: All projects use exact same packages
- **75% disk savings**: 500MB shared vs 2GB isolated
- **Single update point**: pip install once, affects all projects
- **Guaranteed consistency**: Always testing with same environment

**Key insight**: Related projects should share dependencies, not duplicate them.

---

## See Also

- **Abstraction**: [Shared Virtual Environment Pattern](.claude/abstractions/architecture-2026-01-02-shared-venv-pattern.md) - Complete technical details
- **Principle #13**: [Secret Management Discipline](../../.claude/principles/configuration-principles.md) - Similar config inheritance pattern
- **Setup**: Project README setup instructions

---

*Guide version: 2026-01-04*
*Principle: #17 in CLAUDE.md*
*Status: Production pattern, documented for team onboarding*
