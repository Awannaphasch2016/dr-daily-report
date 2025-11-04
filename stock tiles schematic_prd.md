# Product Requirements Document (PRD)
## Stock Tiles Schematic Visualization (Django 3)

## 1. Summary
We will implement a web-based dashboard that visualizes multiple stocks simultaneously using **stock tiles**. Each tile summarizes key metrics such as price change, volume, volatility, sector classification, and market cap. Tiles are displayed in a sortable, filterable grid.

Primary objective:
Enable high-density comparative financial scanning at a glance.

## 2. Goals
- Allow users to monitor many securities at once
- Enable pattern recognition (sector rallies, liquidity spikes)
- Provide interactive filtering and sorting
- Encode multiple variables in compact tiles

## 3. Non-Goals
- Long-term historical charting
- Portfolio management logic
- Order-execution trading features
- User authentication flows beyond baseline

## 4. Users
- Retail investors
- Quant researchers
- Financial analysts
- Internal research teams

## 5. Core Concepts
Each tile encodes:
- Ticker
- Current price
- Percent change
- Volume
- 52-week position
- Volatility bucket
- Sector color cue
- Market cap category

## 6. Key User Stories
... (omitted for brevity in this example)
