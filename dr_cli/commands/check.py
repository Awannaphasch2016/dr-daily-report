"""Code quality and validation commands"""

import click
import subprocess
import sys
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group()
@click.pass_context
def check(ctx):
    """Code quality and validation commands"""
    pass


@check.command()
@click.pass_context
def syntax(ctx):
    """Check Python syntax

    Validates syntax of all Python files in src/
    """
    cmd = [sys.executable, "-m", "py_compile"]

    # Add all Python files in src/
    src_dir = PROJECT_ROOT / "src"
    py_files = list(src_dir.rglob("*.py"))

    if not py_files:
        click.echo("No Python files found in src/")
        sys.exit(0)

    cmd.extend(str(f) for f in py_files)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    if result.returncode == 0:
        click.echo("✓ Syntax check passed")
    else:
        click.echo("✗ Syntax errors found:")
        click.echo(result.stderr)

    sys.exit(result.returncode)


@check.command()
@click.pass_context
def env(ctx):
    """Check environment variables status

    Verifies that required environment variables are set.
    """
    required_vars = [
        "OPENROUTER_API_KEY",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_CHANNEL_SECRET"
    ]

    click.echo("Checking environment variables...")
    all_set = True

    for var in required_vars:
        if os.environ.get(var):
            click.echo(f"✓ {var}: Set")
        else:
            click.echo(f"✗ {var}: Not set")
            all_set = False

    if not all_set:
        click.echo("\nTip: Use 'dr --doppler <command>' to load variables from doppler")
        sys.exit(1)


@check.command()
@click.option('--line-length', default=100, help='Maximum line length')
@click.pass_context
def format(ctx, line_length):
    """Format code with black

    Formats Python code using black formatter.
    """
    cmd = [sys.executable, "-m", "black", "src/", "tests/", f"--line-length={line_length}"]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    if result.returncode == 0:
        click.echo(result.stdout)
        click.echo("✓ Code formatted")
    else:
        if "No module named" in result.stderr:
            click.echo("⚠ black not installed")
            click.echo("  Install with: pip install black")
            sys.exit(0)
        else:
            click.echo("✗ Formatting failed:")
            click.echo(result.stderr)
            sys.exit(result.returncode)


@check.command()
@click.pass_context
def lint(ctx):
    """Lint code with pylint

    Runs pylint on source code (errors only).
    """
    cmd = [sys.executable, "-m", "pylint", "src/", "--disable=C,R,W"]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

    if "No module named" in result.stderr:
        click.echo("⚠ pylint not installed")
        click.echo("  Install with: pip install pylint")
        sys.exit(0)

    click.echo(result.stdout)
    if result.returncode == 0:
        click.echo("✓ No linting errors")
