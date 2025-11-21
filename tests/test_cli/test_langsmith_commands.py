"""Tests for LangSmith commands"""

import pytest
from unittest.mock import patch, MagicMock, call
from click.testing import CliRunner
from dr_cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess.run"""
    mock = MagicMock()
    mock.return_value = MagicMock(returncode=0)
    return mock


# ============================================
# Help Commands Tests
# ============================================

def test_langsmith_help(runner):
    """Test langsmith command group help"""
    result = runner.invoke(cli, ['langsmith', '--help'])
    assert result.exit_code == 0
    assert 'LangSmith trace and feedback management' in result.output
    assert 'list-runs' in result.output
    assert 'show-run' in result.output
    assert 'show-feedback' in result.output
    assert 'stats' in result.output
    assert 'projects' in result.output


def test_langsmith_list_runs_help(runner):
    """Test langsmith list-runs help"""
    result = runner.invoke(cli, ['langsmith', 'list-runs', '--help'])
    assert result.exit_code == 0
    assert 'List recent traces' in result.output
    assert '--limit' in result.output
    assert '--project' in result.output
    assert '--hours' in result.output


def test_langsmith_show_run_help(runner):
    """Test langsmith show-run help"""
    result = runner.invoke(cli, ['langsmith', 'show-run', '--help'])
    assert result.exit_code == 0
    assert 'Show detailed information' in result.output


def test_langsmith_show_feedback_help(runner):
    """Test langsmith show-feedback help"""
    result = runner.invoke(cli, ['langsmith', 'show-feedback', '--help'])
    assert result.exit_code == 0
    assert 'Show evaluation feedback' in result.output


def test_langsmith_stats_help(runner):
    """Test langsmith stats help"""
    result = runner.invoke(cli, ['langsmith', 'stats', '--help'])
    assert result.exit_code == 0
    assert 'Show aggregate statistics' in result.output
    assert '--limit' in result.output
    assert '--hours' in result.output


def test_langsmith_projects_help(runner):
    """Test langsmith projects help"""
    result = runner.invoke(cli, ['langsmith', 'projects', '--help'])
    assert result.exit_code == 0
    assert 'List available LangSmith projects' in result.output


# ============================================
# list-runs Command Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_list_runs(mock_run, runner):
    """Test langsmith list-runs command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'list-runs'])

    assert mock_run.called
    # Verify command structure (without doppler)
    call_args = mock_run.call_args[0][0]
    assert '-m' in call_args
    assert 'dr_cli.commands.langsmith_runner' in call_args
    assert '--command' in call_args
    assert 'list-runs' in call_args


@patch('subprocess.run')
def test_langsmith_list_runs_with_options(mock_run, runner):
    """Test list-runs with custom options"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'list-runs', '--limit', '5', '--hours', '12'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert '--limit' in call_args
    assert '5' in call_args
    assert '--hours' in call_args
    assert '12' in call_args


# ============================================
# show-run Command Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_show_run(mock_run, runner):
    """Test langsmith show-run command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'show-run', 'test-run-id-123'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert '--run-id' in call_args
    assert 'test-run-id-123' in call_args


# ============================================
# show-feedback Command Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_show_feedback(mock_run, runner):
    """Test langsmith show-feedback command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'show-feedback', 'test-run-id'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert '--run-id' in call_args
    assert 'test-run-id' in call_args


# ============================================
# stats Command Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_stats(mock_run, runner):
    """Test langsmith stats command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'stats'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'stats' in call_args


@patch('subprocess.run')
def test_langsmith_stats_with_options(mock_run, runner):
    """Test stats with custom options"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'stats', '--limit', '100', '--hours', '48'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert '--limit' in call_args
    assert '100' in call_args
    assert '--hours' in call_args
    assert '48' in call_args


# ============================================
# projects Command Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_projects(mock_run, runner):
    """Test langsmith projects command"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'projects'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'projects' in call_args


# ============================================
# REGRESSION TESTS for --doppler Flag
# ============================================

@patch('subprocess.run')
def test_langsmith_list_runs_respects_doppler_flag(mock_run, runner):
    """REGRESSION: Verify list-runs uses doppler when --doppler flag is set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'list-runs'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]

    # Verify doppler wrapper is present
    assert 'doppler' in call_args
    assert 'run' in call_args
    assert '--project' in call_args
    assert 'rag-chatbot-worktree' in call_args
    assert '--config' in call_args
    assert 'dev_personal' in call_args
    assert '--' in call_args

    # Verify actual command follows doppler wrapper
    assert 'dr_cli.commands.langsmith_runner' in call_args
    assert 'list-runs' in call_args


@patch('subprocess.run')
def test_langsmith_show_run_respects_doppler_flag(mock_run, runner):
    """REGRESSION: Verify show-run uses doppler when --doppler flag is set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'show-run', 'test-id'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'show-run' in call_args


@patch('subprocess.run')
def test_langsmith_show_feedback_respects_doppler_flag(mock_run, runner):
    """REGRESSION: Verify show-feedback uses doppler when --doppler flag is set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'show-feedback', 'test-id'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'show-feedback' in call_args


@patch('subprocess.run')
def test_langsmith_stats_respects_doppler_flag(mock_run, runner):
    """REGRESSION: Verify stats uses doppler when --doppler flag is set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'stats'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'stats' in call_args


@patch('subprocess.run')
def test_langsmith_projects_respects_doppler_flag(mock_run, runner):
    """REGRESSION: Verify projects uses doppler when --doppler flag is set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'projects'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert 'doppler' in call_args
    assert 'projects' in call_args


@patch('subprocess.run')
def test_langsmith_without_doppler_flag_no_wrapper(mock_run, runner):
    """REGRESSION: Verify commands run without doppler wrapper when flag not set"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'list-runs'])

    assert mock_run.called
    call_args = mock_run.call_args[0][0]

    # Verify doppler is NOT in the command
    # The command should start directly with python
    first_arg = call_args[0]
    assert 'python' in first_arg.lower() or first_arg.endswith('python3')
    assert 'doppler' not in call_args


# ============================================
# Command Structure Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_command_structure_with_doppler(mock_run, runner):
    """Test exact command structure with doppler flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['--doppler', 'langsmith', 'list-runs', '--limit', '5'])

    call_args = mock_run.call_args[0][0]

    # Expected structure:
    # ['doppler', 'run', '--project', 'rag-chatbot-worktree', '--config', 'dev_personal', '--',
    #  sys.executable, '-m', 'dr_cli.commands.langsmith_runner', '--command', 'list-runs', '--limit', '5', ...]

    doppler_idx = call_args.index('doppler')
    run_idx = call_args.index('run')
    dash_dash_idx = call_args.index('--')

    assert run_idx == doppler_idx + 1
    assert '--project' in call_args[doppler_idx:dash_dash_idx]
    assert 'rag-chatbot-worktree' in call_args[doppler_idx:dash_dash_idx]
    assert '-m' in call_args[dash_dash_idx:]
    assert 'dr_cli.commands.langsmith_runner' in call_args[dash_dash_idx:]


@patch('subprocess.run')
def test_langsmith_command_structure_without_doppler(mock_run, runner):
    """Test exact command structure without doppler flag"""
    mock_run.return_value = MagicMock(returncode=0)

    result = runner.invoke(cli, ['langsmith', 'list-runs'])

    call_args = mock_run.call_args[0][0]

    # Expected structure:
    # [sys.executable, '-m', 'dr_cli.commands.langsmith_runner', '--command', 'list-runs', ...]

    # Should NOT contain doppler
    assert 'doppler' not in call_args

    # Should start with python executable
    assert call_args[1] == '-m'
    assert call_args[2] == 'dr_cli.commands.langsmith_runner'
    assert call_args[3] == '--command'
    assert call_args[4] == 'list-runs'


# ============================================
# Error Handling Tests
# ============================================

@patch('subprocess.run')
def test_langsmith_command_error_handling(mock_run, runner):
    """Test that subprocess errors are handled correctly"""
    mock_run.return_value = MagicMock(returncode=1)

    result = runner.invoke(cli, ['langsmith', 'list-runs'])

    # The command should exit with non-zero code
    assert result.exit_code == 1


# ============================================
# Integration with Context Tests
# ============================================

def test_langsmith_with_doppler_flag_context(runner):
    """Test that --doppler flag properly sets context"""
    result = runner.invoke(cli, ['--doppler', 'langsmith', '--help'])
    assert result.exit_code == 0
    # Help should work even with --doppler flag
    assert 'langsmith' in result.output.lower()
