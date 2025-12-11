# -*- coding: utf-8 -*-
"""
SEC EDGAR MCP Server Lambda Handler

Implements Model Context Protocol (MCP) server for SEC EDGAR filings.
Exposes tools for fetching SEC filings (10-K, 10-Q, 8-K, etc.) for US-listed stocks.

MCP Protocol:
- Endpoint: /mcp
- Method: POST
- Content-Type: application/json
- Protocol: JSON-RPC 2.0
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# SEC EDGAR API endpoints
SEC_EDGAR_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_DATA_URL = "https://data.sec.gov"  # For structured data APIs
SEC_EDGAR_API_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


class SECEdgarClient:
    """Client for fetching SEC EDGAR filings."""
    
    def __init__(self):
        """Initialize SEC EDGAR client with user agent header."""
        # SEC requires User-Agent header identifying the requester
        self.user_agent = os.getenv(
            'SEC_EDGAR_USER_AGENT',
            'dr-daily-report/1.0 (contact: support@example.com)'
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })
    
    def get_latest_filing(
        self,
        ticker: str,
        form_type: str = '10-Q',
        lookback_days: int = 365
    ) -> Dict[str, Any]:
        """
        Get latest SEC filing for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'NVDA')
            form_type: Form type (10-K, 10-Q, 8-K, etc.)
            lookback_days: Maximum days to look back for filings
            
        Returns:
            Dictionary with filing data:
            {
                'ticker': str,
                'form_type': str,
                'filing_date': str (ISO format),
                'company_name': str,
                'cik': str,
                'accession_number': str,
                'filing_url': str,
                'xbrl': dict (if available),
                'summary': str
            }
        """
        try:
            # Step 1: Get CIK (Central Index Key) for ticker
            cik = self._get_cik_for_ticker(ticker)
            if not cik:
                raise ValueError(f"Could not find CIK for ticker: {ticker}")
            
            # Step 2: Search for latest filing of specified type
            filing = self._get_latest_filing_by_type(cik, form_type, lookback_days)
            if not filing:
                return {
                    'ticker': ticker,
                    'form_type': form_type,
                    'filing_date': None,
                    'error': f'No {form_type} filing found in last {lookback_days} days'
                }
            
            # Step 3: Get filing details
            filing_details = self._get_filing_details(filing)
            
            return {
                'ticker': ticker,
                'form_type': form_type,
                'filing_date': filing['filingDate'],
                'company_name': filing.get('companyName', ''),
                'cik': cik,
                'accession_number': filing['accessionNumber'],
                'filing_url': filing.get('filingUrl', ''),
                'xbrl': filing_details.get('xbrl', {}),
                'summary': filing_details.get('summary', ''),
                'document_count': filing.get('documentCount', 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching SEC filing for {ticker}: {e}")
            raise
    
    def _get_cik_for_ticker(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker symbol.
        
        Uses SEC company tickers JSON file.
        """
        try:
            # SEC provides a ticker-to-CIK mapping file
            tickers_url = f"{SEC_EDGAR_BASE_URL}/files/company_tickers.json"
            response = self.session.get(tickers_url, timeout=10)
            response.raise_for_status()
            
            tickers_data = response.json()
            
            # Find ticker in the data
            for entry in tickers_data.values():
                if entry.get('ticker', '').upper() == ticker.upper():
                    return str(entry['cik_str']).zfill(10)  # CIK is 10 digits
            
            logger.warning(f"Ticker {ticker} not found in SEC ticker database")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching CIK for {ticker}: {e}")
            return None
    
    def _get_latest_filing_by_type(
        self,
        cik: str,
        form_type: str,
        lookback_days: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest filing of specified type for a CIK.
        
        Uses SEC EDGAR search API and parses HTML response.
        """
        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')
            
            # SEC EDGAR search endpoint
            params = {
                'action': 'getcompany',
                'CIK': cik,
                'type': form_type,
                'dateb': cutoff_date,
                'owner': 'exclude',
                'count': '10'  # Get multiple to find latest valid one
            }
            
            response = self.session.get(SEC_EDGAR_API_URL, params=params, timeout=15)
            response.raise_for_status()
            
            html_content = response.text
            
            # Check if we got results
            if 'No matching CIK' in html_content or 'No matches' in html_content:
                logger.warning(f"No {form_type} filings found for CIK {cik}")
                return None
            
            # Parse HTML table to extract filing data
            # SEC EDGAR returns HTML table with filing information
            # Format: <tr> rows with filing data
            
            # Extract company name from HTML
            company_name_match = re.search(r'<span class="companyName">(.*?)</span>', html_content, re.DOTALL)
            company_name = company_name_match.group(1).strip() if company_name_match else 'Unknown Company'
            # Clean HTML tags from company name
            company_name = re.sub(r'<[^>]+>', '', company_name).strip()
            
            # Parse filing table rows
            # SEC table format: <tr> with filing date, form type, accession number links
            filing_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.DOTALL)
            
            for row in filing_rows:
                # Skip header rows
                if 'Filing Date' in row or 'th>' in row.lower() or '<th' in row.lower():
                    continue
                
                # Extract filing date - look for YYYY-MM-DD format in table cells
                # SEC format: YYYY-MM-DD in a <td> element
                date_match = re.search(r'<td[^>]*>(\d{4}-\d{2}-\d{2})</td>', row)
                if not date_match:
                    # Try alternative format
                    date_match = re.search(r'>(\d{4}-\d{2}-\d{2})<', row)
                if not date_match:
                    continue
                
                filing_date = date_match.group(1)
                
                # Extract accession number from link
                # Format: /cgi-bin/viewer?action=view&cik=...&accession_number=...&xbrl_type=v
                accession_match = re.search(r'accession_number=([^&\s"]+)', row)
                if not accession_match:
                    continue
                
                accession_number = accession_match.group(1)
                
                # Extract document count
                doc_count_match = re.search(r'(\d+)\s*document', row, re.IGNORECASE)
                document_count = int(doc_count_match.group(1)) if doc_count_match else 1
                
                # Extract filing URL
                url_match = re.search(r'href="([^"]*viewer[^"]*)"', row)
                if url_match:
                    filing_url = url_match.group(1)
                    # Decode HTML entities
                    filing_url = filing_url.replace('&amp;', '&').replace('&amp;amp;', '&')
                    if not filing_url.startswith('http'):
                        filing_url = f"https://www.sec.gov{filing_url}"
                else:
                    filing_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_number}"
                
                # Found a valid filing - return it (first one is latest)
                logger.info(f"Found {form_type} filing: {filing_date}, accession: {accession_number}")
                return {
                    'filingDate': filing_date,
                    'accessionNumber': accession_number,
                    'companyName': company_name,
                    'filingUrl': filing_url,
                    'documentCount': document_count
                }
            
            # No valid filing found in parsed rows
            logger.warning(f"Could not parse filing data from HTML for CIK {cik}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching filing for CIK {cik}: {e}", exc_info=True)
            return None
    
    def _get_filing_details(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed filing information including XBRL data if available.
        
        Args:
            filing: Basic filing information
            
        Returns:
            Dictionary with filing details
        """
        # TODO: Implement XBRL parsing
        # For now, return placeholder
        return {
            'xbrl': {},
            'summary': f"SEC filing {filing.get('form_type', 'N/A')} for {filing.get('filingDate', 'N/A')}"
        }
    
    def get_financial_statements(
        self,
        ticker: str,
        form_type: str = '10-Q'
    ) -> Dict[str, Any]:
        """
        Get latest quarter financial statements (Income Statement, Balance Sheet, Cash Flow).
        
        Args:
            ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')
            form_type: Form type (10-Q for quarterly, 10-K for annual)
            
        Returns:
            Dictionary with financial statement data:
            {
                'ticker': str,
                'form_type': str,
                'filing_date': str,
                'period_end': str,
                'income_statement': dict,
                'balance_sheet': dict,
                'cash_flow': dict
            }
        """
        try:
            # Step 1: Get latest filing
            filing = self.get_latest_filing(ticker, form_type)
            if not filing or filing.get('error'):
                return {
                    'ticker': ticker,
                    'form_type': form_type,
                    'error': filing.get('error', 'No filing found') if filing else 'No filing found'
                }
            
            cik = filing['cik']
            accession_number = filing['accession_number']
            
            # Step 2: Extract CIK number (remove leading zeros for URL)
            cik_number = str(int(cik))
            
            # Step 3: Fetch XBRL data from SEC
            # SEC provides XBRL data in JSON format
            # URL format: https://data.sec.gov/api/xbrl/companyconcept/CIK{CIK}/us-gaap/{concept}.json
            # Or we can fetch the filing document and parse it
            
            # For now, fetch the filing document URL and extract key financial metrics
            # In production, use sec-edgar-downloader or parse XBRL directly
            
            # Extract period end date from accession number (format: CIK-YY-MMDD-XXXXX)
            # YY-MMDD format: 24-1120 means 2024-11-20
            accession_parts = accession_number.split('-')
            if len(accession_parts) >= 3:
                year_part = accession_parts[1]  # e.g., "24"
                date_part = accession_parts[2]  # e.g., "1120"
                if len(date_part) == 4:
                    # Convert YY to 20YY
                    year = f"20{year_part}"
                    month = date_part[:2]
                    day = date_part[2:]
                    period_end = f"{year}-{month}-{day}"
                else:
                    period_end = filing['filing_date']
            else:
                period_end = filing['filing_date']
            
            # Fetch financial data from SEC API
            # Use company facts API for structured data
            company_facts_url = f"{SEC_EDGAR_DATA_URL}/api/xbrl/companyfacts/CIK{cik_number.zfill(10)}.json"
            
            financial_data = {
                'ticker': ticker,
                'form_type': form_type,
                'filing_date': filing['filing_date'],
                'period_end': period_end,
                'company_name': filing['company_name'],
                'cik': cik,
                'accession_number': accession_number,
                'filing_url': filing['filing_url'],
                'income_statement': {},
                'balance_sheet': {},
                'cash_flow': {}
            }
            
            # Fetch company facts (structured financial data)
            try:
                response = self.session.get(company_facts_url, timeout=15)
                if response.status_code == 200:
                    facts_data = response.json()
                    
                    # Extract financial statements from company facts
                    # SEC uses US-GAAP taxonomy concepts
                    us_gaap = facts_data.get('facts', {}).get('us-gaap', {})
                    
                    # Income Statement metrics
                    income_statement = {}
                    revenue_concept = us_gaap.get('Revenues', {})
                    if revenue_concept.get('units'):
                        # Get latest period value
                        for unit, periods in revenue_concept['units'].items():
                            if periods:
                                # Handle both dict and list formats
                                if isinstance(periods, dict):
                                    latest = sorted(periods.items(), key=lambda x: x[0], reverse=True)[0]
                                    period_key = latest[0]
                                    period_data = latest[1]
                                elif isinstance(periods, list):
                                    latest = sorted(periods, key=lambda x: x.get('end', ''), reverse=True)[0]
                                    period_key = latest.get('end', '')
                                    period_data = [latest]
                                else:
                                    continue
                                
                                if isinstance(period_data, list) and len(period_data) > 0:
                                    income_statement['revenue'] = {
                                        'value': period_data[0].get('val'),
                                        'unit': unit,
                                        'period': period_key
                                    }
                                    break
                    
                    net_income_concept = us_gaap.get('NetIncomeLoss', {})
                    if net_income_concept.get('units'):
                        for unit, periods in net_income_concept['units'].items():
                            if periods:
                                if isinstance(periods, dict):
                                    latest = sorted(periods.items(), key=lambda x: x[0], reverse=True)[0]
                                    period_key = latest[0]
                                    period_data = latest[1]
                                elif isinstance(periods, list):
                                    latest = sorted(periods, key=lambda x: x.get('end', ''), reverse=True)[0]
                                    period_key = latest.get('end', '')
                                    period_data = [latest]
                                else:
                                    continue
                                
                                if isinstance(period_data, list) and len(period_data) > 0:
                                    income_statement['net_income'] = {
                                        'value': period_data[0].get('val'),
                                        'unit': unit,
                                        'period': period_key
                                    }
                                    break
                    
                    # Helper function to extract latest value from periods
                    def extract_latest_value(concept_data, concept_name):
                        """Extract latest value from a US-GAAP concept."""
                        if not concept_data.get('units'):
                            return None
                        
                        for unit, periods in concept_data['units'].items():
                            if not periods:
                                continue
                            
                            try:
                                if isinstance(periods, dict):
                                    latest = sorted(periods.items(), key=lambda x: x[0], reverse=True)[0]
                                    period_key = latest[0]
                                    period_data = latest[1]
                                elif isinstance(periods, list):
                                    latest = sorted(periods, key=lambda x: x.get('end', ''), reverse=True)[0]
                                    period_key = latest.get('end', '')
                                    period_data = [latest]
                                else:
                                    continue
                                
                                if isinstance(period_data, list) and len(period_data) > 0:
                                    return {
                                        'value': period_data[0].get('val'),
                                        'unit': unit,
                                        'period': period_key
                                    }
                            except Exception as e:
                                logger.debug(f"Error extracting {concept_name}: {e}")
                                continue
                        return None
                    
                    # Balance Sheet metrics
                    balance_sheet = {}
                    assets_concept = us_gaap.get('Assets', {})
                    if assets_concept:
                        result = extract_latest_value(assets_concept, 'Assets')
                        if result:
                            balance_sheet['total_assets'] = result
                    
                    liabilities_concept = us_gaap.get('Liabilities', {})
                    if liabilities_concept:
                        result = extract_latest_value(liabilities_concept, 'Liabilities')
                        if result:
                            balance_sheet['total_liabilities'] = result
                    
                    equity_concept = us_gaap.get('StockholdersEquity', {}) or us_gaap.get('Equity', {})
                    if equity_concept:
                        result = extract_latest_value(equity_concept, 'Equity')
                        if result:
                            balance_sheet['stockholders_equity'] = result
                    
                    # Cash Flow metrics
                    cash_flow = {}
                    operating_cash_concept = us_gaap.get('NetCashProvidedByUsedInOperatingActivities', {})
                    if operating_cash_concept:
                        result = extract_latest_value(operating_cash_concept, 'OperatingCashFlow')
                        if result:
                            cash_flow['operating_cash_flow'] = result
                    
                    financial_data['income_statement'] = income_statement
                    financial_data['balance_sheet'] = balance_sheet
                    financial_data['cash_flow'] = cash_flow
                    financial_data['data_source'] = 'SEC Company Facts API'
                    
                else:
                    financial_data['note'] = f'Company facts API returned status {response.status_code}'
            except Exception as e:
                logger.warning(f"Could not fetch company facts: {e}")
                financial_data['note'] = f'Error fetching financial data: {str(e)}'
            
            return financial_data
            
        except Exception as e:
            logger.error(f"Error fetching financial statements for {ticker}: {e}", exc_info=True)
            return {
                'ticker': ticker,
                'form_type': form_type,
                'error': str(e)
            }


# Initialize client singleton
_sec_client: Optional[SECEdgarClient] = None


def get_sec_client() -> SECEdgarClient:
    """Get singleton SEC EDGAR client."""
    global _sec_client
    if _sec_client is None:
        _sec_client = SECEdgarClient()
    return _sec_client


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for SEC EDGAR MCP server.
    
    Supports both Lambda Function URL and API Gateway events.
    Implements JSON-RPC 2.0 protocol for MCP:
    - tools/list: List available tools
    - tools/call: Call a tool
    
    Args:
        event: Lambda event (Function URL or API Gateway)
        context: Lambda context
        
    Returns:
        For Function URL: Dict with statusCode, headers, body
        For API Gateway: Dict with statusCode, headers, body
    """
    try:
        # Detect event source (Function URL vs API Gateway)
        is_function_url = 'requestContext' in event and 'http' in event.get('requestContext', {})
        is_api_gateway = 'httpMethod' in event or 'requestContext' in event and 'httpMethod' in event.get('requestContext', {})
        
        # Parse request body
        if is_function_url or is_api_gateway:
            # HTTP event (Function URL or API Gateway)
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
        else:
            # Direct invocation (for testing)
            body = event
        
        # Extract JSON-RPC fields
        method = body.get('method')
        params = body.get('params', {})
        request_id = body.get('id', 1)
        
        logger.info(f"MCP request: method={method}, params={params}")
        
        # Route to appropriate handler
        if method == 'tools/list':
            result = handle_tools_list()
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            result = handle_tool_call(tool_name, arguments)
        else:
            error_response = {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }
            return _format_http_response(error_response, 400)
        
        # Return success response
        success_response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }
        return _format_http_response(success_response, 200)
        
    except Exception as e:
        logger.error(f"MCP server error: {e}", exc_info=True)
        error_response = {
            'jsonrpc': '2.0',
            'id': body.get('id', 1) if 'body' in locals() else 1,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }
        return _format_http_response(error_response, 500)


def _format_http_response(data: Dict[str, Any], status_code: int) -> Dict[str, Any]:
    """
    Format response for Lambda Function URL or API Gateway.
    
    Args:
        data: Response data (JSON-RPC response)
        status_code: HTTP status code
        
    Returns:
        Formatted HTTP response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # CORS for MCP clients
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(data)
    }


def handle_tools_list() -> Dict[str, Any]:
    """Handle tools/list MCP request."""
    return {
        'tools': [
            {
                'name': 'get_latest_filing',
                'description': 'Get the latest SEC filing (10-K, 10-Q, 8-K, etc.) for a US-listed stock ticker',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        },
                        'form_type': {
                            'type': 'string',
                            'description': 'Form type (10-K, 10-Q, 8-K, etc.)',
                            'default': '10-Q'
                        },
                        'lookback_days': {
                            'type': 'integer',
                            'description': 'Maximum days to look back for filings',
                            'default': 365
                        }
                    },
                    'required': ['ticker']
                }
            },
            {
                'name': 'get_financial_statements',
                'description': 'Get latest quarter/annual financial statements (Income Statement, Balance Sheet, Cash Flow) for a US-listed stock ticker',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'ticker': {
                            'type': 'string',
                            'description': 'Stock ticker symbol (e.g., AAPL, NVDA)'
                        },
                        'form_type': {
                            'type': 'string',
                            'description': 'Form type - 10-Q for quarterly, 10-K for annual',
                            'default': '10-Q'
                        }
                    },
                    'required': ['ticker']
                }
            }
        ]
    }


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle tools/call MCP request.
    
    Args:
        tool_name: Tool name to call
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    if tool_name == 'get_latest_filing':
        ticker = arguments.get('ticker')
        if not ticker:
            raise ValueError("ticker argument is required")
        
        form_type = arguments.get('form_type', '10-Q')
        lookback_days = arguments.get('lookback_days', 365)
        
        client = get_sec_client()
        result = client.get_latest_filing(ticker, form_type, lookback_days)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(result, indent=2)
                }
            ]
        }
    elif tool_name == 'get_financial_statements':
        ticker = arguments.get('ticker')
        if not ticker:
            raise ValueError("ticker argument is required")
        
        form_type = arguments.get('form_type', '10-Q')
        
        client = get_sec_client()
        result = client.get_financial_statements(ticker, form_type)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(result, indent=2)
                }
            ]
        }
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
