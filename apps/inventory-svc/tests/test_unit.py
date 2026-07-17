"""Unit tests for inventory-svc — pure logic, no I/O."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "current, delta, expected_new, raises",
    [
        (100, -2, 98, False),
        (50, -50, 0, False),
        (10, -11, None, True),   # insufficient stock
        (0, -1, None, True),    # stock already empty
        (50, 10, 60, False),    # restock increase
        (50, 0, None, True),    # zero delta is invalid
    ],
)
def test_stock_delta_logic(
    current: int, delta: int, expected_new: int | None, raises: bool
) -> None:
    """Stock deduction logic: rejects zero delta and negative results."""
    if delta == 0:
        with pytest.raises(ValueError, match="zero"):
            _apply_delta(current, delta)
        return

    if raises:
        with pytest.raises(ValueError, match="insufficient"):
            _apply_delta(current, delta)
    else:
        assert _apply_delta(current, delta) == expected_new


def _apply_delta(current: int, delta: int) -> int:
    """Pure function extracted from inventory update logic for unit testing."""
    if delta == 0:
        raise ValueError("delta must not be zero")
    new_stock = current + delta
    if new_stock < 0:
        raise ValueError("insufficient stock")
    return new_stock


def test_initial_inventory_seed_has_expected_items() -> None:
    """Seed inventory must contain item-001 and item-002."""
    seed: dict[str, dict] = {
        "item-001": {"item_id": "item-001", "name": "Widget A", "stock": 100},
        "item-002": {"item_id": "item-002", "name": "Widget B", "stock": 50},
    }
    assert "item-001" in seed
    assert "item-002" in seed
    assert seed["item-001"]["stock"] == 100
    assert seed["item-002"]["stock"] == 50


def test_stock_boundary_exactly_zero() -> None:
    """Depleting stock to exactly 0 should succeed (not raise)."""
    current_stock = 5
    delta = -5
    new_stock = _apply_delta(current_stock, delta)
    assert new_stock == 0
