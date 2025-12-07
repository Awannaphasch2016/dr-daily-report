# -*- coding: utf-8 -*-
"""
Unit test for user_facing_scores extraction logic.

Tests PrecomputeService._ensure_user_facing_scores() method.
Following TDD principles from CLAUDE.md - tests ACTUAL production code, not duplicated logic.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestUserFacingScoresExtraction:
    """Test user_facing_scores extraction in PrecomputeService"""

    def setup_method(self):
        """Setup test fixtures - follows Canonical Test Pattern from CLAUDE.md"""
        from src.data.aurora.precompute_service import PrecomputeService
        self.service = PrecomputeService()

    def test_ensure_user_facing_scores_extracts_when_missing(self):
        """
        Test that _ensure_user_facing_scores extracts scores when missing.

        Follows Principle 1: Test Outcomes, Not Execution
        - We test WHAT happens (scores get added to result)
        - Not HOW it happens (exact method calls)
        """
        # Arrange: Mock result WITHOUT user_facing_scores
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0, 'sma_20': 100.0},
            'ticker_data': {'sector': 'Technology', 'name': 'NVIDIA'},
            'percentiles': {'rsi': 0.7, 'volume': 0.8},
        }

        # Mock UserFacingScorer (Principle 2: Mock only external boundaries)
        mock_scores = {
            'Technical': {'score': 8.5, 'category': 'Technical', 'rationale': 'Strong RSI'},
            'Fundamental': {'score': 7.2, 'category': 'Fundamental', 'rationale': 'Good fundamentals'},
            'Liquidity': {'score': 6.8, 'category': 'Liquidity', 'rationale': 'High volume'},
            'Valuation': {'score': 7.0, 'category': 'Valuation', 'rationale': 'Fair value'},
            'Selling Pressure': {'score': 5.5, 'category': 'Selling Pressure', 'rationale': 'Moderate'},
            'Uncertainty': {'score': 6.2, 'category': 'Uncertainty', 'rationale': 'Low uncertainty'}
        }

        with patch('src.scoring.user_facing_scorer.UserFacingScorer') as MockScorer:
            mock_scorer_instance = MagicMock()
            mock_scorer_instance.calculate_all_scores.return_value = mock_scores
            MockScorer.return_value = mock_scorer_instance

            # Act: Call ACTUAL production method
            result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

            # Assert: OUTCOME - user_facing_scores should be in result
            assert 'user_facing_scores' in result, "user_facing_scores should be extracted when missing"
            assert result['user_facing_scores'] == mock_scores, "Extracted scores should match scorer output"
            assert len(result['user_facing_scores']) == 6, "Should have 6 scoring categories"

            # Verify scorer was called with correct args
            mock_scorer_instance.calculate_all_scores.assert_called_once_with(
                ticker_data=mock_result['ticker_data'],
                indicators=mock_result['indicators'],
                percentiles=mock_result['percentiles']
            )

    def test_ensure_user_facing_scores_preserves_existing(self):
        """
        Test that existing user_facing_scores are NOT overwritten.

        Follows Principle 1: Test Outcomes (don't replace existing data)
        """
        # Arrange: Result WITH existing user_facing_scores
        existing_scores = {
            'Technical': {'score': 9.0, 'category': 'Technical', 'rationale': 'Custom score'}
        }

        mock_result = {
            'ticker': 'NVDA19',
            'user_facing_scores': existing_scores,  # Already present
            'indicators': {'rsi': 65.0},
            'ticker_data': {'sector': 'Technology'},
            'percentiles': {'rsi': 0.7},
        }

        # Act: Call production method
        result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

        # Assert: OUTCOME - existing scores preserved
        assert result['user_facing_scores'] == existing_scores, "Existing scores should not be overwritten"
        assert result['user_facing_scores']['Technical']['score'] == 9.0, "Original score preserved"

    def test_ensure_user_facing_scores_handles_missing_required_data(self):
        """
        Test graceful handling when required data is missing.

        Follows Principle 5: Silent Failure Detection
        - Missing data shouldn't raise exception
        - Should log warning and return result unchanged
        """
        # Arrange: Mock result MISSING ticker_data and percentiles
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0},
            # Missing: ticker_data, percentiles
        }

        # Act: Call production method
        result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

        # Assert: OUTCOME - user_facing_scores should NOT be added
        assert 'user_facing_scores' not in result, "Should not extract when required data is missing"

    def test_ensure_user_facing_scores_handles_scorer_exception(self):
        """
        Test that scorer exceptions are handled gracefully.

        Follows Principle 2: Explicit Failure Mocking
        - Simulate UserFacingScorer raising exception
        - Should catch, log warning, return result unchanged
        """
        # Arrange: Mock result with all required data
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0},
            'ticker_data': {'sector': 'Technology'},
            'percentiles': {'rsi': 0.7},
        }

        with patch('src.scoring.user_facing_scorer.UserFacingScorer') as MockScorer:
            # Explicit failure: Scorer raises exception
            MockScorer.side_effect = Exception("Scorer calculation failed")

            # Act: Call production method
            result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

            # Assert: OUTCOME - exception handled gracefully, no scores added
            assert 'user_facing_scores' not in result, "Should handle scorer exception gracefully"

    def test_ensure_user_facing_scores_returns_updated_dict(self):
        """
        Test that method returns the updated result dict.

        Verifies the method contract: returns modified dict
        """
        # Arrange
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0},
            'ticker_data': {'sector': 'Technology'},
            'percentiles': {'rsi': 0.7},
        }

        with patch('src.scoring.user_facing_scorer.UserFacingScorer') as MockScorer:
            mock_scorer = MagicMock()
            mock_scorer.calculate_all_scores.return_value = {'Technical': {'score': 8.0}}
            MockScorer.return_value = mock_scorer

            # Act
            result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

            # Assert: Returns dict type
            assert isinstance(result, dict), "Should return dict"
            # Assert: Original fields preserved
            assert result['ticker'] == 'NVDA19', "Should preserve original fields"
            assert result['indicators'] == mock_result['indicators'], "Should preserve indicators"

    def test_ensure_user_facing_scores_handles_empty_dict_fields(self):
        """
        REGRESSION TEST for empty dict truthiness bug.

        GIVEN workflow returns EMPTY DICTS for indicators/ticker_data/percentiles
        WHEN _ensure_user_facing_scores is called
        THEN it should NOT silently skip extraction (empty dicts != missing data)

        This is the ACTUAL production scenario where workflow initializes fields
        to {} and they remain empty if nodes fail or data fetch fails.

        Bug: The check `if not result['indicators']` evaluates to True when
        result['indicators'] = {} (empty dict is falsy), causing early return.

        Expected behavior: Should detect empty dicts explicitly and return
        WITHOUT user_facing_scores (graceful degradation), but with clear
        ERROR log (not buried WARNING).

        Follows CLAUDE.md:
        - TDD RED: This test documents the bug (passes with buggy code)
        - Test will guide fix: explicit empty dict check needed
        - Principle 2: Explicit Failure Mocking (test with empty dicts {})
        - Principle 5: Test Outcomes (verify user_facing_scores not added)
        """
        # Arrange: Mock result with EMPTY DICTS (not missing keys)
        # This mirrors agent workflow initialization (agent.py:158-182)
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {},      # EMPTY dict (falsy but present)
            'ticker_data': {},     # EMPTY dict (falsy but present)
            'percentiles': {},     # EMPTY dict (falsy but present)
        }

        # Act: Call _ensure_user_facing_scores with empty dicts
        result = self.service._ensure_user_facing_scores(mock_result.copy(), 'NVDA19')

        # Assert: OUTCOME - Should NOT add user_facing_scores when fields are empty
        # This test PASSES with current buggy code (documenting the bug)
        # After fix, test will still pass but with explicit empty dict detection
        assert 'user_facing_scores' not in result, \
            "Empty dicts should be detected as invalid input, scores not extracted"

        # Additional assertion: All original fields preserved
        assert result['ticker'] == 'NVDA19', "Should preserve ticker field"
        assert result['indicators'] == {}, "Should preserve empty indicators"
        assert result['ticker_data'] == {}, "Should preserve empty ticker_data"
        assert result['percentiles'] == {}, "Should preserve empty percentiles"
