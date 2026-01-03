# Checklist: CLI/Justfile Synchronization Verification

**Purpose**: Verify dr CLI and Justfile are synchronized (no drift)

**When to use**:
- After adding/modifying commands
- Monthly review (first Monday)
- Before major releases
- When drift suspected

---

## Quick Verification (5 minutes)

### Step 1: Run Drift Detection

- [ ] **Execute drift detection**
  ```bash
  /evolve cli
  ```

  OR (if automation script exists)

  ```bash
  python .claude/automation/detect-cli-drift.py
  ```

### Step 2: Interpret Results

- [ ] **Check status**
  - ✅ **SYNCHRONIZED**: No drift detected → You're done!
  - ❌ **DRIFT DETECTED**: Follow detailed verification below

---

## Detailed Verification (15-30 minutes)

### Step 3: Identify Drift Type

When drift is detected, categorize each finding:

#### Type 1: Command Without Recipe

**Symptom**: `dr <command>` exists but no `just <recipe>`

- [ ] **List affected commands**
  - Write down command names
  - Note which command group (dev, test, deploy, etc.)

- [ ] **Decide action**
  - [ ] **Option A**: Add Justfile recipe (if commonly used manually)
  - [ ] **Option B**: Document as "programmatic use only" in help text (if automation-only)

**Fix for Option A** (add recipe):
```just
# <Intent comment explaining WHEN and WHY>
<recipe-name>:
    dr --doppler <group> <command>
```

**Fix for Option B** (document as dr-only):
```python
@click.command()
def command_name():
    """Description here (programmatic use - no Justfile recipe needed)"""
    ...
```

---

#### Type 2: Recipe Without Command

**Symptom**: `just <recipe>` exists but no `dr <command>`

- [ ] **List affected recipes**
  - Write down recipe names
  - Check what they actually do

- [ ] **Decide action**
  - [ ] **Option A**: Create dr CLI command (formalize the operation)
  - [ ] **Option B**: Keep as Justfile-only (if one-time/simple script)
  - [ ] **Option C**: Remove recipe (if deprecated/unused)

**Fix for Option A** (create command):
```python
# dr_cli/commands/<group>.py
@click.command()
def command_name():
    """Clear help text"""
    run_command([...])
```

Then update Justfile to call it:
```just
<recipe-name>:
    dr --doppler <group> <command>
```

**Fix for Option B** (document as Justfile-only):
```just
# <Recipe name> - Justfile-only (simple script, no dr command needed)
<recipe-name>:
    @echo "Running ..."
    # Bash commands here
```

**Fix for Option C** (remove if deprecated):
```bash
# Delete the recipe from justfile
# Ensure no one is using it first
```

---

#### Type 3: Documentation Mismatch

**Symptom**: Help text doesn't match actual behavior

- [ ] **List mismatches**
  - Command name vs help text
  - Documented options vs actual options
  - Example usage doesn't work

- [ ] **Fix each mismatch**
  - Update help text to match behavior
  - Update examples to be copy-pasteable
  - Ensure consistency across docs

**Fix**:
```python
# Before
@click.command()
def deploy():
    """Deploy to AWS"""  # Too vague

# After
@click.command()
def deploy():
    """Deploy Lambda function code (zero-downtime update)"""  # Specific
```

---

#### Type 4: Missing Documentation

**Symptom**: Command/recipe exists but not in PROJECT_CONVENTIONS.md

- [ ] **List undocumented commands**
  - Check PROJECT_CONVENTIONS.md
  - Check cli.md (if exists)

- [ ] **Add documentation**
  - Add to PROJECT_CONVENTIONS.md (required)
  - Add to cli.md (if detailed docs needed)
  - Add to onboarding (if commonly used)

---

### Step 4: Fix Each Drift Instance

For each drift detected:

- [ ] **Understand the root cause**
  - When was command/recipe added?
  - Why wasn't the other layer created?
  - What prevented synchronization?

- [ ] **Apply the fix**
  - Follow fix pattern from Step 3
  - Update both layers if needed
  - Update documentation

- [ ] **Verify fix locally**
  ```bash
  # Test dr command
  dr <group> <command> --help
  dr <group> <command>  # (with appropriate args)

  # Test Justfile recipe
  just <recipe-name>
  ```

---

### Step 5: Re-Verify Synchronization

- [ ] **Run drift detection again**
  ```bash
  /evolve cli
  ```

- [ ] **Expected: All drift resolved**
  ```
  ✅ CLI/Justfile Sync Check

  Commands without recipes: 0
  Recipes without commands: 0
  Documentation mismatches: 0

  Status: SYNCHRONIZED ✓
  ```

- [ ] **If drift still detected**
  - Review fix implementation
  - Check for typos in command/recipe names
  - Ensure documentation updated
  - Repeat Step 4

---

### Step 6: Document Findings

- [ ] **Log in journal (if significant drift)**
  ```bash
  /journal process "CLI/Justfile drift found and fixed: <summary>"
  ```

- [ ] **Update this checklist** (if gaps found)
  - Add new drift patterns
  - Document better fix approaches
  - Clarify confusing steps

---

## Monthly Review Workflow

Use this for scheduled monthly reviews (first Monday):

### Preparation

- [ ] **Schedule time**: 30 minutes
- [ ] **Notify team**: "Running monthly CLI sync review"

### Execution

- [ ] **Run drift detection**
  ```bash
  /evolve cli
  ```

- [ ] **Generate report**
  - Report saved to: `.claude/evolution/YYYY-MM-DD-cli.md`
  - Review all findings

- [ ] **Triage findings**
  - High priority: Fix immediately
  - Medium priority: Fix this week
  - Low priority: Backlog

- [ ] **Create tickets**
  - One ticket per medium/high drift instance
  - Assign to appropriate developer
  - Link to evolution report

### Follow-up

- [ ] **Track fixes**
  - Monitor ticket completion
  - Re-run `/evolve cli` when fixes complete

- [ ] **Document patterns**
  - If same drift happens repeatedly, update prevention process
  - Add to pre-commit checklist
  - Consider automation

---

## Emergency Drift Fix (Production Issue)

If drift causes production problems:

### Immediate Actions

- [ ] **Assess impact**
  - What broke?
  - What users are affected?
  - What's the blast radius?

- [ ] **Quick fix**
  - Fix production immediately (bypass process if needed)
  - Document fix in incident log
  - Schedule proper fix later

### Post-Incident

- [ ] **Root cause analysis**
  - Why wasn't drift detected earlier?
  - What process failed?
  - How to prevent recurrence?

- [ ] **Update process**
  - Add to pre-commit checklist
  - Add to CI/CD validation
  - Strengthen detection

- [ ] **Communicate**
  - Post-mortem document
  - Share learnings with team
  - Update CLAUDE.md if needed

---

## Common Issues and Solutions

### Issue 1: Drift detection script not found

**Symptom**: `python .claude/automation/detect-cli-drift.py` fails

**Solution**: Use manual method or `/evolve cli` command:
```bash
# Manual verification
dr --help              # List all commands
just --unstable --list # List all recipes
# Compare visually
```

---

### Issue 2: Module commands not detected

**Symptom**: `just --unstable aurora::*` commands show drift

**Solution**: Ensure module detection enabled:
```bash
# Check if modules are loaded
just --unstable --list | grep "::"

# If not showing, check modules/ directory exists
ls -la modules/
```

---

### Issue 3: False positive drift

**Symptom**: Drift detected but both layers exist

**Solution**: Check naming consistency:
```bash
# dr CLI command name
dr <group> <command>

# Justfile recipe name (must match)
<command>:  # Should match dr command name
```

---

### Issue 4: Can't decide if Justfile recipe needed

**Decision tree**:
- Is command used manually by developers? → YES: Add recipe
- Is command only for CI/CD automation? → NO: dr-only is fine
- Is command used occasionally (<1x/week)? → OPTIONAL: Developer preference

---

## Success Criteria

Before marking verification complete:

- [ ] **All drift fixed**
  - Commands without recipes: 0
  - Recipes without commands: 0
  - Documentation mismatches: 0

- [ ] **Documentation complete**
  - PROJECT_CONVENTIONS.md updated
  - cli.md updated (if exists)
  - Onboarding updated (if needed)

- [ ] **Tests passed**
  - All commands work with `--help`
  - All recipes execute successfully
  - No errors in output

- [ ] **Verification complete**
  - `/evolve cli` shows SYNCHRONIZED
  - CI/CD validation passes (if enabled)

---

## Related Documentation

- [CLI/Justfile Maintenance Process](./../processes/cli-justfile-maintenance.md)
- [Adding CLI Command Checklist](./adding-cli-command.md)
- [Drift Review Checklist](./drift-review.md)
- [Justfile and dr CLI Onboarding](./../onboarding/2025-12-30-justfile-and-dr-cli.md)

---

**Created**: 2025-12-31
**Checklist Type**: Synchronization verification
**Estimated Time**: 5-30 minutes (depending on drift)
