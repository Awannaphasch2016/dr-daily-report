"""
Bokeh-based Stock Tiles Visualization
Converts D3.js tiles visualization to Bokeh
"""
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJS, HoverTool, TapTool, OpenURL
from bokeh.layouts import column, row
from bokeh.embed import components
import math


# Tile dimensions - compact for high density
TILE_WIDTH = 180
TILE_HEIGHT = 160
TILE_PADDING = 12

# Sector colors (matching backend)
SECTOR_COLORS = {
    'Technology': '#3498db',
    'Healthcare': '#e74c3c',
    'Financial Services': '#f39c12',
    'Consumer Cyclical': '#9b59b6',
    'Communication Services': '#1abc9c',
    'Industrials': '#34495e',
    'Consumer Defensive': '#e67e22',
    'Energy': '#f1c40f',
    'Utilities': '#16a085',
    'Real Estate': '#c0392b',
    'Basic Materials': '#95a5a6',
    'Unknown': '#7f8c8d'
}


def create_tiles_visualization(data, container_width=1600):
    """
    Create Bokeh visualization for stock tiles
    
    Args:
        data: List of ticker data dictionaries
        container_width: Width of container in pixels
        
    Returns:
        Tuple of (script, div) for embedding in HTML
    """
    if not data:
        return '', '<div class="empty-state">No data available</div>'
    
    # Prepare data for ColumnDataSource
    tiles_data = prepare_tiles_data(data, container_width)
    
    # Extract cols for height calculation (not used in ColumnDataSource)
    cols = tiles_data.pop('cols')
    tile_width = tiles_data.pop('tile_width')
    tile_height = tiles_data.pop('tile_height')
    
    # Create main figure
    p = figure(
        width=container_width,
        height=math.ceil(len(data) / cols) * (tile_height + TILE_PADDING) + TILE_PADDING,
        tools="tap,pan,wheel_zoom,reset",
        toolbar_location=None,
        x_range=(0, container_width),
        y_range=(0, math.ceil(len(data) / cols) * (tile_height + TILE_PADDING) + TILE_PADDING),
        min_border=0,
        outline_line_color=None,
        background_fill_color='white'
    )
    
    # Create ColumnDataSource (without scalar values)
    source = ColumnDataSource(tiles_data)
    
    # Render tile backgrounds
    render_tile_backgrounds(p, source, tile_width, tile_height)
    
    # Render tile content (text)
    render_tile_content(p, source)
    
    # Render 52-week glyphs
    render_week52_glyphs(p, source)
    
    # Add hover tool
    hover = HoverTool(tooltips=[
        ("Ticker", "@ticker"),
        ("Price", "@prices"),
        ("Change", "@change_texts"),
        ("52W Position", "@week52_labels"),
        ("Sector", "@sector"),
        ("Volatility", "@volatilityBucket"),
        ("Market Cap", "@marketCapCategory")
    ])
    p.add_tools(hover)
    
    # Add tap tool for opening reports
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url="/reports/@filename")
    
    # Disable axes
    p.axis.visible = False
    p.grid.visible = False
    
    return components(p)


def prepare_tiles_data(data, container_width):
    """
    Prepare data structure for Bokeh tiles visualization
    
    Calculates grid positions and normalizes all data fields
    """
    cols = max(1, math.floor(container_width / (TILE_WIDTH + TILE_PADDING)))
    
    # Calculate positions for each tile
    tile_x = []
    tile_y = []
    tile_bg_x = []
    tile_bg_y = []
    sector_border_x = []
    sector_border_y = []
    ticker_x = []
    ticker_y = []
    price_x = []
    price_y = []
    change_x = []
    change_y = []
    metric_x = []
    metric_y = []
    week52_bar_x = []
    week52_bar_y1 = []
    week52_bar_y2 = []
    week52_glyph_x = []
    week52_glyph_y = []
    week52_glyph_rx = []
    week52_glyph_ry = []
    volatility_dot_x = []
    volatility_dot_y = []
    volatility_dot_r = []
    market_cap_x = []
    market_cap_y = []
    recommendation_x = []
    recommendation_y = []
    
    # Data arrays
    tickers = []
    prices = []
    changes = []
    change_percents = []
    change_texts = []
    change_colors = []
    week52_positions = []
    week52_labels = []
    volumes = []
    sectors = []
    sector_colors = []
    volatility_buckets = []
    volatility_colors = []
    market_cap_categories = []
    market_cap_badges = []
    market_cap_colors = []
    recommendations = []
    recommendation_colors = []
    filenames = []
    week52_highs = []
    week52_lows = []
    glyph_colors = []
    tail_y1 = []
    tail_opacities = []
    tail_colors = []
    
    for i, d in enumerate(data):
        col = i % cols
        row_idx = math.floor(i / cols)
        base_x = col * (TILE_WIDTH + TILE_PADDING) + TILE_PADDING
        base_y = row_idx * (TILE_HEIGHT + TILE_PADDING) + TILE_PADDING
        
        # Tile background
        tile_x.append(base_x)
        tile_y.append(base_y)
        tile_bg_x.append(base_x + TILE_WIDTH / 2)
        tile_bg_y.append(base_y + TILE_HEIGHT / 2)
        
        # Sector border
        sector_border_x.append(base_x + 2)
        sector_border_y.append(base_y + TILE_HEIGHT / 2)
        
        # Text positions
        ticker_x.append(base_x + 10)
        ticker_y.append(base_y + 25)
        price_x.append(base_x + 10)
        price_y.append(base_y + 50)
        change_x.append(base_x + 10)
        change_y.append(base_y + 68)
        metric_x.append(base_x + 10)
        metric_y.append(base_y + 95)
        
        # Volatility dot
        volatility_dot_x.append(base_x + TILE_WIDTH - 12)
        volatility_dot_y.append(base_y + 12)
        
        # Market cap badge
        market_cap_x.append(base_x + TILE_WIDTH - 10)
        market_cap_y.append(base_y + 30)
        
        # Recommendation
        recommendation_x.append(base_x + TILE_WIDTH - 10)
        recommendation_y.append(base_y + TILE_HEIGHT - 8)
        
        # 52-week bar
        week52_bar_x.append(base_x + TILE_WIDTH - 30)
        week52_bar_y1.append(base_y + 75)
        week52_bar_y2.append(base_y + 115)
        
        # Extract data
        ticker = d.get('ticker', 'N/A')
        tickers.append(ticker)
        
        price = d.get('price')
        if price is not None:
            prices.append(f"${price:.2f}")
        else:
            prices.append("N/A")
        
        change = d.get('change', 0)
        changes.append(change)
        
        change_percent = d.get('changePercent', 0) or 0
        change_percents.append(change_percent)
        
        # Format change percent text
        if price is None:
            change_texts.append("N/A")
        elif change_percent == 0:
            change_texts.append("0.00%")
        else:
            sign = "+" if change_percent >= 0 else ""
            change_texts.append(f"{sign}{change_percent:.2f}%")
        
        # Change color
        if change_percent > 0:
            change_colors.append('#27ae60')
        elif change_percent < 0:
            change_colors.append('#e74c3c')
        else:
            change_colors.append('#95a5a6')
        
        week52_position = d.get('week52Position')
        week52_positions.append(week52_position if week52_position is not None else 50)
        
        week52_high = d.get('week52High')
        week52_low = d.get('week52Low')
        week52_highs.append(week52_high if week52_high else 0)
        week52_lows.append(week52_low if week52_low else 0)
        
        # Week52 label
        if week52_position is not None:
            week52_labels.append(f"52W: {week52_position:.0f}%")
        else:
            week52_labels.append("52W: N/A")
        
        # Volume
        volume = d.get('volume', 0)
        if volume:
            if volume >= 1000000:
                volumes.append(f"Vol: {volume/1000000:.1f}M")
            elif volume >= 1000:
                volumes.append(f"Vol: {volume/1000:.1f}K")
            else:
                volumes.append(f"Vol: {volume}")
        else:
            volumes.append("Vol: N/A")
        
        # Sector
        sector = d.get('sector', 'Unknown')
        sectors.append(sector)
        sector_colors.append(SECTOR_COLORS.get(sector, '#7f8c8d'))
        
        # Volatility
        vol_bucket = d.get('volatilityBucket', '')
        volatility_buckets.append(vol_bucket)
        if vol_bucket == 'high':
            volatility_colors.append('#e74c3c')
            volatility_dot_r.append(6)
        elif vol_bucket == 'medium':
            volatility_colors.append('#f39c12')
            volatility_dot_r.append(4)
        elif vol_bucket == 'low':
            volatility_colors.append('#27ae60')
            volatility_dot_r.append(3)
        else:
            volatility_colors.append('#95a5a6')
            volatility_dot_r.append(3)
        
        # Market cap
        market_cap_cat = d.get('marketCapCategory', '')
        market_cap_categories.append(market_cap_cat)
        if market_cap_cat == 'mega':
            market_cap_badges.append('M')
            market_cap_colors.append('#8e44ad')
        elif market_cap_cat == 'large':
            market_cap_badges.append('L')
            market_cap_colors.append('#3498db')
        elif market_cap_cat == 'mid':
            market_cap_badges.append('M')
            market_cap_colors.append('#27ae60')
        elif market_cap_cat == 'small':
            market_cap_badges.append('S')
            market_cap_colors.append('#f39c12')
        else:
            market_cap_badges.append('')
            market_cap_colors.append('#95a5a6')
        
        # Recommendation
        rec = (d.get('recommendation') or 'N/A').upper()
        recommendations.append(rec)
        if 'BUY' in rec:
            recommendation_colors.append('#27ae60')
        elif 'SELL' in rec:
            recommendation_colors.append('#e74c3c')
        else:
            recommendation_colors.append('#f39c12')
        
        # Filename for navigation
        filenames.append(d.get('filename', ''))
        
        # 52-week glyph position and properties
        week52_glyph_y_base = base_y + 75 + 40  # Bottom of bar
        if week52_position is not None:
            glyph_y = week52_glyph_y_base - (week52_position / 100 * 40)
        else:
            glyph_y = base_y + 75 + 20  # Center
        
        week52_glyph_x.append(base_x + TILE_WIDTH - 30)
        week52_glyph_y.append(glyph_y)
        
        # Glyph size based on change magnitude
        abs_change = abs(change_percent)
        if abs_change > 3:
            week52_glyph_rx.append(5)
            week52_glyph_ry.append(6)
        elif abs_change > 1.5:
            week52_glyph_rx.append(4)
            week52_glyph_ry.append(5)
        elif abs_change > 0.2:
            week52_glyph_rx.append(3.5)
            week52_glyph_ry.append(4)
        else:
            week52_glyph_rx.append(3)
            week52_glyph_ry.append(3)
        
        # Glyph color
        if change_percent > 0.2:
            glyph_colors.append('#27ae60')
        elif change_percent < -0.2:
            glyph_colors.append('#e74c3c')
        else:
            glyph_colors.append('#95a5a6')
        
        # Tail properties
        if change_percent > 1.5:
            tail_y1.append(glyph_y - 8)
            tail_colors.append('#27ae60')
            tail_opacities.append(0.6)
        elif change_percent < -1.5:
            tail_y1.append(glyph_y + 8)
            tail_colors.append('#e74c3c')
            tail_opacities.append(0.6)
        else:
            tail_y1.append(glyph_y)
            tail_colors.append('#95a5a6')
            tail_opacities.append(0.3 if abs_change > 0.2 else 0.3)
    
    return {
        'cols': cols,  # Keep for reference but don't add to ColumnDataSource
        'tile_x': tile_x,
        'tile_y': tile_y,
        'tile_bg_x': tile_bg_x,
        'tile_bg_y': tile_bg_y,
        'tile_width': TILE_WIDTH,
        'tile_height': TILE_HEIGHT,
        'sector_border_x': sector_border_x,
        'sector_border_y': sector_border_y,
        'sector_colors': sector_colors,
        'ticker_x': ticker_x,
        'ticker_y': ticker_y,
        'tickers': tickers,
        'price_x': price_x,
        'price_y': price_y,
        'prices': prices,
        'change_x': change_x,
        'change_y': change_y,
        'changes': changes,
        'change_percents': change_percents,
        'change_texts': change_texts,
        'change_colors': change_colors,
        'metric_x': metric_x,
        'metric_y': metric_y,
        'week52_labels': week52_labels,
        'volumes': volumes,
        'sectors': sectors,
        'volatility_dot_x': volatility_dot_x,
        'volatility_dot_y': volatility_dot_y,
        'volatility_dot_r': volatility_dot_r,
        'volatility_colors': volatility_colors,
        'market_cap_x': market_cap_x,
        'market_cap_y': market_cap_y,
        'market_cap_badges': market_cap_badges,
        'market_cap_colors': market_cap_colors,
        'recommendation_x': recommendation_x,
        'recommendation_y': recommendation_y,
        'recommendations': recommendations,
        'recommendation_colors': recommendation_colors,
        'week52_bar_x': week52_bar_x,
        'week52_bar_y1': week52_bar_y1,
        'week52_bar_y2': week52_bar_y2,
        'week52_glyph_x': week52_glyph_x,
        'week52_glyph_y': week52_glyph_y,
        'week52_glyph_rx': week52_glyph_rx,
        'week52_glyph_ry': week52_glyph_ry,
        'glyph_colors': glyph_colors,
        'tail_y1': tail_y1,
        'tail_opacities': tail_opacities,
        'tail_colors': tail_colors,
        'week52_positions': week52_positions,
        'week52_highs': week52_highs,
        'week52_lows': week52_lows,
        'filenames': filenames,
        'volatility_buckets': volatility_buckets,
        'market_cap_categories': market_cap_categories,
        'ticker': tickers,  # For hover tooltip
        'price': [p.replace('$', '').replace('N/A', '0') if isinstance(p, str) else p for p in prices],
        'changePercent': change_percents,
        'week52Position': week52_positions,
        'sector': sectors,
        'volatilityBucket': volatility_buckets,
        'marketCapCategory': market_cap_categories,
    }


def render_tile_backgrounds(p, source, tile_width, tile_height):
    """Render tile backgrounds and borders"""
    # Main tile background
    p.rect(
        'tile_bg_x', 'tile_bg_y',
        width=tile_width, height=tile_height,
        source=source,
        fill_color='white',
        line_color='sector_colors',
        line_width=2,
        border_radius=6
    )
    
    # Sector color border (left edge)
    p.rect(
        'tile_x', 'sector_border_y',
        width=4, height=tile_height,
        source=source,
        fill_color='sector_colors',
        border_radius=6
    )
    
    # Volatility dots
    p.circle(
        'volatility_dot_x', 'volatility_dot_y',
        radius='volatility_dot_r',
        source=source,
        fill_color='volatility_colors'
    )


def render_tile_content(p, source):
    """Render text content on tiles"""
    # Ticker
    p.text(
        'ticker_x', 'ticker_y',
        text='tickers',
        source=source,
        text_font_size='16px',
        text_font_style='bold',
        text_color='#2c3e50'
    )
    
    # Price
    p.text(
        'price_x', 'price_y',
        text='prices',
        source=source,
        text_font_size='18px',
        text_font_style='bold',
        text_color='#2c3e50'
    )
    
    # Change
    p.text(
        'change_x', 'change_y',
        text='change_texts',
        source=source,
        text_font_size='14px',
        text_font_style='bold',
        text_color='change_colors'
    )
    
    # 52-week label
    p.text(
        'metric_x', 'metric_y',
        text='week52_labels',
        source=source,
        text_font_size='11px',
        text_color='#7f8c8d'
    )
    
    # Volume (needs separate y position)
    volume_y_positions = [y - 15 for y in source.data['metric_y']]
    volume_source = ColumnDataSource({
        'metric_x': source.data['metric_x'],
        'volume_y': volume_y_positions,
        'volumes': source.data['volumes']
    })
    p.text(
        'metric_x', 'volume_y',
        text='volumes',
        source=volume_source,
        text_font_size='11px',
        text_color='#7f8c8d'
    )
    
    # Sector (needs separate y position and truncation)
    sector_y_positions = [y - 30 for y in source.data['metric_y']]
    sectors_truncated = [s[:20] + '...' if len(s) > 20 else s for s in source.data['sectors']]
    sector_source = ColumnDataSource({
        'metric_x': source.data['metric_x'],
        'sector_y': sector_y_positions,
        'sectors_truncated': sectors_truncated
    })
    p.text(
        'metric_x', 'sector_y',
        text='sectors_truncated',
        source=sector_source,
        text_font_size='11px',
        text_color='#7f8c8d'
    )
    
    # Market cap badge
    p.text(
        'market_cap_x', 'market_cap_y',
        text='market_cap_badges',
        source=source,
        text_font_size='9px',
        text_font_style='bold',
        text_color='market_cap_colors',
        text_align='right'
    )
    
    # Recommendation
    p.text(
        'recommendation_x', 'recommendation_y',
        text='recommendations',
        source=source,
        text_font_size='10px',
        text_font_style='bold',
        text_color='recommendation_colors',
        text_align='right'
    )


def render_week52_glyphs(p, source):
    """Render enhanced 52-week glyphs"""
    # Vertical bar
    p.segment(
        'week52_bar_x', 'week52_bar_y1',
        'week52_bar_x', 'week52_bar_y2',
        source=source,
        line_color='#bdc3c7',
        line_width=2
    )
    
    # Tail/stalk
    p.segment(
        'week52_bar_x', 'tail_y1',
        'week52_bar_x', 'week52_glyph_y',
        source=source,
        line_color='tail_colors',
        line_width=1.5,
        line_alpha='tail_opacities'
    )
    
    # Glyph ellipse
    p.ellipse(
        'week52_glyph_x', 'week52_glyph_y',
        'week52_glyph_rx', 'week52_glyph_ry',
        source=source,
        fill_color='glyph_colors',
        line_color='glyph_colors',
        line_width=1
    )
