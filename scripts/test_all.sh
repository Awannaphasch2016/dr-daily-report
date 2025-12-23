#!/bin/bash
# Master Test Script - 7-Layer Testing Strategy
#
# Purpose: Run all test layers in correct order to catch errors early
# Runtime: ~2-5 minutes (depending on which layers are run)
#
# Test Layers (in order):
#   1. Unit Tests (Python + pytest)           - ~15 seconds
#   2. Docker Import Tests                    - ~30 seconds
#   3. Docker Local Execution                 - ~60 seconds
#   4. Contract Tests (Step Functions)        - ~10 seconds
#   5. Terraform Validation                   - ~30 seconds
#   6. Integration Tests (optional)           - ~60 seconds
#   7. OPA Policy Tests (optional)            - ~10 seconds
#
# Usage:
#   ./scripts/test_all.sh                     # Quick tests (layers 1-5)
#   ./scripts/test_all.sh --full              # All tests including integration
#   ./scripts/test_all.sh --layer=3           # Run only up to layer 3
#   ./scripts/test_all.sh --skip-docker       # Skip Docker tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MAX_LAYER=5  # Default: quick tests (no integration)
SKIP_DOCKER=false
VERBOSE=false
START_TIME=$(date +%s)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            MAX_LAYER=7
            shift
            ;;
        --layer=*)
            MAX_LAYER="${1#*=}"
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--full] [--layer=N] [--skip-docker] [--verbose]"
            exit 1
            ;;
    esac
done

# Print banner
echo "======================================================"
echo "Master Test Script - 7-Layer Testing"
echo "======================================================"
echo ""
echo "Running layers 1-${MAX_LAYER}"
if [ "$SKIP_DOCKER" = true ]; then
    echo "Docker tests: SKIPPED"
fi
echo ""

# Track failures
FAILED_LAYERS=()

# Helper function to run a test layer
run_layer() {
    local layer_num=$1
    local layer_name=$2
    local command=$3

    if [ "$layer_num" -gt "$MAX_LAYER" ]; then
        return 0  # Skip this layer
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Layer $layer_num: $layer_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    layer_start=$(date +%s)

    if eval "$command"; then
        layer_end=$(date +%s)
        layer_duration=$((layer_end - layer_start))
        echo ""
        echo -e "${GREEN}✅ Layer $layer_num passed${NC} (${layer_duration}s)"
        echo ""
    else
        echo ""
        echo -e "${RED}❌ Layer $layer_num failed${NC}"
        echo ""
        FAILED_LAYERS+=("Layer $layer_num: $layer_name")
        return 1
    fi
}

# Layer 1: Unit Tests
run_layer 1 "Unit Tests (pytest)" \
    "pytest tests/scheduler/test_get_ticker_list_handler.py tests/scheduler/test_ticker_fetcher_handler.py -v --tb=short" || true

# Layer 2: Docker Import Tests
if [ "$SKIP_DOCKER" = false ]; then
    run_layer 2 "Docker Import Tests" \
        "./scripts/test_docker_imports.sh" || true
else
    echo -e "${YELLOW}⏭️  Layer 2: Docker Import Tests (SKIPPED)${NC}"
    echo ""
fi

# Layer 3: Docker Local Execution
if [ "$SKIP_DOCKER" = false ]; then
    run_layer 3 "Docker Local Execution" \
        "./scripts/test_docker_local.sh" || true
else
    echo -e "${YELLOW}⏭️  Layer 3: Docker Local Execution (SKIPPED)${NC}"
    echo ""
fi

# Layer 4: Contract Tests
run_layer 4 "Step Functions Contract Tests" \
    "./scripts/test_contracts.sh" || true

# Layer 5: Terraform Validation
run_layer 5 "Terraform Validation" \
    "cd terraform && terraform fmt -check -recursive && terraform validate" || true

# Layer 6: Integration Tests (optional)
if [ "$MAX_LAYER" -ge 6 ]; then
    run_layer 6 "Integration Tests (AWS)" \
        "pytest tests/integration/test_precompute_trigger_integration.py -v -m integration --tb=short" || true
fi

# Layer 7: OPA Policy Tests (optional, if OPA policies exist)
if [ "$MAX_LAYER" -ge 7 ] && [ -d "terraform/policies" ]; then
    run_layer 7 "OPA Policy Tests" \
        "opa test terraform/policies/ -v" || true
elif [ "$MAX_LAYER" -ge 7 ]; then
    echo -e "${YELLOW}⏭️  Layer 7: OPA Policy Tests (No policies found, skipped)${NC}"
    echo ""
fi

# Calculate total duration
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

# Print summary
echo "======================================================"
echo "Summary"
echo "======================================================"
echo ""

if [ ${#FAILED_LAYERS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All test layers passed!${NC}"
    echo ""
    echo "Total duration: ${TOTAL_DURATION}s"
    echo ""

    if [ "$MAX_LAYER" -lt 6 ]; then
        echo "Quick tests completed. For full validation:"
        echo "  ./scripts/test_all.sh --full"
    fi

    echo ""
    echo "Next steps:"
    echo "  1. Commit changes: git commit -am 'feat: Add comprehensive testing suite'"
    echo "  2. Deploy to dev: just deploy-dev"
    echo "  3. Run smoke tests: just test-precompute-workflow"

    exit 0
else
    echo -e "${RED}❌ ${#FAILED_LAYERS[@]} test layer(s) failed:${NC}"
    echo ""
    for layer in "${FAILED_LAYERS[@]}"; do
        echo "  - $layer"
    done
    echo ""
    echo "Fix these issues before deploying to AWS."
    echo ""
    echo "Debugging tips:"
    echo "  - Run individual layer: ./scripts/test_<layer>.sh --verbose"
    echo "  - Check logs: pytest -v --tb=long"
    echo "  - Verify environment variables are set"

    exit 1
fi
