"""Ticker fuzzy matching utility"""
import difflib
from typing import Optional, Tuple

class TickerMatcher:
    """Fuzzy matching for ticker symbols"""
    
    def __init__(self, ticker_map: dict):
        """
        Initialize ticker matcher with ticker map
        
        Args:
            ticker_map: Dictionary mapping ticker symbols to Yahoo tickers
        """
        self.ticker_map = ticker_map
        self.available_tickers = list(ticker_map.keys())
    
    def find_best_match(self, input_ticker: str, min_similarity: float = 0.6) -> Optional[Tuple[str, float]]:
        """
        Find best matching ticker using fuzzy matching
        
        Args:
            input_ticker: User input ticker (may have typos)
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            Tuple of (matched_ticker, similarity_score) or None if no good match
        """
        input_upper = input_ticker.upper().strip()
        
        # First try exact match
        if input_upper in self.ticker_map:
            return (input_upper, 1.0)
        
        # Try fuzzy matching
        matches = difflib.get_close_matches(
            input_upper,
            self.available_tickers,
            n=1,
            cutoff=min_similarity
        )
        
        if matches:
            matched_ticker = matches[0]
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, input_upper, matched_ticker).ratio()
            return (matched_ticker, similarity)
        
        return None
    
    def match_with_suggestion(self, input_ticker: str, min_similarity: float = 0.6) -> Tuple[str, Optional[str]]:
        """
        Match ticker and return suggestion if typo detected
        
        Args:
            input_ticker: User input ticker
            min_similarity: Minimum similarity threshold
        
        Returns:
            Tuple of (ticker_to_use, suggestion_message)
            suggestion_message is None if exact match or confidence is high
        """
        input_upper = input_ticker.upper().strip()
        
        # Exact match
        if input_upper in self.ticker_map:
            return (input_upper, None)
        
        # Fuzzy match
        match_result = self.find_best_match(input_ticker, min_similarity)
        
        if match_result:
            matched_ticker, similarity = match_result
            
            # High confidence (>85%) - auto-correct silently
            if similarity >= 0.85:
                return (matched_ticker, None)
            
            # Medium confidence (60-85%) - suggest correction
            elif similarity >= 0.6:
                return (matched_ticker, f"?? ??????? {matched_ticker} ???????? (????????: {input_ticker.upper()})")
        
        # No good match found
        return (input_upper, None)