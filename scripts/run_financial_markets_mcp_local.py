#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Financial Markets MCP Server Runner

FastAPI server running Financial Markets MCP handler locally for testing.
Mimics Lambda Function URL behavior.
"""

import os
import sys
import json
import logging
import argparse
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from src.mcp_servers.financial_markets_handler import lambda_handler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Local Financial Markets MCP Server", version="1.0.0")

# Add CORS middleware (mimics Lambda Function URL CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def convert_fastapi_to_lambda_event(request: Request) -> dict:
    """
    Convert FastAPI request to Lambda event format.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Lambda event dictionary
    """
    # Read request body
    body = await request.body()
    
    # Convert to Lambda event format
    event = {
        'httpMethod': request.method,
        'path': request.url.path,
        'headers': dict(request.headers),
        'queryStringParameters': dict(request.query_params) if request.query_params else None,
        'body': body.decode('utf-8') if isinstance(body, bytes) else body,
        'isBase64Encoded': False,
        'requestContext': {
            'http': {
                'method': request.method,
                'path': request.url.path
            }
        }
    }
    
    return event


def convert_lambda_to_fastapi_response(lambda_response: dict) -> Response:
    """
    Convert Lambda response to FastAPI response.
    
    Args:
        lambda_response: Lambda response dictionary
        
    Returns:
        FastAPI Response object
    """
    status_code = lambda_response.get('statusCode', 200)
    headers = lambda_response.get('headers', {})
    body = lambda_response.get('body', '{}')
    
    # Parse JSON body if it's a string
    if isinstance(body, str):
        try:
            body_json = json.loads(body)
            return JSONResponse(
                content=body_json,
                status_code=status_code,
                headers=headers
            )
        except json.JSONDecodeError:
            # Not JSON, return as text
            return Response(
                content=body,
                status_code=status_code,
                headers=headers,
                media_type='application/json'
            )
    else:
        return JSONResponse(
            content=body,
            status_code=status_code,
            headers=headers
        )


@app.post("/mcp")
async def handle_mcp(request: Request):
    """
    Handle MCP protocol requests.
    
    Mimics Lambda Function URL behavior.
    """
    try:
        # Convert FastAPI request to Lambda event
        event = await convert_fastapi_to_lambda_event(request)
        
        # Call Lambda handler (synchronous)
        lambda_response = lambda_handler(event, None)
        
        # Convert Lambda response to FastAPI response
        return convert_lambda_to_fastapi_response(lambda_response)
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': f'Internal error: {str(e)}'
                },
                'id': None
            }
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "local-financial-markets-mcp-server"}


def main():
    """Run local Financial Markets MCP server."""
    parser = argparse.ArgumentParser(
        description='Run local Financial Markets MCP server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start on default port 8003
  python scripts/run_financial_markets_mcp_local.py

  # Start on custom port
  python scripts/run_financial_markets_mcp_local.py --port 8000

  # Set FINANCIAL_MARKETS_MCP_URL before generating reports
  export FINANCIAL_MARKETS_MCP_URL=http://localhost:8003
  python scripts/run_financial_markets_mcp_local.py --port 8003
        """
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('FINANCIAL_MARKETS_MCP_PORT', '8003')),
        help='Port to run server on (default: 8003 or FINANCIAL_MARKETS_MCP_PORT env var)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default=os.getenv('FINANCIAL_MARKETS_MCP_HOST', '127.0.0.1'),
        help='Host to bind to (default: 127.0.0.1 or FINANCIAL_MARKETS_MCP_HOST env var)'
    )
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Starting local Financial Markets MCP server on {args.host}:{args.port}")
    logger.info(f"   MCP endpoint: http://{args.host}:{args.port}/mcp")
    logger.info(f"   Health check: http://{args.host}:{args.port}/health")
    logger.info(f"   Set FINANCIAL_MARKETS_MCP_URL=http://{args.host}:{args.port} to use this server")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
