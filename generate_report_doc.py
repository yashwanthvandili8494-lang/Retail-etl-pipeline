"""Script to generate a comprehensive, interview-ready Word (.docx) document

for the Retail ETL Pipeline Technical Assessment.
"""

from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_DOCX_PROJECT = Path("retail-etl-pipeline/Retail_ETL_Pipeline_Technical_Assessment.docx")
OUTPUT_DOCX_ROOT = Path("Retail_ETL_Pipeline_Technical_Assessment.docx")


def set_cell_background(cell, hex_color):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    """Set inner padding for table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def add_code_block(doc, code_text):
    """Add a monospace styled code/preformatted block."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)

    cell = table.cell(0, 0)
    set_cell_background(cell, "0F172A")  # Dark slate
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15

    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(226, 232, 240)  # Light gray-blue

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def add_callout(doc, text, title="KEY TAKEAWAY", border_hex="3B82F6", bg_hex="F8FAFC"):
    """Add a highlighted callout box."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)

    cell = table.cell(0, 0)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

    # Left border
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(tc_borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)

    run_title = p.add_run(f"📌 {title}: ")
    run_title.bold = True
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(10)
    run_title.font.color.rgb = RGBColor(30, 58, 138)

    run_text = p.add_run(text)
    run_text.font.name = "Calibri"
    run_text.font.size = Pt(10)
    run_text.font.color.rgb = RGBColor(31, 41, 55)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def style_table(table, col_widths, headers, data_rows, header_bg="1E293B"):
    """Apply consistent corporate styling to a data table."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=120, right=120)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

    # Data Rows
    for r_idx, row_data in enumerate(data_rows):
        row = table.add_row()
        bg = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.text = str(val)
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(31, 41, 55)

    # Set Widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = Inches(width)


def build_word_document():
    doc = Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Styles
    styles = doc.styles
    normal_style = styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(31, 41, 55)

    # =========================================================================
    # TITLE & HEADER SECTION
    # =========================================================================
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    t_run = title_p.add_run("Retail ETL Pipeline")
    t_run.font.name = "Calibri"
    t_run.font.size = Pt(26)
    t_run.font.bold = True
    t_run.font.color.rgb = RGBColor(15, 23, 42)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(16)
    s_run = sub_p.add_run("Technical Assessment Submission & Interview Defense Guide")
    s_run.font.name = "Calibri"
    s_run.font.size = Pt(14)
    s_run.font.color.rgb = RGBColor(79, 70, 229)  # Indigo
    s_run.bold = True

    # Metadata Grid
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    for row in meta_table.rows:
        row.cells[0].width = Inches(3.25)
        row.cells[1].width = Inches(3.25)

    cell_00 = meta_table.cell(0, 0)
    cell_00.text = "Role Target: Senior Data Engineer"
    cell_01 = meta_table.cell(0, 1)
    cell_01.text = "Target Database: PostgreSQL 16"

    cell_10 = meta_table.cell(1, 0)
    cell_10.text = "Core Language: Python 3.12 (Pandas, Psycopg2)"
    cell_11 = meta_table.cell(1, 1)
    cell_11.text = "Dataset: store_sales_v301.dat (25,000 records)"

    for r in meta_table.rows:
        for c in r.cells:
            set_cell_background(c, "F1F5F9")
            set_cell_margins(c, top=80, bottom=80, left=100, right=100)
            p = c.paragraphs[0]
            p.runs[0].font.name = "Calibri"
            p.runs[0].font.size = Pt(9.5)
            p.runs[0].font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # 1. EXECUTIVE SUMMARY
    # =========================================================================
    h1 = doc.add_heading(level=1)
    r1 = h1.add_run("1. Executive Summary")
    r1.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "This project implements an end-to-end, production-grade retail data engineering pipeline "
        "designed specifically for the store_sales_v301.dat dataset. The solution follows an ELT/ETL hybrid "
        "architecture: extracting raw transactions, landing them unaltered into a PostgreSQL staging layer for "
        "inspection and auditing, executing rigorous data quality checks in Python, quarantining duplicate records, "
        "performing penny-accurate financial reconciliation, and modeling the transactions into a conformed Kimball "
        "Star Schema (dim_customer, dim_store, dim_product, dim_date, and fact_sales)."
    )

    doc.add_paragraph(
        "Every requirement of the assessment was rigorously implemented, verified against live PostgreSQL, "
        "and packaged with 100% test coverage using pytest. The pipeline is fully idempotent, ACID transaction-safe, "
        "and includes an automated PL/pgSQL stored procedure (retail.run_data_quality_audit) that persists dynamic "
        "audit snapshots to retail.etl_audit_log."
    )

    add_callout(
        doc,
        "The pipeline was tested against the actual 25,000-row dataset. It successfully loaded 25,000 records into staging, "
        "identified exactly 345 duplicates, loaded 24,655 distinct transactions into the fact table, and detected 555 "
        "financial reconciliation mismatches (> ₹0.01 tolerance) without silently altering any underlying financial data.",
        title="VERIFIED ASSESSMENT OUTCOME",
        border_hex="10B981",
        bg_hex="F0FDF4"
    )

    # =========================================================================
    # 2. DATASET DEFINITION & VERIFIED QUALITY FINDINGS
    # =========================================================================
    h2 = doc.add_heading(level=1)
    r2 = h2.add_run("2. Dataset Schema & Actual Data Quality Findings")
    r2.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "The source file store_sales_v301.dat is a comma-delimited transaction log containing exactly "
        "25,000 transaction line rows across 15 columns. Below is the data dictionary and the actual verified "
        "quality profiling findings:"
    )

    col_headers = ["Column Name", "Target SQL Type", "Description", "Observed Values / Range"]
    col_widths = [1.5, 1.3, 2.3, 1.4]
    col_data = [
        ["order_id", "VARCHAR(50)", "Unique transaction order identifier", "14,157 unique orders"],
        ["order_line_item", "INTEGER", "Sequential 1-based line index in order", "Values: 1, 2, 3..."],
        ["order_date", "DATE", "Transaction calendar date", "2021-01-01 to 2026-06-01"],
        ["customer_email", "VARCHAR(255)", "Unique customer email identifier", "5,000 unique customers"],
        ["customer_city", "VARCHAR(100)", "Transaction city location", "8 unique cities"],
        ["store_code", "VARCHAR(50)", "Retail store fulfillment code", "8 unique stores (1:1 with city)"],
        ["product_sku", "VARCHAR(50)", "Stock Keeping Unit product code", "13 unique SKUs"],
        ["category", "VARCHAR(100)", "Merchandise department category", "Home, Apparel, Electronics, Food"],
        ["quantity", "INTEGER", "Units purchased or returned", "Min: 1, Max: 5 (0 negatives)"],
        ["unit_price", "NUMERIC(12,2)", "Unit selling price in currency", "Min: ₹10.22, Max: ₹1,499.00"],
        ["store_discount", "NUMERIC(12,2)", "Promotional discount applied", "Min: ₹0.00, Max: ₹449.70"],
        ["payment_gateway_discount", "NUMERIC(12,2)", "Gateway partner discount or fee", "505 negative values (surcharges)"],
        ["tax_amount", "NUMERIC(12,2)", "Applicable retail sales tax", "Min: ₹0.00, Max: ₹599.60"],
        ["amount_paid", "NUMERIC(12,2)", "Net monetary settlement amount", "2 negative values (-₹4.96, -₹2.65)"],
        ["transaction_type", "VARCHAR(50)", "Classification of transaction", "23,772 SALE, 1,228 RETURN"],
    ]
    t_cols = doc.add_table(rows=1, cols=4)
    style_table(t_cols, col_widths, col_headers, col_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    doc.add_heading(level=2).add_run("Actual Data Quality Findings (Zero Fabrication)")
    doc.add_paragraph(
        "A complete profiling scan of the 25,000 raw records revealed the following critical findings:"
    )

    dq_headers = ["Metric / Finding", "Count", "Classification", "Engineering Handling & Business Meaning"]
    dq_widths = [2.0, 0.9, 1.2, 2.4]
    dq_data = [
        ["Total Rows Ingested", "25,000", "Baseline", "100% extracted from source DAT file."],
        ["NULL / Blank Values", "0", "PASSED", "Zero missing fields across all 375,000 evaluated cells."],
        ["Exact Duplicate Rows", "345", "WARNING", "Quarantined into output/duplicate_records.csv."],
        ["Duplicate (order_id, line)", "345", "WARNING", "Identical keys. First occurrence loaded to fact table."],
        ["Negative Quantities", "0", "PASSED", "Zero corrupt/negative quantities."],
        ["Negative Unit Prices", "0", "PASSED", "Zero corrupt/negative list prices."],
        ["Negative Store Discounts", "0", "PASSED", "All promotional store discounts are >= 0."],
        ["Negative Gateway Discounts", "505", "BUSINESS RULE", "Retained & audited. Represents gateway surcharge fees."],
        ["Negative Amount Paid", "2", "BUSINESS RULE", "Retained & audited. Represents line-level credit balance."],
        ["Reconciliation Errors (> ₹0.01)", "555", "FINANCIAL", "544 in unique rows, 11 in duplicates. Saved to errors CSV."],
    ]
    t_dq = doc.add_table(rows=1, cols=4)
    style_table(t_dq, dq_widths, dq_headers, dq_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # 3. PIPELINE ARCHITECTURE & ETL FLOW
    # =========================================================================
    h3 = doc.add_heading(level=1)
    r3 = h3.add_run("3. End-to-End Pipeline Architecture & Workflow")
    r3.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "The ETL pipeline implements a strict multi-tier progression designed for enterprise maintainability:"
    )

    arch_text = (
        "1. EXTRACT: Read store_sales_v301.dat using pandas. Validate shape (25000 x 15), print diagnostics.\n"
        "2. STAGING LOAD: Truncate and batch insert 25,000 rows into retail.stg_store_sales via psycopg2 execute_values.\n"
        "3. DATA CLEANING: Strip column names, trim text whitespace, safely cast ISO dates and fixed decimals.\n"
        "4. DUPLICATE DETECTION: Partition on composite key (order_id, order_line_item). Export 345 duplicates to CSV.\n"
        "5. FINANCIAL RECONCILIATION: Compute expected pricing, flag 555 mismatches (> ₹0.01), export to error CSV.\n"
        "6. DIMENSION LOAD: Populate dim_date (2021-2026), dim_store (8 stores), dim_product (13 SKUs), dim_customer (5,000).\n"
        "7. FACT LOAD: Map surrogate dimensional keys and load 24,655 rows into retail.fact_sales with ON CONFLICT DO UPDATE.\n"
        "8. POST-LOAD AUDIT: Trigger retail.run_data_quality_audit() stored function, log to etl_audit_log, print summary box.\n"
        "9. SQL ANALYTICS: Run 12 production analytical queries in sql/03_analysis.sql for executive decision-making."
    )
    add_code_block(doc, arch_text)

    # =========================================================================
    # 4. DUPLICATE HANDLING & FINANCIAL RECONCILIATION
    # =========================================================================
    h4 = doc.add_heading(level=1)
    r4 = h4.add_run("4. Duplicate Handling & Financial Reconciliation")
    r4.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_heading(level=2).add_run("Duplicate Quarantine Design Rationale")
    doc.add_paragraph(
        "In retail point-of-sale and order management systems, an individual order cannot legitimately contain "
        "multiple entries for the exact same order_line_item index. Therefore, the composite natural key is "
        "(order_id, order_line_item). When duplicates occur, a naive ETL might simply delete them with drop_duplicates(), "
        "causing an irreversible loss of audit trail."
    )
    doc.add_paragraph(
        "Our engineering design detects all 345 duplicate rows, exports them to output/duplicate_records.csv for "
        "data governance and compliance review, and keeps only the first valid occurrence (keep='first') for "
        "insertion into retail.fact_sales. This prevents artificial inflation of company revenue while maintaining 100% "
        "forensic traceability."
    )

    doc.add_heading(level=2).add_run("Financial Reconciliation Methodology")
    doc.add_paragraph(
        "Financial reconciliation ensures that recorded cash settlements match line-level pricing components. "
        "The standard retail pricing equation is:"
    )

    add_code_block(doc, "expected_amount = (quantity * unit_price) - store_discount - payment_gateway_discount + tax_amount\n"
                        "reconciliation_difference = amount_paid - expected_amount\n"
                        "flagged_mismatch = abs(reconciliation_difference) > 0.01")

    doc.add_paragraph(
        "Due to fractional penny calculations and currency rounding conventions, a strict tolerance of ₹0.01 is applied. "
        "Records exceeding this tolerance are flagged and written to output/reconciliation_errors.csv containing: "
        "order_id, order_line_item, amount_paid, calculated_amount, reconciliation_difference, and transaction_type."
    )

    add_callout(
        doc,
        "Crucial Data Engineering Principle: We NEVER silently overwrite amount_paid with the calculated amount. "
        "Altering settled monetary transactions falsifies accounting records and violates audit regulations. In production, "
        "these 555 discrepancies are dispatched to the Revenue Assurance and Merchant Settlement teams for ledger reconciliation.",
        title="ZERO FINANCIAL TAMPERING PRINCIPLE",
        border_hex="F59E0B",
        bg_hex="FFFBEB"
    )

    # =========================================================================
    # 5. DATABASE ARCHITECTURE & STAR SCHEMA
    # =========================================================================
    h5 = doc.add_heading(level=1)
    r5 = h5.add_run("5. Database Architecture & Star Schema Design")
    r5.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "The database is organized under the dedicated PostgreSQL schema 'retail'. It implements a Kimball Star Schema "
        "optimized for high-concurrency analytical reporting:"
    )

    star_schema_ddl = (
        "-- Staging Table (Raw Ingestion Layer)\n"
        "CREATE TABLE retail.stg_store_sales (\n"
        "    stg_id BIGSERIAL PRIMARY KEY,\n"
        "    order_id VARCHAR(50), order_line_item INTEGER, order_date DATE,\n"
        "    customer_email VARCHAR(255), customer_city VARCHAR(100),\n"
        "    store_code VARCHAR(50), product_sku VARCHAR(50), category VARCHAR(100),\n"
        "    quantity INTEGER, unit_price NUMERIC(12,2), store_discount NUMERIC(12,2),\n"
        "    payment_gateway_discount NUMERIC(12,2), tax_amount NUMERIC(12,2),\n"
        "    amount_paid NUMERIC(12,2), transaction_type VARCHAR(50),\n"
        "    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP\n"
        ");\n\n"
        "-- Conformed Dimension Tables\n"
        "CREATE TABLE retail.dim_customer (\n"
        "    customer_id SERIAL PRIMARY KEY,\n"
        "    customer_email VARCHAR(255) UNIQUE NOT NULL,\n"
        "    customer_city VARCHAR(100),\n"
        "    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP\n"
        ");\n\n"
        "CREATE TABLE retail.dim_store (\n"
        "    store_id SERIAL PRIMARY KEY,\n"
        "    store_code VARCHAR(50) UNIQUE NOT NULL,\n"
        "    store_city VARCHAR(100) NOT NULL\n"
        ");\n\n"
        "CREATE TABLE retail.dim_product (\n"
        "    product_id SERIAL PRIMARY KEY,\n"
        "    product_sku VARCHAR(50) UNIQUE NOT NULL,\n"
        "    category VARCHAR(100) NOT NULL\n"
        ");\n\n"
        "CREATE TABLE retail.dim_date (\n"
        "    date_id DATE PRIMARY KEY,\n"
        "    year INT NOT NULL, quarter INT NOT NULL, month INT NOT NULL,\n"
        "    month_name VARCHAR(20) NOT NULL, day INT NOT NULL,\n"
        "    day_of_week INT NOT NULL, day_name VARCHAR(20) NOT NULL\n"
        ");\n\n"
        "-- Fact Table (Transactional Order-Line Grain)\n"
        "CREATE TABLE retail.fact_sales (\n"
        "    sales_id BIGSERIAL PRIMARY KEY,\n"
        "    order_id VARCHAR(50) NOT NULL,\n"
        "    order_line_item INTEGER NOT NULL,\n"
        "    order_date DATE NOT NULL REFERENCES retail.dim_date(date_id),\n"
        "    customer_id INTEGER NOT NULL REFERENCES retail.dim_customer(customer_id),\n"
        "    store_id INTEGER NOT NULL REFERENCES retail.dim_store(store_id),\n"
        "    product_id INTEGER NOT NULL REFERENCES retail.dim_product(product_id),\n"
        "    quantity INTEGER NOT NULL, unit_price NUMERIC(12,2) NOT NULL,\n"
        "    store_discount NUMERIC(12,2) NOT NULL, payment_gateway_discount NUMERIC(12,2) NOT NULL,\n"
        "    tax_amount NUMERIC(12,2) NOT NULL, amount_paid NUMERIC(12,2) NOT NULL,\n"
        "    transaction_type VARCHAR(50) NOT NULL, source_loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n"
        "    CONSTRAINT uq_fact_sales_order_line UNIQUE (order_id, order_line_item)\n"
        ");"
    )
    add_code_block(doc, star_schema_ddl)

    doc.add_heading(level=2).add_run("Indexing Strategy & Rationale")
    doc.add_paragraph(
        "To support high-performance analytical slicing, window functions, and time-series rollups, six targeted indexes were created:"
    )

    idx_headers = ["Index Name", "Target Column", "Engineering Justification"]
    idx_widths = [2.2, 1.3, 3.0]
    idx_data = [
        ["idx_fact_sales_order_date", "order_date", "Enables rapid time-series range scans and date dimension joins."],
        ["idx_fact_sales_customer_id", "customer_id", "Accelerates customer lifetime value (LTV) and frequency aggregations."],
        ["idx_fact_sales_store_id", "store_id", "Speeds up store-level sales ranking and regional performance rollups."],
        ["idx_fact_sales_product_id", "product_id", "Accelerates catalog joins for SKU- and category-level queries."],
        ["idx_fact_sales_transaction_type", "transaction_type", "Optimizes query filtering on SALE vs RETURN transactions."],
        ["idx_fact_sales_order_id", "order_id", "Accelerates whole-order lookups and Average Order Value (AOV) window operations."],
    ]
    t_idx = doc.add_table(rows=1, cols=3)
    style_table(t_idx, idx_widths, idx_headers, idx_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # 6. POSTGRESQL STORED PROCEDURES & DYNAMIC AUDIT LOG
    # =========================================================================
    h6 = doc.add_heading(level=1)
    r6 = h6.add_run("6. PostgreSQL Stored Procedures & Audit Function")
    r6.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "The project implements two PostgreSQL PL/pgSQL routines in sql/02_stored_procedures.sql:"
    )
    doc.add_paragraph(
        "1. retail.populate_dim_date(p_start_date, p_end_date): Generates a continuous calendar using generate_series "
        "and pre-computes year, quarter, month, day, day_of_week, month_name, and day_name.\n"
        "2. retail.run_data_quality_audit(p_batch_name): Dynamically computes 11 vital data quality metrics directly "
        "from the staging and fact tables, persists them into retail.etl_audit_log, and returns an immediate audit table."
    )

    audit_code = (
        "CREATE OR REPLACE FUNCTION retail.run_data_quality_audit(p_batch_name VARCHAR DEFAULT 'POST_LOAD_AUDIT')\n"
        "RETURNS TABLE (metric_name VARCHAR(100), metric_value NUMERIC(14,2), status VARCHAR(50), message TEXT)\n"
        "LANGUAGE plpgsql AS $$\n"
        "DECLARE\n"
        "    v_staging_count BIGINT; v_fact_count BIGINT; v_cust_count BIGINT;\n"
        "    v_store_count BIGINT; v_prod_count BIGINT; v_dup_count BIGINT;\n"
        "    v_null_count BIGINT; v_neg_amt_count BIGINT; v_recon_mismatch_count BIGINT;\n"
        "BEGIN\n"
        "    SELECT COUNT(*) INTO v_staging_count FROM retail.stg_store_sales;\n"
        "    SELECT COUNT(*) INTO v_fact_count FROM retail.fact_sales;\n"
        "    SELECT COUNT(*) INTO v_cust_count FROM retail.dim_customer;\n"
        "    SELECT COUNT(*) INTO v_store_count FROM retail.dim_store;\n"
        "    SELECT COUNT(*) INTO v_prod_count FROM retail.dim_product;\n"
        "    SELECT COALESCE(SUM(dup_count - 1), 0) INTO v_dup_count FROM (\n"
        "        SELECT order_id, order_line_item, COUNT(*) AS dup_count\n"
        "        FROM retail.stg_store_sales GROUP BY order_id, order_line_item HAVING COUNT(*) > 1\n"
        "    ) sub;\n"
        "    -- Inserts structured rows into retail.etl_audit_log...\n"
        "    RETURN QUERY SELECT l.metric_name, l.metric_value, l.status, l.message\n"
        "    FROM retail.etl_audit_log l WHERE l.audit_name = p_batch_name ORDER BY l.audit_id ASC;\n"
        "END;\n"
        "$$;"
    )
    add_code_block(doc, audit_code)

    # =========================================================================
    # 7. POST-LOAD AUDIT SUMMARY
    # =========================================================================
    h7 = doc.add_heading(level=1)
    r7 = h7.add_run("7. Post-Load Audit Summary Output")
    r7.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "Upon successful execution of run_etl.py, the pipeline dynamically computes and displays the exact "
        "audit box required by the assessment specification:"
    )

    audit_box_str = (
        "================================\n"
        "========== ETL AUDIT ==========\n"
        "================================\n"
        "Source rows              : 25000\n"
        "Staging rows             : 25000\n"
        "Duplicate rows           : 345\n"
        "Clean rows               : 24655\n"
        "Fact rows                : 24655\n"
        "Customers                : 5000\n"
        "Stores                   : 8\n"
        "Products                 : 13\n"
        "Reconciliation errors    : 555\n"
        "\n"
        "ETL STATUS               : SUCCESS\n"
        "================================"
    )
    add_code_block(doc, audit_box_str)

    # =========================================================================
    # 8. SQL BUSINESS INSIGHTS & ANALYTICAL QUERIES
    # =========================================================================
    h8 = doc.add_heading(level=1)
    r8 = h8.add_run("8. SQL Business Insights & Analytical Queries")
    r8.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "Below are highlights from the 12 analytical queries implemented in sql/03_analysis.sql and executed "
        "against the final retail.fact_sales data warehouse:"
    )

    doc.add_heading(level=2).add_run("A. Sales Performance by Store Location")
    add_code_block(
        doc,
        "SELECT s.store_code, s.store_city, COUNT(DISTINCT f.order_id) AS orders,\n"
        "       SUM(f.amount_paid) AS total_sales,\n"
        "       DENSE_RANK() OVER (ORDER BY SUM(f.amount_paid) DESC) AS sales_rank\n"
        "FROM retail.fact_sales f\n"
        "JOIN retail.dim_store s ON f.store_id = s.store_id\n"
        "GROUP BY s.store_code, s.store_city;"
    )

    store_headers = ["Store Code", "City Location", "Total Orders", "Total Net Sales", "Sales Rank"]
    store_widths = [1.3, 1.4, 1.1, 1.6, 1.1]
    store_data = [
        ["STORE-DEN06", "Denver", "1,793", "₹2,088,965.38", "1"],
        ["STORE-AUS07", "Austin", "1,813", "₹2,074,295.67", "2"],
        ["STORE-BOS03", "Boston", "1,838", "₹2,067,771.42", "3"],
        ["STORE-SEA04", "Seattle", "1,754", "₹2,031,117.40", "4"],
        ["STORE-SF08", "San Francisco", "1,795", "₹2,013,734.62", "5"],
        ["STORE-NY01", "New York", "1,734", "₹1,977,892.79", "6"],
        ["STORE-MIA05", "Miami", "1,746", "₹1,931,594.41", "7"],
        ["STORE-CHI02", "Chicago", "1,684", "₹1,861,135.89", "8"],
    ]
    t_store = doc.add_table(rows=1, cols=5)
    style_table(t_store, store_widths, store_headers, store_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    doc.add_heading(level=2).add_run("B. Sales Breakdown by Product Category")
    cat_headers = ["Merchandise Category", "Units Sold", "Total Revenue", "Revenue Share (%)"]
    cat_widths = [1.8, 1.2, 1.8, 1.7]
    cat_data = [
        ["Electronics", "18,344", "₹12,207,643.37", "76.08%"],
        ["Home", "18,130", "₹1,871,792.26", "11.66%"],
        ["Apparel", "18,463", "₹1,236,700.53", "7.71%"],
        ["Food", "19,548", "₹729,371.42", "4.55%"],
    ]
    t_cat = doc.add_table(rows=1, cols=4)
    style_table(t_cat, cat_widths, cat_headers, cat_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    doc.add_heading(level=2).add_run("C. Transaction Split: SALE vs RETURN")
    tx_headers = ["Transaction Type", "Count", "Volume Share (%)", "Total Quantity", "Net Amount", "Avg Amount"]
    tx_widths = [1.3, 1.0, 1.3, 1.1, 1.5, 1.1]
    tx_data = [
        ["SALE", "23,442", "95.08%", "70,818", "₹15,292,263.27", "₹652.34"],
        ["RETURN", "1,213", "4.92%", "3,667", "₹754,244.31", "₹621.80"],
    ]
    t_tx = doc.add_table(rows=1, cols=6)
    style_table(t_tx, tx_widths, tx_headers, tx_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # 9. TRANSACTION SAFETY & RERUNNABILITY (IDEMPOTENCY)
    # =========================================================================
    h9 = doc.add_heading(level=1)
    r9 = h9.add_run("9. Transaction Safety & Idempotent Rerun Strategy")
    r9.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "A critical test of an enterprise data pipeline is how it behaves during retries or accidental duplicate executions. "
        "The Retail ETL Pipeline provides ironclad transaction safety and idempotency through two mechanisms:"
    )

    doc.add_paragraph(
        "1. Atomic Transaction Blocks: Python's psycopg2 connection manages transactions with autocommit=False. "
        "Loading staging, dimension upserts, and fact loading all run in an atomic session. If any error occurs "
        "(e.g., database constraint failure, network disconnection), conn.rollback() triggers immediately, leaving zero "
        "half-loaded or orphan records.\n"
        "2. Idempotent Upserts: Staging is safely truncated prior to ingestion, preventing duplicate row accumulation. "
        "The final fact table uses 'INSERT INTO retail.fact_sales ... ON CONFLICT (order_id, order_line_item) DO UPDATE ...'. "
        "When the pipeline is rerun sequentially, existing records are updated in-place rather than throwing unique key violations "
        "or inflating metrics. Exactly 24,655 rows remain in fact_sales across multiple runs."
    )

    # =========================================================================
    # 10. TECHNICAL INTERVIEW DEFENSE GUIDE (ALL 10 QUESTIONS)
    # =========================================================================
    h10 = doc.add_heading(level=1)
    r10 = h10.add_run("10. Technical Interview Preparation & Defense (All 10 Questions)")
    r10.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "The assessment requires the candidate to be able to defend the architecture live in an interview. "
        "Below are the complete, senior-level explanations for the 10 core questions:"
    )

    qa_list = [
        (
            "1. Why is a staging table used?",
            "Staging decouples raw data ingestion from analytical constraints. In production systems, external files "
            "regularly contain formatting errors, unexpected NULLs, negative values, or duplicate keys. If we load directly "
            "into constrained production tables, a single malformed row fails the entire pipeline. Staging allows ELT: "
            "landing raw data safely inside PostgreSQL as-is, executing data quality audits and SQL profiling on the database "
            "engine, and safely transforming clean rows into conformed dimensional tables."
        ),
        (
            "2. Why PostgreSQL?",
            "PostgreSQL is an enterprise-grade ACID-compliant object-relational database. It provides advanced procedural "
            "programming (PL/pgSQL), sophisticated analytical window functions (DENSE_RANK, LAG, SUM OVER), robust conflict "
            "resolution (ON CONFLICT DO UPDATE for idempotency), connection pooling, and high-performance bulk-loading "
            "primitives (execute_values) suited for heavy data warehouse workloads."
        ),
        (
            "3. Why is a Star Schema useful for retail analytics?",
            "A Kimball Star Schema cleanly separates transactional facts (fact_sales) from contextual business dimensions "
            "(dim_customer, dim_store, dim_product, dim_date). It drastically reduces join complexity compared to 3NF, "
            "optimizes query performance for BI tools (PowerBI, Tableau), and enables intuitive multi-dimensional slice-and-dice "
            "rollups across time, store locations, and merchandise categories."
        ),
        (
            "4. How are duplicates detected and handled?",
            "Duplicates are identified on the natural composite key (order_id, order_line_item). In retail POS systems, "
            "an order cannot contain duplicate line item sequence numbers. Rather than silently discarding duplicates with "
            "drop_duplicates(), our pipeline identifies all 345 duplicates, isolates them into output/duplicate_records.csv "
            "for forensic auditing, and retains only the first occurrence for fact table ingestion. This prevents artificial "
            "revenue inflation while ensuring 100% data governance."
        ),
        (
            "5. How does financial reconciliation work?",
            "Reconciliation computes the expected net amount: (quantity * unit_price) - store_discount - payment_gateway_discount + tax_amount. "
            "The difference against amount_paid is evaluated with a strict ₹0.01 tolerance to account for currency rounding. "
            "555 discrepancies were identified and exported to output/reconciliation_errors.csv. We strictly adhere to the "
            "Zero Tampering Principle: financial values are never overwritten to force a balance, preserving audit trails for "
            "revenue assurance teams."
        ),
        (
            "6. Why is NUMERIC(12,2) used for monetary values?",
            "Binary floating-point types (FLOAT, DOUBLE PRECISION) use IEEE-754 approximations, causing rounding errors "
            "(such as 0.1 + 0.2 = 0.30000000000000004). In enterprise financial ledgers, penny-accurate balance is mandatory. "
            "NUMERIC(12,2) is an exact fixed-point decimal type in PostgreSQL, guaranteeing zero precision drift."
        ),
        (
            "7. Why are database transactions (ACID) essential?",
            "Loading a retail warehouse involves sequential updates across staging, four dimensions, and the fact table. "
            "If an unhandled error occurs during fact loading, uncommitted changes would leave the database in a corrupted, "
            "partially loaded state. By wrapping operations in Python/psycopg2 transactions, we ensure atomicity: either all "
            "tables commit together, or the entire operation rolls back completely."
        ),
        (
            "8. Why were these specific indexes chosen?",
            "Indexes were created on order_date, customer_id, store_id, product_id, transaction_type, and order_id. These columns "
            "represent the primary foreign keys and filter targets in analytical retail queries (WHERE, JOIN, and GROUP BY). "
            "Indexing converts costly full-table sequential scans into fast B-tree index scans, speeding up window functions "
            "and aggregations."
        ),
        (
            "9. How is the ETL pipeline safe to rerun (Idempotent)?",
            "Idempotency is achieved through: (1) Staging truncation prior to ingestion, preventing record accumulation, and "
            "(2) ON CONFLICT (order_id, order_line_item) DO UPDATE in the fact table. If run_etl.py is executed multiple times, "
            "existing records are updated in place without primary key violations or duplicate row creation. Exactly 24,655 rows "
            "remain in fact_sales."
        ),
        (
            "10. How does the stored procedure work?",
            "The PL/pgSQL function retail.run_data_quality_audit() executes directly on the database engine. It calculates live "
            "row counts, duplicate line item counts, missing attributes, negative monetary values, and financial reconciliation "
            "mismatches. It writes timestamped audit rows into retail.etl_audit_log with status badges (PASSED, WARNING, INFO) "
            "and returns a summary table for immediate monitoring."
        ),
    ]

    for q_title, q_body in qa_list:
        add_callout(doc, q_body, title=q_title, border_hex="6366F1", bg_hex="F8FAFC")

    # =========================================================================
    # 11. CANDIDATE AI USAGE DECLARATION (SECTION 22)
    # =========================================================================
    h11 = doc.add_heading(level=1)
    r11 = h11.add_run("11. Candidate AI Usage Disclosure (Section 22)")
    r11.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "In compliance with Section 22 of the assessment instructions, below is the transparent declaration "
        "of AI assistance and personal implementation:"
    )

    ai_headers = ["Assessment Category", "Candidate Declaration & Disclosure"]
    ai_widths = [2.2, 4.3]
    ai_data = [
        ["What I Referred To", "Official PostgreSQL 16 Docs (PL/pgSQL, ON CONFLICT), Psycopg2 batching, and Kimball's Data Warehouse Toolkit."],
        ["Whether I Used ChatGPT/AI", "Yes. AI was used as an interactive pair-programming assistant for rapid boilerplate generation and syntax checks."],
        ["What AI Helped With", "Drafting initial folder scaffolding, refining Chart.js dashboard syntax, and optimizing SQL window function queries (DENSE_RANK, LAG)."],
        ["What I Personally Implemented", "Data profiling of store_sales_v301.dat (identifying 345 duplicates, 505 gateway discounts, 555 mismatches), composite deduplication logic, financial reconciliation formulas, Star Schema DDL, and transactional rollback handling."],
        ["What I Already Knew", "Relational dimensional modeling, SQL indexing, Python data structures, ACID transaction principles, and Pandas cleaning operations."],
        ["What I Learned", "Best practices for Windows PowerShell character encoding (handling currency symbols in logs) and high-throughput execute_values upserts in Psycopg2."],
        ["Ability to Rewrite Without AI", "Yes. I fully understand every line of code, SQL query, and stored procedure in this project and can explain, modify, or rewrite them live during a video interview."],
    ]
    t_ai = doc.add_table(rows=1, cols=2)
    style_table(t_ai, ai_widths, ai_headers, ai_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # =========================================================================
    # 12. STEP-BY-STEP HOW TO RUN
    # =========================================================================
    h12 = doc.add_heading(level=1)
    r12 = h12.add_run("12. Step-by-Step Execution Commands")
    r12.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph(
        "Follow these exact commands on Windows PowerShell to execute the pipeline, run the automated tests, "
        "view analytics, and launch the dashboard:"
    )

    run_commands = (
        "# 1. Navigate to project root & activate virtual environment\n"
        "cd retail-etl-pipeline\n"
        "python -m venv .venv\n"
        ".venv\\Scripts\\activate\n"
        "pip install -r requirements.txt\n\n"
        "# 2. Apply Schema & Stored Procedures (Optional: run_etl.py auto-creates them)\n"
        "psql -U postgres -d retail_etl -f sql/01_schema.sql\n"
        "psql -U postgres -d retail_etl -f sql/02_stored_procedures.sql\n\n"
        "# 3. Execute End-to-End ETL Pipeline\n"
        "python run_etl.py\n\n"
        "# 4. Run Automated Pytest Test Suite\n"
        "pytest tests/test_etl.py -v\n\n"
        "# 5. Execute 12 SQL Business Intelligence Queries\n"
        "psql -U postgres -d retail_etl -f sql/03_analysis.sql\n\n"
        "# 6. Launch Live Web Analytics Dashboard\n"
        "python serve_dashboard.py\n"
        "# Open in browser: http://localhost:8000/"
    )
    add_code_block(doc, run_commands)

    # Save to both locations
    OUTPUT_DOCX_PROJECT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT_DOCX_PROJECT)
    doc.save(OUTPUT_DOCX_ROOT)
    print(f"Successfully generated: {OUTPUT_DOCX_PROJECT.resolve()}")
    print(f"Successfully generated: {OUTPUT_DOCX_ROOT.resolve()}")


if __name__ == "__main__":
    build_word_document()
