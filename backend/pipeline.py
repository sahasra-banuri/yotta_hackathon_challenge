import hashlib
import logging
import time

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psutil

from sqlalchemy import select

from backend.config import (
    SAMPLE_DATA_DIR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_JSON_BATCH_SIZE,
    STALE_RUN_TIMEOUT_MINUTES
)

from backend.database.connection import SessionLocal
from backend.database.models import PipelineRun

from backend.database.publisher import (
    create_pipeline_run,
    update_pipeline_run,
    publish_products,
    publish_orders,
    publish_rejected_records,
    reconcile_product_snapshot
)

from backend.ingestion.csv_ingestion import read_csv_in_chunks
from backend.ingestion.json_ingestion import read_json_in_batches

from backend.processing.product_validator import validate_product
from backend.processing.order_validator import validate_order

from backend.processing.transform import (
    transform_product,
    transform_order
)


# ==========================================
# 1. TIME
# ==========================================

def utc_now():
    """
    Return timezone-naive UTC time.

    This matches SQLite CURRENT_TIMESTAMP representation.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


# ==========================================
# 2. LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ==========================================
# 3. FILE CHECKSUM
# ==========================================

def calculate_checksum(file_path: Path) -> str:
    """
    Calculate SHA-256 checksum without loading
    the complete file into memory.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:

            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def calculate_combined_checksum(
    products_path: Path,
    orders_path: Path
) -> str:
    """
    Generate a checksum representing both input files.
    """

    combined = hashlib.sha256()

    for file_path in (products_path, orders_path):

        checksum = calculate_checksum(file_path)

        combined.update(file_path.name.encode())
        combined.update(checksum.encode())

    return combined.hexdigest()


# ==========================================
# 4. MEMORY MONITORING
# ==========================================

def get_memory_usage_mb() -> float:

    process = psutil.Process()

    memory_bytes = process.memory_info().rss

    return memory_bytes / (1024 * 1024)


# ==========================================
# 5. STALE RUN RECOVERY
# ==========================================

def recover_stale_runs(session):
    """
    Mark executions that exceeded the configured
    RUNNING timeout as ABANDONED.

    Processing time and peak memory remain NULL because
    an abandoned execution has no reliable completion metrics.
    """

    cutoff_time = utc_now() - timedelta(
        minutes=STALE_RUN_TIMEOUT_MINUTES
    )

    stale_runs = session.scalars(
        select(PipelineRun).where(
            PipelineRun.status == "RUNNING",
            PipelineRun.started_at < cutoff_time
        )
    ).all()

    recovered_count = 0

    for run in stale_runs:

        run.status = "ABANDONED"
        run.completed_at = utc_now()

        # Do not calculate processing_time for abandoned runs.
        # Keep unavailable performance metrics as None.

        logger.warning(
            "Recovered stale pipeline run: %s",
            run.run_id
        )

        recovered_count += 1

    if recovered_count:
        session.commit()

        logger.info(
            "Stale run recovery completed. Recovered: %s",
            recovered_count
        )

    return recovered_count

# ==========================================
# 6. MAIN PIPELINE
# ==========================================

def run_pipeline(
    products_path: Path | str | None = None,
    orders_path: Path | str | None = None
) -> dict:

    start_time = time.perf_counter()

    products_path = Path(
        products_path or SAMPLE_DATA_DIR / "products.csv"
    )

    orders_path = Path(
        orders_path or SAMPLE_DATA_DIR / "orders.json"
    )

    # --------------------------------------
    # Validate input paths
    # --------------------------------------

    if not products_path.is_file():
        raise FileNotFoundError(products_path)

    if not orders_path.is_file():
        raise FileNotFoundError(orders_path)

    # Reject physically empty files before creating a run.
    if products_path.stat().st_size == 0:
        raise ValueError("Products CSV file is physically empty.")

    if orders_path.stat().st_size == 0:
        raise ValueError("Orders JSON file is physically empty.")

    # --------------------------------------
    # Execution metadata
    # --------------------------------------

    run_id = str(uuid4())

    checksum = calculate_combined_checksum(
        products_path,
        orders_path
    )

    peak_memory_mb = get_memory_usage_mb()

    results = {
        "run_id": run_id,
        "status": "RUNNING",
        "total_records": 0,
        "valid_records": 0,
        "rejected_records": 0
    }

    with SessionLocal() as session:

        recover_stale_runs(session)

        # ==================================
        # 6.1 IDEMPOTENCY CHECK
        # ==================================

        previous_run = session.scalar(
            select(PipelineRun).where(
                PipelineRun.file_checksum == checksum,
                PipelineRun.status == "SUCCESS"
            )
        )

        if previous_run:

            logger.info(
                "Identical source files were already processed."
            )

            return {
                "status": "SKIPPED",
                "message": "Identical source files were already processed.",
                "previous_run_id": previous_run.run_id
            }

        # ==================================
        # 6.2 CREATE PIPELINE RUN
        # ==================================

        create_pipeline_run(
            session,
            {
                "run_id": run_id,
                "file_name": (
                    f"{products_path.name} + {orders_path.name}"
                ),
                "file_checksum": checksum,
                "file_type": "CSV + JSON",
                "status": "RUNNING"
            }
        )

        session.commit()

        logger.info(
            "Pipeline started. Run ID: %s",
            run_id
        )

        try:

            # ==================================
            # 7. PROCESS PRODUCTS
            # ==================================

            logger.info("Starting product processing.")

            seen_product_ids = set()

            # Every valid product in the snapshot.
            present_product_ids = set()

            # Only ACTIVE products can be purchased.
            active_product_ids = set()

            product_batch_number = 0

            for batch in read_csv_in_chunks(
                products_path,
                DEFAULT_CHUNK_SIZE
            ):

                product_batch_number += 1

                transformed_products = []
                rejected = []

                # ----------------------------------
                # VALIDATE AND TRANSFORM
                # ----------------------------------

                for record in batch:

                    results["total_records"] += 1

                    valid_product, errors = validate_product(
                        record,
                        seen_product_ids
                    )

                    if errors:

                        rejected.append({
                            "record_id": record.get("product_id"),
                            "raw_record": record,
                            "errors": errors
                        })

                        continue

                    transformed_products.append(
                        transform_product(valid_product)
                    )

                    product_id = valid_product["product_id"]

                    present_product_ids.add(product_id)

                    if valid_product["status"] == "ACTIVE":
                        active_product_ids.add(product_id)

                # ----------------------------------
                # PUBLISH PRODUCTS
                # ----------------------------------

                published_count = publish_products(
                    session,
                    transformed_products
                )

                results["valid_records"] += published_count

                # ----------------------------------
                # STORE REJECTIONS
                # ----------------------------------

                rejected_count = publish_rejected_records(
                    session,
                    run_id,
                    products_path.name,
                    rejected
                )

                results["rejected_records"] += rejected_count

                session.commit()

                peak_memory_mb = max(
                    peak_memory_mb,
                    get_memory_usage_mb()
                )

                logger.info(
                    "Product batch %s | Valid: %s | Rejected: %s",
                    product_batch_number,
                    published_count,
                    rejected_count
                )

            # ----------------------------------
            # PRODUCT SNAPSHOT SAFETY CHECK
            # ----------------------------------

            if not present_product_ids:

                raise ValueError(
                    "Product snapshot contains no valid products. "
                    "Catalogue reconciliation cancelled."
                )

            logger.info(
                "Product processing completed. "
                "Present: %s | Active: %s",
                len(present_product_ids),
                len(active_product_ids)
            )

            # ----------------------------------
            # RECONCILE PRODUCT SNAPSHOT
            # ----------------------------------

            reconciled_count = reconcile_product_snapshot(
                session,
                present_product_ids,
                active_product_ids
            )

            session.commit()

            logger.info(
                "Product catalogue reconciliation completed. "
                "Products present: %s | Active: %s",
                reconciled_count,
                len(active_product_ids)
            )

            # ==================================
            # 8. PROCESS ORDERS
            # ==================================

            logger.info("Starting order processing.")

            seen_order_ids = set()

            processed_orders = 0
            order_batch_number = 0

            for batch in read_json_in_batches(
                orders_path,
                DEFAULT_JSON_BATCH_SIZE
            ):

                order_batch_number += 1

                rejected = []
                orders_to_publish = []
                raw_orders_by_id = {}

                # ----------------------------------
                # VALIDATE AND TRANSFORM
                # ----------------------------------

                for record in batch:

                    results["total_records"] += 1

                    valid_order, errors = validate_order(
                        record,
                        seen_order_ids,
                        active_product_ids
                    )

                    if errors:

                        rejected.append({
                            "record_id": record.get("order_id"),
                            "raw_record": record,
                            "errors": errors
                        })

                        continue

                    order_row, item_rows = transform_order(
                        valid_order
                    )

                    orders_to_publish.append(
                        (order_row, item_rows)
                    )

                    raw_orders_by_id[
                        order_row["order_id"]
                    ] = record

                # ----------------------------------
                # BULK PUBLISH
                # ----------------------------------

                published_count, failed_order_ids = publish_orders(
                    session,
                    orders_to_publish
                )

                results["valid_records"] += published_count

                # ----------------------------------
                # RECORD DATABASE FAILURES
                # ----------------------------------

                for order_id in failed_order_ids:

                    rejected.append({
                        "record_id": order_id,
                        "raw_record": raw_orders_by_id[order_id],
                        "errors": [
                            "Database publishing failed."
                        ]
                    })

                # ----------------------------------
                # STORE REJECTIONS
                # ----------------------------------

                rejected_count = publish_rejected_records(
                    session,
                    run_id,
                    orders_path.name,
                    rejected
                )

                results["rejected_records"] += rejected_count

                session.commit()

                processed_orders += len(batch)

                peak_memory_mb = max(
                    peak_memory_mb,
                    get_memory_usage_mb()
                )

                logger.info(
                    "Order batch %s | Processed: %s | "
                    "Valid: %s | Rejected: %s",
                    order_batch_number,
                    processed_orders,
                    published_count,
                    rejected_count
                )

            # ==================================
            # 9. COMPLETE PIPELINE
            # ==================================

            processing_time = time.perf_counter() - start_time

            results["status"] = "SUCCESS"

            results["processing_time"] = round(
                processing_time,
                4
            )

            results["peak_memory_mb"] = round(
                peak_memory_mb,
                2
            )

            update_pipeline_run(
                session,
                run_id,
                {
                    "status": "SUCCESS",
                    "total_records": results["total_records"],
                    "valid_records": results["valid_records"],
                    "rejected_records": results["rejected_records"],
                    "processing_time": processing_time,
                    "peak_memory_mb": peak_memory_mb,
                    "completed_at": utc_now()
                }
            )

            session.commit()

            logger.info("Pipeline completed successfully.")
            logger.info("Final results: %s", results)

            return results

        # ==================================
        # 10. FAILURE HANDLING
        # ==================================

        except BaseException:

            session.rollback()

            update_pipeline_run(
                session,
                run_id,
                {
                    "status": "FAILED",
                    "total_records": results["total_records"],
                    "valid_records": results["valid_records"],
                    "rejected_records": results["rejected_records"],
                    "processing_time": (
                        time.perf_counter() - start_time
                    ),
                    "peak_memory_mb": peak_memory_mb,
                    "completed_at": utc_now()
                }
            )

            session.commit()

            logger.exception("Pipeline execution failed.")

            raise