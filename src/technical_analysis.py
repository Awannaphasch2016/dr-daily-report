import pandas as pd
import numpy as np

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
