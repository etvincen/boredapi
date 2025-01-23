from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics for content processing
CONTENT_PROCESSED = Counter(
    'content_processed_total',
    'Number of content items processed',
    ['content_type', 'status']
)

PROCESSING_TIME = Histogram(
    'content_processing_seconds',
    'Time spent processing content',
    ['content_type']
)

# Metrics for API endpoints
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['endpoint', 'method', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

# Metrics for storage systems
ELASTICSEARCH_OPERATIONS = Counter(
    'elasticsearch_operations_total',
    'Number of Elasticsearch operations',
    ['operation', 'status']
)

POSTGRES_OPERATIONS = Counter(
    'postgres_operations_total',
    'Number of PostgreSQL operations',
    ['operation', 'status']
)

# System metrics
ACTIVE_MIGRATIONS = Gauge(
    'active_migrations',
    'Number of currently running migrations'
)

QUEUE_SIZE = Gauge(
    'migration_queue_size',
    'Number of items in migration queue'
)

class MetricsMiddleware:
    async def __call__(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        
        REQUEST_COUNT.labels(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            endpoint=request.url.path
        ).observe(time.time() - start_time)
        
        return response 