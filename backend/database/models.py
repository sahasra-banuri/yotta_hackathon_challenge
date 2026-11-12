from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Date,
    DateTime,
    Text,
    ForeignKey,
    func,
    Index
)

from backend.database.connection import Base


# ==========================================
# 1. PRODUCTS TABLE
# ==========================================

class Product(Base):

    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)

    product_name = Column(String(255), nullable=False)

    category = Column(String(100), nullable=False)

    price = Column(Numeric(12, 2), nullable=False)

    stock_quantity = Column(Integer, nullable=False)

    status = Column(String(20), nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )


# ==========================================
# 2. ORDERS TABLE
# ==========================================

class Order(Base):

    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)

    order_date = Column(Date, nullable=False)

    order_status = Column(String(30), nullable=False)

    total_amount = Column(Numeric(14, 2), nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )


# ==========================================
# 3. ORDER ITEMS TABLE
# ==========================================

class OrderItem(Base):

    __tablename__ = "order_items"

    order_item_id = Column(String(100), primary_key=True)

    order_id = Column(
        String(50),
        ForeignKey("orders.order_id"),
        nullable=False
    )

    product_id = Column(
        String(50),
        ForeignKey("products.product_id"),
        nullable=False
    )

    quantity = Column(Integer, nullable=False)

    unit_price = Column(Numeric(12, 2), nullable=False)

    item_total = Column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        Index("idx_order_items_order_id", "order_id"),
        Index("idx_order_items_product_id", "product_id"),
    )


# ==========================================
# 4. REJECTED RECORDS TABLE
# ==========================================

class RejectedRecord(Base):

    __tablename__ = "rejected_records"

    rejection_id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(
        String(50),
        ForeignKey("pipeline_runs.run_id"),
        nullable=False
    )

    source_file = Column(String(255), nullable=False)

    record_id = Column(String(100))

    raw_record = Column(Text, nullable=False)

    rejection_reason = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )


# ==========================================
# 5. PIPELINE RUNS TABLE
# ==========================================

class PipelineRun(Base):

    __tablename__ = "pipeline_runs"

    run_id = Column(String(50), primary_key=True)

    file_name = Column(String(255), nullable=False)

    file_checksum = Column(String(64), nullable=False)

    file_type = Column(String(20), nullable=False)

    status = Column(String(20), nullable=False)

    total_records = Column(Integer, default=0)

    valid_records = Column(Integer, default=0)

    rejected_records = Column(Integer, default=0)

    processing_time = Column(Numeric(12, 4))

    peak_memory_mb = Column(Numeric(12, 2))

    started_at = Column(
        DateTime,
        server_default=func.current_timestamp()
    )

    completed_at = Column(DateTime, nullable=True)