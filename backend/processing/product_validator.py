from decimal import Decimal, InvalidOperation

from backend.config import VALID_PRODUCT_STATUSES


def validate_product(
    record: dict,
    seen_product_ids: set
) -> tuple[dict | None, list[str]]:

    errors = []

    # 1. Validate product ID
    product_id = str(record.get("product_id") or "").strip()

    if not product_id:
        errors.append("Product ID is missing.")

    elif product_id in seen_product_ids:
        errors.append(f"Duplicate product ID: {product_id}")

    else:
        seen_product_ids.add(product_id)

    # 2. Validate product name
    product_name = str(
        record.get("product_name") or ""
    ).strip()

    if not product_name:
        errors.append("Product name is missing.")

    # 3. Validate category
    category = str(
        record.get("category") or ""
    ).strip()

    if not category:
        errors.append("Product category is missing.")

    # 4. Validate price
    try:
        price = Decimal(str(record.get("price", "")).strip())

        if not price.is_finite():
            errors.append("Price must be a finite number.")

        elif price < 0:
            errors.append("Price cannot be negative.")

    except (InvalidOperation, ValueError):
        price = None
        errors.append("Price must be a valid number.")

    # 5. Validate stock quantity
    try:
        stock_quantity = int(
            str(record.get("stock_quantity", "")).strip()
        )

        if stock_quantity < 0:
            errors.append("Stock quantity cannot be negative.")

    except (ValueError, TypeError):
        stock_quantity = None
        errors.append("Stock quantity must be an integer.")

    # 6. Validate status
    status = str(
        record.get("status") or ""
    ).strip().upper()

    if status not in VALID_PRODUCT_STATUSES:
        errors.append(
            f"Invalid product status: {status}"
        )

    # 7. Return validation result
    if errors:
        return None, errors

    valid_product = {
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "price": price,
        "stock_quantity": stock_quantity,
        "status": status
    }

    return valid_product, []