"""Deployment commands"""

import click
import subprocess
import sys
import os
import json
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


@deploy.command('sync-env')
@click.argument('function')
@click.option('--dry-run', is_flag=True, help='Show what would be synced without applying')
@click.pass_context
def sync_env(ctx, function, dry_run):
    """Sync Doppler secrets to Lambda environment variables

    Reads secrets from Doppler and updates Lambda env vars via AWS API.
    Must be run with --doppler flag.

    FUNCTION is the Lambda function name (required).

    Examples:

        dr --doppler deploy sync-env dr-daily-report-telegram-api-dev

        dr --doppler deploy sync-env dr-daily-report-telegram-api-dev --dry-run

        dr --doppler deploy sync-env line-bot-ticker-report
    """
    # Check --doppler flag was used
    if not os.environ.get('OPENROUTER_API_KEY'):
        click.echo("❌ Error: Must run with --doppler flag")
        click.echo("   Usage: dr --doppler deploy sync-env <FUNCTION>")
        sys.exit(1)

    # 1. Get current Lambda env vars
    click.echo(f"📥 Fetching current env vars from Lambda: {function}")
    result = subprocess.run(
        ['aws', 'lambda', 'get-function-configuration',
         '--function-name', function,
         '--query', 'Environment.Variables'],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        click.echo(f"❌ Failed to get Lambda configuration: {result.stderr}")
        sys.exit(1)

    current_env = json.loads(result.stdout) if result.stdout.strip() else {}

    # 2. Build secrets to sync from Doppler env vars
    secrets_to_sync = {
        'OPENAI_API_KEY': os.environ.get('OPENROUTER_API_KEY'),
    }
    # Filter out None/empty values
    secrets_to_sync = {k: v for k, v in secrets_to_sync.items() if v}

    if not secrets_to_sync:
        click.echo("⚠️  No secrets found in Doppler to sync")
        sys.exit(0)

    # 3. Merge (keep existing, update from Doppler)
    merged_env = {**current_env, **secrets_to_sync}

    # 4. Show diff
    click.echo(f"\n🔄 Syncing {len(secrets_to_sync)} secret(s) to Lambda: {function}")
    for key in secrets_to_sync:
        old_val = current_env.get(key, '<not set>')
        new_val = secrets_to_sync[key]
        # Mask values for display
        masked_old = old_val[:12] + '...' if len(old_val) > 12 else old_val
        masked_new = new_val[:8] + '...' if len(new_val) > 8 else new_val
        click.echo(f"   {key}: {masked_old} → {masked_new}")

    # 5. Apply if not dry-run
    if dry_run:
        click.echo("\n🔍 Dry run - no changes applied")
    else:
        click.echo("\n📤 Updating Lambda environment...")
        # AWS CLI needs the environment as a proper JSON structure
        env_structure = {"Variables": merged_env}
        env_json = json.dumps(env_structure)
        result = subprocess.run([
            'aws', 'lambda', 'update-function-configuration',
            '--function-name', function,
            '--environment', env_json
        ], capture_output=True, text=True)

        if result.returncode == 0:
            click.echo("✅ Lambda environment updated successfully")
        else:
            click.echo(f"❌ Failed: {result.stderr}")
            sys.exit(1)
