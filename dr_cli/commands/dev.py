"""Development commands"""

import click
import subprocess
import sys
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
