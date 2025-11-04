# Reports Module
# Commands for generating reports

# Generate report for a single ticker
report TICKER:
    @echo "📄 Generating report for {{TICKER}}..."
    python webapp/save_report_to_db.py {{TICKER}}

# Generate all reports
reports-all:
    @echo "📄 Generating all reports..."
    python generate_all_reports.py

# Generate reports with faithfulness scoring
reports-faithful:
    @echo "📄 Generating reports with faithfulness scoring..."
    python generate_report_with_faithfulness.py
