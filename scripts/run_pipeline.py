import argparse
from pathlib import Path

from backend.pipeline import run_pipeline


def main():

    parser = argparse.ArgumentParser(
        description="Run the scalable e-commerce data pipeline."
    )

    parser.add_argument(
        "--products",
        type=Path,
        help="Path to the products CSV file."
    )

    parser.add_argument(
        "--orders",
        type=Path,
        help="Path to the orders JSON file."
    )

    args = parser.parse_args()

    # Require both paths together or neither.
    if bool(args.products) != bool(args.orders):
        parser.error(
            "Provide both --products and --orders, or neither."
        )

    results = run_pipeline(
        products_path=args.products,
        orders_path=args.orders
    )

    print("\n========== PIPELINE RESULTS ==========")

    for key, value in results.items():
        print(f"{key}: {value}")

    print("======================================")


if __name__ == "__main__":
    main()