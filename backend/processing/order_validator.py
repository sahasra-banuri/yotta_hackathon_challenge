from datetime import date
from decimal import Decimal, InvalidOperation

from backend.config import VALID_ORDER_STATUSES


def validate_order(
    record: dict,
    seen_order_ids: set,
    valid_product_ids: set
) -> tuple[dict | None, list[str]]:

    errors = []

    order_id = str(record.get("order_id") or "").strip()

    if not order_id:
        errors.append("Order ID is missing.")

    elif order_id in seen_order_ids:
        errors.append(f"Duplicate order ID: {order_id}")

    # Validate order date
    try:
        order_date = date.fromisoformat(
            str(record.get("order_date", "")).strip()
        )
    except (ValueError, TypeError):
        order_date = None
        errors.append("Invalid order date.")

    # Validate order status
    order_status = str(
        record.get("order_status") or ""
    ).strip().upper()

    if order_status not in VALID_ORDER_STATUSES:
        errors.append(f"Invalid order status: {order_status}")

    # Validate order items
    items = record.get("items")

    if not isinstance(items, list) or not items:
        errors.append("Order must contain at least one item.")
        items = []

    validated_items = []
    seen_item_product_ids = set()
    total_amount = Decimal("0.00")

    for index, item in enumerate(items, start=1):

        if not isinstance(item, dict):
            errors.append(
                f"Item {index}: Invalid item structure."
            )
            continue

        item_errors = []

        product_id = str(
            item.get("product_id") or ""
        ).strip()

        # Product reference validation
        if not product_id:
            item_errors.append("Product ID is missing.")

        elif product_id not in valid_product_ids:
            item_errors.append(
                f"Unknown product ID or inactive product: {product_id}"
            )

        elif product_id in seen_item_product_ids:
            item_errors.append(
                f"Duplicate product in order: {product_id}"
            )

        else:
            seen_item_product_ids.add(product_id)

        # Quantity validation
        try:
            raw_quantity = item.get("quantity")

            if isinstance(raw_quantity, bool):
                raise ValueError

            quantity = int(raw_quantity)

            if str(raw_quantity).strip() != str(quantity):
                raise ValueError

            if quantity <= 0:
                item_errors.append(
                    "Quantity must be greater than zero."
                )

        except (ValueError, TypeError):
            quantity = None
            item_errors.append(
                "Quantity must be a positive integer."
            )

        # Unit price validation
        try:
            unit_price = Decimal(
                str(item.get("unit_price", "")).strip()
            )

            if not unit_price.is_finite():
                item_errors.append(
                    "Unit price must be a finite number."
                )

            elif unit_price <= 0:
                item_errors.append(
                    "Unit price must be greater than zero."
                )

        except (InvalidOperation, ValueError):
            unit_price = None
            item_errors.append(
                "Unit price must be a valid number."
            )

        # Reject invalid items
        if item_errors:
            errors.extend(
                [
                    f"Item {index}: {error}"
                    for error in item_errors
                ]
            )
            continue

        # Calculate item total
        item_total = quantity * unit_price
        total_amount += item_total

        validated_items.append({
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "item_total": item_total
        })

    # Reject the entire order if any validation failed
    if errors:
        return None, errors

    # Reserve order ID only after successful validation
    seen_order_ids.add(order_id)

    return {
        "order_id": order_id,
        "order_date": order_date,
        "order_status": order_status,
        "items": validated_items,
        "total_amount": total_amount
    }, []