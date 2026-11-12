import pytest

from datetime import date
from decimal import Decimal

from backend.processing.transform import (
    transform_product,
    transform_order
)


def test_transform_product():
    product = {
        "product_id": "P001",
        "product_name": "Laptop",
        "category": "Electronics",
        "price": Decimal("75000.50"),
        "stock_quantity": 10,
        "status": "ACTIVE"
    }

    result = transform_product(product)

    assert result == product


def test_transform_order():
    order = {
        "order_id": "ORD001",
        "order_date": date(2026, 11, 12),
        "order_status": "PENDING",
        "total_amount": Decimal("451.00"),
        "items": [
            {
                "product_id": "P001",
                "quantity": 2,
                "unit_price": Decimal("100.50"),
                "item_total": Decimal("201.00")
            },
            {
                "product_id": "P002",
                "quantity": 1,
                "unit_price": Decimal("250.00"),
                "item_total": Decimal("250.00")
            }
        ]
    }

    order_row, item_rows = transform_order(order)

    assert order_row["order_id"] == "ORD001"
    assert order_row["order_date"] == date(2026, 11, 12)
    assert order_row["order_status"] == "PENDING"
    assert order_row["total_amount"] == Decimal("451.00")

    assert len(item_rows) == 2


def test_transform_order_item_ids_are_generated():
    order = {
        "order_id": "ORD100",
        "order_date": date(2026, 11, 12),
        "order_status": "CONFIRMED",
        "total_amount": Decimal("300"),
        "items": [
            {
                "product_id": "P001",
                "quantity": 1,
                "unit_price": Decimal("100"),
                "item_total": Decimal("100")
            },
            {
                "product_id": "P002",
                "quantity": 2,
                "unit_price": Decimal("100"),
                "item_total": Decimal("200")
            }
        ]
    }

    _, item_rows = transform_order(order)

    assert item_rows[0]["order_item_id"] == "ORD100-ITEM001"
    assert item_rows[1]["order_item_id"] == "ORD100-ITEM002"


def test_transform_order_preserves_item_relationships():
    order = {
        "order_id": "ORD200",
        "order_date": date(2026, 11, 12),
        "order_status": "PENDING",
        "total_amount": Decimal("150"),
        "items": [
            {
                "product_id": "P003",
                "quantity": 3,
                "unit_price": Decimal("50"),
                "item_total": Decimal("150")
            }
        ]
    }

    order_row, item_rows = transform_order(order)

    assert item_rows[0]["order_id"] == order_row["order_id"]
    assert item_rows[0]["product_id"] == "P003"
    assert item_rows[0]["quantity"] == 3
    assert item_rows[0]["item_total"] == Decimal("150")


def test_transform_order_with_no_items():
    order = {
        "order_id": "ORD300",
        "order_date": date(2026, 11, 12),
        "order_status": "PENDING",
        "total_amount": Decimal("0"),
        "items": []
    }

    order_row, item_rows = transform_order(order)

    assert order_row["order_id"] == "ORD300"
    assert item_rows == []