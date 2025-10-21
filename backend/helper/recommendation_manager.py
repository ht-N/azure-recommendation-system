"""
Recommendation management helper module
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from .cosmos_helper import CosmosHelper
from .azure_openai_helper import AzureOpenAIHelper
from .user_manager import UserManager

logger = logging.getLogger(__name__)


class RecommendationManager:
    """Helper class for recommendation generation and management"""
    
    def __init__(self, cosmos_helper: CosmosHelper, openai_helper: AzureOpenAIHelper, user_manager: UserManager):
        """Initialize with required helpers"""
        self.cosmos_helper = cosmos_helper
        self.openai_helper = openai_helper
        self.user_manager = user_manager
        self.logger = logger
    
    def generate_recommendations_for_user(self, user_id: str, 
                                        force_update: bool = False,
                                        tag_count: int = 15,
                                        tag_wildcard: int = 5,
                                        article_count: int = 15,
                                        article_wildcard: int = 5,
                                        candidate_limit: int = 400) -> Dict[str, Any]:
        """
        Generate tag and article recommendations for a specific user
        
        Args:
            user_id: ID of the user to generate recommendations for
            force_update: Whether to force update even if recommendations are recent
            tag_count: Number of primary tag recommendations
            tag_wildcard: Number of wildcard tag recommendations
            article_count: Number of primary article recommendations
            article_wildcard: Number of wildcard article recommendations
            candidate_limit: Maximum number of candidate articles to consider
            
        Returns:
            Dictionary containing recommendation results and status
        """
        try:
            self.logger.info(f"Starting recommendation generation for user {user_id}")
            
            # Step 1: Get user data
            user_data = self.cosmos_helper.get_user_by_id(user_id)
            if not user_data:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "user_id": user_id
                }
            
            # Step 2: Check if update is needed
            if not force_update and self.user_manager.should_skip_update(user_data):
                self.logger.info(f"Skipping update for user {user_id} - recommendations are recent")
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "Recommendations are recent",
                    "user_id": user_id,
                    "existing_recommendations": user_data.get("tags_recommendation", [])
                }
            
            # Step 3: Get user's articles
            user_articles = self.user_manager.get_user_articles_with_interactions(user_data)
            if not user_articles:
                self.logger.warning(f"No articles found for user {user_id}")
                return {
                    "success": False,
                    "error": "No articles found for user",
                    "user_id": user_id
                }
            
            # Step 4: Prepare candidate articles for LLM-only selection
            id_articles_for_recommendation = self.user_manager.prepare_user_article_ids(user_data)
            candidates = self.cosmos_helper.get_candidate_articles(
                exclude_ids=id_articles_for_recommendation,
                limit=candidate_limit
            )

            # Step 5: LLM-only generation for both tags and articles
            llm_out = self.openai_helper.generate_llm_only_recommendations(
                user_articles=user_articles,
                candidate_articles=candidates,
                tag_count=tag_count,
                tag_wildcard=tag_wildcard,
                article_count=article_count,
                article_wildcard=article_wildcard
            )

            # Step 6: Process and format recommendations
            recommendations = self._process_llm_output(llm_out, candidates)
            
            # Step 7: Update user recommendations in database
            success = self.user_manager.update_user_recommendations(
                user_id=user_id,
                tags_recommendation=recommendations["tags"],
                articles_recommendation=recommendations["articles"],
                id_articles_for_recommendation=id_articles_for_recommendation
            )
            
            if success:
                self.logger.info(f"Successfully generated recommendations for user {user_id}")
                return {
                    "success": True,
                    "user_id": user_id,
                    "tags_recommendation": recommendations["tags"],
                    "articles_recommendation": recommendations["articles"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update user recommendations in database",
                    "user_id": user_id
                }
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    def generate_recommendations_batch(self, user_ids: List[str], 
                                     force_update: bool = False,
                                     **kwargs) -> Dict[str, Any]:
        """
        Generate recommendations for multiple users
        
        Args:
            user_ids: List of user IDs to process
            force_update: Whether to force update even if recommendations are recent
            **kwargs: Additional parameters for generate_recommendations_for_user
            
        Returns:
            Batch processing results
        """
        try:
            self.logger.info(f"Starting batch recommendation generation for {len(user_ids)} users")
            
            results = {
                "total_users": len(user_ids),
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "results": []
            }
            
            for user_id in user_ids:
                try:
                    result = self.generate_recommendations_for_user(user_id, force_update, **kwargs)
                    results["results"].append(result)
                    
                    if result["success"]:
                        if result.get("skipped", False):
                            results["skipped"] += 1
                        else:
                            results["successful"] += 1
                    else:
                        results["failed"] += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing user {user_id}: {str(e)}")
                    results["failed"] += 1
                    results["results"].append({
                        "success": False,
                        "error": str(e),
                        "user_id": user_id
                    })
            
            self.logger.info(f"Batch processing completed: {results['successful']} successful, "
                           f"{results['failed']} failed, {results['skipped']} skipped")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch processing: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_users": len(user_ids),
                "successful": 0,
                "failed": len(user_ids),
                "skipped": 0
            }
    
    def _process_llm_output(self, llm_out: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process LLM output and enrich with additional data
        
        Args:
            llm_out: Raw LLM output
            candidates: Candidate articles for enrichment
            
        Returns:
            Processed recommendations
        """
        try:
            # Process tag recommendations and separate wildcard from primary
            all_tags = llm_out.get("tags", [])[:20]
            tag_recommendations = [
                {"tag": t["tag"], "score": t["score"]}
                for t in all_tags
            ]
            
            # Debug: Log wildcard vs primary tags
            wildcard_tags = [t for t in all_tags if t.get("wildcard", False)]
            primary_tags = [t for t in all_tags if not t.get("wildcard", False)]
            self.logger.info(f"Tag breakdown: {len(primary_tags)} primary, {len(wildcard_tags)} wildcard")
            if wildcard_tags:
                self.logger.info(f"Wildcard tags: {[t['tag'] for t in wildcard_tags]}")
            
            # Process article recommendations with abstract enrichment
            candidate_abstract_by_id = {c.get("id"): c.get("abstract", "") for c in candidates}
            article_recommendations = []
            all_articles = llm_out.get("articles", [])[:20]
            
            for a in all_articles:
                art_id = a.get("id")
                if not art_id:
                    continue
                
                # Handle wildcard articles (trending content)
                if (art_id.startswith("wildcard-") or 
                    art_id.startswith("trending-") or 
                    art_id.startswith("newsapi-") or 
                    art_id.startswith("reddit-")):
                    # For trending articles, try to get real abstract from trending content
                    # This will be handled by the LLM which now has access to real trending articles
                    abstract = "Real trending article based on current global events and user interests"
                else:
                    # For regular articles, use abstract from candidate pool
                    abstract = candidate_abstract_by_id.get(art_id, "")
                    
                article_recommendations.append({
                    "id": art_id,
                    "score": a.get("score", 0),
                    "abstract": abstract
                })
            
            # Debug: Log wildcard vs primary articles
            wildcard_articles = [a for a in all_articles if a.get("wildcard", False)]
            primary_articles = [a for a in all_articles if not a.get("wildcard", False)]
            self.logger.info(f"Article breakdown: {len(primary_articles)} primary, {len(wildcard_articles)} wildcard")
            if wildcard_articles:
                wildcard_ids = [a['id'] for a in wildcard_articles]
                self.logger.info(f"Wildcard article IDs: {wildcard_ids}")
            
            return {
                "tags": tag_recommendations,
                "articles": article_recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error processing LLM output: {str(e)}")
            return {"tags": [], "articles": []}
