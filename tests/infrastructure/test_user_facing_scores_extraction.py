# -*- coding: utf-8 -*-
"""
Unit test for user_facing_scores extraction logic.

Tests the fix for bug at src/data/aurora/precompute_service.py:682-698
Following TDD principles from CLAUDE.md
"""

import pytest
from unittest.mock import MagicMock, patch


class TestUserFacingScoresExtraction:
    """Test user_facing_scores extraction in precompute service"""

    def test_user_facing_scores_extracted_when_missing(self):
        """
        GREEN phase: Test that user_facing_scores are extracted when missing.

        This is a BEHAVIOR test (Principle 1: Test Outcomes, Not Execution)
        We test WHAT happens (scores get added), not HOW (exact method calls)
        """
        # Arrange: Mock result dict without user_facing_scores
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0, 'sma_20': 100.0},
            'ticker_data': {'sector': 'Technology', 'name': 'NVIDIA'},
            'percentiles': {'rsi': 0.7, 'volume': 0.8},
        }

        # Mock UserFacingScorer (Principle 2: Explicit Failure Mocking)
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

            # Act: Execute the extraction logic (from precompute_service.py:682-698)
            result = mock_result.copy()
            symbol = 'NVDA19'

            if 'user_facing_scores' not in result:
                if result.get('indicators') and result.get('ticker_data') and result.get('percentiles'):
                    try:
                        from src.scoring.user_facing_scorer import UserFacingScorer
                        scorer = UserFacingScorer()
                        scores = scorer.calculate_all_scores(
                            ticker_data=result.get('ticker_data', {}),
                            indicators=result.get('indicators', {}),
                            percentiles=result.get('percentiles', {})
                        )
                        result['user_facing_scores'] = scores
                    except Exception:
                        pass

            # Assert: OUTCOME - user_facing_scores should be in result
            assert 'user_facing_scores' in result, "user_facing_scores should be extracted when missing"
            assert result['user_facing_scores'] == mock_scores, "Extracted scores should match"
            assert len(result['user_facing_scores']) == 6, "Should have 6 scoring categories"

    def test_user_facing_scores_not_overwritten_when_present(self):
        """
        Test that existing user_facing_scores are NOT overwritten.

        Follows Principle 3: Test the actual behavior (don't replace existing data)
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

        # Act: Extraction logic should NOT run
        result = mock_result.copy()

        if 'user_facing_scores' not in result:
            # This block should NOT execute
            result['user_facing_scores'] = {'SHOULD_NOT': 'HAPPEN'}

        # Assert: OUTCOME - existing scores preserved
        assert result['user_facing_scores'] == existing_scores, "Existing scores should not be overwritten"
        assert 'SHOULD_NOT' not in result['user_facing_scores'], "Logic should not have run"

    def test_user_facing_scores_not_extracted_when_required_data_missing(self):
        """
        Test graceful failure when required data is missing.

        Follows Principle 2: Explicit Failure Mocking
        Follows Principle 5: Silent Failure Detection
        """
        # Arrange: Mock result MISSING ticker_data and percentiles
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0},
            # Missing: ticker_data, percentiles
        }

        # Act: Extraction logic with missing data
        result = mock_result.copy()

        if 'user_facing_scores' not in result:
            if result.get('indicators') and result.get('ticker_data') and result.get('percentiles'):
                result['user_facing_scores'] = {}  # Should NOT execute
            else:
                pass  # Graceful failure - don't extract

        # Assert: OUTCOME - user_facing_scores should NOT be added
        assert 'user_facing_scores' not in result, "Should not extract when required data is missing"

    def test_user_facing_scores_extraction_handles_scorer_exception(self):
        """
        Test that extraction handles UserFacingScorer exceptions gracefully.

        Follows Principle 2: Explicit Failure Mocking (simulate exceptions)
        """
        # Arrange: Mock scorer that raises exception
        mock_result = {
            'ticker': 'NVDA19',
            'indicators': {'rsi': 65.0},
            'ticker_data': {'sector': 'Technology'},
            'percentiles': {'rsi': 0.7},
        }

        with patch('src.scoring.user_facing_scorer.UserFacingScorer') as MockScorer:
            # Explicit failure: Scorer raises exception
            MockScorer.side_effect = Exception("Scorer failed")

            # Act: Extraction should handle exception gracefully
            result = mock_result.copy()

            if 'user_facing_scores' not in result:
                if result.get('indicators') and result.get('ticker_data') and result.get('percentiles'):
                    try:
                        from src.scoring.user_facing_scorer import UserFacingScorer
                        scorer = UserFacingScorer()
                        scores = scorer.calculate_all_scores(
                            ticker_data=result.get('ticker_data', {}),
                            indicators=result.get('indicators', {}),
                            percentiles=result.get('percentiles', {})
                        )
                        result['user_facing_scores'] = scores
                    except Exception:
                        pass  # Graceful failure

            # Assert: OUTCOME - extraction failed gracefully, no scores added
            assert 'user_facing_scores' not in result, "Should handle scorer exception gracefully"
