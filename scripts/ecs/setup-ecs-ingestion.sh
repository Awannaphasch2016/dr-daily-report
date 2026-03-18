#!/usr/bin/env bash
# ===========================================================================
# One-time ECS Fargate setup for ingestion tasks
#
# Creates: ECR repo, ECS cluster, IAM roles, CloudWatch log group,
#          task definition. Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/ecs/setup-ecs-ingestion.sh          # dev (default)
#   ./scripts/ecs/setup-ecs-ingestion.sh staging
#   ./scripts/ecs/setup-ecs-ingestion.sh prod
# ===========================================================================

set -euo pipefail

ENV="${1:-dev}"
REGION="ap-southeast-1"
ACCOUNT_ID="755283537543"
PROJECT="dr-daily-report"

# Resource names
ECR_REPO="${PROJECT}-ingestion-${ENV}"
ECS_CLUSTER="${PROJECT}-ingestion-${ENV}"
LOG_GROUP="/ecs/${PROJECT}-ingestion-${ENV}"
EXEC_ROLE_NAME="${PROJECT}-ecs-execution-${ENV}"
TASK_ROLE_NAME="${PROJECT}-ecs-task-${ENV}"
TASK_DEF_FAMILY="mops-ingestion-${ENV}"

# Aurora config (from Doppler)
AURORA_HOST="${PROJECT}-aurora-${ENV}.cluster-c9a0288e4hqm.${REGION}.rds.amazonaws.com"
AURORA_PORT="3306"
AURORA_DATABASE="ticker_data"
AURORA_USER=$(doppler secrets get AURORA_USER --plain -p dr-daily-report -c "${ENV}" 2>/dev/null || echo "admin")
AURORA_PASSWORD=$(doppler secrets get AURORA_MASTER_PASSWORD --plain -p dr-daily-report -c "${ENV}" 2>/dev/null || echo "")

DATA_LAKE_BUCKET="${PROJECT}-data-lake-${ENV}"

# Security group (Lambda/Aurora SG per environment)
declare -A SG_MAP=(
    [dev]="sg-0185a0d8d92968d03"
    [staging]="sg-0b417197a133a2e32"
    [prod]="sg-06af9bdfe48e9f9d0"
)
SECURITY_GROUP="${SG_MAP[$ENV]}"

# Subnets with NAT gateway
SUBNETS='["subnet-0bfaf6ef0e1a456a6","subnet-0ef493a1aae3b4af4","subnet-012d60cbb95430cd6"]'

echo "============================================================"
echo "ECS Fargate Ingestion Setup"
echo "  Environment: ${ENV}"
echo "  Region:      ${REGION}"
echo "  Cluster:     ${ECS_CLUSTER}"
echo "  ECR Repo:    ${ECR_REPO}"
echo "============================================================"

# -------------------------------------------------------------------
# 1. IAM: Attach ECS/ECR permissions to current user
# -------------------------------------------------------------------
echo ""
echo "[1/7] Attaching ECS/ECR permissions to IAM user..."

POLICY_NAME="${PROJECT}-ecs-user-access-${ENV}"
cat > /tmp/ecs-user-policy.json << 'POLICY'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:CreateCluster",
                "ecs:DescribeClusters",
                "ecs:ListClusters",
                "ecs:RegisterTaskDefinition",
                "ecs:DeregisterTaskDefinition",
                "ecs:DescribeTaskDefinition",
                "ecs:ListTaskDefinitions",
                "ecs:RunTask",
                "ecs:StopTask",
                "ecs:DescribeTasks",
                "ecs:ListTasks",
                "ecr:CreateRepository",
                "ecr:DescribeRepositories",
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "logs:CreateLogGroup",
                "logs:DescribeLogGroups",
                "logs:GetLogEvents",
                "logs:FilterLogEvents",
                "logs:PutRetentionPolicy",
                "logs:TagLogGroup",
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:CreatePolicy",
                "iam:CreatePolicyVersion",
                "iam:ListPolicies",
                "iam:GetRole",
                "iam:PassRole"
            ],
            "Resource": "*"
        }
    ]
}
POLICY

# Create or update the policy
POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${POLICY_NAME}'].Arn" --output text 2>/dev/null || echo "")
if [ -z "$POLICY_ARN" ]; then
    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/ecs-user-policy.json \
        --query 'Policy.Arn' --output text)
    echo "  Created policy: ${POLICY_ARN}"
else
    # Update existing policy (create new version, set as default)
    aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document file:///tmp/ecs-user-policy.json \
        --set-as-default > /dev/null 2>&1 || true
    echo "  Updated policy: ${POLICY_ARN}"
fi

# Attach to current user
CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text | grep -oP '(?<=user/).*' || echo "anak")
aws iam attach-user-policy --user-name "$CURRENT_USER" --policy-arn "$POLICY_ARN" 2>/dev/null || true
echo "  Attached to user: ${CURRENT_USER}"

# -------------------------------------------------------------------
# 2. ECR Repository
# -------------------------------------------------------------------
echo ""
echo "[2/7] Creating ECR repository..."

aws ecr create-repository \
    --repository-name "$ECR_REPO" \
    --region "$REGION" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability IMMUTABLE \
    > /dev/null 2>&1 || echo "  (already exists)"
echo "  ECR: ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

# -------------------------------------------------------------------
# 3. ECS Cluster
# -------------------------------------------------------------------
echo ""
echo "[3/7] Creating ECS cluster..."

aws ecs create-cluster \
    --cluster-name "$ECS_CLUSTER" \
    --region "$REGION" \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    > /dev/null 2>&1 || echo "  (already exists)"
echo "  Cluster: ${ECS_CLUSTER}"

# -------------------------------------------------------------------
# 4. CloudWatch Log Group
# -------------------------------------------------------------------
echo ""
echo "[4/7] Creating CloudWatch log group..."

aws logs create-log-group \
    --log-group-name "$LOG_GROUP" \
    --region "$REGION" \
    > /dev/null 2>&1 || echo "  (already exists)"

aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP" \
    --retention-in-days 30 \
    --region "$REGION" \
    > /dev/null 2>&1 || echo "  (retention policy skipped — IAM not yet propagated)"
echo "  Log group: ${LOG_GROUP}"

# -------------------------------------------------------------------
# 5. IAM Execution Role (ECR pull + CloudWatch logs)
# -------------------------------------------------------------------
echo ""
echo "[5/7] Creating ECS execution role..."

cat > /tmp/ecs-trust-policy.json << 'TRUST'
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
    }]
}
TRUST

aws iam create-role \
    --role-name "$EXEC_ROLE_NAME" \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    > /dev/null 2>&1 || echo "  (already exists)"

aws iam attach-role-policy \
    --role-name "$EXEC_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" \
    > /dev/null 2>&1
echo "  Execution role: ${EXEC_ROLE_NAME}"

# -------------------------------------------------------------------
# 6. IAM Task Role (S3 + Aurora)
# -------------------------------------------------------------------
echo ""
echo "[6/7] Creating ECS task role..."

aws iam create-role \
    --role-name "$TASK_ROLE_NAME" \
    --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
    > /dev/null 2>&1 || echo "  (already exists)"

cat > /tmp/ecs-task-policy.json << TASKPOLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::${DATA_LAKE_BUCKET}",
                "arn:aws:s3:::${DATA_LAKE_BUCKET}/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBClusters",
                "rds:DescribeDBInstances"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:${LOG_GROUP}:*"
        }
    ]
}
TASKPOLICY

TASK_POLICY_NAME="${PROJECT}-ecs-task-policy-${ENV}"
TASK_POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${TASK_POLICY_NAME}'].Arn" --output text 2>/dev/null || echo "")
if [ -z "$TASK_POLICY_ARN" ]; then
    TASK_POLICY_ARN=$(aws iam create-policy \
        --policy-name "$TASK_POLICY_NAME" \
        --policy-document file:///tmp/ecs-task-policy.json \
        --query 'Policy.Arn' --output text)
else
    aws iam create-policy-version \
        --policy-arn "$TASK_POLICY_ARN" \
        --policy-document file:///tmp/ecs-task-policy.json \
        --set-as-default > /dev/null 2>&1 || true
fi

aws iam attach-role-policy \
    --role-name "$TASK_ROLE_NAME" \
    --policy-arn "$TASK_POLICY_ARN" \
    > /dev/null 2>&1
echo "  Task role: ${TASK_ROLE_NAME}"

# -------------------------------------------------------------------
# 7. ECS Task Definition
# -------------------------------------------------------------------
echo ""
echo "[7/7] Registering ECS task definition..."

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

cat > /tmp/ecs-task-def.json << TASKDEF
{
    "family": "${TASK_DEF_FAMILY}",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/${EXEC_ROLE_NAME}",
    "taskRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/${TASK_ROLE_NAME}",
    "containerDefinitions": [{
        "name": "ingestion",
        "image": "${ECR_URI}:latest",
        "essential": true,
        "environment": [
            {"name": "AURORA_HOST", "value": "${AURORA_HOST}"},
            {"name": "AURORA_PORT", "value": "${AURORA_PORT}"},
            {"name": "AURORA_DATABASE", "value": "${AURORA_DATABASE}"},
            {"name": "AURORA_USER", "value": "${AURORA_USER}"},
            {"name": "AURORA_PASSWORD", "value": "${AURORA_PASSWORD}"},
            {"name": "DATA_LAKE_BUCKET", "value": "${DATA_LAKE_BUCKET}"},
            {"name": "ENVIRONMENT", "value": "${ENV}"},
            {"name": "LOG_LEVEL", "value": "INFO"}
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": "${LOG_GROUP}",
                "awslogs-region": "${REGION}",
                "awslogs-stream-prefix": "ingestion"
            }
        }
    }]
}
TASKDEF

aws ecs register-task-definition \
    --cli-input-json file:///tmp/ecs-task-def.json \
    --region "$REGION" \
    > /dev/null 2>&1
echo "  Task definition: ${TASK_DEF_FAMILY}"

# -------------------------------------------------------------------
# Cleanup temp files
# -------------------------------------------------------------------
rm -f /tmp/ecs-trust-policy.json /tmp/ecs-user-policy.json /tmp/ecs-task-policy.json /tmp/ecs-task-def.json

echo ""
echo "============================================================"
echo "SETUP COMPLETE"
echo ""
echo "Next steps:"
echo "  1. Build & push image: ./scripts/ecs/run-mops-ingestion.sh --build"
echo "  2. Run dry-run:        ./scripts/ecs/run-mops-ingestion.sh --dry-run --years-back 1"
echo "  3. Run ingestion:      ./scripts/ecs/run-mops-ingestion.sh --years-back 3"
echo "============================================================"
