"""
Trending content helper for fetching real trending articles and topics
"""
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class TrendingHelper:
    """Helper class for fetching trending content from various sources"""
    
    def __init__(self):
        self.news_api_key = os.getenv("NEWS_API_KEY")  # Optional: for NewsAPI
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_trending_topics(self, limit: int = 5) -> List[str]:
        """
        Get trending topics from various sources
        
        Args:
            limit: Number of trending topics to return
            
        Returns:
            List of trending topic strings
        """
        try:
            trending_topics = []
            
            # Method 1: Use NewsAPI if available
            if self.news_api_key:
                news_topics = self._get_trending_from_newsapi(limit)
                trending_topics.extend(news_topics)
            
            # Method 2: Use Reddit API for trending topics
            reddit_topics = self._get_trending_from_reddit(limit)
            trending_topics.extend(reddit_topics)
            
            # Method 3: Use Twitter/X trending (via web scraping)
            twitter_topics = self._get_trending_from_twitter(limit)
            trending_topics.extend(twitter_topics)
            
            # Remove duplicates and return unique topics
            unique_topics = list(dict.fromkeys(trending_topics))[:limit]
            
            logger.info(f"Found {len(unique_topics)} trending topics: {unique_topics}")
            return unique_topics
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {str(e)}")
            # Fallback to hardcoded trending topics
            return self._get_fallback_trending_topics(limit)
    
    def get_trending_articles(self, topics: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get trending articles based on topics
        
        Args:
            topics: List of trending topics
            limit: Number of articles to return
            
        Returns:
            List of article objects with id, title, abstract
        """
        try:
            trending_articles = []
            
            # Method 1: Use NewsAPI if available
            if self.news_api_key:
                news_articles = self._get_articles_from_newsapi(topics, limit)
                trending_articles.extend(news_articles)
            
            # Method 2: Use Reddit for trending articles
            reddit_articles = self._get_articles_from_reddit(topics, limit)
            trending_articles.extend(reddit_articles)
            
            # Remove duplicates and limit results
            unique_articles = []
            seen_ids = set()
            
            for article in trending_articles:
                if article.get("id") not in seen_ids:
                    unique_articles.append(article)
                    seen_ids.add(article.get("id"))
                    if len(unique_articles) >= limit:
                        break
            
            logger.info(f"Found {len(unique_articles)} trending articles")
            return unique_articles
            
        except Exception as e:
            logger.error(f"Error getting trending articles: {str(e)}")
            # Fallback to generated trending articles
            return self._get_fallback_trending_articles(topics, limit)
    
    def _get_trending_from_newsapi(self, limit: int) -> List[str]:
        """Get trending topics from NewsAPI"""
        try:
            if not self.news_api_key:
                return []
                
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "apiKey": self.news_api_key,
                "country": "us",
                "pageSize": 20
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            # Extract trending topics from article titles
            topics = []
            for article in articles[:limit]:
                title = article.get("title", "")
                if title:
                    # Extract key words from title
                    words = title.lower().split()
                    # Filter out common words and get meaningful terms
                    meaningful_words = [w for w in words if len(w) > 3 and w not in ["the", "and", "for", "with", "this", "that"]]
                    if meaningful_words:
                        topics.append("-".join(meaningful_words[:2]))  # Join first 2 meaningful words
            
            return topics[:limit]
            
        except Exception as e:
            logger.warning(f"NewsAPI trending failed: {str(e)}")
            return []
    
    def _get_trending_from_reddit(self, limit: int) -> List[str]:
        """Get trending topics from Reddit"""
        try:
            # Use Reddit's public API (no auth required for basic trending)
            url = "https://www.reddit.com/r/all/hot.json"
            params = {"limit": 25}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            topics = []
            for post in posts[:limit]:
                title = post.get("data", {}).get("title", "")
                if title:
                    # Extract trending topics from Reddit post titles
                    words = title.lower().split()
                    meaningful_words = [w for w in words if len(w) > 3 and w not in ["the", "and", "for", "with", "this", "that"]]
                    if meaningful_words:
                        topics.append("-".join(meaningful_words[:2]))
            
            return topics[:limit]
            
        except Exception as e:
            logger.warning(f"Reddit trending failed: {str(e)}")
            return []
    
    def _get_trending_from_twitter(self, limit: int) -> List[str]:
        """Get trending topics from Twitter (simplified approach)"""
        try:
            # This is a simplified approach - in reality, you'd need Twitter API
            # For now, return some common trending topics
            current_trending = [
                "ai-advancements",
                "climate-action",
                "tech-innovation", 
                "global-economy",
                "space-exploration"
            ]
            
            return current_trending[:limit]
            
        except Exception as e:
            logger.warning(f"Twitter trending failed: {str(e)}")
            return []
    
    def _get_articles_from_newsapi(self, topics: List[str], limit: int) -> List[Dict[str, Any]]:
        """Get articles from NewsAPI based on topics"""
        try:
            if not self.news_api_key or not topics:
                return []
                
            articles = []
            for topic in topics[:limit]:
                url = "https://newsapi.org/v2/everything"
                params = {
                    "apiKey": self.news_api_key,
                    "q": topic.replace("-", " "),
                    "sortBy": "publishedAt",
                    "pageSize": 1
                }
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                news_articles = data.get("articles", [])
                
                for article in news_articles:
                    articles.append({
                        "id": f"newsapi-{topic}-{len(articles)}",
                        "title": article.get("title", "")[:100],
                        "abstract": article.get("description", "")[:200] or "Latest news on trending topics",
                        "source": "newsapi",
                        "published_at": article.get("publishedAt", "")
                    })
                    
                    if len(articles) >= limit:
                        break
            
            return articles[:limit]
            
        except Exception as e:
            logger.warning(f"NewsAPI articles failed: {str(e)}")
            return []
    
    def _get_articles_from_reddit(self, topics: List[str], limit: int) -> List[Dict[str, Any]]:
        """Get articles from Reddit based on topics"""
        try:
            articles = []
            for topic in topics[:limit]:
                # Search Reddit for posts about the topic
                subreddits = ["all", "news", "worldnews", "technology"]
                
                for subreddit in subreddits:
                    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                    params = {"limit": 10}
                    
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    for post in posts:
                        title = post.get("data", {}).get("title", "")
                        if topic.replace("-", " ") in title.lower():
                            articles.append({
                                "id": f"reddit-{topic}-{len(articles)}",
                                "title": title[:100],
                                "abstract": post.get("data", {}).get("selftext", "")[:200] or "Popular discussion on trending topics",
                                "source": "reddit",
                                "score": post.get("data", {}).get("score", 0)
                            })
                            
                            if len(articles) >= limit:
                                break
                    
                    if len(articles) >= limit:
                        break
            
            return articles[:limit]
            
        except Exception as e:
            logger.warning(f"Reddit articles failed: {str(e)}")
            return []
    
    def _get_fallback_trending_topics(self, limit: int) -> List[str]:
        """Fallback trending topics when APIs fail"""
        return [
            "ai-breakthrough",
            "climate-solutions", 
            "tech-innovation",
            "global-events",
            "space-news",
            "health-advances",
            "economic-trends",
            "sports-highlights"
        ][:limit]
    
    def _get_fallback_trending_articles(self, topics: List[str], limit: int) -> List[Dict[str, Any]]:
        """Fallback trending articles when APIs fail"""
        articles = []
        for i, topic in enumerate(topics[:limit]):
            articles.append({
                "id": f"trending-{topic}-{i+1}",
                "title": f"Latest Updates on {topic.replace('-', ' ').title()}",
                "abstract": f"Current trending content and discussions about {topic.replace('-', ' ')} based on recent global events and popular interest",
                "source": "fallback",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return articles
