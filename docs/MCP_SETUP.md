# MCP (Model Context Protocol) Setup Guide

This guide explains how to set up AWS MCP tools in Cursor IDE for enhanced AWS integration.

---

## Overview

MCP (Model Context Protocol) allows AI assistants in Cursor to interact directly with AWS services, enabling:
- Direct Lambda function management
- S3 bucket operations
- CloudWatch log queries
- DynamoDB table inspection
- And more AWS services

---

## Quick Setup

### Automated Setup (Recommended)

**Windows (PowerShell):**
```powershell
.\scripts\setup-mcp.ps1
```

**Linux/macOS:**
```bash
./scripts/setup-mcp.sh
```

### Manual Setup

#### 1. Install `uv` Package Manager

`uv` is required to run the AWS MCP server. Install it using one of these methods:

**Windows (PowerShell):**
```powershell
# First, set execution policy (run as Administrator or CurrentUser)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then install uv
irm https://astral.sh/uv/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Alternative (Manual):**
1. Download `uv` from: https://github.com/astral-sh/uv/releases
2. Extract and add to PATH

**Verify installation:**
```bash
uv --version
```

### 2. Install Python (if not already installed)

Python 3.11+ is required. Verify:
```bash
python --version
```

If needed, install Python 3.13 using `uv`:
```bash
uv python install 3.13
```

### 3. Configure AWS Credentials

The AWS MCP server needs AWS credentials to access your AWS resources.

**Option A: AWS Credentials File (Recommended)**
```bash
# Create/edit ~/.aws/credentials
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = ap-southeast-1
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=ap-southeast-1
```

**Option C: AWS CLI Configure**
```bash
aws configure
```

**Option D: Use Doppler (Project Standard)**
The project uses Doppler for secrets management. You can configure MCP to use Doppler:

```json
{
  "mcpServers": {
    "aws": {
      "command": "doppler",
      "args": [
        "run",
        "--",
        "uvx",
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**Required AWS Permissions:**
The AWS credentials need permissions for:
- Lambda (read/write)
- S3 (read/write)
- CloudWatch Logs (read)
- DynamoDB (read)
- API Gateway (read)
- CloudFront (read)

See `docs/AWS_SETUP.md` for complete IAM policy reference.

---

## Configuration

### Project-Specific Configuration

**Step 1**: Create `.cursor/mcp.json` in your project root (or copy from `.cursor/mcp.json.template`):

```bash
# Copy the template
cp .cursor/mcp.json.template .cursor/mcp.json

# Or create manually
```

**Step 2**: Add the following configuration to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "ap-southeast-1"
      }
    }
  }
}
```

**Note**: If `.cursor/mcp.json` already exists, merge the `aws` server configuration into the existing `mcpServers` object.

### Global Configuration (Optional)

If you want AWS MCP tools available across all projects, create `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

---

## Verification

### 1. Restart Cursor

After creating/updating the MCP configuration, **restart Cursor** to apply changes.

### 2. Verify MCP Integration

Open the chat panel in Cursor and ask:
```
What AWS MCP tools are available?
```

You should see a list of available AWS MCP tools, confirming successful integration.

### 3. Test AWS Operations

Try asking Cursor to:
```
List all Lambda functions in the ap-southeast-1 region
```

Or:
```
Show me CloudWatch logs for the telegram-api Lambda function
```

---

## Available AWS MCP Tools

Once configured, you'll have access to tools like:

- **Lambda Functions**: List, invoke, get configuration, update code
- **S3 Buckets**: List buckets, get objects, upload files
- **CloudWatch Logs**: Query logs, filter log events
- **DynamoDB**: List tables, scan items, query items
- **API Gateway**: List APIs, get resources
- **CloudFront**: List distributions, invalidate cache
- **EC2**: List instances, describe instances
- **IAM**: List roles, get policies
- And more...

---

## Troubleshooting

### Issue: "uv: command not found"

**Solution**: Install `uv` using the instructions above. Verify with `uv --version`.

### Issue: "AWS credentials not found"

**Solution**: Configure AWS credentials using one of the methods above. Verify with:
```bash
aws sts get-caller-identity
```

### Issue: "Permission denied" errors

**Solution**: Ensure your AWS credentials have the necessary permissions. See `docs/AWS_SETUP.md` for IAM policy reference.

### Issue: MCP tools not appearing in Cursor

**Solution**:
1. Verify `.cursor/mcp.json` exists and is valid JSON
2. Restart Cursor completely
3. Check Cursor logs for MCP errors (Help → Toggle Developer Tools → Console)

### Issue: "uvx: command not found"

**Solution**: Ensure `uv` is installed and in your PATH. Try:
```bash
uv --version
uvx --help
```

---

## Integration with Project Workflow

### Using MCP Tools for Deployment

Instead of running AWS CLI commands manually, you can now ask Cursor:

```
Update the telegram-api Lambda function with the latest code from ECR image sha-abc123
```

Or:
```
Show me the last 10 errors from CloudWatch logs for the telegram-api function
```

### Using MCP Tools for Debugging

```
Query CloudWatch logs for errors in the last hour from the telegram-api Lambda
```

Or:
```
List all DynamoDB tables and show me the item count for each
```

---

## Security Considerations

1. **Credentials**: Never commit AWS credentials to git. Use environment variables or AWS credentials file.
2. **Permissions**: Follow least privilege principle. Only grant necessary AWS permissions.
3. **Audit**: Monitor AWS CloudTrail for MCP-initiated operations.

---

## References

- [MCP Documentation](https://modelcontextprotocol.io/)
- [AWS MCP Server](https://github.com/awslabs/core-mcp-server)
- [Cursor MCP Setup](https://docs.cursor.com/advanced/mcp)
- [AWS Setup Guide](docs/AWS_SETUP.md)

---

## Next Steps

After setup:
1. ✅ Verify MCP tools are available
2. ✅ Test basic AWS operations
3. ✅ Integrate into development workflow
4. ✅ Use for deployment and debugging tasks

