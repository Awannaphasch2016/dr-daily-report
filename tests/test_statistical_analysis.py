#!/usr/bin/env python3
"""
Test suite for statistical analysis (percentile) functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import DataFetcher
from src.technical_analysis import TechnicalAnalyzer
import pandas as pd
import numpy as np
from scipy import stats

def test_calculate_historical_indicators():
    """Test that historical indicators are calculated correctly"""
    print("\n🔍 Test 1: Calculate Historical Indicators")
    
    analyzer = TechnicalAnalyzer()
    
    # Create mock historical data
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    hist_data = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(100, 200, 100),
        'Low': np.random.uniform(100, 200, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)
    
    result = analyzer.calculate_historical_indicators(hist_data)
    
    assert result is not None, "Should return DataFrame"
    assert len(result) == 100, "Should have 100 rows"
    assert 'RSI' in result.columns, "Should have RSI column"
    assert 'MACD' in result.columns, "Should have MACD column"
    assert 'SMA_20' in result.columns, "Should have SMA_20 column"
    assert 'Uncertainty_Score' in result.columns, "Should have Uncertainty_Score column"
    assert 'ATR_Percent' in result.columns, "Should have ATR_Percent column"
    
    print("✅ Test 1 passed: Historical indicators calculated correctly")

def test_calculate_percentiles():
    """Test percentile calculation"""
    print("\n🔍 Test 2: Calculate Percentiles")
    
    analyzer = TechnicalAnalyzer()
    
    # Create mock historical data with known values
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    hist_data = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(100, 200, 100),
        'Low': np.random.uniform(100, 200, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)
    
    historical_df = analyzer.calculate_historical_indicators(hist_data)
    
    # Get current indicators
    current_indicators = analyzer.calculate_all_indicators(hist_data)
    
    # Calculate percentiles
    percentiles = analyzer.calculate_percentiles(historical_df, current_indicators)
    
    assert isinstance(percentiles, dict), "Should return dictionary"
    
    # Check RSI percentiles if available
    if 'rsi' in percentiles:
        rsi_stats = percentiles['rsi']
        assert 'percentile' in rsi_stats, "Should have percentile"
        assert 'mean' in rsi_stats, "Should have mean"
        assert 'std' in rsi_stats, "Should have std"
        assert 0 <= rsi_stats['percentile'] <= 100, "Percentile should be 0-100"
        assert 'frequency_above_70' in rsi_stats, "Should have frequency_above_70"
        assert 'frequency_below_30' in rsi_stats, "Should have frequency_below_30"
    
    print("✅ Test 2 passed: Percentiles calculated correctly")

def test_percentile_rank_calculation():
    """Test that percentile ranks are mathematically correct"""
    print("\n🔍 Test 3: Percentile Rank Calculation")
    
    # Create simple test data
    test_values = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    current_value = 75
    
    # Calculate percentile rank
    percentile = stats.percentileofscore(test_values, current_value, kind='rank')
    
    # Should be around 70-80% (75 is above 7 out of 10 values)
    assert 70 <= percentile <= 80, f"Percentile should be ~75%, got {percentile}%"
    
    print(f"✅ Test 3 passed: Percentile rank = {percentile:.1f}% (expected ~75%)")

def test_frequency_calculations():
    """Test frequency calculations for indicator thresholds"""
    print("\n🔍 Test 4: Frequency Calculations")
    
    analyzer = TechnicalAnalyzer()
    
    # Create test data with known distribution
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    # Create RSI values: 30 values below 30, 40 values between 30-70, 30 values above 70
    rsi_values = np.concatenate([
        np.random.uniform(0, 30, 30),
        np.random.uniform(30, 70, 40),
        np.random.uniform(70, 100, 30)
    ])
    
    hist_data = pd.DataFrame({
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(100, 200, 100),
        'Low': np.random.uniform(100, 200, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)
    
    # Manually set RSI values
    historical_df = analyzer.calculate_historical_indicators(hist_data)
    historical_df['RSI'] = pd.Series(rsi_values, index=historical_df.index)
    
    current_indicators = analyzer.calculate_all_indicators(hist_data)
    current_indicators['rsi'] = 50  # Middle value
    
    percentiles = analyzer.calculate_percentiles(historical_df, current_indicators)
    
    if 'rsi' in percentiles:
        rsi_stats = percentiles['rsi']
        freq_above_70 = rsi_stats['frequency_above_70']
        freq_below_30 = rsi_stats['frequency_below_30']
        
        # Should be approximately 30% above 70 and 30% below 30
        assert 25 <= freq_above_70 <= 35, f"Frequency above 70 should be ~30%, got {freq_above_70}%"
        assert 25 <= freq_below_30 <= 35, f"Frequency below 30 should be ~30%, got {freq_below_30}%"
    
    print("✅ Test 4 passed: Frequency calculations correct")

def test_format_percentile_analysis():
    """Test that percentile analysis formatting works"""
    print("\n🔍 Test 5: Format Percentile Analysis")
    
    analyzer = TechnicalAnalyzer()
    
    # Create mock percentile data
    percentiles = {
        'rsi': {
            'current_value': 75.5,
            'percentile': 85.0,
            'mean': 55.0,
            'std': 15.0,
            'min': 20.0,
            'max': 90.0,
            'frequency_above_70': 25.0,
            'frequency_below_30': 10.0
        }
    }
    
    formatted = analyzer.format_percentile_analysis(percentiles)
    
    assert isinstance(formatted, str), "Should return string"
    assert 'RSI' in formatted, "Should contain RSI"
    assert 'เปอร์เซ็นไทล์' in formatted, "Should contain Thai text"
    assert '85' in formatted or '85.0' in formatted, "Should contain percentile value"
    
    print("✅ Test 5 passed: Formatting works correctly")

def test_integration_with_agent():
    """Test integration with agent workflow"""
    print("\n🔍 Test 6: Integration with Agent")
    
    from src.agent import TickerAnalysisAgent
    
    # Create agent
    agent = TickerAnalysisAgent()
    
    # Create mock state
    state = {
        "messages": [],
        "ticker": "AAPL",
        "ticker_data": {
            'history': pd.DataFrame({
                'Open': np.random.uniform(100, 200, 100),
                'High': np.random.uniform(100, 200, 100),
                'Low': np.random.uniform(100, 200, 100),
                'Close': np.random.uniform(100, 200, 100),
                'Volume': np.random.uniform(1000000, 10000000, 100)
            }, index=pd.date_range('2024-01-01', periods=100, freq='D')),
            'date': '2024-12-01'  # Use string instead of Timestamp for database compatibility
        },
        "indicators": {},
        "percentiles": {},
        "news": [],
        "news_summary": {},
        "report": "",
        "error": ""
    }
    
    # Test analyze_technical method
    result_state = agent.workflow_nodes.analyze_technical(state)
    
    assert 'indicators' in result_state, "Should have indicators"
    assert 'percentiles' in result_state, "Should have percentiles"
    assert result_state.get('error') == '', "Should not have error"
    
    print("✅ Test 6 passed: Integration with agent works")

def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("STATISTICAL ANALYSIS TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Calculate Historical Indicators", test_calculate_historical_indicators),
        ("Calculate Percentiles", test_calculate_percentiles),
        ("Percentile Rank Calculation", test_percentile_rank_calculation),
        ("Frequency Calculations", test_frequency_calculations),
        ("Format Percentile Analysis", test_format_percentile_analysis),
        ("Integration with Agent", test_integration_with_agent),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            test_func()
            results.append(True)
        except Exception as e:
            print(f"❌ {name} test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
