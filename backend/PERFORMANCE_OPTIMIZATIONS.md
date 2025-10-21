# Performance Optimizations for Tag Recommendations

## Tổng quan

Hệ thống recommendation đã được tối ưu hóa để cải thiện hiệu suất khi lấy dữ liệu articles cho việc tạo recommendation. Các tối ưu hóa chính tập trung vào việc giảm số lượng database queries và tăng tốc độ truy xuất dữ liệu.

## Các tối ưu hóa đã thực hiện

### 1. Batch Query thay vì N Individual Queries

**Vấn đề trước đây:**
- `get_articles_by_ids()` thực hiện N queries riêng lẻ cho mỗi article ID
- Với 20 articles (10 liked + 10 bookmarked), hệ thống thực hiện 20 queries riêng lẻ
- Mỗi query có overhead của network round-trip

**Giải pháp:**
```sql
-- Thay vì 20 queries riêng lẻ:
SELECT * FROM c WHERE c.id = 'article1'
SELECT * FROM c WHERE c.id = 'article2'
...
SELECT * FROM c WHERE c.id = 'article20'

-- Chỉ cần 1 query duy nhất:
SELECT c.id, c.title, c.abstract, c.tags, c.status, c.is_active, c.created_at 
FROM c WHERE c.id IN ('article1', 'article2', ..., 'article20')
```

**Cải thiện hiệu suất:** 5-10x nhanh hơn tùy thuộc vào số lượng articles

### 2. In-Memory Caching Layer

**Tính năng:**
- Cache articles trong memory với TTL 5 phút
- Tự động kiểm tra cache trước khi query database
- Chỉ query những articles chưa có trong cache hoặc đã hết hạn

**Lợi ích:**
- Giảm database load đáng kể cho các requests lặp lại
- Tăng tốc độ response cho users có articles trùng lặp
- Giảm chi phí CosmosDB RU (Request Units)

### 3. Optimized Query Structure

**Tối ưu hóa:**
- Chỉ SELECT các fields cần thiết thay vì `SELECT *`
- Giảm network bandwidth và parsing time
- Fields được lấy: `id`, `title`, `abstract`, `tags`, `status`, `is_active`, `created_at`

### 4. Performance Monitoring

**Tính năng:**
- Thêm timing logs cho tất cả operations
- Benchmark method để so sánh hiệu suất các approaches
- Cache statistics để monitor cache hit rate

## Cách sử dụng

### Sử dụng method tối ưu hóa mới:

```python
# Thay vì:
articles = cosmos_helper.get_articles_by_ids(article_ids)

# Sử dụng:
articles = cosmos_helper.get_articles_by_ids_optimized(article_ids)
```

### Monitor hiệu suất:

```python
# Xem cache statistics
cache_stats = cosmos_helper.get_cache_stats()
print(f"Cache hit rate: {cache_stats['valid_entries']}/{cache_stats['total_entries']}")

# Benchmark performance
benchmark_results = cosmos_helper.benchmark_article_retrieval(test_article_ids)
print(f"Speedup: {benchmark_results['speedup_optimized_vs_original']}x")
```

### Clear cache khi cần:

```python
cosmos_helper.clear_article_cache()
```

## Kết quả mong đợi

### Trước tối ưu hóa:
- 20 articles = 20 database queries
- Thời gian: ~2-5 giây
- CosmosDB RU: ~40-100 RUs

### Sau tối ưu hóa:
- 20 articles = 1 database query (lần đầu), 0 queries (cache hit)
- Thời gian: ~0.2-0.5 giây (lần đầu), ~0.01 giây (cache hit)
- CosmosDB RU: ~5-10 RUs (lần đầu), 0 RUs (cache hit)

### Tổng cải thiện:
- **Tốc độ:** 5-10x nhanh hơn
- **Chi phí:** 80-90% giảm CosmosDB RU
- **Scalability:** Có thể xử lý nhiều users đồng thời hơn

## Cấu hình

### Cache TTL:
```python
# Trong CosmosHelper.__init__()
self._cache_ttl = 300  # 5 phút
```

### Logging Level:
```python
# Để xem performance logs
logging.getLogger(__name__).setLevel(logging.INFO)
```

## Lưu ý

1. **Memory Usage:** Cache sử dụng memory, cần monitor memory usage trong production
2. **Cache Invalidation:** Cache tự động expire sau 5 phút, có thể điều chỉnh TTL
3. **Fallback:** Nếu optimized method fail, sẽ tự động fallback về method cũ
4. **Thread Safety:** Cache hiện tại không thread-safe, cần cải thiện nếu sử dụng multi-threading

## Tương lai

Các tối ưu hóa có thể thực hiện thêm:
1. **Redis Cache:** Thay thế in-memory cache bằng Redis cho distributed caching
2. **Connection Pooling:** Tối ưu hóa CosmosDB connection pooling
3. **Async Operations:** Sử dụng async/await cho non-blocking operations
4. **Data Preloading:** Preload popular articles vào cache
5. **Query Optimization:** Sử dụng CosmosDB indexing strategies
