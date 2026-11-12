import json

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert

from backend.database.models import (
    Product,
    Order,
    OrderItem,
    RejectedRecord,
    PipelineRun
)


# ==========================================
# 1. PUBLISH PRODUCTS
# ==========================================

def publish_products(session, products: list[dict]) -> int:
    """
    Publish products using batched UPSERT operations.

    Existing products are updated when their product_id
    already exists.
    """

    if not products:
        return 0

    batch_size = 100
    published_count = 0

    for start in range(0, len(products), batch_size):

        batch = products[start:start + batch_size]

        statement = insert(Product).values(batch)
        excluded = statement.excluded

        statement = statement.on_conflict_do_update(
            index_elements=["product_id"],
            set_={
                "product_name": excluded.product_name,
                "category": excluded.category,
                "price": excluded.price,
                "stock_quantity": excluded.stock_quantity,
                "status": excluded.status
            }
        )

        session.execute(statement)

        published_count += len(batch)

    return published_count


# ==========================================
# 2. PUBLISH ONE ORDER
# ==========================================

def publish_order(
    session,
    order_row: dict,
    item_rows: list[dict]
) -> bool:
    """
    Publish one order and its items atomically.

    Used as a fallback when bulk publishing
    encounters an integrity error.
    """

    try:

        with session.begin_nested():

            statement = insert(Order).values(order_row)

            statement = statement.on_conflict_do_update(
                index_elements=["order_id"],
                set_={
                    "order_date": statement.excluded.order_date,
                    "order_status": statement.excluded.order_status,
                    "total_amount": statement.excluded.total_amount
                }
            )

            session.execute(statement)

            # Remove previously published items.
            session.execute(
                delete(OrderItem).where(
                    OrderItem.order_id == order_row["order_id"]
                )
            )

            # Insert the current items.
            if item_rows:
                session.execute(
                    insert(OrderItem).values(item_rows)
                )

        return True

    except IntegrityError:
        return False


# ==========================================
# 3. PUBLISH MULTIPLE ORDERS
# ==========================================

def publish_orders(
    session,
    orders: list[tuple[dict, list[dict]]]
) -> tuple[int, set[str]]:
    """
    Publish multiple orders using bulk database operations.

    Each element contains:
        (order_row, item_rows)

    Returns:
        Number of successfully published orders.
        Set of order IDs that failed.
    """

    if not orders:
        return 0, set()

    order_rows = [
        order_row
        for order_row, _ in orders
    ]

    all_item_rows = [
        item
        for _, item_rows in orders
        for item in item_rows
    ]

    order_ids = [
        order["order_id"]
        for order in order_rows
    ]

    try:

        # Protect the entire bulk operation with a savepoint.
        with session.begin_nested():

            # ----------------------------------
            # A. BULK UPSERT ORDER HEADERS
            # ----------------------------------

            for start in range(0, len(order_rows), 100):

                batch = order_rows[start:start + 100]

                statement = insert(Order).values(batch)
                excluded = statement.excluded

                statement = statement.on_conflict_do_update(
                    index_elements=["order_id"],
                    set_={
                        "order_date": excluded.order_date,
                        "order_status": excluded.order_status,
                        "total_amount": excluded.total_amount
                    }
                )

                session.execute(statement)

            # ----------------------------------
            # B. DELETE PREVIOUS ORDER ITEMS
            # ----------------------------------

            for start in range(0, len(order_ids), 500):

                batch_ids = order_ids[start:start + 500]

                session.execute(
                    delete(OrderItem).where(
                        OrderItem.order_id.in_(batch_ids)
                    )
                )

            # ----------------------------------
            # C. BULK INSERT ORDER ITEMS
            # ----------------------------------

            for start in range(0, len(all_item_rows), 100):

                batch = all_item_rows[start:start + 100]

                session.execute(
                    insert(OrderItem).values(batch)
                )

        return len(orders), set()

    except IntegrityError:

        # The bulk savepoint has been rolled back.
        # Retry orders individually to isolate failures.

        failed_order_ids = set()

        for order_row, item_rows in orders:

            published = publish_order(
                session,
                order_row,
                item_rows
            )

            if not published:
                failed_order_ids.add(order_row["order_id"])

        successful_count = len(orders) - len(failed_order_ids)

        return successful_count, failed_order_ids


# ==========================================
# 4. PUBLISH REJECTED RECORDS
# ==========================================

def publish_rejected_records(
    session,
    run_id: str,
    source_file: str,
    rejected_records: list[dict]
) -> int:
    """
    Store rejected records and their validation errors.
    """

    if not rejected_records:
        return 0

    database_records = []

    for record in rejected_records:

        database_records.append({
            "run_id": run_id,
            "source_file": source_file,
            "record_id": record.get("record_id"),
            "raw_record": json.dumps(
                record.get("raw_record"),
                default=str
            ),
            "rejection_reason": "; ".join(
                record.get("errors", [])
            )
        })

    session.add_all([
        RejectedRecord(**record)
        for record in database_records
    ])

    session.flush()

    return len(database_records)


# ==========================================
# 5. CREATE PIPELINE RUN
# ==========================================

def create_pipeline_run(session, run_data: dict) -> None:
    """
    Create a database record for a pipeline execution.
    """

    pipeline_run = PipelineRun(**run_data)

    session.add(pipeline_run)
    session.flush()


# ==========================================
# 6. UPDATE PIPELINE RUN
# ==========================================

def update_pipeline_run(
    session,
    run_id: str,
    updates: dict
) -> None:
    """
    Update execution status and processing metrics.
    """

    session.execute(
        update(PipelineRun)
        .where(PipelineRun.run_id == run_id)
        .values(**updates)
    )

    session.flush()