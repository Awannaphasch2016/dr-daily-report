# Checklist: Adding New CLI Command

**Purpose**: Ensure both Justfile and dr CLI layers stay synchronized when adding new commands

**When to use**: Before committing any new CLI command or Justfile recipe

---

## Pre-Implementation Planning

- [ ] **Decide command purpose**
  - What does the command do?
  - When should users run it (WHEN/WHY)?
  - How should it work (HOW)?

- [ ] **Choose command group**
  - dev (development operations)
  - test (testing workflows)
  - build (artifact creation)
  - deploy (deployment operations)
  - clean (cleanup tasks)
  - check (validation/verification)
  - util (utilities and helpers)

- [ ] **Determine if Justfile recipe needed**
  - Is this commonly used manually? → YES: Add Justfile recipe
  - Is this programmatic/automation only? → NO: dr CLI only is fine

---

## Implementation

### Step 1: Create dr CLI Command

- [ ] **Create/edit command file**
  - Location: `dr_cli/commands/<group>.py`
  - Use Click decorators
  - Follow naming convention: `snake_case` for function names

- [ ] **Write clear help text**
  - One-line summary (what it does)
  - Longer description (when to use)
  - Example usage in docstring

- [ ] **Add to command group**
  - Ensure command registered in `<group>.py`
  - Verify command group shows in `dr --help`

**Example**:
```python
# dr_cli/commands/deploy.py

@click.command()
@click.option('--env', default='dev', help='Target environment')
def sync_secrets(env):
    """Sync Doppler secrets to Lambda environment variables.

    Use after updating secrets in Doppler to deploy changes to Lambda.

    Example:
        doppler run -- dr deploy sync-secrets --env dev
    """
    run_command(['doppler', 'secrets', 'upload', ...])
```

- [ ] **Test command locally**
  ```bash
  dr deploy sync-secrets --help
  # Verify help text displays correctly

  doppler run -- dr deploy sync-secrets
  # Verify command executes successfully
  ```

---

### Step 2: Add Justfile Recipe (If Needed)

- [ ] **Add recipe with intent comment**
  - Location: `justfile` (or `modules/<module>.just` for modules)
  - Comment explains WHEN and WHY
  - Recipe calls dr CLI command

**Example**:
```just
# Sync Doppler secrets to Lambda (use after updating secrets in Doppler)
sync-secrets:
    @echo "🔄 Syncing secrets to Lambda..."
    dr --doppler deploy sync-secrets
```

- [ ] **Test Justfile recipe**
  ```bash
  just sync-secrets
  # Verify recipe executes dr command
  # Verify output is clear
  ```

- [ ] **Verify module recipes work** (if using modules)
  ```bash
  just --unstable <module>::<command>
  # Example: just --unstable aurora::tunnel
  ```

---

### Step 3: Update Documentation

- [ ] **Update PROJECT_CONVENTIONS.md**
  - Location: `docs/PROJECT_CONVENTIONS.md`
  - Section: CLI Commands → <appropriate subsection>
  - Add command with example

**Example**:
```markdown
### Deployment

- `dr deploy sync-secrets` - Sync Doppler secrets to Lambda
- `just sync-secrets` - Intent: Use after updating secrets
```

- [ ] **Update cli.md** (if file exists)
  - Add detailed command documentation
  - Include usage examples
  - Document all options/flags

- [ ] **Update onboarding** (if commonly used)
  - Add to `.claude/onboarding/2025-12-30-justfile-and-dr-cli.md`
  - Include in examples section

---

### Step 4: Verify Synchronization

- [ ] **Run drift detection**
  ```bash
  /evolve cli
  ```

  OR

  ```bash
  python .claude/automation/detect-cli-drift.py
  ```

- [ ] **Expected output: No drift detected**
  ```
  ✅ CLI/Justfile Sync Check

  Commands without recipes: 0
  Recipes without commands: 0
  Documentation mismatches: 0

  Status: SYNCHRONIZED ✓
  ```

- [ ] **If drift detected**: Fix issues before proceeding
  - Review error messages
  - Update missing components
  - Re-run verification

---

### Step 5: Code Review Verification

- [ ] **Self-review checklist**
  - Both layers exist (dr CLI + Justfile OR documented as dr-only)
  - Documentation updated in all 3 places
  - Help text clear and accurate
  - Examples work when copy-pasted
  - No drift detected

- [ ] **PR description includes**
  - What command does
  - When to use it
  - Link to updated documentation
  - `/evolve cli` verification result

**Example PR description**:
```markdown
## Add dr deploy sync-secrets command

**What**: New command to sync Doppler secrets to Lambda environment variables

**When to use**: After updating secrets in Doppler

**Changes**:
- Created `dr deploy sync-secrets` command
- Added `just sync-secrets` recipe
- Updated PROJECT_CONVENTIONS.md

**Verification**:
- [x] Both layers created
- [x] Documentation updated
- [x] `/evolve cli` shows no drift
```

---

## Common Mistakes to Avoid

### Mistake 1: Only creating dr CLI command

❌ **Bad**: Create command in `dr_cli/commands/` without Justfile recipe

✅ **Good**: Decide if Justfile needed
- If commonly used manually → Add Justfile recipe
- If programmatic only → Document in help text as "no recipe needed"

---

### Mistake 2: Only creating Justfile recipe

❌ **Bad**: Add Justfile recipe that runs bash commands directly

✅ **Good**: Create dr CLI command first, then Justfile calls it
- Justfile = Intent (WHEN/WHY)
- dr CLI = Implementation (HOW)

---

### Mistake 3: Forgetting documentation

❌ **Bad**: Command works but not documented anywhere

✅ **Good**: Update all 3 documentation locations:
1. PROJECT_CONVENTIONS.md (required)
2. cli.md (if exists)
3. Onboarding guide (if commonly used)

---

### Mistake 4: Not verifying synchronization

❌ **Bad**: Assume it's synchronized without checking

✅ **Good**: Always run `/evolve cli` before committing
- Catches drift before it reaches main branch
- Forces you to fix issues immediately

---

### Mistake 5: Inconsistent naming

❌ **Bad**:
```python
# dr CLI
@click.command('lambda-deploy')  # Hyphenated

# Justfile
deploy_lambda:  # Underscored
```

✅ **Good**:
```python
# dr CLI
@click.command('lambda')  # Consistent

# Justfile
deploy-lambda:  # Matches CLI naming
```

---

## Quick Reference

### Two-Layer Design Pattern

```
Justfile (Intent Layer)
  ├─ WHEN: "use after updating secrets"
  ├─ WHY: "to deploy changes to Lambda"
  └─ Calls: dr --doppler deploy sync-secrets
            ↓
dr CLI (Implementation Layer)
  ├─ HOW: run_command(['doppler', 'secrets', 'upload', ...])
  ├─ Options: --env, --dry-run
  └─ Help: Clear docstring explaining usage
```

### Command Naming Conventions

- **dr CLI**: `snake_case` functions, `kebab-case` command names
- **Justfile**: `kebab-case` recipe names
- **Consistency**: Keep names aligned between layers

### Documentation Locations

1. **docs/PROJECT_CONVENTIONS.md** - Required (extension point reference)
2. **docs/cli.md** - Optional (detailed command docs)
3. **.claude/onboarding/** - Optional (if commonly used)

---

## Completion Verification

Before marking this task complete, verify:

- [ ] **Both layers exist**
  - dr CLI command created ✓
  - Justfile recipe added (or documented as dr-only) ✓

- [ ] **Documentation complete**
  - PROJECT_CONVENTIONS.md updated ✓
  - cli.md updated (if exists) ✓
  - Onboarding updated (if commonly used) ✓

- [ ] **Testing passed**
  - dr command works with `--help` ✓
  - dr command executes successfully ✓
  - Justfile recipe works ✓

- [ ] **Synchronization verified**
  - `/evolve cli` shows no drift ✓
  - All checks passed ✓

- [ ] **Ready to commit**
  - PR description complete ✓
  - Self-review checklist done ✓

---

## Related Documentation

- [CLI/Justfile Maintenance Process](./../processes/cli-justfile-maintenance.md)
- [CLI Sync Verification Checklist](./cli-sync-verification.md)
- [Justfile and dr CLI Onboarding](./../onboarding/2025-12-30-justfile-and-dr-cli.md)
- [PROJECT_CONVENTIONS.md](./../../docs/PROJECT_CONVENTIONS.md)

---

**Created**: 2025-12-31
**Checklist Type**: Pre-commit verification for CLI commands
**Estimated Time**: 15-30 minutes
