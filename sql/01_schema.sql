-- =============================================================================
-- Retail ETL Pipeline - DDL Schema Definition
-- Database: PostgreSQL
-- Schema: retail
-- =============================================================================

-- Create the dedicated application schema
CREATE SCHEMA IF NOT EXISTS retail;

-- -----------------------------------------------------------------------------
-- 1. STAGING TABLE (ELT / Inspection Layer)
-- -----------------------------------------------------------------------------
-- The staging table represents the raw ingested file structure.
-- Business integrity constraints (foreign keys, uniqueness) are deliberately NOT
-- enforced here so that raw, invalid, or duplicate data can be loaded, audited,
-- and reconciled without ingestion pipeline failure.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS retail.stg_store_sales (
    stg_id                      BIGSERIAL PRIMARY KEY,
    order_id                    VARCHAR(50),
    order_line_item             INTEGER,
    order_date                  DATE,
    customer_email              VARCHAR(255),
    customer_city               VARCHAR(100),
    store_code                  VARCHAR(50),
    product_sku                 VARCHAR(50),
    category                    VARCHAR(100),
    quantity                    INTEGER,
    unit_price                  NUMERIC(12, 2),
    store_discount              NUMERIC(12, 2),
    payment_gateway_discount    NUMERIC(12, 2),
    tax_amount                  NUMERIC(12, 2),
    amount_paid                 NUMERIC(12, 2),
    transaction_type            VARCHAR(50),
    loaded_at                   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. DIMENSION TABLES (Star Schema Conformed Dimensions)
-- -----------------------------------------------------------------------------

-- Customer Dimension
CREATE TABLE IF NOT EXISTS retail.dim_customer (
    customer_id                 SERIAL PRIMARY KEY,
    customer_email              VARCHAR(255) UNIQUE NOT NULL,
    customer_city               VARCHAR(100),
    created_at                  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Store Dimension
CREATE TABLE IF NOT EXISTS retail.dim_store (
    store_id                    SERIAL PRIMARY KEY,
    store_code                  VARCHAR(50) UNIQUE NOT NULL,
    store_city                  VARCHAR(100) NOT NULL
);

-- Product Dimension
CREATE TABLE IF NOT EXISTS retail.dim_product (
    product_id                  SERIAL PRIMARY KEY,
    product_sku                 VARCHAR(50) UNIQUE NOT NULL,
    category                    VARCHAR(100) NOT NULL
);

-- Date Dimension
CREATE TABLE IF NOT EXISTS retail.dim_date (
    date_id                     DATE PRIMARY KEY,
    year                        INTEGER NOT NULL,
    quarter                     INTEGER NOT NULL,
    month                       INTEGER NOT NULL,
    month_name                  VARCHAR(20) NOT NULL,
    day                         INTEGER NOT NULL,
    day_of_week                 INTEGER NOT NULL,
    day_name                    VARCHAR(20) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 3. FACT TABLE (Transactional Grain: One line per order item)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS retail.fact_sales (
    sales_id                    BIGSERIAL PRIMARY KEY,
    order_id                    VARCHAR(50) NOT NULL,
    order_line_item             INTEGER NOT NULL,
    order_date                  DATE NOT NULL REFERENCES retail.dim_date(date_id),
    customer_id                 INTEGER NOT NULL REFERENCES retail.dim_customer(customer_id),
    store_id                    INTEGER NOT NULL REFERENCES retail.dim_store(store_id),
    product_id                  INTEGER NOT NULL REFERENCES retail.dim_product(product_id),
    quantity                    INTEGER NOT NULL,
    unit_price                  NUMERIC(12, 2) NOT NULL,
    store_discount              NUMERIC(12, 2) NOT NULL,
    payment_gateway_discount    NUMERIC(12, 2) NOT NULL,
    tax_amount                  NUMERIC(12, 2) NOT NULL,
    amount_paid                 NUMERIC(12, 2) NOT NULL,
    transaction_type            VARCHAR(50) NOT NULL,
    source_loaded_at            TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Business grain uniqueness: strictly prevents duplicate line items
    CONSTRAINT uq_fact_sales_order_line UNIQUE (order_id, order_line_item)
);

-- -----------------------------------------------------------------------------
-- 4. INDEXES
-- -----------------------------------------------------------------------------
-- Indexes optimize analytical queries, aggregations, filtering, and joins:
-- - order_date: Enables fast date-range filtering and time-series rollups.
-- - customer_id: Speeds up customer lifetime value and churn analyses.
-- - store_id: Accelerates store-level sales ranking and aggregation.
-- - product_id: Speeds up product and category performance joins.
-- - transaction_type: Optimizes filtering on SALE vs RETURN transactions.
-- - order_id: Accelerates lookups for whole-order details and order-level aggregations.
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_date        ON retail.fact_sales(order_date);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_id       ON retail.fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_store_id          ON retail.fact_sales(store_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_id        ON retail.fact_sales(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_transaction_type  ON retail.fact_sales(transaction_type);
CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id          ON retail.fact_sales(order_id);

-- -----------------------------------------------------------------------------
-- 5. AUDIT & LOGGING TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS retail.etl_audit_log (
    audit_id                    BIGSERIAL PRIMARY KEY,
    audit_timestamp             TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    audit_name                  VARCHAR(100) NOT NULL,
    metric_name                 VARCHAR(100) NOT NULL,
    metric_value                NUMERIC(14, 2),
    status                      VARCHAR(50) NOT NULL,
    message                     TEXT
);
