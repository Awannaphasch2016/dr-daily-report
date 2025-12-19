#!/usr/bin/env python3
"""
DR CLI - Main entry point

Two-layer design:
- Justfile: Intent-based recipes (WHEN/WHY to run commands)
- CLI: Clean syntax and implementation (HOW to run commands)
"""

import sys
import os
import subprocess
from pathlib import Path
import click

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()


def run_with_doppler(cmd: list[str], project: str = "rag-chatbot-worktree", config: str = "dev_personal"):
    """Wrap command with doppler run"""
    doppler_cmd = ["doppler", "run", "--project", project, "--config", config, "--"]
    return subprocess.run(doppler_cmd + cmd, cwd=PROJECT_ROOT)


def run_command(cmd: list[str], use_doppler: bool = False):
    """Execute a command, optionally with doppler"""
    if use_doppler:
        result = run_with_doppler(cmd)
    else:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


@click.group()
@click.pass_context
def cli(ctx):
    """DR CLI - Daily Report unified command interface

    A clean, consistent interface for all repository operations.
    Use 'dr <command> --help' to see detailed help for each command.

    Note: Environment variables should be provided via 'doppler run -- dr <command>'
    """
    ctx.ensure_object(dict)


# Import command groups
from dr_cli.commands import dev, test, build, deploy, clean, check, utils

cli.add_command(dev.dev)
cli.add_command(test.test)
cli.add_command(build.build_cmd)
cli.add_command(deploy.deploy)
cli.add_command(clean.clean)
cli.add_command(check.check)
cli.add_command(utils.utils)


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == '__main__':
    main()
