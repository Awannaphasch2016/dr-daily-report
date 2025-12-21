# ADR-009: Artifact Promotion Over Per-Env Builds

**Status:** ✅ Accepted
**Date:** 2024-01
**Deciders:** Development Team

## Context

Container-based Lambda deployments can follow two patterns:
1. **Build per environment**: Rebuild container image for each environment (dev, staging, prod)
2. **Artifact promotion**: Build once, promote same immutable image through environments

### Requirements

- Ensure staging and prod run identical code
- Enable fast rollbacks
- Maintain audit trail of what's deployed where
- Optimize CI/CD pipeline speed

## Decision

Build container images once with immutable SHA-based tags, promote same image through all environments.

### Promotion Flow

```
Build Once:  sha-abc123-20251127  (IMMUTABLE)
     │
     ├──▶  DEV:     lambda_image_uri = "sha-abc123-20251127"
     │              (auto on merge to telegram branch)
     │
     ├──▶  STAGING: lambda_image_uri = "sha-abc123-20251127"
     │              (same image, promoted after dev tests pass)
     │
     └──▶  PROD:    lambda_image_uri = "sha-abc123-20251127"
                    (same image, promoted after staging + approval)
```

### Implementation Pattern

**Terraform Variables:**
```hcl
# envs/dev/main.tf
variable "lambda_image_uri" {
  description = "ECR image URI from CI build step"
  type        = string
}

module "telegram_api" {
  source           = "../../modules/telegram-api"
  lambda_image_uri = var.lambda_image_uri  # Passed from CI
}
```

**CI/CD Integration:**
```yaml
# .github/workflows/deploy.yml
jobs:
  build:
    outputs:
      image_uri: ${{ steps.build.outputs.image_uri }}
    steps:
      - name: Build and push Docker image
        id: build
        run: |
          IMAGE_URI="${ECR_REPO}:sha-${GITHUB_SHA}-$(date +%Y%m%d)"
          docker build -t $IMAGE_URI .
          docker push $IMAGE_URI
          echo "image_uri=$IMAGE_URI" >> $GITHUB_OUTPUT

  deploy-dev:
    needs: build
    steps:
      - name: Deploy to dev
        run: |
          terraform apply \
            -var="lambda_image_uri=${{ needs.build.outputs.image_uri }}"

  deploy-staging:
    needs: [build, deploy-dev]
    steps:
      - name: Deploy to staging (same image!)
        run: |
          terraform apply \
            -var="lambda_image_uri=${{ needs.build.outputs.image_uri }}"
```

## Consequences

### Positive

- ✅ **Reproducibility**: What you test in staging is EXACTLY what deploys to prod
- ✅ **Speed**: No rebuild per environment (save 5-10 min per deploy)
- ✅ **Rollback**: Can instantly revert to any previous image tag
- ✅ **Audit Trail**: SHA-based tags link deployments to exact commits
- ✅ **Confidence**: Staging validation applies to prod deployment
- ✅ **Cost**: Build once instead of 3x (saves ECR storage + build minutes)

### Negative

- ❌ **Requires Immutable Tags**: Can't use `latest` or mutable tags
- ❌ **More Complex CI**: Must pass image URI between jobs
- ❌ **Tag Management**: Need strategy for cleaning old images

### Mitigation

- Use date-based tags: `sha-{git_sha}-{date}` (easy to identify)
- Implement ECR lifecycle policy (delete images > 30 days)
- CI job outputs make image URI passing straightforward

## Alternatives Considered

### Alternative 1: Build Per Environment

**Example:**
```yaml
deploy-dev:
  steps:
    - run: docker build -t dev-image .
    - run: docker push dev-image

deploy-staging:
  steps:
    - run: docker build -t staging-image .  # Rebuild!
    - run: docker push staging-image

deploy-prod:
  steps:
    - run: docker build -t prod-image .  # Rebuild again!
    - run: docker push prod-image
```

**Why Rejected:**
- **No Reproducibility**: Staging and prod run different builds (timestamps differ)
- **Slower**: 3x build time (5-10 min each)
- **Risk**: Prod build could fail even if staging succeeded
- **Can't Test Exact Artifact**: Staging validates different image than prod runs

### Alternative 2: Mutable Tags (`:latest`, `:dev`, `:prod`)

**Example:**
```bash
docker tag image:latest image:dev
docker tag image:latest image:prod  # Same tag, different meaning
```

**Why Rejected:**
- **Cache Invalidation**: Lambda may not pull updated image (caches by tag)
- **Audit Trail**: Can't tell what commit `:latest` refers to historically
- **Rollback**: `:latest` is always moving target, can't rollback to "previous latest"

### Alternative 3: Git Tag-Based Versioning (v1.2.3)

**Why Rejected:**
- Requires manual tagging before deploy
- Can't deploy feature branches (no git tag yet)
- Semantic versioning doesn't map to commit SHAs

## References

- **ECR Repository**: `dr-daily-report-telegram-api`
- **Image URI Format**: `{account}.dkr.ecr.{region}.amazonaws.com/{repo}:sha-{sha}-{date}`
- **Deployment Pipeline**: `.github/workflows/deploy.yml`

## Decision Drivers

1. **Reproducibility**: Staging and prod must run identical code
2. **Speed**: Avoid redundant builds (5-10 min savings per environment)
3. **Confidence**: Test exact artifact that will deploy to prod
4. **Audit Trail**: Link every deployment to exact git commit

## Immutable Tag Pattern

**Tag Structure:**
```
sha-{git_sha}-{date}

Example: sha-abc1234-20251127
         │   │        │
         │   │        └─ Build date (human-readable)
         │   └────────── Git commit SHA (traceability)
         └──────────────── Prefix (distinguishes from other tags)
```

**Why This Works:**
- **Immutable**: Tag never changes once created
- **Traceable**: Git SHA links to exact code version
- **Human-Readable**: Date helps identify recent vs old images
- **Unique**: SHA + date combination ensures no collisions

## Rollback Strategy

**Instant Rollback:**
```bash
# Find previous working image
aws ecr list-images --repository-name telegram-api \
  --query 'reverse(sort_by(imageDetails, &imagePushedAt))[1].imageTags[0]'

# Output: sha-xyz5678-20251126 (previous deploy)

# Rollback by updating Lambda to previous image
terraform apply -var="lambda_image_uri=...sha-xyz5678-20251126"
```

No rebuild required - just point Lambda to previous image tag.

## ECR Lifecycle Policy

To prevent unbounded image storage:

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 30 images",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["sha-"],
        "countType": "imageCountMoreThan",
        "countNumber": 30
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

This keeps 30 most recent images (30 days of deploys if daily) while cleaning up old builds.

---

## Update (2025-01-22): Branch-Based Deployment

With the migration to branch-based deployment, the artifact promotion pattern remains but the trigger mechanism changes:

**Before:** Single `telegram` branch → all environments (progressive deployment)
**After:** Separate branches → independent environments (branch-based triggers)

### New Artifact Promotion Flow

```
dev branch push
    ↓
┌─────────────────────┐
│ deploy-dev.yml:     │  Builds image: sha-abc123-20250122-143000
│ - Build Docker      │      ↓
│ - Push to ECR       │  Stores metadata in GitHub Artifacts
│ - Store metadata    │      ↓
└─────────────────────┘  (dev-artifact-metadata)
    ↓
main branch push
    ↓
┌─────────────────────┐
│ deploy-staging.yml: │  Downloads dev-artifact-metadata
│ - Get dev artifact  │      ↓
│ - Deploy same image │  Uses: sha-abc123-20250122-143000 (NO REBUILD)
│ - Store metadata    │      ↓
└─────────────────────┘  (staging-artifact-metadata)
    ↓
v1.2.3 tag on main
    ↓
┌─────────────────────┐
│ deploy-prod.yml:    │  Downloads staging-artifact-metadata
│ - Validate tag      │      ↓
│ - Get staging       │  Uses: sha-abc123-20250122-143000 (SAME IMAGE)
│   artifact          │      ↓
│ - Deploy same image │  Manual approval required
└─────────────────────┘
```

### Implementation Changes

**1. Dev build creates artifact (triggered by `dev` branch push):**
```yaml
# .github/workflows/deploy-dev.yml
jobs:
  build:
    outputs:
      image_uri: ${{ steps.build.outputs.image_uri }}
    steps:
      - name: Build and push
        id: build
        run: |
          IMAGE_URI="${ECR_REPO}:sha-${GITHUB_SHA}-$(date +%Y%m%d%H%M%S)"
          docker build -t $IMAGE_URI .
          docker push $IMAGE_URI
          echo "image_uri=$IMAGE_URI" >> $GITHUB_OUTPUT

      - name: Store artifact metadata
        run: |
          echo "${{ steps.build.outputs.image_uri }}" > artifact-uri.txt

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dev-artifact-metadata
          path: artifact-uri.txt
          retention-days: 30
```

**2. Staging downloads dev artifact (triggered by `main` branch push):**
```yaml
# .github/workflows/deploy-staging.yml
jobs:
  get-dev-artifact:
    runs-on: ubuntu-latest
    outputs:
      image_uri: ${{ steps.download.outputs.image_uri }}
    steps:
      - name: Download artifact from dev
        uses: dawidd6/action-download-artifact@v3
        with:
          workflow: deploy-dev.yml
          branch: dev
          name: dev-artifact-metadata
          path: ./artifacts

      - name: Read artifact metadata
        id: download
        run: |
          IMAGE_URI=$(cat ./artifacts/artifact-uri.txt)
          echo "image_uri=${IMAGE_URI}" >> $GITHUB_OUTPUT

  deploy-staging:
    needs: get-dev-artifact
    steps:
      - name: Update Lambda with dev's image
        run: |
          aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --image-uri ${{ needs.get-dev-artifact.outputs.image_uri }}
```

**3. Production downloads staging artifact (triggered by `v*.*.*` tag):**
```yaml
# .github/workflows/deploy-prod.yml
jobs:
  validate-tag:
    steps:
      - name: Verify tag is on main branch
        run: |
          TAG_COMMIT=$(git rev-list -n 1 ${{ github.ref }})
          MAIN_COMMITS=$(git rev-list main)
          if ! echo "$MAIN_COMMITS" | grep -q "$TAG_COMMIT"; then
            echo "❌ Tag must be on main branch"
            exit 1
          fi

  get-staging-artifact:
    needs: validate-tag
    steps:
      - name: Download artifact from staging
        uses: dawidd6/action-download-artifact@v3
        with:
          workflow: deploy-staging.yml
          branch: main
          name: staging-artifact-metadata
```

### Key Benefits of Branch-Based Artifact Promotion

- ✅ **Fast Dev Iteration**: Dev deploys in ~8 min (vs 30 min for all envs)
- ✅ **Clear Error Isolation**: Know exactly which environment failed (no cascading failures)
- ✅ **Semantic Versioning**: Production releases use explicit tags (`v1.2.3`)
- ✅ **Maintained Reproducibility**: Same immutable image tested in dev → staging → prod
- ✅ **Independent Environments**: Staging/prod won't deploy if dev hasn't built yet
- ✅ **GitHub Artifacts**: 30-day retention provides artifact promotion across workflows

### Workflow Triggers

| Trigger | Workflow | Action | Duration |
|---------|----------|--------|----------|
| Push to `dev` | `deploy-dev.yml` | Build + deploy to dev only | ~8 min |
| Push to `main` | `deploy-staging.yml` | Promote dev artifact to staging | ~10 min |
| Tag `v*.*.*` on `main` | `deploy-prod.yml` | Promote staging artifact to prod | ~12 min |

This maintains the "build once, deploy everywhere" principle while enabling independent environment deployment and faster development iteration.
