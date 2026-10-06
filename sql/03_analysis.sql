-- =============================================================================
-- Retail ETL Pipeline - Business Analytics & Financial Insights
-- Database: PostgreSQL
-- Schema: retail
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Query 1: Overall Financial Summary (Net Sales, Returns, Total Revenue)
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*)                                            AS total_records,
    COUNT(DISTINCT order_id)                           AS unique_orders,
    SUM(CASE WHEN transaction_type = 'SALE' THEN amount_paid ELSE 0 END)   AS gross_sale_revenue,
    SUM(CASE WHEN transaction_type = 'RETURN' THEN amount_paid ELSE 0 END) AS return_amount,
    SUM(amount_paid)                                    AS net_revenue,
    AVG(amount_paid)                                    AS avg_transaction_value
FROM retail.fact_sales;

-- -----------------------------------------------------------------------------
-- Query 2: Sales and Transaction Volume by Store
-- -----------------------------------------------------------------------------
SELECT 
    s.store_code,
    s.store_city,
    COUNT(*)                                            AS total_transactions,
    COUNT(DISTINCT f.order_id)                          AS unique_orders,
    SUM(f.amount_paid)                                  AS total_sales,
    AVG(f.amount_paid)                                  AS avg_sale_amount
FROM retail.fact_sales f
JOIN retail.dim_store s ON f.store_id = s.store_id
GROUP BY s.store_code, s.store_city
ORDER BY total_sales DESC;

-- -----------------------------------------------------------------------------
-- Query 3: Sales by Product Category
-- -----------------------------------------------------------------------------
SELECT 
    p.category,
    SUM(f.quantity)                                     AS quantity_sold,
    SUM(f.amount_paid)                                  AS total_sales,
    ROUND(SUM(f.amount_paid) * 100.0 / SUM(SUM(f.amount_paid)) OVER (), 2) AS pct_of_total_sales
FROM retail.fact_sales f
JOIN retail.dim_product p ON f.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sales DESC;

-- -----------------------------------------------------------------------------
-- Query 4: Monthly Sales Performance (Using Date Dimension)
-- -----------------------------------------------------------------------------
SELECT 
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.order_id)                          AS unique_orders,
    SUM(f.quantity)                                     AS total_units_sold,
    SUM(f.amount_paid)                                  AS monthly_sales
FROM retail.fact_sales f
JOIN retail.dim_date d ON f.order_date = d.date_id
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year ASC, d.month ASC;

-- -----------------------------------------------------------------------------
-- Query 5: Top 10 Products by Total Sales Revenue
-- -----------------------------------------------------------------------------
SELECT 
    p.product_sku,
    p.category,
    SUM(f.quantity)                                     AS units_sold,
    SUM(f.amount_paid)                                  AS total_sales
FROM retail.fact_sales f
JOIN retail.dim_product p ON f.product_id = p.product_id
GROUP BY p.product_sku, p.category
ORDER BY total_sales DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Query 6: Top 10 Customers by Total Spend
-- -----------------------------------------------------------------------------
SELECT 
    c.customer_id,
    c.customer_email,
    c.customer_city,
    COUNT(DISTINCT f.order_id)                          AS orders_placed,
    SUM(f.quantity)                                     AS items_purchased,
    SUM(f.amount_paid)                                  AS total_spend
FROM retail.fact_sales f
JOIN retail.dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_email, c.customer_city
ORDER BY total_spend DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- Query 7: SALE vs RETURN Comparative Analysis
-- -----------------------------------------------------------------------------
SELECT 
    transaction_type,
    COUNT(*)                                            AS transaction_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)  AS pct_transactions,
    SUM(quantity)                                       AS total_quantity,
    SUM(amount_paid)                                    AS total_amount,
    ROUND(AVG(amount_paid), 2)                          AS avg_transaction_amount
FROM retail.fact_sales
GROUP BY transaction_type;

-- -----------------------------------------------------------------------------
-- Query 8: Average Order Value (AOV) by Store Location
-- -----------------------------------------------------------------------------
WITH order_aggregates AS (
    SELECT 
        f.store_id,
        f.order_id,
        SUM(f.amount_paid) AS order_total
    FROM retail.fact_sales f
    GROUP BY f.store_id, f.order_id
)
SELECT 
    s.store_code,
    s.store_city,
    COUNT(oa.order_id)                                  AS total_orders,
    SUM(oa.order_total)                                 AS total_sales,
    ROUND(SUM(oa.order_total) / COUNT(oa.order_id), 2)  AS avg_order_value
FROM order_aggregates oa
JOIN retail.dim_store s ON oa.store_id = s.store_id
GROUP BY s.store_code, s.store_city
ORDER BY avg_order_value DESC;

-- -----------------------------------------------------------------------------
-- Query 9: Store Performance Ranking (Window Function: DENSE_RANK)
-- -----------------------------------------------------------------------------
SELECT 
    s.store_code,
    s.store_city,
    SUM(f.amount_paid)                                  AS total_sales,
    COUNT(DISTINCT f.order_id)                          AS total_orders,
    DENSE_RANK() OVER (ORDER BY SUM(f.amount_paid) DESC) AS sales_rank
FROM retail.fact_sales f
JOIN retail.dim_store s ON f.store_id = s.store_id
GROUP BY s.store_code, s.store_city;

-- -----------------------------------------------------------------------------
-- Query 10: Product Ranking within Category (Window Function: RANK)
-- -----------------------------------------------------------------------------
WITH product_sales AS (
    SELECT 
        p.category,
        p.product_sku,
        SUM(f.amount_paid)                              AS sku_sales,
        SUM(f.quantity)                                 AS sku_units
    FROM retail.fact_sales f
    JOIN retail.dim_product p ON f.product_id = p.product_id
    GROUP BY p.category, p.product_sku
)
SELECT 
    category,
    product_sku,
    sku_sales,
    sku_units,
    RANK() OVER (PARTITION BY category ORDER BY sku_sales DESC) AS category_rank
FROM product_sales
ORDER BY category, category_rank;

-- -----------------------------------------------------------------------------
-- Query 11: Month-over-Month (MoM) Sales Growth Analysis (Window Function: LAG)
-- -----------------------------------------------------------------------------
WITH monthly_summary AS (
    SELECT 
        d.year,
        d.month,
        TO_CHAR(d.date_id, 'YYYY-MM')                   AS year_month,
        SUM(f.amount_paid)                              AS current_month_sales
    FROM retail.fact_sales f
    JOIN retail.dim_date d ON f.order_date = d.date_id
    GROUP BY d.year, d.month, TO_CHAR(d.date_id, 'YYYY-MM')
)
SELECT 
    year_month,
    current_month_sales,
    LAG(current_month_sales, 1) OVER (ORDER BY year, month) AS prev_month_sales,
    ROUND(
        (current_month_sales - LAG(current_month_sales, 1) OVER (ORDER BY year, month))
        * 100.0 / NULLIF(LAG(current_month_sales, 1) OVER (ORDER BY year, month), 0),
        2
    ) AS mom_growth_pct
FROM monthly_summary
ORDER BY year, month;

-- -----------------------------------------------------------------------------
-- Query 12: Financial Reconciliation Discrepancy Breakdown
-- Investigates records where the recorded amount_paid deviates from expected net
-- (quantity * unit_price - store_discount - payment_gateway_discount + tax_amount)
-- -----------------------------------------------------------------------------
WITH reconciliation_detail AS (
    SELECT 
        sales_id,
        order_id,
        order_line_item,
        transaction_type,
        amount_paid,
        (quantity * unit_price - store_discount - payment_gateway_discount + tax_amount) AS calculated_amount,
        ROUND(
            amount_paid - (quantity * unit_price - store_discount - payment_gateway_discount + tax_amount),
            2
        ) AS reconciliation_diff
    FROM retail.fact_sales
)
SELECT 
    transaction_type,
    COUNT(*)                                            AS total_variance_records,
    ROUND(AVG(reconciliation_diff), 2)                  AS avg_variance_amount,
    MIN(reconciliation_diff)                            AS max_negative_variance,
    MAX(reconciliation_diff)                            AS max_positive_variance,
    SUM(reconciliation_diff)                            AS net_unreconciled_impact
FROM reconciliation_detail
WHERE ABS(reconciliation_diff) > 0.01
GROUP BY transaction_type;
