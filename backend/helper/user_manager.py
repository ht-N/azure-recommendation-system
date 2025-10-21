"""
User management helper module
"""
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from .cosmos_helper import CosmosHelper

logger = logging.getLogger(__name__)


class UserManager:
    """Helper class for user-related operations"""
    
    def __init__(self, cosmos_helper: CosmosHelper):
        """Initialize with CosmosDB helper"""
        self.cosmos_helper = cosmos_helper
        self.logger = logger
    
    def get_all_user_ids(self, only_active: bool = False, limit: Optional[int] = None) -> List[str]:
        """
        Retrieve all user IDs from Cosmos DB.
        
        Args:
            only_active: if True, filter users by is_active = true when field exists
            limit: optional cap on number of users returned
            
        Returns:
            List of user IDs
        """
        try:
            # Build query
            if only_active:
                query = "SELECT c.id FROM c WHERE IS_DEFINED(c.is_active) AND c.is_active = true"
            else:
                query = "SELECT c.id FROM c"

            items = list(self.cosmos_helper.users_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))

            ids: List[str] = []
            for it in items:
                # item shape can be {"id": "..."} or {"$1": "..."} depending on query
                if isinstance(it, dict):
                    if "id" in it:
                        ids.append(it["id"])
                    else:
                        # fallback for VALUE queries if used later
                        for v in it.values():
                            if isinstance(v, str):
                                ids.append(v)
            
            if limit is not None:
                ids = ids[:limit]
            
            self.logger.info(f"Retrieved {len(ids)} user IDs")
            return ids
            
        except Exception as e:
            self.logger.error(f"Error retrieving user ids: {str(e)}")
            return []
    
    def get_user_articles_with_interactions(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get all articles the user has interacted with, including interaction types
        
        Args:
            user_data: User document
            
        Returns:
            List of user's articles with interaction types
        """
        start_time = time.time()
        try:
            # Get all article IDs from user's interactions
            liked_articles = user_data.get("liked_articles", [])
            bookmarked_articles = user_data.get("bookmarked_articles", [])
            disliked_articles = user_data.get("disliked_articles", [])
            
            # Combine all article IDs
            all_article_ids = list(set(liked_articles + bookmarked_articles + disliked_articles))
            
            if not all_article_ids:
                self.logger.info(f"No articles found for user {user_data.get('id')}")
                return []
            
            self.logger.info(f"Processing {len(all_article_ids)} unique articles for user {user_data.get('id')}")
            
            # Fetch articles from database using optimized method with caching
            articles = self.cosmos_helper.get_articles_by_ids_optimized(all_article_ids)
            
            # Add interaction type to each article
            for article in articles:
                article_id = article.get("id")
                interaction_types = []
                
                if article_id in liked_articles:
                    interaction_types.append("liked")
                if article_id in bookmarked_articles:
                    interaction_types.append("bookmarked")
                if article_id in disliked_articles:
                    interaction_types.append("disliked")
                
                article["interaction_types"] = interaction_types
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Retrieved {len(articles)} articles for user {user_data.get('id')} in {elapsed_time:.2f}s")
            return articles
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error getting user articles after {elapsed_time:.2f}s: {str(e)}")
            return []
    
    def prepare_user_article_ids(self, user_data: Dict[str, Any], limit: int = 50) -> List[str]:
        """
        Prepare list of article IDs used for recommendation context
        
        Args:
            user_data: User document
            limit: Maximum number of article IDs to return
            
        Returns:
            List of article IDs
        """
        try:
            # Combine all article IDs from user's interactions
            liked = user_data.get("liked_articles", [])
            bookmarked = user_data.get("bookmarked_articles", [])
            disliked = user_data.get("disliked_articles", [])
            
            # Combine and remove duplicates
            all_ids = list(set(liked + bookmarked + disliked))
            
            return all_ids[:limit]
            
        except Exception as e:
            self.logger.error(f"Error preparing article IDs: {str(e)}")
            return []
    
    def should_skip_update(self, user_data: Dict[str, Any], hours_threshold: int = 24) -> bool:
        """
        Check if recommendation update should be skipped based on last update time
        
        Args:
            user_data: User document
            hours_threshold: Hours threshold to skip update
            
        Returns:
            True if update should be skipped
        """
        try:
            last_updated = user_data.get("recommendations_updated_at")
            if not last_updated:
                return False
            
            # Parse last update time
            last_update = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            now = datetime.utcnow()
            
            # Skip if updated within threshold hours
            hours_diff = (now - last_update).total_seconds() / 3600
            return hours_diff < hours_threshold
            
        except Exception as e:
            self.logger.warning(f"Error checking update time: {str(e)}")
            return False
    
    def update_user_recommendations(self, user_id: str, 
                                  tags_recommendation: List[Dict[str, Any]], 
                                  articles_recommendation: List[Dict[str, Any]], 
                                  id_articles_for_recommendation: List[str]) -> bool:
        """
        Update user's recommendation data in CosmosDB
        
        Args:
            user_id: User ID to update
            tags_recommendation: List of tag recommendations with scores
            articles_recommendation: List of article recommendations with scores
            id_articles_for_recommendation: List of article IDs used for recommendation
            
        Returns:
            True if successful, False otherwise
        """
        return self.cosmos_helper.update_user_recommendations(
            user_id=user_id,
            tags_recommendation=tags_recommendation,
            articles_recommendation=articles_recommendation,
            id_articles_for_recommendation=id_articles_for_recommendation
        )
