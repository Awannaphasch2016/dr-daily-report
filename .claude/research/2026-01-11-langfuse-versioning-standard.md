# Research: Langfuse Trace Versioning Standard

**Date**: 2026-01-11
**Focus**: Observability & Traceability
**Status**: Complete

---

## Problem Decomposition

**Goal**: Establish a versioning standard for `LANGFUSE_RELEASE` to enable:
- A/B testing between deployments
- Metric tracking across versions (cost, latency, quality)
- Regression detection when code changes
- Debugging by correlating traces to specific deployments

**Current State**:
- `LANGFUSE_RELEASE` is set to `dev` in local_dev Doppler config
- Production uses git tags `v*.*.*` for releases (CLAUDE.md Branch Strategy)
- No standardized versioning syntax documented

**Core Requirements**:
- [ ] Identify which code version generated a trace
- [ ] Compare metrics between versions
- [ ] Support all environments (local, dev, stg, prd)
- [ ] Integrate with existing branch/tag strategy

**Constraints**:
- Max 200 characters (Langfuse SDK limit)
- Must be deterministic (same deploy = same version)
- Should be human-readable for debugging
- Must work with CI/CD (GitHub Actions)

**Success Criteria**:
- Can filter Langfuse traces by version
- Can compare quality scores between versions
- Can identify which commit caused a regression

---

## Solution Space (Divergent Phase)

### Option 1: Environment Name Only (Current)

**Description**: Use simple environment names: `dev`, `stg`, `prd`

**How it works**:
```bash
# Doppler configs
dev: LANGFUSE_RELEASE=dev
stg: LANGFUSE_RELEASE=stg
prd: LANGFUSE_RELEASE=prd
```

**Pros**:
- Simplest implementation
- Easy to filter by environment
- No CI/CD changes needed

**Cons**:
- Cannot distinguish between deployments within same environment
- No version tracking - all `prd` traces look identical
- Cannot do A/B testing or regression detection
- Loses deployment history

**When to use**: Development-only projects without production versioning needs

---

### Option 2: SemVer Tags (Production) + Environment (Non-Prod)

**Description**: Use semantic version tags for production, environment names for dev/stg

**How it works**:
```bash
# Doppler configs
dev: LANGFUSE_RELEASE=dev
stg: LANGFUSE_RELEASE=stg
prd: LANGFUSE_RELEASE=v1.2.3  # Updated on each release
```

**Pros**:
- Aligns with existing `v*.*.*` tag strategy
- Clear version history in production
- Familiar format (industry standard)
- Easy to correlate with git tags

**Cons**:
- Requires manual Doppler update on each release
- Dev/stg traces still undifferentiated
- Must remember to update before production deploy

**When to use**: Projects with manual release cycles

---

### Option 3: Git Commit SHA

**Description**: Use short git commit hash as version

**How it works**:
```bash
# CI/CD sets at deploy time
LANGFUSE_RELEASE=$(git rev-parse --short HEAD)
# Result: abc1234
```

**Pros**:
- Precise - every deploy is unique
- Automatic - no manual updates
- Direct link to code state
- Works for all environments

**Cons**:
- Not human-readable (what is `abc1234`?)
- Hard to compare versions (which is newer?)
- No semantic meaning (is this a major change?)
- Requires git access at deploy time

**When to use**: High-frequency deployments where precision matters more than readability

---

### Option 4: Hybrid Format (Recommended)

**Description**: Combine environment, version/commit, and timestamp

**Format**: `{env}-{version}-{short_sha}`

**How it works**:
```bash
# Production (tagged releases)
LANGFUSE_RELEASE=prd-v1.2.3-abc1234

# Staging (from main branch)
LANGFUSE_RELEASE=stg-main-def5678

# Development (from dev branch)
LANGFUSE_RELEASE=dev-dev-ghi9012

# Local development
LANGFUSE_RELEASE=local-dev-{commit}
```

**Implementation in CI/CD**:
```yaml
# GitHub Actions
- name: Set Langfuse Release
  run: |
    if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
      # Production: prd-v1.2.3-abc1234
      VERSION="${{ github.ref_name }}"
      echo "LANGFUSE_RELEASE=prd-${VERSION}-${GITHUB_SHA::7}" >> $GITHUB_ENV
    elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      # Staging: stg-main-abc1234
      echo "LANGFUSE_RELEASE=stg-main-${GITHUB_SHA::7}" >> $GITHUB_ENV
    else
      # Development: dev-dev-abc1234
      echo "LANGFUSE_RELEASE=dev-dev-${GITHUB_SHA::7}" >> $GITHUB_ENV
    fi
```

**Pros**:
- Human-readable (see environment + version at a glance)
- Precise (commit SHA for exact code state)
- Automatic (CI/CD generates it)
- Sortable (versions are comparable)
- Supports all environments consistently

**Cons**:
- Longer string (but well under 200 char limit)
- Requires CI/CD integration
- More complex than simple names

**When to use**: Production systems needing full traceability

---

### Option 5: CalVer (Calendar Versioning)

**Description**: Use date-based versioning: `YYYY.MM.DD` or `YYYY.MM.DD.build`

**How it works**:
```bash
# Production
LANGFUSE_RELEASE=prd-2026.01.11

# With build number
LANGFUSE_RELEASE=prd-2026.01.11.1
```

**Pros**:
- Immediately shows when deployed
- Natural ordering (newer dates = newer versions)
- Good for time-series analysis

**Cons**:
- Multiple deploys per day need build numbers
- Doesn't indicate code changes (same date, different code)
- No link to git history
- Less common in software industry

**When to use**: Projects with scheduled releases (e.g., daily/weekly)

---

## Evaluation Matrix

| Criterion | Env Only | SemVer | Git SHA | Hybrid | CalVer |
|-----------|----------|--------|---------|--------|--------|
| Precision (uniqueness) | 2/10 | 5/10 | 10/10 | 9/10 | 4/10 |
| Readability | 10/10 | 8/10 | 3/10 | 7/10 | 8/10 |
| Automation | 10/10 | 3/10 | 9/10 | 8/10 | 6/10 |
| Git Correlation | 1/10 | 6/10 | 10/10 | 10/10 | 2/10 |
| A/B Testing | 2/10 | 7/10 | 9/10 | 9/10 | 5/10 |
| **Total** | **25** | **29** | **41** | **43** | **25** |

**Scoring rationale**:
- **Precision**: Can we uniquely identify each deployment?
- **Readability**: Can humans understand the version at a glance?
- **Automation**: Can CI/CD generate this without manual steps?
- **Git Correlation**: Can we find the exact code from the version?
- **A/B Testing**: Can we compare metrics between versions?

---

## Ranked Recommendations

### 1. Hybrid Format (Score: 43/50)

**Format**: `{env}-{version|branch}-{short_sha}`

**Examples**:
```
prd-v1.2.3-abc1234    # Production release v1.2.3
stg-main-def5678      # Staging from main branch
dev-dev-ghi9012       # Dev from dev branch
local-dev-jkl3456     # Local development
```

**Why**:
- Best balance of readability + precision
- Aligns with existing branch strategy (`dev` → `main` → `v*.*.*`)
- Fully automated via CI/CD
- Direct link to git commit for debugging
- Supports all environments consistently

**Trade-offs**:
- Gain: Full traceability, A/B testing, regression detection
- Lose: Simplicity (requires CI/CD integration)

**Implementation Steps**:
1. Update GitHub Actions workflow to set `LANGFUSE_RELEASE`
2. Update Doppler configs with fallback values
3. Update Lambda environment variables via Terraform
4. Document in CLAUDE.md Principle #22

---

### 2. Git Commit SHA (Score: 41/50)

**Format**: `{short_sha}` (7 characters)

**When to choose**:
- High-frequency deployments (multiple per day)
- Precision more important than readability
- Team comfortable with git SHAs

---

### 3. SemVer Tags (Score: 29/50)

**Format**: `v1.2.3` for prd, `dev`/`stg` for others

**When to choose**:
- Manual release process
- Don't want CI/CD complexity
- Only care about production versioning

---

## Implementation Plan

### Step 1: Update GitHub Actions

Add to `.github/workflows/deploy.yml`:

```yaml
- name: Set Langfuse Release
  id: langfuse
  run: |
    SHORT_SHA="${GITHUB_SHA::7}"
    if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
      RELEASE="prd-${{ github.ref_name }}-${SHORT_SHA}"
    elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      RELEASE="stg-main-${SHORT_SHA}"
    else
      RELEASE="dev-dev-${SHORT_SHA}"
    fi
    echo "release=${RELEASE}" >> $GITHUB_OUTPUT
    echo "LANGFUSE_RELEASE=${RELEASE}" >> $GITHUB_ENV

- name: Deploy Lambda
  run: |
    aws lambda update-function-configuration \
      --function-name ${{ env.FUNCTION_NAME }} \
      --environment "Variables={LANGFUSE_RELEASE=${{ steps.langfuse.outputs.release }}}"
```

### Step 2: Update Doppler Configs

```bash
# Fallback values (used if CI/CD doesn't override)
dev:       LANGFUSE_RELEASE=dev-dev-unknown
stg:       LANGFUSE_RELEASE=stg-main-unknown
prd:       LANGFUSE_RELEASE=prd-unknown-unknown
local_dev: LANGFUSE_RELEASE=local-dev-manual
```

### Step 3: Update Terraform

Add to Lambda environment variables:

```hcl
environment {
  variables = {
    LANGFUSE_RELEASE = var.langfuse_release  # Passed from CI/CD
  }
}
```

### Step 4: Document in CLAUDE.md

Add to Principle #22 (LLM Observability Discipline):

```markdown
**Versioning standard**:
- Format: `{env}-{version|branch}-{short_sha}`
- Examples: `prd-v1.2.3-abc1234`, `stg-main-def5678`, `dev-dev-ghi9012`
- Set automatically by CI/CD at deploy time
- Enables A/B testing, regression detection, and deployment traceability
```

---

## Resources Gathered

**Official Documentation**:
- [Langfuse Releases & Versioning](https://langfuse.com/docs/observability/features/releases-and-versioning)

**Industry Standards**:
- [Semantic Versioning 2.0.0](https://semver.org/)
- [Calendar Versioning](https://calver.org/)

**Project Context**:
- CLAUDE.md Branch Strategy: `dev` → `main` → `v*.*.*`
- Current Doppler: `LANGFUSE_RELEASE=dev`

---

## Next Steps

```bash
# Recommended: Implement hybrid versioning
# 1. Update GitHub Actions workflow
# 2. Update Doppler fallback values
# 3. Document in CLAUDE.md

# Alternative: Quick fix for immediate visibility
/specify "Update LANGFUSE_RELEASE in Doppler configs"
```

---

## Decision

**Selected**: Option 4 - Hybrid Format (`{env}-{version|branch}-{short_sha}`)

**Rationale**: Best alignment with existing branch strategy while providing full traceability for debugging and A/B testing. The additional CI/CD complexity is justified by the observability benefits.

**Implementation Priority**: Medium (after current Langfuse schema documentation work)
