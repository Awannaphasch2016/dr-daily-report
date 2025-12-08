"""
Contract test: UserFacingScorer MUST return primitives only.

Following CLAUDE.md:
- Defensive Programming: Validate data types at creation
- System Boundary: UserFacingScorer → Workflow state → Aurora cache
- Contract: All return values must be Python primitives (int, float, str, bool, None, list, dict)
- Test Fixtures Must Match Production Reality: Use NumPy types in test inputs
"""
import pytest
import json
import numpy as np
import pandas as pd
from src.scoring.user_facing_scorer import UserFacingScorer


class TestUserFacingScorerPrimitivesOnly:
    """Enforce contract: UserFacingScorer returns primitives only."""

    def setup_method(self):
        self.scorer = UserFacingScorer()

    def test_calculate_all_scores_returns_only_primitives(self):
        """GIVEN UserFacingScorer with realistic inputs (including NumPy types)
        WHEN calculate_all_scores is called
        THEN ALL return values must be Python primitives

        Contract: Never return NumPy/Pandas types. Convert at source.

        This test uses NumPy types in inputs to match production reality
        (TechnicalAnalyzer returns NumPy types from pandas calculations).
        """
        # Realistic inputs with NumPy types (matches production!)
        ticker_data = {
            'info': {
                'sector': 'Technology',
                'currentPrice': np.float64(100.0),  # Production uses NumPy
                'marketCap': np.int64(1000000000),
                'trailingPE': np.float64(25.5),
                'priceToBook': np.float64(5.2),
                'debtToEquity': np.float64(0.3)
            },
            'history': pd.DataFrame({
                'Close': [95.0, 98.0, 100.0],
                'Volume': [1000000, 1100000, 1200000]
            })
        }

        indicators = {
            'rsi': np.float64(65.0),
            'sma_20': np.float64(95.0),
            'sma_50': np.float64(90.0),
            'macd': np.float64(0.5),
            'signal': np.float64(0.3),
            'bb_upper': np.float64(105.0),
            'bb_lower': np.float64(95.0)
        }

        percentiles = {
            'rsi_percentile': np.int64(70),
            'volume_percentile': np.int64(60),
            'pe_percentile': np.int64(50),
            'pb_percentile': np.int64(55),
            'debt_percentile': np.int64(45)
        }

        # Call real method (not mocked!)
        scores = self.scorer.calculate_all_scores(
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles
        )

        # CONTRACT: Recursively verify ALL values are primitives
        def assert_primitives_only(obj, path="root"):
            """Fail test if any non-primitive type found."""
            primitive_types = (int, float, str, bool, type(None))

            if isinstance(obj, dict):
                for key, value in obj.items():
                    assert_primitives_only(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    assert_primitives_only(item, f"{path}[{i}]")
            else:
                # The actual check
                assert isinstance(obj, primitive_types), \
                    f"Non-primitive type at {path}: {type(obj).__name__} = {obj}\n" \
                    f"Expected: int, float, str, bool, or None\n" \
                    f"Got: {type(obj).__module__}.{type(obj).__name__}"

        assert_primitives_only(scores)

    def test_output_is_json_serializable(self):
        """GIVEN scorer output
        WHEN json.dumps() is called
        THEN it must succeed (no TypeError)

        This is the ultimate contract: if it's JSON-serializable, it's safe.

        Following CLAUDE.md Principle 3.5: Integration tests must exercise
        critical transformations - don't mock json.dumps()!
        """
        # Realistic inputs with NumPy types
        ticker_data = {
            'info': {
                'sector': 'Technology',
                'currentPrice': np.float64(100.0),
                'marketCap': np.int64(1000000000)
            }
        }

        indicators = {
            'rsi': np.float64(65.0),
            'sma_20': np.float64(95.0)
        }

        percentiles = {
            'rsi_percentile': np.int64(70),
            'volume_percentile': np.int64(60)
        }

        scores = self.scorer.calculate_all_scores(
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles
        )

        # Must not raise TypeError - let json.dumps() execute for real!
        try:
            json_str = json.dumps(scores)
            # Round-trip verification (CLAUDE.md Principle 3)
            deserialized = json.loads(json_str)
            assert deserialized is not None
            assert 'Technical' in deserialized  # Basic structure check
        except TypeError as e:
            pytest.fail(
                f"UserFacingScorer output not JSON-serializable: {e}\n"
                f"This means NumPy/Pandas types are being returned.\n"
                f"Contract violation: All return values must be Python primitives."
            )

    def test_each_score_category_has_required_fields(self):
        """GIVEN scorer output
        WHEN inspecting each score category
        THEN each must have score, category, rationale fields with primitive types
        """
        ticker_data = {
            'info': {
                'sector': 'Technology',
                'currentPrice': np.float64(100.0)
            }
        }
        indicators = {'rsi': np.float64(65.0)}
        percentiles = {'rsi_percentile': np.int64(70)}

        scores = self.scorer.calculate_all_scores(
            ticker_data=ticker_data,
            indicators=indicators,
            percentiles=percentiles
        )

        # Expected categories
        expected_categories = [
            'Technical', 'Fundamental', 'Liquidity',
            'Valuation', 'Selling Pressure', 'Uncertainty'
        ]

        for category in expected_categories:
            if category in scores:  # Some may fail gracefully
                score_data = scores[category]

                # Must have required fields
                assert 'score' in score_data, f"{category} missing 'score' field"
                assert 'category' in score_data, f"{category} missing 'category' field"
                assert 'rationale' in score_data, f"{category} missing 'rationale' field"

                # Fields must be primitives
                assert isinstance(score_data['score'], (int, float)), \
                    f"{category} score is {type(score_data['score'])}, expected int/float"
                assert isinstance(score_data['category'], str), \
                    f"{category} category is {type(score_data['category'])}, expected str"
                assert isinstance(score_data['rationale'], str), \
                    f"{category} rationale is {type(score_data['rationale'])}, expected str"
