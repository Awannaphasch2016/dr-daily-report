import json
from datetime import datetime
from typing import TYPE_CHECKING
from src.agent import TickerAnalysisAgent

if TYPE_CHECKING:
    from typing_extensions import TypedDict

    class LambdaEvent(TypedDict, total=False):
        queryStringParameters: dict[str, str] | None
        headers: dict[str, str] | None
        body: str | None

    class LambdaContext:
        pass

# Initialize agent (cold start optimization)
agent = None

def get_agent():
    """Get or create agent instance"""
    global agent
    if agent is None:
        agent = TickerAnalysisAgent()
    return agent

def sanitize_ticker_data(data: dict[str, object]) -> dict[str, object]:
    """
    Remove non-serializable objects from ticker_data (e.g., DataFrame)

    Args:
        data: Raw ticker_data dictionary

    Returns:
        Sanitized dictionary suitable for JSON serialization
    """
    sanitized: dict[str, object] = {}
    
    # Copy all fields except 'history' (DataFrame)
    for key, value in data.items():
        if key == 'history':
            # Skip DataFrame - it's too large and not needed for API response
            continue
        elif value is None:
            sanitized[key] = None
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, datetime):
            sanitized[key] = value.isoformat()
        else:
            # Try to convert to string as fallback
            sanitized[key] = str(value)
    
    return sanitized

def sanitize_news(news_list: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    Sanitize news items for JSON serialization

    Args:
        news_list: List of news dictionaries

    Returns:
        List of sanitized news dictionaries
    """
    sanitized_news: list[dict[str, object]] = []
    
    for news_item in news_list:
        sanitized_item: dict[str, object] = {}
        
        for key, value in news_item.items():
            if key == 'raw':
                # Skip raw data - too large and not needed
                continue
            elif key == 'timestamp' and isinstance(value, datetime):
                sanitized_item[key] = value.isoformat()
            elif value is None:
                sanitized_item[key] = None
            elif isinstance(value, (str, int, float, bool)):
                sanitized_item[key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized_item[key] = sanitize_dict(value)
            else:
                sanitized_item[key] = str(value)
        
        sanitized_news.append(sanitized_item)
    
    return sanitized_news

def sanitize_dict(data: dict[str, object]) -> dict[str, object]:
    """Recursively sanitize dictionary for JSON serialization"""
    sanitized: dict[str, object] = {}

    for key, value in data.items():
        if value is None:
            sanitized[key] = None
        elif isinstance(value, datetime):
            sanitized[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = str(value)
    
    return sanitized

def api_handler(event: "LambdaEvent", context: "LambdaContext | None") -> dict[str, object]:
    """
    AWS Lambda handler for REST API endpoint

    Expected query parameters:
    - ticker: Ticker symbol (e.g., 'AAPL', 'DBS19')

    Expected environment variables:
    - OPENAI_API_KEY: OpenAI API key

    Returns:
        JSON response with ticker analysis data including percentiles
    """
    try:
        # Extract ticker from query parameters
        query_params = event.get('queryStringParameters') or {}
        ticker = query_params.get('ticker')
        
        if not ticker:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'  # CORS support
                },
                'body': json.dumps({
                    'error': 'Missing required parameter: ticker',
                    'message': 'Please provide a ticker symbol as a query parameter. Example: /analyze?ticker=AAPL'
                })
            }
        
        # Get agent instance
        agent_instance = get_agent()
        
        # Initialize state (AgentState type)
        from src.agent import AgentState
        initial_state: AgentState = {
            "messages": [],
            "ticker": ticker.upper(),
            "ticker_data": {},
            "indicators": {},
            "percentiles": {},
            "chart_patterns": [],
            "pattern_statistics": {},
            "strategy_performance": {},
            "news": [],
            "news_summary": {},
            "chart_base64": "",
            "report": "",
            "error": ""
        }
        
        # Run the graph to get full AgentState
        final_state = agent_instance.graph.invoke(initial_state)
        
        # Check for errors
        if final_state.get("error"):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': final_state['error'],
                    'ticker': ticker.upper()
                })
            }
        
        # Sanitize data for JSON serialization
        ticker_data = sanitize_ticker_data(final_state.get("ticker_data", {}))
        indicators = sanitize_dict(final_state.get("indicators", {}))
        percentiles = sanitize_dict(final_state.get("percentiles", {}))
        news = sanitize_news(final_state.get("news", []))
        news_summary = sanitize_dict(final_state.get("news_summary", {}))
        chart_base64 = final_state.get("chart_base64", "")
        report = final_state.get("report", "")

        # Build response
        response_data = {
            'ticker': ticker.upper(),
            'ticker_data': ticker_data,
            'indicators': indicators,
            'percentiles': percentiles,  # Include percentiles in response
            'news': news,
            'news_summary': news_summary,
            'chart_base64': chart_base64,  # Include chart as base64 PNG
            'report': report
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # CORS support
            },
            'body': json.dumps(response_data, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Error in API handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def test_handler() -> None:
    """Test handler locally"""
    # Load test event
    test_event: "LambdaEvent" = {
        'queryStringParameters': {
            'ticker': 'DBS19'
        }
    }

    # Test
    result = api_handler(test_event, None)
    body = result.get('body')
    if isinstance(body, str):
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    else:
        print("Error: body is not a string")

if __name__ == "__main__":
    # For local testing
    test_handler()
