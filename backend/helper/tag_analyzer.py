"""
Tag analyzer module for analyzing user preferences and generating tag recommendations
"""
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter
import math
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TagAnalyzer:
    """Analyzer for user tag preferences and recommendations"""
    
    def __init__(self):
        """Initialize the tag analyzer"""
        self.logger = logger
    
    def analyze_user_preferences(self, user_data: Dict[str, Any], 
                                user_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze user's tag preferences from their interaction history
        
        Args:
            user_data: User document from CosmosDB
            user_articles: Articles the user has interacted with
            
        Returns:
            Analysis results including tag preferences and patterns
        """
        try:
            analysis = {
                "user_id": user_data.get("id"),
                "tag_preferences": self._extract_tag_preferences(user_data, user_articles),
                "interaction_patterns": self._analyze_interaction_patterns(user_data),
                "content_preferences": self._analyze_content_preferences(user_articles),
                "recommendation_context": self._build_recommendation_context(user_data, user_articles)
            }
            
            self.logger.info(f"Completed preference analysis for user {analysis['user_id']}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing user preferences: {str(e)}")
            return {}
    
    def _extract_tag_preferences(self, user_data: Dict[str, Any], 
                                user_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract tag preferences from user's liked, bookmarked, and disliked articles
        
        Args:
            user_data: User document
            user_articles: Articles the user has interacted with
            
        Returns:
            Tag preference analysis
        """
        try:
            # Get user's interaction lists
            liked_articles = user_data.get("liked_articles", [])
            bookmarked_articles = user_data.get("bookmarked_articles", [])
            disliked_articles = user_data.get("disliked_articles", [])
            
            # Count tags from different interaction types
            liked_tags = Counter()
            bookmarked_tags = Counter()
            disliked_tags = Counter()
            
            # Analyze liked articles
            for article in user_articles:
                article_id = article.get("id")
                article_tags = article.get("tags", [])
                
                if article_id in liked_articles:
                    liked_tags.update(article_tags)
                elif article_id in bookmarked_articles:
                    bookmarked_tags.update(article_tags)
                elif article_id in disliked_articles:
                    disliked_tags.update(article_tags)
            
            # Calculate weighted tag preferences
            tag_scores = {}
            all_tags = set(liked_tags.keys()) | set(bookmarked_tags.keys()) | set(disliked_tags.keys())
            
            for tag in all_tags:
                # Weight: liked=3, bookmarked=2, disliked=-2
                score = (liked_tags[tag] * 3 + 
                        bookmarked_tags[tag] * 2 - 
                        disliked_tags[tag] * 2)
                
                if score > 0:
                    tag_scores[tag] = score
            
            # Normalize scores to 1-5 range
            if tag_scores:
                max_score = max(tag_scores.values())
                min_score = min(tag_scores.values())
                
                if max_score > min_score:
                    for tag in tag_scores:
                        normalized_score = 1 + (tag_scores[tag] - min_score) / (max_score - min_score) * 4
                        tag_scores[tag] = round(normalized_score, 2)
            
            return {
                "tag_scores": tag_scores,
                "liked_tags": dict(liked_tags),
                "bookmarked_tags": dict(bookmarked_tags),
                "disliked_tags": dict(disliked_tags),
                "total_interactions": len(liked_articles) + len(bookmarked_articles) + len(disliked_articles)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting tag preferences: {str(e)}")
            return {}
    
    def _analyze_interaction_patterns(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user's interaction patterns and behavior
        
        Args:
            user_data: User document
            
        Returns:
            Interaction pattern analysis
        """
        try:
            liked_count = len(user_data.get("liked_articles", []))
            bookmarked_count = len(user_data.get("bookmarked_articles", []))
            disliked_count = len(user_data.get("disliked_articles", []))
            
            total_interactions = liked_count + bookmarked_count + disliked_count
            
            patterns = {
                "total_interactions": total_interactions,
                "liked_ratio": liked_count / total_interactions if total_interactions > 0 else 0,
                "bookmarked_ratio": bookmarked_count / total_interactions if total_interactions > 0 else 0,
                "disliked_ratio": disliked_count / total_interactions if total_interactions > 0 else 0,
                "engagement_level": self._calculate_engagement_level(total_interactions),
                "diversity_score": self._calculate_diversity_score(user_data)
            }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing interaction patterns: {str(e)}")
            return {}
    
    def _analyze_content_preferences(self, user_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze content preferences from user's articles
        
        Args:
            user_articles: Articles the user has interacted with
            
        Returns:
            Content preference analysis
        """
        try:
            if not user_articles:
                return {}
            
            # Analyze article characteristics
            total_views = sum(article.get("views", 0) for article in user_articles)
            avg_views = total_views / len(user_articles) if user_articles else 0
            
            # Analyze tags diversity
            all_tags = []
            for article in user_articles:
                all_tags.extend(article.get("tags", []))
            
            tag_diversity = len(set(all_tags)) / len(all_tags) if all_tags else 0
            
            # Analyze content themes (based on tags)
            tag_themes = self._identify_content_themes(all_tags)
            
            return {
                "avg_views": round(avg_views, 2),
                "tag_diversity": round(tag_diversity, 3),
                "content_themes": tag_themes,
                "total_articles": len(user_articles)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing content preferences: {str(e)}")
            return {}
    
    def _build_recommendation_context(self, user_data: Dict[str, Any], 
                                    user_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build context for recommendation generation
        
        Args:
            user_data: User document
            user_articles: Articles the user has interacted with
            
        Returns:
            Recommendation context
        """
        try:
            # Get user's current recommendation data
            current_tags_rec = user_data.get("tags_recommendation", [])
            last_updated = user_data.get("recommendations_updated_at")
            
            # Build context
            context = {
                "has_existing_recommendations": len(current_tags_rec) > 0,
                "last_updated": last_updated,
                "user_activity_level": self._assess_activity_level(user_data),
                "preference_stability": self._assess_preference_stability(current_tags_rec, user_articles),
                "recommendation_freshness": self._assess_recommendation_freshness(last_updated)
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error building recommendation context: {str(e)}")
            return {}
    
    def _calculate_engagement_level(self, total_interactions: int) -> str:
        """
        Calculate user engagement level based on total interactions
        
        Args:
            total_interactions: Total number of user interactions
            
        Returns:
            Engagement level string
        """
        if total_interactions >= 100:
            return "high"
        elif total_interactions >= 50:
            return "medium"
        elif total_interactions >= 10:
            return "low"
        else:
            return "minimal"
    
    def _calculate_diversity_score(self, user_data: Dict[str, Any]) -> float:
        """
        Calculate diversity score based on user's interactions
        
        Args:
            user_data: User document
            
        Returns:
            Diversity score (0-1)
        """
        try:
            liked = set(user_data.get("liked_articles", []))
            bookmarked = set(user_data.get("bookmarked_articles", []))
            disliked = set(user_data.get("disliked_articles", []))
            
            # Calculate Jaccard similarity between different interaction types
            total_unique = len(liked | bookmarked | disliked)
            if total_unique == 0:
                return 0.0
            
            # Higher diversity when interactions don't overlap much
            overlap = len(liked & bookmarked) + len(liked & disliked) + len(bookmarked & disliked)
            diversity = 1 - (overlap / total_unique)
            
            return round(diversity, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating diversity score: {str(e)}")
            return 0.0
    
    def _identify_content_themes(self, tags: List[str]) -> Dict[str, int]:
        """
        Identify content themes from tags
        
        Args:
            tags: List of tags
            
        Returns:
            Theme frequency dictionary
        """
        try:
            # Group related tags into themes
            themes = {
                "technology": ["ai", "machine-learning", "deep-learning", "nlp", "computer-vision", "data-science"],
                "programming": ["python", "javascript", "java", "react", "nodejs", "web-development"],
                "business": ["startup", "entrepreneurship", "marketing", "product-management", "strategy"],
                "design": ["ui", "ux", "design", "frontend", "user-experience"],
                "data": ["analytics", "big-data", "database", "sql", "statistics"],
                "security": ["cybersecurity", "privacy", "encryption", "security"],
                "mobile": ["ios", "android", "mobile", "react-native", "flutter"],
                "cloud": ["aws", "azure", "gcp", "cloud", "devops", "kubernetes"]
            }
            
            theme_counts = Counter()
            for tag in tags:
                for theme, theme_tags in themes.items():
                    if tag.lower() in [t.lower() for t in theme_tags]:
                        theme_counts[theme] += 1
            
            return dict(theme_counts)
            
        except Exception as e:
            self.logger.error(f"Error identifying content themes: {str(e)}")
            return {}
    
    def _assess_activity_level(self, user_data: Dict[str, Any]) -> str:
        """
        Assess user's activity level
        
        Args:
            user_data: User document
            
        Returns:
            Activity level string
        """
        try:
            total_interactions = (len(user_data.get("liked_articles", [])) + 
                                len(user_data.get("bookmarked_articles", [])) + 
                                len(user_data.get("disliked_articles", [])))
            
            if total_interactions >= 50:
                return "high"
            elif total_interactions >= 20:
                return "medium"
            elif total_interactions >= 5:
                return "low"
            else:
                return "minimal"
                
        except Exception as e:
            self.logger.error(f"Error assessing activity level: {str(e)}")
            return "minimal"
    
    def _assess_preference_stability(self, current_recommendations: List[Dict[str, Any]], 
                                   user_articles: List[Dict[str, Any]]) -> str:
        """
        Assess stability of user preferences
        
        Args:
            current_recommendations: Current tag recommendations
            user_articles: User's articles
            
        Returns:
            Stability level string
        """
        try:
            if not current_recommendations or not user_articles:
                return "unknown"
            
            # Check if user's recent interactions align with current recommendations
            current_tags = {rec.get("tag") for rec in current_recommendations}
            recent_tags = set()
            
            for article in user_articles[-10:]:  # Check last 10 articles
                recent_tags.update(article.get("tags", []))
            
            if not recent_tags:
                return "unknown"
            
            # Calculate alignment
            alignment = len(current_tags & recent_tags) / len(recent_tags)
            
            if alignment >= 0.7:
                return "stable"
            elif alignment >= 0.4:
                return "moderate"
            else:
                return "unstable"
                
        except Exception as e:
            self.logger.error(f"Error assessing preference stability: {str(e)}")
            return "unknown"
    
    def _assess_recommendation_freshness(self, last_updated: Optional[str]) -> str:
        """
        Assess freshness of current recommendations
        
        Args:
            last_updated: Last update timestamp
            
        Returns:
            Freshness level string
        """
        try:
            if not last_updated:
                return "never"
            
            from datetime import datetime, timezone
            last_update = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            days_diff = (now - last_update).days
            
            if days_diff <= 7:
                return "fresh"
            elif days_diff <= 30:
                return "stale"
            else:
                return "very_stale"
                
        except Exception as e:
            self.logger.error(f"Error assessing recommendation freshness: {str(e)}")
            return "unknown"
    
    def generate_tag_suggestions(self, analysis: Dict[str, Any], 
                               all_available_tags: List[str]) -> List[str]:
        """
        Generate tag suggestions based on analysis
        
        Args:
            analysis: User preference analysis
            all_available_tags: All available tags in the system
            
        Returns:
            List of suggested tags
        """
        try:
            suggestions = set()
            
            # Get tags from current preferences
            tag_preferences = analysis.get("tag_preferences", {})
            current_tags = list(tag_preferences.get("tag_scores", {}).keys())
            
            # Add current high-scoring tags
            for tag, score in tag_preferences.get("tag_scores", {}).items():
                if score >= 3.0:
                    suggestions.add(tag)
            
            # Add related tags based on themes
            content_preferences = analysis.get("content_preferences", {})
            themes = content_preferences.get("content_themes", {})
            
            theme_tag_mapping = {
                "technology": ["ai", "machine-learning", "deep-learning", "nlp", "data-science"],
                "programming": ["python", "javascript", "web-development", "react", "nodejs"],
                "business": ["startup", "entrepreneurship", "product-management"],
                "design": ["ui", "ux", "frontend", "user-experience"],
                "data": ["analytics", "big-data", "database", "sql"],
                "security": ["cybersecurity", "privacy", "encryption"],
                "mobile": ["ios", "android", "mobile-development"],
                "cloud": ["aws", "azure", "cloud-computing", "devops"]
            }
            
            for theme, count in themes.items():
                if count > 0 and theme in theme_tag_mapping:
                    suggestions.update(theme_tag_mapping[theme])
            
            # Filter to only available tags
            suggestions = [tag for tag in suggestions if tag in all_available_tags]
            
            # Limit to reasonable number
            return suggestions[:20]
            
        except Exception as e:
            self.logger.error(f"Error generating tag suggestions: {str(e)}")
            return []
