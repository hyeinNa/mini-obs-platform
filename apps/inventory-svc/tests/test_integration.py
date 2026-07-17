"""Integration tests for inventory-svc — tests the FastAPI app with TestClient."""
import pytest
from fastapi.testclient import TestClient

# conftest.py installs the no-op otel_setup stub before this import runs
from main import app, _inventory

SEED_ITEM_ID = "item-001"
SEED_ITEM_ID_B = "item-002"
SEED_STOCK_A = 100
SEED_STOCK_B = 50


@pytest.fixture(autouse=True)
def reset_inventory():
    """Restore inventory to seed state between tests."""
    _inventory.clear()
    _inventory.update({
        SEED_ITEM_ID: {"item_id": SEED_ITEM_ID, "name": "Widget A", "stock": SEED_STOCK_A},
        SEED_ITEM_ID_B: {"item_id": SEED_ITEM_ID_B, "name": "Widget B", "stock": SEED_STOCK_B},
        "item-003": {"item_id": "item-003", "name": "Widget C", "stock": 200},
    })
    yield
    _inventory.clear()


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
    assert response.json() == {"status": "ok", "service": "inventory-svc"}


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------

def test_metrics_endpoint_returns_prometheus_text(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "inventory_stock_level" in response.text


# ---------------------------------------------------------------------------
# GET /items
# ---------------------------------------------------------------------------

def test_list_items_returns_all_seed_items(client: TestClient) -> None:
    response = client.get("/items")
    assert response.status_code == 200
    items = response.json()["items"]
    item_ids = {item["item_id"] for item in items}
    assert SEED_ITEM_ID in item_ids
    assert SEED_ITEM_ID_B in item_ids


def test_list_items_contains_stock_field(client: TestClient) -> None:
    response = client.get("/items")
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "stock" in item


# ---------------------------------------------------------------------------
# PUT /items/{item_id}/stock
# ---------------------------------------------------------------------------

def test_deduct_stock_success(client: TestClient) -> None:
    deduction = -2
    response = client.put(
        f"/items/{SEED_ITEM_ID}/stock",
        json={"delta": deduction},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previous_stock"] == SEED_STOCK_A
    assert body["current_stock"] == SEED_STOCK_A + deduction
    assert body["delta"] == deduction


def test_deduct_stock_updates_in_memory_store(client: TestClient) -> None:
    deduction = -5
    client.put(f"/items/{SEED_ITEM_ID}/stock", json={"delta": deduction})
    assert _inventory[SEED_ITEM_ID]["stock"] == SEED_STOCK_A + deduction


def test_restock_increases_stock(client: TestClient) -> None:
    increase = 20
    response = client.put(f"/items/{SEED_ITEM_ID}/stock", json={"delta": increase})
    assert response.status_code == 200
    assert response.json()["current_stock"] == SEED_STOCK_A + increase


def test_deduct_stock_to_exactly_zero(client: TestClient) -> None:
    """Depleting to exactly 0 must succeed."""
    response = client.put(
        f"/items/{SEED_ITEM_ID}/stock",
        json={"delta": -SEED_STOCK_A},
    )
    assert response.status_code == 200
    assert response.json()["current_stock"] == 0


def test_insufficient_stock_returns_409(client: TestClient) -> None:
    over_deduction = -(SEED_STOCK_A + 1)
    response = client.put(
        f"/items/{SEED_ITEM_ID}/stock",
        json={"delta": over_deduction},
    )
    assert response.status_code == 409


def test_zero_delta_returns_400(client: TestClient) -> None:
    response = client.put(f"/items/{SEED_ITEM_ID}/stock", json={"delta": 0})
    assert response.status_code == 400


def test_unknown_item_returns_404(client: TestClient) -> None:
    response = client.put("/items/item-nonexistent/stock", json={"delta": -1})
    assert response.status_code == 404


def test_missing_delta_field_returns_422(client: TestClient) -> None:
    response = client.put(f"/items/{SEED_ITEM_ID}/stock", json={})
    assert response.status_code == 422
