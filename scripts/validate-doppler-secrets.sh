#!/usr/bin/env bash
#
# Pre-deployment validation script for Doppler secrets
#
# Purpose: Validates that all required Doppler secrets exist and are non-empty
#          before running Terraform apply. Prevents deployment failures caused
#          by missing environment variables.
#
# Usage:
#   ./scripts/validate-doppler-secrets.sh <environment>
#
# Example:
#   ./scripts/validate-doppler-secrets.sh dev
#   ./scripts/validate-doppler-secrets.sh stg
#   ./scripts/validate-doppler-secrets.sh prd
#
# Exit codes:
#   0 - All required secrets present and valid
#   1 - Missing or empty secrets detected
#   2 - Invalid arguments or configuration
#
# Related:
#   - Bug Hunt Report: .claude/bug-hunts/2026-01-09-linebot-no-response.md
#   - Principle #15: Infrastructure-Application Contract
#   - Principle #13: Secret Management Discipline

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

#######################################
# Print colored message
# Arguments:
#   $1 - Color code
#   $2 - Message
#######################################
print_msg() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

#######################################
# Print error message
#######################################
error() {
    print_msg "$RED" "❌ ERROR: $*" >&2
}

#######################################
# Print success message
#######################################
success() {
    print_msg "$GREEN" "✅ $*"
}

#######################################
# Print info message
#######################################
info() {
    print_msg "$BLUE" "ℹ️  $*"
}

#######################################
# Print warning message
#######################################
warn() {
    print_msg "$YELLOW" "⚠️  WARNING: $*"
}

#######################################
# Print usage information
#######################################
usage() {
    cat <<EOF
Usage: $0 <environment>

Validates that all required Doppler secrets exist and are non-empty
before running Terraform apply.

Arguments:
  environment    Target environment (dev, stg, or prd)

Examples:
  $0 dev
  $0 stg
  $0 prd

Exit codes:
  0 - All required secrets present and valid
  1 - Missing or empty secrets detected
  2 - Invalid arguments or configuration

Environment:
  DOPPLER_TOKEN  Optional: Doppler service token for CI/CD
EOF
}

#######################################
# Define required secrets for each environment
# These are the TF_VAR_* secrets that Terraform expects
#######################################
declare -A REQUIRED_SECRETS=(
    # Core secrets required for all environments
    ["OPENROUTER_API_KEY"]="OpenRouter API key for LLM access"
    ["AURORA_MASTER_PASSWORD"]="Aurora MySQL master password"

    # LINE Bot secrets (required for LINE bot Lambda)
    ["LINE_CHANNEL_ACCESS_TOKEN"]="LINE Bot channel access token"
    ["LINE_CHANNEL_SECRET"]="LINE Bot channel secret"

    # Langfuse observability (optional but recommended)
    ["LANGFUSE_PUBLIC_KEY"]="Langfuse public key for observability"
    ["LANGFUSE_SECRET_KEY"]="Langfuse secret key for observability"
    ["LANGFUSE_HOST"]="Langfuse host URL"
)

# Terraform-specific secrets (TF_VAR_ prefixed versions)
declare -A TERRAFORM_SECRETS=(
    ["TF_VAR_OPENROUTER_API_KEY"]="Terraform variable for OpenRouter API key"
    ["TF_VAR_AURORA_MASTER_PASSWORD"]="Terraform variable for Aurora password"
    ["TF_VAR_LINE_CHANNEL_ACCESS_TOKEN"]="Terraform variable for LINE access token"
    ["TF_VAR_LINE_CHANNEL_SECRET"]="Terraform variable for LINE secret"
)

# Optional secrets (warn if missing but don't fail)
declare -A OPTIONAL_SECRETS=(
    ["LANGFUSE_PUBLIC_KEY"]="Langfuse observability (optional)"
    ["LANGFUSE_SECRET_KEY"]="Langfuse observability (optional)"
    ["LANGFUSE_HOST"]="Langfuse observability (optional)"
)

#######################################
# Check if Doppler CLI is installed
#######################################
check_doppler_cli() {
    if ! command -v doppler &> /dev/null; then
        error "Doppler CLI is not installed"
        info "Install with: brew install dopplerhq/cli/doppler (macOS) or curl -Ls https://cli.doppler.com/install.sh | sh (Linux)"
        return 1
    fi
    return 0
}

#######################################
# Check if secret exists in Doppler config
# Arguments:
#   $1 - Secret name
#   $2 - Config name (e.g., dev, stg, prd)
# Returns:
#   0 if secret exists and is non-empty
#   1 if secret missing or empty
#######################################
check_secret() {
    local secret_name=$1
    local config=$2

    # Try to get secret value
    local secret_value
    if ! secret_value=$(doppler secrets get "$secret_name" --config "$config" --plain 2>/dev/null); then
        return 1
    fi

    # Check if value is empty
    if [[ -z "$secret_value" ]]; then
        return 1
    fi

    return 0
}

#######################################
# Validate all required secrets for an environment
# Arguments:
#   $1 - Environment (dev, stg, prd)
# Returns:
#   0 if all required secrets present
#   1 if any required secrets missing
#######################################
validate_secrets() {
    local env=$1
    local config=$env
    local has_errors=0
    local missing_secrets=()
    local empty_secrets=()
    local missing_optional=()

    info "Validating Doppler secrets for environment: $env"
    info "Doppler config: $config"
    echo ""

    # Check if config exists
    if ! doppler configs get "$config" &>/dev/null; then
        error "Doppler config '$config' not found"
        info "Available configs:"
        doppler configs list --json 2>/dev/null | jq -r '.[].name' | sed 's/^/  - /'
        return 2
    fi

    # Validate required secrets (base versions)
    info "Checking required secrets..."
    for secret_name in "${!REQUIRED_SECRETS[@]}"; do
        local description="${REQUIRED_SECRETS[$secret_name]}"

        # Skip if this is an optional secret
        if [[ -v "OPTIONAL_SECRETS[$secret_name]" ]]; then
            continue
        fi

        if check_secret "$secret_name" "$config"; then
            success "$secret_name - Present"
        else
            error "$secret_name - MISSING or EMPTY"
            error "  Description: $description"
            missing_secrets+=("$secret_name")
            has_errors=1
        fi
    done

    echo ""

    # Validate Terraform-specific secrets (TF_VAR_ versions)
    info "Checking Terraform-specific secrets (TF_VAR_*)..."
    for secret_name in "${!TERRAFORM_SECRETS[@]}"; do
        local description="${TERRAFORM_SECRETS[$secret_name]}"

        if check_secret "$secret_name" "$config"; then
            success "$secret_name - Present"
        else
            error "$secret_name - MISSING or EMPTY"
            error "  Description: $description"
            missing_secrets+=("$secret_name")
            has_errors=1
        fi
    done

    echo ""

    # Check optional secrets (warn only, don't fail)
    info "Checking optional secrets..."
    for secret_name in "${!OPTIONAL_SECRETS[@]}"; do
        local description="${OPTIONAL_SECRETS[$secret_name]}"

        if check_secret "$secret_name" "$config"; then
            success "$secret_name - Present"
        else
            warn "$secret_name - Missing (optional)"
            warn "  Description: $description"
            missing_optional+=("$secret_name")
        fi
    done

    echo ""
    echo "================================================================"

    # Print summary
    if [[ $has_errors -eq 0 ]]; then
        success "All required secrets present and valid!"

        if [[ ${#missing_optional[@]} -gt 0 ]]; then
            echo ""
            warn "Optional secrets missing: ${missing_optional[*]}"
            info "These are optional but recommended for full functionality"
        fi

        echo ""
        info "Safe to proceed with Terraform apply"
        return 0
    else
        error "Validation failed: ${#missing_secrets[@]} required secret(s) missing"
        echo ""
        error "Missing or empty secrets:"
        for secret in "${missing_secrets[@]}"; do
            error "  - $secret"
        done

        echo ""
        error "Cannot proceed with Terraform apply"
        info "Add missing secrets with: doppler secrets set <SECRET_NAME>='<value>' --config $config"

        echo ""
        info "Or copy from another environment:"
        info "  TOKEN=\$(doppler secrets get <SECRET_NAME> --config stg --plain)"
        info "  doppler secrets set <SECRET_NAME>=\"\$TOKEN\" --config $config"

        return 1
    fi
}

#######################################
# Main function
#######################################
main() {
    # Check arguments
    if [[ $# -ne 1 ]]; then
        error "Invalid number of arguments"
        echo ""
        usage
        return 2
    fi

    local environment=$1

    # Validate environment argument
    case "$environment" in
        dev|stg|prd)
            ;;
        *)
            error "Invalid environment: $environment"
            info "Valid environments: dev, stg, prd"
            echo ""
            usage
            return 2
            ;;
    esac

    # Check prerequisites
    if ! check_doppler_cli; then
        return 2
    fi

    # Validate secrets
    if validate_secrets "$environment"; then
        return 0
    else
        return 1
    fi
}

# Run main function
main "$@"
