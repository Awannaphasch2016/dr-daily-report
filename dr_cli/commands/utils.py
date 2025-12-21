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

    Generates a daily report analysis for the specified ticker symbol (Thai only).
    Uses Semantic Layer Architecture (three-layer pattern).

    Examples:
      dr util report DBS19
    """
    trace = ctx.obj.get('trace')

    cmd = [
        sys.executable, "-c",
        f"from src.agent import TickerAnalysisAgent; agent = TickerAnalysisAgent(); result = agent.analyze_ticker('{ticker}'); print(result['report'])"
    ]

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env)
    sys.exit(result.returncode)


@utils.command()
@click.argument('ticker')
@click.option('--date', type=str, default=None,
              help='Report date (YYYY-MM-DD), defaults to today')
@click.pass_context
def report_cached(ctx, ticker, date):
    """Regenerate report from cached data (no API calls, no sink nodes)

    Uses existing data in Aurora to generate a new report. This is much faster
    and cheaper than live generation since it skips all API calls.
    Uses Semantic Layer Architecture (three-layer pattern).

    Useful for:
    - Testing new prompts without refetching data
    - Cost-efficient development iteration

    Examples:
      dr util report-cached DBS19                   # Regenerate with today's data
      dr util report-cached DBS19 --date 2024-01-15 # Use specific date's data
    """
    # Build Python command
    date_param = f"from datetime import datetime; data_date = datetime.strptime('{date}', '%Y-%m-%d').date(); " if date else "data_date = None; "

    cmd = [
        sys.executable, "-c",
        f"from src.data.aurora.precompute_service import PrecomputeService; "
        f"{date_param}"
        f"service = PrecomputeService(); "
        f"result = service.regenerate_report_from_cache('{ticker}', data_date=data_date); "
        f"print(f'\\n✅ Generated in {{result[\"generation_time_ms\"]}}ms\\n'); "
        f"print(result['report_text']); "
        f"print(f'\\n📊 LLM Calls: {{result.get(\"api_costs\", {{}}).get(\"llm_calls\", \"N/A\")}}') if 'api_costs' in result else None"
    ]

    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    click.echo(f"🔄 Regenerating report for {ticker} from cached data...")
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


@utils.command(name='prompt-vars')
@click.argument('ticker')
@click.option('--output', type=click.Path(), default=None,
              help='Save output to file (optional)')
@click.pass_context
def prompt_vars(ctx, ticker, output):
    """Inspect prompt variables for a ticker (useful for prompt debugging)

    Builds the prompt context without generating the full report, displaying
    all template variables in a clean, readable format.
    Uses Semantic Layer Architecture (three-layer pattern).

    Examples:
      dr util prompt-vars DBS19                   # Inspect prompt
      dr util prompt-vars DBS19 --output prompt.txt  # Save to file
    """
    trace = ctx.obj.get('trace')
    
    # Create a Python script to inspect prompt variables
    script_content = f'''import sys
import os
sys.path.insert(0, r"{PROJECT_ROOT}")
from src.agent import TickerAnalysisAgent

# Initialize agent (this sets up all components)
agent = TickerAnalysisAgent()

# Run workflow up to data collection (before LLM call)
initial_state = {{
    "messages": [],
    "ticker": "{ticker}",
    "ticker_data": {{}},
    "indicators": {{}},
    "percentiles": {{}},
    "chart_patterns": [],
    "pattern_statistics": {{}},
    "strategy_performance": {{}},
    "news": [],
    "news_summary": {{}},
    "comparative_data": {{}},
    "comparative_insights": {{}},
    "chart_base64": "",
    "report": "",
    "faithfulness_score": {{}},
    "completeness_score": {{}},
    "reasoning_quality_score": {{}},
    "compliance_score": {{}},
    "qos_score": {{}},
    "cost_score": {{}},
    "timing_metrics": {{}},
    "api_costs": {{}},
    "database_metrics": {{}},
    "sec_filing_data": {{}},
    "financial_markets_data": {{}},
    "portfolio_insights": {{}},
    "alpaca_data": {{}},
    "error": ""
}}

# Run workflow nodes to collect data
try:
    state = agent.workflow_nodes.fetch_data(initial_state)
    if state.get("error"):
        print(f"❌ Error fetching data: {{state.get('error')}}", file=sys.stderr)
        sys.exit(1)

    # Merge partial state (analyze_technical returns only modified fields)
    partial_state = agent.workflow_nodes.analyze_technical(state)
    state.update(partial_state)
    if state.get("error"):
        print(f"❌ Error analyzing technical: {{state.get('error')}}", file=sys.stderr)
        sys.exit(1)

    # Merge partial state (fetch_news returns only modified fields)
    partial_state = agent.workflow_nodes.fetch_news(state)
    state.update(partial_state)
    if state.get("error"):
        print(f"❌ Error fetching news: {{state.get('error')}}", file=sys.stderr)
        sys.exit(1)

    # Fetch comparative data first (required for insights)
    partial_state = agent.workflow_nodes.fetch_comparative_data(state)
    state.update(partial_state)
    if state.get("error"):
        print(f"❌ Error fetching comparative: {{state.get('error')}}", file=sys.stderr)
        sys.exit(1)

    # Analyze comparative insights (returns only modified fields)
    partial_state = agent.workflow_nodes.analyze_comparative_insights(state)
    state.update(partial_state)
    if state.get("error"):
        print(f"❌ Error analyzing comparative: {{state.get('error')}}", file=sys.stderr)
        sys.exit(1)

    # Build context and prompt (without LLM call)
    ticker_data = state.get("ticker_data", {{}})
    indicators = state.get("indicators", {{}})
    percentiles = state.get("percentiles", {{}})
    news = state.get("news", [])
    news_summary = state.get("news_summary", {{}})
    strategy_performance = state.get("strategy_performance", {{}})
    comparative_insights = state.get("comparative_insights", {{}})
    sec_filing_data = state.get("sec_filing_data", {{}})
    financial_markets_data = state.get("financial_markets_data", {{}})
    portfolio_insights = state.get("portfolio_insights", {{}})
    alpaca_data = state.get("alpaca_data", {{}})

    # Build context
    context = agent.context_builder.prepare_context(
        "{ticker}",
        ticker_data,
        indicators,
        percentiles,
        news,
        news_summary,
        strategy_performance=strategy_performance,
        comparative_insights=comparative_insights,
        sec_filing_data=sec_filing_data if sec_filing_data else None,
        financial_markets_data=financial_markets_data if financial_markets_data else None,
        portfolio_insights=portfolio_insights if portfolio_insights else None,
        alpaca_data=alpaca_data if alpaca_data else None
    )

    # Calculate ground truth from indicators (same as workflow_nodes.py)
    from src.analysis.market_analyzer import MarketAnalyzer
    market_analyzer = MarketAnalyzer()
    conditions = market_analyzer.calculate_market_conditions(indicators)

    ground_truth = {{
        'uncertainty_score': indicators.get('uncertainty_score', 0),
        'atr_pct': (indicators.get('atr', 0) / indicators.get('current_price', 1)) * 100
                   if indicators.get('current_price', 0) > 0 else 0,
        'vwap_pct': conditions.get('price_vs_vwap_pct', 0),
        'volume_ratio': conditions.get('volume_ratio', 0),
    }}

    # Build final prompt using v4 minimal template with dynamic filtering
    final_prompt = agent.prompt_builder.build_prompt(
        "{ticker}",
        context,
        ground_truth=ground_truth,
        indicators=indicators,
        percentiles=percentiles,
        ticker_data=ticker_data,
        strategy_performance=strategy_performance,
        comparative_insights=comparative_insights,
        sec_filing_data=sec_filing_data if sec_filing_data else None,
        financial_markets_data=financial_markets_data if financial_markets_data else None,
        portfolio_insights=portfolio_insights if portfolio_insights else None,
        alpaca_data=alpaca_data if alpaca_data else None
    )

    # Calculate token estimate
    token_count = len(final_prompt) // 4

    # Display output
    print("━" * 80)
    print("📝 PROMPT INSPECTION (Semantic Layer Architecture)")
    print("━" * 80)
    print(f"Ticker: {ticker}")
    print(f"Token Estimate: ~{{token_count}} tokens")
    print("━" * 80)
    print()
    print("FULL PROMPT TO LLM:")
    print("━" * 80)
    print(final_prompt)
    print()
    print("━" * 80)
    print(f"✅ Total: {{len(final_prompt)}} chars (~{{token_count}} tokens)")
    print("━" * 80)
    print()
except Exception as e:
    import traceback
    print(f"❌ Error: {{e}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''
    
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    # Run command and capture output
    result = subprocess.run(
        [sys.executable, "-c", script_content],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        sys.exit(result.returncode)
    
    output_text = result.stdout
    
    # Save to file if requested
    if output:
        output_path = Path(output)
        output_path.write_text(output_text, encoding='utf-8')
        click.echo(f"✅ Output saved to {output_path}")
    else:
        click.echo(output_text)
