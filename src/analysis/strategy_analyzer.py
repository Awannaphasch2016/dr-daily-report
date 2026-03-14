"""Strategy analysis utilities for filtering supporting strategies"""

from typing import Dict, Optional


class StrategyAnalyzer:
    """Analyzes strategy performance and filters supporting strategies.

    Works with precomputed strategy_performance dicts from Aurora.
    """

    def __init__(self):
        pass

    def extract_recommendation(self, report: str) -> str:
        """Extract BUY/SELL/HOLD recommendation from report"""
        report_upper = report.upper()

        if 'BUY MORE' in report_upper or 'BUY' in report_upper:
            if '????? BUY' in report or '????? BUY MORE' in report or 'BUY MORE' in report_upper:
                return 'BUY'

        if 'SELL' in report_upper:
            if '????? SELL' in report or 'SELL' in report_upper:
                return 'SELL'

        return 'HOLD'

    def filter_supporting_strategies(
        self, recommendation: str, strategy_performance: Dict
    ) -> Dict:
        """Find strategies whose results support the LLM's recommendation.

        Args:
            recommendation: 'BUY', 'SELL', or 'HOLD'
            strategy_performance: {'per_strategy': {name: {buy_only: {...}, sell_only: {...}}, ...}}

        Returns:
            {
                'supporting_strategies': {name: {buy_only: {...}, sell_only: {...}}, ...},
                'best_supporting': {'name': str, 'buy_only': {...}, 'sell_only': {...}},
                'support_count': int,
                'total_count': int,
            }
        """
        empty_result = {
            'supporting_strategies': {},
            'best_supporting': {},
            'support_count': 0,
            'total_count': 0,
        }

        if not strategy_performance:
            return empty_result

        per_strategy = strategy_performance.get('per_strategy', {})
        if not per_strategy:
            return empty_result

        total_count = len(per_strategy)

        # HOLD: no strategies included
        if recommendation == 'HOLD':
            return {
                'supporting_strategies': {},
                'best_supporting': {},
                'support_count': 0,
                'total_count': total_count,
            }

        supporting = {}
        best_name = None
        best_return = float('-inf')
        best_buy = {}
        best_sell = {}

        for name, directions in per_strategy.items():
            if recommendation == 'BUY':
                data = directions.get('buy_only', {})
            else:  # SELL
                data = directions.get('sell_only', {})

            supports = (
                data.get('total_return_pct', 0) > 0
                or data.get('sharpe_ratio', 0) > 0.5
                or data.get('win_rate', 0) > 50
            )

            if supports:
                supporting[name] = directions
                ret = data.get('total_return_pct', 0)
                if ret > best_return:
                    best_return = ret
                    best_name = name
                    best_buy = directions.get('buy_only', {})
                    best_sell = directions.get('sell_only', {})

        best_supporting = {}
        if best_name:
            best_supporting = {
                'name': best_name,
                'buy_only': best_buy,
                'sell_only': best_sell,
            }

        return {
            'supporting_strategies': supporting,
            'best_supporting': best_supporting,
            'support_count': len(supporting),
            'total_count': total_count,
        }
