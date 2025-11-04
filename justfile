# Justfile for Daily Report Media Project
# Main entry point - includes modules for better organization

# Default recipe - show available commands
default:
    @just --list

# Include modules
import 'justfile-modules/webapp.just'
import 'justfile-modules/test.just'
import 'justfile-modules/deps.just'
import 'justfile-modules/db.just'
import 'justfile-modules/reports.just'
import 'justfile-modules/dev.just'
import 'justfile-modules/deploy.just'
import 'justfile-modules/api.just'
import 'justfile-modules/utils.just'
import 'justfile-modules/docs.just'
import 'justfile-modules/workflow.just'

# ============================================================================
# Help
# ============================================================================

# Show help
help:
    @echo "Daily Report Media - Common Commands"
    @echo ""
    @echo "Web Application:"
    @echo "  just webapp          - Start Flask webapp"
    @echo "  just webapp-dev      - Start Flask webapp (development mode)"
    @echo ""
    @echo "Testing:"
    @echo "  just test            - Run all tests"
    @echo "  just test-unit       - Run unit tests only"
    @echo "  just test-e2e        - Run E2E tests"
    @echo ""
    @echo "Development:"
    @echo "  just dev-start       - Start full dev environment"
    @echo "  just clean           - Clean cache files"
    @echo ""
    @echo "Report Generation:"
    @echo "  just report TICKER   - Generate report for ticker"
    @echo "  just reports-all     - Generate all reports"
    @echo ""
    @echo "See 'just --list' for all available commands"
