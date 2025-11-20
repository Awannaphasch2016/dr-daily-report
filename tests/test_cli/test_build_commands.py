"""Tests for build commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


def test_build_help(runner):
    """Test build command help"""
    result = runner.invoke(cli, ['build', '--help'])
    assert result.exit_code == 0
    assert 'Create Lambda deployment package' in result.output
    assert '--minimal' in result.output
    assert '--type' in result.output


@patch('subprocess.run')
def test_build_default(mock_run, runner):
    """Test build command default behavior"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['build'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'deploy.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_build_minimal(mock_run, runner):
    """Test build command with --minimal flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['build', '--minimal'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'create_lambda_minimal.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_build_type_lambda(mock_run, runner):
    """Test build command with --type lambda"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['build', '--type', 'lambda'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'create_lambda.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_build_type_standard(mock_run, runner):
    """Test build command with --type standard"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['build', '--type', 'standard'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'deploy.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_build_with_doppler(mock_run, runner):
    """Test build command with doppler flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'build'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args


def test_build_invalid_type(runner):
    """Test build command with invalid type"""
    result = runner.invoke(cli, ['build', '--type', 'invalid'])
    assert result.exit_code != 0
