"""
Langfuse Trace Schema Contract Tests

Following CLAUDE.md Principle #22 (LLM Observability Discipline) and #23 (Configuration Variation Axis):
- Verify trace schema is populated with correct values
- Verify env vars are passed to client constructor
- Verify trace_context sets correct attributes
- Verify score normalization (0-100 → 0-1)
- Verify graceful degradation when Langfuse unavailable

Schema Reference: .claude/skills/langfuse-observability/SCHEMA.md

These tests use mocking because:
1. We don't want to send real traces during tests
2. We verify the CONTRACT (correct values passed to SDK)
3. Langfuse SDK is trusted to handle values correctly
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager


# Reset singleton before each test
@pytest.fixture(autouse=True)
def reset_langfuse_singleton():
    """Reset Langfuse client singleton before each test."""
    import src.integrations.langfuse_client as lf_module
    lf_module._langfuse_client = None
    yield
    lf_module._langfuse_client = None


class TestLangfuseClientInitialization:
    """Verify Langfuse client is initialized with correct env vars.

    Schema columns set at client init:
    - release: from LANGFUSE_RELEASE env var
    - environment: from LANGFUSE_TRACING_ENVIRONMENT env var
    """

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
        'LANGFUSE_HOST': 'https://test.langfuse.com',
        'LANGFUSE_RELEASE': 'dev-local',
        'LANGFUSE_TRACING_ENVIRONMENT': 'local'
    })
    @patch('langfuse.Langfuse')
    def test_client_passes_release_to_constructor(self, mock_langfuse_class):
        """GIVEN LANGFUSE_RELEASE env var is set
        WHEN Langfuse client is created
        THEN release is passed to Langfuse constructor

        This ensures 'Version' column is populated in Langfuse UI.
        """
        from src.integrations.langfuse_client import get_langfuse_client

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        client = get_langfuse_client()

        mock_langfuse_class.assert_called_once()
        call_kwargs = mock_langfuse_class.call_args.kwargs

        assert call_kwargs.get('release') == 'dev-local', \
            f"Expected release='dev-local', got release='{call_kwargs.get('release')}'"

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
        'LANGFUSE_HOST': 'https://test.langfuse.com',
        'LANGFUSE_RELEASE': 'prd',
        'LANGFUSE_TRACING_ENVIRONMENT': 'prd'
    })
    @patch('langfuse.Langfuse')
    def test_client_passes_environment_to_constructor(self, mock_langfuse_class):
        """GIVEN LANGFUSE_TRACING_ENVIRONMENT env var is set
        WHEN Langfuse client is created
        THEN environment is passed to Langfuse constructor

        This ensures 'Environment' column is populated in Langfuse UI.
        """
        from src.integrations.langfuse_client import get_langfuse_client

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        client = get_langfuse_client()

        call_kwargs = mock_langfuse_class.call_args.kwargs

        assert call_kwargs.get('environment') == 'prd', \
            f"Expected environment='prd', got environment='{call_kwargs.get('environment')}'"

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
        'LANGFUSE_HOST': 'https://custom.langfuse.com',
        'LANGFUSE_RELEASE': 'v1.0.0',
        'LANGFUSE_TRACING_ENVIRONMENT': 'stg'
    })
    @patch('langfuse.Langfuse')
    def test_client_passes_all_constructor_params(self, mock_langfuse_class):
        """GIVEN all Langfuse env vars are set
        WHEN Langfuse client is created
        THEN all params are passed to constructor

        Verifies complete schema: public_key, secret_key, host, release, environment
        """
        from src.integrations.langfuse_client import get_langfuse_client

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        client = get_langfuse_client()

        call_kwargs = mock_langfuse_class.call_args.kwargs

        assert call_kwargs.get('public_key') == 'pk-test-123'
        assert call_kwargs.get('secret_key') == 'sk-test-456'
        assert call_kwargs.get('host') == 'https://custom.langfuse.com'
        assert call_kwargs.get('release') == 'v1.0.0'
        assert call_kwargs.get('environment') == 'stg'

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    }, clear=True)
    @patch('langfuse.Langfuse')
    def test_client_handles_missing_optional_env_vars(self, mock_langfuse_class):
        """GIVEN optional env vars (RELEASE, ENVIRONMENT) are not set
        WHEN Langfuse client is created
        THEN client is still created (optional params are None)

        Ensures graceful handling of missing optional config.
        """
        # Need to also set PATH for the environment
        os.environ.setdefault('PATH', '/usr/bin')

        from src.integrations.langfuse_client import get_langfuse_client

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        client = get_langfuse_client()

        # Should still create client
        mock_langfuse_class.assert_called_once()
        call_kwargs = mock_langfuse_class.call_args.kwargs

        # Optional params should be None (not cause error)
        assert call_kwargs.get('release') is None
        assert call_kwargs.get('environment') is None


class TestTraceContextSchema:
    """Verify trace_context sets correct trace attributes.

    Schema columns set via trace_context:
    - user_id: User identifier
    - session_id: Session grouping
    - tags: Filterable tags
    - metadata: Key-value metadata
    """

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_sets_user_id(self, mock_langfuse_class):
        """GIVEN trace_context called with user_id
        WHEN context is entered
        THEN update_current_trace is called with user_id
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        # Initialize client
        get_langfuse_client()

        with trace_context(user_id="telegram_user_12345"):
            pass

        mock_client.update_current_trace.assert_called_once()
        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert call_kwargs.get('user_id') == 'telegram_user_12345'

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_sets_session_id(self, mock_langfuse_class):
        """GIVEN trace_context called with session_id
        WHEN context is entered
        THEN update_current_trace is called with session_id
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        with trace_context(session_id="daily_2026-01-11"):
            pass

        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert call_kwargs.get('session_id') == 'daily_2026-01-11'

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_sets_tags(self, mock_langfuse_class):
        """GIVEN trace_context called with tags
        WHEN context is entered
        THEN update_current_trace is called with tags array
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        with trace_context(tags=["report_generation", "cli"]):
            pass

        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert call_kwargs.get('tags') == ["report_generation", "cli"]

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_sets_metadata(self, mock_langfuse_class):
        """GIVEN trace_context called with metadata dict
        WHEN context is entered
        THEN update_current_trace is called with metadata
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        with trace_context(metadata={"ticker": "DBS19", "model": "gpt-4o-mini"}):
            pass

        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert call_kwargs.get('metadata') == {"ticker": "DBS19", "model": "gpt-4o-mini"}

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_sets_all_attributes(self, mock_langfuse_class):
        """GIVEN trace_context called with all attributes
        WHEN context is entered
        THEN update_current_trace receives all attributes

        Verifies complete trace context schema.
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        with trace_context(
            user_id="anak",
            session_id="daily_2026-01-11",
            tags=["report_generation", "test"],
            metadata={"ticker": "AAPL", "version": "v2"}
        ):
            pass

        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert call_kwargs.get('user_id') == 'anak'
        assert call_kwargs.get('session_id') == 'daily_2026-01-11'
        assert call_kwargs.get('tags') == ["report_generation", "test"]
        assert call_kwargs.get('metadata') == {"ticker": "AAPL", "version": "v2"}

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_trace_context_truncates_long_user_id(self, mock_langfuse_class):
        """GIVEN trace_context called with user_id > 200 chars
        WHEN context is entered
        THEN user_id is truncated to 200 chars

        Langfuse has 200 char limit on user_id.
        """
        from src.integrations.langfuse_client import get_langfuse_client, trace_context

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        long_user_id = "u" * 300  # 300 chars

        with trace_context(user_id=long_user_id):
            pass

        call_kwargs = mock_client.update_current_trace.call_args.kwargs

        assert len(call_kwargs.get('user_id')) == 200, \
            f"Expected user_id truncated to 200 chars, got {len(call_kwargs.get('user_id'))}"


class TestObservationLevelSchema:
    """Verify set_observation_level sets correct level values.

    Schema column: level (on observation)
    Valid values: DEBUG, DEFAULT, WARNING, ERROR
    """

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_observation_level_error(self, mock_langfuse_class):
        """GIVEN set_observation_level called with 'ERROR'
        WHEN function executes
        THEN update_current_observation receives level='ERROR'
        """
        from src.integrations.langfuse_client import get_langfuse_client, set_observation_level

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        result = set_observation_level("ERROR")

        assert result is True
        mock_client.update_current_observation.assert_called_once_with(level="ERROR")

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_observation_level_warning(self, mock_langfuse_class):
        """GIVEN set_observation_level called with 'WARNING'
        WHEN function executes
        THEN update_current_observation receives level='WARNING'
        """
        from src.integrations.langfuse_client import get_langfuse_client, set_observation_level

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        result = set_observation_level("WARNING")

        assert result is True
        mock_client.update_current_observation.assert_called_once_with(level="WARNING")

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_observation_level_rejects_invalid(self, mock_langfuse_class):
        """GIVEN set_observation_level called with invalid level
        WHEN function executes
        THEN returns False and does NOT call update_current_observation
        """
        from src.integrations.langfuse_client import get_langfuse_client, set_observation_level

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        result = set_observation_level("INVALID_LEVEL")

        assert result is False
        mock_client.update_current_observation.assert_not_called()

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_observation_level_all_valid_values(self, mock_langfuse_class):
        """GIVEN set_observation_level called with each valid level
        WHEN function executes
        THEN all valid levels are accepted

        Valid levels per schema: DEBUG, DEFAULT, WARNING, ERROR
        """
        from src.integrations.langfuse_client import set_observation_level
        import src.integrations.langfuse_client as lf_module

        valid_levels = ["DEBUG", "DEFAULT", "WARNING", "ERROR"]

        for level in valid_levels:
            # Reset singleton for each iteration
            lf_module._langfuse_client = None

            mock_client = Mock()
            mock_langfuse_class.return_value = mock_client

            from src.integrations.langfuse_client import get_langfuse_client
            get_langfuse_client()

            result = set_observation_level(level)

            assert result is True, f"Level '{level}' should be accepted"
            mock_client.update_current_observation.assert_called_with(level=level)


class TestTraceLevelSchema:
    """Verify set_trace_level sets correct level values.

    Schema column: level (on trace)
    Valid values: DEBUG, DEFAULT, WARNING, ERROR
    """

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_trace_level_error(self, mock_langfuse_class):
        """GIVEN set_trace_level called with 'ERROR'
        WHEN function executes
        THEN update_current_trace receives level='ERROR'
        """
        from src.integrations.langfuse_client import get_langfuse_client, set_trace_level

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        result = set_trace_level("ERROR")

        assert result is True
        mock_client.update_current_trace.assert_called_once_with(level="ERROR")

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_set_trace_level_rejects_invalid(self, mock_langfuse_class):
        """GIVEN set_trace_level called with invalid level
        WHEN function executes
        THEN returns False and does NOT call update_current_trace
        """
        from src.integrations.langfuse_client import get_langfuse_client, set_trace_level

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        result = set_trace_level("CRITICAL")  # Not a valid Langfuse level

        assert result is False
        mock_client.update_current_trace.assert_not_called()


class TestScoreNormalization:
    """Verify score values are normalized correctly.

    Schema: score value is 0-1 in Langfuse
    Our API uses 0-100 scale for readability
    Normalization: value / 100
    """

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_normalizes_100_to_1(self, mock_langfuse_class):
        """GIVEN score_current_trace called with value=100
        WHEN function executes
        THEN Langfuse receives value=1.0
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        score_current_trace("faithfulness", 100)

        mock_client.score_current_trace.assert_called_once()
        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        assert call_kwargs.get('value') == 1.0, \
            f"Expected normalized value=1.0, got {call_kwargs.get('value')}"

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_normalizes_50_to_0_5(self, mock_langfuse_class):
        """GIVEN score_current_trace called with value=50
        WHEN function executes
        THEN Langfuse receives value=0.5
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        score_current_trace("completeness", 50)

        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        assert call_kwargs.get('value') == 0.5

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_normalizes_0_to_0(self, mock_langfuse_class):
        """GIVEN score_current_trace called with value=0
        WHEN function executes
        THEN Langfuse receives value=0.0
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        score_current_trace("reasoning_quality", 0)

        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        assert call_kwargs.get('value') == 0.0

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_normalizes_85_5_to_0_855(self, mock_langfuse_class):
        """GIVEN score_current_trace called with value=85.5
        WHEN function executes
        THEN Langfuse receives value=0.855

        Tests decimal preservation in normalization.
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        score_current_trace("compliance", 85.5)

        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        assert call_kwargs.get('value') == 0.855

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_passes_name_and_comment(self, mock_langfuse_class):
        """GIVEN score_current_trace called with name and comment
        WHEN function executes
        THEN Langfuse receives name and comment unchanged
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        score_current_trace("faithfulness", 85, comment="Good numeric accuracy")

        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        assert call_kwargs.get('name') == 'faithfulness'
        assert call_kwargs.get('comment') == 'Good numeric accuracy'

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_already_normalized_not_double_normalized(self, mock_langfuse_class):
        """GIVEN score_current_trace called with value=0.85 (already 0-1)
        WHEN function executes
        THEN value is NOT double-normalized (remains 0.85)

        The function should detect already-normalized values.
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_current_trace

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        # Value <= 1 should be treated as already normalized
        score_current_trace("consistency", 0.85)

        call_kwargs = mock_client.score_current_trace.call_args.kwargs

        # Should NOT divide by 100 again
        assert call_kwargs.get('value') == 0.85, \
            f"Expected 0.85 (already normalized), got {call_kwargs.get('value')}"


class TestScoreBatch:
    """Verify score_trace_batch passes multiple scores correctly."""

    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test-123',
        'LANGFUSE_SECRET_KEY': 'sk-test-456',
    })
    @patch('langfuse.Langfuse')
    def test_score_batch_calls_score_for_each(self, mock_langfuse_class):
        """GIVEN score_trace_batch called with 3 scores
        WHEN function executes
        THEN score_current_trace is called 3 times
        """
        from src.integrations.langfuse_client import get_langfuse_client, score_trace_batch

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        get_langfuse_client()

        scores = {
            "faithfulness": (85.0, "Good accuracy"),
            "completeness": (72.0, None),
            "reasoning_quality": (90.5, "Clear structure"),
        }

        count = score_trace_batch(scores)

        assert count == 3
        assert mock_client.score_current_trace.call_count == 3


class TestGracefulDegradation:
    """Verify functions work gracefully when Langfuse unavailable.

    Per CLAUDE.md Principle #22: All Langfuse operations are non-blocking
    and fail gracefully. Core functionality must work without Langfuse.
    """

    @patch.dict(os.environ, {}, clear=True)
    def test_get_client_returns_none_without_keys(self):
        """GIVEN Langfuse keys not set in environment
        WHEN get_langfuse_client called
        THEN returns None (not error)
        """
        # Ensure PATH is set for subprocess operations
        os.environ['PATH'] = '/usr/bin'

        import src.integrations.langfuse_client as lf_module
        lf_module._langfuse_client = None

        from src.integrations.langfuse_client import get_langfuse_client

        client = get_langfuse_client()

        assert client is None

    @patch.dict(os.environ, {}, clear=True)
    def test_trace_context_works_without_client(self):
        """GIVEN Langfuse not configured
        WHEN trace_context is used
        THEN code executes normally (no error)
        """
        os.environ['PATH'] = '/usr/bin'

        import src.integrations.langfuse_client as lf_module
        lf_module._langfuse_client = None

        from src.integrations.langfuse_client import trace_context

        # Should not raise error
        with trace_context(user_id="test", tags=["test"]):
            result = 1 + 1

        assert result == 2

    @patch.dict(os.environ, {}, clear=True)
    def test_score_returns_false_without_client(self):
        """GIVEN Langfuse not configured
        WHEN score_current_trace called
        THEN returns False (not error)
        """
        os.environ['PATH'] = '/usr/bin'

        import src.integrations.langfuse_client as lf_module
        lf_module._langfuse_client = None

        from src.integrations.langfuse_client import score_current_trace

        result = score_current_trace("test", 85)

        assert result is False

    @patch.dict(os.environ, {}, clear=True)
    def test_set_level_returns_false_without_client(self):
        """GIVEN Langfuse not configured
        WHEN set_observation_level called
        THEN returns False (not error)
        """
        os.environ['PATH'] = '/usr/bin'

        import src.integrations.langfuse_client as lf_module
        lf_module._langfuse_client = None

        from src.integrations.langfuse_client import set_observation_level

        result = set_observation_level("ERROR")

        assert result is False

    @patch.dict(os.environ, {}, clear=True)
    def test_flush_works_without_client(self):
        """GIVEN Langfuse not configured
        WHEN flush called
        THEN no error raised
        """
        os.environ['PATH'] = '/usr/bin'

        import src.integrations.langfuse_client as lf_module
        lf_module._langfuse_client = None

        from src.integrations.langfuse_client import flush

        # Should not raise error
        flush()


class TestConstantsUsage:
    """Verify constants from src/config.py are used correctly.

    Per CLAUDE.md Principle #23: Static values that never change
    should be Python constants, not env vars.
    """

    def test_trace_names_constants_exist(self):
        """GIVEN src/config.py TRACE_NAMES class
        WHEN imported
        THEN expected trace names are defined
        """
        from src.config import TRACE_NAMES

        assert hasattr(TRACE_NAMES, 'ANALYZE_TICKER')
        assert TRACE_NAMES.ANALYZE_TICKER == 'analyze_ticker'

    def test_observation_names_constants_exist(self):
        """GIVEN src/config.py OBSERVATION_NAMES class
        WHEN imported
        THEN expected observation names are defined
        """
        from src.config import OBSERVATION_NAMES

        assert hasattr(OBSERVATION_NAMES, 'FETCH_DATA')
        assert hasattr(OBSERVATION_NAMES, 'GENERATE_REPORT')

    def test_score_names_constants_exist(self):
        """GIVEN src/config.py SCORE_NAMES class
        WHEN imported
        THEN expected score names are defined
        """
        from src.config import SCORE_NAMES

        expected_scores = ['faithfulness', 'completeness', 'reasoning_quality',
                          'compliance', 'consistency']

        for score in expected_scores:
            assert score in SCORE_NAMES.all(), \
                f"Expected '{score}' in SCORE_NAMES.all()"

    def test_trace_tags_constants_exist(self):
        """GIVEN src/config.py TRACE_TAGS class
        WHEN imported
        THEN expected tag values are defined
        """
        from src.config import TRACE_TAGS

        assert hasattr(TRACE_TAGS, 'REPORT_GENERATION')
        assert hasattr(TRACE_TAGS, 'TEST')
        assert hasattr(TRACE_TAGS, 'CLI')

    def test_default_user_id_constant_exists(self):
        """GIVEN src/config.py DEFAULT_USER_ID constant
        WHEN imported
        THEN default user is 'anak'
        """
        from src.config import DEFAULT_USER_ID

        assert DEFAULT_USER_ID == 'anak'
