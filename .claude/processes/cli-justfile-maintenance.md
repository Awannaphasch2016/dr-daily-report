# CLI/Justfile Synchronization Maintenance Process

**Purpose**: Keep dr CLI and Justfile recipes synchronized with current code and infrastructure state

**Last Updated**: 2025-12-31

**Principle**: Two-layer CLI design requires both layers stay in sync - Justfile (intent/WHEN/WHY) + dr CLI (implementation/HOW)

---

## Overview

The project uses a **two-layer CLI architecture**:

- **Layer 1: Justfile** (Intent) - Describes WHEN and WHY to run commands
- **Layer 2: dr CLI** (Implementation) - Explicit syntax for HOW commands work

Both layers must stay synchronized to prevent:
- Commands documented but not implemented
- Commands implemented but not documented
- Justfile recipes without dr CLI equivalents
- dr CLI commands without Justfile recipes

---

## WHEN to Check Synchronization

### 1. Pre-Commit (Required)

**Trigger**: Before committing any of these changes:
- Added new dr CLI command
- Added new Justfile recipe
- Modified existing command behavior
- Updated infrastructure that requires new commands
- Removed deprecated commands

**Action**: Follow [Adding CLI Command Checklist](./../checklists/adding-cli-command.md)

### 2. Monthly Review (Scheduled)

**Trigger**: First Monday of each month

**Action**:
1. Run `/evolve cli`
2. Follow [Drift Review Checklist](./../checklists/drift-review.md)
3. Document findings in monthly journal

### 3. After Major Changes (Reactive)

**Trigger**:
- Infrastructure refactoring (e.g., Aurora migration, Lambda changes)
- New feature requiring CLI operations
- Deprecating old workflows

**Action**:
1. Audit all related commands
2. Update both layers
3. Verify with `/evolve cli`

---

## HOW to Verify Synchronization

### Method 1: Manual Verification (Quick Check)

```bash
# Step 1: List all dr CLI commands
dr --help

# Step 2: List all Justfile recipes
just --unstable --list

# Step 3: Compare visually
# Look for:
#   - Commands in dr without Justfile recipes
#   - Recipes in Justfile without dr commands
#   - Naming mismatches
```

### Method 2: Automated Detection (Recommended)

```bash
# Run drift detection
/evolve cli

# Or use automation script directly
python .claude/automation/detect-cli-drift.py
```

**Expected output if synchronized**:
```
✅ CLI/Justfile Sync Check

Commands without recipes: 0
Recipes without commands: 0
Documentation mismatches: 0

Status: SYNCHRONIZED ✓
```

**Expected output if drift detected**:
```
❌ CLI/Justfile Sync Check

Commands without recipes: 2
  - dr dev verify-env
  - dr deploy sync-secrets

Recipes without commands: 1
  - just test-integration

Documentation mismatches: 1
  - dr test all: Help text says "Run all tests" but actually only runs unit tests

Status: DRIFT DETECTED
See: .claude/evolution/2025-12-31-cli.md
```

### Method 3: CI/CD Validation (Automated)

**GitHub Actions check**:
```yaml
# .github/workflows/validate-cli-sync.yml
- name: Validate CLI/Justfile Sync
  run: |
    python .claude/automation/detect-cli-drift.py
    # Exit code 1 if drift detected (fails CI)
```

---

## WHAT to Update

When drift is detected, update these components in order:

### 1. Implementation First

**If command exists in Justfile but not dr CLI**:
```bash
# Add command to dr CLI
# Location: dr_cli/commands/<group>.py

# Example:
@click.command()
def sync_env():
    """Sync environment variables to Lambda"""
    run_command([...])
```

**If command exists in dr CLI but not Justfile**:
```bash
# Add recipe to justfile
# Location: justfile or modules/*.just

# Example:
# Sync environment variables to Lambda (use after changing .env)
sync-env:
    dr --doppler deploy sync-env
```

### 2. Documentation Second

Update all three documentation locations:

**A. Extension Point** (`docs/PROJECT_CONVENTIONS.md`):
```markdown
## CLI Commands

### Deployment
- `dr deploy sync-env` - Sync environment variables to Lambda
- `just sync-env` - Intent: Use after changing .env
```

**B. Command Help** (`docs/cli.md` if exists):
```markdown
### dr deploy sync-env

Synchronize environment variables from Doppler to Lambda function.

**Usage**: `doppler run -- dr deploy sync-env`
```

**C. Onboarding** (`.claude/onboarding/` if commonly used):
- Update relevant onboarding guide with new command

### 3. Verification Third

```bash
# Re-run drift detection
/evolve cli

# Or
python .claude/automation/detect-cli-drift.py

# Confirm: No drift detected
```

---

## WHO is Responsible

**Developer adding the command**: Primary responsibility
- Ensure both layers created
- Update all documentation
- Verify synchronization before commit

**Code Reviewer**: Secondary verification
- Check both layers exist in PR
- Verify documentation updated
- Run `/evolve cli` if suspicious

**Monthly Reviewer**: Periodic audit
- Run `/evolve cli` on first Monday
- Triage detected drift
- Create tickets for high-priority fixes

---

## TRIGGERS for Review

### Automated Triggers (CI/CD)

**Pre-merge validation**:
- Every PR checks CLI/Justfile sync
- Blocks merge if drift detected
- Forces developer to fix before approval

**Post-deploy validation**:
- After successful deployment
- Verify commands work as documented
- Alert if discrepancies found

### Manual Triggers

**After infrastructure changes**:
- New AWS resources (Lambda, S3, Aurora)
- Configuration changes (environment variables)
- New external integrations (APIs, services)

**After feature completion**:
- New feature shipped
- Verify all related commands documented
- Check for unused/deprecated commands

**When onboarding new developers**:
- Fresh perspective finds gaps
- Document confusing areas
- Update onboarding guide

---

## Common Drift Patterns

### Pattern 1: Justfile Recipe Without dr Command

**Symptom**: `just deploy-staging` exists but `dr deploy staging` doesn't

**Cause**: Justfile recipe added as quick script, not formalized in dr CLI

**Fix**:
1. Decide: Should this be in dr CLI?
   - YES: Create dr command, update Justfile to call it
   - NO: Document in Justfile comment why it's Justfile-only

**Example fix**:
```python
# dr_cli/commands/deploy.py
@click.command()
@click.argument('environment')
def deploy(environment):
    """Deploy to specified environment"""
    run_command(['terraform', 'apply', f'-var', f'env={environment}'])
```

```just
# justfile
deploy-staging:
    dr --doppler deploy staging
```

### Pattern 2: dr Command Without Justfile Recipe

**Symptom**: `dr dev verify-env` exists but no `just verify-env`

**Cause**: dr command added for programmatic use, not common workflow

**Fix**:
1. Decide: Is this commonly used manually?
   - YES: Add Justfile recipe with intent comment
   - NO: Document in dr command help as "programmatic use only"

**Example fix** (if commonly used):
```just
# Verify development environment setup (use when setup fails)
verify-env:
    dr --doppler dev verify-env
```

**Example fix** (if programmatic only):
```python
@click.command()
def verify_env():
    """Verify development environment (programmatic use - no Justfile recipe needed)"""
    ...
```

### Pattern 3: Documentation Out of Sync

**Symptom**: Help text says "Deploy to AWS Lambda" but command is `dr deploy lambda-deploy` (unclear naming)

**Cause**: Command renamed but help text not updated

**Fix**:
```python
# Before
@click.command('lambda-deploy')
def deploy():
    """Deploy to AWS Lambda"""  # Generic

# After
@click.command('lambda')
def deploy():
    """Deploy Lambda function code (zero-downtime update)"""  # Specific
```

### Pattern 4: Deprecated Commands Still Executable

**Symptom**: Justfile has `just aurora-test-ticker` marked DEPRECATED but still works

**Cause**: Deprecation warning added but command not removed (violates Single Execution Path principle)

**Fix**:
```just
# Before
# DEPRECATED: Use 'just aurora::local' instead
aurora-test-ticker:
    @echo "⚠️ DEPRECATED"
    @exit 1

# After
# (Remove entirely - enforce single execution path)
```

---

## Escalation

### Low Priority Drift
- Minor documentation mismatch
- Rarely-used command missing recipe
- **Action**: Add to monthly review backlog

### Medium Priority Drift
- Commonly-used command not documented
- New command added 2+ weeks ago without docs
- **Action**: Fix within 1 week

### High Priority Drift
- Production deployment command missing
- Security-critical command undocumented
- Breaking change not reflected in docs
- **Action**: Fix immediately (same day)

---

## Success Metrics

Track these metrics to measure synchronization health:

1. **Drift Detection Time**: Time from drift creation to detection
   - Target: < 24 hours (via CI/CD)

2. **Drift Fix Time**: Time from detection to fix
   - Target: < 1 hour for high priority, < 1 week for medium

3. **Drift Prevention Rate**: % of PRs with no drift detected
   - Target: > 95%

4. **Documentation Completeness**: % of commands documented
   - Target: 100%

5. **Automation Coverage**: % of drift detected automatically
   - Target: > 90%

---

## Related Documentation

- [Adding CLI Command Checklist](./../checklists/adding-cli-command.md)
- [CLI Sync Verification Checklist](./../checklists/cli-sync-verification.md)
- [Drift Review Checklist](./../checklists/drift-review.md)
- [Justfile and dr CLI Onboarding](./../onboarding/2025-12-30-justfile-and-dr-cli.md)
- [Evolve Command - CLI Focus](./../commands/evolve.md)
- [PROJECT_CONVENTIONS.md](./../../docs/PROJECT_CONVENTIONS.md)

---

## Tools

### Detection
- `/evolve cli` - Manual drift detection command
- `python .claude/automation/detect-cli-drift.py` - Automated script

### Verification
- `dr --help` - List all dr CLI commands
- `just --unstable --list` - List all Justfile recipes
- `just --unstable aurora::help` - List Aurora module commands

### Documentation
- `docs/PROJECT_CONVENTIONS.md` - Extension points
- `docs/cli.md` - CLI command reference
- `.claude/onboarding/` - Onboarding guides

---

## Examples

### Example 1: Adding New Command (Complete Flow)

```bash
# Step 1: Create dr CLI command
# Edit: dr_cli/commands/deploy.py
@click.command()
def sync_secrets():
    """Sync Doppler secrets to Lambda environment variables"""
    run_command(['doppler', 'secrets', 'upload', ...])

# Step 2: Add Justfile recipe
# Edit: justfile
# Sync Doppler secrets to Lambda (use after updating secrets)
sync-secrets:
    dr --doppler deploy sync-secrets

# Step 3: Update documentation
# Edit: docs/PROJECT_CONVENTIONS.md
# Add to deployment commands section

# Step 4: Verify synchronization
/evolve cli
# Output: ✅ No drift detected

# Step 5: Commit
git add dr_cli/commands/deploy.py justfile docs/PROJECT_CONVENTIONS.md
git commit -m "feat(deploy): Add sync-secrets command for Doppler integration"
```

### Example 2: Fixing Detected Drift

```bash
# Monthly review found drift
/evolve cli

# Output:
# ❌ Commands without recipes: 1
#   - dr dev verify-env

# Decision: Commonly used, add Justfile recipe

# Edit: justfile
# Verify development environment setup (use when first-time setup or after clean)
verify-env:
    dr --doppler dev verify-env

# Re-verify
/evolve cli
# Output: ✅ No drift detected

# Commit fix
git add justfile
git commit -m "docs(justfile): Add verify-env recipe for common workflow"
```

---

## Feedback Loop

**After using this process**:
1. Document what was unclear about synchronization
2. Suggest improvements to detection automation
3. Update checklists with lessons learned
4. Refine triggers and thresholds based on experience

**Improvement process**:
```bash
/observe behavior "CLI/Justfile synchronization maintenance experience"
/journal process "Suggested improvements to CLI sync process"
/evolve cli  # Re-check for new patterns
```

---

**Created**: 2025-12-31
**Maintenance Type**: CLI/Justfile Synchronization
**Owner**: Development Team
**Review Frequency**: Monthly (first Monday) + pre-commit
