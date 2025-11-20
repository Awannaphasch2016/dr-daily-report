"""Tests for test commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


def test_test_help(runner):
    """Test test command help"""
    result = runner.invoke(cli, ['test', '--help'])
    assert result.exit_code == 0
    assert 'Testing commands' in result.output
    assert 'all' in result.output
    assert 'file' in result.output
    assert 'line' in result.output


@patch('subprocess.run')
def test_test_default(mock_run, runner):
    """Test test command without subcommand runs all tests"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'pytest' in ' '.join(call_args)
    assert 'tests/' in ' '.join(call_args)


@patch('subprocess.run')
def test_test_all(mock_run, runner):
    """Test test all command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'all'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'pytest' in ' '.join(call_args)
    assert 'tests/' in ' '.join(call_args)


@patch('subprocess.run')
def test_test_all_verbose(mock_run, runner):
    """Test test all command with verbose flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'all', '-v'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert '-v' in call_args


@patch('subprocess.run')
def test_test_file(mock_run, runner):
    """Test test file command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'file', 'test_agent.py'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'pytest' in ' '.join(call_args)
    assert 'test_agent.py' in ' '.join(call_args)


@patch('subprocess.run')
def test_test_line_follow(mock_run, runner):
    """Test test line command with follow type"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'line', 'follow'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'test_line_follow.py' in ' '.join(call_args)


@patch('subprocess.run')
def test_test_line_help(mock_run, runner):
    """Test test line command with help type"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'line', 'help'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'test_line_help.py' in ' '.join(call_args)


@patch('subprocess.run')
def test_test_line_cache(mock_run, runner):
    """Test test line command with cache type"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'line', 'cache'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'test_caching.py' in ' '.join(call_args)


def test_test_line_invalid_type(runner):
    """Test test line command with invalid type"""
    result = runner.invoke(cli, ['test', 'line', 'invalid'])
    assert result.exit_code != 0


@patch('subprocess.run')
def test_test_message(mock_run, runner):
    """Test test message command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'message', 'AAPL'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'test_line_message.py' in ' '.join(call_args)
    assert 'AAPL' in call_args


@patch('subprocess.run')
def test_test_integration(mock_run, runner):
    """Test test integration command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['test', 'integration', 'GOOGL'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'test_line_integration.py' in ' '.join(call_args)
    assert 'GOOGL' in call_args


@patch('subprocess.run')
def test_test_with_doppler(mock_run, runner):
    """Test test command with doppler flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'test'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
