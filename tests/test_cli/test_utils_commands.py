# -*- coding: utf-8 -*-
"""Tests for utils commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


class TestUtilsCommands:
    """Tests for the utils command group"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing"""
        return CliRunner()

    def test_utils_help(self, runner):
        """Test util command help"""
        result = runner.invoke(cli, ['util', '--help'])

        assert result.exit_code == 0
        assert 'Utility commands' in result.output
        assert 'tree' in result.output
        assert 'stats' in result.output
        assert 'report' in result.output
        assert 'info' in result.output

    @patch('subprocess.run')
    def test_utils_tree(self, mock_run, runner):
        """Test util tree command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='.\n├── src/\n└── tests/'
        )

        result = runner.invoke(cli, ['util', 'tree'])

        assert mock_run.called

    @patch('subprocess.run')
    def test_utils_stats(self, mock_run, runner):
        """Test util stats command"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout='./src/agent.py\n./src/workflow.py'),
            MagicMock(returncode=0, stdout='  100 ./src/agent.py\n  200 ./src/workflow.py\n  300 total')
        ]

        result = runner.invoke(cli, ['util', 'stats'])

        assert result.exit_code == 0

    @patch('subprocess.run')
    def test_utils_list_py(self, mock_run, runner):
        """Test util list-py command"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='./src/agent.py\n./src/workflow.py'
        )

        result = runner.invoke(cli, ['util', 'list-py'])

        assert result.exit_code == 0

    @patch('subprocess.run')
    def test_utils_report(self, mock_run, runner):
        """Test util report command"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['util', 'report', 'AAPL'])

        assert mock_run.called
        call_args = str(mock_run.call_args[0][0])
        assert 'AAPL' in call_args

    @patch('subprocess.run')
    def test_utils_report_with_doppler(self, mock_run, runner):
        """Test util report command with doppler"""
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['--doppler', 'util', 'report', 'GOOGL'])

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert 'doppler' in call_args
        assert 'GOOGL' in str(call_args)

    @patch('pathlib.Path.exists')
    def test_utils_report_all_script_not_found(self, mock_exists, runner):
        """Test util report-all command when script doesn't exist"""
        mock_exists.return_value = False

        result = runner.invoke(cli, ['util', 'report-all'])

        assert result.exit_code == 0
        assert 'not found' in result.output

    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_utils_report_all(self, mock_run, mock_exists, runner):
        """Test util report-all command"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(cli, ['util', 'report-all'])

        assert mock_run.called

    def test_utils_info(self, runner):
        """Test util info command"""
        result = runner.invoke(cli, ['util', 'info'])

        assert result.exit_code == 0
        assert 'Daily Report LINE Bot' in result.output
        assert 'Common commands' in result.output

    def test_utils_tree_help(self, runner):
        """Test util tree command help"""
        result = runner.invoke(cli, ['util', 'tree', '--help'])

        assert result.exit_code == 0
        assert 'Show project structure' in result.output

    def test_utils_stats_help(self, runner):
        """Test util stats command help"""
        result = runner.invoke(cli, ['util', 'stats', '--help'])

        assert result.exit_code == 0
        assert 'Count lines of code' in result.output

    def test_utils_report_help(self, runner):
        """Test util report command help"""
        result = runner.invoke(cli, ['util', 'report', '--help'])

        assert result.exit_code == 0
        assert 'Generate report for a ticker' in result.output

    def test_utils_info_help(self, runner):
        """Test util info command help"""
        result = runner.invoke(cli, ['util', 'info', '--help'])

        assert result.exit_code == 0
        assert 'Show project info' in result.output
