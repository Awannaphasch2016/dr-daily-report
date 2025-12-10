#!/bin/bash
# Validate MCP configuration for Cursor
# This script checks that all MCP servers are properly configured

set -e

PROJECT_ROOT="/home/anak/dev/dr-daily-report_telegram"
MCP_CONFIG="${PROJECT_ROOT}/.cursor/mcp.json"

echo "🔍 Validating MCP Configuration for Cursor"
echo "=========================================="
echo ""

# Check 1: JSON syntax validation
echo "[1/7] Validating JSON syntax..."
if python3 -m json.tool "$MCP_CONFIG" > /dev/null 2>&1; then
    echo "✅ JSON syntax is valid"
else
    echo "❌ JSON syntax is invalid"
    exit 1
fi

# Check 2: File exists
echo "[2/7] Checking configuration file exists..."
if [ -f "$MCP_CONFIG" ]; then
    echo "✅ Configuration file exists: $MCP_CONFIG"
else
    echo "❌ Configuration file missing: $MCP_CONFIG"
    exit 1
fi

# Check 3: Parse servers from JSON
echo "[3/7] Extracting MCP server configurations..."
SERVERS=$(python3 <<EOF
import json
with open("$MCP_CONFIG") as f:
    config = json.load(f)
    servers = list(config.get("mcpServers", {}).keys())
    print(" ".join(servers))
EOF
)

if [ -z "$SERVERS" ]; then
    echo "❌ No MCP servers found in configuration"
    exit 1
fi

echo "✅ Found MCP servers: $SERVERS"

# Check 4: Validate each server's wrapper script
echo "[4/7] Validating wrapper scripts..."
for server in $SERVERS; do
    # Extract command path from JSON
    COMMAND=$(python3 <<EOF
import json
with open("$MCP_CONFIG") as f:
    config = json.load(f)
    server_config = config.get("mcpServers", {}).get("$server", {})
    print(server_config.get("command", ""))
EOF
)
    
    if [ -z "$COMMAND" ]; then
        echo "❌ Server '$server': No command specified"
        exit 1
    fi
    
    if [ ! -f "$COMMAND" ]; then
        echo "❌ Server '$server': Wrapper script not found: $COMMAND"
        exit 1
    fi
    
    if [ ! -x "$COMMAND" ]; then
        echo "❌ Server '$server': Wrapper script not executable: $COMMAND"
        exit 1
    fi
    
    echo "✅ Server '$server': Wrapper script OK: $COMMAND"
done

# Check 5: Validate dependencies
echo "[5/7] Checking dependencies..."

# Check doppler (required by AWS wrapper)
if command -v doppler > /dev/null 2>&1; then
    echo "✅ Doppler CLI is installed: $(doppler --version 2>&1 | head -n1)"
else
    echo "⚠️  Doppler CLI not found (required for AWS MCP server)"
fi

# Check uvx (required by AWS wrapper)
if command -v uvx > /dev/null 2>&1; then
    echo "✅ uvx is installed: $(uvx --version 2>&1 | head -n1)"
else
    echo "⚠️  uvx not found (required for AWS MCP server)"
fi

# Check npx (required by GitHub wrapper)
if command -v npx > /dev/null 2>&1; then
    echo "✅ npx is installed: $(npx --version 2>&1 | head -n1)"
else
    echo "⚠️  npx not found (required for GitHub MCP server)"
fi

# Check 6: Validate environment variables
echo "[6/7] Checking environment variable configuration..."
AWS_ENV=$(python3 <<EOF
import json
with open("$MCP_CONFIG") as f:
    config = json.load(f)
    aws_config = config.get("mcpServers", {}).get("aws", {})
    env = aws_config.get("env", {})
    print(f"FASTMCP_LOG_LEVEL={env.get('FASTMCP_LOG_LEVEL', 'NOT_SET')}")
    print(f"AWS_REGION={env.get('AWS_REGION', 'NOT_SET')}")
EOF
)

if echo "$AWS_ENV" | grep -q "NOT_SET"; then
    echo "⚠️  Some AWS environment variables not set in config"
else
    echo "✅ AWS environment variables configured:"
    echo "$AWS_ENV" | sed 's/^/   /'
fi

# Check 7: Validate paths are absolute
echo "[7/7] Validating command paths are absolute..."
for server in $SERVERS; do
    COMMAND=$(python3 <<EOF
import json
with open("$MCP_CONFIG") as f:
    config = json.load(f)
    server_config = config.get("mcpServers", {}).get("$server", {})
    print(server_config.get("command", ""))
EOF
)
    
    if [[ "$COMMAND" == /* ]]; then
        echo "✅ Server '$server': Path is absolute: $COMMAND"
    else
        echo "⚠️  Server '$server': Path is relative (may cause issues): $COMMAND"
    fi
done

echo ""
echo "=========================================="
echo "✅ MCP Configuration Validation Complete"
echo ""
echo "📋 Summary:"
echo "   Configuration file: $MCP_CONFIG"
echo "   MCP Servers: $SERVERS"
echo ""
echo "💡 Next Steps:"
echo "   1. Restart Cursor to load the new MCP configuration"
echo "   2. Check Cursor's MCP status in Settings → Features → Model Context Protocol"
echo "   3. Verify servers are connected (green status indicators)"
echo ""
