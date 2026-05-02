---
name: grafana
description: Grafana dashboard management, datasource operations, CloudWatch panels, and troubleshooting for AWS Managed Grafana
tier: 1
---

# Grafana Skill

**Focus**: Dashboard management, datasource operations, CloudWatch panel configuration, and troubleshooting for AWS Managed Grafana.

**Source**: Extracted from `scripts/build-grafana-dashboards.py`, `scripts/setup-grafana.sh`, and operational experience with SigV4 vs Service Account Token auth discovery.

---

## When to Use This Skill

Use grafana when:
- Adding or modifying Grafana dashboards
- Adding new panels to existing dashboards
- Managing MySQL or CloudWatch datasources
- Troubleshooting "no data", auth errors, or datasource issues
- Extending to new environments (staging, prod)

**DO NOT use for:**
- CloudWatch alarm configuration (use [deployment skill](../deployment/))
- Terraform infrastructure changes (use Terraform directly)
- Aurora schema changes (use [database-migration skill](../database-migration/))

---

## Quick Decision Tree

```
What are you doing?
│
├── Building a new dashboard
│   └── See DASHBOARD-PATTERNS.md → "Adding a New Dashboard"
│
├── Adding a panel to an existing dashboard
│   └── See DASHBOARD-PATTERNS.md → "Adding a New Panel"
│
├── Fixing datasource or auth issues
│   └── See TROUBLESHOOTING.md
│
├── Setting up Grafana infrastructure
│   └── See AUTH-AND-INFRA.md → "Workspace Provisioning"
│
├── Adding a new environment (staging/prod)
│   └── See AUTH-AND-INFRA.md → "Multi-Environment"
│
└── Understanding how auth works
    └── See AUTH-AND-INFRA.md → "Auth Model"
```

---

## Core Patterns

### 1. Auth: Self-Provisioned Ephemeral Tokens

AWS Managed Grafana does **not** support legacy API keys. The workspace HTTP API requires Bearer tokens (not SigV4).

**Solution**: `boto3` creates a Service Account + ephemeral token (5 min TTL) at script start. No manual key management.

```
IAM creds → boto3 grafana client → get/create Service Account → create token (300s) → Bearer header
```

See [AUTH-AND-INFRA.md](AUTH-AND-INFRA.md) for full details.

### 2. Datasource Naming Convention

MySQL datasources **must** be named `mysql-{env}` (e.g., `mysql-dev`, `mysql-staging`, `mysql-prod`).

Template variables use regex `/mysql-.*/` to discover datasources. Misnamed datasources won't appear in the dropdown.

### 3. Template Variables on Every Dashboard

Every dashboard includes 3 standard template variables via `_env_template_variables()`:

| Variable | Type | Purpose |
|----------|------|---------|
| `datasource` | datasource | MySQL datasource selector (regex `/mysql-.*/`) |
| `env` | custom | Environment dropdown (`AVAILABLE_ENVS` constant) |
| `cw_datasource` | datasource | CloudWatch datasource (hidden, avoids hardcoding UID) |

Dashboard-specific variables (e.g., `$ticker`) are added via the `extra_vars` parameter.

### 4. Panel Helpers

Seven reusable panel builder functions:

| Helper | Use Case | Datasource |
|--------|----------|------------|
| `stat_panel` | Single metric values | MySQL |
| `timeseries_panel` | Time-series line charts | MySQL |
| `table_panel` | Raw data tables | MySQL |
| `barchart_panel` | Horizontal bar comparisons | MySQL |
| `gauge_panel` | Threshold visualization | MySQL |
| `piechart_panel` | Distribution pie charts | MySQL |
| `cloudwatch_timeseries` | AWS CloudWatch metrics | CloudWatch |

### 5. Environment Expansion

Single constant controls multi-env support:

```python
AVAILABLE_ENVS = "dev"       # Future: "dev,staging,prod"
DEFAULT_ENV = "dev"           # Future: "prod"
```

---

## File Organization

```
.claude/skills/grafana/
├── SKILL.md                  # This file — entry point, decision tree
├── DASHBOARD-PATTERNS.md     # Panel types, SQL patterns, CloudWatch dimensions
├── AUTH-AND-INFRA.md         # Auth flow, workspace setup, datasource management
└── TROUBLESHOOTING.md        # Common issues: no data, auth errors, connectivity
```

---

## Key Source Files

| File | Purpose |
|------|---------|
| `scripts/build-grafana-dashboards.py` | Dashboard builder — auth, panels, deploy |
| `scripts/setup-grafana.sh` | Infrastructure provisioning (SG, IAM, workspace) |
| `db/migrations/028_create_grafana_readonly_user.sql` | MySQL read-only user for Grafana |
| `terraform/monitoring.tf` | CloudWatch alarms (feeds data to Grafana panels) |

---

## References

- [DASHBOARD-PATTERNS.md](DASHBOARD-PATTERNS.md) — Panel helpers, SQL patterns, CloudWatch dimensions
- [AUTH-AND-INFRA.md](AUTH-AND-INFRA.md) — Auth model, workspace provisioning, datasource management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Common issues and fixes
