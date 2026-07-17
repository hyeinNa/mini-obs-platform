"""Prometheus custom metrics for inventory-svc."""
from prometheus_client import Counter, Gauge, Histogram

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

inventory_stock_level = Gauge(
    "inventory_stock_level",
    "Current stock level per item",
    ["item_id"],
)
