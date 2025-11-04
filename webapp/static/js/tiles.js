/**
 * Stock Tiles Dashboard - Main JavaScript
 * High-density multi-variable financial visualization using D3.js
 */

// Global variables
let allData = [];
let filteredData = [];
let sortBy = 'ticker';
let filterSector = '';
let filterVolatility = '';
let filterMarketCap = '';
let filterRecommendation = '';
let searchTicker = 'DBS19';

// Tile dimensions - compact for high density
const tileWidth = 180;
const tileHeight = 160;
const tilePadding = 12;

// Sector colors (matching backend)
const sectorColors = {
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
};

/**
 * Initialize visualization
 */
async function init() {
    try {
        // Set default search ticker value
        const searchInput = document.getElementById('searchTicker');
        if (searchInput) {
            searchInput.value = searchTicker;
        }
        
        console.log('Fetching data from /api/tiles-data...');
        const response = await fetch('/api/tiles-data');
        
        if (!response.ok) {
            throw new Error(`API responded with status ${response.status}`);
        }
        
        allData = await response.json();
        
        console.log('Total data received:', allData.length);
        if (allData.length > 0) {
            console.log('Sample data:', allData.slice(0, 2));
        }
        
        // Populate sector filter
        const sectors = [...new Set(allData.map(d => d.sector).filter(Boolean))].sort();
        const sectorSelect = document.getElementById('filterSector');
        sectors.forEach(sector => {
            const option = document.createElement('option');
            option.value = sector;
            option.textContent = sector;
            sectorSelect.appendChild(option);
        });
        
        updateStats();
        applyFilters();
        console.log('After filtering, filteredData length:', filteredData.length);
        renderTiles();
        
        // Setup event listeners
        setupEventListeners();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('tiles-container').innerHTML = 
            '<div class="empty-state">Error loading data: ' + error.message + '</div>';
    }
}

/**
 * Setup event listeners for filters and controls
 */
function setupEventListeners() {
    document.getElementById('sortBy').addEventListener('change', (e) => {
        sortBy = e.target.value;
        applyFilters();
        renderTiles();
    });

    document.getElementById('filterSector').addEventListener('change', (e) => {
        filterSector = e.target.value;
        applyFilters();
        renderTiles();
    });

    document.getElementById('filterVolatility').addEventListener('change', (e) => {
        filterVolatility = e.target.value;
        applyFilters();
        renderTiles();
    });

    document.getElementById('filterMarketCap').addEventListener('change', (e) => {
        filterMarketCap = e.target.value;
        applyFilters();
        renderTiles();
    });

    document.getElementById('filterRecommendation').addEventListener('change', (e) => {
        filterRecommendation = e.target.value;
        applyFilters();
        renderTiles();
    });

    document.getElementById('searchTicker').addEventListener('input', (e) => {
        searchTicker = e.target.value.toUpperCase();
        applyFilters();
        renderTiles();
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        renderTiles();
    });
}

/**
 * Update dashboard statistics
 */
function updateStats() {
    const total = allData.length;
    const gainers = allData.filter(d => d.changePercent > 0).length;
    const decliners = allData.filter(d => d.changePercent < 0).length;
    const latestDate = allData.length > 0 ? allData[0].date : 'N/A';

    document.getElementById('totalTickers').textContent = total;
    document.getElementById('gainers').textContent = gainers;
    document.getElementById('decliners').textContent = decliners;
    document.getElementById('latestDate').textContent = latestDate;
}

/**
 * Apply filters and sorting to data
 */
function applyFilters() {
    filteredData = [...allData];

    // Filter by sector
    if (filterSector) {
        filteredData = filteredData.filter(d => d.sector === filterSector);
    }

    // Filter by volatility
    if (filterVolatility) {
        filteredData = filteredData.filter(d => d.volatilityBucket === filterVolatility);
    }

    // Filter by market cap
    if (filterMarketCap) {
        filteredData = filteredData.filter(d => d.marketCapCategory === filterMarketCap);
    }

    // Filter by recommendation
    if (filterRecommendation) {
        filteredData = filteredData.filter(d => 
            d.recommendation && d.recommendation.toUpperCase() === filterRecommendation
        );
    }

    // Filter by search ticker
    if (searchTicker) {
        filteredData = filteredData.filter(d => 
            d.ticker.toUpperCase().includes(searchTicker.toUpperCase())
        );
    }

    // Sort data
    filteredData.sort((a, b) => {
        switch(sortBy) {
            case 'ticker':
                return a.ticker.localeCompare(b.ticker);
            case 'date':
                return new Date(b.date) - new Date(a.date);
            case 'changePercent':
                return (b.changePercent || 0) - (a.changePercent || 0);
            case 'price':
                return (b.price || 0) - (a.price || 0);
            case 'volume':
                return (b.volume || 0) - (a.volume || 0);
            case 'week52Position':
                return (b.week52Position || 0) - (a.week52Position || 0);
            case 'volatility':
                const volOrder = {high: 3, medium: 2, low: 1};
                return (volOrder[b.volatilityBucket] || 0) - (volOrder[a.volatilityBucket] || 0);
            case 'marketCap':
                return (b.marketCap || 0) - (a.marketCap || 0);
            case 'sector':
                return (a.sector || '').localeCompare(b.sector || '');
            default:
                return 0;
        }
    });
}

/**
 * Render stock tiles using D3.js
 */
function renderTiles() {
    const container = d3.select('#tiles-container');
    container.selectAll('*').remove();

    console.log('Filtered data length:', filteredData.length);
    
    if (filteredData.length === 0) {
        if (allData.length === 0) {
            container.html('<div class="empty-state">No data available. Please check the API endpoint.</div>');
        } else {
            container.html('<div class="empty-state">No data matches your filters. Try clearing the filters.</div>');
        }
        return;
    }

    // Calculate grid dimensions
    const containerWidth = container.node().getBoundingClientRect().width;
    const colsPerRow = Math.floor(containerWidth / (tileWidth + tilePadding));
    const cols = Math.max(1, colsPerRow);

    // Create SVG container
    const svg = container.append('svg')
        .attr('width', containerWidth)
        .attr('height', Math.ceil(filteredData.length / cols) * (tileHeight + tilePadding) + tilePadding);

    // Create groups for each tile
    const tiles = svg.selectAll('.tile')
        .data(filteredData)
        .enter()
        .append('g')
        .attr('class', 'tile')
        .attr('transform', (d, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            const x = col * (tileWidth + tilePadding) + tilePadding;
            const y = row * (tileHeight + tilePadding) + tilePadding;
            return `translate(${x},${y})`;
        })
        .on('click', (event, d) => {
            window.open(`/reports/${d.filename}`, '_blank');
        });

    // Render tile elements
    renderTileBackground(tiles);
    renderTileContent(tiles);
    renderWeek52Glyph(tiles);
}

/**
 * Render tile background and borders
 */
function renderTileBackground(tiles) {
    // Tile background with sector color border
    tiles.append('rect')
        .attr('class', 'tile-background')
        .attr('width', tileWidth)
        .attr('height', tileHeight)
        .attr('rx', 6)
        .attr('fill', '#ffffff')
        .attr('stroke', d => sectorColors[d.sector] || '#bdc3c7')
        .attr('stroke-width', 2);

    // Sector color border (left edge)
    tiles.append('rect')
        .attr('class', 'tile-sector-border')
        .attr('width', 4)
        .attr('height', tileHeight)
        .attr('rx', 6)
        .attr('x', 0)
        .attr('y', 0)
        .attr('fill', d => sectorColors[d.sector] || '#7f8c8d');

    // Volatility indicator (dot in top-right)
    tiles.append('circle')
        .attr('class', d => {
            const vol = d.volatilityBucket;
            if (!vol) return 'volatility-dot';
            return `volatility-dot volatility-${vol}`;
        })
        .attr('cx', tileWidth - 12)
        .attr('cy', 12)
        .attr('r', d => {
            const vol = d.volatilityBucket;
            if (vol === 'high') return 6;
            if (vol === 'medium') return 4;
            return 3;
        })
        .attr('fill', d => {
            const vol = d.volatilityBucket;
            if (vol === 'high') return '#e74c3c';
            if (vol === 'medium') return '#f39c12';
            if (vol === 'low') return '#27ae60';
            return '#95a5a6';
        });
}

/**
 * Render tile content (text elements)
 */
function renderTileContent(tiles) {
    // Ticker symbol
    tiles.append('text')
        .attr('class', 'tile-text tile-ticker')
        .attr('x', 10)
        .attr('y', 25)
        .text(d => d.ticker);

    // Market cap badge (top-right)
    tiles.append('text')
        .attr('class', 'tile-text market-cap-badge')
        .attr('x', tileWidth - 10)
        .attr('y', 30)
        .attr('fill', d => {
            const cat = d.marketCapCategory;
            if (cat === 'mega') return '#8e44ad';
            if (cat === 'large') return '#3498db';
            if (cat === 'mid') return '#27ae60';
            if (cat === 'small') return '#f39c12';
            return '#95a5a6';
        })
        .text(d => {
            const cat = d.marketCapCategory;
            if (cat === 'mega') return 'M';
            if (cat === 'large') return 'L';
            if (cat === 'mid') return 'M';
            if (cat === 'small') return 'S';
            return '';
        });

    // Price
    tiles.append('text')
        .attr('class', 'tile-text tile-price')
        .attr('x', 10)
        .attr('y', 50)
        .text(d => {
            if (d.price) {
                return '$' + d.price.toFixed(2);
            }
            return 'N/A';
        });

    // Change
    tiles.append('text')
        .attr('class', d => {
            const change = d.changePercent || 0;
            if (change > 0) return 'tile-text tile-change-positive';
            if (change < 0) return 'tile-text tile-change-negative';
            return 'tile-text tile-change-neutral';
        })
        .attr('x', 10)
        .attr('y', 68)
        .text(d => {
            const change = d.change || 0;
            const changePercent = d.changePercent || 0;
            if (d.price === null || d.price === undefined) {
                return 'N/A';
            }
            if (change === 0 && changePercent === 0) return '0.00%';
            const sign = change >= 0 ? '+' : '';
            return `${sign}${changePercent.toFixed(2)}%`;
        });

    // 52-week position label
    tiles.append('text')
        .attr('class', 'tile-text tile-metric')
        .attr('x', 10)
        .attr('y', 95)
        .text(d => {
            const pos = d.week52Position;
            if (pos === null || pos === undefined) return '52W: N/A';
            return `52W: ${pos.toFixed(0)}%`;
        });

    // Volume
    tiles.append('text')
        .attr('class', 'tile-text tile-metric')
        .attr('x', 10)
        .attr('y', 110)
        .text(d => {
            if (d.volume) {
                const vol = d.volume >= 1000000 
                    ? (d.volume / 1000000).toFixed(1) + 'M'
                    : d.volume >= 1000
                    ? (d.volume / 1000).toFixed(1) + 'K'
                    : d.volume;
                return `Vol: ${vol}`;
            }
            return 'Vol: N/A';
        });

    // Sector (bottom)
    tiles.append('text')
        .attr('class', 'tile-text tile-metric')
        .attr('x', 10)
        .attr('y', 125)
        .text(d => {
            const sector = d.sector || 'Unknown';
            return sector.length > 20 ? sector.substring(0, 20) + '...' : sector;
        });

    // Recommendation badge (bottom-right)
    tiles.append('text')
        .attr('class', 'tile-text tile-metric')
        .attr('x', tileWidth - 10)
        .attr('y', tileHeight - 8)
        .attr('text-anchor', 'end')
        .attr('font-weight', '700')
        .attr('font-size', '10px')
        .attr('fill', d => {
            const rec = (d.recommendation || '').toUpperCase();
            if (rec.includes('BUY')) return '#27ae60';
            if (rec.includes('SELL')) return '#e74c3c';
            return '#f39c12';
        })
        .text(d => {
            const rec = d.recommendation || 'N/A';
            if (rec === 'N/A') return '';
            return rec.toUpperCase();
        });
}

/**
 * Render enhanced 52-week glyph (vertical bar with daily move indicator)
 */
function renderWeek52Glyph(tiles) {
    const week52BarY = 75;
    const week52BarHeight = 40;
    const week52BarX = tileWidth - 30;

    // Create 52-week glyph group for each tile
    const week52Groups = tiles.append('g')
        .attr('class', 'week52-group');

    // Vertical bar background (full 52-week range)
    week52Groups.append('line')
        .attr('class', 'week52-bar-vertical')
        .attr('x1', week52BarX)
        .attr('y1', week52BarY)
        .attr('x2', week52BarX)
        .attr('y2', week52BarY + week52BarHeight)
        .attr('stroke', '#bdc3c7')
        .attr('stroke-width', 2);

    // Calculate glyph position and properties
    const week52Glyphs = week52Groups.append('g')
        .attr('class', 'week52-glyph-container')
        .attr('transform', d => {
            const pos = d.week52Position;
            if (pos === null || pos === undefined) {
                // Center if no data
                return `translate(${week52BarX}, ${week52BarY + week52BarHeight / 2})`;
            }
            // Normalized position: 0 = bottom (52wk_low), 1 = top (52wk_high)
            const yPos = week52BarY + week52BarHeight - (pos / 100 * week52BarHeight);
            return `translate(${week52BarX}, ${yPos})`;
        });

    // Tail/stalk showing available range
    week52Glyphs.append('line')
        .attr('class', d => {
            const change = d.changePercent || 0;
            if (change > 0) return 'week52-tail week52-tail-up';
            if (change < 0) return 'week52-tail week52-tail-down';
            return 'week52-tail';
        })
        .attr('x1', 0)
        .attr('y1', d => {
            const change = d.changePercent || 0;
            if (change > 1.5) return -8; // Tail extends up for positive moves
            if (change < -1.5) return 8; // Tail extends down for negative moves
            return 0;
        })
        .attr('x2', 0)
        .attr('y2', 0)
        .attr('stroke-width', 1.5)
        .attr('stroke', d => {
            const change = d.changePercent || 0;
            if (change > 0) return '#27ae60';
            if (change < 0) return '#e74c3c';
            return '#95a5a6';
        })
        .attr('opacity', d => {
            const change = Math.abs(d.changePercent || 0);
            return change > 0.2 ? 0.6 : 0.3;
        });

    // Glyph shape (circle/ellipse based on daily move magnitude)
    week52Glyphs.append('ellipse')
        .attr('class', d => {
            const change = d.changePercent || 0;
            if (change > 0.2) return 'week52-glyph week52-glyph-positive';
            if (change < -0.2) return 'week52-glyph week52-glyph-negative';
            return 'week52-glyph week52-glyph-neutral';
        })
        .attr('rx', d => {
            const change = Math.abs(d.changePercent || 0);
            // Base size: 3px, scales up with magnitude
            if (change > 3) return 5;
            if (change > 1.5) return 4;
            if (change > 0.2) return 3.5;
            return 3;
        })
        .attr('ry', d => {
            const change = d.changePercent || 0;
            const absChange = Math.abs(change);
            // Vertical elongation for larger moves
            if (absChange > 3) return 6;
            if (absChange > 1.5) return 5;
            if (absChange > 0.2) return 4;
            return 3;
        })
        .attr('cy', d => {
            const change = d.changePercent || 0;
            // Slight vertical offset based on direction
            if (change > 1.5) return -1; // Shift up for positive moves
            if (change < -1.5) return 1; // Shift down for negative moves
            return 0;
        })
        .attr('cx', 0);

    // Tooltip (shown on hover)
    week52Glyphs.append('title')
        .text(d => {
            const pos = d.week52Position;
            const change = d.changePercent || 0;
            const price = d.price;
            const week52High = d.week52High;
            const week52Low = d.week52Low;
            
            if (pos === null || pos === undefined) {
                return 'No 52-week range data';
            }
            
            let tooltip = `Price: $${price?.toFixed(2) || 'N/A'}\n`;
            tooltip += `Daily Change: ${change >= 0 ? '+' : ''}${change.toFixed(2)}%\n`;
            tooltip += `52-Wk Position: ${pos.toFixed(1)}%\n`;
            if (week52High && week52Low) {
                tooltip += `52-Wk Range: $${week52Low.toFixed(2)} - $${week52High.toFixed(2)}`;
            }
            return tooltip;
        });
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
