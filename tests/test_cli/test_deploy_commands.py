"""Tests for deploy commands"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from dr_cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


def test_deploy_help(runner):
    """Test deploy command help"""
    result = runner.invoke(cli, ['deploy', '--help'])
    assert result.exit_code == 0
    assert 'Deployment commands' in result.output
    assert 'lambda-deploy' in result.output
    assert 'webhook' in result.output


@patch('subprocess.run')
def test_deploy_lambda(mock_run, runner):
    """Test deploy lambda-deploy command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['deploy', 'lambda-deploy'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'create_lambda.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_deploy_lambda_with_doppler(mock_run, runner):
    """Test deploy lambda-deploy command with doppler"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'deploy', 'lambda-deploy'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'create_lambda.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_deploy_webhook(mock_run, runner):
    """Test deploy webhook command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['deploy', 'webhook'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'bash' in call_args
    assert 'setup_line_webhook.sh' in ' '.join(call_args)


@patch('subprocess.run')
def test_deploy_webhook_with_doppler(mock_run, runner):
    """Test deploy webhook command with doppler"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'deploy', 'webhook'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'setup_line_webhook.sh' in ' '.join(call_args)


def test_deploy_lambda_help(runner):
    """Test deploy lambda-deploy command help"""
    result = runner.invoke(cli, ['deploy', 'lambda-deploy', '--help'])
    assert result.exit_code == 0
    assert 'Deploy to AWS Lambda' in result.output


def test_deploy_webhook_help(runner):
    """Test deploy webhook command help"""
    result = runner.invoke(cli, ['deploy', 'webhook', '--help'])
    assert result.exit_code == 0
    assert 'Setup LINE webhook' in result.output
