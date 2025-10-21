# AI Recommendation System - Workforce Intelligence Platform

> **Continuation Project**: This project builds upon and extends the excellent work from [pdz1804/azure-search-system](https://github.com/pdz1804/azure-search-system), adding advanced AI-powered recommendation capabilities for workforce intelligence.

A comprehensive AI-powered recommendation system that analyzes user reading patterns and generates intelligent content recommendations using Azure AI services. This system extends the original Azure Search System with advanced recommendation algorithms, performance optimizations, and a modern demo interface.

## 🖼️ Demo Interface

![AI Recommendation System Demo](overall_website.png)

The demo interface showcases:
- **User Reading History Analysis**: View detailed interaction patterns (liked, bookmarked, disliked articles)
- **Intelligent Tag Recommendations**: AI-powered tag suggestions with personalized and trending content
- **Article Recommendations**: Smart content suggestions based on user preferences
- **Performance Monitoring**: Real-time metrics and cache optimization insights
- **Recent Recommendations Handling**: Automatic detection of recently generated recommendations

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js (for demo frontend)
- Azure account with Cosmos DB, OpenAI, and AI Search services
- Git

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd azure-recommendation-system
   ```

2. **Set up environment variables**
   ```bash
   # Copy the sample environment file
   cp .env.sample .env
   
   # Edit .env with your Azure credentials
   nano .env
   ```

3. **Install dependencies**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Install demo dependencies
   cd demo
   pip install -r requirements.txt
   ```

4. **Run the demo**
   ```bash
   # Navigate to demo directory
   cd demo
   
   # Start the demo (recommended for testing)
   python run_demo.py --force
   
   # Or run directly
   python app.py
   ```

5. **Access the demo**
   - Open your browser to `http://localhost:5000`
   - Enter a user ID and click "Generate Recommendations"
   - Explore the intelligent recommendations and user analytics

## 🏗️ Project Structure

```
continue-whats-left/
├── 📁 azure/                          # Azure service configurations
│   ├── ai-search/                     # Azure AI Search setup
│   │   ├── provision.py               # Index provisioning
│   │   ├── run_indexer.py            # Indexer management
│   │   └── search_example.py         # Search examples
│   ├── cosmosdb/                      # Cosmos DB utilities
│   │   └── upload.py                 # Data upload scripts
│   └── data/                         # Sample datasets
│       ├── articles.json             # Article data
│       ├── users.json                # User data
│       └── test.json                 # Test data
├── 📁 backend/                        # Core recommendation engine
│   ├── 📁 helper/                     # Helper modules
│   │   ├── azure_openai_helper.py    # Azure OpenAI integration
│   │   ├── cosmos_helper.py          # Cosmos DB operations
│   │   ├── recommendation_manager.py # Recommendation logic
│   │   ├── tag_analyzer.py           # Tag analysis algorithms
│   │   ├── trending_helper.py        # Trending content detection
│   │   └── user_manager.py           # User data management
│   ├── recommendation.py             # Main recommendation engine
│   ├── test_openai.py               # OpenAI connection testing
│   └── PERFORMANCE_OPTIMIZATIONS.md  # Performance documentation
├── 📁 demo/                          # Interactive demo interface
│   ├── app.py                        # Flask demo server
│   ├── index.html                    # Demo frontend
│   ├── script.js                     # Frontend JavaScript
│   ├── styles.css                    # Demo styling
│   ├── run_demo.py                   # Demo runner script
│   ├── start_demo.bat               # Windows demo launcher
│   ├── start_demo.sh                # Linux/Mac demo launcher
│   └── README.md                     # Demo documentation
├── 📄 requirements.txt               # Python dependencies
├── 📄 .env.sample                    # Environment variables template
└── 📄 README.md                      # This file
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# === Cosmos DB Configuration ===
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-primary-key
DATABASE_NAME=intern-htn
ARTICLES_CONTAINER=articles
USER_CONTAINER=users

# === Azure OpenAI Configuration ===
AZURE_OPENAI_CHAT_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_CHAT_API_KEY=your-azure-openai-key
AZURE_OPENAI_CHAT_MODELNAME=gpt-4
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# === Optional: Trending Content ===
NEWS_API_KEY=your-news-api-key  # For real-time trending content

# === Demo Configuration ===
DEMO_MODE=false                   # Set to true for mock data mode
FLASK_DEBUG=False                # Enable Flask debug mode
PORT=5000                        # Demo server port
```

## 🎯 Key Features

### 🧠 AI-Powered Recommendations
- **LLM-Only Generation**: Uses Azure OpenAI for intelligent content analysis
- **Hybrid Recommendations**: Combines personalized and trending content
- **Smart Scoring**: Advanced scoring algorithms with configurable weights
- **Context Awareness**: Analyzes user reading history and interaction patterns

### ⚡ Performance Optimizations
- **Batch Query Processing**: Reduces database queries by 90%
- **Intelligent Caching**: 5-minute TTL with 80-90% hit rates
- **Connection Pooling**: Optimized Azure service connections
- **Parallel Processing**: Concurrent user recommendation generation

### 📊 Advanced Analytics
- **User Behavior Analysis**: Detailed interaction pattern analysis
- **Performance Monitoring**: Real-time metrics and cache statistics
- **Trending Content Detection**: Real-time trending topics integration
- **Recommendation Freshness**: Automatic detection of recent recommendations

### 🎨 Modern Demo Interface
- **Two-Column Layout**: User articles and recommendations side-by-side
- **Interactive Visualizations**: Real-time performance metrics
- **Responsive Design**: Works on desktop and mobile devices
- **Real-Time Updates**: Live recommendation generation and display

## 🚀 Usage Examples

### Command Line Interface

```bash
# Generate recommendations for a specific user
python backend/recommendation.py --user-id "user123"

# Generate recommendations with custom parameters
python backend/recommendation.py --user-id "user123" \
    --tag-count 20 \
    --article-count 25 \
    --candidate-limit 500

# Force update (bypass 24-hour check)
python backend/recommendation.py --user-id "user123" --force

# Batch processing for multiple users
python backend/recommendation.py --batch

# Benchmark performance
python backend/recommendation.py --user-id "user123" --benchmark
```

### Programmatic Usage

```python
from backend.recommendation import TagRecommendationEngine

# Initialize the engine
engine = TagRecommendationEngine()

# Generate recommendations for a user
result = engine.generate_recommendations_for_user(
    user_id="user123",
    force_update=False,
    tag_count=15,
    tag_wildcard=5,
    article_count=15,
    article_wildcard=5,
    candidate_limit=400
)

# Check results
if result["success"]:
    print(f"Generated {len(result['tags_recommendation'])} tag recommendations")
    print(f"Generated {len(result['articles_recommendation'])} article recommendations")
```

### Demo Interface

1. **Start the demo**: `cd demo && python run_demo.py --force`
2. **Open browser**: Navigate to `http://localhost:5000`
3. **Enter user ID**: Input a valid user ID from your database
4. **Generate recommendations**: Click "Generate Recommendations"
5. **Explore results**: View user articles, tag recommendations, and article suggestions

## 📈 Performance Metrics

### Optimization Results
- **Query Time**: Reduced from 5+ seconds to <1 second (5-10x improvement)
- **Database Queries**: 90% reduction in Cosmos DB requests
- **Cache Hit Rate**: 80-90% for repeated requests
- **Concurrent Users**: 10x improvement in handling multiple users
- **Cost Reduction**: 90% reduction in Cosmos DB RU consumption

### Benchmarking
```bash
# Run performance benchmark
python backend/recommendation.py --user-id "user123" --benchmark

# Expected output:
# {
#   "user_id": "user123",
#   "total_time": 0.45,
#   "articles_fetch_time": 0.23,
#   "articles_count": 84,
#   "cache_stats": {
#     "total_entries": 156,
#     "valid_entries": 142,
#     "cache_ttl": 300
#   }
# }
```

## 🔗 Relationship to Original Project

This project extends the excellent work from [pdz1804/azure-search-system](https://github.com/pdz1804/azure-search-system) by adding:

### New Capabilities
- **AI Recommendation Engine**: Advanced LLM-powered recommendation algorithms
- **User Behavior Analysis**: Deep analysis of reading patterns and preferences
- **Performance Optimizations**: Significant improvements in query speed and caching
- **Interactive Demo**: Modern web interface for testing and demonstration
- **Trending Content Integration**: Real-time trending topics and content detection

### Architectural Enhancements
- **Modular Design**: Clean separation of concerns with helper modules
- **Error Handling**: Robust error handling and graceful degradation
- **Configuration Management**: Flexible configuration system
- **Monitoring**: Comprehensive performance monitoring and metrics

### Data Flow Integration
```
Original System: Articles → AI Search → Search Results
Extended System: Users + Articles → AI Analysis → Personalized Recommendations
```

## 🛠️ Development

### Running Tests
```bash
# Test OpenAI connection
python backend/test_openai.py

# Test recommendation engine
python backend/recommendation.py --user-id "test-user" --benchmark
```


### Debugging
```bash
# Enable debug mode
export FLASK_DEBUG=True

# Run with verbose logging
python demo/app.py --verbose
```

## 🚀 Deployment

### Production Deployment
```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment
export DEMO_MODE=False
export FLASK_DEBUG=False

# Run production server
python demo/app.py
```

### Docker Deployment
```bash
# Build Docker image
docker build -t ai-recommendation-demo .

# Run container
docker run -p 5000:5000 --env-file .env ai-recommendation-demo
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- **Demo Health**: `GET http://localhost:5000/api/health`
- **Cache Stats**: `GET http://localhost:5000/api/cache/stats`
- **Clear Cache**: `POST http://localhost:5000/api/cache/clear`

### Performance Monitoring
- **Query Times**: Monitor database query performance
- **Cache Hit Rates**: Track cache effectiveness
- **Memory Usage**: Monitor system resource consumption
- **Error Rates**: Track and alert on system errors

## 🔮 Future Enhancements

### Planned Features
- **Multi-language Support**: Support for multiple languages
- **Advanced Analytics**: User behavior insights and reporting
- **Real-time Updates**: Live recommendation updates
- **A/B Testing**: Recommendation algorithm testing framework
- **Mobile App**: Native mobile application

### AI/ML Improvements
- **Custom Embeddings**: Domain-specific embedding models
- **Federated Learning**: Privacy-preserving recommendation learning
- **Auto-tuning**: Automatic hyperparameter optimization
- **Explainable AI**: Recommendation explanation and reasoning

## 🆘 Troubleshooting

### Common Issues

#### Environment Setup
```bash
# Check environment variables
python -c "import os; print('COSMOS_ENDPOINT:', os.getenv('COSMOS_ENDPOINT'))"

# Test Azure connections
python backend/test_openai.py
```

#### Performance Issues
```bash
# Clear cache
curl -X POST http://localhost:5000/api/cache/clear

# Check cache stats
curl http://localhost:5000/api/cache/stats
```

#### Recommendation Issues
```bash
# Force update recommendations
python backend/recommendation.py --user-id "user123" --force

# Check user data
python -c "from backend.helper.cosmos_helper import CosmosHelper; ch = CosmosHelper(); print(ch.get_user_by_id('user123'))"
```

## 📚 Documentation

- **[Backend Documentation](backend/README.md)**: Core recommendation engine
- **[Demo Documentation](demo/README.md)**: Interactive demo interface
- **[Performance Guide](backend/PERFORMANCE_OPTIMIZATIONS.md)**: Optimization details

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** and add tests
4. **Run quality checks**: `make lint test`
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Create Pull Request**

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Original Project**: Built upon [pdz1804/azure-search-system](https://github.com/pdz1804/azure-search-system)
- **Azure AI Services**: Powered by Azure OpenAI, Cosmos DB, and AI Search
- **Open Source Community**: Thanks to all contributors and the open source ecosystem

## 📞 Support

- **Documentation**: Check component-specific README files
- **Issues**: Create GitHub issues for bug reports
- **Questions**: Use GitHub Discussions for questions
- **Enterprise Support**: Contact the development team

---

**Built with ❤️ using Azure AI Services, extending the excellent work from pdz1804**
