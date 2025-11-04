# Database Module
# Commands for database operations

# Initialize database
db-init:
    @echo "💾 Initializing database..."
    cd webapp && python -c "from app import init_db; init_db()"

# Index existing PDFs
db-index-pdfs:
    @echo "💾 Indexing PDFs..."
    cd webapp && python index_existing_pdfs.py

# Check database contents
db-check:
    @echo "💾 Checking database..."
    python webapp/check_db.py

# View database
db-view:
    @echo "💾 Opening database..."
    @sqlite3 webapp/data/ticker_reports.db ".tables" || sqlite3 data/ticker_reports.db ".tables"

# Reset database and reindex
reset-db:
    @echo "🔄 Resetting database..."
    @rm -f webapp/data/ticker_reports.db data/ticker_reports.db
    @just db-init
    @just db-index-pdfs
    @echo "✅ Database reset complete!"
