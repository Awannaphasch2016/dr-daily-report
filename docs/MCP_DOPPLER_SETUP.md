# MCP Configuration with Doppler

This document describes how MCP servers are configured to use Doppler for secrets management, following the project's standard pattern from `.cursor/principles.md`.

## Overview

All MCP servers in this project use **Doppler** to inject environment variables and secrets. This follows the project's secret management principle:

> **"Environment Variables: Managed via Doppler"**  
> Pattern: `ENV=dev doppler run -- python app.py`

## Configuration

The MCP configuration in `.cursor/mcp.json` uses Doppler for all servers:

```json
{
  "mcpServers": {
    "aws": {
      "command": "doppler",
      "args": [
        "run",
        "--config",
        "dev",
        "--",
        "uvx",
        "awslabs.core-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "ap-southeast-1"
      }
    },
    "aurora-mysql": {
      "command": "doppler",
      "args": [
        "run",
        "--config",
        "dev",
        "--",
        "uvx",
        "awslabs.mysql-mcp-server@latest"
      ],
      "env": {
        "AWS_REGION": "ap-southeast-1",
        "AURORA_CLUSTER_IDENTIFIER": "dr-daily-report-aurora-dev",
        "AURORA_DATABASE_NAME": "ticker_data"
      }
    },
    "github": {
      "command": "doppler",
      "args": [
        "run",
        "--config",
        "dev",
        "--",
        "npx",
        "-y",
        "@modelcontextprotocol/server-github"
      ]
    }
  }
}
```

## How It Works

1. **Doppler Command**: Each MCP server uses `doppler` as the command
2. **Config Selection**: `--config dev` specifies the Doppler config to use
3. **Command Separation**: `--` separates Doppler args from the actual command
4. **Environment Injection**: Doppler injects all secrets from the `dev` config as environment variables

## Required Secrets in Doppler

### AWS MCP Server
- `AWS_ACCESS_KEY_ID` (or AWS credentials via IAM role)
- `AWS_SECRET_ACCESS_KEY` (if using access keys)
- `AWS_REGION` (can also be set in `env` block)

### Aurora MySQL MCP Server
- `AURORA_CLUSTER_IDENTIFIER` (can be set in `env` block)
- `AURORA_DATABASE_NAME` (can be set in `env` block)
- AWS credentials (same as AWS MCP)

### GitHub MCP Server
- `GITHUB_PERSONAL_ACCESS_TOKEN` (required)

## Adding Secrets to Doppler

### Via CLI

```bash
# Add GitHub token
doppler secrets set GITHUB_PERSONAL_ACCESS_TOKEN=your_token --config dev

# Add AWS credentials (if not using IAM role)
doppler secrets set AWS_ACCESS_KEY_ID=your_key --config dev
doppler secrets set AWS_SECRET_ACCESS_KEY=your_secret --config dev
```

### Via Doppler Dashboard

1. Go to [Doppler Dashboard](https://dashboard.doppler.com)
2. Select project: `dr-daily-report-telegram`
3. Select config: `dev`
4. Add secrets as needed

## Verification

### Quick Check

```bash
# Verify configuration
just verify-mcp

# Or directly
python scripts/test_mcp_doppler.py
```

### Manual Verification

```bash
# Check if Doppler is installed
doppler --version

# Check if config is accessible
doppler secrets --config dev

# Check specific secret
doppler secrets get GITHUB_PERSONAL_ACCESS_TOKEN --config dev --plain
```

## Troubleshooting

### GitHub MCP Not Working

**Symptom**: GitHub MCP server fails to start or shows authentication errors.

**Solution**:
1. Verify token exists: `doppler secrets get GITHUB_PERSONAL_ACCESS_TOKEN --config dev --plain`
2. If missing, add it: `doppler secrets set GITHUB_PERSONAL_ACCESS_TOKEN=your_token --config dev`
3. Restart Cursor IDE

### AWS MCP Not Working

**Symptom**: AWS MCP server fails to authenticate or shows permission errors.

**Solution**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. If using access keys, ensure they're in Doppler:
   - `doppler secrets get AWS_ACCESS_KEY_ID --config dev --plain`
   - `doppler secrets get AWS_SECRET_ACCESS_KEY --config dev --plain`
3. If using IAM role, ensure role has necessary permissions
4. Restart Cursor IDE

### Doppler Config Not Found

**Symptom**: Error about Doppler config 'dev' not being set up.

**Solution**:
```bash
# Setup Doppler config
doppler setup --config dev

# Or manually set project/config
doppler configure set project dr-daily-report-telegram
doppler configure set config dev
```

## Benefits of Doppler Integration

1. **Centralized Secrets**: All secrets in one place (Doppler)
2. **Environment Separation**: Different secrets per environment (dev/staging/prod)
3. **Security**: No secrets in code or config files
4. **Consistency**: Same pattern as application code (Lambda functions)
5. **Audit Trail**: Doppler tracks who accessed what secrets when

## Related Documentation

- `.cursor/principles.md` - Project principles and secret management guidelines
- `docs/MCP_SETUP.md` - General MCP setup instructions
- `docs/MCP_RECOMMENDATIONS.md` - Recommended MCP servers for this project
- `docs/deployment/WORKFLOW.md` - Deployment workflow and secrets
