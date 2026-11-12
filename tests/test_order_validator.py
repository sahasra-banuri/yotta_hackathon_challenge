import pytest

from datetime import date
from decimal import Decimal

from backend.processing.order_validator import validate_order


@pytest.fixture
def valid_order():
    return {
        "order_id": "ORD001",
        "order_date": "2026-11-12",
        "order_status": "PENDING",
        "items": [
            {
                "product_id": "P001",
                "quantity": 2,
                "unit_price": "100.50"
            },
            {
                "product_id": "P002",
                "quantity": 1,
                "unit_price": "250.00"
            }
        ]
    }


@pytest.fixture
def valid_product_ids():
    return {"P001", "P002", "P003"}


def test_valid_order(valid_order, valid_product_ids):
    seen_ids = set()

    result, errors = validate_order(
        valid_order,
        seen_ids,
        valid_product_ids
    )

    assert errors == []
    assert result is not None

    assert result["order_id"] == "ORD001"
    assert result["order_date"] == date(2026, 11, 12)
    assert result["order_status"] == "PENDING"

    assert result["total_amount"] == Decimal("451.00")
    assert len(result["items"]) == 2

    assert "ORD001" in seen_ids


def test_order_item_totals(valid_order, valid_product_ids):
    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert errors == []

    assert result["items"][0]["item_total"] == Decimal("201.00")
    assert result["items"][1]["item_total"] == Decimal("250.00")


def test_order_status_normalization(valid_order, valid_product_ids):
    valid_order["order_status"] = " pending "

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert errors == []
    assert result["order_status"] == "PENDING"


@pytest.mark.parametrize(
    "field,value,expected_error",
    [
        ("order_id", "", "Order ID is missing."),
        ("order_date", "invalid-date", "Invalid order date."),
        ("order_status", "UNKNOWN", "Invalid order status: UNKNOWN"),
        ("items", [], "Order must contain at least one item."),
        ("items", None, "Order must contain at least one item."),
    ]
)
def test_invalid_order_fields(
    valid_order,
    valid_product_ids,
    field,
    value,
    expected_error
):
    valid_order[field] = value

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert result is None
    assert expected_error in errors


def test_duplicate_order_id(valid_order, valid_product_ids):
    seen_ids = {"ORD001"}

    result, errors = validate_order(
        valid_order,
        seen_ids,
        valid_product_ids
    )

    assert result is None
    assert "Duplicate order ID: ORD001" in errors


def test_unknown_product_reference(valid_order):
    valid_order["items"][0]["product_id"] = "UNKNOWN"

    result, errors = validate_order(
        valid_order,
        set(),
        {"P001", "P002"}
    )

    assert result is None
    assert any(
        "Unknown product ID: UNKNOWN" in error
        or "Unknown product ID or inactive product: UNKNOWN" in error
        for error in errors
    )


def test_duplicate_product_within_order(valid_order, valid_product_ids):
    valid_order["items"][1]["product_id"] = "P001"

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert result is None
    assert any(
        "Duplicate product in order: P001" in error
        for error in errors
    )


@pytest.mark.parametrize(
    "field,value,expected_error",
    [
        ("quantity", 0, "Quantity must be greater than zero."),
        ("quantity", -2, "Quantity must be greater than zero."),
        ("quantity", 1.5, "Quantity must be a positive integer."),
        ("quantity", True, "Quantity must be a positive integer."),
        ("unit_price", "-10", "Unit price must be greater than zero."),
        ("unit_price", "invalid", "Unit price must be a valid number."),
        ("unit_price", "NaN", "Unit price must be a finite number."),
    ]
)
def test_invalid_order_items(
    valid_order,
    valid_product_ids,
    field,
    value,
    expected_error
):
    valid_order["items"][0][field] = value

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert result is None
    assert any(
        expected_error in error
        for error in errors
    )


def test_invalid_item_structure(valid_order, valid_product_ids):
    valid_order["items"][0] = "invalid-item"

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert result is None
    assert "Item 1: Invalid item structure." in errors


def test_invalid_record_does_not_reserve_order_id(
    valid_order,
    valid_product_ids
):
    seen_ids = set()

    invalid_order = valid_order.copy()
    invalid_order["order_date"] = "invalid-date"

    result, errors = validate_order(
        invalid_order,
        seen_ids,
        valid_product_ids
    )

    assert result is None
    assert "ORD001" not in seen_ids

    result, errors = validate_order(
        valid_order,
        seen_ids,
        valid_product_ids
    )

    assert errors == []
    assert result is not None
    assert "ORD001" in seen_ids


def test_order_is_rejected_if_any_item_is_invalid(
    valid_order,
    valid_product_ids
):
    valid_order["items"].append({
        "product_id": "UNKNOWN",
        "quantity": 1,
        "unit_price": "100"
    })

    result, errors = validate_order(
        valid_order,
        set(),
        valid_product_ids
    )

    assert result is None
    assert any(
        "Unknown product ID" in error
        for error in errors
    )