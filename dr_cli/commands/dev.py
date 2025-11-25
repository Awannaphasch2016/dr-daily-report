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

    # Check if requirements.txt exists
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        click.echo("✅ requirements.txt found")
    else:
        click.echo("❌ requirements.txt not found")

    # Check Doppler if flag set
    if use_doppler:
        result = subprocess.run(["doppler", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ Doppler CLI available")
        else:
            click.echo("❌ Doppler CLI not found")

    # Check Docker for Telegram target
    if target in ['telegram', 'all']:
        result = subprocess.run(["docker", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ Docker available")
        else:
            click.echo("⚠️  Docker not found (needed for local DynamoDB)")

    click.echo()
    click.echo("=" * 50)
    click.echo("ℹ️  Run full verification: dr dev verify telegram")
    click.echo()
