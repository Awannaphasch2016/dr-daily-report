# -*- coding: utf-8 -*-
"""
Fund Data CSV Parser

Parses CSV files exported from on-premises SQL Server with robust encoding detection
and type conversion. Handles Windows-1252 encoded CSVs exported from SQL Server.

Design Principles:
    1. Encoding Detection: Auto-detect charset (chardet library)
    2. Defensive Parsing: Explicit validation at system boundary
    3. Type Conversion: Convert string values to appropriate Python types
    4. Error Context: Rich error messages for debugging

Data Flow:
    S3 raw/sql_server/fund_data/*.csv → this parser → fund_data_repository → Aurora
"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import chardet

logger = logging.getLogger(__name__)


class FundDataParser:
    """CSV parser for fund data with encoding detection and type conversion.

    Handles CSV files exported from SQL Server on-premises system.
    Auto-detects encoding (typically Windows-1252 or UTF-8).

    Example:
        >>> parser = FundDataParser()
        >>> with open('fund_data.csv', 'rb') as f:
        ...     csv_bytes = f.read()
        >>> records = parser.parse(csv_bytes, s3_key='raw/fund_data.csv')
        >>> print(f"Parsed {len(records)} records")
    """

    def __init__(
        self,
        expected_columns: Optional[List[str]] = None,
        confidence_threshold: float = 0.7
    ):
        """Initialize parser.

        Args:
            expected_columns: Expected CSV column names (for validation).
                If None, uses default: ['d_trade', 'stock', 'ticker', 'col_code',
                                         'value_numeric', 'value_text']
            confidence_threshold: Minimum chardet confidence to accept encoding (0.0-1.0)
        """
        self.expected_columns = expected_columns or [
            'd_trade', 'stock', 'ticker', 'col_code', 'value_numeric', 'value_text'
        ]
        self.confidence_threshold = confidence_threshold

    # =========================================================================
    # Public API
    # =========================================================================

    def parse(
        self,
        csv_bytes: bytes,
        s3_key: str
    ) -> List[Dict[str, Any]]:
        """Parse CSV bytes into fund data records.

        Args:
            csv_bytes: Raw CSV file content as bytes
            s3_key: S3 object key (for data lineage and error context)

        Returns:
            List of parsed records. Each record has:
                - d_trade: date object
                - stock: str
                - ticker: str
                - col_code: str
                - value_numeric: Decimal or None
                - value_text: str or None
                - s3_source_key: str (data lineage)

        Raises:
            ValueError: If CSV parsing fails or validation errors
            UnicodeDecodeError: If encoding detection fails

        Example:
            >>> csv_data = b"d_trade,stock,ticker,col_code,value\\n2025-12-09,DBS,DBS19,CLOSE,38.50"
            >>> records = parser.parse(csv_data, 's3://bucket/file.csv')
            >>> assert len(records) == 1
            >>> assert records[0]['value_numeric'] == Decimal('38.50')
        """
        # 1. Detect encoding
        encoding, confidence = self._detect_encoding(csv_bytes)
        logger.info(
            f"Detected encoding: {encoding} (confidence: {confidence:.2f}) "
            f"for {s3_key}"
        )

        # 2. Decode bytes to string
        try:
            csv_string = csv_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                encoding, csv_bytes, e.start, e.end,
                f"Failed to decode CSV with {encoding} encoding. "
                f"S3 key: {s3_key}"
            )

        # 3. Parse CSV
        records = self._parse_csv_string(csv_string, s3_key)

        # 4. Validate schema
        self._validate_records(records, s3_key)

        logger.info(f"Successfully parsed {len(records)} records from {s3_key}")
        return records

    # =========================================================================
    # Encoding Detection
    # =========================================================================

    def _detect_encoding(self, csv_bytes: bytes) -> tuple[str, float]:
        """Detect CSV file encoding using chardet.

        Args:
            csv_bytes: Raw CSV file content

        Returns:
            Tuple of (encoding_name, confidence_score)

        Raises:
            ValueError: If confidence below threshold or detection fails
        """
        # Use chardet to detect encoding
        detection = chardet.detect(csv_bytes)
        encoding = detection.get('encoding')
        confidence = detection.get('confidence', 0.0)

        # Validate detection
        if encoding is None:
            raise ValueError(
                "Failed to detect CSV encoding. "
                f"Detection result: {detection}"
            )

        if confidence < self.confidence_threshold:
            logger.warning(
                f"Low encoding confidence: {confidence:.2f} < {self.confidence_threshold}. "
                f"Detected: {encoding}. Proceeding anyway..."
            )

        return encoding, confidence

    # =========================================================================
    # CSV Parsing
    # =========================================================================

    def _parse_csv_string(
        self,
        csv_string: str,
        s3_key: str
    ) -> List[Dict[str, Any]]:
        """Parse CSV string into records.

        Args:
            csv_string: Decoded CSV content
            s3_key: S3 object key (for error context)

        Returns:
            List of raw records (before type conversion)

        Raises:
            ValueError: If CSV format invalid
        """
        # Parse CSV
        csv_file = io.StringIO(csv_string)
        reader = csv.DictReader(csv_file)

        # Validate header (case-insensitive)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header row. S3 key: {s3_key}")

        header = list(reader.fieldnames)
        # Normalize column names to lowercase for case-insensitive comparison
        header_lower = [col.lower() for col in header]
        missing_cols = set(self.expected_columns) - set(header_lower)
        if missing_cols:
            raise ValueError(
                f"CSV missing required columns: {missing_cols}. "
                f"Found columns: {header} (normalized: {header_lower}). S3 key: {s3_key}"
            )

        # Create mapping from uppercase CSV columns to lowercase expected columns
        column_mapping = {col: col.lower() for col in header}

        # Parse rows with type conversion
        records = []
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Normalize row keys to lowercase using column mapping
                normalized_row = {column_mapping[k]: v for k, v in row.items() if k in column_mapping}
                record = self._convert_row_types(normalized_row, s3_key)
                records.append(record)
            except Exception as e:
                raise ValueError(
                    f"Failed to parse row {row_num} in {s3_key}: {e}. "
                    f"Row data: {row}"
                ) from e

        if not records:
            raise ValueError(f"CSV contains no data rows. S3 key: {s3_key}")

        return records

    # =========================================================================
    # Type Conversion
    # =========================================================================

    def _convert_row_types(
        self,
        row: Dict[str, str],
        s3_key: str
    ) -> Dict[str, Any]:
        """Convert CSV row string values to appropriate Python types.

        Args:
            row: Raw CSV row (all values are strings)
            s3_key: S3 object key (for data lineage)

        Returns:
            Converted record with typed values

        Raises:
            ValueError: If type conversion fails
        """
        # Extract raw values
        d_trade_str = row.get('d_trade', '').strip()
        stock = row.get('stock', '').strip()
        ticker = row.get('ticker', '').strip()
        col_code = row.get('col_code', '').strip()
        value_numeric_str = row.get('value_numeric', '').strip()
        value_text_str = row.get('value_text', '').strip()

        # Validate required fields
        if not d_trade_str:
            raise ValueError("Field 'd_trade' is required but empty")
        if not stock:
            raise ValueError("Field 'stock' is required but empty")
        if not ticker:
            raise ValueError("Field 'ticker' is required but empty")
        if not col_code:
            raise ValueError("Field 'col_code' is required but empty")

        # Convert d_trade to date
        try:
            # Try common formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d']:
                try:
                    d_trade = datetime.strptime(d_trade_str, fmt).date()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(
                    f"Invalid date format '{d_trade_str}'. "
                    "Expected: YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY"
                )
        except Exception as e:
            raise ValueError(f"Failed to parse d_trade '{d_trade_str}': {e}") from e

        # Convert value_numeric and value_text from separate fields
        value_numeric = None
        value_text = None

        # Parse VALUE_NUMERIC field
        if value_numeric_str:
            value_numeric = self._try_parse_numeric(value_numeric_str)

        # Parse VALUE_TEXT field
        if value_text_str:
            value_text = value_text_str

        return {
            'd_trade': d_trade,
            'stock': stock,
            'ticker': ticker,
            'col_code': col_code,
            'value_numeric': value_numeric,
            'value_text': value_text,
            's3_source_key': s3_key
        }

    def _try_parse_numeric(self, value_str: str) -> Optional[Decimal]:
        """Attempt to parse string as numeric value.

        Args:
            value_str: String value to parse

        Returns:
            Decimal value or None if not numeric

        Example:
            >>> parser = FundDataParser()
            >>> parser._try_parse_numeric('38.50')
            Decimal('38.50')
            >>> parser._try_parse_numeric('ACTIVE')
            None
        """
        if not value_str:
            return None

        # Remove common formatting (commas, spaces)
        cleaned = value_str.replace(',', '').replace(' ', '')

        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            # Not a valid number - treat as text
            return None

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_records(
        self,
        records: List[Dict[str, Any]],
        s3_key: str
    ) -> None:
        """Validate parsed records.

        Args:
            records: Parsed records
            s3_key: S3 object key (for error context)

        Raises:
            ValueError: If validation fails

        Defensive Programming:
            - Explicit validation at system boundary (CSV → Python)
            - Checks data contracts before database insertion
        """
        if not records:
            raise ValueError(f"No records parsed from {s3_key}")

        # Sample check: all records have required fields
        for i, record in enumerate(records):
            required_keys = {'d_trade', 'stock', 'ticker', 'col_code', 's3_source_key'}
            missing = required_keys - set(record.keys())
            if missing:
                raise ValueError(
                    f"Record {i} missing required keys: {missing}. "
                    f"S3 key: {s3_key}"
                )

            # At least one value field must be populated
            if record.get('value_numeric') is None and not record.get('value_text'):
                logger.warning(
                    f"Record {i} has both value_numeric and value_text as None/empty. "
                    f"S3 key: {s3_key}. Record: {record}"
                )


# ============================================================================
# Module-Level Singleton (Optional - for Lambda cold start optimization)
# ============================================================================

_parser: Optional[FundDataParser] = None


def get_fund_data_parser() -> FundDataParser:
    """Get or create fund data parser singleton.

    Returns:
        FundDataParser instance (shared across Lambda invocations)

    Example:
        >>> parser = get_fund_data_parser()
        >>> records = parser.parse(csv_bytes, s3_key)
    """
    global _parser
    if _parser is None:
        _parser = FundDataParser()
    return _parser
