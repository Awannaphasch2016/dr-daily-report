#!/usr/bin/env bash
# =============================================================================
# setup-webhook-health.sh — Provision webhook health check Lambda + schedule
#
# Creates: Lambda function, EventBridge schedule, CloudWatch log group + alarm
# Idempotent: checks if each resource exists before creating
#
# Usage:
#   ./scripts/setup-webhook-health.sh              # provision all resources
#   ./scripts/setup-webhook-health.sh --cleanup    # tear down all resources
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate permissions
#   - Existing ECR image (shared container) and Lambda execution role
#   - LINE_WEBHOOK_URL known (from Lambda function URL output)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REGION="ap-southeast-1"
PROJECT="dr-daily-report"
ENV="${ENV:-dev}"

FUNCTION_NAME="${PROJECT}-webhook-health-${ENV}"
LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"
ALARM_NAME="${FUNCTION_NAME}-errors-${ENV}"
SCHEDULE_NAME="${FUNCTION_NAME}"
HANDLER="src.scheduler.webhook_health_handler.lambda_handler"
TIMEOUT=60
MEMORY=256

# Networking (same as other schedulers)
SUBNETS="subnet-0bfaf6ef0e1a456a6,subnet-0ef493a1aae3b4af4,subnet-012d60cbb95430cd6"
LAMBDA_SG_NAME="${PROJECT}-lambda-aurora-${ENV}"
SNS_TOPIC_NAME="${PROJECT}-telegram-alerts-${ENV}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "$(date +%H:%M:%S) [INFO]  $*"; }
warn() { echo "$(date +%H:%M:%S) [WARN]  $*" >&2; }
fail() { echo "$(date +%H:%M:%S) [ERROR] $*" >&2; exit 1; }

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Reuse the same container image as the ticker-scheduler (shared codebase)
ECR_IMAGE=$(aws lambda get-function \
    --function-name "${PROJECT}-ticker-scheduler-${ENV}" \
    --query 'Code.ImageUri' --output text --region "$REGION")
[[ -z "$ECR_IMAGE" || "$ECR_IMAGE" == "None" ]] && fail "Could not get ECR image from ticker-scheduler Lambda"

# ---------------------------------------------------------------------------
# Cleanup mode
# ---------------------------------------------------------------------------
if [[ "${1:-}" == "--cleanup" ]]; then
    echo "============================================"
    echo "  CLEANUP: Removing webhook health resources"
    echo "============================================"

    log "Deleting EventBridge schedule..."
    aws scheduler delete-schedule --name "$SCHEDULE_NAME" --region "$REGION" 2>/dev/null || warn "Schedule not found"

    log "Deleting CloudWatch alarm..."
    aws cloudwatch delete-alarms --alarm-names "$ALARM_NAME" --region "$REGION" 2>/dev/null || warn "Alarm not found"

    log "Deleting Lambda function..."
    aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || warn "Lambda not found"

    log "Deleting CloudWatch log group..."
    aws logs delete-log-group --log-group-name "$LOG_GROUP" --region "$REGION" 2>/dev/null || warn "Log group not found"

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
echo "  Provisioning: ${FUNCTION_NAME}"
echo "  Region: ${REGION}"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Lookup existing resource IDs
# ---------------------------------------------------------------------------
log "Step 1: Looking up existing resources..."

LAMBDA_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${LAMBDA_SG_NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || true)
[[ -z "$LAMBDA_SG_ID" || "$LAMBDA_SG_ID" == "None" ]] && fail "Lambda SG '${LAMBDA_SG_NAME}' not found"
log "  Lambda SG: $LAMBDA_SG_ID"

ROLE_ARN=$(aws iam get-role \
    --role-name "${PROJECT}-telegram-api-role-${ENV}" \
    --query 'Role.Arn' --output text 2>/dev/null || true)
[[ -z "$ROLE_ARN" || "$ROLE_ARN" == "None" ]] && fail "${PROJECT}-telegram-api-role-${ENV} not found"
log "  Role ARN: $ROLE_ARN"

SNS_ARN=$(aws sns list-topics --region "$REGION" \
    --query "Topics[?contains(TopicArn,'${SNS_TOPIC_NAME}')].TopicArn | [0]" \
    --output text 2>/dev/null || true)
log "  SNS ARN: ${SNS_ARN:-none}"

# Get LINE webhook URL from the existing Lambda function URL
LINE_WEBHOOK_URL="${LINE_WEBHOOK_URL:-}"
if [[ -z "$LINE_WEBHOOK_URL" ]]; then
    LINE_WEBHOOK_URL=$(aws lambda get-function-url-config \
        --function-name "${PROJECT}-line-bot-${ENV}" \
        --query 'FunctionUrl' --output text --region "$REGION" 2>/dev/null || true)
fi
[[ -z "$LINE_WEBHOOK_URL" || "$LINE_WEBHOOK_URL" == "None" ]] && warn "LINE_WEBHOOK_URL not found — Lambda will need manual env var update"
log "  LINE Webhook URL: ${LINE_WEBHOOK_URL:-NOT SET}"

# Get Aurora env vars from an existing Lambda (reuse config)
AURORA_HOST=$(aws lambda get-function-configuration \
    --function-name "${PROJECT}-ticker-scheduler-${ENV}" \
    --query "Environment.Variables.AURORA_HOST" --output text --region "$REGION" 2>/dev/null || true)
AURORA_USER=$(aws lambda get-function-configuration \
    --function-name "${PROJECT}-ticker-scheduler-${ENV}" \
    --query "Environment.Variables.AURORA_USER" --output text --region "$REGION" 2>/dev/null || true)
AURORA_PASSWORD=$(aws lambda get-function-configuration \
    --function-name "${PROJECT}-ticker-scheduler-${ENV}" \
    --query "Environment.Variables.AURORA_PASSWORD" --output text --region "$REGION" 2>/dev/null || true)
AURORA_DATABASE=$(aws lambda get-function-configuration \
    --function-name "${PROJECT}-ticker-scheduler-${ENV}" \
    --query "Environment.Variables.AURORA_DATABASE" --output text --region "$REGION" 2>/dev/null || true)

[[ -z "$AURORA_HOST" || "$AURORA_HOST" == "None" ]] && fail "Could not read AURORA_HOST from ticker-scheduler Lambda"
log "  Aurora host: $AURORA_HOST"

echo ""

# ---------------------------------------------------------------------------
# Step 2: CloudWatch Log Group
# ---------------------------------------------------------------------------
log "Step 2: CloudWatch log group..."

if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$REGION" \
    --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" --output text | grep -q "$LOG_GROUP"; then
    log "  Already exists"
else
    aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$REGION"
    aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30 --region "$REGION"
    log "  Created (retention: 30 days)"
fi

echo ""

# ---------------------------------------------------------------------------
# Step 3: Lambda function
# ---------------------------------------------------------------------------
log "Step 3: Lambda function..."

ENV_VARS="{\"Variables\":{\"TZ\":\"Asia/Bangkok\",\"AURORA_HOST\":\"${AURORA_HOST}\",\"AURORA_USER\":\"${AURORA_USER}\",\"AURORA_PASSWORD\":\"${AURORA_PASSWORD}\",\"AURORA_DATABASE\":\"${AURORA_DATABASE}\",\"LINE_WEBHOOK_URL\":\"${LINE_WEBHOOK_URL:-}\",\"SNS_TOPIC_ARN\":\"${SNS_ARN:-}\"}}"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
    log "  Already exists — updating configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --environment "$ENV_VARS" \
        --region "$REGION" > /dev/null
    log "  Configuration updated"

    # Wait for update to complete before updating code
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$ECR_IMAGE" \
        --region "$REGION" > /dev/null
    log "  Code updated"
else
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --package-type Image \
        --code "ImageUri=${ECR_IMAGE}" \
        --role "$ROLE_ARN" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --environment "$ENV_VARS" \
        --image-config "Command=${HANDLER}" \
        --vpc-config "SubnetIds=${SUBNETS},SecurityGroupIds=${LAMBDA_SG_ID}" \
        --tags "Project=${PROJECT},Environment=${ENV},App=shared,ManagedBy=aws-cli,Component=webhook-health" \
        --region "$REGION" > /dev/null
    log "  Created"
fi

# Wait for function to be active
log "  Waiting for function to be active..."
aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME" --region "$REGION"
log "  Function is active"

echo ""

# ---------------------------------------------------------------------------
# Step 4: Lambda alias (live)
# ---------------------------------------------------------------------------
log "Step 4: Lambda alias..."

LATEST_VERSION=$(aws lambda publish-version \
    --function-name "$FUNCTION_NAME" \
    --query 'Version' --output text --region "$REGION")
log "  Published version: $LATEST_VERSION"

if aws lambda get-alias --function-name "$FUNCTION_NAME" --name live --region "$REGION" &>/dev/null; then
    aws lambda update-alias \
        --function-name "$FUNCTION_NAME" \
        --name live \
        --function-version "$LATEST_VERSION" \
        --region "$REGION" > /dev/null
    log "  Alias 'live' updated to v${LATEST_VERSION}"
else
    aws lambda create-alias \
        --function-name "$FUNCTION_NAME" \
        --name live \
        --function-version "$LATEST_VERSION" \
        --region "$REGION" > /dev/null
    log "  Alias 'live' created at v${LATEST_VERSION}"
fi

LAMBDA_ALIAS_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}:live"

echo ""

# ---------------------------------------------------------------------------
# Step 5: EventBridge Scheduler
# ---------------------------------------------------------------------------
log "Step 5: EventBridge schedule (5 AM Bangkok daily)..."

# Create scheduler role if needed
SCHEDULER_ROLE_NAME="${PROJECT}-scheduler-webhook-health-${ENV}"
if ! aws iam get-role --role-name "$SCHEDULER_ROLE_NAME" &>/dev/null; then
    aws iam create-role \
        --role-name "$SCHEDULER_ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "scheduler.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' > /dev/null

    aws iam put-role-policy \
        --role-name "$SCHEDULER_ROLE_NAME" \
        --policy-name "invoke-lambda" \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": \"lambda:InvokeFunction\",
                \"Resource\": [
                    \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}\",
                    \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}:*\"
                ]
            }]
        }"
    log "  Created scheduler IAM role"
    # Brief wait for IAM propagation
    sleep 5
fi

SCHEDULER_ROLE_ARN=$(aws iam get-role --role-name "$SCHEDULER_ROLE_NAME" --query 'Role.Arn' --output text)

# Create or update schedule
if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$REGION" &>/dev/null; then
    log "  Schedule already exists — updating..."
fi

aws scheduler create-schedule \
    --name "$SCHEDULE_NAME" \
    --schedule-expression "cron(0 5 * * ? *)" \
    --schedule-expression-timezone "Asia/Bangkok" \
    --flexible-time-window '{"Mode":"FLEXIBLE","MaximumWindowInMinutes":60}' \
    --target "{
        \"Arn\": \"${LAMBDA_ALIAS_ARN}\",
        \"RoleArn\": \"${SCHEDULER_ROLE_ARN}\",
        \"RetryPolicy\": {\"MaximumRetryAttempts\": 2, \"MaximumEventAgeInSeconds\": 3600}
    }" \
    --state ENABLED \
    --region "$REGION" 2>/dev/null \
|| aws scheduler update-schedule \
    --name "$SCHEDULE_NAME" \
    --schedule-expression "cron(0 5 * * ? *)" \
    --schedule-expression-timezone "Asia/Bangkok" \
    --flexible-time-window '{"Mode":"FLEXIBLE","MaximumWindowInMinutes":60}' \
    --target "{
        \"Arn\": \"${LAMBDA_ALIAS_ARN}\",
        \"RoleArn\": \"${SCHEDULER_ROLE_ARN}\",
        \"RetryPolicy\": {\"MaximumRetryAttempts\": 2, \"MaximumEventAgeInSeconds\": 3600}
    }" \
    --state ENABLED \
    --region "$REGION"

log "  Schedule configured: daily 5 AM Bangkok"

echo ""

# ---------------------------------------------------------------------------
# Step 6: CloudWatch Alarm
# ---------------------------------------------------------------------------
log "Step 6: CloudWatch alarm (Lambda errors)..."

aws cloudwatch put-metric-alarm \
    --alarm-name "$ALARM_NAME" \
    --alarm-description "Webhook health check Lambda errors" \
    --namespace "AWS/Lambda" \
    --metric-name "Errors" \
    --dimensions "Name=FunctionName,Value=${FUNCTION_NAME}" \
    --statistic "Sum" \
    --period 86400 \
    --evaluation-periods 1 \
    --threshold 0 \
    --comparison-operator "GreaterThanThreshold" \
    --treat-missing-data "notBreaching" \
    ${SNS_ARN:+--alarm-actions "$SNS_ARN"} \
    --tags Key=Project,Value=${PROJECT} Key=Environment,Value=${ENV} Key=App,Value=shared Key=ManagedBy,Value=aws-cli \
    --region "$REGION"

log "  Alarm created: $ALARM_NAME"

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================"
echo "  Webhook Health Check — Provisioned!"
echo "============================================"
echo ""
echo "  Lambda:    ${FUNCTION_NAME}"
echo "  Alias:     ${FUNCTION_NAME}:live (v${LATEST_VERSION})"
echo "  Schedule:  ${SCHEDULE_NAME} (daily 5 AM Bangkok)"
echo "  Log group: ${LOG_GROUP}"
echo "  Alarm:     ${ALARM_NAME}"
echo ""
echo "MANUAL TEST:"
echo "  aws lambda invoke --function-name ${FUNCTION_NAME} \\"
echo "    --payload '{}' /tmp/health-result.json --region ${REGION}"
echo "  cat /tmp/health-result.json | python3 -m json.tool"
echo ""
