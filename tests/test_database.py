import pytest

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.database.connection import Base
from backend.database.models import (
    Product,
    Order,
    OrderItem,
    RejectedRecord,
    PipelineRun
)


@pytest.fixture
def db_session(tmp_path):
    """
    Create an isolated temporary SQLite database
    for each test.
    """

    database_path = tmp_path / "test_database.db"

    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False}
    )

    # Enable foreign-key enforcement for the test database.
    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    session = TestingSession()

    yield session

    session.close()
    test_engine.dispose()


@pytest.fixture
def sample_product():
    return Product(
        product_id="P001",
        product_name="Laptop",
        category="Electronics",
        price=Decimal("75000.50"),
        stock_quantity=10,
        status="ACTIVE"
    )


@pytest.fixture
def sample_order():
    return Order(
        order_id="ORD001",
        order_date=date(2026, 11, 12),
        order_status="PENDING",
        total_amount=Decimal("150000.00")
    )


@pytest.fixture
def sample_pipeline_run():
    return PipelineRun(
        run_id="RUN001",
        file_name="products.csv + orders.json",
        file_checksum="a" * 64,
        file_type="COMBINED",
        status="RUNNING"
    )


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def test_all_tables_are_created(db_session):
    inspector = inspect(db_session.bind)

    tables = set(inspector.get_table_names())

    expected_tables = {
        "products",
        "orders",
        "order_items",
        "rejected_records",
        "pipeline_runs"
    }

    assert expected_tables.issubset(tables)


def test_order_item_indexes_exist(db_session):
    inspector = inspect(db_session.bind)

    indexes = inspector.get_indexes("order_items")

    index_names = {
        index["name"]
        for index in indexes
    }

    assert "idx_order_items_order_id" in index_names
    assert "idx_order_items_product_id" in index_names


# ==========================================
# PRODUCT MODEL
# ==========================================

def test_insert_product(db_session, sample_product):
    db_session.add(sample_product)
    db_session.commit()

    result = db_session.get(Product, "P001")

    assert result is not None
    assert result.product_name == "Laptop"
    assert result.category == "Electronics"
    assert result.price == Decimal("75000.50")
    assert result.stock_quantity == 10
    assert result.status == "ACTIVE"


def test_product_primary_key_uniqueness(
    db_session,
    sample_product
):
    db_session.add(sample_product)
    db_session.commit()

    duplicate = Product(
        product_id="P001",
        product_name="Another Laptop",
        category="Electronics",
        price=Decimal("50000"),
        stock_quantity=5,
        status="ACTIVE"
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_product_created_at_default(db_session, sample_product):
    db_session.add(sample_product)
    db_session.commit()

    result = db_session.get(Product, "P001")

    assert result.created_at is not None


# ==========================================
# ORDER MODEL
# ==========================================

def test_insert_order(db_session, sample_order):
    db_session.add(sample_order)
    db_session.commit()

    result = db_session.get(Order, "ORD001")

    assert result is not None
    assert result.order_date == date(2026, 11, 12)
    assert result.order_status == "PENDING"
    assert result.total_amount == Decimal("150000.00")


def test_order_created_at_default(db_session, sample_order):
    db_session.add(sample_order)
    db_session.commit()

    result = db_session.get(Order, "ORD001")

    assert result.created_at is not None


# ==========================================
# ORDER ITEM MODEL
# ==========================================

def test_insert_order_item(
    db_session,
    sample_product,
    sample_order
):
    db_session.add_all([
        sample_product,
        sample_order
    ])

    db_session.flush()

    item = OrderItem(
        order_item_id="ORD001-ITEM001",
        order_id="ORD001",
        product_id="P001",
        quantity=2,
        unit_price=Decimal("75000.00"),
        item_total=Decimal("150000.00")
    )

    db_session.add(item)
    db_session.commit()

    result = db_session.get(
        OrderItem,
        "ORD001-ITEM001"
    )

    assert result is not None
    assert result.order_id == "ORD001"
    assert result.product_id == "P001"
    assert result.quantity == 2
    assert result.item_total == Decimal("150000.00")


def test_order_item_rejects_unknown_order(
    db_session,
    sample_product
):
    db_session.add(sample_product)
    db_session.flush()

    item = OrderItem(
        order_item_id="INVALID001",
        order_id="UNKNOWN",
        product_id="P001",
        quantity=1,
        unit_price=Decimal("100"),
        item_total=Decimal("100")
    )

    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_order_item_rejects_unknown_product(
    db_session,
    sample_order
):
    db_session.add(sample_order)
    db_session.flush()

    item = OrderItem(
        order_item_id="INVALID002",
        order_id="ORD001",
        product_id="UNKNOWN",
        quantity=1,
        unit_price=Decimal("100"),
        item_total=Decimal("100")
    )

    db_session.add(item)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


# ==========================================
# REJECTED RECORD MODEL
# ==========================================

def test_insert_rejected_record(
    db_session,
    sample_pipeline_run
):
    db_session.add(sample_pipeline_run)
    db_session.flush()

    rejected = RejectedRecord(
        run_id="RUN001",
        source_file="products.csv",
        record_id="P002",
        raw_record='{"product_id": "P002", "price": "-100"}',
        rejection_reason="Price cannot be negative."
    )

    db_session.add(rejected)
    db_session.commit()

    result = db_session.query(RejectedRecord).first()

    assert result is not None
    assert result.run_id == "RUN001"
    assert result.record_id == "P002"
    assert result.rejection_reason == "Price cannot be negative."


def test_rejected_record_requires_valid_pipeline_run(db_session):
    rejected = RejectedRecord(
        run_id="UNKNOWN",
        source_file="products.csv",
        record_id="P002",
        raw_record="{}",
        rejection_reason="Invalid record"
    )

    db_session.add(rejected)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


# ==========================================
# PIPELINE RUN MODEL
# ==========================================

def test_create_pipeline_run(
    db_session,
    sample_pipeline_run
):
    db_session.add(sample_pipeline_run)
    db_session.commit()

    result = db_session.get(PipelineRun, "RUN001")

    assert result is not None
    assert result.status == "RUNNING"
    assert result.file_type == "COMBINED"
    assert result.started_at is not None


def test_update_pipeline_run_status(
    db_session,
    sample_pipeline_run
):
    db_session.add(sample_pipeline_run)
    db_session.commit()

    result = db_session.get(PipelineRun, "RUN001")

    result.status = "SUCCESS"
    result.total_records = 100
    result.valid_records = 95
    result.rejected_records = 5

    db_session.commit()

    updated = db_session.get(PipelineRun, "RUN001")

    assert updated.status == "SUCCESS"
    assert updated.total_records == 100
    assert updated.valid_records == 95
    assert updated.rejected_records == 5


def test_pipeline_run_completion_timestamp(
    db_session,
    sample_pipeline_run
):
    db_session.add(sample_pipeline_run)
    db_session.commit()

    result = db_session.get(PipelineRun, "RUN001")

    assert result.completed_at is None

    from datetime import datetime, timezone

    result.status = "SUCCESS"
    result.completed_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    )

    db_session.commit()

    updated = db_session.get(PipelineRun, "RUN001")

    assert updated.completed_at is not None