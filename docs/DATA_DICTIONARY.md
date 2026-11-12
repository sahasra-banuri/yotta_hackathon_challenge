# Data Dictionary

## 1. Overview

The pipeline processes two primary datasets: Products and Orders.

### Products Dataset

**Source:** `data/sample/products.csv`
**Format:** CSV
**Purpose:** Represents the product catalogue.

| Field | Data Type | Description | Validation |
|---|---|---|---|
| product_id | String | Unique product identifier | Required, unique |
| product_name | String | Product name | Required, non-empty |
| category | String | Product category | Required, non-empty |
| price | Decimal | Product selling price | Finite and greater than zero |
| stock_quantity | Integer | Available stock quantity | Non-negative integer |
| status | String | Product availability status | ACTIVE or INACTIVE |

### Orders Dataset

**Source:** `data/sample/orders.json`
**Format:** JSON
**Purpose:** Represents customer orders and their associated items.

| Field | Data Type | Description | Validation |
|---|---|---|---|
| order_id | String | Unique order identifier | Required, unique |
| order_date | Date | Date the order was placed | Valid ISO date |
| order_status | String | Current order status | Must match configured statuses |
| items | Array | Products included in the order | Must contain at least one item |

### Order Items

Each order contains one or more item objects.

| Field | Data Type | Description | Validation |
|---|---|---|---|
| product_id | String | Referenced product identifier | Must exist and be ACTIVE |
| quantity | Integer | Number of units ordered | Positive integer |
| unit_price | Decimal | Price per unit at order time | Finite and greater than zero |

## 2. Configured Order Statuses

- PENDING
- CONFIRMED
- SHIPPED
- COMPLETED
- CANCELLED

All configured statuses are accepted. Order transition enforcement is not implemented.

## 3. Business Rules

### Product Rules

1. Product identifiers must be unique.
2. The first valid occurrence of a product ID is retained.
3. Invalid occurrences do not reserve an identifier.
4. Products missing from a successfully processed catalogue snapshot are marked INACTIVE.
5. Products are not physically deleted during reconciliation.

### Order Rules

1. Order identifiers must be unique.
2. The first valid occurrence of an order ID is retained.
3. Every order must contain at least one item.
4. Every referenced product must exist and be ACTIVE.
5. Duplicate product IDs within an order are not allowed.
6. If an item is invalid, the entire order is rejected.
7. Historical unit prices are preserved even when catalogue prices change.

### Inventory Rules

Stock quantity is informational. The pipeline does not decrement inventory or reject orders based on available stock.

## 4. Rejection Handling

Invalid records are persisted separately in the rejected-record storage.

Examples include:

- Missing mandatory identifiers.
- Invalid numerical values.
- Invalid statuses.
- Duplicate identifiers.
- Unknown product references.
- Inactive product references.
- Invalid order items.

## 5. Database Entities

The relational database contains the following main entities:

| Entity | Purpose |
|---|---|
| Product | Stores product catalogue records |
| Order | Stores valid orders |
| OrderItem | Stores individual items belonging to orders |
| RejectedRecord | Stores rejected input records and rejection information |
| PipelineRun | Stores pipeline execution metadata and operational metrics |

Relationships:

- One Order can contain multiple OrderItems.
- Each OrderItem references a Product.
- PipelineRun records execution-level information.
- RejectedRecord stores records that fail validation.
