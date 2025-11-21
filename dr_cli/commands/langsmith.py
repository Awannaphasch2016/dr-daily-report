"""LangSmith data retrieval commands"""

import click
import sys
import subprocess
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


def run_langsmith_command(ctx, command: str, extra_args: list = None) -> int:
    """
    Execute a langsmith command via subprocess, wrapping with doppler if needed.

    Args:
        ctx: Click context
        command: Command name (list-runs, show-run, show-feedback, stats, projects)
        extra_args: Additional arguments to pass to the runner

    Returns:
        Exit code
    """
    use_doppler = ctx.obj.get('doppler', False)

    # Build command list
    cmd = [
        sys.executable,
        '-m',
        'dr_cli.commands.langsmith_runner',
        '--command',
        command
    ]

    # Add extra arguments
    if extra_args:
        cmd.extend(extra_args)

    # Wrap with doppler if needed
    if use_doppler:
        doppler_cmd = [
            'doppler', 'run',
            '--project', 'rag-chatbot-worktree',
            '--config', 'dev_personal',
            '--'
        ]
        cmd = doppler_cmd + cmd

    # Execute command
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


@click.group(name='langsmith')
@click.pass_context
def langsmith_group(ctx):
    """LangSmith trace and feedback management

    Retrieve and analyze traces, feedback, and statistics from LangSmith.

    Examples:
      dr --doppler langsmith list-runs
      dr --doppler langsmith show-feedback <run_id>
      dr --doppler langsmith stats
    """
    pass


@langsmith_group.command('list-runs')
@click.option('--limit', default=10, type=int, help='Number of runs to show')
@click.option('--project', default='default', help='Project name')
@click.option('--hours', default=24, type=int, help='Look back hours')
@click.pass_context
def list_runs(ctx, limit, project, hours):
    """List recent traces with feedback summary

    Shows recent traces from LangSmith with their basic information
    and feedback counts.

    Example:
      dr --doppler langsmith list-runs --limit 5 --hours 2
    """
    extra_args = [
        '--limit', str(limit),
        '--project', project,
        '--hours', str(hours)
    ]
    sys.exit(run_langsmith_command(ctx, 'list-runs', extra_args))


@langsmith_group.command('show-run')
@click.argument('run_id')
@click.pass_context
def show_run(ctx, run_id):
    """Show detailed information about a specific trace

    Displays comprehensive information including inputs, outputs,
    child spans, and feedback summary.

    Example:
      dr --doppler langsmith show-run 224f0a87-a325-4945-808f-4a8e1c3fa823
    """
    extra_args = ['--run-id', run_id]
    sys.exit(run_langsmith_command(ctx, 'show-run', extra_args))


@langsmith_group.command('show-feedback')
@click.argument('run_id')
@click.pass_context
def show_feedback(ctx, run_id):
    """Show evaluation feedback for a trace

    Displays all 6 evaluation scores with detailed breakdowns
    showing metric components.

    Example:
      dr --doppler langsmith show-feedback 224f0a87-a325-4945-808f-4a8e1c3fa823
    """
    extra_args = ['--run-id', run_id]
    sys.exit(run_langsmith_command(ctx, 'show-feedback', extra_args))


@langsmith_group.command('stats')
@click.option('--limit', default=50, type=int, help='Number of runs to analyze')
@click.option('--hours', default=24, type=int, help='Look back hours')
@click.option('--project', default='default', help='Project name')
@click.pass_context
def stats(ctx, limit, hours, project):
    """Show aggregate statistics across recent traces

    Calculates average scores, min/max values, and performance metrics
    across recent traces with feedback.

    Example:
      dr --doppler langsmith stats --limit 100 --hours 48
    """
    extra_args = [
        '--limit', str(limit),
        '--hours', str(hours),
        '--project', project
    ]
    sys.exit(run_langsmith_command(ctx, 'stats', extra_args))


@langsmith_group.command('projects')
@click.pass_context
def projects(ctx):
    """List available LangSmith projects

    Shows all projects accessible with the current API key.

    Example:
      dr --doppler langsmith projects
    """
    sys.exit(run_langsmith_command(ctx, 'projects'))
