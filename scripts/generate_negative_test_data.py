import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "data" / "generated"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 1. TEST PRODUCTS
# ==========================================

products = [
    {
        "product_id": "TP001",
        "product_name": "Wireless Mouse",
        "category": "Electronics",
        "price": "550.00",
        "stock_quantity": "100",
        "status": "ACTIVE"
    },
    {
        "product_id": "TP001",
        "product_name": "Duplicate Mouse",
        "category": "Electronics",
        "price": "600.00",
        "stock_quantity": "50",
        "status": "ACTIVE"
    },
    {
        "product_id": "TP002",
        "product_name": "Invalid Price Product",
        "category": "Electronics",
        "price": "-100.00",
        "stock_quantity": "20",
        "status": "ACTIVE"
    },
    {
        "product_id": "TP003",
        "product_name": "",
        "category": "Furniture",
        "price": "1200.00",
        "stock_quantity": "10",
        "status": "ACTIVE"
    },
    {
        "product_id": "TP004",
        "product_name": "Office Chair",
        "category": "Furniture",
        "price": "3500.00",
        "stock_quantity": "15",
        "status": "ACTIVE"
    },
    {
        "product_id": "TP005",
        "product_name": "Invalid Status Product",
        "category": "Electronics",
        "price": "800.00",
        "stock_quantity": "10",
        "status": "UNKNOWN"
    }
]

products_path = GENERATED_DIR / "test_products.csv"

with open(products_path, "w", newline="", encoding="utf-8") as file:

    writer = csv.DictWriter(
        file,
        fieldnames=products[0].keys()
    )

    writer.writeheader()
    writer.writerows(products)


# ==========================================
# 2. TEST ORDERS
# ==========================================

orders = [

    # Valid order
    {
        "order_id": "ORDTEST001",
        "order_date": "2026-11-10",
        "order_status": "COMPLETED",
        "items": [
            {"product_id": "TP001", "quantity": 2, "unit_price": 550},
            {"product_id": "TP004", "quantity": 1, "unit_price": 3500}
        ]
    },

    # First occurrence: valid
    {
        "order_id": "ORDTEST002",
        "order_date": "2026-11-11",
        "order_status": "CONFIRMED",
        "items": [
            {"product_id": "TP001", "quantity": 1, "unit_price": 550}
        ]
    },

    # Duplicate order ID
    {
        "order_id": "ORDTEST002",
        "order_date": "2026-11-11",
        "order_status": "PENDING",
        "items": [
            {"product_id": "TP004", "quantity": 1, "unit_price": 3500}
        ]
    },

    # Invalid date
    {
        "order_id": "ORDTEST003",
        "order_date": "invalid-date",
        "order_status": "COMPLETED",
        "items": [
            {"product_id": "TP001", "quantity": 1, "unit_price": 550}
        ]
    },

    # Product does not exist
    {
        "order_id": "ORDTEST004",
        "order_date": "2026-11-11",
        "order_status": "PENDING",
        "items": [
            {"product_id": "UNKNOWN_PRODUCT", "quantity": 1, "unit_price": 500}
        ]
    },

    # Invalid quantity
    {
        "order_id": "ORDTEST005",
        "order_date": "2026-11-11",
        "order_status": "CONFIRMED",
        "items": [
            {"product_id": "TP001", "quantity": 0, "unit_price": 550}
        ]
    },

    # Duplicate product within one order
    {
        "order_id": "ORDTEST006",
        "order_date": "2026-11-11",
        "order_status": "COMPLETED",
        "items": [
            {"product_id": "TP001", "quantity": 1, "unit_price": 550},
            {"product_id": "TP001", "quantity": 2, "unit_price": 550}
        ]
    },

    # One invalid item should reject the entire order
    {
        "order_id": "ORDTEST007",
        "order_date": "2026-11-11",
        "order_status": "COMPLETED",
        "items": [
            {"product_id": "TP001", "quantity": 1, "unit_price": 550},
            {"product_id": "UNKNOWN_PRODUCT", "quantity": 1, "unit_price": 500}
        ]
    }
]

orders_path = GENERATED_DIR / "test_orders.json"

with open(orders_path, "w", encoding="utf-8") as file:

    json.dump(
        orders,
        file,
        indent=4
    )


# ==========================================
# 3. SUMMARY
# ==========================================

print("\nTEST DATA GENERATED SUCCESSFULLY")
print("================================")

print(f"Products file: {products_path}")
print(f"Product records: {len(products)}")

print(f"\nOrders file: {orders_path}")
print(f"Order records: {len(orders)}")

print("\nExpected product results:")
print("Valid: 2")
print("Rejected: 4")

print("\nExpected order results:")
print("Valid: 2")
print("Rejected: 6")