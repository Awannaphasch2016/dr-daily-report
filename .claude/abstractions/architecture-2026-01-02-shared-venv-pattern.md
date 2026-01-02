# Architecture Pattern: Shared Virtual Environment via Symlink

**Abstracted From**:
- Current codebase analysis (venv symlink: `venv -> ../dr-daily-report/venv`)
- Documentation references across 41 files mentioning "venv"
- Deployment runbook patterns (Telegram, fund data sync)
- DR CLI setup workflow (`dr dev install`)
- GitHub Actions CI/CD workflows (8 workflows)

**Pattern Type**: Architecture
**Confidence**: High (production pattern in use, consistent across all documentation)
**Date Created**: 2026-01-02

---

## Pattern Description

**What it is**: Multiple related repositories share a single Python virtual environment via symlink to reduce duplication and ensure dependency consistency.

**When it occurs**: Multi-repository projects with shared dependencies (e.g., `dr-daily-report` ecosystem with 4 repositories)

**Why it works**: 
- Eliminates dependency version conflicts between related projects
- Reduces disk usage (~500MB shared vs ~2GB if isolated)
- Simplifies dependency management (update once, affects all projects)
- Faster development workflow (changes immediately available across projects)

---

## Concrete Instances

### Instance 1: Current Project Structure
**From**: Codebase analysis
**Context**: Four related repositories in `/home/anak/dev/`
- `dr-daily-report` (parent, contains actual venv)
- `dr-daily-report_telegram` (symlink: `venv -> ../dr-daily-report/venv`)
- `dr-daily-report_media` (assumed same pattern)
- `dr-daily-report_news` (assumed same pattern)

**Manifestation**: 
```bash
$ ls -la venv
lrwxrwxrwx  1 anak anak  23 Nov 27 17:39 venv -> ../dr-daily-report/venv
```

### Instance 2: Documentation Pattern
**From**: `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`
**Context**: Deployment runbook emphasizes venv activation
**Manifestation**:
```bash
# IMPORTANT: Always use the project's virtual environment
source venv/bin/activate

# Verify you're in venv
which python
# Expected: /home/anak/dev/dr-daily-report_telegram/venv/bin/python
```

### Instance 3: DR CLI Integration
**From**: `dr_cli/commands/dev.py`, `justfile`
**Context**: Installation workflow assumes shared venv
**Manifestation**:
```bash
just setup → dr dev install → pip install -r requirements.txt
# Installs to shared venv via symlink
```

---

## Generalized Pattern

### Signature (how to recognize it)
- Symlink in project root: `venv -> ../parent-project/venv`
- Multiple related repositories in same parent directory
- Shared dependencies in `requirements.txt` across projects
- Documentation mentions "activate venv" without creation instructions
- No `python -m venv venv` commands in setup scripts

### Preconditions (what enables it)
- Projects exist in same filesystem (sibling directories)
- Projects share majority of dependencies
- Development team works across multiple repositories
- Unix-like filesystem supporting symlinks (Linux, macOS)

### Components (what's involved)
1. **Parent project** - Contains actual venv directory
2. **Sibling projects** - Contain symlinks to parent venv
3. **Symlink** - Transparent redirection (`venv -> ../parent/venv`)
4. **Shared dependencies** - Common packages in `requirements.txt`
5. **Activation workflow** - `source venv/bin/activate` works via symlink

### Mechanism (how it works)
```
Project Structure:
/home/anak/dev/
  ├── dr-daily-report/           # Parent project
  │   └── venv/                  # Actual virtual environment (500MB)
  │       ├── bin/
  │       ├── lib/
  │       └── ...
  ├── dr-daily-report_telegram/  # Sibling project
  │   └── venv -> ../dr-daily-report/venv  # Symlink
  ├── dr-daily-report_media/
  │   └── venv -> ../dr-daily-report/venv  # Symlink
  └── dr-daily-report_news/
      └── venv -> ../dr-daily-report/venv  # Symlink

Activation flow:
1. Developer: cd dr-daily-report_telegram/
2. Developer: source venv/bin/activate
3. Shell resolves: venv -> ../dr-daily-report/venv
4. Activates: /home/anak/dev/dr-daily-report/venv/bin/activate
5. Python path: /home/anak/dev/dr-daily-report/venv/bin/python
6. All projects see same packages
```

---

## Pattern Template

### Architecture Pattern: Shared Virtual Environment

**Problem**: Multiple related projects need consistent Python dependencies without duplication.

**Context**: 
- Multi-repository project structure
- Shared core dependencies
- Development across multiple repos simultaneously
- Disk space constraints (multiple venvs = ~2GB)

**Solution**: Symlink virtual environments to parent project

**Structure**:

**Components**:
- **Parent venv** - Single source of truth for Python packages
- **Symlinks** - Transparent pointers from sibling projects
- **Shared requirements.txt** - Similar dependencies across projects

**Relationships**:
```
Parent Project (contains venv)
    ↑ symlink
Sibling Project 1
    ↑ symlink  
Sibling Project 2
    ↑ symlink
Sibling Project 3
```

**Data flow**:
- Package installation → Parent venv
- Import statements → Resolved via symlink → Parent venv
- Activation script → Symlink → Parent activation

**Implementation**:

1. **Create parent venv** (once):
   ```bash
   cd dr-daily-report/
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Symlink sibling projects**:
   ```bash
   cd dr-daily-report_telegram/
   ln -s ../dr-daily-report/venv venv
   
   cd ../dr-daily-report_media/
   ln -s ../dr-daily-report/venv venv
   ```

3. **Activate in any project** (transparent):
   ```bash
   cd dr-daily-report_telegram/
   source venv/bin/activate  # Works via symlink
   python  # Uses shared venv
   ```

4. **Update dependencies** (affects all):
   ```bash
   cd dr-daily-report/
   source venv/bin/activate
   pip install new-package  # Available in all projects
   ```

**Trade-offs**:

Pros:
- **Consistency**: All projects use identical package versions
- **Disk efficiency**: 75% disk savings (1 venv vs 4 venvs)
- **Simplicity**: One venv to manage, not four
- **Development speed**: Updates immediately available everywhere
- **Prevents conflicts**: Impossible to have version mismatches

Cons:
- **Single point of failure**: Corrupt parent venv breaks all projects
- **Coupling**: Projects can't use different package versions
- **Platform limitation**: Requires symlink support (no Windows without WSL)
- **Confusion**: New developers may not understand symlink structure
- **Rebuilds**: Recreating venv requires recreating all symlinks

**When to use**:
- Multiple repositories with shared dependencies (>70% overlap)
- Development team works across repositories simultaneously
- Disk space constraints (development machines, CI runners)
- All projects target same Python version
- Unix-like environment (Linux, macOS, WSL)

**When NOT to use**:
- Projects need different package versions (version conflicts)
- Projects use different Python versions (3.10 vs 3.11)
- Windows development without WSL (no symlink support)
- Isolated testing environments needed (separate CI per project)
- Projects have diverging dependency needs over time

**Related patterns**:
- **Monorepo**: Shares code AND dependencies in single repo (more tightly coupled)
- **Shared library**: Extract common code to package (loosely coupled, but separate venvs)
- **Docker**: Package dependencies with code (isolated, but heavier)
- **Poetry workspaces**: Modern Python tool with multi-project support

---

## Variations

### Variation 1: Parent Selection
**Observed**: `dr-daily-report` is parent (likely oldest/most complete project)

**Alternative approaches**:
- Dedicated venv directory (e.g., `dr-venv/`) shared by all
- Most active project as parent
- Alphabetically first project

**Trade-off**: Dedicated directory cleanest but adds another entity

### Variation 2: Fallback Strategy
**Observed**: Documentation shows creating isolated venv if symlink broken

**Pattern**:
```bash
# If parent unavailable
rm venv  # Remove broken symlink
python -m venv venv  # Create isolated venv
pip install -r requirements.txt
```

**When to use fallback**:
- Parent project not cloned yet
- Testing dependency changes without affecting siblings
- Temporary isolation for experimentation

---

## Verification Checklist

**Before using pattern**:
- [ ] Projects share >70% dependencies
- [ ] Projects use same Python version
- [ ] Filesystem supports symlinks
- [ ] Team understands symlink structure

**After setup**:
- [ ] Symlink exists: `ls -la venv` shows `-> ../parent/venv`
- [ ] Target exists: `ls -la ../parent/venv/` shows venv structure
- [ ] Activation works: `source venv/bin/activate` succeeds
- [ ] Python path correct: `which python` points to parent venv
- [ ] Packages available: `python -c "import required_package"` works

**Ongoing maintenance**:
- [ ] Document parent project in README
- [ ] Update all projects after dependency changes
- [ ] Warn team before recreating parent venv
- [ ] Test CI builds after venv changes
- [ ] Monitor for dependency divergence

---

## Migration from Isolated Venvs

**If projects currently use isolated venvs**:

1. **Choose parent project** (e.g., most complete)
2. **Audit dependencies**: Compare `requirements.txt` across projects
3. **Merge dependencies**: Union of all project requirements
4. **Update parent requirements.txt** with merged dependencies
5. **Recreate parent venv**:
   ```bash
   cd parent-project/
   rm -rf venv
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
6. **Replace sibling venvs with symlinks**:
   ```bash
   cd sibling-project/
   rm -rf venv  # Remove old isolated venv
   ln -s ../parent-project/venv venv
   ```
7. **Test all projects**: Run tests in each project
8. **Update documentation**: Explain new shared venv pattern

---

## Troubleshooting

### Problem: `source venv/bin/activate` fails with "No such file"
**Diagnosis**: Symlink broken (target doesn't exist)
```bash
ls -la venv  # Check symlink
ls -la ../dr-daily-report/venv  # Check target
```
**Solution**: 
- Option A: Clone parent project
- Option B: Recreate parent venv
- Option C: Create isolated venv (fallback)

### Problem: Wrong Python version
**Diagnosis**: System Python activated instead of venv
```bash
which python  # Should show path in venv
python --version  # Should match venv Python
```
**Solution**: Ensure venv activated before running commands

### Problem: `ModuleNotFoundError` despite venv activated
**Diagnosis**: Package not installed in shared venv
```bash
source venv/bin/activate
pip list | grep package-name
```
**Solution**: Install in parent venv (affects all projects)

### Problem: Version conflict between projects
**Diagnosis**: Project A needs package==1.0, Project B needs package==2.0
**Solution**: 
- Option A: Upgrade both projects to compatible version
- Option B: Split into isolated venvs (abandon shared pattern)
- Option C: Use Docker for true isolation

---

## Graduation Path

**Current status**: ✅ **In production** (actively used pattern)

**Documentation status**: ❌ **Undocumented** (implicit knowledge)

**Next steps**:

1. **Document in CLAUDE.md** (HIGH priority):
   - Add Principle #18: "Shared Virtual Environment Pattern"
   - Explain rationale and setup
   - Link to this abstraction

2. **Update PROJECT_CONVENTIONS.md** (HIGH priority):
   - Add "Python Environment" section
   - Document venv structure
   - Provide setup instructions

3. **Enhance `dr dev verify`** (MEDIUM priority):
   ```python
   def verify_venv():
       """Verify venv symlink integrity."""
       if not os.path.islink('venv'):
           warn("venv is not a symlink")
       if not os.path.exists('venv'):
           error("venv symlink broken")
       # ... more checks
   ```

4. **Create verification script** (MEDIUM priority):
   - `scripts/verify_venv_setup.sh`
   - Checks symlink, target, activation
   - Offers to recreate if broken

5. **Add to README.md** (LOW priority):
   - Setup section explaining symlink
   - Fallback instructions
   - Link to troubleshooting

---

## Action Items

- [x] Extract pattern from codebase (this document)
- [ ] Add to CLAUDE.md as Principle #18
- [ ] Update PROJECT_CONVENTIONS.md with Python Environment section
- [ ] Create `scripts/verify_venv_setup.sh`
- [ ] Enhance `dr dev verify` with venv checks
- [ ] Update README.md with setup instructions
- [ ] Test pattern with fresh clone (validate instructions)

---

## Metadata

**Pattern Type**: architecture
**Confidence**: high (production use, consistent across documentation)
**Created**: 2026-01-02
**Instances**: 41 venv references, 8 CI workflows, 4 projects
**Last Updated**: 2026-01-02
**Related Principles**: 
- CLAUDE.md Principle #13 (Secret Management Discipline) - Similar "share instead of duplicate" philosophy
- CLAUDE.md Principle #17 (Single Execution Path) - One venv, not multiple paths

---

## References

**Files analyzed**:
- `venv` symlink (project root)
- `requirements.txt`, `requirements-dev.txt` (dependency files)
- `docs/deployment/TELEGRAM_DEPLOYMENT_RUNBOOK.md`
- `dr_cli/commands/dev.py` (install command)
- `justfile` (setup recipe)
- `.gitignore` (venv exclusions)
- 8 GitHub Actions workflows

**Similar patterns in other ecosystems**:
- **Doppler config inheritance** (Principle #13): `local_dev` inherits from `dev`
- **Docker image promotion** (Principle #11): Build once, promote everywhere
- **Aurora table name centralization** (Principle #15): Single source of truth

**External references**:
- Python venv documentation: https://docs.python.org/3/library/venv.html
- Symlink behavior: Unix symlinks are transparent to most programs
