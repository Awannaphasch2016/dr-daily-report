# -*- coding: utf-8 -*-
"""Technical analysis module with NumPy type conversion for JSON serialization."""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def __init__(self):
        pass

    def calculate_sma(self, data, window):
        """Calculate Simple Moving Average"""
        return data['Close'].rolling(window=window).mean()

    def calculate_rsi(self, data, period=14):
        """Calculate Relative Strength Index"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = data['Close'].ewm(span=slow, adjust=False).mean()

        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()

        return macd, signal_line

    def calculate_bollinger_bands(self, data, window=20, num_std=2):
        """Calculate Bollinger Bands"""
        sma = data['Close'].rolling(window=window).mean()
        std = data['Close'].rolling(window=window).std()

        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)

        return upper_band, sma, lower_band

    def calculate_atr(self, data, period=14):
        """
        Calculate Average True Range (ATR) - Volatility Indicator
        ATR measures market volatility by decomposing the entire range of price movement
        """
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # True Range calculation
        tr1 = high - low  # Current high - current low
        tr2 = abs(high - close.shift())  # Current high - previous close
        tr3 = abs(low - close.shift())  # Current low - previous close
        
        # True Range is the maximum of the three
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the moving average of True Range
        atr = tr.rolling(window=period).mean()
        
        return atr

    def calculate_vwap(self, data):
        """
        Calculate Volume Weighted Average Price (VWAP)
        VWAP = Sum(Price * Volume) / Sum(Volume)
        Represents the average price weighted by volume
        """
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        vwap = (typical_price * data['Volume']).cumsum() / data['Volume'].cumsum()
        
        return vwap

    def calculate_uncertainty_score(self, data, atr_period=14):
        """
        Calculate Pricing Uncertainty Score (0-100 scale)
        
        Formula: Uncertainty = Buy-Sell Pressure × Volatility
        Where: Buy-Sell Pressure = Price Action × Volume
        
        Components:
        - ATR: Average True Range (volatility measure)
        - VWAP: Volume Weighted Average Price (price action with volume)
        - Volume Ratio: Current volume vs average volume
        
        Score Interpretation:
        0-25:   Low uncertainty (stable market)
        25-50:  Moderate uncertainty
        50-75:  High uncertainty
        75-100: Extreme uncertainty (volatile with strong buy/sell pressure)
        """
        try:
            # Calculate ATR (volatility component)
            atr = self.calculate_atr(data, period=atr_period)
            
            # Calculate VWAP (price action component)
            vwap = self.calculate_vwap(data)
            
            # Calculate volume ratio (volume pressure component)
            volume_sma = data['Volume'].rolling(window=20).mean()
            volume_ratio = data['Volume'] / volume_sma
            
            # Calculate price deviation from VWAP (price action component)
            price_deviation = abs(data['Close'] - vwap) / vwap
            
            # Buy-Sell Pressure = Price Action × Volume Ratio
            buy_sell_pressure = price_deviation * volume_ratio
            
            # Normalize ATR as percentage of price
            atr_normalized = atr / data['Close']
            
            # Pricing Uncertainty = Buy-Sell Pressure × Volatility
            uncertainty_raw = buy_sell_pressure * atr_normalized
            
            # Normalize to 0-100 scale using tanh function for smooth bounded output
            # tanh squashes values to [-1, 1], we scale to [0, 100]
            uncertainty_score = 50 * (1 + np.tanh(uncertainty_raw * 10))
            
            return uncertainty_score, atr, vwap
            
        except Exception as e:
            print(f"Error calculating uncertainty score: {str(e)}")
            return None, None, None

    def calculate_historical_indicators(self, hist_data):
        """
        Calculate all technical indicators for entire historical period
        Returns DataFrame with all indicators for each date
        """
        if hist_data is None or hist_data.empty:
            return None

        try:
            df = hist_data.copy()

            # Moving Averages
            df['SMA_20'] = self.calculate_sma(df, 20)
            df['SMA_50'] = self.calculate_sma(df, 50)
            df['SMA_200'] = self.calculate_sma(df, 200)

            # RSI
            df['RSI'] = self.calculate_rsi(df)

            # MACD
            df['MACD'], df['MACD_Signal'] = self.calculate_macd(df)

            # Bollinger Bands
            df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self.calculate_bollinger_bands(df)

            # Volume SMA
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()

            # Pricing Uncertainty Score Components
            df['Uncertainty_Score'], df['ATR'], df['VWAP'] = self.calculate_uncertainty_score(df)

            # Calculate ATR as percentage of price
            df['ATR_Percent'] = (df['ATR'] / df['Close']) * 100

            # Calculate price vs VWAP percentage
            df['Price_VWAP_Pct'] = ((df['Close'] - df['VWAP']) / df['VWAP']) * 100

            # Calculate volume ratio
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']

            return df

        except Exception as e:
            print(f"Error calculating historical indicators: {str(e)}")
            return None

    def _calculate_single_percentile(self, historical_values, current_value, frequency_functions=None):
        """Calculate percentile for a single indicator

        Returns:
            Dict with all values as Python primitives (int, float) - never NumPy types.
            Contract: Safe for JSON serialization and Aurora MySQL JSON storage.
        """
        if len(historical_values) == 0:
            return None

        # Calculate percentile using numpy instead of scipy
        percentile = (np.sum(historical_values <= current_value) / len(historical_values)) * 100

        # CONTRACT: Convert NumPy → Python primitives at SOURCE
        # Following CLAUDE.md: "Convert at source where data is created, not at boundaries"
        result = {
            'current_value': float(current_value),          # np.float64 → float
            'percentile': float(percentile),                # np.float64 → float
            'mean': float(historical_values.mean()),        # np.float64 → float
            'std': float(historical_values.std()),          # np.float64 → float
            'min': float(historical_values.min()),          # np.float64 → float
            'max': float(historical_values.max())           # np.float64 → float
        }

        if frequency_functions:
            for key, func in frequency_functions.items():
                # Convert frequency percentages to Python float
                freq_value = func(historical_values).sum() / len(historical_values) * 100
                result[key] = float(freq_value)

        return result
    
    def _calculate_rsi_percentile(self, valid_data, current_indicators):
        """Calculate RSI percentile"""
        if 'RSI' not in valid_data.columns or current_indicators.get('rsi') is None:
            return None
        
        rsi_values = valid_data['RSI'].dropna()
        freq_funcs = {
            'frequency_above_70': lambda x: x > 70,
            'frequency_below_30': lambda x: x < 30
        }
        return self._calculate_single_percentile(rsi_values, current_indicators['rsi'], freq_funcs)
    
    def _calculate_macd_percentile(self, valid_data, current_indicators):
        """Calculate MACD percentile"""
        if 'MACD' not in valid_data.columns or current_indicators.get('macd') is None:
            return None
        
        macd_values = valid_data['MACD'].dropna()
        freq_funcs = {'frequency_positive': lambda x: x > 0}
        return self._calculate_single_percentile(macd_values, current_indicators['macd'], freq_funcs)
    
    def _calculate_uncertainty_percentile(self, valid_data, current_indicators):
        """Calculate Uncertainty Score percentile"""
        if 'Uncertainty_Score' not in valid_data.columns or current_indicators.get('uncertainty_score') is None:
            return None
        
        uncertainty_values = valid_data['Uncertainty_Score'].dropna()
        freq_funcs = {
            'frequency_low': lambda x: x < 25,
            'frequency_high': lambda x: x > 75
        }
        return self._calculate_single_percentile(uncertainty_values, current_indicators['uncertainty_score'], freq_funcs)
    
    def _calculate_atr_percent_percentile(self, valid_data, current_indicators):
        """Calculate ATR percent percentile"""
        if 'ATR_Percent' not in valid_data.columns or current_indicators.get('atr') is None:
            return None
        
        atr_pct_values = valid_data['ATR_Percent'].dropna()
        current_price = current_indicators.get('current_price', 0)
        if current_price <= 0 or len(atr_pct_values) == 0:
            return None
        
        current_atr_pct = (current_indicators['atr'] / current_price) * 100
        freq_funcs = {
            'frequency_low_volatility': lambda x: x < 1,
            'frequency_high_volatility': lambda x: x > 4
        }
        return self._calculate_single_percentile(atr_pct_values, current_atr_pct, freq_funcs)
    
    def _calculate_vwap_percent_percentile(self, valid_data, current_indicators):
        """Calculate Price vs VWAP percent percentile"""
        if 'Price_VWAP_Pct' not in valid_data.columns or current_indicators.get('vwap') is None:
            return None
        
        vwap_pct_values = valid_data['Price_VWAP_Pct'].dropna()
        current_price = current_indicators.get('current_price', 0)
        current_vwap = current_indicators.get('vwap', 0)
        if current_vwap <= 0 or len(vwap_pct_values) == 0:
            return None
        
        current_vwap_pct = ((current_price - current_vwap) / current_vwap) * 100
        freq_funcs = {
            'frequency_above_3pct': lambda x: x > 3,
            'frequency_below_neg3pct': lambda x: x < -3
        }
        return self._calculate_single_percentile(vwap_pct_values, current_vwap_pct, freq_funcs)
    
    def _calculate_volume_ratio_percentile(self, valid_data, current_indicators):
        """Calculate Volume Ratio percentile"""
        if 'Volume_Ratio' not in valid_data.columns or current_indicators.get('volume') is None:
            return None
        
        volume_ratio_values = valid_data['Volume_Ratio'].dropna()
        current_volume = current_indicators.get('volume', 0)
        volume_sma = current_indicators.get('volume_sma', 1)
        if volume_sma <= 0 or len(volume_ratio_values) == 0:
            return None
        
        current_volume_ratio = current_volume / volume_sma
        freq_funcs = {
            'frequency_high_volume': lambda x: x > 2.0,
            'frequency_low_volume': lambda x: x < 0.7
        }
        return self._calculate_single_percentile(volume_ratio_values, current_volume_ratio, freq_funcs)
    
    def _calculate_sma_percentiles(self, valid_data, current_indicators):
        """Calculate SMA deviation percentiles for all periods"""
        sma_percentiles = {}
        
        for sma_period in [20, 50, 200]:
            sma_col = f'SMA_{sma_period}'
            sma_key = f'sma_{sma_period}'
            
            if sma_col not in valid_data.columns or current_indicators.get(sma_key) is None:
                continue
            
            current_sma = current_indicators[sma_key]
            current_price = current_indicators.get('current_price', 0)
            if current_price <= 0:
                continue
            
            sma_diff_pct = ((current_price - current_sma) / current_sma) * 100
            sma_diff_values = ((valid_data['Close'] - valid_data[sma_col]) / valid_data[sma_col] * 100).dropna()
            
            if len(sma_diff_values) > 0:
                freq_funcs = {'frequency_above_sma': lambda x: x > 0}
                result = self._calculate_single_percentile(sma_diff_values, sma_diff_pct, freq_funcs)
                if result:
                    sma_percentiles[f'{sma_key}_deviation'] = result
        
        return sma_percentiles

    def calculate_percentiles(self, historical_df, current_indicators):
        """
        Calculate percentile ranks for current indicator values based on historical distribution
        
        Args:
            historical_df: DataFrame with historical indicator values (from calculate_historical_indicators)
            current_indicators: Dict with current indicator values
            
        Returns:
            Dict with percentile information for each indicator
        """
        if historical_df is None or historical_df.empty:
            return {}

        try:
            percentiles = {}
            valid_data = historical_df.dropna()
            
            if valid_data.empty:
                return {}

            # Calculate each indicator percentile using helper methods
            rsi_result = self._calculate_rsi_percentile(valid_data, current_indicators)
            if rsi_result:
                percentiles['rsi'] = rsi_result

            macd_result = self._calculate_macd_percentile(valid_data, current_indicators)
            if macd_result:
                percentiles['macd'] = macd_result

            uncertainty_result = self._calculate_uncertainty_percentile(valid_data, current_indicators)
            if uncertainty_result:
                percentiles['uncertainty_score'] = uncertainty_result

            atr_result = self._calculate_atr_percent_percentile(valid_data, current_indicators)
            if atr_result:
                percentiles['atr_percent'] = atr_result

            vwap_result = self._calculate_vwap_percent_percentile(valid_data, current_indicators)
            if vwap_result:
                percentiles['price_vwap_percent'] = vwap_result

            volume_result = self._calculate_volume_ratio_percentile(valid_data, current_indicators)
            if volume_result:
                percentiles['volume_ratio'] = volume_result

            # SMA percentiles
            sma_percentiles = self._calculate_sma_percentiles(valid_data, current_indicators)
            percentiles.update(sma_percentiles)

            return percentiles

        except Exception as e:
            print(f"Error calculating percentiles: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def calculate_all_indicators(self, hist_data):
        """Calculate all technical indicators"""
        if hist_data is None or hist_data.empty:
            return None

        try:
            df = hist_data.copy()

            # Moving Averages
            df['SMA_20'] = self.calculate_sma(df, 20)
            df['SMA_50'] = self.calculate_sma(df, 50)
            df['SMA_200'] = self.calculate_sma(df, 200)

            # RSI
            df['RSI'] = self.calculate_rsi(df)

            # MACD
            df['MACD'], df['MACD_Signal'] = self.calculate_macd(df)

            # Bollinger Bands
            df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self.calculate_bollinger_bands(df)

            # Volume SMA
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()

            # Pricing Uncertainty Score Components
            df['Uncertainty_Score'], df['ATR'], df['VWAP'] = self.calculate_uncertainty_score(df)

            # Get latest indicators
            latest = df.iloc[-1]

            # CONTRACT: Convert all NumPy types to Python primitives
            # This is critical for JSON serialization to MySQL Aurora JSON column
            indicators = {
                'sma_20': float(latest['SMA_20']),
                'sma_50': float(latest['SMA_50']),
                'sma_200': float(latest['SMA_200']),
                'rsi': float(latest['RSI']),
                'macd': float(latest['MACD']),
                'macd_signal': float(latest['MACD_Signal']),
                'bb_upper': float(latest['BB_Upper']),
                'bb_middle': float(latest['BB_Middle']),
                'bb_lower': float(latest['BB_Lower']),
                'volume_sma': float(latest['Volume_SMA']),
                'current_price': float(latest['Close']),
                'volume': float(latest['Volume']),
                # New uncertainty indicators
                'uncertainty_score': float(latest['Uncertainty_Score']),
                'atr': float(latest['ATR']),
                'vwap': float(latest['VWAP'])
            }

            return indicators
        except Exception as e:
            print(f"Error calculating indicators: {str(e)}")
            return None

    def calculate_all_indicators_with_percentiles(self, hist_data):
        """
        Calculate all technical indicators with percentile analysis
        
        Returns:
            Dict with 'indicators' (current values) and 'percentiles' (statistical analysis)
        """
        if hist_data is None or hist_data.empty:
            raise ValueError("Cannot calculate indicators: hist_data is empty or None")

        try:
            # Calculate historical indicators for all periods
            historical_df = self.calculate_historical_indicators(hist_data)

            if historical_df is None or historical_df.empty:
                raise ValueError("Cannot calculate indicators: historical_df is empty or None")

            # Get current indicators
            current_indicators = self.calculate_all_indicators(hist_data)

            if current_indicators is None:
                raise ValueError("Cannot calculate indicators: current_indicators is None")

            # Calculate percentiles
            percentiles = self.calculate_percentiles(historical_df, current_indicators)

            return {
                'indicators': current_indicators,
                'percentiles': percentiles
            }

        except Exception as e:
            logger.error(
                f"Error calculating indicators with percentiles: {str(e)}",
                exc_info=True  # Includes full traceback in CloudWatch logs
            )
            return None

    def analyze_trend(self, indicators, price):
        """Analyze price trend"""
        if not indicators:
            return "ไม่สามารถวิเคราะห์ได้"

        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        sma_200 = indicators.get('sma_200')

        trends = []

        if sma_20 and sma_50 and sma_200:
            if price > sma_20 > sma_50 > sma_200:
                trends.append("แนวโน้มขาขึ้นแข็งแกร่ง")
            elif price > sma_20 > sma_50:
                trends.append("แนวโน้มขาขึ้น")
            elif price < sma_20 < sma_50 < sma_200:
                trends.append("แนวโน้มขาลงแข็งแกร่ง")
            elif price < sma_20 < sma_50:
                trends.append("แนวโน้มขาลง")
            else:
                trends.append("แนวโน้มไม่ชัดเจน")

        return " | ".join(trends) if trends else "ไม่สามารถวิเคราะห์ได้"

    def analyze_momentum(self, indicators):
        """Analyze momentum using RSI"""
        if not indicators:
            return "ไม่สามารถวิเคราะห์ได้"

        rsi = indicators.get('rsi')

        if rsi is None:
            return "ไม่มีข้อมูล RSI"

        if rsi > 70:
            return f"RSI {rsi:.2f} - ภาวะ Overbought (ซื้อมากเกินไป)"
        elif rsi < 30:
            return f"RSI {rsi:.2f} - ภาวะ Oversold (ขายมากเกินไป)"
        else:
            return f"RSI {rsi:.2f} - อยู่ในกรอบปกติ"

    def analyze_macd(self, indicators):
        """Analyze MACD signal"""
        if not indicators:
            return "ไม่สามารถวิเคราะห์ได้"

        macd = indicators.get('macd')
        signal = indicators.get('macd_signal')

        if macd is None or signal is None:
            return "ไม่มีข้อมูล MACD"

        if macd > signal:
            return f"MACD เหนือ Signal Line - สัญญาณซื้อ"
        else:
            return f"MACD ต่ำกว่า Signal Line - สัญญาณขาย"

    def analyze_bollinger(self, indicators):
        """Analyze Bollinger Bands"""
        if not indicators:
            return "ไม่สามารถวิเคราะห์ได้"

        price = indicators.get('current_price')
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        bb_middle = indicators.get('bb_middle')

        if not all([price, bb_upper, bb_lower, bb_middle]):
            return "ไม่มีข้อมูล Bollinger Bands"

        if price >= bb_upper:
            return f"ราคาแตะแนว Upper Band - อาจมีแรงขาย"
        elif price <= bb_lower:
            return f"ราคาแตะแนว Lower Band - อาจมีแรงซื้อ"
        elif price > bb_middle:
            return f"ราคาอยู่เหนือแนวกลาง - แนวโน้มบวก"
        else:
            return f"ราคาอยู่ใต้แนวกลาง - แนวโน้มลบ"

    def analyze_uncertainty(self, indicators):
        """Analyze Pricing Uncertainty Score"""
        if not indicators:
            return "ไม่สามารถวิเคราะห์ได้"

        uncertainty = indicators.get('uncertainty_score')
        atr = indicators.get('atr')
        vwap = indicators.get('vwap')
        price = indicators.get('current_price')

        if uncertainty is None:
            return "ไม่มีข้อมูล Uncertainty Score"

        # Interpret uncertainty level
        if uncertainty < 25:
            level = "ต่ำ (ตลาดเสถียร)"
            recommendation = "ความเสี่ยงต่ำ เหมาะสำหรับการถือระยะยาว"
        elif uncertainty < 50:
            level = "ปานกลาง"
            recommendation = "ความเสี่ยงปานกลาง ควรติดตามอย่างใกล้ชิด"
        elif uncertainty < 75:
            level = "สูง"
            recommendation = "ความเสี่ยงสูง ระวังความผันผวน"
        else:
            level = "สูงมาก (ผันผวนรุนแรง)"
            recommendation = "ความเสี่ยงสูงมาก เหมาะสำหรับนักเทรดมืออาชีพเท่านั้น"

        # Price position relative to VWAP
        if vwap and price:
            if price > vwap:
                vwap_position = f"ราคาเหนือ VWAP ({vwap:.2f}) - แรงซื้อเหนือกว่า"
            else:
                vwap_position = f"ราคาต่ำกว่า VWAP ({vwap:.2f}) - แรงขายเหนือกว่า"
        else:
            vwap_position = ""

        result = f"Uncertainty Score: {uncertainty:.2f}/100 - ระดับ{level}\n{recommendation}"
        if vwap_position:
            result += f"\n{vwap_position}"
        if atr:
            result += f"\nATR: {atr:.4f} (ความผันผวน)"

        return result

    def format_percentile_analysis(self, percentiles=None):
        """Thai reports don't show percentile section.

        Percentile data is still calculated in the workflow, just not displayed.
        Kept as method (not removed) to avoid breaking existing callers.

        Args:
            percentiles: Dict with percentile information (unused, kept for compatibility)

        Returns:
            Empty string (Thai reports don't show percentile analysis)
        """
        return ""
