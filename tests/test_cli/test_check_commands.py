# -*- coding: utf-8 -*-
"""Tests for check commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


class TestCheckCommands:
    """Tests for the check command group"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing"""
        return CliRunner()

    def test_check_help(self, runner):
        """Test check command help"""
        result = runner.invoke(cli, ['check', '--help'])

        assert result.exit_code == 0
        assert 'Code quality and validation commands' in result.output
        assert 'syntax' in result.output
        assert 'env' in result.output
        assert 'format' in result.output
        assert 'lint' in result.output

    @patch('subprocess.run')
    @patch('pathlib.Path.rglob')
    def test_check_syntax(self, mock_rglob, mock_run, runner):
        """Test check syntax command"""
        # Mock some Python files
        mock_file = MagicMock()
        mock_file.__str__ = lambda self: 'src/test.py'
        mock_rglob.return_value = [mock_file]

        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['check', 'syntax'])

        assert result.exit_code == 0

    @patch.dict('dr_cli.commands.check.os.environ', {
        'OPENROUTER_API_KEY': 'test_key',
        'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
        'LINE_CHANNEL_SECRET': 'test_secret'
    })
    def test_check_env_all_set(self, runner):
        """Test check env command when all variables are set"""
        result = runner.invoke(cli, ['check', 'env'])

        assert result.exit_code == 0
        assert 'OPENROUTER_API_KEY' in result.output
        assert 'LINE_CHANNEL_ACCESS_TOKEN' in result.output
        assert 'LINE_CHANNEL_SECRET' in result.output

    @patch.dict('dr_cli.commands.check.os.environ', {}, clear=True)
    def test_check_env_missing_vars(self, runner):
        """Test check env command when variables are missing"""
        result = runner.invoke(cli, ['check', 'env'])

        assert result.exit_code == 1
        assert 'Not set' in result.output

    @patch('subprocess.run')
    def test_check_format(self, mock_run, runner):
        """Test check format command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='All done! ✨',
            stderr=''
        )

        result = runner.invoke(cli, ['check', 'format'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'black' in ' '.join(call_args)
        assert 'src/' in call_args
        assert 'tests/' in call_args

    @patch('subprocess.run')
    def test_check_format_with_line_length(self, mock_run, runner):
        """Test check format command with custom line length"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='All done! ✨',
            stderr=''
        )

        result = runner.invoke(cli, ['check', 'format', '--line-length', '120'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert '--line-length=120' in call_args

    @patch('subprocess.run')
    def test_check_format_not_installed(self, mock_run, runner):
        """Test check format command when black is not installed"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='No module named black'
        )

        result = runner.invoke(cli, ['check', 'format'])

        assert result.exit_code == 0
        assert 'not installed' in result.output

    @patch('subprocess.run')
    def test_check_lint(self, mock_run, runner):
        """Test check lint command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Your code has been rated at 10.00/10',
            stderr=''
        )

        result = runner.invoke(cli, ['check', 'lint'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'pylint' in ' '.join(call_args)
        assert 'src/' in call_args

    @patch('subprocess.run')
    def test_check_lint_not_installed(self, mock_run, runner):
        """Test check lint command when pylint is not installed"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='No module named pylint'
        )

        result = runner.invoke(cli, ['check', 'lint'])

        assert result.exit_code == 0
        assert 'not installed' in result.output

    def test_check_syntax_help(self, runner):
        """Test check syntax command help"""
        result = runner.invoke(cli, ['check', 'syntax', '--help'])

        assert result.exit_code == 0
        assert 'Check Python syntax' in result.output

    def test_check_env_help(self, runner):
        """Test check env command help"""
        result = runner.invoke(cli, ['check', 'env', '--help'])

        assert result.exit_code == 0
        assert 'Check environment variables' in result.output

    def test_check_format_help(self, runner):
        """Test check format command help"""
        result = runner.invoke(cli, ['check', 'format', '--help'])

        assert result.exit_code == 0
        assert 'Format code with black' in result.output
