# Test script for AWS MCP server handshake
# This script tests the MCP protocol initialization handshake

Write-Host "🧪 Testing AWS MCP Server Handshake..." -ForegroundColor Cyan
Write-Host ""

# Add uv to PATH
$env:Path = "C:\Users\yt900138\.local\bin;$env:Path"

# Set AWS region
$env:AWS_REGION = "ap-southeast-1"
$env:FASTMCP_LOG_LEVEL = "ERROR"

# Check if uv is available
try {
    $uvVersion = uv --version 2>$null
    Write-Host "✅ uv is installed: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ uv is not installed. Run: just setup-mcp" -ForegroundColor Red
    exit 1
}

# Check AWS credentials
try {
    $awsIdentity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    Write-Host "✅ AWS credentials configured" -ForegroundColor Green
    Write-Host "   Account: $($awsIdentity.Account)" -ForegroundColor Gray
    Write-Host "   User ARN: $($awsIdentity.Arn)" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  AWS credentials not found. MCP server may still work for some operations." -ForegroundColor Yellow
    Write-Host "   Configure with: aws configure" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📡 Starting MCP server test..." -ForegroundColor Cyan

# Create a test script that sends MCP initialize request
$testScript = @'
import json
import sys
import subprocess
import time

# MCP Initialize request (JSON-RPC 2.0)
initialize_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "clientInfo": {
            "name": "mcp-handshake-test",
            "version": "1.0.0"
        }
    }
}

# Start MCP server process
print("Starting AWS MCP server...")
process = subprocess.Popen(
    ["uvx", "awslabs.core-mcp-server@latest"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

try:
    # Send initialize request
    print("Sending initialize request...")
    request_json = json.dumps(initialize_request) + "\n"
    process.stdin.write(request_json)
    process.stdin.flush()
    
    # Wait for response (with timeout)
    print("Waiting for response...")
    process.stdin.close()
    
    # Read response
    stdout, stderr = process.communicate(timeout=30)
    
    if stdout:
        print("\n✅ Server Response:")
        print(stdout)
        
        # Try to parse response
        try:
            for line in stdout.strip().split('\n'):
                if line.strip():
                    response = json.loads(line)
                    if response.get("result"):
                        print("\n✅ Handshake successful!")
                        print(f"   Protocol Version: {response.get('result', {}).get('protocolVersion', 'N/A')}")
                        print(f"   Server Info: {response.get('result', {}).get('serverInfo', {}).get('name', 'N/A')}")
                        if 'tools' in response.get('result', {}).get('capabilities', {}):
                            tools = response.get('result', {}).get('capabilities', {}).get('tools', {}).get('listChanged', False)
                            print(f"   Tools Available: {tools}")
                        sys.exit(0)
        except json.JSONDecodeError as e:
            print(f"\n⚠️  Could not parse response as JSON: {e}")
            print("   Raw output:", stdout)
    
    if stderr:
        print("\n⚠️  Server stderr:")
        print(stderr)
        
except subprocess.TimeoutExpired:
    print("\n❌ Timeout waiting for server response")
    process.kill()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    process.kill()
    sys.exit(1)
finally:
    process.terminate()
'@

# Write test script to temp file
$testScriptPath = "$env:TEMP\test_mcp_handshake.py"
$testScript | Out-File -FilePath $testScriptPath -Encoding utf8

Write-Host "Running handshake test..." -ForegroundColor Yellow
Write-Host ""

# Run the test
try {
    python $testScriptPath
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "✅ MCP Handshake Test PASSED!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📋 Next steps:" -ForegroundColor Cyan
        Write-Host "   1. Restart Cursor IDE" -ForegroundColor White
        Write-Host "   2. Ask Cursor: 'What AWS MCP tools are available?'" -ForegroundColor White
        Write-Host "   3. Test: 'List all Lambda functions in ap-southeast-1'" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "❌ MCP Handshake Test FAILED (exit code: $exitCode)" -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Troubleshooting:" -ForegroundColor Yellow
        Write-Host "   - Check network connection (MCP server downloads dependencies)" -ForegroundColor Gray
        Write-Host "   - Try: uvx awslabs.core-mcp-server@latest manually" -ForegroundColor Gray
        Write-Host "   - Increase timeout: `$env:UV_HTTP_TIMEOUT='60'" -ForegroundColor Gray
    }
} catch {
    Write-Host ""
    Write-Host "❌ Error running test: $_" -ForegroundColor Red
}

# Cleanup
Remove-Item $testScriptPath -ErrorAction SilentlyContinue

