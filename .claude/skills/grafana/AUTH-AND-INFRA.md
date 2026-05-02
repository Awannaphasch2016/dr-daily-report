---
name: grafana-auth-and-infra
description: Grafana auth model (Service Account Tokens via boto3), workspace provisioning, datasource management, and multi-environment setup
---

# Auth and Infrastructure

Authentication model, workspace provisioning, datasource management, and multi-environment expansion for AWS Managed Grafana.

---

## Auth Model

### Key Discovery: No Legacy API Keys

AWS Managed Grafana does **not** support legacy Grafana API keys. The workspace HTTP API requires a Bearer token, but **not** SigV4 (which is for AWS APIs, not the Grafana workspace API).

### Solution: Self-Provisioned Service Account Tokens

`scripts/build-grafana-dashboards.py` uses boto3 to create an ephemeral token at runtime:

```
┌─────────────┐    ┌──────────────────┐    ┌───────────────────┐    ┌──────────────┐
│  IAM Creds  │───>│  boto3 grafana   │───>│  Service Account  │───>│  Token (5m)  │
│  (env/role) │    │  client          │    │  "dashboard-      │    │  Bearer auth │
│             │    │                  │    │   deployer"        │    │  for HTTP API│
└─────────────┘    └──────────────────┘    └───────────────────┘    └──────────────┘
```

**Flow in code** (`build-grafana-dashboards.py`):

1. **`get_grafana_token()`**: Entry point
2. **`_get_or_create_service_account(client)`**: Find or create SA named `"dashboard-deployer"` with `ADMIN` role
3. **`_cleanup_stale_tokens(client, sa_id)`**: Delete old `"ephemeral-deploy"` tokens to avoid accumulation
4. **`_provision_token(client, sa_id)`**: Create new token with 5-minute TTL (`secondsToLive=300`)

**Why ephemeral tokens?**
- No secrets to manage or rotate
- Auto-expires after script finishes
- Stale tokens cleaned up on next run
- IAM credentials handle the actual auth (already in environment)

### Required IAM Permissions

The IAM user/role running the script needs:
- `grafana:ListWorkspaceServiceAccounts`
- `grafana:CreateWorkspaceServiceAccount`
- `grafana:ListWorkspaceServiceAccountTokens`
- `grafana:CreateWorkspaceServiceAccountToken`
- `grafana:DeleteWorkspaceServiceAccountToken`

### Token Usage

```python
HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
# All subsequent API calls use these headers
```

---

## Workspace Provisioning (setup-grafana.sh)

`scripts/setup-grafana.sh` provisions all infrastructure for Grafana. **Idempotent** — safe to re-run.

### What It Creates

| Step | Resource | Purpose |
|------|----------|---------|
| 1 | Resource lookup | VPC, Aurora SG, Aurora endpoint, SNS ARN |
| 2 | Security Group | `{project}-grafana-{env}` — VPC connectivity for Managed Grafana |
| 3 | Aurora SG ingress | Port 3306 from Grafana SG → Aurora SG |
| 4 | IAM Role | `{project}-grafana-role-{env}` — assumed by `grafana.amazonaws.com` |
| 5 | CloudWatch policy | Read-only CW access (`GetMetricData`, `ListMetrics`, etc.) |
| 6 | SNS policy | `sns:Publish` to alert topic (for Grafana alerting) |
| 7 | Secrets Manager | `{project}/grafana-mysql/{env}` — MySQL credentials |
| 8 | Grafana Workspace | `{project}-grafana-{env}` — Grafana 10.4, VPC-connected |

### Usage

```bash
# Provision (idempotent)
./scripts/setup-grafana.sh

# Cleanup (destructive)
./scripts/setup-grafana.sh --cleanup
```

### Configuration Constants

```bash
REGION="ap-southeast-1"
PROJECT="dr-daily-report"
ENV="${ENV:-dev}"
WORKSPACE_NAME="${PROJECT}-grafana-${ENV}"
```

### Post-Provisioning Manual Steps

After `setup-grafana.sh` completes:

1. **Assign SSO user** as Admin in AWS Console
2. **Configure MySQL datasource** in Grafana UI:
   - Name: `mysql-{env}` (required for template variable discovery)
   - Host: Aurora endpoint `:3306`
   - Database: `ticker_data`
   - User: `grafana_readonly`
   - Password: from Secrets Manager
3. **CloudWatch datasource** auto-configured via IAM role
4. **Deploy dashboards**: `python scripts/build-grafana-dashboards.py`

---

## Datasource Management

### Naming Convention

MySQL datasources **must** follow `mysql-{env}` naming:

| Environment | Datasource Name |
|-------------|----------------|
| dev | `mysql-dev` |
| staging | `mysql-staging` |
| prod | `mysql-prod` |

This convention is enforced by:
- Template variable regex: `/mysql-.*/`
- `rename_datasource_if_needed()` function in the dashboard script

### Automated Rename

If a datasource was created with a different name, the script auto-renames it:

```python
MYSQL_DS_UID = "bfg0lw3z4zqbkf"  # Known datasource UID

def main():
    ...
    rename_datasource_if_needed(MYSQL_DS_UID, DEFAULT_MYSQL_DS)
```

### CloudWatch Datasource

Auto-configured via the workspace IAM role. No manual setup needed — the role's CloudWatch policy grants read access. The `cw_datasource` template variable is hidden (`hide: 2`) since there's typically only one CloudWatch datasource.

---

## Multi-Environment

### Current State

Currently **dev only**:

```python
AVAILABLE_ENVS = "dev"
DEFAULT_ENV = "dev"
```

### Prerequisites for Staging/Prod

| Step | Action | Why |
|------|--------|-----|
| 1 | Run migration 028 on target Aurora | Creates `grafana_readonly` user |
| 2 | Add Aurora SG ingress from Grafana SG | Network connectivity on port 3306 |
| 3 | Register `mysql-{env}` datasource in Grafana UI | Dashboard template variables need it |
| 4 | Update `AVAILABLE_ENVS` constant | Adds env to dropdown |

### Expansion

To add staging and production:

```python
# In build-grafana-dashboards.py
AVAILABLE_ENVS = "dev,staging,prod"  # Change from "dev"
DEFAULT_ENV = "prod"                  # Change from "dev"
```

The template variable system automatically creates dropdowns for all listed environments. Each environment's datasource is discovered via the `/mysql-.*/` regex.

---

## Key Constants

| Constant | Value | Location |
|----------|-------|----------|
| `REGION` | `ap-southeast-1` | Both scripts |
| `WORKSPACE_ID` | `g-4df4c51648` | `build-grafana-dashboards.py` |
| `ENDPOINT` | `https://{WORKSPACE_ID}.grafana-workspace.{REGION}.amazonaws.com` | `build-grafana-dashboards.py` |
| `SERVICE_ACCOUNT_NAME` | `dashboard-deployer` | `build-grafana-dashboards.py` |
| `PROJECT_NAME` | `dr-daily-report` | `build-grafana-dashboards.py` |
| `MYSQL_DS_UID` | `bfg0lw3z4zqbkf` | `build-grafana-dashboards.py` |
