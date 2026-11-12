# Scalable E-Commerce Data Pipeline

A modular, batch-oriented data engineering pipeline designed to ingest, validate, transform, and publish e-commerce product and order data.

The project demonstrates data quality management, duplicate detection, idempotent execution, database publishing, operational monitoring, automated testing, and performance measurement.

## 1. Project Overview

The pipeline processes two input datasets:

- Products: CSV file containing product catalogue information.
- Orders: JSON file containing customer order and item details.

Records pass through ingestion, validation, transformation, and publishing stages. Invalid records are captured separately for inspection, while valid records are stored in a relational database.

A FastAPI backend exposes pipeline operations and database information. A Streamlit dashboard provides an interface for execution, monitoring, data exploration, and performance analysis.

## 2. Architecture

```text
                  INPUT DATA
              Products CSV | Orders JSON
                         |
                         v
                    INGESTION
             CSV Reader | JSON Reader
                         |
                         v
                    VALIDATION
             Schema and Business Rules
                    /          \
                   /            \
                  v              v
          VALID RECORDS     REJECTED RECORDS
                  |              |
                  v              v
             TRANSFORMATION   Rejection Storage
                  |
                  v
                PUBLISHING
                  |
                  v
              SQLite Database
                  |
          +-------+--------+
          |                |
          v                v
      FastAPI API     Monitoring
          |
          v
     Streamlit Dashboard
```

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Data ingestion | Python CSV, ijson |
| Validation | Python, Decimal |
| Database | SQLite |
| Database interaction | SQLAlchemy |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Automated testing | pytest |
| Performance monitoring | psutil |
| Version control | Git |

## 4. Project Structure

```text
scalable_ecommerce_pipeline/
│
├── backend/
│   ├── api/
│   ├── database/
│   ├── ingestion/
│   ├── processing/
│   ├── config.py
│   ├── pipeline.py
│   └── generate_medium_data.py
│
├── frontend/
│   └── app.py
│
├── data/
│   ├── sample/
│   │   ├── products.csv
│   │   └── orders.json
│   └── generated/
│
├── tests/
├── scripts/
├── docs/
│   ├── DATA_DICTIONARY.md
│   └── DESIGN_NOTES.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

## 5. Setup Instructions

### Prerequisites

- Python 3.10 or later
- Git
- Windows, Linux, or macOS

### Clone the repository

```bash
git clone <repository-url>
cd scalable_ecommerce_pipeline
```

### Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Run database initialization

```bash
python -m backend.database.init_db
```

### Execute the pipeline

From the project root:

```bash
python -c "from backend.pipeline import run_pipeline; print(run_pipeline())"
```

### Run automated tests

```bash
python -m pytest -v
```

### Start the API

```bash
uvicorn backend.api.main:app --reload
```

### Start the dashboard

In a separate terminal:

```bash
streamlit run frontend/app.py
```

## 6. Data Validation

The pipeline applies schema-level and business-rule validation.

**Product validation**
- Product IDs must be present and unique.
- Product name and category must not be empty.
- Price must be a finite positive decimal.
- Stock quantity must be a non-negative integer.
- Status must be ACTIVE or INACTIVE.

**Order validation**
- Order IDs must be present and unique.
- Order dates must be valid ISO dates.
- Order status must belong to the configured status set.
- Orders must contain at least one item.
- Referenced products must exist and be active.
- Item quantities and unit prices must be positive.
- Duplicate product IDs within an order are rejected.
- An order is rejected if any of its items are invalid.

Invalid records are stored separately in the rejection table.

## 7. Reliability and Idempotency

- SHA-256 checksums identify previously processed input combinations.
- Reprocessing identical inputs after a successful run returns SKIPPED.
- Duplicate product and order identifiers are handled.
- Product catalogue reconciliation deactivates missing products instead of deleting them.
- Stale RUNNING executions are identified and marked ABANDONED.
- Failed pipeline executions are recorded.

The current implementation supports safe re-execution but does not implement checkpoint-based resumption or a dedicated backfill scheduler.

## 8. Performance Results

The following measurements were obtained during local execution.

| Workload | Records | Processing Time | Peak Memory |
|---|---:|---:|---:|
| Small | 14 | 0.05 sec | 53.41 MB |
| Medium | 20,000 | 6.87 sec | 76.05 MB |
| Large | 110,000 | 41.31 sec | 86.73 MB |

The small workload was validation-oriented and included rejected records. These measurements are initial local benchmarks, not controlled production scalability tests.

## 9. Testing

Automated tests are implemented using pytest.

The latest reported test execution completed with:

- Total tests passed: 99
- Failed tests: 0

The test suite covers validation, ingestion, database operations, publishing, and transformation.

Run tests using:

```bash
python -m pytest -v
```

## 10. Documentation

Additional documentation:

- `docs/DATA_DICTIONARY.md` — Dataset schemas, field definitions, and business rules.
- `docs/DESIGN_NOTES.md` — Architecture decisions, trade-offs, reliability behavior, and limitations.

## 11. Future Improvements

- Object storage integration.
- Dedicated Raw, Validated, and Curated storage zones.
- Partitioned data storage.
- Checkpoint-based restart and recovery.
- Dedicated replay and backfill workflows.
- More extensive performance benchmarking.
- Automated deployment and orchestration.

## 12. License

Specify the intended repository license before public distribution.