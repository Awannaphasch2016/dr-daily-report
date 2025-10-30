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
                'volume': latest['Volume']
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
