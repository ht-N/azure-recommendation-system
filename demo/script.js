// Demo Application JavaScript
class RecommendationDemo {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5000/api';
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        document.getElementById('generateBtn').addEventListener('click', () => {
            this.generateRecommendations();
        });

        document.getElementById('benchmarkBtn').addEventListener('click', () => {
            this.benchmarkPerformance();
        });

        // Enter key support
        document.getElementById('userId').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.generateRecommendations();
            }
        });
    }


    async generateRecommendations() {
        const userId = document.getElementById('userId').value.trim();
        
        if (!userId) {
            this.showError('Please enter a user ID');
            return;
        }

        this.showLoading();
        this.hideError();
        this.hideResults();
        this.hideRecentMessage();

        try {
            // First load user articles
            const userResponse = await fetch(`${this.apiBaseUrl}/user/${userId}/articles`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!userResponse.ok) {
                throw new Error(`Failed to load user articles: ${userResponse.status}`);
            }

            const userData = await userResponse.json();
            if (!userData.success) {
                throw new Error(userData.error || 'Failed to load user articles');
            }

            // Then generate recommendations
            const response = await fetch(`${this.apiBaseUrl}/recommendations/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    force_update: false,
                    tag_count: 15,
                    tag_wildcard: 5,
                    article_count: 15,
                    article_wildcard: 5,
                    candidate_limit: 400
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // Check if recommendations were skipped (already recent)
                if (data.skipped) {
                    this.displayRecentRecommendations(userData, data);
                } else {
                    // Display both user articles and new recommendations
                    this.displayUserArticles(userData);
                    this.displayRecommendations(data);
                }
            } else {
                this.showError(data.error || 'Failed to generate recommendations');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showError(`Network error: ${error.message}`);
        }
    }

    async benchmarkPerformance() {
        const userId = document.getElementById('userId').value.trim();
        
        if (!userId) {
            this.showError('Please enter a user ID');
            return;
        }

        this.showLoading();
        this.hideError();
        this.hideResults();
        this.hideRecentMessage();

        try {
            const response = await fetch(`${this.apiBaseUrl}/benchmark/${userId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.user_id) {
                this.displayBenchmarkResults(data);
            } else {
                this.showError(data.error || 'Failed to benchmark performance');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showError(`Network error: ${error.message}`);
        }
    }

    displayRecommendations(data) {
        this.hideLoading();
        this.showResults();

        // Display tag recommendations in right column
        const tagContainer = document.getElementById('tagRecommendations');
        tagContainer.innerHTML = '';

        if (data.tags_recommendation && data.tags_recommendation.length > 0) {
            data.tags_recommendation.forEach(tag => {
                const tagElement = this.createTagElement(tag);
                tagContainer.appendChild(tagElement);
            });
        } else {
            tagContainer.innerHTML = '<p>No tag recommendations available</p>';
        }

        // Display article recommendations in full width below
        const articleContainer = document.getElementById('articleRecommendations');
        articleContainer.innerHTML = '';

        if (data.articles_recommendation && data.articles_recommendation.length > 0) {
            data.articles_recommendation.forEach(article => {
                const articleElement = this.createArticleElement(article);
                articleContainer.appendChild(articleElement);
            });
        } else {
            articleContainer.innerHTML = '<p>No article recommendations available</p>';
        }

        // Add fade-in animation
        document.getElementById('resultsSection').classList.add('fade-in');
    }

    displayRecentRecommendations(userData, recommendationData) {
        this.hideLoading();
        this.hideResults();
        this.showRecentMessage();
        
        // Display recent recommendations message
        const recentMessage = document.getElementById('recentMessage');
        recentMessage.textContent = `Recommendations for this user were already generated recently (within 24 hours). Using existing recommendations.`;
        
        // Display user articles (same as normal flow)
        this.displayUserArticles(userData);
        
        // Display existing recommendations
        if (recommendationData.existing_recommendations && recommendationData.existing_recommendations.length > 0) {
            this.displayExistingRecommendations(recommendationData);
        }
        
        // Add fade-in animation
        document.getElementById('recentSection').classList.add('fade-in');
    }

    displayExistingRecommendations(data) {
        this.showResults();

        // Display existing tag recommendations in right column
        const tagContainer = document.getElementById('tagRecommendations');
        tagContainer.innerHTML = '';

        if (data.existing_recommendations && data.existing_recommendations.length > 0) {
            data.existing_recommendations.forEach(tag => {
                const tagElement = this.createTagElement(tag);
                tagContainer.appendChild(tagElement);
            });
        } else {
            tagContainer.innerHTML = '<p>No existing tag recommendations available</p>';
        }

        // For existing recommendations, we might not have article recommendations
        // So we'll show a message instead
        const articleContainer = document.getElementById('articleRecommendations');
        articleContainer.innerHTML = '<p style="text-align: center; color: #718096; padding: 20px;">Article recommendations are generated with new recommendations only.</p>';

        // Add fade-in animation
        document.getElementById('resultsSection').classList.add('fade-in');
    }

    displayUserArticles(data) {
        // Display interaction summary
        const summaryContainer = document.getElementById('userInteractionSummary');
        const summary = data.interaction_summary;
        
        summaryContainer.innerHTML = `
            <div class="summary-item">
                <div class="summary-label">Total Articles</div>
                <div class="summary-value">${summary.total_articles}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Liked</div>
                <div class="summary-value liked">${summary.liked_count}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Bookmarked</div>
                <div class="summary-value bookmarked">${summary.bookmarked_count}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Disliked</div>
                <div class="summary-value disliked">${summary.disliked_count}</div>
            </div>
        `;
        
        // Display user articles
        const articlesContainer = document.getElementById('userArticlesList');
        articlesContainer.innerHTML = '';
        
        if (data.articles && data.articles.length > 0) {
            data.articles.forEach(article => {
                const articleElement = this.createUserArticleElement(article);
                articlesContainer.appendChild(articleElement);
            });
        } else {
            articlesContainer.innerHTML = '<p style="text-align: center; color: #718096; padding: 20px;">No articles found for this user</p>';
        }
    }

    createUserArticleElement(article) {
        const articleDiv = document.createElement('div');
        articleDiv.className = 'user-article-item';
        
        const header = document.createElement('div');
        header.className = 'user-article-header';
        
        const title = document.createElement('div');
        title.className = 'user-article-title';
        title.textContent = article.title || 'Untitled Article';
        
        const interactions = document.createElement('div');
        interactions.className = 'user-article-interactions';
        
        if (article.interaction_types && article.interaction_types.length > 0) {
            article.interaction_types.forEach(type => {
                const badge = document.createElement('span');
                badge.className = `interaction-badge ${type}`;
                badge.textContent = type.charAt(0).toUpperCase() + type.slice(1);
                interactions.appendChild(badge);
            });
        }
        
        header.appendChild(title);
        header.appendChild(interactions);
        
        const abstract = document.createElement('div');
        abstract.className = 'user-article-abstract';
        abstract.textContent = article.abstract || 'No abstract available';
        
        const tags = document.createElement('div');
        tags.className = 'user-article-tags';
        
        if (article.tags && article.tags.length > 0) {
            article.tags.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.className = 'user-article-tag';
                tagElement.textContent = tag;
                tags.appendChild(tagElement);
            });
        }
        
        articleDiv.appendChild(header);
        articleDiv.appendChild(abstract);
        articleDiv.appendChild(tags);
        
        return articleDiv;
    }

    displayBenchmarkResults(data) {
        this.hideLoading();
        this.showResults();
        this.showPerformanceMetrics(data);

        // Display mock recommendations for demo
        const mockRecommendations = {
            tags_recommendation: [
                { tag: 'Technology', score: 0.95 },
                { tag: 'AI', score: 0.92 },
                { tag: 'Machine Learning', score: 0.89 },
                { tag: 'Data Science', score: 0.85 },
                { tag: 'Programming', score: 0.82 }
            ],
            articles_recommendation: [
                {
                    id: 'article_001',
                    score: 0.94,
                    abstract: 'Latest advances in artificial intelligence and machine learning applications in modern technology.'
                },
                {
                    id: 'article_002',
                    score: 0.91,
                    abstract: 'Comprehensive guide to data science methodologies and best practices for industry professionals.'
                },
                {
                    id: 'article_003',
                    score: 0.88,
                    abstract: 'Exploring the future of programming languages and development frameworks in 2024.'
                }
            ]
        };

        this.displayRecommendations(mockRecommendations);
    }

    createTagElement(tag) {
        const tagDiv = document.createElement('div');
        tagDiv.className = 'tag-item';
        
        // Add wildcard indicator if it's a wildcard tag
        if (tag.wildcard) {
            tagDiv.classList.add('wildcard-tag');
        }
        
        const tagName = document.createElement('div');
        tagName.className = 'tag-name';
        tagName.textContent = tag.tag;
        
        const tagScore = document.createElement('div');
        tagScore.className = 'tag-score';
        tagScore.textContent = `${tag.score.toFixed(1)}`;
        
        const tagType = document.createElement('div');
        tagType.className = 'tag-type';
        tagType.textContent = tag.wildcard ? 'Trending' : 'Personalized';
        
        tagDiv.appendChild(tagName);
        tagDiv.appendChild(tagScore);
        tagDiv.appendChild(tagType);
        
        return tagDiv;
    }

    createArticleElement(article) {
        const articleDiv = document.createElement('div');
        articleDiv.className = 'article-item';
        
        // Add wildcard indicator if it's a wildcard article
        if (article.wildcard) {
            articleDiv.classList.add('wildcard-article');
        }
        
        const header = document.createElement('div');
        header.className = 'article-header';
        
        const articleId = document.createElement('span');
        articleId.className = 'article-id';
        articleId.textContent = article.id;
        
        const articleScore = document.createElement('span');
        articleScore.className = 'article-score';
        articleScore.textContent = `${article.score.toFixed(1)}`;
        
        const articleType = document.createElement('span');
        articleType.className = 'article-type';
        articleType.textContent = article.wildcard ? 'Trending' : 'Personalized';
        articleType.style.background = article.wildcard ? '#ed8936' : '#4299e1';
        
        header.appendChild(articleId);
        header.appendChild(articleType);
        header.appendChild(articleScore);
        
        const abstract = document.createElement('div');
        abstract.className = 'article-abstract';
        abstract.textContent = article.abstract || 'No abstract available';
        
        articleDiv.appendChild(header);
        articleDiv.appendChild(abstract);
        
        return articleDiv;
    }

    showPerformanceMetrics(data) {
        const metricsCard = document.getElementById('performanceMetrics');
        metricsCard.classList.remove('hidden');
        
        document.getElementById('totalTime').textContent = `${data.total_time.toFixed(2)}s`;
        document.getElementById('articlesTime').textContent = `${data.articles_fetch_time.toFixed(2)}s`;
        document.getElementById('articlesCount').textContent = data.articles_count || 'N/A';
        
        const cacheStats = data.cache_stats || {};
        const cacheHitRate = cacheStats.total_entries > 0 
            ? ((cacheStats.valid_entries / cacheStats.total_entries) * 100).toFixed(1)
            : '0';
        document.getElementById('cacheHitRate').textContent = `${cacheHitRate}%`;
    }

    showLoading() {
        document.getElementById('loadingSection').classList.remove('hidden');
        document.getElementById('generateBtn').disabled = true;
        document.getElementById('benchmarkBtn').disabled = true;
    }

    hideLoading() {
        document.getElementById('loadingSection').classList.add('hidden');
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('benchmarkBtn').disabled = false;
    }

    showResults() {
        document.getElementById('resultsSection').classList.remove('hidden');
    }

    hideResults() {
        document.getElementById('resultsSection').classList.add('hidden');
    }

    showPerformanceMetrics(data) {
        const metricsCard = document.getElementById('performanceMetrics');
        metricsCard.classList.remove('hidden');
        
        document.getElementById('totalTime').textContent = `${data.total_time.toFixed(2)}s`;
        document.getElementById('articlesTime').textContent = `${data.articles_fetch_time.toFixed(2)}s`;
        document.getElementById('articlesCount').textContent = data.articles_count || 'N/A';
        
        const cacheStats = data.cache_stats || {};
        const cacheHitRate = cacheStats.total_entries > 0 
            ? ((cacheStats.valid_entries / cacheStats.total_entries) * 100).toFixed(1)
            : '0';
        document.getElementById('cacheHitRate').textContent = `${cacheHitRate}%`;
    }

    hidePerformanceMetrics() {
        document.getElementById('performanceMetrics').classList.add('hidden');
    }

    showRecentMessage() {
        document.getElementById('recentSection').classList.remove('hidden');
    }

    hideRecentMessage() {
        document.getElementById('recentSection').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorSection').classList.remove('hidden');
        this.hideLoading();
    }

    hideError() {
        document.getElementById('errorSection').classList.add('hidden');
    }

    // Simulate loading steps for better UX
    simulateLoadingSteps() {
        const steps = document.querySelectorAll('.step');
        let currentStep = 0;

        const stepInterval = setInterval(() => {
            if (currentStep < steps.length) {
                steps[currentStep].classList.add('active');
                currentStep++;
            } else {
                clearInterval(stepInterval);
            }
        }, 800);
    }
}

// Initialize the demo when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RecommendationDemo();
    
    // Add some interactive effects
    const cards = document.querySelectorAll('.card, .feature-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });

    // Add typing effect to header
    const headerTitle = document.querySelector('.header-content h1');
    const originalText = headerTitle.textContent;
    headerTitle.textContent = '';
    
    let i = 0;
    const typeInterval = setInterval(() => {
        if (i < originalText.length) {
            headerTitle.textContent += originalText.charAt(i);
            i++;
        } else {
            clearInterval(typeInterval);
        }
    }, 100);
});

// Utility function to format numbers
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// Utility function to format percentages
function formatPercentage(num) {
    return `${(num * 100).toFixed(1)}%`;
}
