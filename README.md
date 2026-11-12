# Scalable E-Commerce Data Pipeline

A Python-based e-commerce data pipeline designed to ingest, validate, transform, and publish product and order data into a relational database. The project includes a FastAPI backend, a Streamlit dashboard, automated testing, and performance monitoring.

## Overview

The pipeline processes product and order datasets from CSV and JSON files, applies configurable validation rules, transforms valid records, and publishes them into a SQLite database.

It also provides an interactive dashboard for pipeline execution, database exploration, data quality analysis, execution history, and performance monitoring.

## Key Features

- **Data Ingestion:** Reads product CSV files in configurable chunks and processes order JSON files using streaming ingestion.
- **Data Validation:** Validates product and order records against defined business rules.
- **Data Transformation:** Converts validated records into structured database-ready objects.
- **Database Publishing:** Stores products, orders, order items, rejected records, and pipeline execution details in SQLite.
- **Snapshot Reconciliation:** Updates product availability based on the latest product catalogue.
- **Duplicate Handling:** Prevents duplicate processing through record-level validation and file-checksum-based idempotency.
- **Error Handling:** Captures rejected records with reasons for rejection.
- **Execution Monitoring:** Tracks processing time, peak memory usage, record counts, and pipeline status.
- **REST API:** Exposes pipeline operations and database information through FastAPI.
- **Interactive Dashboard:** Provides a Streamlit interface for running and monitoring the pipeline.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Data Ingestion | Python CSV, ijson |
| Data Validation | Python |
| Database | SQLite |
| ORM | SQLAlchemy |
| Backend API | FastAPI |
| Frontend Dashboard | Streamlit |
| Performance Monitoring | psutil |
| Automated Testing | pytest |
| HTTP Requests | requests |

## Project Structure

```text
scalable_ecommerce_pipeline/
│
├── backend/
│   ├── api/
│   ├── database/
│   ├── ingestion/
│   ├── processing/
│   ├── config.py
│   ├── generate_medium_data.py
│   └── pipeline.py
│
├── data/
│   └── sample/
│       ├── products.csv
│       └── orders.json
│
├── docs/
│   └── DATA_DICTIONARY.md
│
├── frontend/
│   └── app.py
│
├── scripts/
│   └── Standalone verification scripts
│
├── tests/
│   └── Automated pytest test suite
│
├── .gitignore
├── README.md
└── requirements.txt
```

## Pipeline Workflow

```text
        Product CSV       Order JSON
              │               │
              └───────┬───────┘
                      │
                Data Ingestion
                      │
                Data Validation
                      │
               Data Transformation
                      │
               Database Publishing
                      │
                SQLite Database
                      │
             Execution Monitoring
                      │
             FastAPI Backend
                      │
             Streamlit Dashboard
```

## Business Rules

### Product Validation
- Product IDs must be present and unique.
- Product names and categories cannot be empty.
- Prices must be valid positive decimal values.
- Stock quantities must be non-negative integers.
- Product status must be either `ACTIVE` or `INACTIVE`.

### Order Validation
- Order IDs must be present and unique.
- Order dates must be valid ISO-formatted dates.
- Order status must belong to the configured set of valid statuses.
- Orders must contain at least one item.
- Referenced products must exist and be active.
- Item quantities and unit prices must be positive.
- Duplicate product IDs within an order are not allowed.
- An order containing an invalid item is rejected as a whole.

### Data Consistency
- Historical order-item prices are preserved.
- Product stock is treated as informational and is not automatically decremented.
- Missing products in a successfully processed product snapshot are marked inactive rather than deleted.
- Rejected records are stored with their validation errors.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sahasra-banuri/yotta_hackathon_challenge.git
cd yotta_hackathon_challenge
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

The application uses separate backend and frontend processes.

### 1. Start the FastAPI Backend

```bash
uvicorn backend.api.main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 2. Start the Streamlit Dashboard

Open another terminal, activate the virtual environment, and run:

```bash
streamlit run frontend/app.py
```

The dashboard will be available at:

```text
http://localhost:8501
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Check API and database health |
| POST | `/api/v1/pipeline/run` | Trigger pipeline execution |
| GET | `/api/v1/pipeline/tasks/{task_id}` | Check execution task status |
| GET | `/api/v1/pipeline/runs` | Retrieve pipeline execution history |
| GET | `/api/v1/pipeline/runs/{run_id}` | Retrieve details of a pipeline run |
| GET | `/api/v1/rejections` | Retrieve rejected records |
| GET | `/api/v1/stats` | Retrieve pipeline statistics |
| GET | `/api/v1/database/overview` | Retrieve database overview |
| GET | `/api/v1/database/tables/{table_name}` | Explore database table records |

## Testing

The project uses pytest for automated testing.

Run the complete test suite:

```bash
python -m pytest -v
```

**Latest test results:**

- Total automated tests: 94
- Tests passed: 94
- Tests failed: 0

The `scripts/` directory also contains standalone verification utilities separate from the automated pytest suite.

## Performance Benchmarks

The pipeline was evaluated using generated datasets of different sizes.

| Dataset Size | Valid Records | Rejected Records | Processing Time | Peak Memory |
|---|---:|---:|---:|---:|
| 20,000 | 20,000 | 0 | 6.87 seconds | 76.05 MB |
| 110,000 | 110,000 | 0 | 41.31 seconds | 86.73 MB |

These results represent local benchmark observations and may vary depending on hardware and execution conditions.

## Documentation

Refer to [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) for descriptions of the source datasets and their fields.

## Project Context

Developed as part of the YottaFlex 72-hour coding challenge, focusing on building a structured and scalable data processing pipeline with validation, database publishing, monitoring, and an interactive interface.