"""Deployment commands"""

import click
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group()
@click.pass_context
def deploy(ctx):
    """Deployment commands - deploy to AWS, setup webhooks"""
    pass


@deploy.command()
@click.pass_context
def lambda_deploy(ctx):
    """Deploy to AWS Lambda

    Deploys the application to AWS Lambda.
    Requires AWS CLI to be configured with proper credentials.
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = ["bash", "scripts/create_lambda.sh"]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)


@deploy.command()
@click.pass_context
def webhook(ctx):
    """Setup LINE webhook configuration

    Helper script to configure LINE webhook settings.
    """
    use_doppler = ctx.obj.get('doppler', False)
    cmd = ["bash", "scripts/setup_line_webhook.sh"]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)
