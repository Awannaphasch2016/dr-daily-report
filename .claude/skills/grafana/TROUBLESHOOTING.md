---
name: grafana-troubleshooting
description: Common Grafana issues and fixes — no data, auth errors, datasource connectivity, dashboard deploy failures
---

# Troubleshooting

Common issues when working with AWS Managed Grafana and the dashboard builder script.

---

## "No Data" on Panels

### Datasource Name Mismatch

**Symptom**: Panel shows "No data" even though tables have data.

**Cause**: MySQL datasource not named `mysql-{env}`.

**Fix**: Rename datasource to follow convention:
- In Grafana UI: Data sources → MySQL → Settings → Name → `mysql-dev`
- Or let the script auto-rename: `rename_datasource_if_needed(MYSQL_DS_UID, DEFAULT_MYSQL_DS)`

### Template Variable Not Selected

**Symptom**: Panels show "No data" intermittently.

**Cause**: Template variable dropdown at top of dashboard not selected (blank).

**Fix**: Select a value from each dropdown (Database, Environment). Verify `$datasource`, `$env`, and `$cw_datasource` all have values.

### Aurora Tables Empty

**Symptom**: All MySQL panels show "No data", CloudWatch panels work fine.

**Cause**: No data in Aurora tables.

**Fix**: Verify data exists by running SQL directly:
```sql
SELECT COUNT(*) FROM daily_prices;
SELECT COUNT(*) FROM user_requests;
SELECT MAX(price_date) FROM daily_prices;
```

### Time Range Too Narrow

**Symptom**: Time-series panels show "No data" but stat panels work.

**Cause**: Dashboard time picker set to a range with no data (e.g., "Last 1 hour" but data is daily).

**Fix**: Widen the time range. Pipeline Health defaults to `now-24h`, Strategy Performance to `now-90d`.

### CloudWatch Dimension Mismatch

**Symptom**: CloudWatch panels show "No data".

**Cause**: Lambda function names don't match the expected pattern `{PROJECT_NAME}-{base}-{env}`.

**Fix**: Verify Lambda function names in AWS Console match `LAMBDA_BASE_NAMES`:
```python
LAMBDA_BASE_NAMES = [
    "telegram-api", "report-worker", "ticker-scheduler",
    "precompute-controller", "line-bot", "credit-checker",
]
# Expected: dr-daily-report-telegram-api-dev, etc.
```

---

## Auth Errors

### "API key" Errors

**Symptom**: Error mentioning API keys.

**Cause**: Attempting to use legacy Grafana API keys, which AWS Managed Grafana does not support.

**Fix**: Use Service Account Tokens. The `build-grafana-dashboards.py` script handles this automatically via `get_grafana_token()`. Do not try to create API keys manually.

### boto3 Permission Error

**Symptom**: `AccessDeniedException` or `UnauthorizedException` when running the script.

**Cause**: IAM user/role missing required `grafana:*` permissions.

**Fix**: Ensure the IAM entity has these permissions:
```
grafana:ListWorkspaceServiceAccounts
grafana:CreateWorkspaceServiceAccount
grafana:ListWorkspaceServiceAccountTokens
grafana:CreateWorkspaceServiceAccountToken
grafana:DeleteWorkspaceServiceAccountToken
```

### Token Expired

**Symptom**: `401 Unauthorized` when pushing dashboards.

**Cause**: Token expired (5-minute TTL) — can happen if script pauses or is run interactively.

**Fix**: Re-run the script. It auto-provisions a fresh token on each execution. The `_cleanup_stale_tokens()` function removes old tokens first.

### "Cannot connect to Grafana API" on Startup

**Symptom**: Script exits with `ERROR: Cannot connect to Grafana API: {status_code}`.

**Cause**: Token provisioning succeeded but API call failed.

**Fix**:
1. Check `WORKSPACE_ID` and `REGION` constants match your workspace
2. Verify workspace is `ACTIVE`: `aws grafana describe-workspace --workspace-id g-4df4c51648 --region ap-southeast-1`
3. Verify network connectivity (workspace endpoint must be reachable)

---

## Datasource Connectivity

### Security Group: Grafana Cannot Reach Aurora

**Symptom**: MySQL datasource shows "connection refused" or timeout in Grafana.

**Cause**: Aurora security group missing ingress rule from Grafana security group on port 3306.

**Fix**: `setup-grafana.sh` Step 3 handles this. Verify manually:
```bash
# Check Aurora SG has ingress from Grafana SG
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=dr-daily-report-aurora-dev" \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`3306`]' \
  --region ap-southeast-1
```

### grafana_readonly User Does Not Exist

**Symptom**: MySQL datasource shows "Access denied for user 'grafana_readonly'".

**Cause**: Migration 028 not executed on the target Aurora cluster.

**Fix**: Run `db/migrations/028_create_grafana_readonly_user.sql` via SSM tunnel:
```bash
# 1. Start SSM tunnel
aws ssm start-session --target i-0dab21bdf83ce9aaf \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["<aurora-endpoint>"],"portNumber":["3306"],"localPortNumber":["3307"]}' \
  --region ap-southeast-1

# 2. Connect and run migration
mysql -h 127.0.0.1 -P 3307 -u admin -p ticker_data < db/migrations/028_create_grafana_readonly_user.sql
```

### Wrong Password

**Symptom**: "Access denied for user 'grafana_readonly'" after migration 028 was run.

**Cause**: Password mismatch between Grafana datasource config and what was set in migration 028.

**Fix**: Password should match what's in Secrets Manager (`dr-daily-report/grafana-mysql/{env}`), which comes from Doppler `GRAFANA_MYSQL_PASSWORD`.

---

## Dashboard Deploy Failures

### 401/403 on Push

**Symptom**: `ERROR pushing dashboard: 401` or `403`.

**Cause**: Token provisioning failed or token has insufficient permissions.

**Fix**:
1. Check IAM permissions (see Auth Errors above)
2. Verify Service Account has `ADMIN` role (set in `_get_or_create_service_account()`)
3. Re-run the script (auto-provisions fresh token)

### 412 Conflict

**Symptom**: `ERROR pushing dashboard: 412`.

**Cause**: Dashboard UID conflict with version mismatch.

**Fix**: Already handled — `push_dashboard()` sets `overwrite: True`. If still failing, manually delete the dashboard in Grafana UI and re-deploy.

### Panels Show "Datasource not found"

**Symptom**: Dashboard deploys successfully but panels show "datasource not found" error.

**Cause**: Panels reference `${datasource}` or `${cw_datasource}` template variables, but the datasource isn't registered or isn't named correctly.

**Fix**:
1. Verify MySQL datasource exists and is named `mysql-{env}`
2. Verify CloudWatch datasource exists (should be auto-configured)
3. Refresh the dashboard page (template variables sometimes need a page reload)

### Snapshot Creation Fails

**Symptom**: Dashboard pushes successfully but snapshot creation returns an error.

**Cause**: Snapshot API may have different permission requirements or the dashboard has template variables that can't be resolved in snapshot mode.

**Fix**: Snapshots are nice-to-have (public view without login, 24h expiry). If they fail, the dashboard itself is still accessible via the workspace URL.
