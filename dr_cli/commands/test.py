"""Testing commands"""

import click
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group(invoke_without_command=True)
@click.pass_context
def test(ctx):
    """Testing commands - run tests, specific test files, LINE bot tests

    Running 'dr test' without subcommands runs all pytest tests.
    """
    if ctx.invoked_subcommand is None:
        # Default: run all tests
        use_doppler = ctx.obj.get('doppler', False)
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

        if use_doppler:
            doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
            result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
        else:
            result = subprocess.run(cmd, cwd=PROJECT_ROOT)

        sys.exit(result.returncode)


@test.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--tb', default='short', help='Traceback style (short, long, no)')
@click.pass_context
def all(ctx, verbose, tb):
    """Run all tests with pytest

    Runs the complete test suite.
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = [sys.executable, "-m", "pytest", "tests/", f"--tb={tb}"]
    if verbose:
        cmd.append("-v")

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


@test.command()
@click.argument('file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def file(ctx, file, verbose):
    """Run a specific test file

    Examples:
      dr test file test_agent.py
      dr test file tests/test_line_bot.py
    """
    use_doppler = ctx.obj.get('doppler', False)
    test_path = file if file.startswith('tests/') else f"tests/{file}"
    cmd = [sys.executable, "-m", "pytest", test_path]
    if verbose:
        cmd.append("-v")

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


@test.command()
@click.argument('type', type=click.Choice(['follow', 'help', 'error', 'fuzzy', 'cache']))
@click.pass_context
def line(ctx, type):
    """Run LINE bot specific tests

    Available types:
      follow - Test follow event handling
      help   - Test help command
      error  - Test error handling
      fuzzy  - Test fuzzy matching
      cache  - Test caching functionality
    """
    use_doppler = ctx.obj.get('doppler', False)
    test_map = {
        'follow': 'test_line_follow.py',
        'help': 'test_line_help.py',
        'error': 'test_line_error_handling.py',
        'fuzzy': 'test_fuzzy_matching.py',
        'cache': 'test_caching.py'
    }

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, f"tests/{test_map[type]}"]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env=env)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

    sys.exit(result.returncode)


@test.command()
@click.argument('ticker')
@click.pass_context
def message(ctx, ticker):
    """Test LINE bot message for a specific ticker

    Example:
      dr test message AAPL
    """
    use_doppler = ctx.obj.get('doppler', False)
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, "tests/test_line_message.py", ticker]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env=env)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

    sys.exit(result.returncode)


@test.command()
@click.argument('ticker')
@click.pass_context
def integration(ctx, ticker):
    """Run integration test for a specific ticker

    Example:
      dr test integration AAPL
    """
    use_doppler = ctx.obj.get('doppler', False)
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, "tests/test_line_integration.py", ticker]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env=env)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

    sys.exit(result.returncode)
