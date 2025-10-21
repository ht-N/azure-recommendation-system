"""
Azure OpenAI helper module for LLM operations
"""
import os
import json
import time
from typing import Dict, List, Optional, Any
import logging
from dotenv import load_dotenv, find_dotenv
from .trending_helper import TrendingHelper

load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from openai import AzureOpenAI
except ImportError:
    logger.error("Failed to import AzureOpenAI. Please install openai package.")
    raise


class AzureOpenAIHelper:
    """Helper class for Azure OpenAI operations"""
    
    def __init__(self):
        """Initialize Azure OpenAI client"""
        self.endpoint = os.getenv("AZURE_OPENAI_CHAT_ENDPOINT")
        self.chat_api_key = os.getenv("AZURE_OPENAI_CHAT_API_KEY")
        self.embedding_api_key = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY")
        self.chat_model = os.getenv("AZURE_OPENAI_CHAT_MODELNAME", "gpt-4")
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODELNAME", "text-embedding-3-large")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        self.embedding_dim = int(os.getenv("EMBEDDING_DIM", "3072"))
        
        self.trending_helper = TrendingHelper()
        
        if not self.endpoint or not self.chat_api_key:
            raise ValueError("AZURE_OPENAI_CHAT_ENDPOINT and AZURE_OPENAI_CHAT_API_KEY environment variables are required")
        
        try:
            # Try different initialization methods for chat client
            try:
                # Method 1: Standard initialization
                self.chat_client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=self.chat_api_key,
                    api_version=self.api_version
                )
                logger.info("Successfully initialized chat client (Method 1)")
            except Exception as e1:
                logger.warning(f"Method 1 failed: {e1}")
                try:
                    # Method 2: Without api_version
                    self.chat_client = AzureOpenAI(
                        azure_endpoint=self.endpoint,
                        api_key=self.chat_api_key
                    )
                    logger.info("Successfully initialized chat client (Method 2)")
                except Exception as e2:
                    logger.error(f"Method 2 failed: {e2}")
                    raise e1  # Raise the original error
            
            # Initialize embedding client (use same client if same key)
            if self.embedding_api_key and self.embedding_api_key != self.chat_api_key:
                try:
                    self.embedding_client = AzureOpenAI(
                        azure_endpoint=self.endpoint,
                        api_key=self.embedding_api_key,
                        api_version=self.api_version
                    )
                except Exception:
                    # Fallback without api_version
                    self.embedding_client = AzureOpenAI(
                        azure_endpoint=self.endpoint,
                        api_key=self.embedding_api_key
                    )
            else:
                self.embedding_client = self.chat_client
                
            logger.info("Successfully initialized Azure OpenAI clients")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI: {str(e)}")
            logger.error(f"Endpoint: {self.endpoint}")
            logger.error(f"API Version: {self.api_version}")
            logger.error(f"Chat API Key length: {len(self.chat_api_key) if self.chat_api_key else 'None'}")
            raise
    
    def generate_tag_recommendations(self, user_tags: List[str], user_articles: List[Dict[str, Any]], 
                                   all_available_tags: List[str]) -> List[Dict[str, float]]:
        """
        Generate tag recommendations using LLM based on user's reading history
        
        Args:
            user_tags: Tags from articles the user has interacted with
            user_articles: Articles the user has liked/bookmarked
            all_available_tags: All available tags in the system
            
        Returns:
            List of tag recommendations with scores
        """
        try:
            # Prepare user's reading context
            user_reading_context = self._prepare_user_context(user_tags, user_articles)
            
            # Create prompt for tag recommendation
            prompt = self._create_tag_recommendation_prompt(
                user_reading_context, 
                user_tags, 
                all_available_tags
            )
            
            # Call LLM for tag recommendations
            response = self._call_chat_completion(prompt)
            
            # Parse and validate response
            recommendations = self._parse_tag_recommendations(response, all_available_tags)
            
            logger.info(f"Generated {len(recommendations)} tag recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating tag recommendations: {str(e)}")
            return []

    def generate_llm_only_recommendations(self,
                                          user_articles: List[Dict[str, Any]],
                                          candidate_articles: List[Dict[str, Any]],
                                          tag_count: int = 15,
                                          tag_wildcard: int = 5,
                                          article_count: int = 15,
                                          article_wildcard: int = 5) -> Dict[str, Any]:
        """
        Use only LLM to produce tag and article recommendations from user history and a candidate pool.

        Returns a dict with keys: tags (list[{tag, score, wildcard?}]) and articles (list[{id, score, wildcard?}]).
        """
        try:
            # Prepare compact context for the model
            def compress_article(article: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "id": article.get("id"),
                    "title": article.get("title", "")[:140],
                    "abstract": article.get("abstract", "")[:600],
                    "tags": article.get("tags", [])
                }

            user_ctx = [compress_article(a) for a in user_articles][:60]
            pool_ctx = [compress_article(a) for a in candidate_articles][:400]

            # Get real trending content for wildcard recommendations
            logger.info("Fetching trending content for wildcard recommendations...")
            trending_topics = self.trending_helper.get_trending_topics(tag_wildcard)
            trending_articles = self.trending_helper.get_trending_articles(trending_topics, article_wildcard)
            
            # Debug: Print data summary
            logger.info(f"LLM Input Summary:")
            logger.info(f"- User articles (context): {len(user_ctx)}")
            logger.info(f"- Candidate articles (pool): {len(pool_ctx)}")
            logger.info(f"- Trending topics found: {len(trending_topics)}")
            logger.info(f"- Trending articles found: {len(trending_articles)}")
            logger.info(f"- Requested tags: {tag_count} primary + {tag_wildcard} wildcard")
            logger.info(f"- Requested articles: {article_count} primary + {article_wildcard} wildcard")

            prompt = self._create_llm_only_prompt(
                user_ctx,
                pool_ctx,
                trending_topics,
                trending_articles,
                tag_count,
                tag_wildcard,
                article_count,
                article_wildcard
            )

            # Debug: Print prompt for understanding
            logger.info("=" * 80)
            logger.info("PROMPT SENT TO LLM:")
            logger.info("=" * 80)
            logger.info(prompt)
            logger.info("=" * 80)

            raw = self._call_chat_completion(prompt)
            parsed_result = self._parse_llm_only_output(raw)
            
            # Debug: Print parsed results
            logger.info(f"Parsed Results:")
            logger.info(f"- Tags found: {len(parsed_result.get('tags', []))}")
            logger.info(f"- Articles found: {len(parsed_result.get('articles', []))}")
            
            return parsed_result
        except Exception as e:
            logger.error(f"Error in LLM-only generation: {str(e)}")
            return {"tags": [], "articles": []}

    def _create_llm_only_prompt(self,
                                user_ctx: List[Dict[str, Any]],
                                pool_ctx: List[Dict[str, Any]],
                                trending_topics: List[str],
                                trending_articles: List[Dict[str, Any]],
                                tag_count: int,
                                tag_wildcard: int,
                                article_count: int,
                                article_wildcard: int) -> str:
        return f"""
You are a recommendation engine with access to current trends and real-time data. You should recommend based on user history AND actual trending content.

User history articles (abstracts and tags):
{json.dumps(user_ctx, ensure_ascii=False)}

Candidate articles (id, abstract, tags):
{json.dumps(pool_ctx, ensure_ascii=False)}

REAL TRENDING CONTENT:
Current trending topics: {json.dumps(trending_topics, ensure_ascii=False)}
Real trending articles: {json.dumps(trending_articles, ensure_ascii=False)}

Task:
1. PRIMARY RECOMMENDATIONS (based on user history):
   - Recommend exactly {tag_count} tags the user is most likely to enjoy based on their reading history
   - Recommend exactly {article_count} article IDs from the candidate pool (most relevant to user)

2. WILDCARD RECOMMENDATIONS (using REAL trending content):
   - For WILDCARD tags: Use the provided trending topics list above. Select {tag_wildcard} topics that would interest this user based on their history
   - For WILDCARD articles: Use the provided trending articles list above. Select {article_wildcard} articles that would interest this user based on their history

WILDCARD Rules:
- Use ONLY the trending topics and articles provided above - these are real, current trending content
- Wildcard tags must come from the trending topics list
- Wildcard articles must use the IDs and content from the trending articles list
- Choose trending content that would genuinely interest the user based on their reading history

Output valid JSON ONLY with this shape:
{{
  "tags": [
    {{"tag": "string", "score": number, "wildcard": false}},
    ... {tag_count} primary tags first, then {tag_wildcard} wildcard tags with "wildcard": true ...
  ],
  "articles": [
    {{"id": "uuid-or-id", "score": number, "wildcard": false}},
    ... {article_count} primary articles first, then {article_wildcard} wildcard articles with "wildcard": true ...
  ]
}}
Scores: 1.0 to 5.0. Higher is more relevant. Do not add extra fields.
"""

    def _parse_llm_only_output(self, response: str) -> Dict[str, Any]:
        try:
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text)

            tags = []
            for t in data.get("tags", []):
                if isinstance(t, dict) and "tag" in t and "score" in t:
                    try:
                        score = float(t["score"])
                    except Exception:
                        continue
                    tags.append({
                        "tag": t["tag"],
                        "score": max(1.0, min(5.0, score)),
                        "wildcard": bool(t.get("wildcard", False))
                    })

            articles = []
            for a in data.get("articles", []):
                if isinstance(a, dict) and "id" in a and "score" in a:
                    try:
                        score = float(a["score"])
                    except Exception:
                        continue
                    articles.append({
                        "id": a["id"],
                        "score": round(max(0.0, min(5.0, score)), 4),
                        "wildcard": bool(a.get("wildcard", False))
                    })

            return {"tags": tags, "articles": articles}
        except Exception as e:
            logger.error(f"Failed parsing LLM-only output: {str(e)}")
            return {"tags": [], "articles": []}
    
    def _prepare_user_context(self, user_tags: List[str], user_articles: List[Dict[str, Any]]) -> str:
        """
        Prepare user's reading context from their articles
        
        Args:
            user_tags: Tags from user's articles
            user_articles: User's articles
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add user's tag preferences
        if user_tags:
            tag_frequency = {}
            for tag in user_tags:
                tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
            
            sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
            context_parts.append(f"User's tag interests (frequency): {dict(sorted_tags[:10])}")
        
        # Add sample of user's articles
        if user_articles:
            article_samples = []
            for article in user_articles[:5]:  # Limit to 5 articles for context
                article_info = {
                    "title": article.get("title", ""),
                    "tags": article.get("tags", []),
                    "abstract": article.get("abstract", "")[:200] + "..." if len(article.get("abstract", "")) > 200 else article.get("abstract", "")
                }
                article_samples.append(article_info)
            
            context_parts.append(f"Sample articles user has interacted with: {json.dumps(article_samples, ensure_ascii=False)}")
        
        return "\n".join(context_parts)
    
    def _create_tag_recommendation_prompt(self, user_context: str, user_tags: List[str], 
                                        all_available_tags: List[str]) -> str:
        """
        Create prompt for tag recommendation
        
        Args:
            user_context: User's reading context
            user_available_tags: Tags from user's articles
            all_available_tags: All available tags in the system
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
You are an expert content recommendation system. Based on the user's reading history and preferences, recommend the most relevant tags for this user.

User's reading context:
{user_context}

User's current tag interests:
{user_tags}

Available tags in the system:
{all_available_tags}

Please recommend the top 10 most relevant tags for this user based on their reading history and interests. Consider:
1. Tags from articles they've liked/bookmarked
2. Similar or related tags they might be interested in
3. Popular tags in their areas of interest
4. Emerging or trending tags in their domain

Return your response as a JSON array of objects with the following format:
[
    {{"tag": "tag_name", "score": 5.0}},
    {{"tag": "another_tag", "score": 4.5}},
    ...
]

The score should be between 1.0 and 5.0, where:
- 5.0: Perfect match, user is very likely interested
- 4.0-4.9: Strong match, user is likely interested
- 3.0-3.9: Good match, user might be interested
- 2.0-2.9: Weak match, user could be interested
- 1.0-1.9: Minimal match, user might have a little interest or none at all

Only include tags that are in the available tags list. Return exactly 10 recommendations.
"""
        return prompt
    
    def _call_chat_completion(self, prompt: str, max_retries: int = 3) -> str:
        """
        Call Azure OpenAI chat completion with retry logic
        
        Args:
            prompt: Input prompt
            max_retries: Maximum number of retry attempts
            
        Returns:
            LLM response
        """
        for attempt in range(max_retries):
            try:
                response = self.chat_client.chat.completions.create(
                    model=self.chat_deployment,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that provides accurate JSON responses for content recommendation systems."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0,
                    max_tokens=2000
                )
                
                content = response.choices[0].message.content
                logger.info("Successfully received response from Azure OpenAI")
                
                # Debug: Print LLM response for understanding
                logger.info("=" * 80)
                logger.info("LLM RESPONSE FOR DEBUGGING:")
                logger.info("=" * 80)
                logger.info(content)
                logger.info("=" * 80)
                
                return content
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise
        
        return ""
    
    def _parse_tag_recommendations(self, response: str, all_available_tags: List[str]) -> List[Dict[str, float]]:
        """
        Parse LLM response and validate tag recommendations
        
        Args:
            response: LLM response string
            all_available_tags: List of valid tags
            
        Returns:
            List of validated tag recommendations
        """
        try:
            # Clean the response to extract JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Parse JSON
            recommendations = json.loads(response)
            
            # Validate and filter recommendations
            valid_recommendations = []
            for rec in recommendations:
                if isinstance(rec, dict) and "tag" in rec and "score" in rec:
                    tag = rec["tag"]
                    score = rec["score"]
                    
                    # Validate tag exists in available tags
                    if tag in all_available_tags:
                        # Validate score is a number
                        try:
                            score_float = float(score)
                            if 1.0 <= score_float <= 5.0:
                                valid_recommendations.append({"tag": tag, "score": score_float})
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid score for tag {tag}: {score}")
                            continue
                    else:
                        logger.warning(f"Tag {tag} not found in available tags")
            
            # Sort by score descending and limit to 10
            valid_recommendations.sort(key=lambda x: x["score"], reverse=True)
            return valid_recommendations[:10]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Response was: {response}")
            return []
        except Exception as e:
            logger.error(f"Error parsing tag recommendations: {str(e)}")
            return []
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = []
            
            # Process in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = self.embedding_client.embeddings.create(
                    input=batch,
                    model=self.embedding_deployment
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                # Small delay between batches
                if i + batch_size < len(texts):
                    time.sleep(0.1)
            
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []
