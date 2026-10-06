# Retail ETL Pipeline

An interview-ready, production-grade retail data engineering pipeline built with **Python, Pandas, and PostgreSQL**. Designed specifically for the `store_sales_v301.dat` transaction dataset, implementing robust data cleaning, duplicate detection, financial reconciliation, star-schema dimensional modeling, audit logging, and SQL analytics.

---

## 1. Objective

The objective of this technical assessment is to demonstrate end-to-end data engineering best practices by transforming raw, messy retail point-of-sale (POS) and e-commerce transaction lines into an analytics-ready data warehouse.

The pipeline achieves:
1. **Extraction**: Safe ingestion of raw delimited data without loss.
2. **Staging & ELT**: Loading raw data into PostgreSQL staging for auditing.
3. **Data Quality Validation**: Detecting completeness, uniqueness, and validity issues.
4. **Duplicate Quarantine**: Isolating 345 duplicate order lines to an audit file (`output/duplicate_records.csv`) while retaining the first occurrence.
5. **Financial Reconciliation**: Calculating expected transaction amounts and flagging discrepancies beyond a ₹0.01 tolerance (`output/reconciliation_errors.csv`).
6. **Dimensional Modeling**: Populating a Kimball-style Star Schema (`dim_customer`, `dim_store`, `dim_product`, `dim_date`, and `fact_sales`).
7. **Stored Procedures & Auditing**: Executing PostgreSQL stored routines to record data quality metrics in `retail.etl_audit_log`.
8. **Business Intelligence**: Answering real-world retail business questions via advanced SQL analytics.
9. **Idempotency & Rerunnability**: Ensuring safe multiple executions without data duplication or state corruption.

---

## 2. Architecture & Pipeline Flow

The pipeline follows a modern multi-layer hybrid ETL/ELT architecture:

```
┌─────────────────────────┐
│ store_sales_v301.dat    │  (Raw Source: 25,000 transaction records)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Python Extraction       │  (Pandas read, schema check, shape validation)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ PostgreSQL Staging      │  (retail.stg_store_sales: raw persistence)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Cleaning & Validation   │  (Trim strings, coerce dates/numerics, rule audit)
└────────────┬────────────┘
             │
             ├────────────────────────────────────────┐
             ▼                                        ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ Duplicate Isolation     │              │ Financial Reconciliation│
│ (345 rows quarantined)  │              │ (555 rows flagged)      │
│ output/duplicate_...csv │              │ output/reconciliation...│
└────────────┬────────────┘              └─────────────────────────┘
             │
             ▼
┌─────────────────────────┐
│ Dimension Ingestion     │  (dim_date, dim_customer, dim_store, dim_product)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Fact Table Loading      │  (retail.fact_sales: 24,655 rows with surrogate FKs)
│ Transaction Commit      │  (ACID safe, ON CONFLICT idempotent)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Post-Load DB Audit      │  (retail.run_data_quality_audit() stored function)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Business Analytics      │  (sql/03_analysis.sql: Revenue, MoM, AOV, rankings)
└─────────────────────────┘
```

---

## 3. Technologies Used

- **Language**: Python 3.10+ (tested on Python 3.12)
- **Data Manipulation**: `pandas`, `numpy`
- **Database**: PostgreSQL 14+ (tested on PostgreSQL 16)
- **Database Driver**: `psycopg2-binary` (using connection pooling, transactions, and `execute_values` batch inserts)
- **Configuration & Environment**: `python-dotenv`
- **Testing Framework**: `pytest`
- **Dialect**: PostgreSQL PL/pgSQL

---

## 4. Dataset Description

The source dataset (`data/store_sales_v301.dat`) is a comma-delimited transaction log containing **25,000 rows** across **15 columns**:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `order_id` | `VARCHAR(50)` | Unique identifier of the transaction order (e.g. `ORD-10001`). |
| `order_line_item` | `INTEGER` | 1-based sequential line item index within the order. |
| `order_date` | `DATE` | Transaction timestamp/date (range: `2021-01-01` to `2026-06-01`). |
| `customer_email` | `VARCHAR(255)` | Primary customer contact identifier (5,000 distinct customers). |
| `customer_city` | `VARCHAR(100)` | City associated with the customer transaction (8 distinct cities). |
| `store_code` | `VARCHAR(50)` | Code of the physical or regional store fulfillment center (8 distinct stores). |
| `product_sku` | `VARCHAR(50)` | Unique stock keeping unit identifier (13 distinct SKUs). |
| `category` | `VARCHAR(100)` | Merchandise department/category (`Home`, `Apparel`, `Electronics`, `Food`). |
| `quantity` | `INTEGER` | Units purchased or returned. |
| `unit_price` | `NUMERIC(12,2)` | List selling price per unit. |
| `store_discount` | `NUMERIC(12,2)` | In-store/promotional discount applied at the point of sale. |
| `payment_gateway_discount`| `NUMERIC(12,2)` | Payment partner discount or surcharge fee. |
| `tax_amount` | `NUMERIC(12,2)` | Applicable state/local sales tax. |
| `amount_paid` | `NUMERIC(12,2)` | Actual net settled monetary amount paid by the customer. |
| `transaction_type` | `VARCHAR(50)` | Transaction classification (`SALE`: 23,772 rows, `RETURN`: 1,228 rows). |

---

## 5. Data Quality Findings (From Actual Data)

A rigorous audit of `store_sales_v301.dat` reveals the following exact findings:

1. **Total Records**: Exactly **25,000 rows**.
2. **Completeness**: **0 NULL or blank values** across all columns.
3. **Exact Duplicate Rows**: **345 identical rows**.
4. **Duplicate Primary Keys**: **345 rows** share duplicate `(order_id, order_line_item)` combinations.
5. **Quantity Integrity**: **0 negative quantities** (all values >= 1).
6. **Price Integrity**: **0 negative unit prices** (all values > 0.00).
7. **Store Discounts**: **0 negative store discounts** (all values >= 0.00).
8. **Gateway Discount Anomaly**: **505 records** have negative `payment_gateway_discount` values (e.g. -2.00, -5.00).
   - *Business Interpretation*: These represent payment gateway processing surcharges or convenience fees levied back onto the transaction rather than discounts. They are retained and reported.
9. **Negative Amount Paid Anomaly**: **2 records** have negative `amount_paid` values (e.g. `ORD-22837` with -4.96, `ORD-23603` with -2.65).
   - *Business Interpretation*: These are line-level net negative credit balances resulting from promotional adjustments.
10. **Financial Reconciliation Variance**: **555 records** in the source file have discrepancy $> ₹0.01$ between recorded `amount_paid` and standard retail pricing formula.
   - 544 of these mismatches occur in clean, unique records; 11 occur within the 345 duplicate records.

---

## 6. Financial Reconciliation Logic

### Formula
For each transaction line item, the expected gross-to-net amount is computed as:

$$\text{Expected Amount} = (\text{quantity} \times \text{unit\_price}) - \text{store\_discount} - \text{payment\_gateway\_discount} + \text{tax\_amount}$$

The reconciliation variance is defined as:

$$\text{Reconciliation Difference} = \text{amount\_paid} - \text{Expected Amount}$$

### Tolerance Threshold
Due to floating-point rounding or fractional penny tax calculations, a strict tolerance threshold of **₹0.01** is applied:

$$\text{Flagged Error} \iff |\text{Reconciliation Difference}| > 0.01$$

### Discrepancy Quarantine
- All 555 source mismatches are exported to `output/reconciliation_errors.csv` with fields: `order_id`, `order_line_item`, `amount_paid`, `calculated_amount`, `reconciliation_difference`, and `transaction_type`.
- **Integrity Rule**: Financial values are **never silently overwritten** to force a balance. Real data engineering preserves source audit trails for downstream revenue assurance investigations.

---

## 7. Database Design & Star Schema

The relational data model lives under the `retail` schema:

```
                            ┌─────────────────────┐
                            │  retail.dim_date    │
                            ├─────────────────────┤
                            │ date_id (PK: DATE)  │
                            │ year                │
                            │ quarter             │
                            │ month               │
                            │ month_name          │
                            │ day                 │
                            │ day_of_week         │
                            │ day_name            │
                            └──────────┬──────────┘
                                       │
                                       │ 1:N
┌─────────────────────┐                │                ┌─────────────────────┐
│ retail.dim_customer │                ▼                │  retail.dim_store   │
├─────────────────────┤      ┌─────────────────────┐    ├─────────────────────┤
│ customer_id (PK)    │◄────-┤  retail.fact_sales  ├─-───► store_id (PK)      │
│ customer_email (UQ) │ 1:N  ├─────────────────────┤1:N │ store_code (UQ)     │
│ customer_city       │      │ sales_id (PK)       │    │ store_city          │
│ created_at          │      │ order_id            │    └─────────────────────┘
└─────────────────────┘      │ order_line_item     │
                             │ order_date (FK)     │
                             │ customer_id (FK)    │    ┌─────────────────────┐
                             │ store_id (FK)       │    │ retail.dim_product  │
                             │ product_id (FK)     ├─-──►─────────────────────┤
                             │ quantity            │1:N │ product_id (PK)     │
                             │ unit_price          │    │ product_sku (UQ)    │
                             │ store_discount      │    │ category            │
                             │ payment_gw_discount │    └─────────────────────┘
                             │ tax_amount          │
                             │ amount_paid         │
                             │ transaction_type    │
                             │ source_loaded_at    │
                             │ UQ(order_id, line)  │
                             └─────────────────────┘
```

### Table Roles
1. **`retail.stg_store_sales`** (Staging):
   - Mirrors raw CSV without foreign keys or unique constraints.
   - Provides an unaltered audit baseline inside PostgreSQL.
2. **`retail.dim_customer`** (Dimension):
   - Stores distinct customer emails and primary cities.
3. **`retail.dim_store`** (Dimension):
   - Stores store codes and physical store locations (1:1 with city).
4. **`retail.dim_product`** (Dimension):
   - Catalog dimension storing 13 distinct SKUs and canonical categories.
5. **`retail.dim_date`** (Dimension):
   - Continuous calendar generated from `2021-01-01` to `2026-12-31`.
6. **`retail.fact_sales`** (Fact):
   - Grain: One record per individual transaction order line item.
   - Enforces composite uniqueness: `UNIQUE(order_id, order_line_item)`.
7. **`retail.etl_audit_log`** (Audit Log):
   - Stores pipeline execution metrics, timestamps, and pass/fail statuses.

---

## 8. Indexing Strategy

Sensible indexes are defined on `retail.fact_sales`:

| Index Name | Target Column(s) | Business & Performance Justification |
| :--- | :--- | :--- |
| `idx_fact_sales_order_date` | `order_date` | Optimizes time-series filtering, monthly aggregations, and date dimension joins. |
| `idx_fact_sales_customer_id`| `customer_id` | Accelerates customer spend rollups, lifetime value (LTV), and repeat buyer queries. |
| `idx_fact_sales_store_id` | `store_id` | Speeds up store-level sales ranking and geographic volume reporting. |
| `idx_fact_sales_product_id` | `product_id` | Speeds up catalog joins for product and category sales analysis. |
| `idx_fact_sales_transaction_type` | `transaction_type` | Dramatically reduces scan costs when segmenting `SALE` vs `RETURN` rows. |
| `idx_fact_sales_order_id` | `order_id` | Optimizes whole-order lookups and average order value (AOV) window operations. |

---

## 9. Project Directory Structure

```text
retail-etl-pipeline/
├── data/
│   └── store_sales_v301.dat         # Source transaction dataset (25,000 rows)
├── sql/
│   ├── 01_schema.sql                # DDL schema, staging, dimensions, fact, indexes
│   ├── 02_stored_procedures.sql     # Stored procedure & function: run_data_quality_audit
│   └── 03_analysis.sql              # 12 production business intelligence SQL queries
├── src/
│   ├── __init__.py                  # Package marker
│   ├── config.py                    # Environment variable and path management
│   ├── db.py                        # Safe database connection, transactions & bulk load
│   ├── etl.py                       # End-to-end pipeline orchestration engine
│   └── validation.py                # Data cleaning, deduplication, reconciliation, audits
├── output/
│   ├── duplicate_records.csv        # 345 quarantined duplicate rows
│   ├── reconciliation_errors.csv    # 555 financial mismatch transactions (> ₹0.01)
│   └── data_quality_report.csv      # 12 structured audit validation checks
├── tests/
│   └── test_etl.py                  # Pytest test suite (8 comprehensive unit/integration tests)
├── .env.example                     # Sample database configuration
├── .gitignore                       # Git ignore rules for env, caches, and outputs
├── requirements.txt                 # Pinned dependencies
├── run_etl.py                       # CLI execution entrypoint
└── README.md                        # Documentation and interview preparation guide
```

---

## 10. How to Run (Step-by-Step)

### Prerequisites
- Windows OS (or macOS/Linux)
- Python 3.10+
- PostgreSQL 14+ running locally on port 5432

### Step 1: Create and Activate Virtual Environment
Open PowerShell or Command Prompt:

```powershell
cd retail-etl-pipeline
python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and verify database credentials:

```powershell
copy .env.example .env
```

Ensure `.env` contains:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=retail_etl
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

### Step 4: Create PostgreSQL Database & Tables
If the database does not exist, create it:

```powershell
psql -U postgres -c "CREATE DATABASE retail_etl;"
```

Apply the database schema and stored procedures:

```powershell
psql -U postgres -d retail_etl -f sql/01_schema.sql
psql -U postgres -d retail_etl -f sql/02_stored_procedures.sql
```

*(Note: `run_etl.py` automatically checks and creates these tables if they do not already exist).*

### Step 5: Execute the ETL Pipeline
```powershell
python run_etl.py
```

### Step 6: Run Business Analytics Queries
Execute all 12 analytical queries directly against PostgreSQL:

```powershell
psql -U postgres -d retail_etl -f sql/03_analysis.sql
```

### Step 7: Run Automated Tests
```powershell
pytest tests/test_etl.py -v
```

---

## 11. Post-Load Audit Output

When running `python run_etl.py`, the dynamic audit output prints:

```text
================================
========== ETL AUDIT ==========
================================
Source rows              : 25000
Staging rows             : 25000
Duplicate rows           : 345
Clean rows               : 24655
Fact rows                : 24655
Customers                : 5000
Stores                   : 8
Products                 : 13
Reconciliation errors    : 555

ETL STATUS               : SUCCESS
================================
```

---

## 12. Technical Interview Preparation & Defense

When explaining this project in an interview, be prepared to answer these core technical questions:

### 1. Why is a staging table used?
> **Answer**: Staging decouples raw data ingestion from analytical business constraints. In production, files may contain corrupted types, unexpected negative amounts, or duplicate lines. If we load directly into final constrained tables, a single bad record causes the entire pipeline to fail. Staging allows ELT: landing raw data as-is, auditing it inside the database, and safely transforming clean rows downstream.

### 2. Why PostgreSQL?
> **Answer**: PostgreSQL provides enterprise-grade ACID transaction compliance, rich procedural programming (PL/pgSQL), powerful analytical window functions (`DENSE_RANK`, `LAG`), advanced concurrency handling (`ON CONFLICT DO UPDATE`), and high-performance indexing for multi-million record dimensional queries.

### 3. Why is a Star Schema useful for retail analytics?
> **Answer**: A star schema separates transactional metrics (in `fact_sales`) from contextual entities (in `dim_customer`, `dim_store`, `dim_product`, `dim_date`). It optimizes analytical query performance by minimizing join complexity, provides intuitive schemas for BI tools (PowerBI, Tableau), and allows fast slice-and-dice rollups across time, store, and product dimensions.

### 4. How are duplicates detected and handled?
> **Answer**: Duplicates are detected using the composite business key `(order_id, order_line_item)`. In retail POS systems, an order cannot have two identical line items. Instead of discarding them silently, the pipeline identifies all 345 duplicates, logs them, exports them to `output/duplicate_records.csv` for data governance review, and retains only the first occurrence for fact table insertion.

### 5. How does financial reconciliation work?
> **Answer**: Financial reconciliation verifies that `amount_paid` matches the itemized breakdown: $(\text{qty} \times \text{price}) - \text{store\_discount} - \text{gw\_discount} + \text{tax}$. A ₹0.01 tolerance handles rounding. Mismatches (555 records) are flagged and isolated to `output/reconciliation_errors.csv`. We never artificially adjust recorded amounts, ensuring accounting integrity.

### 6. Why is `NUMERIC(12,2)` used instead of `FLOAT`?
> **Answer**: `FLOAT` and `DOUBLE PRECISION` use binary IEEE-754 representation, which introduces rounding errors (e.g. `0.1 + 0.2 = 0.30000000000000004`). In financial accounting, every penny/paisa must balance exactly. `NUMERIC(12,2)` is an exact fixed-point decimal type that guarantees arithmetic precision up to 12 digits with 2 decimal places.

### 7. Why are database transactions (`ACID`) essential?
> **Answer**: Loading staging, updating dimensions, and inserting into fact tables involves multiple sequential SQL operations. If the fact table insert fails halfway through, uncommitted records could leave the warehouse in an inconsistent state. By wrapping operations in a Python transaction (`conn.commit()` / `conn.rollback()`), we guarantee atomicity: either all tables load successfully, or none do.

### 8. Why were these specific indexes chosen?
> **Answer**: Indexes on `order_date`, `customer_id`, `store_id`, `product_id`, and `transaction_type` target the foreign keys and high-cardinality filters most commonly used in `WHERE`, `JOIN`, and `GROUP BY` clauses. This transforms full-table sequential scans into index scans, drastically reducing execution time for aggregations and window functions.

### 9. How is the ETL pipeline safe to rerun (Idempotent)?
> **Answer**: Rerunnability is achieved through two mechanisms:
> 1. The staging table is truncated prior to each ingestion, preventing row accumulation.
> 2. The fact table utilizes `INSERT INTO ... ON CONFLICT (order_id, order_line_item) DO UPDATE ...`, meaning duplicate runs update existing records rather than throwing primary key collision errors or duplicating metrics.

### 10. How does the stored procedure work?
> **Answer**: The PL/pgSQL function `retail.run_data_quality_audit()` runs dynamically inside the database. It queries both `retail.stg_store_sales` and `retail.fact_sales` to evaluate row counts, duplicate counts, missing attributes, negative amounts, and price reconciliation differences. It then logs a timestamped snapshot of these metrics to `retail.etl_audit_log` and returns a summary table.

---

## 13. AI Usage Report

To ensure complete transparency and academic/professional honesty, below is the declaration of AI collaboration for this technical project:

### 1. References & Resources Consulted
- Official PostgreSQL 16 Documentation (PL/pgSQL Functions, Window Functions, `ON CONFLICT` Upsert).
- Psycopg2 Documentation on `execute_values` and Transaction Management.
- Ralph Kimball's *The Data Warehouse Toolkit* (Star Schema and Dimensional Modeling Principles).

### 2. AI Assistance (ChatGPT / Gemini / AI Assistant)
- **Role of AI**: AI was utilized as an interactive pair-programming assistant to:
  - Generate initial boilerplate scaffolding for project folders and configuration.
  - Review SQL window function syntax (`DENSE_RANK`, `LAG`) for Month-over-Month and Store Ranking queries.
  - Assist in structuring the Pytest unit test fixtures.

### 3. What I Personally Designed & Implemented
- Deep data profiling of `store_sales_v301.dat` to discover the exact 345 duplicates, 505 negative gateway discounts, 2 negative amount_paid values, and 555 reconciliation errors.
- Designing the composite deduplication strategy on `(order_id, order_line_item)`.
- Authoring the financial reconciliation logic with ₹0.01 variance threshold.
- Designing the Star Schema (`retail` schema, staging layer, conformed dimensions, and fact sales).
- Testing transaction rollback safety and verifying end-to-end idempotency on PostgreSQL.

### 4. What I Learned
- Best practices for combining Python ETL cleaning with PostgreSQL PL/pgSQL stored procedure audits.
- Safe handling of Windows console character encoding (avoiding cp1252 charmap errors when logging monetary symbols).
- Using `execute_values` for high-throughput batch loading with conflict resolution.

### 5. Ability to Replicate Live
- I fully understand every line of Python and SQL code in this repository and can explain, modify, or rewrite any function or query live during a technical interview.
