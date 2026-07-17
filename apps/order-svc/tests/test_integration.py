"""Integration tests for order-svc — tests the FastAPI app with httpx.AsyncClient.

inventory-svc calls are mocked via httpx transport so these tests run without
a live inventory-svc instance.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# conftest.py installs the no-op otel_setup stub before this import runs
from main import app, _orders


@pytest.fixture(autouse=True)
def clear_orders():
    """Reset in-memory store between tests."""
    _orders.clear()
    yield
    _orders.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "order-svc"}


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

def test_metrics_endpoint_returns_prometheus_text(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "orders_created_total" in response.text


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------

def _mock_inventory_success(quantity: int) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "item_id": "item-001",
            "previous_stock": 100,
            "current_stock": 100 - quantity,
            "delta": -quantity,
        },
    )


def test_create_order_returns_201(client: TestClient) -> None:
    order_payload = {"item_id": "item-001", "quantity": 2, "customer_id": "cust-test"}

    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.put = AsyncMock(return_value=_mock_inventory_success(2))
        mock_client_cls.return_value = mock_instance

        response = client.post("/orders", json=order_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["item_id"] == "item-001"
    assert body["quantity"] == 2
    assert body["status"] == "created"
    assert body["order_id"].startswith("ord-")


def test_create_order_stored_in_memory(client: TestClient) -> None:
    order_payload = {"item_id": "item-002", "quantity": 1}

    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.put = AsyncMock(return_value=_mock_inventory_success(1))
        mock_client_cls.return_value = mock_instance

        response = client.post("/orders", json=order_payload)

    assert response.status_code == 201
    order_id = response.json()["order_id"]
    assert order_id in _orders


def test_create_order_quantity_zero_returns_422(client: TestClient) -> None:
    """quantity=0 must be rejected by Pydantic validation (422)."""
    response = client.post("/orders", json={"item_id": "item-001", "quantity": 0})
    assert response.status_code == 422


def test_create_order_missing_item_id_returns_422(client: TestClient) -> None:
    response = client.post("/orders", json={"quantity": 1})
    assert response.status_code == 422


def test_create_order_inventory_insufficient_returns_409(client: TestClient) -> None:
    with patch("main.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.put = AsyncMock(
            return_value=httpx.Response(409, json={"detail": "insufficient stock"})
        )
        mock_client_cls.return_value = mock_instance

        response = client.post("/orders", json={"item_id": "item-001", "quantity": 9999})

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /orders/{order_id}
# ---------------------------------------------------------------------------

def test_get_order_returns_200_when_exists(client: TestClient) -> None:
    order_id = "ord-test-abc"
    _orders[order_id] = {
        "order_id": order_id,
        "item_id": "item-001",
        "quantity": 3,
        "status": "created",
        "created_at": "2026-03-28T10:00:00+00:00",
    }

    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_get_order_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/orders/ord-does-not-exist")
    assert response.status_code == 404
