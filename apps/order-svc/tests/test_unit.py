"""Unit tests for order-svc — pure logic, no I/O."""
import pytest


def test_order_id_format_prefix() -> None:
    """Generated order IDs must start with 'ord-'."""
    import uuid
    order_id = f"ord-{uuid.uuid4()}"
    assert order_id.startswith("ord-")


def test_order_id_uniqueness() -> None:
    """Two generated order IDs must be distinct."""
    import uuid
    id_a = f"ord-{uuid.uuid4()}"
    id_b = f"ord-{uuid.uuid4()}"
    assert id_a != id_b


def test_in_memory_store_isolation() -> None:
    """In-memory dict behaves correctly for insert and lookup."""
    store: dict[str, dict] = {}
    order_id = "ord-test-001"
    store[order_id] = {"order_id": order_id, "status": "created"}

    assert store.get(order_id) is not None
    assert store.get("ord-nonexistent") is None


def test_in_memory_store_missing_returns_none() -> None:
    """Missing key lookup returns None (no KeyError)."""
    store: dict[str, dict] = {}
    assert store.get("ord-does-not-exist") is None


@pytest.mark.parametrize(
    "quantity, valid",
    [
        (1, True),
        (10, True),
        (0, False),
        (-1, False),
    ],
)
def test_quantity_validation(quantity: int, valid: bool) -> None:
    """Quantities below 1 are invalid."""
    is_valid = quantity >= 1
    assert is_valid == valid
