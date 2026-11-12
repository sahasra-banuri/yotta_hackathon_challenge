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
    DEFAULT_JSON_BATCH_SIZE
)

from backend.database.connection import SessionLocal

from backend.database.models import PipelineRun

from backend.database.publisher import (
    create_pipeline_run,
    update_pipeline_run,
    publish_products,
    publish_orders,
    publish_rejected_records
)

from backend.ingestion.csv_ingestion import read_csv_in_chunks
from backend.ingestion.json_ingestion import read_json_in_batches

from backend.processing.product_validator import validate_product
from backend.processing.order_validator import validate_order

from backend.processing.transform import (
    transform_product,
    transform_order
)

def utc_now():
    """
    Return current UTC time as a timezone-naive datetime.

    SQLite CURRENT_TIMESTAMP stores UTC timestamps without
    timezone information, so we use the same representation.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ==========================================
# 1. LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ==========================================
# 2. FILE CHECKSUM
# ==========================================

def calculate_checksum(file_path: Path) -> str:
    """
    Calculate SHA-256 checksum for a file.

    Reading the file in chunks avoids loading
    the entire file into memory.
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
    Generate one checksum representing both input files.
    """

    combined = hashlib.sha256()

    for file_path in (products_path, orders_path):

        checksum = calculate_checksum(file_path)

        combined.update(file_path.name.encode())
        combined.update(checksum.encode())

    return combined.hexdigest()


# ==========================================
# 3. MEMORY MONITORING
# ==========================================

def get_memory_usage_mb() -> float:
    """
    Return current process memory usage in MB.
    """

    process = psutil.Process()

    memory_bytes = process.memory_info().rss

    return memory_bytes / (1024 * 1024)

def recover_stale_runs(session):
    """
    Identify pipeline executions that have remained RUNNING
    beyond the configured timeout.

    Mark them as ABANDONED because their original execution
    did not record a final status.
    """

    from backend.config import STALE_RUN_TIMEOUT_MINUTES

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

        if run.processing_time is None and run.started_at:
            run.processing_time = (
                run.completed_at - run.started_at
            ).total_seconds()

        logger.warning(
            "Recovered stale pipeline run: %s",
            run.run_id
        )

        recovered_count += 1

    if recovered_count:
        session.commit()

        logger.info(
            "Stale pipeline recovery completed. "
            "Recovered runs: %s",
            recovered_count
        )

    return recovered_count

# ==========================================
# 4. MAIN PIPELINE
# ==========================================

def run_pipeline(
    products_path: Path | str | None = None,
    orders_path: Path | str | None = None
) -> dict:

    start_time = time.perf_counter()

    # --------------------------------------
    # Resolve input paths
    # --------------------------------------

    products_path = Path(
        products_path or SAMPLE_DATA_DIR / "products.csv"
    )

    orders_path = Path(
        orders_path or SAMPLE_DATA_DIR / "orders.json"
    )

    if not products_path.is_file():
        raise FileNotFoundError(products_path)

    if not orders_path.is_file():
        raise FileNotFoundError(orders_path)

    # --------------------------------------
    # Generate execution metadata
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

        # ==================================
        # 4.1 CHECK PREVIOUS EXECUTION
        # ==================================
        recover_stale_runs(session)
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
        # 4.2 CREATE PIPELINE RUN
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
            # 5. PROCESS PRODUCTS
            # ==================================

            logger.info("Starting product processing.")

            seen_product_ids = set()
            valid_product_ids = set()

            product_batch_number = 0

            for batch in read_csv_in_chunks(
                products_path,
                DEFAULT_CHUNK_SIZE
            ):

                product_batch_number += 1

                transformed_products = []
                rejected = []

                # ----------------------------------
                # VALIDATE AND TRANSFORM PRODUCTS
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

                    transformed = transform_product(valid_product)

                    transformed_products.append(transformed)

                    valid_product_ids.add(
                        valid_product["product_id"]
                    )

                # ----------------------------------
                # PUBLISH PRODUCTS
                # ----------------------------------

                published_count = publish_products(
                    session,
                    transformed_products
                )

                results["valid_records"] += published_count

                # ----------------------------------
                # STORE REJECTED PRODUCTS
                # ----------------------------------

                rejected_count = publish_rejected_records(
                    session,
                    run_id,
                    products_path.name,
                    rejected
                )

                results["rejected_records"] += rejected_count

                # ----------------------------------
                # COMMIT PRODUCT BATCH
                # ----------------------------------

                session.commit()

                peak_memory_mb = max(
                    peak_memory_mb,
                    get_memory_usage_mb()
                )

                logger.info(
                    "Product batch %s completed | "
                    "Valid: %s | Rejected: %s",
                    product_batch_number,
                    published_count,
                    rejected_count
                )

            logger.info(
                "Product processing completed. "
                "Valid product IDs: %s",
                len(valid_product_ids)
            )

            # ==================================
            # 6. PROCESS ORDERS
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
                # VALIDATE AND TRANSFORM ORDERS
                # ----------------------------------

                for record in batch:

                    results["total_records"] += 1

                    valid_order, errors = validate_order(
                        record,
                        seen_order_ids,
                        valid_product_ids
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
                # BULK PUBLISH ORDERS
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
                # STORE REJECTED ORDERS
                # ----------------------------------

                rejected_count = publish_rejected_records(
                    session,
                    run_id,
                    orders_path.name,
                    rejected
                )

                results["rejected_records"] += rejected_count

                # ----------------------------------
                # COMMIT ORDER BATCH
                # ----------------------------------

                session.commit()

                processed_orders += len(batch)

                peak_memory_mb = max(
                    peak_memory_mb,
                    get_memory_usage_mb()
                )

                logger.info(
                    "Order batch %s completed | "
                    "Processed: %s | Valid: %s | Rejected: %s",
                    order_batch_number,
                    processed_orders,
                    published_count,
                    rejected_count
                )

            logger.info(
                "Order processing completed. "
                "Total orders processed: %s",
                processed_orders
            )

            # ==================================
            # 7. COMPLETE PIPELINE RUN
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

            logger.info(
                "Final pipeline results: %s",
                results
            )

            return results

        # ==================================
        # 8. HANDLE PIPELINE FAILURE
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
                    "completed_at": datetime.now()
                }
            )

            session.commit()

            logger.exception(
                "Pipeline execution failed."
            )

            raise