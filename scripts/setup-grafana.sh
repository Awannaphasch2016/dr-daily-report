#!/usr/bin/env bash
# =============================================================================
# setup-grafana.sh — Provision AWS Managed Grafana for DR Daily Report
#
# Creates: Security Group, IAM Role + Policies, Secrets Manager, Workspace
# Idempotent: checks if each resource exists before creating
#
# Usage:
#   ./scripts/setup-grafana.sh              # provision all resources
#   ./scripts/setup-grafana.sh --cleanup    # tear down all resources
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate permissions
#   - IAM Identity Center enabled in the AWS account
#   - Doppler secret GRAFANA_MYSQL_PASSWORD set (or will prompt)
#   - Migration 028 executed (grafana_readonly MySQL user created)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REGION="ap-southeast-1"
PROJECT="dr-daily-report"
ENV="${ENV:-dev}"

WORKSPACE_NAME="${PROJECT}-grafana-${ENV}"
SG_NAME="${PROJECT}-grafana-${ENV}"
ROLE_NAME="${PROJECT}-grafana-role-${ENV}"
SECRET_NAME="${PROJECT}/grafana-mysql/${ENV}"
AURORA_SG_NAME="${PROJECT}-aurora-${ENV}"
AURORA_CLUSTER_ID="${PROJECT}-aurora-${ENV}"
SNS_TOPIC_NAME="${PROJECT}-telegram-alerts-${ENV}"
SUBNETS="subnet-0bfaf6ef0e1a456a6,subnet-0ef493a1aae3b4af4,subnet-012d60cbb95430cd6"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "$(date +%H:%M:%S) [INFO]  $*"; }
warn() { echo "$(date +%H:%M:%S) [WARN]  $*" >&2; }
fail() { echo "$(date +%H:%M:%S) [ERROR] $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Cleanup mode
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--cleanup" ]]; then
    echo "============================================"
    echo "  CLEANUP: Removing Grafana resources"
    echo "============================================"

    # Get workspace ID
    WORKSPACE_ID=$(aws grafana list-workspaces --region "$REGION" \
        --query "workspaces[?name=='${WORKSPACE_NAME}'].id" --output text 2>/dev/null || true)

    if [[ -n "$WORKSPACE_ID" && "$WORKSPACE_ID" != "None" ]]; then
        log "Deleting workspace: $WORKSPACE_ID"
        aws grafana delete-workspace --workspace-id "$WORKSPACE_ID" --region "$REGION"
        log "Waiting for workspace deletion..."
        while aws grafana describe-workspace --workspace-id "$WORKSPACE_ID" --region "$REGION" &>/dev/null; do
            sleep 10
        done
        log "Workspace deleted"
    else
        warn "No workspace found"
    fi

    # Delete secret
    if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
        log "Deleting secret: $SECRET_NAME"
        aws secretsmanager delete-secret --secret-id "$SECRET_NAME" \
            --force-delete-without-recovery --region "$REGION"
    fi

    # Delete IAM policies and role
    if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
        log "Deleting IAM role: $ROLE_NAME"
        aws iam delete-role-policy --role-name "$ROLE_NAME" \
            --policy-name "${PROJECT}-grafana-cloudwatch-${ENV}" 2>/dev/null || true
        aws iam delete-role-policy --role-name "$ROLE_NAME" \
            --policy-name "${PROJECT}-grafana-sns-${ENV}" 2>/dev/null || true
        aws iam delete-role --role-name "$ROLE_NAME"
    fi

    # Get SG IDs for cleanup
    GRAFANA_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${SG_NAME}" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || true)
    AURORA_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${AURORA_SG_NAME}" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || true)

    if [[ -n "$GRAFANA_SG_ID" && "$GRAFANA_SG_ID" != "None" ]]; then
        # Revoke Aurora ingress rule
        if [[ -n "$AURORA_SG_ID" && "$AURORA_SG_ID" != "None" ]]; then
            log "Revoking Aurora SG ingress from Grafana SG"
            aws ec2 revoke-security-group-ingress --group-id "$AURORA_SG_ID" \
                --protocol tcp --port 3306 --source-group "$GRAFANA_SG_ID" \
                --region "$REGION" 2>/dev/null || true
        fi

        # Wait for ENIs to detach (Grafana VPC cleanup can take a few minutes)
        log "Waiting for ENIs to detach from Grafana SG..."
        for i in $(seq 1 24); do
            ENI_COUNT=$(aws ec2 describe-network-interfaces \
                --filters "Name=group-id,Values=${GRAFANA_SG_ID}" \
                --query 'length(NetworkInterfaces)' --output text --region "$REGION" 2>/dev/null || echo "0")
            [[ "$ENI_COUNT" == "0" ]] && break
            sleep 10
        done

        log "Deleting security group: $GRAFANA_SG_ID"
        aws ec2 delete-security-group --group-id "$GRAFANA_SG_ID" --region "$REGION"
    fi

    echo ""
    echo "============================================"
    echo "  Cleanup complete"
    echo "============================================"
    exit 0
fi

# ---------------------------------------------------------------------------
# PROVISION MODE
# ---------------------------------------------------------------------------
echo "============================================"
echo "  Provisioning Grafana: ${WORKSPACE_NAME}"
echo "  Region: ${REGION}"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Lookup existing resource IDs
# ---------------------------------------------------------------------------
log "Step 1: Looking up existing resources..."

VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' --output text --region "$REGION")
[[ -z "$VPC_ID" || "$VPC_ID" == "None" ]] && fail "Default VPC not found"
log "  VPC: $VPC_ID"

AURORA_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${AURORA_SG_NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text --region "$REGION")
[[ -z "$AURORA_SG_ID" || "$AURORA_SG_ID" == "None" ]] && fail "Aurora SG '${AURORA_SG_NAME}' not found"
log "  Aurora SG: $AURORA_SG_ID"

AURORA_ENDPOINT=$(aws rds describe-db-clusters \
    --db-cluster-identifier "$AURORA_CLUSTER_ID" \
    --query 'DBClusters[0].Endpoint' --output text --region "$REGION")
[[ -z "$AURORA_ENDPOINT" || "$AURORA_ENDPOINT" == "None" ]] && fail "Aurora cluster '${AURORA_CLUSTER_ID}' not found"
log "  Aurora endpoint: $AURORA_ENDPOINT"

SNS_ARN=$(aws sns list-topics --region "$REGION" \
    --query "Topics[?contains(TopicArn,'${SNS_TOPIC_NAME}')].TopicArn" \
    --output text)
[[ -z "$SNS_ARN" || "$SNS_ARN" == "None" ]] && warn "SNS topic '${SNS_TOPIC_NAME}' not found — skipping SNS policy"
log "  SNS ARN: ${SNS_ARN:-none}"

echo ""

# ---------------------------------------------------------------------------
# Step 2: Create Grafana security group
# ---------------------------------------------------------------------------
log "Step 2: Security group..."

GRAFANA_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${SG_NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || true)

if [[ -n "$GRAFANA_SG_ID" && "$GRAFANA_SG_ID" != "None" ]]; then
    log "  Already exists: $GRAFANA_SG_ID"
else
    GRAFANA_SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "Security group for Managed Grafana VPC connectivity" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' --output text --region "$REGION")

    aws ec2 create-tags --resources "$GRAFANA_SG_ID" \
        --tags \
            Key=Name,Value=${PROJECT}-grafana-sg \
            Key=Project,Value=${PROJECT} \
            Key=ManagedBy,Value=aws-cli \
            Key=Environment,Value=${ENV} \
            Key=Owner,Value=data-team \
            Key=App,Value=shared \
            Key=Component,Value=grafana-security-group \
        --region "$REGION"

    log "  Created: $GRAFANA_SG_ID"
fi

# ---------------------------------------------------------------------------
# Step 3: Add ingress rule on Aurora SG
# ---------------------------------------------------------------------------
log "Step 3: Aurora SG ingress rule (3306 from Grafana SG)..."

if aws ec2 authorize-security-group-ingress \
    --group-id "$AURORA_SG_ID" \
    --ip-permissions "IpProtocol=tcp,FromPort=3306,ToPort=3306,UserIdGroupPairs=[{GroupId=${GRAFANA_SG_ID},Description=MySQL from Managed Grafana}]" \
    --region "$REGION" 2>&1 | grep -q "InvalidPermission.Duplicate"; then
    log "  Already exists"
else
    log "  Added ingress rule"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 4: Create IAM role
# ---------------------------------------------------------------------------
log "Step 4: IAM role..."

if aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
    log "  Already exists"
else
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "grafana.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --tags \
            Key=Project,Value=${PROJECT} \
            Key=Environment,Value=${ENV} \
            Key=App,Value=shared \
            Key=Component,Value=iam-role \
        --output text --query 'Role.Arn' > /dev/null
    log "  Created"
fi

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
log "  ARN: $ROLE_ARN"

# ---------------------------------------------------------------------------
# Step 5: CloudWatch read policy
# ---------------------------------------------------------------------------
log "Step 5: CloudWatch read policy..."

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "${PROJECT}-grafana-cloudwatch-${ENV}" \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "cloudwatch:DescribeAlarmsForMetric",
                "cloudwatch:DescribeAlarmHistory",
                "cloudwatch:DescribeAlarms",
                "cloudwatch:ListMetrics",
                "cloudwatch:GetMetricData",
                "cloudwatch:GetMetricStatistics",
                "logs:DescribeLogGroups",
                "logs:GetLogGroupFields",
                "logs:StartQuery",
                "logs:StopQuery",
                "logs:GetQueryResults",
                "logs:GetLogEvents"
            ],
            "Resource": "*"
        }]
    }'
log "  Applied"

# ---------------------------------------------------------------------------
# Step 6: SNS publish policy (for Grafana alerting → Slack)
# ---------------------------------------------------------------------------
log "Step 6: SNS publish policy..."

if [[ -n "$SNS_ARN" && "$SNS_ARN" != "None" ]]; then
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "${PROJECT}-grafana-sns-${ENV}" \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": [\"sns:Publish\"],
                \"Resource\": \"${SNS_ARN}\"
            }]
        }"
    log "  Applied (topic: $SNS_ARN)"
else
    warn "  Skipped — no SNS topic found"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 7: Secrets Manager (Grafana MySQL credentials)
# ---------------------------------------------------------------------------
log "Step 7: Secrets Manager..."

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$REGION" &>/dev/null; then
    log "  Already exists: $SECRET_NAME"
else
    # Get password from env, Doppler, or prompt
    GRAFANA_PW="${GRAFANA_MYSQL_PASSWORD:-}"
    if [[ -z "$GRAFANA_PW" ]]; then
        GRAFANA_PW=$(doppler secrets get GRAFANA_MYSQL_PASSWORD --plain --config "${ENV}" 2>/dev/null || true)
    fi
    if [[ -z "$GRAFANA_PW" ]]; then
        read -sp "Enter Grafana MySQL password for grafana_readonly user: " GRAFANA_PW
        echo ""
    fi
    [[ -z "$GRAFANA_PW" ]] && fail "No password provided"

    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Grafana read-only MySQL credentials for ${ENV}" \
        --secret-string "{
            \"username\": \"grafana_readonly\",
            \"password\": \"${GRAFANA_PW}\",
            \"host\": \"${AURORA_ENDPOINT}\",
            \"port\": 3306,
            \"database\": \"ticker_data\"
        }" \
        --tags \
            Key=Project,Value=${PROJECT} \
            Key=ManagedBy,Value=aws-cli \
            Key=Environment,Value=${ENV} \
            Key=App,Value=shared \
            Key=Component,Value=secrets-manager \
        --region "$REGION" > /dev/null
    log "  Created: $SECRET_NAME"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 8: Create Grafana workspace
# ---------------------------------------------------------------------------
log "Step 8: Grafana workspace..."

WORKSPACE_ID=$(aws grafana list-workspaces --region "$REGION" \
    --query "workspaces[?name=='${WORKSPACE_NAME}'].id" --output text 2>/dev/null || true)

if [[ -n "$WORKSPACE_ID" && "$WORKSPACE_ID" != "None" ]]; then
    log "  Already exists: $WORKSPACE_ID"
else
    WORKSPACE_ID=$(aws grafana create-workspace \
        --workspace-name "$WORKSPACE_NAME" \
        --account-access-type CURRENT_ACCOUNT \
        --authentication-providers SAML \
        --permission-type SERVICE_MANAGED \
        --workspace-role-arn "$ROLE_ARN" \
        --workspace-data-sources CLOUDWATCH \
        --grafana-version "10.4" \
        --vpc-configuration "{\"securityGroupIds\":[\"${GRAFANA_SG_ID}\"],\"subnetIds\":[\"subnet-0bfaf6ef0e1a456a6\",\"subnet-0ef493a1aae3b4af4\",\"subnet-012d60cbb95430cd6\"]}" \
        --configuration '{"plugins":{"pluginAdminEnabled":true},"unifiedAlerting":{"enabled":true}}' \
        --query 'workspace.id' --output text \
        --region "$REGION")
    # Note: --tags omitted due to grafana:TagResource permission requirement.
    # Add tags via console or after granting grafana:TagResource to your IAM user.
    log "  Created: $WORKSPACE_ID"
fi

log "  Waiting for workspace to become ACTIVE..."
for i in $(seq 1 40); do
    STATUS=$(aws grafana describe-workspace --workspace-id "$WORKSPACE_ID" \
        --query 'workspace.status' --output text --region "$REGION")
    if [[ "$STATUS" == "ACTIVE" ]]; then
        break
    fi
    echo "    Status: $STATUS (attempt $i/40, waiting 15s...)"
    sleep 15
done

if [[ "$STATUS" != "ACTIVE" ]]; then
    fail "Workspace did not become ACTIVE after 10 minutes. Current status: $STATUS"
fi

ENDPOINT=$(aws grafana describe-workspace --workspace-id "$WORKSPACE_ID" \
    --query 'workspace.endpoint' --output text --region "$REGION")

echo ""
echo "============================================"
echo "  Grafana workspace ready!"
echo "  URL:          https://${ENDPOINT}"
echo "  Workspace ID: ${WORKSPACE_ID}"
echo "  Region:       ${REGION}"
echo "============================================"

# ---------------------------------------------------------------------------
# Step 9: Post-deploy instructions
# ---------------------------------------------------------------------------
echo ""
echo "NEXT STEPS (manual):"
echo ""
echo "1. Assign SSO user as Admin:"
echo "   AWS Console → Amazon Managed Grafana → ${WORKSPACE_NAME} → Assign user"
echo ""
echo "2. Configure MySQL datasource in Grafana UI:"
echo "   IMPORTANT: Name the datasource 'mysql-${ENV}' (e.g. mysql-dev, mysql-staging, mysql-prod)"
echo "   The dashboard template variables use regex /mysql-.*/ to discover datasources."
echo "   Host: ${AURORA_ENDPOINT}:3306"
echo "   Database: ticker_data"
echo "   User: grafana_readonly"
echo "   Password: (from Secrets Manager: ${SECRET_NAME})"
echo ""
echo "3. CloudWatch datasource:"
echo "   Auto-configured via IAM role — just select region ${REGION}"
echo ""
echo "4. Build dashboards:"
echo "   export GRAFANA_API_KEY=\"...\""
echo "   python scripts/build-grafana-dashboards.py"
echo ""
echo "5. Multi-environment setup (when staging/prod prerequisites are met):"
echo "   a. Run migration 028 on target Aurora (creates grafana_readonly user)"
echo "   b. Add AMG security group egress to target Aurora on port 3306"
echo "   c. Register 'mysql-staging' / 'mysql-prod' datasource in Grafana UI"
echo "   d. Update AVAILABLE_ENVS in build-grafana-dashboards.py"
echo ""
