#!/bin/bash
#
# Lambda Rollback Script
# ======================
# Quickly rollback Lambda functions to a previous version by updating aliases.
#
# Usage:
#   ./scripts/rollback.sh <env>                    # Interactive mode (list versions, prompt for selection)
#   ./scripts/rollback.sh <env> <version>          # Rollback both Lambdas to specific version
#   ./scripts/rollback.sh <env> telegram <version> # Rollback only Telegram API Lambda
#   ./scripts/rollback.sh <env> worker <version>   # Rollback only Report Worker Lambda
#
# Examples:
#   ./scripts/rollback.sh dev                # Interactive mode for dev
#   ./scripts/rollback.sh dev 5              # Rollback both dev Lambdas to version 5
#   ./scripts/rollback.sh staging telegram 3 # Rollback staging Telegram API to version 3
#   ./scripts/rollback.sh prod worker 4      # Rollback prod Worker to version 4
#
# Environments: dev, staging, prod

set -e

# Validate environment argument
ENV="${1:-}"
if [[ ! "$ENV" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Error: First argument must be environment (dev, staging, prod)"
    echo ""
    echo "Usage: $0 <env> [version|telegram|worker] [version]"
    echo "Examples:"
    echo "  $0 dev              # Interactive mode for dev"
    echo "  $0 dev 5            # Rollback both dev Lambdas to version 5"
    echo "  $0 staging telegram 3  # Rollback staging Telegram API to version 3"
    exit 1
fi
shift  # Remove env from arguments

# Configuration based on environment
TELEGRAM_FUNCTION="dr-daily-report-telegram-api-${ENV}"
WORKER_FUNCTION="dr-daily-report-report-worker-${ENV}"
ALIAS_NAME="live"
REGION="${AWS_REGION:-ap-southeast-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get current alias version
get_current_version() {
    local function_name=$1
    aws lambda get-alias \
        --function-name "$function_name" \
        --name "$ALIAS_NAME" \
        --region "$REGION" \
        --query 'FunctionVersion' \
        --output text 2>/dev/null || echo "unknown"
}

# List available versions
list_versions() {
    local function_name=$1
    echo ""
    echo_info "Available versions for $function_name:"
    aws lambda list-versions-by-function \
        --function-name "$function_name" \
        --region "$REGION" \
        --query 'Versions[*].[Version,Description,LastModified]' \
        --output table 2>/dev/null | head -20
}

# Rollback function to specific version
rollback_function() {
    local function_name=$1
    local target_version=$2

    echo_info "Rolling back $function_name to version $target_version..."

    # Update alias
    aws lambda update-alias \
        --function-name "$function_name" \
        --name "$ALIAS_NAME" \
        --function-version "$target_version" \
        --region "$REGION" \
        --output text > /dev/null

    echo_success "$function_name alias '$ALIAS_NAME' now points to version $target_version"
}

# Main logic
main() {
    echo ""
    echo "🔄 Lambda Rollback Script"
    echo "========================="
    echo "Environment: ${ENV}"
    echo ""

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        echo_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    # Get current versions
    CURRENT_TELEGRAM=$(get_current_version "$TELEGRAM_FUNCTION")
    CURRENT_WORKER=$(get_current_version "$WORKER_FUNCTION")

    echo_info "Current versions:"
    echo "   Telegram API: $CURRENT_TELEGRAM"
    echo "   Report Worker: $CURRENT_WORKER"

    # Parse arguments
    case "${1:-}" in
        "telegram")
            if [ -z "${2:-}" ]; then
                list_versions "$TELEGRAM_FUNCTION"
                echo ""
                read -p "Enter version to rollback to: " VERSION
            else
                VERSION="$2"
            fi
            rollback_function "$TELEGRAM_FUNCTION" "$VERSION"
            ;;

        "worker")
            if [ -z "${2:-}" ]; then
                list_versions "$WORKER_FUNCTION"
                echo ""
                read -p "Enter version to rollback to: " VERSION
            else
                VERSION="$2"
            fi
            rollback_function "$WORKER_FUNCTION" "$VERSION"
            ;;

        "")
            # Interactive mode
            echo ""
            list_versions "$TELEGRAM_FUNCTION"
            list_versions "$WORKER_FUNCTION"
            echo ""
            read -p "Enter version to rollback BOTH functions to (or 'q' to quit): " VERSION

            if [ "$VERSION" = "q" ]; then
                echo "Cancelled."
                exit 0
            fi

            echo ""
            echo_warning "This will rollback BOTH functions to version $VERSION"
            read -p "Are you sure? (y/N): " CONFIRM

            if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
                echo "Cancelled."
                exit 0
            fi

            rollback_function "$TELEGRAM_FUNCTION" "$VERSION"
            rollback_function "$WORKER_FUNCTION" "$VERSION"
            ;;

        *)
            # Version number provided directly
            VERSION="$1"
            echo ""
            echo_warning "This will rollback BOTH functions to version $VERSION"
            read -p "Are you sure? (y/N): " CONFIRM

            if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
                echo "Cancelled."
                exit 0
            fi

            rollback_function "$TELEGRAM_FUNCTION" "$VERSION"
            rollback_function "$WORKER_FUNCTION" "$VERSION"
            ;;
    esac

    echo ""
    echo_success "Rollback complete!"
    echo ""

    # Show new state
    NEW_TELEGRAM=$(get_current_version "$TELEGRAM_FUNCTION")
    NEW_WORKER=$(get_current_version "$WORKER_FUNCTION")

    echo_info "New versions:"
    echo "   Telegram API: $NEW_TELEGRAM"
    echo "   Report Worker: $NEW_WORKER"
}

main "$@"
