#!/usr/bin/env bash
# ===========================================================================
# Build, push, and run MOPS ingestion as ECS Fargate task
#
# Usage:
#   ./scripts/ecs/run-mops-ingestion.sh --dry-run --years-back 1
#   ./scripts/ecs/run-mops-ingestion.sh --skip-doc-download --years-back 3
#   ./scripts/ecs/run-mops-ingestion.sh --doc-only
#   ./scripts/ecs/run-mops-ingestion.sh --build   # build+push only, don't run
#
# All arguments after script flags are passed to the ingestion script.
# ===========================================================================

set -euo pipefail

ENV="${ECS_ENV:-dev}"
REGION="ap-southeast-1"
ACCOUNT_ID="755283537543"
PROJECT="dr-daily-report"

ECR_REPO="${PROJECT}-ingestion-${ENV}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"
ECS_CLUSTER="${PROJECT}-ingestion-${ENV}"
TASK_DEF="mops-ingestion-${ENV}"

# Security group per environment
declare -A SG_MAP=(
    [dev]="sg-0185a0d8d92968d03"
    [staging]="sg-0b417197a133a2e32"
    [prod]="sg-06af9bdfe48e9f9d0"
)
SECURITY_GROUP="${SG_MAP[$ENV]}"
SUBNETS="subnet-0bfaf6ef0e1a456a6,subnet-0ef493a1aae3b4af4"

# Parse script-level flags
BUILD_ONLY=false
SCRIPT_ARGS=()
for arg in "$@"; do
    case "$arg" in
        --build) BUILD_ONLY=true ;;
        *) SCRIPT_ARGS+=("$arg") ;;
    esac
done

# -------------------------------------------------------------------
# Build and push Docker image
# -------------------------------------------------------------------
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
TIMESTAMP=$(date +%Y%m%d%H%M%S)
IMAGE_TAG="sha-${COMMIT_SHA}-${TIMESTAMP}"

echo "Building image: ${ECR_REPO}:${IMAGE_TAG}"
docker build -f Dockerfile.ingestion -t "${ECR_REPO}:${IMAGE_TAG}" .

echo "Pushing to ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"
echo "Pushed: ${ECR_URI}:${IMAGE_TAG}"

if [ "$BUILD_ONLY" = true ]; then
    echo "Build complete (--build flag, not running task)"
    exit 0
fi

# -------------------------------------------------------------------
# Run Fargate task
# -------------------------------------------------------------------

# Build command array for container override
CMD_JSON="[\"scripts.ingest_mops_filings\""
for arg in "${SCRIPT_ARGS[@]}"; do
    CMD_JSON+=",\"${arg}\""
done
CMD_JSON+="]"

echo ""
echo "Running Fargate task..."
echo "  Cluster: ${ECS_CLUSTER}"
echo "  Task:    ${TASK_DEF}"
echo "  Image:   ${ECR_URI}:${IMAGE_TAG}"
echo "  Command: python -m ${SCRIPT_ARGS[*]:-scripts.ingest_mops_filings}"

TASK_ARN=$(aws ecs run-task \
    --cluster "$ECS_CLUSTER" \
    --task-definition "$TASK_DEF" \
    --launch-type FARGATE \
    --region "$REGION" \
    --network-configuration "{
        \"awsvpcConfiguration\": {
            \"subnets\": [\"${SUBNETS//,/\",\"}\"],
            \"securityGroups\": [\"${SECURITY_GROUP}\"],
            \"assignPublicIp\": \"DISABLED\"
        }
    }" \
    --overrides "{
        \"containerOverrides\": [{
            \"name\": \"ingestion\",
            \"command\": ${CMD_JSON}
        }]
    }" \
    --query 'tasks[0].taskArn' --output text)

echo ""
echo "Task started: ${TASK_ARN}"
TASK_ID=$(echo "$TASK_ARN" | grep -oP '[^/]+$')

echo ""
echo "Monitor with:"
echo "  aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks ${TASK_ID} --region ${REGION} --query 'tasks[0].lastStatus'"
echo ""
echo "View logs:"
echo "  aws logs tail ${LOG_GROUP:-/ecs/${PROJECT}-ingestion-${ENV}} --region ${REGION} --follow"
