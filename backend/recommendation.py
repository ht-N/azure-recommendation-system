"""
Main module for generating tag recommendations using Azure AI Foundry
"""
import os
import time
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Add the helper directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'helper'))

from helper.cosmos_helper import CosmosHelper
from helper.azure_openai_helper import AzureOpenAIHelper
from helper.user_manager import UserManager
from helper.recommendation_manager import RecommendationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TagRecommendationEngine:
    """Main engine for generating tag recommendations"""
    
    def __init__(self):
        """Initialize the recommendation engine"""
        self.cosmos_helper = None
        self.openai_helper = None
        self.user_manager = None
        self.recommendation_manager = None
        self.logger = logger
        
        # Initialize helpers
        self._initialize_helpers()
    
    def _initialize_helpers(self):
        """Initialize all required helpers"""
        try:
            # Initialize core helpers
            self.cosmos_helper = CosmosHelper()
            self.openai_helper = AzureOpenAIHelper()
            
            # Initialize manager helpers
            self.user_manager = UserManager(self.cosmos_helper)
            self.recommendation_manager = RecommendationManager(
                self.cosmos_helper, 
                self.openai_helper, 
                self.user_manager
            )
            
            self.logger.info("Successfully initialized all helpers and managers")
        except Exception as e:
            self.logger.error(f"Failed to initialize helpers: {str(e)}")
            raise
    
    def get_all_user_ids(self, only_active: bool = False, limit: Optional[int] = None) -> List[str]:
        """
        Retrieve all user IDs from Cosmos DB.
        
        Args:
            only_active: if True, filter users by is_active = true when field exists
            limit: optional cap on number of users returned
            
        Returns:
            List of user IDs
        """
        return self.user_manager.get_all_user_ids(only_active, limit)
    
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
        return self.recommendation_manager.generate_recommendations_for_user(
            user_id=user_id,
            force_update=force_update,
            tag_count=tag_count,
            tag_wildcard=tag_wildcard,
            article_count=article_count,
            article_wildcard=article_wildcard,
            candidate_limit=candidate_limit
        )
    
    def benchmark_recommendation_performance(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """
        Benchmark recommendation performance for a specific user
        
        Args:
            user_id: ID of the user to benchmark
            **kwargs: Additional parameters for generate_recommendations_for_user
            
        Returns:
            Dictionary containing performance metrics
        """
        import time
        
        start_time = time.time()
        
        # Get user data timing
        user_start = time.time()
        user_data = self.cosmos_helper.get_user_by_id(user_id)
        user_fetch_time = time.time() - user_start
        
        if not user_data:
            return {"error": f"User {user_id} not found"}
        
        # Get user articles timing
        articles_start = time.time()
        user_articles = self.user_manager.get_user_articles_with_interactions(user_data)
        articles_fetch_time = time.time() - articles_start
        
        # Get cache stats
        cache_stats = self.cosmos_helper.get_cache_stats()
        
        total_time = time.time() - start_time
        
        return {
            "user_id": user_id,
            "total_time": total_time,
            "user_fetch_time": user_fetch_time,
            "articles_fetch_time": articles_fetch_time,
            "articles_count": len(user_articles),
            "cache_stats": cache_stats,
            "performance_summary": {
                "fast_retrieval": articles_fetch_time < 1.0,
                "cache_effective": cache_stats["valid_entries"] > 0,
                "optimization_working": articles_fetch_time < 2.0
            }
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
        return self.recommendation_manager.generate_recommendations_batch(
            user_ids=user_ids,
            force_update=force_update,
            **kwargs
        )
    


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate tag recommendations for users")
    parser.add_argument("--user-id", type=str, help="Generate recommendations for specific user")
    parser.add_argument("--batch", action="store_true", help="Process all users in batch")
    parser.add_argument("--force", action="store_true", help="Force update even if recent")
    parser.add_argument("--user-ids", nargs="+", help="List of user IDs for batch processing")
    # Tunables
    parser.add_argument("--candidate-limit", type=int, default=400, help="Max candidate articles to consider (default: 400)")
    parser.add_argument("--tag-count", type=int, default=15, help="Primary tag recommendations count (default: 15)")
    parser.add_argument("--tag-wildcard", type=int, default=5, help="Wildcard tag recommendations count (default: 5)")
    parser.add_argument("--article-count", type=int, default=15, help="Primary article recommendations count (default: 15)")
    parser.add_argument("--article-wildcard", type=int, default=5, help="Wildcard article recommendations count (default: 5)")
    
    args = parser.parse_args()
    start = time.time()
    try:
        # Initialize recommendation engine
        engine = TagRecommendationEngine()
        
        if args.user_id:
            # Single user processing
            result = engine.generate_recommendations_for_user(
                args.user_id,
                args.force,
                tag_count=args.tag_count,
                tag_wildcard=args.tag_wildcard,
                article_count=args.article_count,
                article_wildcard=args.article_wildcard,
                candidate_limit=args.candidate_limit,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.batch or args.user_ids:
            # Batch processing
            if args.user_ids:
                user_ids = args.user_ids
            else:
                # Get all user IDs from database
                user_ids = engine.get_all_user_ids(only_active=False)
                if not user_ids:
                    print("No users found to process in batch mode")
                    return
            
            result = engine.generate_recommendations_batch(
                user_ids,
                args.force,
                tag_count=args.tag_count,
                tag_wildcard=args.tag_wildcard,
                article_count=args.article_count,
                article_wildcard=args.article_wildcard,
                candidate_limit=args.candidate_limit,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        else:
            print("Please specify --user-id for single user or --batch for batch processing")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(json.dumps({"success": False, "error": str(e)}, indent=2))

    end = time.time()
    print(f"Time taken: {end - start} seconds")

if __name__ == "__main__":
    main()
