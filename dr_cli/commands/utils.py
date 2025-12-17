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
@click.option('--strategy', type=click.Choice(['single-stage', 'multi-stage']), default='single-stage',
              help='Report generation strategy: single-stage (default) or multi-stage')
@click.option('--language', type=click.Choice(['th', 'en']), default='th',
              help='Report language: th (Thai, default) or en (English)')
@click.pass_context
def report(ctx, ticker, strategy, language):
    """Generate report for a ticker

    Generates a daily report analysis for the specified ticker symbol.

    Examples:
      dr util report DBS19                         # Thai, single-stage (defaults)
      dr util report DBS19 --language en           # English report
      dr util report DBS19 --strategy multi-stage  # Multi-stage Thai report
    """
    trace = ctx.obj.get('trace')

    cmd = [
        sys.executable, "-c",
        f"from src.agent import TickerAnalysisAgent; agent = TickerAnalysisAgent(); result = agent.analyze_ticker('{ticker}', strategy='{strategy}', language='{language}'); print(result['report'])"
    ]

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    # Control LangSmith tracing via CLI flag (overrides environment variable)
    if trace is True:
        env['LANGSMITH_TRACING_V2'] = 'true'
    elif trace is False:
        env['LANGSMITH_TRACING_V2'] = 'false'
    # If trace is None, use existing environment variable value

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
    sys.exit(result.returncode)


@utils.command()
@click.argument('ticker')
@click.option('--strategy', type=click.Choice(['single-stage', 'multi-stage']), default='single-stage',
              help='Report generation strategy: single-stage (default) or multi-stage')
@click.option('--language', type=click.Choice(['th', 'en']), default='th',
              help='Report language: th (Thai, default) or en (English)')
@click.option('--date', type=str, default=None,
              help='Report date (YYYY-MM-DD), defaults to today')
@click.pass_context
def report_cached(ctx, ticker, strategy, language, date):
    """Regenerate report from cached data (no API calls, no sink nodes)

    Uses existing data in Aurora to generate a new report. This is much faster
    and cheaper than live generation since it skips all API calls.

    Useful for:
    - Testing new prompts without refetching data
    - Comparing single-stage vs multi-stage on same data
    - Cost-efficient development iteration

    Examples:
      dr util report-cached DBS19                          # Regenerate with today's data
      dr util report-cached DBS19 --strategy multi-stage   # Try multi-stage on cached data
      dr util report-cached DBS19 --date 2024-01-15        # Use specific date's data
    """
    # Build Python command
    date_param = f"from datetime import datetime; data_date = datetime.strptime('{date}', '%Y-%m-%d').date(); " if date else "data_date = None; "

    cmd = [
        sys.executable, "-c",
        f"from src.data.aurora.precompute_service import PrecomputeService; "
        f"{date_param}"
        f"service = PrecomputeService(); "
        f"result = service.regenerate_report_from_cache('{ticker}', strategy='{strategy}', language='{language}', data_date=data_date); "
        f"print(f'\\n✅ Generated in {{result[\"generation_time_ms\"]}}ms\\n'); "
        f"print(result['report_text']); "
        f"print(f'\\n📊 LLM Calls: {{result.get(\"api_costs\", {{}}).get(\"llm_calls\", \"N/A\")}}') if 'api_costs' in result else None"
    ]

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    click.echo(f"🔄 Regenerating {strategy} report for {ticker} from cached data...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)

    if result.returncode != 0:
        click.echo(f"\n💡 Tip: Run 'dr util report {ticker}' first to populate cache")

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
