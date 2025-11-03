# Daily Report Archive Webapp

A minimalist web interface to browse and view historical PDF ticker analysis reports.

## Features

- 📊 Simple archive page listing all PDF reports
- 🔍 Filter by ticker or date
- 📄 Direct PDF viewing in browser
- 🚫 No API endpoints - pure HTML interface
- 💾 Lightweight database with minimal duplication

## Setup

### 1. Install Dependencies

```bash
pip install flask
```

### 2. Initialize Database (Already Done!)

The `pdf_archive` table has been created and populated with 36 existing PDFs.

### 3. Run the Webapp

```bash
cd webapp
python app.py
```

The webapp will be available at: http://localhost:5000

## Database Schema

The webapp uses a lightweight `pdf_archive` table:

```sql
CREATE TABLE pdf_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    report_date DATE NOT NULL,
    pdf_filename TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, report_date)
);
```

This design avoids duplicating data from `ticker_data.db` and only stores webapp-specific metadata.

## Usage

### Browse Reports

1. Open http://localhost:5000 in your browser
2. View all 36 indexed reports in a table
3. Filter by ticker or date using the dropdown filters
4. Click "View PDF 📄" to open any report in your browser

### Index New PDFs

When you generate new reports using `generate_all_reports.py`, they will be automatically indexed in the `pdf_archive` table.

You can also manually index PDFs from the `/reports` directory:

```bash
cd webapp
python index_existing_pdfs.py
```

## File Structure

```
webapp/
├── app.py                    # Flask application
├── index_existing_pdfs.py    # Migration script to index PDFs
├── data/
│   └── ticker_reports.db     # SQLite database with pdf_archive table
├── templates/
│   └── archive.html          # Archive listing page
└── README.md                 # This file
```

## Current Status

✅ Database initialized with `pdf_archive` table
✅ 36 existing PDFs indexed
✅ Archive page template created
✅ PDF serving route configured
⏳ Ready to run (install Flask first)

## No Duplication Design

Unlike the original `ticker_reports` table which stores full report content, charts, audio, etc., the `pdf_archive` table only stores:

- `ticker` - Ticker symbol
- `report_date` - Report date
- `pdf_filename` - Filename in `/reports` directory
- `created_at` - Timestamp

This minimalist design:
- Avoids duplicating analytical data from `ticker_data.db`
- Keeps the webapp database small and fast
- Serves PDFs directly from the filesystem
- Enables easy filtering and searching
