# -*- coding: utf-8 -*-
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

class NewsFetcher:
    """Fetch and filter high-impact news from Yahoo Finance"""

    # Keywords that indicate high-impact news
    HIGH_IMPACT_KEYWORDS = [
        # Earnings & Financial Results
        'earnings', 'revenue', 'profit', 'loss', 'quarterly results', 'annual results',
        'eps', 'beat', 'miss', 'guidance', 'outlook', 'forecast',

        # Corporate Actions
        'merger', 'acquisition', 'buyout', 'takeover', 'deal', 'partnership',
        'dividend', 'stock split', 'share buyback', 'repurchase',

        # Management & Strategy
        'ceo', 'resignation', 'appointed', 'fired', 'restructuring', 'layoff',
        'bankruptcy', 'chapter 11',

        # Regulatory & Legal
        'sec', 'investigation', 'lawsuit', 'settlement', 'fine', 'penalty',
        'regulatory', 'approval', 'fda', 'patent',

        # Market Moving Events
        'downgrade', 'upgrade', 'rating', 'price target', 'analyst',
        'halt', 'suspended', 'delisting',

        # Financial Health
        'debt', 'default', 'credit rating', 'liquidity', 'cash flow',
        'funding', 'capital raise', 'ipo', 'offering'
    ]

    # Negative sentiment indicators
    NEGATIVE_KEYWORDS = [
        'loss', 'miss', 'decline', 'drop', 'fall', 'plunge', 'crash',
        'lawsuit', 'investigation', 'scandal', 'fraud', 'bankruptcy',
        'downgrade', 'warning', 'risk', 'concern', 'threat',
        'layoff', 'fired', 'resignation', 'suspended', 'halt'
    ]

    # Positive sentiment indicators
    POSITIVE_KEYWORDS = [
        'beat', 'surge', 'soar', 'rally', 'gain', 'growth', 'profit',
        'upgrade', 'partnership', 'deal', 'approval', 'breakthrough',
        'record', 'strong', 'robust', 'exceed', 'outperform'
    ]

    def __init__(self):
        pass

    def fetch_news(self, ticker: str, max_news: int = 20) -> List[Dict]:
        """Fetch recent news for a ticker from Yahoo Finance.
        
        Symbol-type invariant: Accepts any symbol format (DR, Yahoo, etc.)
        and automatically resolves to Yahoo Finance format before API calls.

        Args:
            ticker: Ticker symbol in any format (e.g., 'DBS19' or 'D05.SI')
            max_news: Maximum number of news items to fetch

        Returns:
            List of news dictionaries with title, link, publisher, and timestamp
        """
        # Resolve symbol to Yahoo Finance format (symbol-type invariant)
        try:
            from src.data.aurora.ticker_resolver import get_ticker_resolver
            resolver = get_ticker_resolver()
            ticker_info = resolver.resolve(ticker)
            yahoo_ticker = ticker_info.yahoo_symbol if ticker_info else ticker
        except Exception as e:
            # If resolver fails, use ticker as-is (might be new ticker)
            logger.debug(f"Symbol resolution failed for {ticker}: {e}, using as-is")
            yahoo_ticker = ticker
        
        try:
            stock = yf.Ticker(yahoo_ticker)
            news = stock.news

            if not news:
                return []

            # Process and format news
            formatted_news = []
            for item in news[:max_news]:
                # Yahoo Finance API has nested structure - check for 'content' object
                content = item.get('content', item)

                # Get title from nested content or top level
                title = content.get('title', item.get('title', ''))

                # Get publisher from nested provider or top level
                provider = content.get('provider', {})
                publisher = provider.get('displayName', item.get('publisher', 'Unknown'))

                # Get link from canonicalUrl or top level
                canonical = content.get('canonicalUrl', {})
                link = canonical.get('url', item.get('link', ''))

                # Get timestamp from pubDate or providerPublishTime
                pub_date = content.get('pubDate', content.get('displayTime', ''))
                if pub_date:
                    try:
                        from dateutil import parser
                        timestamp = parser.parse(pub_date)
                    except:
                        timestamp = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                else:
                    timestamp = datetime.fromtimestamp(item.get('providerPublishTime', 0))

                formatted_news.append({
                    'title': title,
                    'link': link,
                    'publisher': publisher,
                    'timestamp': timestamp,
                    'raw': item
                })

            return formatted_news

        except Exception as e:
            logger.error(f"Error fetching news for {ticker} (resolved to {yahoo_ticker}): {str(e)}")
            return []

    def calculate_impact_score(self, news_item: Dict) -> float:
        """
        Calculate impact score for a news item (0-100)
        Higher score = more likely to impact price

        Scoring factors:
        - High impact keywords: +10 each
        - Recency: +20 if < 24h, +10 if < 7 days
        - Sentiment strength: +15 if strong positive/negative
        - Publisher credibility: +10 if major outlet
        """
        score = 0.0
        title = news_item.get('title', '').lower()
        timestamp = news_item.get('timestamp')
        publisher = news_item.get('publisher', '').lower()

        # 1. Keyword matching (max 40 points)
        keyword_matches = sum(1 for keyword in self.HIGH_IMPACT_KEYWORDS if keyword in title)
        score += min(keyword_matches * 10, 40)

        # 2. Recency score (max 20 points)
        if timestamp:
            # Make both datetimes timezone-aware or naive for comparison
            now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
            hours_ago = (now - timestamp).total_seconds() / 3600
            if hours_ago < 24:
                score += 20
            elif hours_ago < 168:  # 7 days
                score += 10

        # 3. Sentiment strength (max 15 points)
        negative_count = sum(1 for keyword in self.NEGATIVE_KEYWORDS if keyword in title)
        positive_count = sum(1 for keyword in self.POSITIVE_KEYWORDS if keyword in title)

        if negative_count >= 2 or positive_count >= 2:
            score += 15
        elif negative_count >= 1 or positive_count >= 1:
            score += 7

        # 4. Publisher credibility (max 10 points)
        major_publishers = ['reuters', 'bloomberg', 'wsj', 'financial times',
                           'cnbc', 'marketwatch', 'barrons', 'seeking alpha']
        if any(pub in publisher for pub in major_publishers):
            score += 10

        # 5. Earnings-specific boost (max 15 points)
        earnings_keywords = ['earnings', 'quarterly results', 'eps', 'revenue']
        if any(keyword in title for keyword in earnings_keywords):
            score += 15

        return min(score, 100)

    def classify_sentiment(self, news_item: Dict) -> str:
        """
        Classify news sentiment as 'positive', 'negative', or 'neutral'
        """
        title = news_item.get('title', '').lower()

        negative_count = sum(1 for keyword in self.NEGATIVE_KEYWORDS if keyword in title)
        positive_count = sum(1 for keyword in self.POSITIVE_KEYWORDS if keyword in title)

        if positive_count > negative_count and positive_count >= 1:
            return 'positive'
        elif negative_count > positive_count and negative_count >= 1:
            return 'negative'
        else:
            return 'neutral'

    def filter_high_impact_news(self, ticker: str, min_score: float = 40.0,
                               max_news: int = 5) -> List[Dict]:
        """
        Fetch and filter only high-impact news

        Args:
            ticker: Yahoo Finance ticker symbol
            min_score: Minimum impact score to include (0-100)
            max_news: Maximum number of high-impact news to return

        Returns:
            List of high-impact news with scores and metadata
        """
        all_news = self.fetch_news(ticker, max_news=20)

        if not all_news:
            return []

        # Score and filter news
        scored_news = []
        for news_item in all_news:
            score = self.calculate_impact_score(news_item)

            if score >= min_score:
                news_item['impact_score'] = score
                news_item['sentiment'] = self.classify_sentiment(news_item)
                scored_news.append(news_item)

        # Sort by impact score (descending)
        scored_news.sort(key=lambda x: x['impact_score'], reverse=True)

        return scored_news[:max_news]

    def format_news_for_report(self, news_items: List[Dict]) -> str:
        """
        Format news items for inclusion in Thai report

        Returns Thai text with references like [1], [2], etc.
        """
        if not news_items:
            return ""

        formatted = "📰 **ข่าวสำคัญล่าสุด:**\n\n"

        for idx, news in enumerate(news_items, 1):
            title = news['title']
            sentiment = news['sentiment']
            score = news['impact_score']
            timestamp = news['timestamp']

            # Format timestamp
            now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
            hours_ago = (now - timestamp).total_seconds() / 3600
            if hours_ago < 24:
                time_str = f"{int(hours_ago)} ชั่วโมงที่แล้ว"
            else:
                days_ago = int(hours_ago / 24)
                time_str = f"{days_ago} วันที่แล้ว"

            # Sentiment emoji
            sentiment_emoji = {
                'positive': '📈',
                'negative': '📉',
                'neutral': '📊'
            }.get(sentiment, '📊')

            formatted += f"[{idx}] {sentiment_emoji} {title}\n"
            formatted += f"    (ผลกระทบ: {score:.0f}/100 | {time_str})\n\n"

        return formatted

    def get_news_references(self, news_items: List[Dict]) -> str:
        """
        Create reference list with links
        """
        if not news_items:
            return ""

        references = "\n📎 **แหล่งข้อมูลข่าว:**\n"

        for idx, news in enumerate(news_items, 1):
            publisher = news['publisher']
            link = news['link']
            references += f"[{idx}] {publisher}: {link}\n"

        return references

    def get_news_summary(self, news_items: List[Dict]) -> Dict:
        """
        Get summary statistics about the news
        """
        if not news_items:
            return {
                'total_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'avg_impact_score': 0,
                'has_recent_news': False
            }

        positive = sum(1 for n in news_items if n['sentiment'] == 'positive')
        negative = sum(1 for n in news_items if n['sentiment'] == 'negative')
        neutral = sum(1 for n in news_items if n['sentiment'] == 'neutral')

        avg_score = sum(n['impact_score'] for n in news_items) / len(news_items)

        # Check if any news is less than 24 hours old
        def is_recent(news):
            ts = news['timestamp']
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            return (now - ts).total_seconds() < 86400

        recent = any(is_recent(n) for n in news_items)

        return {
            'total_count': len(news_items),
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'avg_impact_score': avg_score,
            'has_recent_news': recent,
            'dominant_sentiment': 'positive' if positive > negative else
                                 'negative' if negative > positive else 'neutral'
        }
