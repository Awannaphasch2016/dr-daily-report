"""Strategy analysis utilities for extracting signals and checking alignment"""

from typing import Dict, Optional
import pandas as pd
from src.strategy import SMAStrategyBacktester


class StrategyAnalyzer:
    """Analyzes strategy performance and extracts signals"""
    
    def __init__(self, strategy_backtester: SMAStrategyBacktester):
        """Initialize with a strategy backtester"""
        self.strategy_backtester = strategy_backtester
    
    def get_last_buy_signal(self, hist_data: pd.DataFrame) -> Optional[Dict]:
        """Get last buy signal information"""
        try:
            df = self.strategy_backtester.detect_signals(hist_data)
            if df is None or df.empty:
                return None
            
            buy_signals = df[df['Buy_Signal'] == True]
            if buy_signals.empty:
                return None
            
            last_buy = buy_signals.iloc[-1]
            return {
                'date': last_buy.name,
                'price': float(last_buy['Close']),
                'sma_fast': float(last_buy['SMA_Fast']) if pd.notna(last_buy['SMA_Fast']) else None,
                'sma_slow': float(last_buy['SMA_Slow']) if pd.notna(last_buy['SMA_Slow']) else None
            }
        except Exception as e:
            print(f"Error getting last buy signal: {str(e)}")
            return None
    
    def get_last_sell_signal(self, hist_data: pd.DataFrame) -> Optional[Dict]:
        """Get last sell signal information"""
        if not self.strategy_backtester:
            return None
        try:
            df = self.strategy_backtester.detect_signals(hist_data)
            if df is None or df.empty:
                return None
            
            sell_signals = df[df['Sell_Signal'] == True]
            if sell_signals.empty:
                return None
            
            last_sell = sell_signals.iloc[-1]
            return {
                'date': last_sell.name,
                'price': float(last_sell['Close']),
                'sma_fast': float(last_sell['SMA_Fast']) if pd.notna(last_sell['SMA_Fast']) else None,
                'sma_slow': float(last_sell['SMA_Slow']) if pd.notna(last_sell['SMA_Slow']) else None
            }
        except Exception as e:
            print(f"Error getting last sell signal: {str(e)}")
            return None
    
    def extract_recommendation(self, report: str) -> str:
        """Extract BUY/SELL/HOLD recommendation from report"""
        report_upper = report.upper()
        
        # Look for BUY signals
        if 'BUY MORE' in report_upper or 'BUY' in report_upper:
            if '????? BUY' in report or '????? BUY MORE' in report or 'BUY MORE' in report_upper:
                return 'BUY'
        
        # Look for SELL signals
        if 'SELL' in report_upper:
            if '????? SELL' in report or 'SELL' in report_upper:
                return 'SELL'
        
        # Default to HOLD
        return 'HOLD'
    
    def check_strategy_alignment(self, recommendation: str, strategy_performance: Dict) -> bool:
        """Check if strategy performance aligns with recommendation"""
        if not strategy_performance or not strategy_performance.get('buy_only') or not strategy_performance.get('sell_only'):
            return False
        
        buy_perf = strategy_performance['buy_only']
        sell_perf = strategy_performance['sell_only']
        
        # Check if we have valid performance data
        buy_return = buy_perf.get('total_return_pct', 0)
        buy_sharpe = buy_perf.get('sharpe_ratio', 0)
        buy_win_rate = buy_perf.get('win_rate', 0)
        
        sell_return = sell_perf.get('total_return_pct', 0)
        sell_sharpe = sell_perf.get('sharpe_ratio', 0)
        sell_win_rate = sell_perf.get('win_rate', 0)
        
        if recommendation == 'BUY':
            # For BUY recommendation, buy_only strategy should perform well
            # Consider aligned if: positive return OR good sharpe (>0.5) OR good win rate (>50%)
            return buy_return > 0 or buy_sharpe > 0.5 or buy_win_rate > 50
        
        elif recommendation == 'SELL':
            # For SELL recommendation, sell_only strategy should perform well
            # Consider aligned if: positive return OR good sharpe (>0.5) OR good win rate (>50%)
            return sell_return > 0 or sell_sharpe > 0.5 or sell_win_rate > 50
        
        # For HOLD, we don't include strategy data
        return False
