# Feature PRD: Enhanced 52-Week Relative Price Bar with Daily Move Glyph Overlay

## 1. Summary
Enhance each stock tile’s current 52-week price bar to:
- Show the current price’s relative position within the 52-week range using a vertical bar.
- Overlay a glyph (shape marker) that communicates daily % movement magnitude and direction.
- Preserve high-density scanning characteristics.

This enables at-a-glance insight into:
- Where price sits relative to historic bounds.
- How aggressively it is moving today.

## 2. Goals
- Encode two price dimensions in the same vertical bar:
  - 52-week context (range normalization)
  - Intraday daily change (glyph offset)
- Visually cluster stocks trending toward highs/lows
- Instantly spot large positive/negative movers

## 3. Non-Goals
- K-line/candlestick substitution
- Replacing existing numeric text values
- Handling intraday OHLC

## 4. User Stories
US-01: As a user, I want to see how close a stock is to its 52-week high or low at a glance.
US-02: As a user, I want to detect daily momentum vs longer-term price positioning.
US-03: As a user, I want negative daily moves to be visually distinct from positive ones.

## 5. Visual Encoding Specification

### 5.1 Vertical 52-Week Context Bar
- Full vertical line represents the range [52wk_low … 52wk_high].
- The current price’s normalized position is the location where the glyph sits.

Formula:
normalized = (price - 52wk_low) / (52wk_high - 52wk_low)

### 5.2 Glyph Overlay (Daily Move)
Glyph type:
- Circle + tail (neutral baseline)
- Offset ellipse shape indicates magnitude relative to baseline

Glyph position:
- Anchored at normalized price coordinate.

Glyph fill color:
- Positive daily move: green
- Negative daily move: red
- Near-zero: neutral grey

Glyph vertical offset (optional mode):
- If daily move > threshold, shift glyph up/down proportionally.

### 5.3 Tail Stalk
Thin vertical extensions above/below glyph show:
- Available range up/down

## 6. Data Requirements
New fields required (if not present):
- daily_change_percent (float)
- price

Existing:
- fifty_two_week_high
- fifty_two_week_low

## 7. Rules & Behavior
| Scenario | Behavior |
|---------|----------|
| price == 52wk_high | glyph touches top |
| price == 52wk_low | glyph touches bottom |
| daily change > +1.5% | glyph grows in scale |
| daily change < -1.5% | glyph stretches vertically downward |
| daily change within ±0.2% | neutral small circle |

Magnitude thresholds configurable.

## 8. Interaction
Hover tooltip:
- Current price
- Daily % move
- 52-week rank position (percentile)

Optional click:
- Opens micro detail view (not required)

## 9. Rendering Expectations
Performance:
- Must draw glyphs efficiently across 200–300 tiles
- SVG recommended

Fallback:
- Pure CSS markers if SVG unsupported

## 10. Sorting & Filtering (New Options)
Sorting:
- 52wk relative position
- Daily % change

Filtering:
- Highlight near 52-week breakout zones
- Highlight large daily movers

## 11. Accessibility
- Glyph color must be paired with positional signal (shape/size)
- Color-blind safe palette
- Tooltip with numeric values

## 12. Error Handling
If fifty_two_week_high == fifty_two_week_low:
- Render center position
- Grey glyph
- Tooltip notes "No 52-week range data"

If missing daily_change_percent:
- Render small neutral indicator

## 13. Testing / QA Criteria
TC-01: Daily move positive shows green and slight vertical elongation.
TC-02: Daily move negative shows red and vertical downward elongation.
TC-03: Relative positioning matches normalized formula.
TC-04: Edge case: price == 52wk_high.
TC-05: Edge case: price == 52wk_low.
TC-06: Rendering remains performant at 300+ tiles.

## 14. Acceptance Criteria
- The feature visually displays daily change magnitude & direction on the 52-week bar.
- Glyph scale increases with larger movements.
- All glyphs align consistently per tile.
- Users can visually cluster extremes without reading numbers.

## 15. Risks
- Overencoding complexity
- Narrow tiles may compress glyph rendering
- Users might misinterpret vertical offset direction if not subtle

Mitigation:
- Include minimal legend (optional)
- Keep glyph scale bounded

## 16. Future Enhancements
- Annotate price anomalies
- Combine 1-day & 5-day movement glyphs
- Animate glyph shift intraday
- Alert badges for new 52-week events
