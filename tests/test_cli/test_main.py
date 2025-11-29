# -*- coding: utf-8 -*-
"""Tests for main CLI entry point"""

import pytest
from click.testing import CliRunner
from dr_cli.main import cli


class TestCLIMain:
    """Tests for the main CLI entry point"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing"""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test that CLI help is displayed correctly"""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'DR CLI - Daily Report unified command interface' in result.output
        assert 'Commands:' in result.output

    def test_cli_without_command(self, runner):
        """Test CLI without any command shows help or error"""
        result = runner.invoke(cli, [])

        # Click returns exit code 0 for help, or 2 for missing command depending on configuration
        assert result.exit_code in [0, 2]

    def test_cli_with_doppler_flag(self, runner):
        """Test that --doppler flag is recognized"""
        result = runner.invoke(cli, ['--doppler', '--help'])

        assert result.exit_code == 0
        assert '--doppler' in result.output

    def test_cli_version_info(self, runner):
        """Test CLI version and description"""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'A clean, consistent interface' in result.output

    def test_all_command_groups_registered(self, runner):
        """Test that all command groups are registered"""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

        expected_commands = ['build', 'check', 'clean', 'deploy', 'dev', 'test', 'util']
        for cmd in expected_commands:
            assert cmd in result.output, f"Expected command '{cmd}' not found in help output"

    def test_invalid_command(self, runner):
        """Test that invalid command shows error"""
        result = runner.invoke(cli, ['invalid-command'])

        assert result.exit_code != 0
        assert 'No such command' in result.output or 'Error' in result.output
