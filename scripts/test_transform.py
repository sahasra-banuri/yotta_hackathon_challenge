from datetime import date
from decimal import Decimal

from backend.processing.transform import (
    transform_product,
    transform_order
)


def test_product_transformation():

    product = {
        "product_id": "P001",
        "product_name": "Laptop",
        "category": "Electronics",
        "price": Decimal("55000"),
        "stock_quantity": 10,
        "status": "ACTIVE"
    }

    result = transform_product(product)

    assert result["product_id"] == "P001"
    assert result["price"] == Decimal("55000")

    print("Product transformation: PASSED")


def test_order_transformation():

    order = {
        "order_id": "ORD001",
        "order_date": date(2026, 11, 10),
        "order_status": "COMPLETED",
        "total_amount": Decimal("1300"),

        "items": [
            {
                "product_id": "P001",
                "quantity": 2,
                "unit_price": Decimal("500"),
                "item_total": Decimal("1000")
            },
            {
                "product_id": "P002",
                "quantity": 1,
                "unit_price": Decimal("300"),
                "item_total": Decimal("300")
            }
        ]
    }

    order_row, item_rows = transform_order(order)

    assert order_row["order_id"] == "ORD001"
    assert order_row["total_amount"] == Decimal("1300")

    assert len(item_rows) == 2

    assert item_rows[0]["order_item_id"] == "ORD001-ITEM001"
    assert item_rows[1]["order_item_id"] == "ORD001-ITEM002"

    assert item_rows[0]["item_total"] == Decimal("1000")
    assert item_rows[1]["item_total"] == Decimal("300")

    print("Order transformation: PASSED")


if __name__ == "__main__":
    test_product_transformation()
    test_order_transformation()

    print("\nAll transformation tests passed.")
