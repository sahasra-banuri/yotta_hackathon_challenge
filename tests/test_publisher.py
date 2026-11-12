import pytest

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database.connection import Base
from backend.database.models import (
    Product,
    Order,
    OrderItem,
    RejectedRecord,
    PipelineRun
)

from backend.database.publisher import (
    publish_products,
    publish_order,
    publish_orders,
    publish_rejected_records,
    create_pipeline_run,
    update_pipeline_run
)


# ==========================================
# TEST DATABASE FIXTURE
# ==========================================

@pytest.fixture
def session(tmp_path):

    database_path = tmp_path / "publisher_test.db"

    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False}
    )

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestSession = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False
    )

    test_session = TestSession()

    yield test_session

    test_session.close()
    test_engine.dispose()


# ==========================================
# TEST DATA HELPERS
# ==========================================

def make_product(
    product_id="P001",
    name="Laptop",
    price=Decimal("50000.00"),
    stock=10
):
    return {
        "product_id": product_id,
        "product_name": name,
        "category": "Electronics",
        "price": price,
        "stock_quantity": stock,
        "status": "ACTIVE"
    }


def make_order(
    order_id="O001",
    total=Decimal("1000.00")
):
    return {
        "order_id": order_id,
        "order_date": date(2026, 11, 10),
        "order_status": "CONFIRMED",
        "total_amount": total
    }


def make_item(
    item_id,
    order_id,
    product_id,
    quantity=2,
    unit_price=Decimal("500.00")
):
    """
    Build an order item using the model's actual primary-key name.
    """

    primary_key = next(
        iter(OrderItem.__table__.primary_key.columns)
    ).name

    return {
        primary_key: item_id,
        "order_id": order_id,
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "item_total": unit_price * quantity
    }


def add_product(session, product_id="P001"):
    session.add(Product(**make_product(product_id)))
    session.flush()


# ==========================================
# 1. PRODUCT PUBLISHING TESTS
# ==========================================

def test_publish_products_empty_list(session):

    result = publish_products(session, [])

    assert result == 0


def test_publish_products_successfully(session):

    products = [
        make_product("P001"),
        make_product("P002"),
        make_product("P003")
    ]

    result = publish_products(session, products)

    session.commit()

    assert result == 3

    assert session.query(Product).count() == 3


def test_publish_products_updates_existing_product(session):

    session.add(
        Product(**make_product("P001", name="Old Laptop"))
    )
    session.commit()

    updated_product = make_product(
        "P001",
        name="New Laptop",
        price=Decimal("65000.00"),
        stock=20
    )

    result = publish_products(
        session,
        [updated_product]
    )

    session.commit()

    stored_product = session.get(Product, "P001")

    assert result == 1
    assert session.query(Product).count() == 1
    assert stored_product.product_name == "New Laptop"
    assert stored_product.price == Decimal("65000.00")
    assert stored_product.stock_quantity == 20


def test_publish_products_handles_multiple_batches(session):

    products = [
        make_product(f"P{i:03d}")
        for i in range(1, 251)
    ]

    result = publish_products(session, products)

    session.commit()

    assert result == 250
    assert session.query(Product).count() == 250


# ==========================================
# 2. SINGLE ORDER PUBLISHING TESTS
# ==========================================

def test_publish_order_successfully(session):

    add_product(session)

    order = make_order()

    items = [
        make_item(
            "O001-ITEM001",
            "O001",
            "P001"
        )
    ]

    result = publish_order(
        session,
        order,
        items
    )

    session.commit()

    assert result is True

    assert session.get(Order, "O001") is not None
    assert session.query(OrderItem).count() == 1


def test_publish_order_replaces_existing_items(session):

    add_product(session, "P001")
    add_product(session, "P002")

    session.add(Order(**make_order()))
    session.add(
        OrderItem(**make_item(
            "OLD-ITEM",
            "O001",
            "P001"
        ))
    )
    session.commit()

    replacement_items = [
        make_item(
            "NEW-ITEM",
            "O001",
            "P002",
            quantity=3,
            unit_price=Decimal("200.00")
        )
    ]

    result = publish_order(
        session,
        make_order(total=Decimal("600.00")),
        replacement_items
    )

    session.commit()

    stored_items = (
        session.query(OrderItem)
        .filter_by(order_id="O001")
        .all()
    )

    assert result is True
    assert len(stored_items) == 1
    assert stored_items[0].product_id == "P002"
    assert stored_items[0].quantity == 3


def test_publish_order_rejects_invalid_product_reference(session):

    order = make_order()

    invalid_items = [
        make_item(
            "O001-ITEM001",
            "O001",
            "UNKNOWN_PRODUCT"
        )
    ]

    result = publish_order(
        session,
        order,
        invalid_items
    )

    assert result is False

    # The order header must also be rolled back.
    assert session.get(Order, "O001") is None


# ==========================================
# 3. BULK ORDER PUBLISHING TESTS
# ==========================================

def test_publish_orders_empty_list(session):

    result, failed_ids = publish_orders(session, [])

    assert result == 0
    assert failed_ids == set()


def test_publish_orders_successfully(session):

    add_product(session, "P001")
    add_product(session, "P002")

    orders = [
        (
            make_order("O001"),
            [
                make_item(
                    "O001-ITEM001",
                    "O001",
                    "P001"
                )
            ]
        ),
        (
            make_order("O002"),
            [
                make_item(
                    "O002-ITEM001",
                    "O002",
                    "P002"
                )
            ]
        )
    ]

    successful_count, failed_ids = publish_orders(
        session,
        orders
    )

    session.commit()

    assert successful_count == 2
    assert failed_ids == set()

    assert session.query(Order).count() == 2
    assert session.query(OrderItem).count() == 2


def test_publish_orders_replaces_existing_items(session):

    add_product(session, "P001")
    add_product(session, "P002")

    session.add(Order(**make_order("O001")))
    session.add(
        OrderItem(**make_item(
            "OLD-ITEM",
            "O001",
            "P001"
        ))
    )
    session.commit()

    orders = [
        (
            make_order("O001"),
            [
                make_item(
                    "NEW-ITEM",
                    "O001",
                    "P002"
                )
            ]
        )
    ]

    successful_count, failed_ids = publish_orders(
        session,
        orders
    )

    session.commit()

    stored_items = (
        session.query(OrderItem)
        .filter_by(order_id="O001")
        .all()
    )

    assert successful_count == 1
    assert failed_ids == set()
    assert len(stored_items) == 1
    assert stored_items[0].product_id == "P002"


def test_publish_orders_fallback_isolates_invalid_order(session):

    add_product(session, "P001")

    orders = [
        (
            make_order("O001"),
            [
                make_item(
                    "O001-ITEM001",
                    "O001",
                    "P001"
                )
            ]
        ),
        (
            make_order("O002"),
            [
                make_item(
                    "O002-ITEM001",
                    "O002",
                    "UNKNOWN_PRODUCT"
                )
            ]
        )
    ]

    successful_count, failed_ids = publish_orders(
        session,
        orders
    )

    session.commit()

    assert successful_count == 1
    assert failed_ids == {"O002"}

    assert session.get(Order, "O001") is not None
    assert session.get(Order, "O002") is None

    assert session.query(OrderItem).count() == 1


# ==========================================
# 4. REJECTED RECORD TESTS
# ==========================================

def create_test_pipeline_run(session):

    run = PipelineRun(
        run_id="TEST-RUN-001",
        file_name="products.csv",
        file_checksum="test-checksum",
        file_type="CSV",
        status="RUNNING"
    )

    session.add(run)
    session.flush()

    return run


def test_publish_rejected_records_empty_list(session):

    result = publish_rejected_records(
        session,
        "TEST-RUN-001",
        "products.csv",
        []
    )

    assert result == 0


def test_publish_rejected_records_successfully(session):

    create_test_pipeline_run(session)

    rejected_records = [
        {
            "record_id": "P101",
            "raw_record": {
                "product_id": "P101",
                "price": "-100"
            },
            "errors": [
                "Price cannot be negative."
            ]
        },
        {
            "record_id": "P102",
            "raw_record": {
                "product_id": "P102",
                "status": "UNKNOWN"
            },
            "errors": [
                "Invalid product status: UNKNOWN"
            ]
        }
    ]

    result = publish_rejected_records(
        session,
        "TEST-RUN-001",
        "products.csv",
        rejected_records
    )

    session.commit()

    stored_records = session.query(RejectedRecord).all()

    assert result == 2
    assert len(stored_records) == 2

    assert stored_records[0].run_id == "TEST-RUN-001"
    assert stored_records[0].source_file == "products.csv"
    assert "Price cannot be negative." in (
        stored_records[0].rejection_reason
    )


# ==========================================
# 5. PIPELINE RUN TESTS
# ==========================================

def test_create_pipeline_run(session):

    run_data = {
        "run_id": "RUN-001",
        "file_name": "products.csv",
        "file_checksum": "checksum-001",
        "file_type": "CSV",
        "status": "RUNNING"
    }

    create_pipeline_run(session, run_data)

    session.commit()

    stored_run = session.get(
        PipelineRun,
        "RUN-001"
    )

    assert stored_run is not None
    assert stored_run.status == "RUNNING"


def test_update_pipeline_run(session):

    create_test_pipeline_run(session)

    completed_at = datetime(2026, 11, 12, 12, 0, 0)

    updates = {
        "status": "SUCCESS",
        "total_records": 100,
        "valid_records": 95,
        "rejected_records": 5,
        "completed_at": completed_at
    }

    update_pipeline_run(
        session,
        "TEST-RUN-001",
        updates
    )

    session.commit()

    stored_run = session.get(
        PipelineRun,
        "TEST-RUN-001"
    )

    assert stored_run.status == "SUCCESS"
    assert stored_run.total_records == 100
    assert stored_run.valid_records == 95
    assert stored_run.rejected_records == 5
    assert stored_run.completed_at == completed_at