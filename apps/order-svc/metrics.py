"""Prometheus custom metrics for order-svc."""
from prometheus_client import Counter, Histogram

DURATION_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code", "service"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "service"],
    buckets=DURATION_BUCKETS,
)

orders_created_total = Counter(
    "orders_created_total",
    "Total number of orders created",
)

order_processing_duration_seconds = Histogram(
    "order_processing_duration_seconds",
    "Order processing time distribution",
    buckets=DURATION_BUCKETS,
)
