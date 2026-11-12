# Data Dictionary
## Scalable E-Commerce Data Processing Pipeline

### 1. Project Overview

This document defines the source datasets, target database schemas, data types, constraints, relationships, business rules and assumptions used by the Scalable E-Commerce Data Processing Pipeline.

The application processes e-commerce product and order datasets using memory-efficient ingestion and publishes validated records into a relational database.

### 2. Source Datasets

#### 2.1 Products Dataset

Source file: `products.csv`

| Field | Data Type | Nullable | Description |
|---|---|---|---|
| product_id | String | No | Unique product identifier |
| product_name | String | No | Product name |
| category | String | No | Product category |
| price | Decimal | No | Product selling price |
| stock_quantity | Integer | No | Available stock |
| status | String | No | Product availability status |

#### 2.2 Orders Dataset

Source file: `orders.json`

| Field | Data Type | Nullable | Description |
|---|---|---|---|
| order_id | String | No | Unique order identifier |
| order_date | Date | No | Date of order placement |
| order_status | String | No | Current order status |
| items | Array | No | Collection of products in the order |

#### 2.3 Order Items

Nested within the Orders dataset.

| Field | Data Type | Nullable | Description |
|---|---|---|---|
| product_id | String | No | Reference to product catalog |
| quantity | Integer | No | Number of units ordered |
| unit_price | Decimal | No | Price per unit at order time |

### 3. Target Database Schema

#### 3.1 products

Primary key: `product_id`

Stores validated and transformed product records.

#### 3.2 orders

Primary key: `order_id`

Stores validated order headers and calculated order totals.

#### 3.3 order_items

Primary key: `order_item_id`

Foreign keys:
- order_id references orders.order_id
- product_id references products.product_id

Stores individual products associated with each order.

#### 3.4 rejected_records

Primary key: `rejection_id`

Stores rejected source records, their originating file, execution reference and rejection reasons.

#### 3.5 pipeline_runs

Primary key: `run_id`

Stores execution metadata, processing statistics and operational metrics.

### 4. Business Rules

#### Product Validation

- Product identifiers must be present and unique.
- Product names and categories cannot be empty.
- Product prices cannot be negative.
- Stock quantities cannot be negative.
- Product status must be ACTIVE or INACTIVE.

#### Order Validation

- Order identifiers must be present and unique.
- Order dates must be valid.
- Order statuses must belong to the permitted set.
- Each order must contain at least one item.
- Referenced products must exist.
- Item quantities must be positive.
- Unit prices cannot be negative.
- An order containing an invalid item is rejected as a complete unit.

### 5. Transformation Rules

- Standardize product names and category values.
- Normalize status values to uppercase.
- Standardize date formats.
- Calculate item totals using quantity multiplied by unit price.
- Calculate order totals using the sum of item totals.

### 6. Assumptions

1. Product records are processed before order records.
2. Product IDs and order IDs are unique business identifiers.
3. The product catalog is the reference dataset for order validation.
4. An order is published only when all its items pass validation.
5. Original rejected records are retained for traceability.
6. Processing is deterministic and designed for safe reruns.
7. Source datasets may contain invalid, duplicate or inconsistent records.
8. The system supports CSV and nested JSON inputs.
9. Data is processed incrementally to maintain bounded application memory.

### 7. Idempotency

- SHA-256 checksums identify previously processed files.
- Primary keys and unique constraints prevent duplicate target records.
- Stable order item identifiers prevent duplicate item publishing.
- Failed executions are distinguished from successful executions.

### 8. Processing Metrics

The application captures:

- Total input records.
- Valid records.
- Rejected records.
- Published records.
- Processing duration.
- Peak memory consumption.
- Processing throughput.
- Number of chunks processed.

## Database relationships
Parent table-----Child table--------Relationship
products---------order_items--------One-to-Many
orders-----------order_items--------One-to-Many
pipeline_runs----rejected_records---One-to-Many


### Referential integrity:
- Every order item must reference an existing order.
- Every order item must reference an existing product.
- Every rejected record must reference an existing pipeline execution.