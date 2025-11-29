#!/usr/bin/env python3
"""
Verify Pricing Uncertainty Score implementation.

Usage: python scripts/verify_uncertainty_score.py
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.analysis.technical_analysis import TechnicalAnalyzer

def generate_sample_data(days=100):
    """Generate sample stock data for testing"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Simulate price movement
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, days)
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV data
    data = pd.DataFrame({
        'Open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'High': prices * (1 + np.random.uniform(0, 0.03, days)),
        'Low': prices * (1 + np.random.uniform(-0.03, 0, days)),
        'Close': prices,
        'Volume': np.random.uniform(1000000, 5000000, days)
    }, index=dates)
    
    return data

def test_uncertainty_score():
    """Test the uncertainty score calculation"""
    print("=" * 70)
    print("Testing Pricing Uncertainty Score Implementation")
    print("=" * 70)
    
    # Initialize analyzer
    analyzer = TechnicalAnalyzer()
    
    # Generate test data
    print("\n1. Generating sample stock data...")
    data = generate_sample_data(days=250)  # Need enough data for 200-day SMA
    print(f"   ✓ Generated {len(data)} days of data")
    print(f"   Price range: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
    
    # Test individual methods
    print("\n2. Testing ATR calculation...")
    atr = analyzer.calculate_atr(data)
    print(f"   ✓ ATR calculated: Latest value = {atr.iloc[-1]:.4f}")
    
    print("\n3. Testing VWAP calculation...")
    vwap = analyzer.calculate_vwap(data)
    print(f"   ✓ VWAP calculated: Latest value = {vwap.iloc[-1]:.2f}")
    print(f"   Current price: {data['Close'].iloc[-1]:.2f}")
    
    print("\n4. Testing Uncertainty Score calculation...")
    uncertainty, atr_result, vwap_result = analyzer.calculate_uncertainty_score(data)
    print(f"   ✓ Uncertainty Score: {uncertainty.iloc[-1]:.2f}/100")
    
    # Interpret the score
    score = uncertainty.iloc[-1]
    if score < 25:
        level = "LOW (Stable Market)"
    elif score < 50:
        level = "MODERATE"
    elif score < 75:
        level = "HIGH"
    else:
        level = "EXTREME (Highly Volatile)"
    print(f"   Interpretation: {level}")
    
    # Test full integration
    print("\n5. Testing integration with calculate_all_indicators()...")
    indicators = analyzer.calculate_all_indicators(data)
    
    if indicators:
        print("   ✓ All indicators calculated successfully!")
        print("\n   New Indicators Added:")
        print(f"   - Uncertainty Score: {indicators.get('uncertainty_score', 'N/A'):.2f}")
        print(f"   - ATR: {indicators.get('atr', 'N/A'):.4f}")
        print(f"   - VWAP: {indicators.get('vwap', 'N/A'):.2f}")
        
        # Test analysis method
        print("\n6. Testing analyze_uncertainty() method...")
        analysis = analyzer.analyze_uncertainty(indicators)
        print("   Thai Analysis Output:")
        print("   " + "\n   ".join(analysis.split("\n")))
    else:
        print("   ✗ Error calculating indicators")
        return False
    
    print("\n" + "=" * 70)
    print("✓ All tests passed successfully!")
    print("=" * 70)
    
    # Display summary statistics
    print("\nSummary Statistics:")
    print(f"  Average Uncertainty: {uncertainty.mean():.2f}")
    print(f"  Max Uncertainty: {uncertainty.max():.2f}")
    print(f"  Min Uncertainty: {uncertainty.min():.2f}")
    print(f"  Std Dev: {uncertainty.std():.2f}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_uncertainty_score()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
