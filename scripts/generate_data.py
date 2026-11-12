import csv
import json
import random
import argparse
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "sample"

PRODUCT_CATEGORIES = [
    "Electronics",
    "Clothing",
    "Home",
    "Books",
    "Sports",
    "Accessories"
]

PRODUCT_STATUSES = ["ACTIVE", "INACTIVE"]

ORDER_STATUSES = [
    "PENDING",
    "CONFIRMED",
    "SHIPPED",
    "COMPLETED",
    "CANCELLED"
]


def generate_products(count, seed):
    random.seed(seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    product_ids = []

    file_path = DATA_DIR / "products.csv"

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "product_id",
            "product_name",
            "category",
            "price",
            "stock_quantity",
            "status"
        ])

        for i in range(1, count + 1):
            product_id = f"P{i:06d}"
            product_ids.append(product_id)

            writer.writerow([
                product_id,
                f"Product {i}",
                random.choice(PRODUCT_CATEGORIES),
                round(random.uniform(100, 100000), 2),
                random.randint(0, 500),
                random.choice(PRODUCT_STATUSES)
            ])

    print(f"Generated {count:,} products: {file_path}")

    return product_ids


def generate_orders(count, product_ids, seed):
    random.seed(seed)

    file_path = DATA_DIR / "orders.json"

    start_date = date(2026, 1, 1)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write("[\n")

        for i in range(1, count + 1):
            item_count = random.randint(1, min(5, len(product_ids)))
            selected_products = random.sample(product_ids, item_count)

            items = []

            for product_id in selected_products:
                quantity = random.randint(1, 5)

                items.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": round(random.uniform(100, 100000), 2)
                })

            order = {
                "order_id": f"ORD{i:08d}",
                "order_date": str(
                    start_date + timedelta(days=random.randint(0, 300))
                ),
                "order_status": random.choice(ORDER_STATUSES),
                "items": items
            }

            json.dump(order, file)

            if i < count:
                file.write(",\n")

        file.write("\n]")

    print(f"Generated {count:,} orders: {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate reproducible e-commerce datasets."
    )

    parser.add_argument("--products", type=int, default=1000)
    parser.add_argument("--orders", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    product_ids = generate_products(args.products, args.seed)

    generate_orders(
        args.orders,
        product_ids,
        args.seed
    )

    print("\nData generation completed successfully.")


if __name__ == "__main__":
    main()