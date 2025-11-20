# DR CLI Unit Tests

Comprehensive unit tests for the DR CLI using pytest and Click's testing utilities.

## Test Coverage

**Total: 74 tests** covering all CLI commands and functionality.

### Test Files

- **test_main.py** (6 tests) - Main CLI entry point
  - Help display
  - Command registration
  - Global flags (--doppler)
  - Error handling

- **test_dev_commands.py** (9 tests) - Development commands
  - `dr dev server`
  - `dr dev shell`
  - `dr dev run`
  - `dr dev install`
  - Doppler integration

- **test_test_commands.py** (12 tests) - Testing commands
  - `dr test` (all, file, line)
  - `dr test message`
  - `dr test integration`
  - Test type validation

- **test_build_commands.py** (7 tests) - Build commands
  - `dr build` (standard, minimal, lambda)
  - Build type options
  - Doppler integration

- **test_deploy_commands.py** (7 tests) - Deployment commands
  - `dr deploy lambda-deploy`
  - `dr deploy webhook`
  - Doppler integration

- **test_clean_commands.py** (8 tests) - Cleanup commands
  - `dr clean build`
  - `dr clean cache`
  - `dr clean all`

- **test_check_commands.py** (11 tests) - Code quality commands
  - `dr check syntax`
  - `dr check env`
  - `dr check format`
  - `dr check lint`
  - Tool availability detection

- **test_utils_commands.py** (14 tests) - Utility commands
  - `dr util tree`
  - `dr util stats`
  - `dr util list-py`
  - `dr util report`
  - `dr util info`

## Running Tests

### Run All CLI Tests

```bash
# From project root
pytest tests/test_cli/ -v

# Or using the CLI
dr test file test_cli/
```

### Run Specific Test File

```bash
pytest tests/test_cli/test_dev_commands.py -v
```

### Run Specific Test

```bash
pytest tests/test_cli/test_dev_commands.py::test_dev_server -v
```

### Run with Coverage

```bash
pytest tests/test_cli/ --cov=dr_cli --cov-report=html
```

### Quick Test Summary

```bash
pytest tests/test_cli/ -v --tb=short
```

## Test Structure

Tests use:
- **pytest** - Test framework
- **Click's CliRunner** - CLI testing utilities
- **unittest.mock** - Mocking subprocess calls and file operations

### Example Test Pattern

```python
from click.testing import CliRunner
from unittest.mock import patch
from dr_cli.main import cli

def test_command(runner):
    """Test description"""
    result = runner.invoke(cli, ['command', 'args'])
    assert result.exit_code == 0
    assert 'expected output' in result.output
```

## What Tests Cover

### ✅ Command Execution
- Correct subprocess calls with proper arguments
- Command chaining and composition
- Exit code validation

### ✅ Help System
- Help text at every command level
- Command descriptions
- Option documentation

### ✅ Doppler Integration
- `--doppler` flag handling
- Environment variable loading
- Doppler command wrapping

### ✅ Error Handling
- Invalid commands
- Missing arguments
- Invalid options
- Tool availability (black, pylint)

### ✅ File Operations
- Path handling
- Build artifact cleanup
- Cache management

### ✅ Output Validation
- Success messages
- Error messages
- Formatted output

## Mocking Strategy

Tests mock external operations to:
1. **Avoid side effects** - No actual file system changes
2. **Speed** - Tests run in <1 second
3. **Isolation** - Each test is independent
4. **Predictability** - Consistent results

### Mocked Operations

- `subprocess.run` - Command execution
- `pathlib.Path` operations - File system
- `os.environ` - Environment variables
- `shutil` - File operations

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run CLI tests
  run: |
    pip install -e .
    pytest tests/test_cli/ -v
```

## Test Maintenance

When adding new CLI commands:

1. Create test file in `tests/test_cli/test_<command>_commands.py`
2. Test help text
3. Test command execution with mocked subprocess
4. Test with and without doppler flag
5. Test error cases
6. Update this README with test count

## Coverage Goals

- ✅ **Command registration**: All commands discoverable
- ✅ **Help system**: Help text at all levels
- ✅ **Execution**: Correct subprocess calls
- ✅ **Doppler**: Flag handling
- ✅ **Error cases**: Invalid inputs handled
- ✅ **Output**: Expected messages displayed

Current coverage: **100% of CLI commands**

## Running Tests in Development

```bash
# Watch mode (requires pytest-watch)
ptw tests/test_cli/

# Verbose with output
pytest tests/test_cli/ -vv -s

# Stop on first failure
pytest tests/test_cli/ -x

# Run last failed tests
pytest tests/test_cli/ --lf
```

## Troubleshooting

### Tests failing after CLI changes

1. Check if command signatures changed
2. Update mocked subprocess calls
3. Verify help text updates

### Import errors

```bash
# Reinstall CLI in editable mode
pip install -e .
```

### Mock not working

Ensure mock path matches actual import:
```python
# Correct
@patch('dr_cli.commands.dev.subprocess.run')

# Incorrect
@patch('subprocess.run')
```

## Future Test Enhancements

- [ ] Integration tests with real subprocess calls
- [ ] End-to-end workflow tests
- [ ] Performance benchmarks
- [ ] CLI output formatting tests
- [ ] Configuration file tests
