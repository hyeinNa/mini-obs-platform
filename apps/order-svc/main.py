"""order-svc — FastAPI order processing service with OTel instrumentation."""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
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
    order_processing_duration_seconds,
    orders_created_total,
)
from otel_setup import setup_otel

# ---------------------------------------------------------------------------
# Logging — structured JSON output so Fluent Bit can parse trace_id/span_id
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "service": os.environ.get("OTEL_SERVICE_NAME", "order-svc"),
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
# OTel setup (must happen before app instrumentation)
# ---------------------------------------------------------------------------
setup_otel()

app = FastAPI(title="order-svc", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer("order-svc")

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_orders: dict[str, dict[str, Any]] = {}

INVENTORY_SVC_URL = os.environ.get(
    "INVENTORY_SVC_URL",
    "http://localhost:8082",
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class OrderRequest(BaseModel):
    item_id: str
    quantity: int = Field(..., ge=1, description="Order quantity (minimum 1)")
    customer_id: str = "anonymous"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return ""


async def _deduct_stock(item_id: str, quantity: int) -> None:
    """Call inventory-svc PUT /items/{item_id}/stock. Raises HTTPException on failure."""
    from opentelemetry.propagate import inject

    headers: dict[str, str] = {}
    inject(headers)

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.put(
                f"{INVENTORY_SVC_URL}/items/{item_id}/stock",
                json={"delta": -quantity},
                headers=headers,
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="inventory-svc unreachable")
        except httpx.TimeoutException:
            raise HTTPException(status_code=502, detail="inventory-svc timeout")

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"item {item_id} not found")
    if resp.status_code == 409:
        raise HTTPException(status_code=409, detail="insufficient stock")
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="inventory-svc error")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/orders", status_code=201)
async def create_order(body: OrderRequest, request: Request) -> JSONResponse:
    start = time.perf_counter()

    with tracer.start_as_current_span(
        "create_order",
        context=extract(dict(request.headers)),
    ) as span:
        orders_created_total.inc()

        with order_processing_duration_seconds.time():
            await _deduct_stock(body.item_id, body.quantity)

            order_id = f"ord-{uuid.uuid4()}"
            created_at = datetime.now(timezone.utc).isoformat()
            order: dict[str, Any] = {
                "order_id": order_id,
                "item_id": body.item_id,
                "quantity": body.quantity,
                "customer_id": body.customer_id,
                "status": "created",
                "created_at": created_at,
            }
            _orders[order_id] = order

        trace_id = _get_trace_id()
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.item_id", body.item_id)
        span.set_attribute("order.quantity", body.quantity)

        elapsed = time.perf_counter() - start
        http_requests_total.labels(
            method="POST", path="/orders", status_code="201", service="order-svc"
        ).inc()
        http_request_duration_seconds.labels(
            method="POST", path="/orders", service="order-svc"
        ).observe(elapsed)

        logger.info("order created: %s", order_id)

        return JSONResponse(
            status_code=201,
            content={**order, "trace_id": trace_id},
        )


@app.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request) -> JSONResponse:
    with tracer.start_as_current_span(
        "get_order",
        context=extract(dict(request.headers)),
    ) as span:
        span.set_attribute("order.id", order_id)

        order = _orders.get(order_id)
        if order is None:
            http_requests_total.labels(
                method="GET",
                path="/orders/{order_id}",
                status_code="404",
                service="order-svc",
            ).inc()
            raise HTTPException(status_code=404, detail="order not found")

        http_requests_total.labels(
            method="GET",
            path="/orders/{order_id}",
            status_code="200",
            service="order-svc",
        ).inc()
        return JSONResponse(content=order)


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "service": "order-svc"})
