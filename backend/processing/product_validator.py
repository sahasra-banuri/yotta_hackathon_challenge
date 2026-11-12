from decimal import Decimal, InvalidOperation

from backend.config import VALID_PRODUCT_STATUSES


def validate_product(
    record: dict,
    seen_product_ids: set
) -> tuple[dict | None, list[str]]:

    errors = []

    product_id = str(record.get("product_id") or "").strip()

    if not product_id:
        errors.append("Product ID is missing.")

    elif product_id in seen_product_ids:
        errors.append(f"Duplicate product ID: {product_id}")

    product_name = str(
        record.get("product_name") or ""
    ).strip()

    if not product_name:
        errors.append("Product name is missing.")

    category = str(
        record.get("category") or ""
    ).strip()

    if not category:
        errors.append("Product category is missing.")

    try:
        price = Decimal(str(record.get("price", "")).strip())

        if not price.is_finite():
            errors.append("Price must be a finite number.")

        elif price <= 0:
            errors.append("Price must be greater than zero.")

    except (InvalidOperation, ValueError):
        price = None
        errors.append("Price must be a valid number.")

    try:
        stock_quantity = int(
            str(record.get("stock_quantity", "")).strip()
        )

        if stock_quantity < 0:
            errors.append("Stock quantity cannot be negative.")

    except (ValueError, TypeError):
        stock_quantity = None
        errors.append("Stock quantity must be an integer.")

    status = str(
        record.get("status") or ""
    ).strip().upper()

    if status not in VALID_PRODUCT_STATUSES:
        errors.append(f"Invalid product status: {status}")

    if errors:
        return None, errors

    # Reserve the ID only after complete validation.
    seen_product_ids.add(product_id)

    return {
        "product_id": product_id,
        "product_name": product_name,
        "category": category,
        "price": price,
        "stock_quantity": stock_quantity,
        "status": status
    }, []