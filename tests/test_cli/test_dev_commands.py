# -*- coding: utf-8 -*-
"""Tests for dev commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


class TestDevCommands:
    """Tests for the dev command group"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing"""
        return CliRunner()

    def test_dev_help(self, runner):
        """Test dev command help"""
        result = runner.invoke(cli, ['dev', '--help'])

        assert result.exit_code == 0
        assert 'Development commands' in result.output
        assert 'server' in result.output
        assert 'shell' in result.output
        assert 'run' in result.output
        assert 'install' in result.output

    @patch('subprocess.run')
    def test_dev_server(self, mock_run, runner):
        """Test dev server command"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['dev', 'server'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'run_server.py' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_dev_server_with_doppler(self, mock_run, runner):
        """Test dev server command with doppler"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['--doppler', 'dev', 'server'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'doppler' in call_args
        assert 'run_server.py' in ' '.join(call_args)

    @patch('subprocess.run')
    def test_dev_shell(self, mock_run, runner):
        """Test dev shell command"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['dev', 'shell'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert '-i' in call_args

    @patch('subprocess.run')
    def test_dev_run_script(self, mock_run, runner):
        """Test dev run command with script"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['dev', 'run', 'scripts/test.py'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'scripts/test.py' in call_args

    @patch('subprocess.run')
    def test_dev_install(self, mock_run, runner):
        """Test dev install command"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['dev', 'install'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'pip' in call_args
        assert 'install' in call_args
        assert 'requirements.txt' in ' '.join(call_args)

    def test_dev_server_help(self, runner):
        """Test dev server command help"""
        result = runner.invoke(cli, ['dev', 'server', '--help'])

        assert result.exit_code == 0
        assert 'Run the Flask server locally' in result.output

    def test_dev_shell_help(self, runner):
        """Test dev shell command help"""
        result = runner.invoke(cli, ['dev', 'shell', '--help'])

        assert result.exit_code == 0
        assert 'interactive Python shell' in result.output

    def test_dev_run_help(self, runner):
        """Test dev run command help"""
        result = runner.invoke(cli, ['dev', 'run', '--help'])

        assert result.exit_code == 0
        assert 'Run a Python script' in result.output
