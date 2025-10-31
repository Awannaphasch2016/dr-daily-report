import pandas as pd
import numpy as np
from scipy import stats

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
            
            # Filter out NaN values for calculations
            valid_data = historical_df.dropna()
            
            if valid_data.empty:
                return {}

            # RSI Percentiles (0-100 scale)
            if 'RSI' in valid_data.columns and current_indicators.get('rsi') is not None:
                rsi_values = valid_data['RSI'].dropna()
                if len(rsi_values) > 0:
                    current_rsi = current_indicators['rsi']
                    percentile = stats.percentileofscore(rsi_values, current_rsi, kind='rank')
                    percentiles['rsi'] = {
                        'current_value': current_rsi,
                        'percentile': percentile,
                        'mean': rsi_values.mean(),
                        'std': rsi_values.std(),
                        'min': rsi_values.min(),
                        'max': rsi_values.max(),
                        'frequency_above_70': (rsi_values > 70).sum() / len(rsi_values) * 100,
                        'frequency_below_30': (rsi_values < 30).sum() / len(rsi_values) * 100
                    }

            # MACD Percentiles
            if 'MACD' in valid_data.columns and current_indicators.get('macd') is not None:
                macd_values = valid_data['MACD'].dropna()
                if len(macd_values) > 0:
                    current_macd = current_indicators['macd']
                    percentile = stats.percentileofscore(macd_values, current_macd, kind='rank')
                    percentiles['macd'] = {
                        'current_value': current_macd,
                        'percentile': percentile,
                        'mean': macd_values.mean(),
                        'std': macd_values.std(),
                        'min': macd_values.min(),
                        'max': macd_values.max(),
                        'frequency_positive': (macd_values > 0).sum() / len(macd_values) * 100
                    }

            # Uncertainty Score Percentiles (0-100 scale)
            if 'Uncertainty_Score' in valid_data.columns and current_indicators.get('uncertainty_score') is not None:
                uncertainty_values = valid_data['Uncertainty_Score'].dropna()
                if len(uncertainty_values) > 0:
                    current_uncertainty = current_indicators['uncertainty_score']
                    percentile = stats.percentileofscore(uncertainty_values, current_uncertainty, kind='rank')
                    percentiles['uncertainty_score'] = {
                        'current_value': current_uncertainty,
                        'percentile': percentile,
                        'mean': uncertainty_values.mean(),
                        'std': uncertainty_values.std(),
                        'min': uncertainty_values.min(),
                        'max': uncertainty_values.max(),
                        'frequency_low': ((uncertainty_values < 25).sum() / len(uncertainty_values) * 100),
                        'frequency_high': ((uncertainty_values > 75).sum() / len(uncertainty_values) * 100)
                    }

            # ATR Percent Percentiles (volatility as % of price)
            if 'ATR_Percent' in valid_data.columns and current_indicators.get('atr') is not None:
                atr_pct_values = valid_data['ATR_Percent'].dropna()
                if len(atr_pct_values) > 0:
                    current_price = current_indicators.get('current_price', 0)
                    if current_price > 0:
                        current_atr_pct = (current_indicators['atr'] / current_price) * 100
                        percentile = stats.percentileofscore(atr_pct_values, current_atr_pct, kind='rank')
                        percentiles['atr_percent'] = {
                            'current_value': current_atr_pct,
                            'percentile': percentile,
                            'mean': atr_pct_values.mean(),
                            'std': atr_pct_values.std(),
                            'min': atr_pct_values.min(),
                            'max': atr_pct_values.max(),
                            'frequency_low_volatility': ((atr_pct_values < 1).sum() / len(atr_pct_values) * 100),
                            'frequency_high_volatility': ((atr_pct_values > 4).sum() / len(atr_pct_values) * 100)
                        }

            # Price vs VWAP Percent Percentiles
            if 'Price_VWAP_Pct' in valid_data.columns and current_indicators.get('vwap') is not None:
                vwap_pct_values = valid_data['Price_VWAP_Pct'].dropna()
                if len(vwap_pct_values) > 0:
                    current_price = current_indicators.get('current_price', 0)
                    current_vwap = current_indicators.get('vwap', 0)
                    if current_vwap > 0:
                        current_vwap_pct = ((current_price - current_vwap) / current_vwap) * 100
                        percentile = stats.percentileofscore(vwap_pct_values, current_vwap_pct, kind='rank')
                        percentiles['price_vwap_percent'] = {
                            'current_value': current_vwap_pct,
                            'percentile': percentile,
                            'mean': vwap_pct_values.mean(),
                            'std': vwap_pct_values.std(),
                            'min': vwap_pct_values.min(),
                            'max': vwap_pct_values.max(),
                            'frequency_above_3pct': ((vwap_pct_values > 3).sum() / len(vwap_pct_values) * 100),
                            'frequency_below_neg3pct': ((vwap_pct_values < -3).sum() / len(vwap_pct_values) * 100)
                        }

            # Volume Ratio Percentiles
            if 'Volume_Ratio' in valid_data.columns and current_indicators.get('volume') is not None:
                volume_ratio_values = valid_data['Volume_Ratio'].dropna()
                if len(volume_ratio_values) > 0:
                    current_volume = current_indicators.get('volume', 0)
                    volume_sma = current_indicators.get('volume_sma', 1)
                    if volume_sma > 0:
                        current_volume_ratio = current_volume / volume_sma
                        percentile = stats.percentileofscore(volume_ratio_values, current_volume_ratio, kind='rank')
                        percentiles['volume_ratio'] = {
                            'current_value': current_volume_ratio,
                            'percentile': percentile,
                            'mean': volume_ratio_values.mean(),
                            'std': volume_ratio_values.std(),
                            'min': volume_ratio_values.min(),
                            'max': volume_ratio_values.max(),
                            'frequency_high_volume': ((volume_ratio_values > 2.0).sum() / len(volume_ratio_values) * 100),
                            'frequency_low_volume': ((volume_ratio_values < 0.7).sum() / len(volume_ratio_values) * 100)
                        }

            # SMA Percentiles (20-day, 50-day, 200-day)
            for sma_period in [20, 50, 200]:
                sma_col = f'SMA_{sma_period}'
                sma_key = f'sma_{sma_period}'
                if sma_col in valid_data.columns and current_indicators.get(sma_key) is not None:
                    sma_values = valid_data[sma_col].dropna()
                    if len(sma_values) > 0:
                        current_sma = current_indicators[sma_key]
                        current_price = current_indicators.get('current_price', 0)
                        if current_price > 0:
                            # Calculate price vs SMA percentage
                            sma_diff_pct = ((current_price - current_sma) / current_sma) * 100
                            sma_diff_values = ((valid_data['Close'] - valid_data[sma_col]) / valid_data[sma_col] * 100).dropna()
                            
                            if len(sma_diff_values) > 0:
                                percentile = stats.percentileofscore(sma_diff_values, sma_diff_pct, kind='rank')
                                percentiles[f'{sma_key}_deviation'] = {
                                    'current_value': sma_diff_pct,
                                    'percentile': percentile,
                                    'mean': sma_diff_values.mean(),
                                    'std': sma_diff_values.std(),
                                    'min': sma_diff_values.min(),
                                    'max': sma_diff_values.max(),
                                    'frequency_above_sma': ((sma_diff_values > 0).sum() / len(sma_diff_values) * 100)
                                }

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

            indicators = {
                'sma_20': latest['SMA_20'],
                'sma_50': latest['SMA_50'],
                'sma_200': latest['SMA_200'],
                'rsi': latest['RSI'],
                'macd': latest['MACD'],
                'macd_signal': latest['MACD_Signal'],
                'bb_upper': latest['BB_Upper'],
                'bb_middle': latest['BB_Middle'],
                'bb_lower': latest['BB_Lower'],
                'volume_sma': latest['Volume_SMA'],
                'current_price': latest['Close'],
                'volume': latest['Volume'],
                # New uncertainty indicators
                'uncertainty_score': latest['Uncertainty_Score'],
                'atr': latest['ATR'],
                'vwap': latest['VWAP']
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
            return None

        try:
            # Calculate historical indicators for all periods
            historical_df = self.calculate_historical_indicators(hist_data)
            
            if historical_df is None or historical_df.empty:
                return None

            # Get current indicators
            current_indicators = self.calculate_all_indicators(hist_data)
            
            if current_indicators is None:
                return None

            # Calculate percentiles
            percentiles = self.calculate_percentiles(historical_df, current_indicators)

            return {
                'indicators': current_indicators,
                'percentiles': percentiles
            }

        except Exception as e:
            print(f"Error calculating indicators with percentiles: {str(e)}")
            import traceback
            traceback.print_exc()
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

    def format_percentile_analysis(self, percentiles):
        """
        Format percentile analysis into readable Thai text
        
        Args:
            percentiles: Dict with percentile information
            
        Returns:
            Formatted string describing percentile positions
        """
        if not percentiles:
            return ""

        lines = []
        lines.append("\n📊 **การวิเคราะห์เปอร์เซ็นไทล์ (Percentile Analysis):**\n")

        # RSI Percentiles
        if 'rsi' in percentiles:
            rsi_stats = percentiles['rsi']
            percentile = rsi_stats['percentile']
            current = rsi_stats['current_value']
            
            if percentile >= 90:
                level = "สูงมาก (อยู่ในช่วง 90% บนสุด)"
                interpretation = "RSI สูงมากในอดีต - ควรระวังภาวะ Overbought"
            elif percentile >= 75:
                level = "สูง (อยู่ในช่วง 75-90%)"
                interpretation = "RSI สูงกว่าปกติ - ตลาดอาจร้อนแรง"
            elif percentile >= 50:
                level = "ปานกลางสูง (อยู่ในช่วง 50-75%)"
                interpretation = "RSI สูงกว่าค่าเฉลี่ย - แรงซื้อดี"
            elif percentile >= 25:
                level = "ปานกลางต่ำ (อยู่ในช่วง 25-50%)"
                interpretation = "RSI ต่ำกว่าค่าเฉลี่ย - แรงซื้ออ่อน"
            else:
                level = "ต่ำ (อยู่ในช่วง 25% ล่างสุด)"
                interpretation = "RSI ต่ำมากในอดีต - อาจเป็นโอกาสซื้อ (Oversold)"
            
            lines.append(f"RSI: {current:.2f} (เปอร์เซ็นไทล์: {percentile:.1f}% - {level})")
            lines.append(f"  - {interpretation}")
            lines.append(f"  - ค่าเฉลี่ย: {rsi_stats['mean']:.2f}, ค่าเบี่ยงเบนมาตรฐาน: {rsi_stats['std']:.2f}")
            lines.append(f"  - ความถี่ที่ RSI > 70: {rsi_stats['frequency_above_70']:.1f}%")
            lines.append(f"  - ความถี่ที่ RSI < 30: {rsi_stats['frequency_below_30']:.1f}%\n")

        # MACD Percentiles
        if 'macd' in percentiles:
            macd_stats = percentiles['macd']
            percentile = macd_stats['percentile']
            current = macd_stats['current_value']
            
            if percentile >= 75:
                level = "สูงมาก"
                interpretation = "MACD สูงกว่าปกติ - แรงซื้อแรงมาก"
            elif percentile >= 50:
                level = "สูงกว่าค่าเฉลี่ย"
                interpretation = "MACD บวก - แรงซื้อเหนือกว่า"
            elif percentile >= 25:
                level = "ต่ำกว่าค่าเฉลี่ย"
                interpretation = "MACD ลบ - แรงขายเหนือกว่า"
            else:
                level = "ต่ำมาก"
                interpretation = "MACD ต่ำมาก - แรงขายหนัก"
            
            lines.append(f"MACD: {current:.4f} (เปอร์เซ็นไทล์: {percentile:.1f}% - {level})")
            lines.append(f"  - {interpretation}")
            lines.append(f"  - ค่าเฉลี่ย: {macd_stats['mean']:.4f}")
            lines.append(f"  - ความถี่ที่ MACD > 0: {macd_stats['frequency_positive']:.1f}%\n")

        # Uncertainty Score Percentiles
        if 'uncertainty_score' in percentiles:
            unc_stats = percentiles['uncertainty_score']
            percentile = unc_stats['percentile']
            current = unc_stats['current_value']
            
            if percentile >= 90:
                level = "สูงมาก (อยู่ในช่วง 90% บนสุด)"
                interpretation = "ความไม่แน่นอนสูงมากในอดีต - ตลาดผันผวนรุนแรง"
            elif percentile >= 75:
                level = "สูง (อยู่ในช่วง 75-90%)"
                interpretation = "ความไม่แน่นอนสูง - ตลาดผันผวน"
            elif percentile >= 50:
                level = "ปานกลางสูง (อยู่ในช่วง 50-75%)"
                interpretation = "ความไม่แน่นอนสูงกว่าปกติ"
            elif percentile >= 25:
                level = "ปานกลางต่ำ (อยู่ในช่วง 25-50%)"
                interpretation = "ความไม่แน่นอนต่ำกว่าปกติ - ตลาดค่อนข้างเสถียร"
            else:
                level = "ต่ำ (อยู่ในช่วง 25% ล่างสุด)"
                interpretation = "ความไม่แน่นอนต่ำมากในอดีต - ตลาดเสถียรมาก"
            
            lines.append(f"Uncertainty Score: {current:.2f}/100 (เปอร์เซ็นไทล์: {percentile:.1f}% - {level})")
            lines.append(f"  - {interpretation}")
            lines.append(f"  - ค่าเฉลี่ย: {unc_stats['mean']:.2f}")
            lines.append(f"  - ความถี่ที่ต่ำ (<25): {unc_stats['frequency_low']:.1f}%")
            lines.append(f"  - ความถี่ที่สูง (>75): {unc_stats['frequency_high']:.1f}%\n")

        # ATR Percent Percentiles
        if 'atr_percent' in percentiles:
            atr_stats = percentiles['atr_percent']
            percentile = atr_stats['percentile']
            current = atr_stats['current_value']
            
            if percentile >= 90:
                level = "สูงมาก (อยู่ในช่วง 90% บนสุด)"
                interpretation = "ความผันผวนสูงมากในอดีต - ตลาดผันผวนรุนแรง"
            elif percentile >= 75:
                level = "สูง (อยู่ในช่วง 75-90%)"
                interpretation = "ความผันผวนสูง - ตลาดผันผวน"
            elif percentile >= 50:
                level = "ปานกลางสูง"
                interpretation = "ความผันผวนสูงกว่าปกติ"
            elif percentile >= 25:
                level = "ปานกลางต่ำ"
                interpretation = "ความผันผวนต่ำกว่าปกติ - ตลาดเสถียร"
            else:
                level = "ต่ำ (อยู่ในช่วง 25% ล่างสุด)"
                interpretation = "ความผันผวนต่ำมากในอดีต - ตลาดเสถียรมาก"
            
            lines.append(f"ATR (%): {current:.2f}% (เปอร์เซ็นไทล์: {percentile:.1f}% - {level})")
            lines.append(f"  - {interpretation}")
            lines.append(f"  - ค่าเฉลี่ย: {atr_stats['mean']:.2f}%")
            lines.append(f"  - ความถี่ที่ความผันผวนต่ำ (<1%): {atr_stats['frequency_low_volatility']:.1f}%")
            lines.append(f"  - ความถี่ที่ความผันผวนสูง (>4%): {atr_stats['frequency_high_volatility']:.1f}%\n")

        # Volume Ratio Percentiles
        if 'volume_ratio' in percentiles:
            vol_stats = percentiles['volume_ratio']
            percentile = vol_stats['percentile']
            current = vol_stats['current_value']
            
            if percentile >= 90:
                level = "สูงมาก (อยู่ในช่วง 90% บนสุด)"
                interpretation = "ปริมาณซื้อขายสูงมากในอดีต - มีเหตุการณ์สำคัญ"
            elif percentile >= 75:
                level = "สูง (อยู่ในช่วง 75-90%)"
                interpretation = "ปริมาณซื้อขายสูง - ความสนใจเพิ่มขึ้น"
            elif percentile >= 50:
                level = "ปานกลางสูง"
                interpretation = "ปริมาณซื้อขายสูงกว่าปกติ"
            elif percentile >= 25:
                level = "ปานกลางต่ำ"
                interpretation = "ปริมาณซื้อขายต่ำกว่าปกติ"
            else:
                level = "ต่ำ (อยู่ในช่วง 25% ล่างสุด)"
                interpretation = "ปริมาณซื้อขายต่ำมากในอดีต - ตลาดเงียบ"
            
            lines.append(f"Volume Ratio: {current:.2f}x (เปอร์เซ็นไทล์: {percentile:.1f}% - {level})")
            lines.append(f"  - {interpretation}")
            lines.append(f"  - ค่าเฉลี่ย: {vol_stats['mean']:.2f}x")
            lines.append(f"  - ความถี่ที่ปริมาณสูง (>2x): {vol_stats['frequency_high_volume']:.1f}%")
            lines.append(f"  - ความถี่ที่ปริมาณต่ำ (<0.7x): {vol_stats['frequency_low_volume']:.1f}%\n")

        return "\n".join(lines)
