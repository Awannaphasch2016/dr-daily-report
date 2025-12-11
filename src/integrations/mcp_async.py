# -*- coding: utf-8 -*-
"""
Async MCP call pattern using SQS for decoupling and resilience.

This module provides async MCP call patterns using Amazon SQS to decouple
the agent from MCP servers, enabling better error handling, retries, and
rate limiting.
"""

import json
import os
import logging
import boto3
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Initialize SQS client
sqs_client = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'ap-southeast-1'))
MCP_QUEUE_URL = os.getenv('MCP_QUEUE_URL')


def queue_mcp_call(
    server: str,
    tool_name: str,
    arguments: Dict[str, Any],
    callback_state: Optional[Dict] = None
) -> str:
    """
    Queue MCP call for async processing via SQS.
    
    Args:
        server: MCP server name ('sec_edgar', 'alpaca', etc.)
        tool_name: Tool name to call
        arguments: Tool arguments
        callback_state: Optional state to pass to callback handler
        
    Returns:
        Request ID for tracking
        
    Raises:
        ValueError: If MCP_QUEUE_URL not configured
    """
    if not MCP_QUEUE_URL:
        raise ValueError("MCP_QUEUE_URL environment variable not set")
    
    request_id = str(uuid4())
    
    message = {
        'request_id': request_id,
        'server': server,
        'tool_name': tool_name,
        'arguments': arguments,
        'callback_state': callback_state or {}
    }
    
    try:
        response = sqs_client.send_message(
            QueueUrl=MCP_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        logger.info(
            f"Queued MCP call: {server}.{tool_name} "
            f"(request_id: {request_id}, message_id: {response['MessageId']})"
        )
        return request_id
        
    except Exception as e:
        logger.error(f"Failed to queue MCP call: {e}")
        raise


def get_queue_status() -> Dict[str, Any]:
    """
    Get SQS queue status (approximate number of messages).
    
    Returns:
        Dictionary with queue status information
    """
    if not MCP_QUEUE_URL:
        return {'error': 'MCP_QUEUE_URL not configured'}
    
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=MCP_QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
        )
        
        attributes = response['Attributes']
        return {
            'queue_url': MCP_QUEUE_URL,
            'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
            'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0))
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return {'error': str(e)}
