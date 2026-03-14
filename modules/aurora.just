# Aurora Database Operations
# Local development recipes for Aurora MySQL database access via SSM tunnel
#
# Prerequisites:
#   1. AWS CLI with valid credentials
#   2. SSM plugin installed
#   3. Access to bastion EC2 instance (i-0dab21bdf83ce9aaf)
#   4. Doppler dev_local config (AURORA_HOST=127.0.0.1, AURORA_PORT=3307)
#
# Workflow:
#   1. Start tunnel: just aurora::tunnel (keep terminal open)
#   2. Run commands: just aurora::local util report DBS19

# === TUNNEL MANAGEMENT ===

# Start SSM port forwarding to Aurora (keep terminal open)
tunnel:
    @echo "🔌 Starting SSM tunnel to Aurora..."
    @echo "   Local port: 3307"
    @echo "   Remote: dr-daily-report-aurora-dev"
    @echo ""
    @echo "⚠️  Keep this terminal open while using Aurora"
    @echo "   Press Ctrl+C to stop the tunnel"
    @echo ""
    aws ssm start-session \
      --target i-0dab21bdf83ce9aaf \
      --document-name AWS-StartPortForwardingSessionToRemoteHost \
      --parameters '{"host":["dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com"],"portNumber":["3306"],"localPortNumber":["3307"]}' \
      --region ap-southeast-1

# Check if Aurora SSM tunnel is active
check:
    #!/usr/bin/env bash
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just aurora::tunnel"
        echo ""
        exit 1
    fi
    echo "✅ Aurora tunnel is active on port 3307"

# === LOCAL DEVELOPMENT (via dr CLI) ===

# Run any dr command with local Aurora setup (requires tunnel)
#
# This is the single entry point for all Aurora operations.
# It handles environment setup (dev_local Doppler config) and routes to dr CLI.
#
# Examples:
#   just aurora::local util report DBS19 --strategy single-stage
#   just aurora::local util report-cached DBS19 --date 2025-12-15
#   just aurora::local util stats
local *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail

    # Verify tunnel is active
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just aurora::tunnel"
        echo ""
        exit 1
    fi

    # Route to dr CLI with dev_local Doppler config
    doppler run --config dev_local --project rag-chatbot-worktree -- dr {{ARGS}}

# === DATABASE OPERATIONS ===

# Run SQL query against Aurora
#
# Examples:
#   just aurora::query "SELECT * FROM ticker_master LIMIT 5"
#   just aurora::query "SELECT COUNT(*) FROM precomputed_reports"
#   just aurora::query "DESCRIBE precomputed_reports" --output vd
query QUERY *FLAGS:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check tunnel inline (don't call other recipe to avoid unstable flag issues)
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just --unstable aurora tunnel"
        echo ""
        exit 1
    fi

    # Parse output flag
    output="table"
    if echo "{{FLAGS}}" | grep -q "\--output"; then
        output=$(echo "{{FLAGS}}" | sed -n 's/.*--output[= ]\([^ ]*\).*/\1/p')
    fi

    # Execute query with selected output format
    if [ "$output" = "vd" ]; then
        echo "📊 Opening in VisiData..." >&2
        mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
            ticker_data --batch -e "{{QUERY}}" 2>/dev/null | vd -f tsv
    else
        echo "📝 Query: {{QUERY}}"
        echo ""
        mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
            ticker_data -e "{{QUERY}}"
    fi

# List available tickers in Aurora precomputed_reports
list-tickers:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check tunnel inline
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just --unstable aurora tunnel"
        echo ""
        exit 1
    fi

    echo "📋 Available tickers in Aurora precomputed_reports..."
    echo ""
    mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
        ticker_data -e "SELECT symbol, COUNT(*) as reports, MAX(report_date) as latest_report FROM precomputed_reports WHERE status='completed' GROUP BY symbol ORDER BY symbol"

# Describe table structure with column comments
describe TABLE:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check tunnel inline
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just --unstable aurora tunnel"
        echo ""
        exit 1
    fi

    echo "📋 Describing table: {{TABLE}}"
    echo ""
    mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
        ticker_data -e "
        SELECT
            COLUMN_NAME as 'Column',
            DATA_TYPE as 'Type',
            IS_NULLABLE as 'Null',
            COLUMN_KEY as 'Key',
            COLUMN_DEFAULT as 'Default',
            LEFT(COLUMN_COMMENT, 80) as 'Comment'
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'ticker_data'
          AND TABLE_NAME = '{{TABLE}}'
        ORDER BY ORDINAL_POSITION
        " 2>/dev/null | grep -v "insecure" | column -t -s $'\t'

# Count ticker_info rows created/updated on a specific date
count-ticker-info DATE="":
    #!/usr/bin/env bash
    set -euo pipefail

    # Check tunnel inline
    if ! ss -ltn | grep -q 3307; then
        echo "❌ Aurora SSM tunnel not running on port 3307"
        echo ""
        echo "Start tunnel in another terminal:"
        echo "   just --unstable aurora tunnel"
        echo ""
        exit 1
    fi

    # Default to today if no date provided
    if [ -z "{{DATE}}" ]; then
        QUERY_DATE=$(date +%Y-%m-%d)
    else
        QUERY_DATE="{{DATE}}"
    fi

    echo "📊 Counting ticker_info rows for date: $QUERY_DATE"
    echo ""
    mysql -h 127.0.0.1 -P 3307 -u admin -p'AuroraDevDb2025SecureX1' \
        ticker_data -e "
        SELECT
            '$QUERY_DATE' as query_date,
            COUNT(*) as total,
            SUM(CASE WHEN DATE(created_at) = '$QUERY_DATE' THEN 1 ELSE 0 END) as created,
            SUM(CASE WHEN DATE(updated_at) = '$QUERY_DATE' THEN 1 ELSE 0 END) as updated
        FROM ticker_info
        WHERE DATE(created_at) = '$QUERY_DATE' OR DATE(updated_at) = '$QUERY_DATE'
        " 2>/dev/null | grep -v "insecure"

# === MIGRATIONS ===

# Run Aurora database migration via Lambda
#
# Examples:
#   just aurora::migrate create_sgx_tables
#   just aurora::migrate create_data_acquisitions
#   just aurora::migrate create_sgx_filings
#   just aurora::migrate create_sgx_tables stg
migrate MIGRATION="create_sgx_tables" ENV="dev":
    #!/usr/bin/env bash
    set -euo pipefail

    FUNCTION="dr-daily-report-report-worker-{{ENV}}"
    echo "Running migration '{{MIGRATION}}' via Lambda: $FUNCTION"

    aws lambda invoke \
      --function-name "$FUNCTION" \
      --payload "{\"migration\": \"{{MIGRATION}}\"}" \
      --cli-binary-format raw-in-base64-out \
      /tmp/migration-result.json

    echo ""
    echo "Result:"
    python3 -m json.tool /tmp/migration-result.json

    # Check status from response body
    STATUS=$(python3 -c "
import json
with open('/tmp/migration-result.json') as f:
    resp = json.load(f)
body = json.loads(resp.get('body', '{}')) if isinstance(resp.get('body'), str) else resp.get('body', {})
print(body.get('status', 'unknown'))
")
    if [ "$STATUS" = "success" ]; then
        echo ""
        echo "Migration succeeded!"
    else
        echo ""
        echo "Migration status: $STATUS — check CloudWatch logs"
        exit 1
    fi

# === HELP ===

# Show Aurora commands and usage
help:
    @echo "🔧 Aurora Database Commands"
    @echo "════════════════════════════════════════════════════════════════"
    @echo ""
    @echo "Setup:"
    @echo "  just aurora::tunnel          - Start SSM tunnel (keep terminal open)"
    @echo "  just aurora::check           - Verify tunnel is active"
    @echo ""
    @echo "Report Generation (via dr CLI):"
    @echo "  just aurora::local util report DBS19"
    @echo "  just aurora::local util report DBS19 --strategy multi-stage"
    @echo "  just aurora::local util report-cached DBS19 --date 2025-12-15"
    @echo "  just aurora::local util report-cached DBS19 --strategy multi-stage"
    @echo ""
    @echo "Database Operations:"
    @echo "  just aurora::query 'SELECT * FROM ticker_master LIMIT 5'"
    @echo "  just aurora::describe ticker_info       # Show table structure with comments"
    @echo "  just aurora::query '...' --output vd    # Open in VisiData"
    @echo "  just aurora::list-tickers               # Show cached tickers"
    @echo "  just aurora::count-ticker-info 2025-12-30  # Count rows for date"
    @echo ""
    @echo "Migrations:"
    @echo "  just aurora::migrate create_sgx_tables   # Run both SGX migrations"
    @echo "  just aurora::migrate create_sgx_tables stg  # Run on staging"
    @echo ""
    @echo "Workflow:"
    @echo "  1. Start tunnel:  just aurora::tunnel (in separate terminal)"
    @echo "  2. Run commands:  just aurora::local util report DBS19"
    @echo "  3. Stop tunnel:   Ctrl+C in tunnel terminal"
    @echo ""
    @echo "Note: All 'aurora::local' commands use dev_local Doppler config"
    @echo "      (AURORA_HOST=127.0.0.1, AURORA_PORT=3307 for SSM tunnel)"
