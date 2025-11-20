"""Cleanup commands"""

import click
import subprocess
import sys
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


@click.group(invoke_without_command=True)
@click.pass_context
def clean(ctx):
    """Cleanup commands - remove build artifacts, cache, etc.

    Running 'dr clean' without subcommands shows available options.
    """
    if ctx.invoked_subcommand is None:
        click.echo("Available clean commands:")
        click.echo("  dr clean build     - Remove build artifacts")
        click.echo("  dr clean cache     - Remove Python cache files")
        click.echo("  dr clean all       - Remove everything")


@clean.command()
def build():
    """Clean build artifacts

    Removes build/ directory and *.zip files.
    """
    build_dir = PROJECT_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        click.echo("✓ Removed build/ directory")

    for zip_file in PROJECT_ROOT.glob("*.zip"):
        zip_file.unlink()
        click.echo(f"✓ Removed {zip_file.name}")

    click.echo("✓ Build artifacts cleaned")


@clean.command()
def cache():
    """Clean Python cache files

    Removes __pycache__ directories and .pyc files.
    """
    # Remove __pycache__ directories
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)

    # Remove .pyc files
    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        pyc.unlink()

    click.echo("✓ Python cache cleaned")


@clean.command()
def all():
    """Clean everything - build artifacts, cache, test artifacts

    Comprehensive cleanup of all generated files.
    """
    # Build artifacts
    build_dir = PROJECT_ROOT / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    for zip_file in PROJECT_ROOT.glob("*.zip"):
        zip_file.unlink()

    # Python cache
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)

    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        pyc.unlink()

    # Test artifacts
    pytest_cache = PROJECT_ROOT / ".pytest_cache"
    if pytest_cache.exists():
        shutil.rmtree(pytest_cache)

    coverage_file = PROJECT_ROOT / ".coverage"
    if coverage_file.exists():
        coverage_file.unlink()

    htmlcov = PROJECT_ROOT / "htmlcov"
    if htmlcov.exists():
        shutil.rmtree(htmlcov)

    click.echo("✓ All artifacts cleaned")
