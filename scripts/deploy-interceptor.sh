#!/bin/bash
# Deploy/Rollback Lambda Request Interceptor
# Usage: ./scripts/deploy-interceptor.sh [dev|staging|prod] [--rollback]
#
# This script configures Lambda functions to use the request interceptor.
# It does NOT rebuild or push Docker images (use deploy-backend.sh for that).
#
# Deploy:   ./scripts/deploy-interceptor.sh dev
# Rollback: ./scripts/deploy-interceptor.sh dev --rollback

set -euo pipefail

ENV=${1:-dev}
ROLLBACK=${2:-""}
PROJECT_NAME="dr-daily-report"
AWS_REGION="ap-southeast-1"

# ─── Function registry: component -> original handler ─────────────────
declare -A ORIGINAL_HANDLERS
ORIGINAL_HANDLERS=(
    ["line-bot"]="lambda_handler.lambda_handler"
    ["telegram-api"]="telegram_lambda_handler.handler"
    ["report-worker"]="report_worker_handler.handler"
)

# ─── Validate environment ─────────────────────────────────────────────
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: $0 [dev|staging|prod] [--rollback]"
    exit 1
fi

echo "🔧 Request Interceptor — ${ENV}"
echo ""

# ─── Process each function ────────────────────────────────────────────
for COMPONENT in "${!ORIGINAL_HANDLERS[@]}"; do
    FUNCTION_NAME="${PROJECT_NAME}-${COMPONENT}-${ENV}"
    ORIG_HANDLER="${ORIGINAL_HANDLERS[$COMPONENT]}"

    echo "── ${FUNCTION_NAME}"

    # Verify function exists
    if ! aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" > /dev/null 2>&1; then
        echo "   ⏭️  SKIP (function not found)"
        echo ""
        continue
    fi

    # Get current env vars
    CURRENT_ENV=$(aws lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null || echo '{}')

    # Handle null env vars
    if [ "$CURRENT_ENV" = "null" ] || [ -z "$CURRENT_ENV" ]; then
        CURRENT_ENV='{}'
    fi

    if [[ "$ROLLBACK" == "--rollback" ]]; then
        # ── Rollback: restore original handler ──
        echo "   ↩️  Restoring original handler: ${ORIG_HANDLER}"

        UPDATED_ENV=$(echo "$CURRENT_ENV" | python3 -c "
import sys, json
env = json.load(sys.stdin)
env.pop('ORIGINAL_HANDLER', None)
env.pop('INTERCEPTOR_DISABLED', None)
print(json.dumps({'Variables': env}))
")

        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --image-config "{\"Command\":[\"${ORIG_HANDLER}\"]}" \
            --environment "$UPDATED_ENV" \
            --region "$AWS_REGION" \
            --output text > /dev/null

    else
        # ── Deploy: activate interceptor ──
        echo "   🔀 Activating interceptor (original: ${ORIG_HANDLER})"

        UPDATED_ENV=$(echo "$CURRENT_ENV" | python3 -c "
import sys, json
env = json.load(sys.stdin)
env['ORIGINAL_HANDLER'] = '${ORIG_HANDLER}'
print(json.dumps({'Variables': env}))
")

        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --image-config '{"Command":["request_interceptor.handler"]}' \
            --environment "$UPDATED_ENV" \
            --region "$AWS_REGION" \
            --output text > /dev/null
    fi

    # Wait for update to complete
    echo "   ⏳ Waiting for update..."
    aws lambda wait function-updated \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION"

    echo "   ✅ Done"
    echo ""
done

# ─── Summary ──────────────────────────────────────────────────────────
if [[ "$ROLLBACK" == "--rollback" ]]; then
    echo "↩️  Rollback complete. Original handlers restored."
else
    echo "✅ Interceptor deployed."
    echo ""
    echo "Verify with CloudWatch Insights:"
    echo "  filter @message like /USER_REQUEST/"
    echo '  | parse @message "platform=* user_id=* ticker=*" as platform, user_id, ticker'
    echo "  | sort @timestamp desc"
fi
