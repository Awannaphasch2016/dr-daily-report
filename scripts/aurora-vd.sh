#!/bin/bash
# Aurora VisiData Explorer with Date Filtering
# Usage:
#   ./aurora-vd.sh [table_name] [limit] [--before DATE] [--after DATE] [--exclude-today]
#
# Examples:
#   ./aurora-vd.sh precomputed_reports 100                    # Basic usage
#   ./aurora-vd.sh daily_prices 200 --exclude-today           # Exclude today's data
#   ./aurora-vd.sh precomputed_reports 50 --before 2025-12-13 # Only before specific date
#   ./aurora-vd.sh ticker_info 100 --after 2025-12-01         # Only after specific date
#
# Requires: SSM port forward running on localhost:3307

# Default values
TABLE="precomputed_reports"
LIMIT="100"
WHERE_CLAUSE=""
DATE_COLUMN=""

# Parse arguments
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --before)
      BEFORE_DATE="$2"
      shift 2
      ;;
    --after)
      AFTER_DATE="$2"
      shift 2
      ;;
    --date)
      EXACT_DATE="$2"
      shift 2
      ;;
    --exclude-today)
      EXCLUDE_TODAY=1
      shift
      ;;
    --date-column)
      DATE_COLUMN="$2"
      shift 2
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

# Restore positional parameters
set -- "${POSITIONAL[@]}"
TABLE="${1:-$TABLE}"
LIMIT="${2:-$LIMIT}"

# Auto-detect date column if not specified
if [ -z "$DATE_COLUMN" ]; then
  # Try to detect date column from table schema
  DETECTED_COLUMN=$(mysql -h 127.0.0.1 -P 3307 -u admin -pAuroraDevDb2025SecureX1 ticker_data \
    -se "DESCRIBE $TABLE" 2>/dev/null | \
    grep -iE 'created_at|updated_at|date|timestamp' | \
    head -1 | awk '{print $1}')

  if [ -n "$DETECTED_COLUMN" ]; then
    DATE_COLUMN="$DETECTED_COLUMN"
  fi
fi

# Build WHERE clause
if [ -n "$DATE_COLUMN" ]; then
  CONDITIONS=()

  if [ -n "$EXCLUDE_TODAY" ]; then
    CONDITIONS+=("DATE($DATE_COLUMN) < CURDATE()")
  fi

  if [ -n "$BEFORE_DATE" ]; then
    CONDITIONS+=("DATE($DATE_COLUMN) < '$BEFORE_DATE'")
  fi

  if [ -n "$AFTER_DATE" ]; then
    CONDITIONS+=("DATE($DATE_COLUMN) >= '$AFTER_DATE'")
  fi

  if [ -n "$EXACT_DATE" ]; then
    CONDITIONS+=("DATE($DATE_COLUMN) = '$EXACT_DATE'")
  fi

  # Join conditions with AND
  if [ ${#CONDITIONS[@]} -gt 0 ]; then
    WHERE_CLAUSE="WHERE "
    for i in "${!CONDITIONS[@]}"; do
      if [ $i -gt 0 ]; then
        WHERE_CLAUSE+=" AND "
      fi
      WHERE_CLAUSE+="${CONDITIONS[$i]}"
    done
  fi
fi

# Build SQL query
SQL="SELECT * FROM $TABLE $WHERE_CLAUSE LIMIT $LIMIT"

# Show what we're doing
echo "📊 Fetching from table: $TABLE"
if [ -n "$DATE_COLUMN" ]; then
  echo "📅 Date column: $DATE_COLUMN"
fi
if [ -n "$WHERE_CLAUSE" ]; then
  echo "🔍 Filter: $WHERE_CLAUSE"
fi
echo "📝 Query: $SQL"
echo ""

# Execute query
mysql -h 127.0.0.1 -P 3307 -u admin -pAuroraDevDb2025SecureX1 ticker_data \
  -e "$SQL" 2>/dev/null > /tmp/aurora_${TABLE}.tsv

if [ $? -eq 0 ]; then
  ROW_COUNT=$(wc -l < /tmp/aurora_${TABLE}.tsv)
  ACTUAL_ROWS=$((ROW_COUNT - 1))  # Subtract header row

  echo "✅ Exported $ACTUAL_ROWS rows to /tmp/aurora_${TABLE}.tsv"

  if [ $ACTUAL_ROWS -eq 0 ]; then
    echo "⚠️  No data matched the filter criteria"
    echo "💡 Try: mysql -h 127.0.0.1 -P 3307 -u admin -p ticker_data -e 'SELECT COUNT(*) FROM $TABLE $WHERE_CLAUSE'"
  else
    echo "📂 Opening in VisiData..."
    vd /tmp/aurora_${TABLE}.tsv
  fi
else
  echo "❌ Export failed. Is SSM port forward running?"
  echo "   Start with: aws ssm start-session --target i-0dab21bdf83ce9aaf \\"
  echo "     --document-name AWS-StartPortForwardingSessionToRemoteHost \\"
  echo "     --parameters '{\"host\":[\"dr-daily-report-aurora-dev.cluster-c9a0288e4hqm.ap-southeast-1.rds.amazonaws.com\"],\"portNumber\":[\"3306\"],\"localPortNumber\":[\"3307\"]}' \\"
  echo "     --region ap-southeast-1"
fi
