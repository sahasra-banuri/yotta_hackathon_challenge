from backend.processing.order_validator import validate_order


def main():

    seen_order_ids = set()

    valid_product_ids = {"P001", "P002", "P003"}

    # Test 1: Valid order
    order_1 = {
        "order_id": "ORD001",
        "order_date": "2026-11-10",
        "order_status": "COMPLETED",
        "items": [
            {
                "product_id": "P001",
                "quantity": 2,
                "unit_price": 500
            },
            {
                "product_id": "P002",
                "quantity": 1,
                "unit_price": 300
            }
        ]
    }

    valid, errors = validate_order(
        order_1, seen_order_ids, valid_product_ids
    )

    print("\nTEST 1: Valid order")
    print("Valid:", valid is not None)
    print("Total:", valid["total_amount"] if valid else None)
    print("Errors:", errors)

    # Test 2: Unknown product
    order_2 = {
        "order_id": "ORD002",
        "order_date": "2026-11-10",
        "order_status": "CONFIRMED",
        "items": [
            {
                "product_id": "P999",
                "quantity": 1,
                "unit_price": 500
            }
        ]
    }

    valid, errors = validate_order(
        order_2, seen_order_ids, valid_product_ids
    )

    print("\nTEST 2: Unknown product")
    print("Valid:", valid is not None)
    print("Errors:", errors)

    # Test 3: Invalid item quantity
    order_3 = {
        "order_id": "ORD003",
        "order_date": "2026-11-10",
        "order_status": "PENDING",
        "items": [
            {
                "product_id": "P001",
                "quantity": 0,
                "unit_price": 500
            }
        ]
    }

    valid, errors = validate_order(
        order_3, seen_order_ids, valid_product_ids
    )

    print("\nTEST 3: Invalid quantity")
    print("Valid:", valid is not None)
    print("Errors:", errors)

    # Test 4: Duplicate order ID
    order_4 = {
        "order_id": "ORD001",
        "order_date": "2026-11-10",
        "order_status": "COMPLETED",
        "items": [
            {
                "product_id": "P003",
                "quantity": 1,
                "unit_price": 100
            }
        ]
    }

    valid, errors = validate_order(
        order_4, seen_order_ids, valid_product_ids
    )

    print("\nTEST 4: Duplicate order")
    print("Valid:", valid is not None)
    print("Errors:", errors)


if __name__ == "__main__":
    main()