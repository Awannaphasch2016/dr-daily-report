"""Build commands"""

import click
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.command(name='build')
@click.option('--minimal', is_flag=True, help='Create minimal Lambda package')
@click.option('--type', 'build_type', type=click.Choice(['standard', 'lambda']), default='standard',
              help='Build type: standard or lambda')
@click.pass_context
def build_cmd(ctx, minimal, build_type):
    """Create Lambda deployment package

    Builds a deployment package for AWS Lambda.

    Options:
      --minimal    Create minimal package (smaller size)
      --type       Choose build type (standard or lambda)

    Examples:
      dr build                    # Standard build
      dr build --minimal          # Minimal build
      dr build --type lambda      # Lambda-specific build
    """
    use_doppler = ctx.obj.get('doppler', False)

    if minimal:
        script = "scripts/create_lambda_minimal.sh"
    elif build_type == 'lambda':
        script = "scripts/create_lambda.sh"
    else:
        script = "scripts/deploy.sh"

    cmd = ["bash", script]

    if use_doppler:
        doppler_cmd = ["doppler", "run", "--project", "rag-chatbot-worktree", "--config", "dev_personal", "--"]
        result = subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    sys.exit(result.returncode)
