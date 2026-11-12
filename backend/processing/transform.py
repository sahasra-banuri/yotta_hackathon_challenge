def transform_product(valid_product: dict) -> dict:
    """
    Prepare a validated product for database insertion.
    """

    return {
        "product_id": valid_product["product_id"],
        "product_name": valid_product["product_name"],
        "category": valid_product["category"],
        "price": valid_product["price"],
        "stock_quantity": valid_product["stock_quantity"],
        "status": valid_product["status"]
    }


def transform_order(valid_order: dict) -> tuple[dict, list[dict]]:
    """
    Flatten a validated order into:
    1. One order record.
    2. Multiple order item records.
    """

    order_row = {
        "order_id": valid_order["order_id"],
        "order_date": valid_order["order_date"],
        "order_status": valid_order["order_status"],
        "total_amount": valid_order["total_amount"]
    }

    item_rows = []

    for index, item in enumerate(valid_order["items"], start=1):

        item_row = {
            "order_item_id": (
                f"{valid_order['order_id']}-ITEM{index:03d}"
            ),
            "order_id": valid_order["order_id"],
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "item_total": item["item_total"]
        }

        item_rows.append(item_row)

    return order_row, item_rows
