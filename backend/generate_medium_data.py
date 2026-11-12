import csv
import json
import random
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

from backend.config import (
    SAMPLE_DATA_DIR,
    GENERATED_DATA_DIR,
)

random.seed(42)

PRODUCT_FILE = SAMPLE_DATA_DIR / "products.csv"
OUTPUT_FILE = GENERATED_DATA_DIR / "medium_orders.json"

GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load active products from the existing catalogue.
products = []

with open(PRODUCT_FILE, "r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        if row["status"].strip().upper() == "ACTIVE":
            products.append({
                "product_id": row["product_id"],
                "price": Decimal(row["price"]),
            })

if not products:
    raise ValueError("No active products found.")

orders = []

statuses = [
    "PENDING",
    "CONFIRMED",
    "SHIPPED",
    "COMPLETED",
    "CANCELLED",
]

today = date.today()

for number in range(1, 10001):

    order_items = []
    used_products = set()

    item_count = random.randint(1, 3)

    for _ in range(item_count):

        available = [
            product for product in products
            if product["product_id"] not in used_products
        ]

        product = random.choice(available)
        used_products.add(product["product_id"])

        quantity = random.randint(1, 5)
        unit_price = product["price"]

        item_total = unit_price * quantity

        order_items.append({
            "product_id": product["product_id"],
            "quantity": quantity,
            "unit_price": float(unit_price),
            "item_total": float(item_total),
        })

    total_amount = sum(
        Decimal(str(item["item_total"]))
        for item in order_items
    )

    order_date = today - timedelta(
        days=random.randint(1, 180)
    )

    orders.append({
        "order_id": f"MED-ORDER-{number:06d}",
        "order_date": order_date.isoformat(),
        "order_status": random.choice(statuses),
        "total_amount": float(total_amount),
        "items": order_items,
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(orders, file, indent=None)

print("Medium benchmark dataset generated successfully.")
print(f"Products available: {len(products)}")
print(f"Orders generated: {len(orders)}")
print(f"Total records: {len(products) + len(orders)}")
print(f"Output: {OUTPUT_FILE}")