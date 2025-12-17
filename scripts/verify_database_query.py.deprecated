#!/usr/bin/env python3
from src.data.database import TickerDatabase

db = TickerDatabase()
rows = db.get_latest_data('D05.SI', days=10)

print(f"Latest {len(rows)} days of data for DBS19:")
for row in rows:
    print(f"{row[3]}: Close=${row[7]:.2f}")
