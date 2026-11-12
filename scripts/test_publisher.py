from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database.connection import Base
from backend.database.models import (
    Product,
    Order,
    OrderItem
)

from backend.database.publisher import (
    create_pipeline_run,
    publish_products,
    publish_order
)


def test_publisher():

    # Create an isolated in-memory SQLite database.
    # This prevents test records from entering the project database.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )

    # Enable foreign-key enforcement for the test database.
    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    try:
        run_id = str(uuid4())

        product_id = "TEST_PUBLISH_P001"
        order_id = "TEST_PUBLISH_ORD001"

        with TestSessionLocal() as session:

            with session.begin():

                # Create a pipeline run first.
                create_pipeline_run(
                    session,
                    {
                        "run_id": run_id,
                        "file_name": "publisher_test",
                        "file_checksum": "test_checksum",
                        "file_type": "TEST",
                        "status": "RUNNING"
                    }
                )

                # Prepare a product.
                products = [
                    {
                        "product_id": product_id,
                        "product_name": "Test Laptop",
                        "category": "Electronics",
                        "price": Decimal("55000.00"),
                        "stock_quantity": 10,
                        "status": "ACTIVE"
                    }
                ]

                count = publish_products(session, products)
                assert count == 1

                # Prepare an order.
                order_row = {
                    "order_id": order_id,
                    "order_date": date(2026, 11, 10),
                    "order_status": "COMPLETED",
                    "total_amount": Decimal("110000.00")
                }

                item_rows = [
                    {
                        "order_item_id": f"{order_id}-ITEM001",
                        "order_id": order_id,
                        "product_id": product_id,
                        "quantity": 2,
                        "unit_price": Decimal("55000.00"),
                        "item_total": Decimal("110000.00")
                    }
                ]

                result = publish_order(
                    session,
                    order_row,
                    item_rows
                )

                assert result is True

                # Verify database records.
                saved_product = session.get(Product, product_id)
                saved_order = session.get(Order, order_id)

                saved_items = (
                    session.query(OrderItem)
                    .filter_by(order_id=order_id)
                    .all()
                )

                assert saved_product is not None
                assert saved_order is not None
                assert len(saved_items) == 1

                print("Product publishing: PASSED")
                print("Order publishing: PASSED")
                print("Order item publishing: PASSED")

                # Test rerunning the same records.
                publish_products(session, products)

                result = publish_order(
                    session,
                    order_row,
                    item_rows
                )

                assert result is True

                saved_items = (
                    session.query(OrderItem)
                    .filter_by(order_id=order_id)
                    .all()
                )

                assert len(saved_items) == 1

                print("Idempotent publishing test: PASSED")

        print("\nAll publisher tests passed.")
        print("Test database was isolated from the project database.")

    finally:
        test_engine.dispose()


if __name__ == "__main__":
    test_publisher()