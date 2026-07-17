"""inventory-svc — FastAPI inventory service with OTel instrumentation."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import extract
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from metrics import (
    http_request_duration_seconds,
    http_requests_total,
    inventory_stock_level,
)
from otel_setup import setup_otel

# ---------------------------------------------------------------------------
# Logging — structured JSON
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "service": os.environ.get("OTEL_SERVICE_NAME", "inventory-svc"),
            "message": record.getMessage(),
        }
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            log_record["trace_id"] = format(ctx.trace_id, "032x")
            log_record["span_id"] = format(ctx.span_id, "016x")
        return json.dumps(log_record)


logging.basicConfig(level=logging.INFO)
for handler in logging.root.handlers:
    handler.setFormatter(StructuredFormatter())

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OTel setup
# ---------------------------------------------------------------------------
setup_otel()

app = FastAPI(title="inventory-svc", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer("inventory-svc")

# ---------------------------------------------------------------------------
# In-memory inventory store (initial seed values)
# ---------------------------------------------------------------------------
_inventory: dict[str, dict[str, Any]] = {
    "item-001": {"item_id": "item-001", "name": "Widget A", "stock": 100},
    "item-002": {"item_id": "item-002", "name": "Widget B", "stock": 50},
    "item-003": {"item_id": "item-003", "name": "Widget C", "stock": 200},
}

# Initialise Gauge with seed values so /metrics shows meaningful data on start
for _item_id, _item in _inventory.items():
    inventory_stock_level.labels(item_id=_item_id).set(_item["stock"])

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StockDeltaRequest(BaseModel):
    delta: int = Field(..., description="Stock change (negative = deduct, positive = add, 0 not allowed)")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/items")
async def list_items(request: Request) -> JSONResponse:
    start = time.perf_counter()

    with tracer.start_as_current_span(
        "list_items",
        context=extract(dict(request.headers)),
    ):
        items = list(_inventory.values())

        elapsed = time.perf_counter() - start
        http_requests_total.labels(
            method="GET", path="/items", status_code="200", service="inventory-svc"
        ).inc()
        http_request_duration_seconds.labels(
            method="GET", path="/items", service="inventory-svc"
        ).observe(elapsed)

        return JSONResponse(content={"items": items})


@app.put("/items/{item_id}/stock")
async def update_stock(
    item_id: str, body: StockDeltaRequest, request: Request
) -> JSONResponse:
    start = time.perf_counter()

    with tracer.start_as_current_span(
        "update_stock",
        context=extract(dict(request.headers)),
    ) as span:
        span.set_attribute("inventory.item_id", item_id)
        span.set_attribute("inventory.delta", body.delta)

        if body.delta == 0:
            http_requests_total.labels(
                method="PUT",
                path="/items/{item_id}/stock",
                status_code="400",
                service="inventory-svc",
            ).inc()
            raise HTTPException(status_code=400, detail="delta must not be zero")

        item = _inventory.get(item_id)
        if item is None:
            http_requests_total.labels(
                method="PUT",
                path="/items/{item_id}/stock",
                status_code="404",
                service="inventory-svc",
            ).inc()
            raise HTTPException(status_code=404, detail=f"item {item_id} not found")

        previous_stock: int = item["stock"]
        new_stock = previous_stock + body.delta
        if new_stock < 0:
            http_requests_total.labels(
                method="PUT",
                path="/items/{item_id}/stock",
                status_code="409",
                service="inventory-svc",
            ).inc()
            raise HTTPException(status_code=409, detail="insufficient stock")

        item["stock"] = new_stock
        inventory_stock_level.labels(item_id=item_id).set(new_stock)

        span.set_attribute("inventory.previous_stock", previous_stock)
        span.set_attribute("inventory.current_stock", new_stock)

        elapsed = time.perf_counter() - start
        http_requests_total.labels(
            method="PUT",
            path="/items/{item_id}/stock",
            status_code="200",
            service="inventory-svc",
        ).inc()
        http_request_duration_seconds.labels(
            method="PUT", path="/items/{item_id}/stock", service="inventory-svc"
        ).observe(elapsed)

        logger.info("stock updated: %s %+d -> %d", item_id, body.delta, new_stock)

        return JSONResponse(
            content={
                "item_id": item_id,
                "previous_stock": previous_stock,
                "current_stock": new_stock,
                "delta": body.delta,
            }
        )


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": "inventory-svc"})
