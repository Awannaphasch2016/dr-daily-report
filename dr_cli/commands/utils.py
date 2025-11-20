"""Utility commands"""

import click
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group(name='util')
@click.pass_context
def utils(ctx):
    """Utility commands - project info, stats, report generation"""
    pass


@utils.command()
def tree():
    """Show project structure

    Displays the directory tree (max depth 2).
    """
    # Try tree command first
    result = subprocess.run(
        ["tree", "-L", "2", "-I", "venv|__pycache__|*.pyc|.git|build"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        click.echo(result.stdout)
    else:
        # Fallback to find
        result = subprocess.run(
            ["find", ".", "-maxdepth", "2", "-not", "-path", "*/.*", "-not", "-path", "*/venv/*", "-not", "-path", "*/build/*"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        lines = result.stdout.split('\n')[:30]
        click.echo('\n'.join(lines))


@utils.command()
def stats():
    """Count lines of code

    Shows total lines of Python code in the project.
    """
    result = subprocess.run(
        ["find", ".", "-name", "*.py", "-not", "-path", "./venv/*", "-not", "-path", "./build/*", "-not", "-path", "./.git/*"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    py_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]

    if not py_files:
        click.echo("No Python files found")
        return

    result = subprocess.run(
        ["wc", "-l"] + py_files,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().split('\n')
    if len(lines) > 1:
        # Last line has total
        total_line = lines[-1]
        click.echo(total_line)


@utils.command()
def list_py():
    """List Python files

    Shows all Python files in the project (max 50).
    """
    result = subprocess.run(
        ["find", ".", "-name", "*.py", "-not", "-path", "./venv/*", "-not", "-path", "./build/*", "-not", "-path", "./.git/*"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().split('\n')[:50]
    for line in lines:
        if line:
            click.echo(line)


@utils.command()
@click.argument('ticker')
@click.pass_context
def report(ctx, ticker):
    """Generate report for a ticker

    Generates a daily report analysis for the specified ticker symbol.

    Example:
      dr util report AAPL
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = [
        sys.executable, "-c",
        f"from src.agent import TickerAnalysisAgent; agent = TickerAnalysisAgent(); print(agent.analyze_ticker('{ticker}'))"
    ]

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env=env)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

    sys.exit(result.returncode)


@utils.command()
@click.pass_context
def report_all(ctx):
    """Generate all reports

    Runs generate_all_reports.py if it exists.
    """
    script = PROJECT_ROOT / "generate_all_reports.py"

    if not script.exists():
        click.echo("⚠ generate_all_reports.py not found")
        return

    use_doppler = ctx.obj.get('doppler', False)
    cmd = [sys.executable, str(script)]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


@utils.command()
def info():
    """Show project info and common commands

    Displays quick reference for the most common commands.
    """
    click.echo("📊 Daily Report LINE Bot\n")
    click.echo("Common commands:")
    click.echo("  dr dev server         - Run Flask server locally")
    click.echo("  dr test               - Run all tests")
    click.echo("  dr build              - Create Lambda deployment package")
    click.echo("  dr clean all          - Clean all build artifacts")
    click.echo("  dr check env          - Check environment variables")
    click.echo("")
    click.echo("For all commands: dr --help")
    click.echo("For command help: dr <command> --help")
