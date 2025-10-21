# Tag Recommendation System

Hệ thống đề xuất tags sử dụng Azure AI Foundry để phân tích sở thích người dùng và đề xuất tags phù hợp dựa trên lịch sử tương tác với articles.

## Cấu trúc thư mục

```
tags/
├── tags_recommendation.py    # File chính để chạy hệ thống
├── helper/                   # Các module helper
│   ├── __init__.py
│   ├── cosmos_helper.py      # Kết nối và thao tác với CosmosDB
│   ├── azure_openai_helper.py # Gọi Azure OpenAI API
│   ├── tag_analyzer.py       # Phân tích sở thích người dùng
│   ├── user_manager.py       # Quản lý operations liên quan đến user
│   └── recommendation_manager.py # Quản lý logic recommendation
├── requirements.txt          # Dependencies
└── README.md                # Hướng dẫn sử dụng
```

## Cài đặt

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Tạo file `.env` từ `.env.sample` và điền thông tin cấu hình:
```bash
cp .env.sample .env
```

3. Cập nhật các biến môi trường trong file `.env`:
   - `COSMOS_ENDPOINT`: Endpoint của CosmosDB
   - `COSMOS_KEY`: Primary key của CosmosDB
   - `AZURE_OPENAI_ENDPOINT`: Endpoint của Azure OpenAI
   - `AZURE_OPENAI_CHAT_API_KEY`: API key cho chat completion
   - Các biến khác theo cấu hình của bạn

## Sử dụng

### Chạy cho một user cụ thể:
```bash
python tags_recommendation.py --user-id "d2ac2d2d-13d3-481d-bac5-f99f5a0c8620"
```

### Chạy batch cho nhiều users:
```bash
python tags_recommendation.py --batch
```

### Force update (bỏ qua kiểm tra thời gian cập nhật gần đây):
```bash
python tags_recommendation.py --user-id "user-id" --force
```

### Sử dụng trong code:
```python
from tags_recommendation import TagRecommendationEngine

# Khởi tạo engine
engine = TagRecommendationEngine()

# Tạo recommendations cho một user
result = engine.generate_recommendations_for_user("user-id")

# Tạo recommendations cho nhiều users
results = engine.generate_recommendations_batch(["user1", "user2"])

# Tùy chỉnh tham số recommendation
result = engine.generate_recommendations_for_user(
    "user-id", 
    tag_count=20, 
    article_count=25,
    candidate_limit=500
)
```

## Cách hoạt động (LLM-only)

1. **Đọc lịch sử người dùng**: Lấy các bài viết user từng tương tác (abstract, tags) từ CosmosDB.
2. **Tạo pool ứng viên**: Lấy danh sách bài viết ứng viên (published, active) làm đầu vào cho LLM.
3. **Gọi LLM duy nhất**: Truyền lịch sử và pool ứng viên, LLM trả về:
   - 15 tags phù hợp + 5 tags wildcard (trending/đa dạng hóa), tổng 20.
   - 15 articles phù hợp + 5 articles wildcard (từ pool), tổng 20.
4. **Ghi đè dữ liệu**: Cập nhật `tags_recommendation`, `articles_recommendation`, `id_articles_for_recommendation` trong document user.

## Tính năng

- **Thông minh**: Sử dụng LLM để hiểu context và đưa ra đề xuất chính xác
- **Hiệu quả**: Chỉ cập nhật khi cần thiết (tránh cập nhật quá thường xuyên)
- **Linh hoạt**: Hỗ trợ cả single user và batch processing
- **Robust**: Có error handling và logging chi tiết
- **Scalable**: Có thể xử lý nhiều users đồng thời
- **Modular**: Code được tổ chức thành các modules riêng biệt, dễ maintain và extend
- **Configurable**: Có thể tùy chỉnh số lượng recommendations và các tham số khác

## Output format

Kết quả recommendations được lưu trong user document với format:
```json
{
  "tags_recommendation": [
    {"tag": "ai", "score": 5.0},
    {"tag": "machine-learning", "score": 4.5}
  ],
  "articles_recommendation": [
    {"id": "article-id", "score": 0.85}
  ],
  "id_articles_for_recommendation": ["article-id-1", "article-id-2"],
  "recommendations_updated_at": "2025-01-01T00:00:00.000000",
  "time_stamp_recommend": 1735689600
}
```

## Lưu ý

- Hệ thống sẽ tự động skip update nếu recommendations đã được cập nhật trong vòng 24 giờ
- Sử dụng `--force` để bỏ qua kiểm tra này
- Đảm bảo có đủ quyền truy cập CosmosDB và Azure OpenAI
- Monitor logs để theo dõi quá trình xử lý
