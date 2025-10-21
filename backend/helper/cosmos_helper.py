"""
CosmosDB helper module for database operations
"""
import os
import json
import time
from typing import Dict, List, Optional, Any
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosResourceExistsError
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CosmosHelper:
    """Helper class for CosmosDB operations"""
    
    def __init__(self):
        """Initialize CosmosDB connection"""
        self.endpoint = os.getenv("COSMOS_ENDPOINT")
        self.key = os.getenv("COSMOS_KEY")
        self.database_name = os.getenv("DATABASE_NAME", "intern-htn")
        self.articles_container_name = os.getenv("ARTICLES_CONTAINER", "articles")
        self.users_container_name = os.getenv("USER_CONTAINER", "users")
        
        # Simple in-memory cache for articles (TTL: 5 minutes)
        self._article_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        if not self.endpoint or not self.key:
            raise ValueError("COSMOS_ENDPOINT and COSMOS_KEY environment variables are required")
        
        try:
            self.client = CosmosClient(self.endpoint, self.key)
            self.database = self.client.get_database_client(self.database_name)
            self.articles_container = self.database.get_container_client(self.articles_container_name)
            self.users_container = self.database.get_container_client(self.users_container_name)
            logger.info("Successfully connected to CosmosDB")
        except Exception as e:
            logger.error(f"Failed to connect to CosmosDB: {str(e)}")
            raise
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID
        
        Args:
            user_id: User ID to retrieve
            
        Returns:
            User document or None if not found
        """
        try:
            user = self.users_container.read_item(item=user_id, partition_key=user_id)
            logger.info(f"Retrieved user {user_id}")
            return user
        except CosmosResourceNotFoundError:
            logger.warning(f"User {user_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            raise
    
    def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get articles by their IDs using batch query for better performance
        
        Args:
            article_ids: List of article IDs to retrieve
            
        Returns:
            List of article documents
        """
        if not article_ids:
            return []
        
        try:
            # Use batch query instead of individual read_item calls
            # Create parameterized query for better performance - only select needed fields
            article_ids_str = "', '".join(article_ids)
            query = f"SELECT c.id, c.title, c.abstract, c.tags, c.status, c.is_active, c.created_at FROM c WHERE c.id IN ('{article_ids_str}')"
            
            articles = list(self.articles_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            logger.info(f"Retrieved {len(articles)} articles out of {len(article_ids)} requested using batch query")
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles by IDs: {str(e)}")
            # Fallback to individual queries if batch query fails
            return self._get_articles_by_ids_fallback(article_ids)
    
    def _get_articles_by_ids_fallback(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fallback method using individual read_item calls
        
        Args:
            article_ids: List of article IDs to retrieve
            
        Returns:
            List of article documents
        """
        articles = []
        for article_id in article_ids:
            try:
                article = self.articles_container.read_item(item=article_id, partition_key=article_id)
                articles.append(article)
            except CosmosResourceNotFoundError:
                logger.warning(f"Article {article_id} not found")
                continue
            except Exception as e:
                logger.error(f"Error retrieving article {article_id}: {str(e)}")
                continue
        
        logger.info(f"Retrieved {len(articles)} articles out of {len(article_ids)} requested using fallback method")
        return articles
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry.get('timestamp', 0) < self._cache_ttl
    
    def _get_from_cache(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """Get articles from cache if available and valid"""
        cached_articles = []
        missing_ids = []
        
        for article_id in article_ids:
            if article_id in self._article_cache:
                cache_entry = self._article_cache[article_id]
                if self._is_cache_valid(cache_entry):
                    cached_articles.append(cache_entry['article'])
                else:
                    # Remove expired cache entry
                    del self._article_cache[article_id]
                    missing_ids.append(article_id)
            else:
                missing_ids.append(article_id)
        
        return cached_articles, missing_ids
    
    def _update_cache(self, articles: List[Dict[str, Any]]):
        """Update cache with new articles"""
        current_time = time.time()
        for article in articles:
            article_id = article.get('id')
            if article_id:
                self._article_cache[article_id] = {
                    'article': article,
                    'timestamp': current_time
                }
    
    def get_articles_by_ids_optimized(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get articles by IDs with caching for better performance
        
        Args:
            article_ids: List of article IDs to retrieve
            
        Returns:
            List of article documents
        """
        if not article_ids:
            return []
        
        try:
            # Check cache first
            cached_articles, missing_ids = self._get_from_cache(article_ids)
            
            if not missing_ids:
                logger.info(f"Retrieved {len(cached_articles)} articles from cache")
                return cached_articles
            
            # Fetch missing articles from database
            if missing_ids:
                # Use batch query for missing articles - only select needed fields
                missing_ids_str = "', '".join(missing_ids)
                query = f"SELECT c.id, c.title, c.abstract, c.tags, c.status, c.is_active, c.created_at FROM c WHERE c.id IN ('{missing_ids_str}')"
                
                db_articles = list(self.articles_container.query_items(
                    query=query,
                    enable_cross_partition_query=True
                ))
                
                # Update cache with new articles
                self._update_cache(db_articles)
                
                # Combine cached and database results
                all_articles = cached_articles + db_articles
                
                logger.info(f"Retrieved {len(all_articles)} articles total: {len(cached_articles)} from cache, {len(db_articles)} from database")
                return all_articles
            
        except Exception as e:
            logger.error(f"Error in optimized article retrieval: {str(e)}")
            # Fallback to non-cached method
            return self.get_articles_by_ids(article_ids)
        
        return cached_articles
    
    def clear_article_cache(self):
        """Clear the article cache"""
        self._article_cache.clear()
        logger.info("Article cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_entries = sum(1 for entry in self._article_cache.values() 
                           if current_time - entry.get('timestamp', 0) < self._cache_ttl)
        
        return {
            "total_entries": len(self._article_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._article_cache) - valid_entries,
            "cache_ttl": self._cache_ttl
        }

    def get_candidate_articles(self, exclude_ids: Optional[List[str]] = None, limit: int = 300) -> List[Dict[str, Any]]:
        """
        Get a pool of candidate articles for LLM-only selection.

        Args:
            exclude_ids: Article IDs to exclude (e.g., already interacted)
            limit: Maximum number of articles to return

        Returns:
            List of article documents containing at least id, title, abstract, tags
        """
        try:
            exclude_ids = set(exclude_ids or [])
            # Prefer active, published articles first
            query = f"SELECT TOP {limit} c.id, c.title, c.abstract, c.tags, c.status, c.is_active FROM c WHERE c.is_active = true AND c.status = 'published'"
            items = list(self.articles_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))

            # Fallback if none found with filters
            if not items:
                query_fallback = f"SELECT TOP {limit} c.id, c.title, c.abstract, c.tags FROM c"
                items = list(self.articles_container.query_items(
                    query=query_fallback,
                    enable_cross_partition_query=True
                ))

            candidates: List[Dict[str, Any]] = []
            for it in items:
                if it.get("id") in exclude_ids:
                    continue
                # Ensure required fields exist
                it.setdefault("abstract", "")
                it.setdefault("tags", [])
                candidates.append(it)

            return candidates
        except Exception as e:
            logger.error(f"Error retrieving candidate articles: {str(e)}")
            return []
    
    def update_user_recommendations(self, user_id: str, tags_recommendation: List[Dict[str, Any]], 
                                  articles_recommendation: List[Dict[str, Any]], 
                                  id_articles_for_recommendation: List[str]) -> bool:
        """
        Update user's recommendation data
        
        Args:
            user_id: User ID to update
            tags_recommendation: List of tag recommendations with scores
            articles_recommendation: List of article recommendations with scores
            id_articles_for_recommendation: List of article IDs used for recommendation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current user document
            user = self.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found for update")
                return False
            
            # Update recommendation fields
            from datetime import datetime
            user["tags_recommendation"] = tags_recommendation
            user["articles_recommendation"] = articles_recommendation
            user["id_articles_for_recommendation"] = id_articles_for_recommendation
            user["recommendations_updated_at"] = datetime.utcnow().isoformat()
            user["time_stamp_recommend"] = int(datetime.utcnow().timestamp())
            
            # Replace the document
            self.users_container.replace_item(item=user_id, body=user)
            logger.info(f"Successfully updated recommendations for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {user_id} recommendations: {str(e)}")
            return False
    
    def get_all_articles_tags(self) -> List[str]:
        """
        Get all unique tags from all articles
        
        Returns:
            List of unique tags
        """
        try:
            # Query all articles
            query = "SELECT DISTINCT VALUE tag FROM c JOIN tag IN c.tags"
            articles = list(self.articles_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            # Flatten and get unique tags
            all_tags = set()
            for article in articles:
                if isinstance(article, str):
                    all_tags.add(article)
            
            unique_tags = list(all_tags)
            logger.info(f"Found {len(unique_tags)} unique tags across all articles")
            return unique_tags
            
        except Exception as e:
            logger.error(f"Error retrieving all article tags: {str(e)}")
            return []
    
    def get_articles_by_tags(self, tags: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get articles that contain any of the specified tags
        
        Args:
            tags: List of tags to search for
            limit: Maximum number of articles to return
            
        Returns:
            List of matching articles
        """
        try:
            if not tags:
                return []
            
            # Create query for articles containing any of the specified tags
            tag_conditions = " OR ".join([f"ARRAY_CONTAINS(c.tags, '{tag}')" for tag in tags])
            query = f"SELECT TOP {limit} * FROM c WHERE {tag_conditions}"
            
            articles = list(self.articles_container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            
            logger.info(f"Found {len(articles)} articles matching tags: {tags}")
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles by tags: {str(e)}")
            return []
    
    def benchmark_article_retrieval(self, article_ids: List[str]) -> Dict[str, Any]:
        """
        Benchmark different article retrieval methods for performance comparison
        
        Args:
            article_ids: List of article IDs to test with
            
        Returns:
            Dictionary with performance metrics
        """
        results = {}
        
        # Test original method (individual queries)
        start_time = time.time()
        original_articles = self._get_articles_by_ids_fallback(article_ids)
        original_time = time.time() - start_time
        results["original_method"] = {
            "time": original_time,
            "articles_retrieved": len(original_articles)
        }
        
        # Test batch query method
        start_time = time.time()
        batch_articles = self.get_articles_by_ids(article_ids)
        batch_time = time.time() - start_time
        results["batch_method"] = {
            "time": batch_time,
            "articles_retrieved": len(batch_articles)
        }
        
        # Test optimized method with cache
        start_time = time.time()
        optimized_articles = self.get_articles_by_ids_optimized(article_ids)
        optimized_time = time.time() - start_time
        results["optimized_method"] = {
            "time": optimized_time,
            "articles_retrieved": len(optimized_articles)
        }
        
        # Calculate speedup
        if original_time > 0:
            results["speedup_batch_vs_original"] = original_time / batch_time
            results["speedup_optimized_vs_original"] = original_time / optimized_time
        
        logger.info(f"Benchmark results: {results}")
        return results
