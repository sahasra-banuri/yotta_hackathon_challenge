import logging
import threading
import uuid

from datetime import datetime, timezone
from sqlalchemy import inspect
from backend.database.connection import engine
from backend.config import DATABASE_PATH

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from sqlalchemy import select, func, desc, text

from backend.database.connection import SessionLocal
from backend.database.models import (
    Product,
    Order,
    OrderItem,
    PipelineRun,
    RejectedRecord
)
from backend.pipeline import run_pipeline


# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Scalable E-Commerce Data Pipeline API",
    description=(
        "REST API for managing and monitoring "
        "the e-commerce data processing pipeline."
    ),
    version="1.1.0"
)

pipeline_lock = threading.Lock()

# In-memory execution tracking for background tasks.
pipeline_tasks = {}
task_lock = threading.Lock()


# ==========================================
# BACKGROUND PIPELINE EXECUTION
# ==========================================

def execute_pipeline(task_id: str):

    try:

        with task_lock:
            pipeline_tasks[task_id]["status"] = "RUNNING"

        logger.info(
            "Pipeline task started: %s",
            task_id
        )

        result = run_pipeline()

        if not isinstance(result, dict):
            result = {
                "status": "SUCCESS",
                "message": "Pipeline execution completed."
            }

        status = str(
            result.get("status", "SUCCESS")
        ).upper()

        run_id = result.get("run_id")

        # SKIPPED executions refer to a previous successful run.
        if status == "SKIPPED":
            run_id = result.get("previous_run_id")

        # Retrieve the latest database run if the pipeline
        # did not include its run ID in the return value.
        elif not run_id:

            with SessionLocal() as session:

                latest_run = session.scalars(
                    select(PipelineRun)
                    .order_by(desc(PipelineRun.started_at))
                    .limit(1)
                ).first()

                if latest_run:
                    run_id = latest_run.run_id

        with task_lock:

            pipeline_tasks[task_id].update({
                "status": status,
                "run_id": run_id,
                "previous_run_id": result.get("previous_run_id"),
                "message": result.get(
                    "message",
                    "Pipeline execution finished."
                ),
                "result": result,
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "error": None
            })

        logger.info(
            "Pipeline task completed: %s | Status: %s",
            task_id,
            status
        )

    except Exception as error:

        logger.exception(
            "Pipeline task failed: %s",
            task_id
        )

        with task_lock:

            pipeline_tasks[task_id].update({
                "status": "FAILED",
                "message": "Pipeline execution failed.",
                "error": str(error),
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat()
            })

    finally:

        pipeline_lock.release()


# ==========================================
# 1. HEALTH CHECK
# ==========================================

@app.get("/api/v1/health", tags=["System"])
def health_check():

    try:

        with SessionLocal() as session:
            session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "application": "E-Commerce Data Pipeline API",
            "database": "connected"
        }

    except Exception as error:

        logger.exception("Health check failed.")

        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(error)}"
        )


# ==========================================
# 2. TRIGGER PIPELINE
# ==========================================

@app.post("/api/v1/pipeline/run", tags=["Pipeline"])
def trigger_pipeline(background_tasks: BackgroundTasks):

    if not pipeline_lock.acquire(blocking=False):

        raise HTTPException(
            status_code=409,
            detail="A pipeline execution is already in progress."
        )

    try:

        task_id = str(uuid.uuid4())

        with task_lock:

            pipeline_tasks[task_id] = {
                "task_id": task_id,
                "status": "QUEUED",
                "run_id": None,
                "previous_run_id": None,
                "message": "Pipeline execution accepted.",
                "result": None,
                "error": None,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "completed_at": None
            }

        background_tasks.add_task(
            execute_pipeline,
            task_id
        )

        return {
            "task_id": task_id,
            "status": "QUEUED",
            "message": "Pipeline execution accepted."
        }

    except Exception:

        pipeline_lock.release()
        raise


# ==========================================
# 3. BACKGROUND TASK STATUS
# ==========================================

@app.get(
    "/api/v1/pipeline/tasks/{task_id}",
    tags=["Pipeline"]
)
def get_pipeline_task(task_id: str):

    with task_lock:

        task = pipeline_tasks.get(task_id)

        if task is None:

            raise HTTPException(
                status_code=404,
                detail="Pipeline task not found."
            )

        return dict(task)


# ==========================================
# 4. PIPELINE EXECUTION HISTORY
# ==========================================

@app.get("/api/v1/pipeline/runs", tags=["Pipeline"])
def get_pipeline_runs(

    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)

):

    with SessionLocal() as session:

        runs = session.scalars(
            select(PipelineRun)
            .order_by(desc(PipelineRun.started_at))
            .limit(limit)
            .offset(offset)
        ).all()

        total = session.scalar(
            select(func.count()).select_from(PipelineRun)
        )

        return {
            "total_runs": total,
            "limit": limit,
            "offset": offset,
            "runs": [
                {
                    "run_id": run.run_id,
                    "file_name": run.file_name,
                    "status": run.status,
                    "total_records": run.total_records,
                    "valid_records": run.valid_records,
                    "rejected_records": run.rejected_records,
                    "processing_time": (
                        float(run.processing_time)
                        if run.processing_time is not None
                        else None
                    ),
                    "peak_memory_mb": (
                        float(run.peak_memory_mb)
                        if run.peak_memory_mb is not None
                        else None
                    ),
                    "started_at": run.started_at,
                    "completed_at": run.completed_at
                }
                for run in runs
            ]
        }


# ==========================================
# 5. INDIVIDUAL PIPELINE RUN
# ==========================================

@app.get(
    "/api/v1/pipeline/runs/{run_id}",
    tags=["Pipeline"]
)
def get_pipeline_run(run_id: str):

    with SessionLocal() as session:

        run = session.get(PipelineRun, run_id)

        if run is None:

            raise HTTPException(
                status_code=404,
                detail="Pipeline execution not found."
            )

        return {
            "run_id": run.run_id,
            "file_name": run.file_name,
            "file_type": run.file_type,
            "status": run.status,
            "total_records": run.total_records,
            "valid_records": run.valid_records,
            "rejected_records": run.rejected_records,
            "processing_time": (
                float(run.processing_time)
                if run.processing_time is not None
                else None
            ),
            "peak_memory_mb": (
                float(run.peak_memory_mb)
                if run.peak_memory_mb is not None
                else None
            ),
            "started_at": run.started_at,
            "completed_at": run.completed_at
        }


# ==========================================
# 6. REJECTED RECORDS
# ==========================================

@app.get("/api/v1/rejections", tags=["Validation"])
def get_rejected_records(

    run_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0)

):

    with SessionLocal() as session:

        query = select(RejectedRecord)

        count_query = select(
            func.count()
        ).select_from(RejectedRecord)

        if run_id:

            query = query.where(
                RejectedRecord.run_id == run_id
            )

            count_query = count_query.where(
                RejectedRecord.run_id == run_id
            )

        records = session.scalars(
            query
            .order_by(desc(RejectedRecord.created_at))
            .limit(limit)
            .offset(offset)
        ).all()

        total = session.scalar(count_query)

        return {
            "total_rejections": total,
            "limit": limit,
            "offset": offset,
            "records": [
                {
                    "rejection_id": record.rejection_id,
                    "run_id": record.run_id,
                    "source_file": record.source_file,
                    "record_id": record.record_id,
                    "raw_record": record.raw_record,
                    "rejection_reason": record.rejection_reason,
                    "created_at": record.created_at
                }
                for record in records
            ]
        }

# ==========================================
# 7. DATABASE EXPLORER
# ==========================================

DATABASE_TABLES = {
    "products",
    "orders",
    "order_items",
    "rejected_records",
    "pipeline_runs"
}


@app.get("/api/v1/database/overview", tags=["Database"])
def database_overview():

    with SessionLocal() as session:

        inspector = inspect(engine)
        tables = []

        for table_name in sorted(DATABASE_TABLES):

            if not inspector.has_table(table_name):
                continue

            count = session.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar_one()

            columns = inspector.get_columns(table_name)

            tables.append({
                "table_name": table_name,
                "record_count": count,
                "columns": len(columns),
                "schema": [
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column["nullable"]
                    }
                    for column in columns
                ]
            })

        return {
            "database": DATABASE_PATH.name,
            "database_size_mb": (
                round(DATABASE_PATH.stat().st_size / (1024 * 1024), 2)
                if DATABASE_PATH.exists()
                else 0
            ),
            "table_count": len(tables),
            "tables": tables
        }


@app.get("/api/v1/database/tables/{table_name}", tags=["Database"])
def explore_database_table(
    table_name: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):

    if table_name not in DATABASE_TABLES:
        raise HTTPException(
            status_code=404,
            detail="Database table not found."
        )

    inspector = inspect(engine)

    if not inspector.has_table(table_name):
        raise HTTPException(
            status_code=404,
            detail="Database table does not exist."
        )

    with SessionLocal() as session:

        total = session.execute(
            text(f'SELECT COUNT(*) FROM "{table_name}"')
        ).scalar_one()

        rows = session.execute(
            text(
                f'SELECT * FROM "{table_name}" '
                f'LIMIT :limit OFFSET :offset'
            ),
            {
                "limit": limit,
                "offset": offset
            }
        ).mappings().all()

        return {
            "table_name": table_name,
            "total_records": total,
            "limit": limit,
            "offset": offset,
            "records": [
                dict(row) for row in rows
            ]
        }

# ==========================================
# 7. DATABASE STATISTICS
# ==========================================

@app.get("/api/v1/stats", tags=["Analytics"])
def get_database_statistics():

    with SessionLocal() as session:

        product_count = session.scalar(
            select(func.count()).select_from(Product)
        )

        order_count = session.scalar(
            select(func.count()).select_from(Order)
        )

        order_item_count = session.scalar(
            select(func.count()).select_from(OrderItem)
        )

        rejected_count = session.scalar(
            select(func.count()).select_from(RejectedRecord)
        )

        pipeline_run_count = session.scalar(
            select(func.count()).select_from(PipelineRun)
        )

        active_products = session.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.status == "ACTIVE")
        )

        return {
            "products": product_count,
            "active_products": active_products,
            "orders": order_count,
            "order_items": order_item_count,
            "rejected_records": rejected_count,
            "pipeline_runs": pipeline_run_count
        }