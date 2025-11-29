# -*- coding: utf-8 -*-
"""Tests for clean commands"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from dr_cli.main import cli


class TestCleanCommands:
    """Tests for the clean command group"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing"""
        return CliRunner()

    def test_clean_help(self, runner):
        """Test clean command help"""
        result = runner.invoke(cli, ['clean', '--help'])

        assert result.exit_code == 0
        assert 'Cleanup commands' in result.output
        assert 'build' in result.output
        assert 'cache' in result.output
        assert 'all' in result.output

    def test_clean_without_subcommand(self, runner):
        """Test clean command without subcommand shows options"""
        result = runner.invoke(cli, ['clean'])

        assert result.exit_code == 0
        assert 'Available clean commands' in result.output

    @patch('shutil.rmtree')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_clean_build(self, mock_glob, mock_exists, mock_rmtree, runner):
        """Test clean build command"""
        mock_exists.return_value = True
        mock_glob.return_value = []

        result = runner.invoke(cli, ['clean', 'build'])

        assert result.exit_code == 0
        assert 'cleaned' in result.output.lower()

    @patch('shutil.rmtree')
    @patch('pathlib.Path.rglob')
    def test_clean_cache(self, mock_rglob, mock_rmtree, runner):
        """Test clean cache command"""
        mock_rglob.return_value = []

        result = runner.invoke(cli, ['clean', 'cache'])

        assert result.exit_code == 0
        assert 'cleaned' in result.output.lower()

    @patch('shutil.rmtree')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    @patch('pathlib.Path.rglob')
    @patch('pathlib.Path.unlink')
    def test_clean_all(self, mock_unlink, mock_rglob, mock_glob, mock_exists, mock_rmtree, runner):
        """Test clean all command"""
        mock_exists.return_value = True
        mock_glob.return_value = []
        mock_rglob.return_value = []

        result = runner.invoke(cli, ['clean', 'all'])

        assert result.exit_code == 0
        assert 'cleaned' in result.output.lower()

    def test_clean_build_help(self, runner):
        """Test clean build command help"""
        result = runner.invoke(cli, ['clean', 'build', '--help'])

        assert result.exit_code == 0
        assert 'Clean build artifacts' in result.output

    def test_clean_cache_help(self, runner):
        """Test clean cache command help"""
        result = runner.invoke(cli, ['clean', 'cache', '--help'])

        assert result.exit_code == 0
        assert 'Clean Python cache' in result.output

    def test_clean_all_help(self, runner):
        """Test clean all command help"""
        result = runner.invoke(cli, ['clean', 'all', '--help'])

        assert result.exit_code == 0
        assert 'Clean everything' in result.output
