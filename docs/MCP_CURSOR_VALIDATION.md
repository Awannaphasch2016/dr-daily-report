# MCP Cursor Validation Guide

This guide helps you validate that MCP servers are working correctly in Cursor IDE.

## Pre-Validation Checklist

Before validating in Cursor, ensure:

- ✅ Wrapper scripts are executable: `chmod +x scripts/mcp_wrapper_*.sh`
- ✅ Doppler is installed and configured: `doppler --version`
- ✅ MCP configuration is valid: `python3 -m json.tool .cursor/mcp.json`
- ✅ Validation script passes: `python3 scripts/validate_mcp_cursor_session.py`

## Step 1: Restart Cursor IDE

**IMPORTANT:** Cursor must be completely restarted to load MCP configuration changes.

1. **Close Cursor completely:**
   - Close all Cursor windows
   - Wait 5-10 seconds
   - Verify Cursor process is not running (optional: `ps aux | grep -i cursor`)

2. **Reopen Cursor IDE:**
   - Launch Cursor IDE
   - Open this project: `/home/anak/dev/dr-daily-report_telegram`
   - Wait for Cursor to fully load

## Step 2: Verify MCP Servers Are Loaded

1. **Open Cursor Chat Panel:**
   - Press `Ctrl+L` (Linux/Windows) or `Cmd+L` (Mac)
   - Or click the chat icon in the sidebar

2. **Ask Cursor:**
   ```
   What MCP tools are available?
   ```

3. **Expected Response:**
   - Cursor should list available MCP tools from AWS and GitHub servers
   - You should see tools like:
     - AWS Lambda functions
     - AWS S3 operations
     - GitHub repository operations
     - GitHub issue management

## Step 3: Test AWS MCP Server

Try these commands in Cursor chat:

### Test 1: List Lambda Functions
```
List all Lambda functions in the ap-southeast-1 region
```

**Expected:** List of Lambda functions including `dr-daily-report-telegram-api-dev`

### Test 2: CloudWatch Logs
```
Show recent CloudWatch logs for the telegram-api Lambda function
```

**Expected:** Recent log entries from the Lambda function

### Test 3: S3 Buckets
```
List all S3 buckets in my AWS account
```

**Expected:** List of S3 buckets

### Test 4: DynamoDB Tables
```
List all DynamoDB tables in ap-southeast-1
```

**Expected:** List of DynamoDB tables

## Step 4: Test GitHub MCP Server

Try these commands in Cursor chat:

### Test 1: List Repositories
```
List repositories in my GitHub account
```

**Expected:** List of your GitHub repositories

### Test 2: Repository Info
```
Show information about the dr-daily-report_telegram repository
```

**Expected:** Repository details, description, stars, etc.

### Test 3: Recent Commits
```
Show recent commits in the telegram branch of this repository
```

**Expected:** List of recent commits

### Test 4: Create Issue (Optional)
```
Create a new issue in this repository titled "Test MCP Integration" with body "Testing GitHub MCP server"
```

**Expected:** New issue created successfully

## Step 5: Troubleshooting

If MCP servers are not working:

### Check Cursor Logs

1. **Open Cursor Logs:**
   - Help → Show Logs
   - Or: `Ctrl+Shift+P` → "Show Logs"

2. **Search for MCP errors:**
   - Search for: `mcp` or `modelcontextprotocol`
   - Look for error messages

3. **Common Issues:**

   **Issue: "Command not found"**
   - **Solution:** Verify wrapper scripts exist and are executable
   - Run: `ls -la scripts/mcp_wrapper_*.sh`
   - Fix: `chmod +x scripts/mcp_wrapper_*.sh`

   **Issue: "Doppler error"**
   - **Solution:** Verify Doppler is installed and configured
   - Run: `doppler --version`
   - Check: `doppler secrets --config dev`

   **Issue: "MCP server not responding"**
   - **Solution:** Test wrapper scripts manually
   - Run: `./scripts/mcp_wrapper_aws.sh` (should start and wait for input)
   - Press Ctrl+C to exit

   **Issue: "No MCP tools available"**
   - **Solution:** Verify configuration is correct
   - Check: `.cursor/mcp.json` syntax
   - Restart Cursor completely

### Manual Validation

Run the validation script:

```bash
python3 scripts/validate_mcp_cursor_session.py
```

This simulates how Cursor would interact with MCP servers.

### Test Wrapper Scripts Directly

Test each wrapper script:

```bash
# Test AWS wrapper (should start MCP server)
./scripts/mcp_wrapper_aws.sh

# In another terminal, send MCP initialize:
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"test","version":"1.0"}}}' | ./scripts/mcp_wrapper_aws.sh

# Test GitHub wrapper
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"clientInfo":{"name":"test","version":"1.0"}}}' | ./scripts/mcp_wrapper_github.sh
```

## Success Criteria

✅ **MCP servers are working if:**
- Cursor lists MCP tools when asked
- AWS operations (Lambda, S3, etc.) work
- GitHub operations (repos, issues, etc.) work
- No errors in Cursor logs

❌ **MCP servers are NOT working if:**
- Cursor says "No MCP tools available"
- Commands fail with "MCP error" messages
- Errors appear in Cursor logs
- Validation script fails

## Current Configuration

**Active MCP Servers:**
- ✅ AWS MCP Server (`scripts/mcp_wrapper_aws.sh`)
- ✅ GitHub MCP Server (`scripts/mcp_wrapper_github.sh`)
- ⚠️ Aurora MySQL MCP Server (disabled - requires Secrets Manager ARN)

**Configuration File:**
- `.cursor/mcp.json` - Active MCP configuration

**Wrapper Scripts:**
- `scripts/mcp_wrapper_aws.sh` - AWS MCP with Doppler
- `scripts/mcp_wrapper_github.sh` - GitHub MCP with Doppler
- `scripts/mcp_wrapper_aurora.sh` - Aurora MySQL MCP (not in use)

## Additional Resources

- [MCP Setup Guide](MCP_SETUP.md)
- [MCP Doppler Setup](MCP_DOPPLER_SETUP.md)
- [MCP Recommendations](MCP_RECOMMENDATIONS.md)
