---
name: list-cli
description: List all dr CLI commands grouped by category (dev, test, build, deploy, clean, check, util)
accepts_args: false
composition: []
---

# List CLI

**Purpose**: Display all `dr` CLI commands organized by functional group for easy discovery

**Core Principle**: "Two-layer design" - Justfile (intent/WHEN) + dr CLI (implementation/HOW)

**When to use**:
- Forgot which dr commands are available
- Looking for specific functionality in dr CLI
- Quick reference for command options
- Understanding dr CLI structure
- Finding alternatives to manual workflows

---

## Quick Reference

```bash
/list-cli    # Show all dr commands by category
```

---

## Execution Flow

### Step 1: Introspect CLI Object

Use Click's introspection capabilities:

```python
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

# Import CLI
from dr_cli.main import cli

# Introspect command groups
groups = {}
for name, command in cli.commands.items():
    if hasattr(command, 'commands'):  # It's a group
        groups[name] = {
            'help': command.help or command.__doc__ or '',
            'commands': {}
        }
        for subname, subcmd in command.commands.items():
            help_text = subcmd.help or subcmd.__doc__ or ''
            # Extract first line of docstring if multi-line
            groups[name]['commands'][subname] = help_text.split('\n')[0]
```

### Step 2: Extract Command Information

For each command group:
1. Get group name from `cli.commands.keys()`
2. Get group help text from `command.help` or `command.__doc__`
3. Iterate subcommands via `command.commands.items()`
4. Extract subcommand help text (first line of docstring)
5. Parse arguments/options from `command.params` (optional)

### Step 3: Generate Formatted Output

```markdown
# DR CLI Commands

**Two-layer design**:
- **Justfile**: Intent layer (WHEN/WHY to run commands)
- **dr CLI**: Implementation layer (HOW to run commands)

Use `dr --help` for detailed help on any command.

---

## Command Groups

### {group_name} - {Group Title}
**Purpose**: {group help text}

- `dr {group} {command}` - {command help}
- `dr {group} {command} <arg>` - {command help}
[...]
```

---

## Command Groups

### dev - Development Commands

**Purpose**: Local development workflow - server, shell, scripts, environment setup

- `dr dev server` - Run the Flask server locally for development and testing
- `dr dev shell` - Start interactive Python shell with project context (PYTHONPATH configured)
- `dr dev run <script>` - Run a Python script with proper PYTHONPATH configuration
- `dr dev install` - Install project dependencies from requirements.txt
- `dr dev verify [target]` - Verify development environment setup (optional: aurora/frontend/all)

**Common workflow**:
```bash
dr dev verify        # Check environment first
dr dev server        # Run server
dr dev shell         # Interactive testing
```

---

### test - Testing Commands

**Purpose**: Run tests - unit tests, integration tests, LINE bot tests, tier-based tests

- `dr test` - Run all pytest tests (default behavior, same as `dr test all`)
- `dr test all` - Run all tests with pytest
- `dr test file <file>` - Run a specific test file
- `dr test line <type>` - Run LINE bot specific tests (follow/help/error/fuzzy/cache)
- `dr test telegram <ticker>` - Test Telegram bot message generation for a specific ticker
- `dr test integration <ticker>` - Run integration test for a ticker
- `dr test message <ticker>` - Test LINE bot message for a ticker (legacy)

**Common workflow**:
```bash
dr test              # Run all tests
dr test file tests/test_scoring.py  # Specific file
dr test integration AAPL             # Integration test
```

---

### build - Build Commands

**Purpose**: Create Lambda deployment packages and Docker images

- `dr build` - Create Lambda deployment package (standard build)
- `dr build --minimal` - Create minimal Lambda package (exclude dev dependencies)
- `dr build --type <type>` - Choose build type (lambda/standard)

**Common workflow**:
```bash
dr build             # Standard Lambda package
dr build --minimal   # Minimal package for production
```

---

### deploy - Deployment Commands

**Purpose**: Deploy to AWS Lambda, sync environment variables, setup webhooks

- `dr deploy lambda-deploy` - Deploy Lambda function to AWS
- `dr deploy sync-env <function>` - Sync Doppler secrets to Lambda environment variables
- `dr deploy webhook` - Setup LINE webhook configuration

**Common workflow**:
```bash
dr build                      # Build first
dr deploy lambda-deploy       # Deploy to Lambda
dr deploy sync-env <name>     # Sync env vars
```

---

### clean - Cleanup Commands

**Purpose**: Remove build artifacts, cache files, temporary files

- `dr clean all` - Clean everything (build artifacts + cache + temporary files)
- `dr clean build` - Clean build artifacts only (dist/, build/, *.egg-info)
- `dr clean cache` - Clean Python cache files only (__pycache__, *.pyc)

**Common workflow**:
```bash
dr clean all         # Full cleanup
dr clean build       # Before fresh build
```

---

### check - Code Quality & Validation

**Purpose**: Verify code quality, environment, formatting, linting

- `dr check env` - Check environment variables status (shows missing/set variables)
- `dr check format` - Format code with black (auto-formats Python files)
- `dr check lint` - Lint code with pylint (code quality checks)
- `dr check syntax` - Check Python syntax (validates all .py files)

**Common workflow**:
```bash
dr check env         # Verify environment first
dr check format      # Format code
dr check lint        # Check quality
```

---

### util - Utility Commands

**Purpose**: Project information, statistics, report generation, exploration

- `dr util info` - Show project info and common commands (quick reference)
- `dr util tree` - Show project structure (directory tree)
- `dr util stats` - Count lines of code (by file type)
- `dr util list-py` - List all Python files in the project
- `dr util report <ticker>` - Generate report for a specific ticker
- `dr util report-all` - Generate reports for all tickers
- `dr util report-cached <ticker>` - Regenerate report from cached data
- `dr util prompt-vars <ticker>` - Inspect prompt variables for debugging

**Common workflow**:
```bash
dr util info             # Quick reference
dr util report AAPL      # Generate report
dr util stats            # Project statistics
```

---

## Two-Layer Design Explained

### Layer 1: Justfile (Intent)

**Answers**: "WHEN should I use this?" and "WHY does this exist?"

Example Justfile recipe:
```just
# Deploy after successful tests
deploy-dev: test
    dr deploy lambda-deploy
```

### Layer 2: dr CLI (Implementation)

**Answers**: "HOW does this work?" and "WHAT does it do?"

Example dr CLI command:
```bash
dr deploy lambda-deploy
# → Builds package
# → Uploads to Lambda
# → Updates function code
```

### Relationship

- **Justfile recipes** = High-level workflows (can chain multiple dr commands)
- **dr CLI commands** = Low-level operations (single responsibility)
- **Both are discoverable**: `just --list` and `/list-cli`
- **Both have help**: `just --help` and `dr --help`

---

## Quick Tips

### By Use Case

**"I want to start development"**:
```bash
dr dev verify        # Check environment
dr dev server        # Run server
```

**"I want to test my changes"**:
```bash
dr test              # Run all tests
dr test file <file>  # Run specific test
```

**"I want to deploy"**:
```bash
dr build                    # Build package
dr deploy lambda-deploy     # Deploy
dr check env                # Verify environment
```

**"I want to clean up"**:
```bash
dr clean all         # Full cleanup
```

**"I want project info"**:
```bash
dr util info         # Quick reference
dr util tree         # Project structure
dr util stats        # Statistics
```

---

## Execution Example

```bash
# Get help on any command
dr --help                    # All command groups
dr dev --help                # Development commands
dr test --help               # Testing commands
dr deploy --help             # Deployment commands

# Run specific commands
dr dev verify                # Verify environment
dr test                      # Run all tests
dr util report AAPL          # Generate report
dr build                     # Build package
dr deploy lambda-deploy      # Deploy
```

---

## Command Discovery

### List All Commands

```python
# Get all command groups
from dr_cli.main import cli
print(list(cli.commands.keys()))
# Output: ['build', 'check', 'clean', 'deploy', 'dev', 'test', 'util']

# Get commands in a group
print(list(cli.commands['test'].commands.keys()))
# Output: ['all', 'file', 'line', 'telegram', 'integration', 'message']
```

### Get Command Help

```python
# Get command help text
from dr_cli.main import cli
command = cli.commands['dev'].commands['server']
print(command.help)
# Output: "Run the Flask server locally for development and testing"
```

---

## Statistics

**Total command groups**: 7
- dev (5 commands)
- test (7 commands)
- build (1 command with options)
- deploy (3 commands)
- clean (3 commands)
- check (4 commands)
- util (8 commands)

**Total commands**: ~31 commands

**Design pattern**: Click framework with command groups

**Two layers**:
- Justfile: High-level workflows
- dr CLI: Low-level operations

---

## Examples

### Example 1: Complete Development Workflow

```bash
# Setup
dr dev install       # Install dependencies
dr dev verify        # Verify environment

# Development
dr dev server        # Run server (one terminal)
dr dev shell         # Interactive shell (another terminal)

# Testing
dr test              # Run all tests
dr test file tests/test_api.py  # Specific test

# Code quality
dr check format      # Format code
dr check lint        # Check quality

# Deploy
dr build             # Build package
dr deploy lambda-deploy  # Deploy
```

---

### Example 2: Quick Report Generation

```bash
# Generate report
dr util report AAPL

# Generate all reports
dr util report-all

# Use cached data
dr util report-cached AAPL
```

---

### Example 3: Clean Development Environment

```bash
# Full cleanup
dr clean all

# Selective cleanup
dr clean build       # Remove build artifacts
dr clean cache       # Remove Python cache
```

---

## Environment Requirements

Most `dr` commands require:
- **Doppler**: Environment variables
  ```bash
  ENV=dev doppler run -- dr <command>
  ```

- **Python environment**: Virtual environment activated
  ```bash
  source venv/bin/activate
  dr <command>
  ```

- **AWS credentials**: For deployment commands
  ```bash
  aws configure  # Setup once
  dr deploy <command>
  ```

---

## Related Commands

- `/list-commands` - List all slash commands
- `/evolve cli` - Detect CLI drift and inconsistencies
- `dr util info` - Project info and common commands

---

## Learn More

### CLI Documentation

```bash
# Read CLI documentation
cat docs/cli.md
cat docs/PROJECT_CONVENTIONS.md
```

### Command Implementation

```bash
# See command source code
cat dr_cli/commands/dev.py
cat dr_cli/commands/test.py
cat dr_cli/commands/util.py
```

### Justfile (if exists)

```bash
# List Justfile recipes
just --list

# See Justfile
cat Justfile
```

---

## See Also

- `docs/cli.md` - CLI reference documentation
- `docs/PROJECT_CONVENTIONS.md` - Project conventions (includes CLI design)
- `dr_cli/main.py` - CLI entry point
- `dr_cli/commands/*.py` - Command implementations
