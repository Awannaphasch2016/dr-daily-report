# PowerShell setup script for AWS MCP in Cursor IDE

Write-Host "🔧 Setting up AWS MCP for Cursor IDE..." -ForegroundColor Cyan

# Check if uv is installed
try {
    $uvVersion = uv --version 2>$null
    Write-Host "✅ uv is installed: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ uv is not installed" -ForegroundColor Red
    Write-Host "📦 Installing uv..." -ForegroundColor Yellow
    
    # Check execution policy
    $executionPolicy = Get-ExecutionPolicy -Scope CurrentUser
    if ($executionPolicy -eq "Restricted") {
        Write-Host "⚠️  PowerShell execution policy is Restricted" -ForegroundColor Yellow
        Write-Host "   Setting execution policy to RemoteSigned..." -ForegroundColor Yellow
        Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    }
    
    # Install uv
    irm https://astral.sh/uv/install.ps1 | iex
    
    # Add to PATH
    $env:Path += ";$env:USERPROFILE\.cargo\bin"
    
    Write-Host "✅ uv installed. Please restart your terminal or run: refreshenv" -ForegroundColor Green
}

# Check if Python is installed
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Python is installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed" -ForegroundColor Red
    Write-Host "📦 Installing Python 3.13 via uv..." -ForegroundColor Yellow
    uv python install 3.13
}

# Create .cursor directory if it doesn't exist
if (-not (Test-Path ".cursor")) {
    New-Item -ItemType Directory -Path ".cursor" | Out-Null
    Write-Host "✅ Created .cursor directory" -ForegroundColor Green
}

# Create mcp.json if it doesn't exist
if (-not (Test-Path ".cursor\mcp.json")) {
    if (Test-Path ".cursor\mcp.json.template") {
        Copy-Item ".cursor\mcp.json.template" ".cursor\mcp.json"
        Write-Host "✅ Created .cursor\mcp.json from template" -ForegroundColor Green
    } else {
        Write-Host "📝 Creating .cursor\mcp.json..." -ForegroundColor Yellow
        $mcpConfig = @{
            mcpServers = @{
                aws = @{
                    command = "uvx"
                    args = @("awslabs.core-mcp-server@latest")
                    env = @{
                        FASTMCP_LOG_LEVEL = "ERROR"
                        AWS_REGION = "ap-southeast-1"
                    }
                }
            }
        } | ConvertTo-Json -Depth 10
        
        $mcpConfig | Out-File -FilePath ".cursor\mcp.json" -Encoding utf8
        Write-Host "✅ Created .cursor\mcp.json" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  .cursor\mcp.json already exists. Please merge AWS MCP config manually." -ForegroundColor Yellow
    Write-Host "   See .cursor\mcp.json.template for reference." -ForegroundColor Yellow
}

# Check AWS credentials
try {
    $awsIdentity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    Write-Host "✅ AWS credentials are configured" -ForegroundColor Green
    Write-Host "   Account: $($awsIdentity.Account)" -ForegroundColor Gray
    Write-Host "   User ARN: $($awsIdentity.Arn)" -ForegroundColor Gray
} catch {
    Write-Host "⚠️  AWS credentials not found. Please configure:" -ForegroundColor Yellow
    Write-Host "   1. Run: aws configure" -ForegroundColor Gray
    Write-Host "   2. Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables" -ForegroundColor Gray
    Write-Host "   3. Or use Doppler: doppler setup" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Restart Cursor IDE" -ForegroundColor White
Write-Host "   2. Verify MCP tools: Ask Cursor 'What AWS MCP tools are available?'" -ForegroundColor White
Write-Host "   3. Test: Ask Cursor 'List all Lambda functions in ap-southeast-1'" -ForegroundColor White
Write-Host ""
Write-Host "📚 See docs/MCP_SETUP.md for detailed documentation" -ForegroundColor Cyan

