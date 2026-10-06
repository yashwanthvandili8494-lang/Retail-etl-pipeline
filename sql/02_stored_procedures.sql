-- =============================================================================
-- Retail ETL Pipeline - Stored Procedures & Functions
-- Database: PostgreSQL
-- Schema: retail
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. FUNCTION: populate_dim_date
-- Populates the date dimension table across a specified contiguous date range.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION retail.populate_dim_date(
    p_start_date DATE DEFAULT '2021-01-01',
    p_end_date   DATE DEFAULT '2026-12-31'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_inserted INTEGER := 0;
BEGIN
    INSERT INTO retail.dim_date (
        date_id,
        year,
        quarter,
        month,
        month_name,
        day,
        day_of_week,
        day_name
    )
    SELECT
        d::DATE                                    AS date_id,
        EXTRACT(YEAR FROM d)::INTEGER              AS year,
        EXTRACT(QUARTER FROM d)::INTEGER           AS quarter,
        EXTRACT(MONTH FROM d)::INTEGER             AS month,
        TRIM(TO_CHAR(d, 'Month'))                  AS month_name,
        EXTRACT(DAY FROM d)::INTEGER               AS day,
        EXTRACT(ISODOW FROM d)::INTEGER            AS day_of_week,
        TRIM(TO_CHAR(d, 'Day'))                    AS day_name
    FROM generate_series(p_start_date::timestamp, p_end_date::timestamp, '1 day'::interval) AS s(d)
    ON CONFLICT (date_id) DO NOTHING;

    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;
    RETURN v_rows_inserted;
END;
$$;

-- -----------------------------------------------------------------------------
-- 2. FUNCTION / PROCEDURE: run_data_quality_audit
-- Computes and logs essential data quality and financial reconciliation metrics
-- into the audit log table `retail.etl_audit_log`, returning the summary report.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION retail.run_data_quality_audit(
    p_batch_name VARCHAR DEFAULT 'POST_LOAD_AUDIT'
)
RETURNS TABLE (
    metric_name     VARCHAR(100),
    metric_value    NUMERIC(14, 2),
    status          VARCHAR(50),
    message         TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_staging_count         BIGINT;
    v_fact_count            BIGINT;
    v_cust_count            BIGINT;
    v_store_count           BIGINT;
    v_prod_count            BIGINT;
    v_dup_count             BIGINT;
    v_null_count            BIGINT;
    v_neg_amt_count         BIGINT;
    v_neg_gw_count          BIGINT;
    v_recon_mismatch_count  BIGINT;
    v_orphan_facts          BIGINT;
BEGIN
    -- 1. Source / Staging rows
    SELECT COUNT(*) INTO v_staging_count FROM retail.stg_store_sales;

    -- 2. Fact sales rows
    SELECT COUNT(*) INTO v_fact_count FROM retail.fact_sales;

    -- 3. Dimensions
    SELECT COUNT(*) INTO v_cust_count FROM retail.dim_customer;
    SELECT COUNT(*) INTO v_store_count FROM retail.dim_store;
    SELECT COUNT(*) INTO v_prod_count FROM retail.dim_product;

    -- 4. Duplicate (order_id, order_line_item) in staging
    SELECT COALESCE(SUM(dup_count - 1), 0)
    INTO v_dup_count
    FROM (
        SELECT order_id, order_line_item, COUNT(*) AS dup_count
        FROM retail.stg_store_sales
        GROUP BY order_id, order_line_item
        HAVING COUNT(*) > 1
    ) sub;

    -- 5. Null mandatory fields in staging
    SELECT COUNT(*) INTO v_null_count
    FROM retail.stg_store_sales
    WHERE order_id IS NULL
       OR order_line_item IS NULL
       OR order_date IS NULL
       OR customer_email IS NULL
       OR store_code IS NULL
       OR product_sku IS NULL
       OR quantity IS NULL
       OR unit_price IS NULL
       OR amount_paid IS NULL;

    -- 6. Negative amount_paid in staging
    SELECT COUNT(*) INTO v_neg_amt_count
    FROM retail.stg_store_sales
    WHERE amount_paid < 0;

    -- 7. Negative payment_gateway_discount in staging (business rule inspection)
    SELECT COUNT(*) INTO v_neg_gw_count
    FROM retail.stg_store_sales
    WHERE payment_gateway_discount < 0;

    -- 8. Financial reconciliation mismatches in staging (|difference| > 0.01)
    SELECT COUNT(*) INTO v_recon_mismatch_count
    FROM retail.stg_store_sales
    WHERE ABS(
        amount_paid - (
            (quantity * unit_price)
            - store_discount
            - payment_gateway_discount
            + tax_amount
        )
    ) > 0.01;

    -- 9. Check for orphan foreign keys in fact_sales
    SELECT COUNT(*) INTO v_orphan_facts
    FROM retail.fact_sales f
    LEFT JOIN retail.dim_customer c ON f.customer_id = c.customer_id
    LEFT JOIN retail.dim_store s    ON f.store_id = s.store_id
    LEFT JOIN retail.dim_product p  ON f.product_id = p.product_id
    LEFT JOIN retail.dim_date d     ON f.order_date = d.date_id
    WHERE c.customer_id IS NULL
       OR s.store_id IS NULL
       OR p.product_id IS NULL
       OR d.date_id IS NULL;

    -- Insert metrics into retail.etl_audit_log
    INSERT INTO retail.etl_audit_log (audit_name, metric_name, metric_value, status, message)
    VALUES
        (p_batch_name, 'staging_row_count', v_staging_count, 'INFO', 'Total rows ingested into staging table'),
        (p_batch_name, 'fact_row_count', v_fact_count, 'INFO', 'Total valid rows loaded into fact_sales'),
        (p_batch_name, 'dim_customer_count', v_cust_count, 'INFO', 'Unique customer profiles loaded'),
        (p_batch_name, 'dim_store_count', v_store_count, 'INFO', 'Unique retail store locations loaded'),
        (p_batch_name, 'dim_product_count', v_prod_count, 'INFO', 'Unique catalog products loaded'),
        (p_batch_name, 'staging_duplicate_count', v_dup_count,
            CASE WHEN v_dup_count = 0 THEN 'PASSED' ELSE 'WARNING' END,
            'Duplicate order line items identified in raw dataset'),
        (p_batch_name, 'null_critical_count', v_null_count,
            CASE WHEN v_null_count = 0 THEN 'PASSED' ELSE 'FAILED' END,
            'Records missing critical mandatory attributes'),
        (p_batch_name, 'negative_amount_paid_count', v_neg_amt_count,
            CASE WHEN v_neg_amt_count = 0 THEN 'PASSED' ELSE 'WARNING' END,
            'Transactions with negative amount_paid (charge adjustments/credits)'),
        (p_batch_name, 'negative_payment_gateway_discount_count', v_neg_gw_count,
            CASE WHEN v_neg_gw_count = 0 THEN 'PASSED' ELSE 'WARNING' END,
            'Transactions with negative gateway discount (gateway surcharges)'),
        (p_batch_name, 'financial_reconciliation_mismatches', v_recon_mismatch_count,
            CASE WHEN v_recon_mismatch_count = 0 THEN 'PASSED' ELSE 'WARNING' END,
            'Transactions with price reconciliation variance > ₹0.01'),
        (p_batch_name, 'orphan_fact_records', v_orphan_facts,
            CASE WHEN v_orphan_facts = 0 THEN 'PASSED' ELSE 'FAILED' END,
            'Fact table records with missing dimensional foreign keys');

    -- Return the metrics for immediate inspection
    RETURN QUERY
    SELECT l.metric_name, l.metric_value, l.status, l.message
    FROM retail.etl_audit_log l
    WHERE l.audit_name = p_batch_name
      AND l.audit_timestamp >= NOW() - INTERVAL '1 minute'
    ORDER BY l.audit_id ASC;
END;
$$;

-- Procedure wrapper for CALL syntax
CREATE OR REPLACE PROCEDURE retail.sp_run_data_quality_audit(
    p_batch_name VARCHAR DEFAULT 'POST_LOAD_AUDIT'
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM retail.run_data_quality_audit(p_batch_name);
END;
$$;
