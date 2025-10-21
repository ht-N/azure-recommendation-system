#!/usr/bin/env python3
"""
Flask API wrapper for the AI Recommendation System Demo
"""
import os
import sys
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# Add the backend path to sys.path
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.append(backend_path)

# Import the recommendation engine
from recommendation import TagRecommendationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize recommendation engine with force update option
force_update_mode = '--force' in sys.argv
force_demo = os.getenv('DEMO_MODE', 'false').lower() == 'true'

# Debug logging
logger.info(f"Command line args: {sys.argv}")
logger.info(f"Force update mode: {force_update_mode}")
logger.info(f"Force demo mode: {force_demo}")

if force_demo:
    logger.info("Running in DEMO mode - using mock data")
    recommendation_engine = None
else:
    try:
        recommendation_engine = TagRecommendationEngine()
        logger.info("Recommendation engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize recommendation engine: {str(e)}")
        logger.info("Falling back to demo mode with mock data")
        recommendation_engine = None

@app.route('/')
def serve_index():
    """Serve the main demo page"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    return send_from_directory('.', filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'engine_ready': recommendation_engine is not None,
        'demo_mode': recommendation_engine is None,
        'force_demo': force_demo
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get list of available users"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        # Get sample users for demo
        users = recommendation_engine.get_all_user_ids(only_active=False, limit=10)
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/<user_id>/articles', methods=['GET'])
def get_user_articles(user_id):
    """Get articles that a user has interacted with"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        # Get user data
        user_data = recommendation_engine.cosmos_helper.get_user_by_id(user_id)
        if not user_data:
            return jsonify({'error': f'User {user_id} not found'}), 404
        
        # Get user articles with interactions
        user_articles = recommendation_engine.user_manager.get_user_articles_with_interactions(user_data)
        
        # Get interaction summary
        liked_articles = user_data.get("liked_articles", [])
        bookmarked_articles = user_data.get("bookmarked_articles", [])
        disliked_articles = user_data.get("disliked_articles", [])
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'articles': user_articles,
            'interaction_summary': {
                'total_articles': len(user_articles),
                'liked_count': len(liked_articles),
                'bookmarked_count': len(bookmarked_articles),
                'disliked_count': len(disliked_articles)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user articles for {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/<user_id>', methods=['POST'])
def generate_recommendations(user_id):
    """Generate recommendations for a specific user"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        # Get parameters from request body
        data = request.get_json() or {}
        
        # Force update if --force flag was used when starting the app
        force_update = data.get('force_update', False) or force_update_mode
        
        tag_count = data.get('tag_count', 15)
        tag_wildcard = data.get('tag_wildcard', 5)
        article_count = data.get('article_count', 15)
        article_wildcard = data.get('article_wildcard', 5)
        candidate_limit = data.get('candidate_limit', 400)
        
        logger.info(f"Generating recommendations for user {user_id} (force_update={force_update})")
        
        # Generate recommendations
        result = recommendation_engine.generate_recommendations_for_user(
            user_id=user_id,
            force_update=force_update,
            tag_count=tag_count,
            tag_wildcard=tag_wildcard,
            article_count=article_count,
            article_wildcard=article_wildcard,
            candidate_limit=candidate_limit
        )
        
        # Add API metadata
        result['api_timestamp'] = datetime.utcnow().isoformat()
        result['api_version'] = '1.0'
        result['force_update_used'] = force_update
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'user_id': user_id
        }), 500

@app.route('/api/benchmark/<user_id>', methods=['GET'])
def benchmark_performance(user_id):
    """Benchmark recommendation performance for a specific user"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        logger.info(f"Benchmarking performance for user {user_id}")
        
        # Benchmark performance
        result = recommendation_engine.benchmark_recommendation_performance(user_id)
        
        # Add API metadata
        result['api_timestamp'] = datetime.utcnow().isoformat()
        result['api_version'] = '1.0'
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error benchmarking performance for user {user_id}: {str(e)}")
        return jsonify({
            'error': str(e),
            'user_id': user_id
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        cache_stats = recommendation_engine.cosmos_helper.get_cache_stats()
        
        return jsonify({
            'success': True,
            'cache_stats': cache_stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the article cache"""
    try:
        if not recommendation_engine:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        recommendation_engine.cosmos_helper.clear_article_cache()
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check if environment variables are set
    required_env_vars = ['COSMOS_ENDPOINT', 'COSMOS_KEY', 'OPENAI_API_KEY', 'OPENAI_API_VERSION']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    # Run the Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("=" * 60)
    logger.info("🚀 AI Recommendation System Demo")
    logger.info("=" * 60)
    
    if force_update_mode:
        logger.info("⚡ FORCE UPDATE MODE enabled - Will bypass recent recommendations check")
        logger.info("   Perfect for testing and demonstrations!")
    
    if force_demo:
        logger.info("🎭 RUNNING IN DEMO MODE - Using mock data")
        logger.info("   Perfect for presentations and demos!")
    else:
        if missing_vars:
            logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
            logger.warning("   Some features may not work properly")
        else:
            logger.info("✅ All environment variables found")
            logger.info("   Full functionality available")
    
    logger.info(f"🌐 Demo available at: http://localhost:{port}")
    logger.info(f"📱 API health check: http://localhost:{port}/api/health")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
