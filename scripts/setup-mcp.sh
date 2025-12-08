#!/bin/bash
# Setup script for AWS MCP in Cursor IDE

set -e

echo "🔧 Setting up AWS MCP for Cursor IDE..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "📦 Installing uv..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "⚠️  Windows detected. Please install uv manually:"
        echo "   1. Set execution policy: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
        echo "   2. Run: irm https://astral.sh/uv/install.ps1 | iex"
        exit 1
    fi
    
    # Add to PATH if needed
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv is installed: $(uv --version)"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed"
    echo "📦 Installing Python 3.13 via uv..."
    uv python install 3.13
else
    echo "✅ Python is installed: $(python --version)"
fi

# Create .cursor directory if it doesn't exist
mkdir -p .cursor

# Create mcp.json if it doesn't exist
if [ ! -f .cursor/mcp.json ]; then
    echo "📝 Creating .cursor/mcp.json..."
    cp .cursor/mcp.json.template .cursor/mcp.json
    echo "✅ Created .cursor/mcp.json"
else
    echo "⚠️  .cursor/mcp.json already exists. Please merge AWS MCP config manually."
    echo "   See .cursor/mcp.json.template for reference."
fi

# Check AWS credentials
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials are configured"
    aws sts get-caller-identity
else
    echo "⚠️  AWS credentials not found. Please configure:"
    echo "   1. Run: aws configure"
    echo "   2. Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    echo "   3. Or use Doppler: doppler setup"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Restart Cursor IDE"
echo "   2. Verify MCP tools: Ask Cursor 'What AWS MCP tools are available?'"
echo "   3. Test: Ask Cursor 'List all Lambda functions in ap-southeast-1'"
echo ""
echo "📚 See docs/MCP_SETUP.md for detailed documentation"

