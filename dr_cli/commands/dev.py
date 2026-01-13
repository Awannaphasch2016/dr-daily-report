"""Development commands"""

import click
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group()
@click.pass_context
def dev(ctx):
    """Development commands - run server, shell, scripts"""
    pass


@dev.command()
@click.pass_context
def server(ctx):
    """Run the Flask server locally

    Starts the development server on localhost.
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = [sys.executable, "scripts/run_server.py"]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


@dev.command()
@click.argument('script')
@click.pass_context
def run(ctx, script):
    """Run a Python script with PYTHONPATH set

    Examples:
      dr dev run scripts/test.py
      dr dev run src/agent.py
    """
    use_doppler = ctx.obj.get('doppler', False)
    env = {"PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, script]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env={**env})
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env={**env})

    sys.exit(result.returncode)


@dev.command()
@click.pass_context
def shell(ctx):
    """Start interactive Python shell with project imports

    Opens a Python REPL with PYTHONPATH configured for project imports.
    """
    use_doppler = ctx.obj.get('doppler', False)
    env = {"PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, "-i"]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT, env={**env})
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, env={**env})

    sys.exit(result.returncode)


@dev.command()
@click.pass_context
def install(ctx):
    """Install project dependencies

    Installs packages from requirements.txt
    """
    cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    sys.exit(result.returncode)


@dev.command()
@click.argument('target', default='all', type=click.Choice(['all', 'telegram', 'line', 'db']))
@click.pass_context
def verify(ctx, target):
    """Verify development environment setup

    Checks that all required tools, dependencies, and services are properly
    configured for development.

    Examples:
      dr dev verify              # Check everything
      dr dev verify telegram     # Check Telegram Mini App setup
      dr dev verify line         # Check LINE bot setup
      dr --doppler dev verify    # Include API key checks
    """
    use_doppler = ctx.obj.get('doppler', False)

    # Run verification script
    if target == 'telegram':
        script_path = PROJECT_ROOT / "scripts" / "verify_telegram_setup.py"
    elif target == 'line':
        click.echo("LINE bot verification not yet implemented")
        sys.exit(0)
    elif target == 'db':
        script_path = PROJECT_ROOT / "scripts" / "verify_local_setup.sh"
        # Run bash script
        result = subprocess.run(["bash", str(script_path)], cwd=PROJECT_ROOT)
        sys.exit(result.returncode)
    else:  # 'all'
        script_path = PROJECT_ROOT / "scripts" / "verify_dev_setup.py"

    # Check if script exists
    if not script_path.exists():
        click.echo(f"⚠️  Verification script not found: {script_path}")
        click.echo(f"Creating placeholder...")
        # For now, fall back to basic check
        _basic_verify(target, use_doppler)
        return

    # Run Python verification script
    env = {"PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [sys.executable, str(script_path)]

    if use_doppler:
        env["USE_DOPPLER"] = "true"

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, env={**os.environ, **env})
    sys.exit(result.returncode)


@dev.command("langfuse-test")
@click.option('--ticker', default=None, help='Test with real ticker (requires Aurora)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.pass_context
def langfuse_test(ctx, ticker, verbose):
    """Test Langfuse tracing and scoring integration

    Runs an isolated test trace to verify Langfuse is configured correctly.
    Creates a 'test_scoring' trace with 5 quality scores.

    Examples:
      dr dev langfuse-test              # Test with mock data
      dr dev langfuse-test --verbose    # Show detailed scoring output
      dr dev langfuse-test --ticker DBS19  # Test with real ticker (needs Aurora)
    """
    import sys

    use_doppler = ctx.obj.get('doppler', False)

    if ticker:
        # Real ticker test (requires Aurora)
        click.echo(f"🔍 Testing Langfuse with real ticker: {ticker}")
        click.echo("   ⚠️  Requires Aurora connection")
        script = f'''
import logging
logging.basicConfig(level=logging.{"DEBUG" if verbose else "INFO"}, format="%(levelname)s - %(message)s")

for name in ["httpx", "httpcore", "urllib3", "boto3", "botocore", "langchain", "openai"]:
    logging.getLogger(name).setLevel(logging.ERROR)

from src.agent import TickerAnalysisAgent

agent = TickerAnalysisAgent()
result = agent.analyze_ticker("{ticker}")

print()
print("=" * 50)
print("RESULTS")
print("=" * 50)
print(f"Report: {{len(result.get('report', ''))}} chars")
print(f"Quality Scores: {{result.get('quality_scores', {{}})}}")
print(f"Error: {{result.get('error', '(none)')}}")
print()
print("Check Langfuse at: https://us.cloud.langfuse.com")
'''
    else:
        # Mock data test (no Aurora needed)
        click.echo("🧪 Testing Langfuse with mock data")
        click.echo("   Testing all trace columns: user_id, session_id, tags, metadata, scores")
        script = f'''
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.{"DEBUG" if verbose else "INFO"}, format="%(levelname)s - %(message)s")

from src.evaluation import observe, score_trace_batch, flush, get_langfuse_client, trace_context
from src.scoring.scoring_service import ScoringService, ScoringContext

# Verify Langfuse is configured
client = get_langfuse_client()
if not client:
    print("❌ Langfuse not configured!")
    print("   Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
    exit(1)

print("✅ Langfuse client initialized")

# Create mock context
context = ScoringContext(
    indicators={{"current_price": 100, "rsi": 55, "macd": 1.2}},
    percentiles={{"rsi_percentile": 45, "volume_percentile": 60}},
    news=[{{"title": "Test news", "summary": "Good quarterly results"}}],
    ticker_data={{"symbol": "TEST", "name": "Test Corporation", "sector": "Technology"}},
    market_conditions={{"uncertainty_score": 0.3, "volatility": "normal"}}
)

# Mock report
test_report = """
**สรุปวิเคราะห์ TEST**

ราคาปัจจุบัน: 100 บาท
RSI: 55 (อยู่ในระดับปกติ)
Volume: ปกติ

ข่าว: มีข่าวดีออกมาเกี่ยวกับผลประกอบการ

แนะนำ: ถือ
"""

@observe(name="test_scoring")
def run_test():
    # Use trace_context to set all Langfuse columns
    with trace_context(
        user_id="test_user_123",
        session_id=f"test_session_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}",
        tags=["test", "cli"],
        metadata={{
            "ticker": "TEST",
            "workflow": "langfuse_test",
            "model": "mock",
            "source": "dr_cli"
        }}
    ):
        print()
        print("Trace context set:")
        print("  user_id: test_user_123")
        print("  session_id: test_session_*")
        print("  tags: [test, cli]")
        print("  metadata: ticker=TEST, workflow=langfuse_test, model=mock, source=dr_cli")
        print()

        print("Computing quality scores (rule-based)...")
        service = ScoringService(enable_llm_scoring=True)
        scores = service.compute_all_quality_scores(test_report, context)

        print()
        print("Rule-based scores computed:")
        for name, result in scores.items():
            if hasattr(result, "overall_score"):
                print(f"  {{name}}: {{result.overall_score:.1f}}")

        # Push rule-based scores to Langfuse
        langfuse_scores = {{}}
        for name, result in scores.items():
            if hasattr(result, "overall_score"):
                langfuse_scores[name] = (result.overall_score, None)

        pushed = score_trace_batch(langfuse_scores)
        print()
        print(f"📊 Pushed {{pushed}} rule-based scores to Langfuse")

        # Compute LLM-as-judge scores (Two-Tier Framework)
        print()
        print("Computing LLM-as-judge scores...")
        llm_context = service.build_llm_scoring_context(
            report_text=test_report,
            ticker="TEST",
            context=context,
            query="Generate stock analysis report for TEST"
        )

        llm_scores = service.compute_llm_scores(llm_context)

        if llm_scores:
            print()
            print("LLM-as-judge scores computed:")
            for name, result in llm_scores.items():
                print(f"  {{name}}: {{result.value:.2f}}")

            # Push LLM scores to Langfuse
            llm_langfuse_scores = service.llm_scores_to_langfuse_format(llm_scores)
            llm_pushed = score_trace_batch(llm_langfuse_scores)
            print()
            print(f"📊 Pushed {{llm_pushed}} LLM-as-judge scores to Langfuse")
        else:
            print("⚠️  LLM scoring disabled or failed")

        return scores, llm_scores if llm_scores else {{}}

# Run test
scores = run_test()

# Flush to ensure sent
flush()

print()
print("=" * 50)
print("✅ Test complete!")
print()
print("Columns populated:")
print("  ✅ timestamp (automatic)")
print("  ✅ name: test_scoring")
print("  ✅ user_id: test_user_123")
print("  ✅ session_id: test_session_*")
print("  ✅ tags: [test, cli]")
print("  ✅ metadata: ticker, workflow, model, source")
print("  ✅ environment: via LANGFUSE_TRACING_ENVIRONMENT")
print("  ✅ rule-based scores: faithfulness, completeness, reasoning_quality, compliance, consistency")
print("  ✅ LLM-as-judge scores: hallucination, helpfulness, conciseness, answer_relevancy")
print()
print("View trace at: https://us.cloud.langfuse.com")
print("Look for trace named: test_scoring")
print("=" * 50)
'''

    # Run the script
    cmd = [sys.executable, "-c", script]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--config", "dev_local", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        click.echo("⚠️  Running without Doppler - Langfuse keys must be in environment")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


def _basic_verify(target, use_doppler):
    """Basic verification when full script not available"""
    click.echo("🔍 Basic Development Environment Check")
    click.echo("=" * 50)
    click.echo()

    # Check Python version
    py_version = sys.version_info
    if py_version.major == 3 and py_version.minor >= 11:
        click.echo(f"✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        click.echo(f"⚠️  Python {py_version.major}.{py_version.minor} (3.11+ recommended)")

    # === Virtual Environment Integrity Checks ===
    # See CLAUDE.md Principle #18: Shared Virtual Environment Pattern
    click.echo()
    click.echo("📦 Virtual Environment:")

    venv_path = PROJECT_ROOT / "venv"

    # Check 1: Symlink exists
    if venv_path.exists():
        if venv_path.is_symlink():
            target_path = venv_path.resolve()
            click.echo(f"✅ venv is symlink → {target_path}")

            # Check 2: Target exists
            if target_path.exists():
                click.echo(f"✅ Symlink target exists")
            else:
                click.echo(f"❌ Symlink target missing: {target_path}")
                click.echo(f"   Fix: Clone parent project or create isolated venv")

            # Check 3: Python path points to shared venv
            python_exe = Path(sys.executable)
            if str(target_path) in str(python_exe):
                click.echo(f"✅ Python path points to shared venv")
            else:
                click.echo(f"⚠️  Python path: {python_exe}")
                click.echo(f"   Expected: {target_path / 'bin' / 'python'}")

        else:
            click.echo(f"⚠️  venv exists but is NOT a symlink (isolated venv)")
            click.echo(f"   Location: {venv_path}")
    else:
        click.echo(f"❌ venv not found at: {venv_path}")
        click.echo(f"   Fix: source venv/bin/activate (if symlink) or python -m venv venv")

    # Check 4: DR CLI installed
    click.echo()
    click.echo("🛠️  DR CLI:")
    result = subprocess.run([sys.executable, "-m", "dr_cli", "--help"],
                          capture_output=True, text=True)
    if result.returncode == 0:
        click.echo("✅ DR CLI installed and working")
    else:
        click.echo("❌ DR CLI not found")
        click.echo("   Fix: pip install -e . (from project root)")

    # Check if requirements.txt exists
    click.echo()
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        click.echo("✅ requirements.txt found")
    else:
        click.echo("❌ requirements.txt not found")

    # Check Doppler if flag set
    if use_doppler:
        click.echo()
        result = subprocess.run(["doppler", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ Doppler CLI available")
        else:
            click.echo("❌ Doppler CLI not found")

    # Check Docker for Telegram target
    if target in ['telegram', 'all']:
        click.echo()
        result = subprocess.run(["docker", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ Docker available")
        else:
            click.echo("⚠️  Docker not found (needed for local DynamoDB)")

    click.echo()
    click.echo("=" * 50)
    click.echo("ℹ️  Run full verification: dr dev verify telegram")
    click.echo("ℹ️  See: CLAUDE.md Principle #18 for venv details")
    click.echo()
