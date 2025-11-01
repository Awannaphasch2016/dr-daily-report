"""
Chart Generator for Stock Technical Analysis

Generates professional-looking charts with:
- Candlestick price chart
- Volume bars
- Technical indicators (SMA, Bollinger Bands)
- RSI subplot
- MACD subplot
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64


class ChartGenerator:
    """Generate technical analysis charts for stock data"""

    def __init__(self):
        # Chart styling
        self.fig_size = (14, 10)
        self.dpi = 100

        # Colors
        self.color_up = '#26a69a'  # Green for up candles
        self.color_down = '#ef5350'  # Red for down candles
        self.color_sma20 = '#2962FF'  # Blue
        self.color_sma50 = '#FF6D00'  # Orange
        self.color_sma200 = '#AA00FF'  # Purple
        self.color_bb = '#B0BEC5'  # Gray for Bollinger Bands
        self.color_volume_up = '#26a69a'
        self.color_volume_down = '#ef5350'
        self.color_rsi = '#9C27B0'  # Purple
        self.color_macd = '#2196F3'  # Blue
        self.color_signal = '#FF9800'  # Orange

    def generate_chart(self, ticker_data: dict, indicators: dict,
                      ticker_symbol: str, days: int = 90) -> str:
        """
        Generate comprehensive technical analysis chart

        Args:
            ticker_data: Dict with 'history' DataFrame (OHLCV data)
            indicators: Dict with technical indicators
            ticker_symbol: Ticker symbol for chart title
            days: Number of days to display (default 90)

        Returns:
            Base64-encoded PNG image string
        """
        # Get historical data
        df = ticker_data.get('history')
        if df is None or df.empty:
            raise ValueError("No historical data available")

        # Limit to specified days
        df = df.tail(days).copy()

        # Calculate additional data needed for chart
        df = self._prepare_dataframe(df, indicators)

        # Create figure with subplots
        fig = plt.figure(figsize=self.fig_size, dpi=self.dpi)
        gs = fig.add_gridspec(4, 1, height_ratios=[3, 0.8, 1, 1], hspace=0.05)

        # Create axes
        ax_price = fig.add_subplot(gs[0])
        ax_volume = fig.add_subplot(gs[1], sharex=ax_price)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_price)
        ax_macd = fig.add_subplot(gs[3], sharex=ax_price)

        # Plot each component
        self._plot_candlesticks(ax_price, df)
        self._plot_technical_indicators(ax_price, df, indicators)
        self._plot_volume(ax_volume, df)
        self._plot_rsi(ax_rsi, df, indicators)
        self._plot_macd(ax_macd, df, indicators)

        # Format chart
        self._format_chart(ax_price, ax_volume, ax_rsi, ax_macd,
                          df, ticker_symbol, ticker_data)

        # Convert to base64
        return self._fig_to_base64(fig)

    def _prepare_dataframe(self, df: pd.DataFrame, indicators: dict) -> pd.DataFrame:
        """Prepare DataFrame with all needed calculations"""
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Add color for candles
        df['color'] = df.apply(
            lambda row: self.color_up if row['Close'] >= row['Open']
            else self.color_down, axis=1
        )

        # Add volume color
        df['volume_color'] = df.apply(
            lambda row: self.color_volume_up if row['Close'] >= row['Open']
            else self.color_volume_down, axis=1
        )

        return df

    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlestick chart"""
        # Calculate candle widths
        if len(df) > 1:
            time_diff = (df.index[1] - df.index[0]).total_seconds() / 86400
            width = time_diff * 0.8
        else:
            width = 0.8

        # Plot candles
        for idx, row in df.iterrows():
            # Draw wick (high-low line)
            ax.plot([idx, idx], [row['Low'], row['High']],
                   color='black', linewidth=0.8, alpha=0.8)

            # Draw body (open-close rectangle)
            body_height = abs(row['Close'] - row['Open'])
            body_bottom = min(row['Open'], row['Close'])

            rect = Rectangle(
                (mdates.date2num(idx) - width/2, body_bottom),
                width, body_height,
                facecolor=row['color'],
                edgecolor='black',
                linewidth=0.5,
                alpha=0.9
            )
            ax.add_patch(rect)

    def _plot_technical_indicators(self, ax, df: pd.DataFrame, indicators: dict):
        """Plot SMA lines and Bollinger Bands"""
        # Get SMA values from last N days
        sma_20_values = []
        sma_50_values = []
        sma_200_values = []

        # Calculate SMAs for each point (using pandas rolling)
        if 'Close' in df.columns:
            sma_20_values = df['Close'].rolling(window=20, min_periods=1).mean()
            sma_50_values = df['Close'].rolling(window=50, min_periods=1).mean()
            sma_200_values = df['Close'].rolling(window=200, min_periods=1).mean()

        # Plot SMA lines
        if len(sma_20_values) > 0:
            ax.plot(df.index, sma_20_values,
                   label='SMA 20', color=self.color_sma20, linewidth=1.5, alpha=0.8)

        if len(sma_50_values) > 0 and not sma_50_values.isna().all():
            ax.plot(df.index, sma_50_values,
                   label='SMA 50', color=self.color_sma50, linewidth=1.5, alpha=0.8)

        if len(sma_200_values) > 0 and not sma_200_values.isna().all():
            ax.plot(df.index, sma_200_values,
                   label='SMA 200', color=self.color_sma200, linewidth=1.5, alpha=0.8)

        # Plot Bollinger Bands if available
        bb_upper = indicators.get('bb_upper')
        bb_middle = indicators.get('bb_middle')
        bb_lower = indicators.get('bb_lower')

        if bb_upper and bb_middle and bb_lower:
            # Calculate BB for all points
            bb_period = 20
            rolling_std = df['Close'].rolling(window=bb_period).std()
            bb_middle_line = df['Close'].rolling(window=bb_period).mean()
            bb_upper_line = bb_middle_line + (rolling_std * 2)
            bb_lower_line = bb_middle_line - (rolling_std * 2)

            ax.plot(df.index, bb_upper_line,
                   color=self.color_bb, linewidth=1, alpha=0.5, linestyle='--')
            ax.plot(df.index, bb_lower_line,
                   color=self.color_bb, linewidth=1, alpha=0.5, linestyle='--')
            ax.fill_between(df.index, bb_upper_line, bb_lower_line,
                           color=self.color_bb, alpha=0.1)

    def _plot_volume(self, ax, df: pd.DataFrame):
        """Plot volume bars"""
        # Calculate bar width
        if len(df) > 1:
            time_diff = (df.index[1] - df.index[0]).total_seconds() / 86400
            width = time_diff * 0.8
        else:
            width = 0.8

        # Plot volume bars
        for idx, row in df.iterrows():
            ax.bar(idx, row['Volume'],
                  width=width,
                  color=row['volume_color'],
                  alpha=0.5)

        ax.set_ylabel('Volume', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K')
        )

    def _plot_rsi(self, ax, df: pd.DataFrame, indicators: dict):
        """Plot RSI indicator"""
        rsi_period = 14

        # Calculate RSI for all points
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi_values = 100 - (100 / (1 + rs))

        # Plot RSI line
        ax.plot(df.index, rsi_values,
               color=self.color_rsi, linewidth=1.5, label='RSI(14)')

        # Add overbought/oversold lines
        ax.axhline(y=70, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.axhline(y=30, color='green', linestyle='--', linewidth=0.8, alpha=0.5)
        ax.axhline(y=50, color='gray', linestyle=':', linewidth=0.5, alpha=0.3)

        # Fill overbought/oversold zones
        ax.fill_between(df.index, 70, 100, color='red', alpha=0.05)
        ax.fill_between(df.index, 0, 30, color='green', alpha=0.05)

        ax.set_ylabel('RSI', fontsize=9)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=8)

    def _plot_macd(self, ax, df: pd.DataFrame, indicators: dict):
        """Plot MACD indicator"""
        # Calculate MACD for all points
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        # Plot MACD histogram
        colors = ['green' if x >= 0 else 'red' for x in histogram]
        ax.bar(df.index, histogram, color=colors, alpha=0.3, width=0.8)

        # Plot MACD and Signal lines
        ax.plot(df.index, macd_line,
               color=self.color_macd, linewidth=1.5, label='MACD')
        ax.plot(df.index, signal_line,
               color=self.color_signal, linewidth=1.5, label='Signal')

        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        ax.set_ylabel('MACD', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=8)

    def _format_chart(self, ax_price, ax_volume, ax_rsi, ax_macd,
                     df: pd.DataFrame, ticker_symbol: str, ticker_data: dict):
        """Format and style the chart"""
        # Title
        company_name = ticker_data.get('company_name', ticker_symbol)
        current_price = df['Close'].iloc[-1]
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[0]
        price_change_pct = (price_change / df['Close'].iloc[0]) * 100

        title = f'{company_name} ({ticker_symbol}) - ${current_price:.2f} '
        title += f'{"+" if price_change >= 0 else ""}{price_change:.2f} '
        title += f'({price_change_pct:+.2f}%)'

        ax_price.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # Price chart formatting
        ax_price.set_ylabel('Price ($)', fontsize=10)
        ax_price.grid(True, alpha=0.3)
        ax_price.legend(loc='upper left', fontsize=8)

        # Remove x-axis labels from all but bottom chart
        plt.setp(ax_price.get_xticklabels(), visible=False)
        plt.setp(ax_volume.get_xticklabels(), visible=False)
        plt.setp(ax_rsi.get_xticklabels(), visible=False)

        # Format x-axis on bottom chart
        ax_macd.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax_macd.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax_macd.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax_macd.set_xlabel('Date', fontsize=10)

        # Tight layout
        plt.tight_layout()

    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        return img_base64

    def save_chart(self, ticker_data: dict, indicators: dict,
                   ticker_symbol: str, filepath: str, days: int = 90):
        """
        Generate and save chart to file

        Args:
            ticker_data: Dict with 'history' DataFrame
            indicators: Dict with technical indicators
            ticker_symbol: Ticker symbol
            filepath: Path to save PNG file
            days: Number of days to display
        """
        # Get historical data
        df = ticker_data.get('history')
        if df is None or df.empty:
            raise ValueError("No historical data available")

        df = df.tail(days).copy()
        df = self._prepare_dataframe(df, indicators)

        # Create figure
        fig = plt.figure(figsize=self.fig_size, dpi=self.dpi)
        gs = fig.add_gridspec(4, 1, height_ratios=[3, 0.8, 1, 1], hspace=0.05)

        ax_price = fig.add_subplot(gs[0])
        ax_volume = fig.add_subplot(gs[1], sharex=ax_price)
        ax_rsi = fig.add_subplot(gs[2], sharex=ax_price)
        ax_macd = fig.add_subplot(gs[3], sharex=ax_price)

        # Plot components
        self._plot_candlesticks(ax_price, df)
        self._plot_technical_indicators(ax_price, df, indicators)
        self._plot_volume(ax_volume, df)
        self._plot_rsi(ax_rsi, df, indicators)
        self._plot_macd(ax_macd, df, indicators)

        # Format
        self._format_chart(ax_price, ax_volume, ax_rsi, ax_macd,
                          df, ticker_symbol, ticker_data)

        # Save
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        print(f"Chart saved to: {filepath}")
