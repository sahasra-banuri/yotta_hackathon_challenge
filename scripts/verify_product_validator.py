from backend.processing.product_validator import validate_product


def main():

    seen_product_ids = set()

    # Test 1: Valid product
    product_1 = {
        "product_id": "P001",
        "product_name": "Laptop",
        "category": "Electronics",
        "price": "55000.00",
        "stock_quantity": "20",
        "status": "active"
    }

    valid, errors = validate_product(
        product_1,
        seen_product_ids
    )

    print("\nTEST 1: Valid product")
    print("Valid:", valid is not None)
    print("Errors:", errors)

    # Test 2: Invalid product
    product_2 = {
        "product_id": "P002",
        "product_name": "",
        "category": "Electronics",
        "price": "-500",
        "stock_quantity": "-10",
        "status": "UNKNOWN"
    }

    valid, errors = validate_product(
        product_2,
        seen_product_ids
    )

    print("\nTEST 2: Invalid product")
    print("Valid:", valid is not None)
    print("Errors:", errors)

    # Test 3: Duplicate product ID
    product_3 = {
        "product_id": "P001",
        "product_name": "Laptop Pro",
        "category": "Electronics",
        "price": "65000",
        "stock_quantity": "10",
        "status": "ACTIVE"
    }

    valid, errors = validate_product(
        product_3,
        seen_product_ids
    )

    print("\nTEST 3: Duplicate product")
    print("Valid:", valid is not None)
    print("Errors:", errors)


if __name__ == "__main__":
    main()