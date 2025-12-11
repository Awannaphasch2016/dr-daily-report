# -*- coding: utf-8 -*-
"""
MCP Client for calling MCP servers from LangGraph workflow.

This module provides a client for calling Model Context Protocol (MCP) servers
via HTTP. It supports multiple MCP servers (SEC EDGAR, Alpaca, Financial Markets)
with error handling, timeout management, and circuit breaker patterns.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MCPServerError(Exception):
    """Exception raised when MCP server call fails."""
    pass


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for MCP server calls to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count: Dict[str, int] = {}
        self.circuit_open: Dict[str, datetime] = {}
    
    def call(self, server: str, func, *args, **kwargs):
        """
        Call function with circuit breaker protection.
        
        Args:
            server: MCP server name (for tracking failures)
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
        """
        # Check if circuit is open
        if server in self.circuit_open:
            open_time = self.circuit_open[server]
            if datetime.now() - open_time < timedelta(seconds=self.timeout):
                logger.warning(f"Circuit breaker OPEN for {server}, skipping call")
                raise CircuitBreakerOpenError(f"Circuit breaker open for {server}")
            else:
                # Timeout expired, attempt to close circuit
                logger.info(f"Attempting to close circuit for {server}")
                del self.circuit_open[server]
                self.failure_count[server] = 0
        
        # Attempt call
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            self.failure_count[server] = 0
            return result
        except Exception as e:
            # Failure - increment count
            self.failure_count[server] = self.failure_count.get(server, 0) + 1
            logger.warning(
                f"MCP call failed for {server}: {e} "
                f"(failures: {self.failure_count[server]})"
            )
            
            # Open circuit if threshold reached
            if self.failure_count[server] >= self.failure_threshold:
                self.circuit_open[server] = datetime.now()
                logger.error(f"Circuit breaker OPENED for {server}")
            
            raise


class MCPClient:
    """
    Client for calling MCP servers via HTTP.
    
    Supports multiple MCP servers with error handling, timeout management,
    and circuit breaker patterns for resilience.
    """
    
    def __init__(self, timeout: Optional[int] = None):
        """
        Initialize MCP client with server URLs from environment.
        
        Args:
            timeout: Default request timeout in seconds (default: 30)
        """
        self.servers = {
            'sec_edgar': os.getenv('SEC_EDGAR_MCP_URL') if os.getenv('ENABLE_SEC_EDGAR', 'false').lower() == 'true' else None,
            'alpaca': os.getenv('ALPACA_MCP_URL'),
            'financial_markets': os.getenv('FINANCIAL_MARKETS_MCP_URL'),
            'portfolio_manager': os.getenv('PORTFOLIO_MANAGER_MCP_URL'),
        }
        self.timeout = timeout or int(os.getenv('MCP_TIMEOUT', '30'))
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        # Log configured servers
        configured = [s for s, url in self.servers.items() if url]
        if configured:
            logger.info(f"✅ MCP Client initialized with servers: {', '.join(configured)}")
        else:
            logger.warning("⚠️ No MCP servers configured (set MCP_*_URL environment variables)")
    
    def call_tool(
        self,
        server: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call MCP server tool.
        
        Args:
            server: MCP server name ('sec_edgar', 'alpaca', etc.)
            tool_name: Tool name to call
            arguments: Tool arguments
            timeout: Request timeout (default: self.timeout)
            
        Returns:
            Tool response data
            
        Raises:
            ValueError: If server not found or not configured
            MCPServerError: If HTTP request fails
            CircuitBreakerOpenError: If circuit breaker is open
        """
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")
        
        server_url = self.servers[server]
        if not server_url:
            raise ValueError(f"MCP server URL not configured: {server}")
        
        request_timeout = timeout or self.timeout
        
        logger.info(f"Calling MCP tool: {server}.{tool_name}")
        
        def _make_request():
            """Make HTTP request to MCP server."""
            response = requests.post(
                f"{server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                },
                timeout=request_timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                error_msg = data['error'].get('message', 'Unknown error')
                raise MCPServerError(f"MCP error: {error_msg}")
            
            result = data.get("result", {})
            
            # Parse MCP response format: result.content[0].text contains JSON string
            if "content" in result and isinstance(result["content"], list) and len(result["content"]) > 0:
                content_item = result["content"][0]
                if content_item.get("type") == "text" and "text" in content_item:
                    try:
                        # Parse JSON from text field
                        parsed_data = json.loads(content_item["text"])
                        return parsed_data
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse MCP response JSON: {e}, returning raw result")
                        return result
            
            # If no content array, return result as-is (backward compatibility)
            return result
        
        try:
            # Call with circuit breaker protection
            return self.circuit_breaker.call(server, _make_request)
        except CircuitBreakerOpenError:
            # Circuit breaker is open - return empty result for graceful degradation
            logger.warning(f"Circuit breaker open for {server}, returning empty result")
            return {}
        except requests.Timeout:
            logger.error(f"MCP call timed out: {server}.{tool_name}")
            raise MCPServerError(f"MCP timeout: {server}.{tool_name}")
        except requests.RequestException as e:
            logger.error(f"MCP call failed: {server}.{tool_name} - {e}")
            raise MCPServerError(f"MCP call failed: {server}.{tool_name} - {e}")
    
    def list_tools(self, server: str) -> List[Dict[str, Any]]:
        """
        List available tools for an MCP server.
        
        Args:
            server: MCP server name
            
        Returns:
            List of available tools
            
        Raises:
            ValueError: If server not found or not configured
            MCPServerError: If HTTP request fails
        """
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")
        
        server_url = self.servers[server]
        if not server_url:
            raise ValueError(f"MCP server URL not configured: {server}")
        
        try:
            response = requests.post(
                f"{server_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 1
                },
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                error_msg = data['error'].get('message', 'Unknown error')
                raise MCPServerError(f"MCP error: {error_msg}")
            
            return data.get("result", {}).get("tools", [])
            
        except requests.RequestException as e:
            logger.error(f"Failed to list tools: {server} - {e}")
            raise MCPServerError(f"Failed to list tools: {server} - {e}")
    
    def is_server_available(self, server: str) -> bool:
        """
        Check if MCP server is configured and available.
        
        Args:
            server: MCP server name
            
        Returns:
            True if server is configured, False otherwise
        """
        return server in self.servers and self.servers[server] is not None


# Singleton instance
_mcp_client: Optional[MCPClient] = None


@lru_cache(maxsize=1)
def get_mcp_client() -> MCPClient:
    """
    Get singleton MCP client instance.
    
    Returns:
        MCPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
