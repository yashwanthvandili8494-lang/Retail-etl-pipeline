"""Main ETL Pipeline Orchestrator for Retail Store Sales."""

import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from psycopg2.extras import execute_values

from src.config import Config
from src.db import get_connection, execute_sql_file
from src.validation import (
    clean_raw_data,
    detect_duplicates,
    perform_financial_reconciliation,
    run_data_quality_checks,
)

logger = logging.getLogger(__name__)


class RetailETLPipeline:
    """Manages the full lifecycle of the Retail Store Sales ETL Pipeline."""

    def __init__(self, data_file: Path = Config.DATA_FILE):
        self.data_file = data_file
        self.raw_df: pd.DataFrame = pd.DataFrame()
        self.cleaned_df: pd.DataFrame = pd.DataFrame()
        self.clean_df: pd.DataFrame = pd.DataFrame()
        self.dup_df: pd.DataFrame = pd.DataFrame()
        self.recon_df: pd.DataFrame = pd.DataFrame()
        self.recon_errors_df: pd.DataFrame = pd.DataFrame()
        self.audit_metrics: Dict[str, Any] = {}

    def extract(self) -> pd.DataFrame:
        """Step 1: Extract raw data from CSV/DAT file with safety validations."""
        logger.info("Starting Extraction phase from: %s", self.data_file)

        if not self.data_file.exists():
            error_msg = f"Source data file not found: {self.data_file.resolve()}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Read CSV formatted DAT file
        self.raw_df = pd.read_csv(self.data_file)
        num_rows, num_cols = self.raw_df.shape
        logger.info("Extracted %d rows and %d columns successfully.", num_rows, num_cols)

        # Print detailed extraction diagnostic summary
        print("\n[EXTRACT DIAGNOSTIC]")
        print(f"Source file        : {self.data_file}")
        print(f"Total Rows         : {num_rows}")
        print(f"Total Columns      : {num_cols}")
        print(f"Columns            : {list(self.raw_df.columns)}")
        print("\nSample Records (First 3):")
        print(self.raw_df.head(3).to_string(index=False))

        return self.raw_df

    def transform(self) -> None:
        """Step 2: Clean, validate, deduplicate, and reconcile transaction data."""
        logger.info("Starting Transformation and Validation phase.")

        # 1. Clean data (normalize headers, strip strings, cast types)
        self.cleaned_df = clean_raw_data(self.raw_df)
        logger.info("Data cleaned and standardized. Normalized rows: %d", len(self.cleaned_df))

        # 2. Duplicate Detection (Composite key: order_id + order_line_item)
        self.clean_df, self.dup_df = detect_duplicates(self.cleaned_df, Config.OUTPUT_DIR)
        logger.info(
            "Duplicate detection complete. Valid rows: %d, Rejected duplicates: %d",
            len(self.clean_df),
            len(self.dup_df),
        )

        # 3. Financial Reconciliation (reconciles source records, exporting all 555 file discrepancies)
        self.recon_df, self.recon_errors_df = perform_financial_reconciliation(
            self.cleaned_df,
            tolerance=Config.RECONCILIATION_TOLERANCE,
            output_dir=Config.OUTPUT_DIR,
        )
        logger.info(
            "Financial reconciliation evaluated. Total source mismatches (> INR %.2f): %d",
            Config.RECONCILIATION_TOLERANCE,
            len(self.recon_errors_df),
        )

        # 4. Generate Comprehensive Data Quality Report
        run_data_quality_checks(
            raw_df=self.raw_df,
            clean_df=self.clean_df,
            dup_df=self.dup_df,
            recon_errors_df=self.recon_errors_df,
            output_dir=Config.OUTPUT_DIR,
        )

    def load_staging(self, conn) -> int:
        """Step 3: Ingest raw records into staging table (retail.stg_store_sales).

        Truncates staging first to maintain idempotency and zero duplicate accumulation.
        """
        logger.info("Loading raw data into staging table (retail.stg_store_sales)...")
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE retail.stg_store_sales;")

            cols = [
                "order_id",
                "order_line_item",
                "order_date",
                "customer_email",
                "customer_city",
                "store_code",
                "product_sku",
                "category",
                "quantity",
                "unit_price",
                "store_discount",
                "payment_gateway_discount",
                "tax_amount",
                "amount_paid",
                "transaction_type",
            ]

            # Prepare tuples for bulk insertion
            records = [
                tuple(row[c] for c in cols)
                for _, row in self.raw_df.iterrows()
            ]

            sql = f"""
                INSERT INTO retail.stg_store_sales ({', '.join(cols)})
                VALUES %s;
            """
            execute_values(cur, sql, records, page_size=5000)

        logger.info("Successfully loaded %d records into staging table.", len(records))
        return len(records)

    def load_dimensions(self, conn) -> None:
        """Step 4: Load dimension tables (dim_date, dim_customer, dim_store, dim_product)."""
        logger.info("Loading dimension tables...")
        with conn.cursor() as cur:
            # 1. Date Dimension: populate full date range
            cur.execute("SELECT retail.populate_dim_date('2021-01-01', '2026-12-31');")

            # 2. Store Dimension (Unique store_code + store_city)
            # In the dataset, each store_code is 1-to-1 with its location city
            store_records = (
                self.clean_df[["store_code", "customer_city"]]
                .drop_duplicates(subset=["store_code"])
                .values.tolist()
            )
            store_sql = """
                INSERT INTO retail.dim_store (store_code, store_city)
                VALUES %s
                ON CONFLICT (store_code) DO NOTHING;
            """
            execute_values(cur, store_sql, store_records)

            # 3. Product Dimension (Unique product_sku + canonical category)
            # Resolves canonical category via most frequent occurrence
            prod_canonical = (
                self.clean_df.groupby("product_sku")["category"]
                .agg(lambda x: x.mode()[0])
                .reset_index()
                .values.tolist()
            )
            prod_sql = """
                INSERT INTO retail.dim_product (product_sku, category)
                VALUES %s
                ON CONFLICT (product_sku) DO UPDATE
                SET category = EXCLUDED.category;
            """
            execute_values(cur, prod_sql, prod_canonical)

            # 4. Customer Dimension (Unique customer_email + customer_city)
            # Pick latest recorded city per customer email
            cust_df = (
                self.clean_df.sort_values(by=["order_date"])
                .groupby("customer_email")
                .last()[["customer_city"]]
                .reset_index()
            )
            cust_records = cust_df.values.tolist()
            cust_sql = """
                INSERT INTO retail.dim_customer (customer_email, customer_city)
                VALUES %s
                ON CONFLICT (customer_email) DO UPDATE
                SET customer_city = EXCLUDED.customer_city;
            """
            execute_values(cur, cust_sql, cust_records, page_size=2500)

        logger.info("Dimension tables successfully loaded.")

    def load_fact(self, conn) -> int:
        """Step 5: Load cleansed transactions into retail.fact_sales with dimensional FKs.

        Uses ON CONFLICT (order_id, order_line_item) to prevent duplicates and enable reruns.
        """
        logger.info("Loading fact table (retail.fact_sales)...")
        with conn.cursor() as cur:
            # Fetch dimension lookup dictionaries for fast surrogate key mapping
            cur.execute("SELECT customer_email, customer_id FROM retail.dim_customer;")
            cust_map = dict(cur.fetchall())

            cur.execute("SELECT store_code, store_id FROM retail.dim_store;")
            store_map = dict(cur.fetchall())

            cur.execute("SELECT product_sku, product_id FROM retail.dim_product;")
            prod_map = dict(cur.fetchall())

            # Prepare fact tuples
            fact_records = []
            for _, row in self.clean_df.iterrows():
                cust_id = cust_map[row["customer_email"]]
                store_id = store_map[row["store_code"]]
                prod_id = prod_map[row["product_sku"]]

                fact_records.append((
                    row["order_id"],
                    int(row["order_line_item"]),
                    row["order_date"],
                    cust_id,
                    store_id,
                    prod_id,
                    int(row["quantity"]),
                    float(row["unit_price"]),
                    float(row["store_discount"]),
                    float(row["payment_gateway_discount"]),
                    float(row["tax_amount"]),
                    float(row["amount_paid"]),
                    row["transaction_type"],
                ))

            fact_sql = """
                INSERT INTO retail.fact_sales (
                    order_id,
                    order_line_item,
                    order_date,
                    customer_id,
                    store_id,
                    product_id,
                    quantity,
                    unit_price,
                    store_discount,
                    payment_gateway_discount,
                    tax_amount,
                    amount_paid,
                    transaction_type
                )
                VALUES %s
                ON CONFLICT (order_id, order_line_item) DO UPDATE SET
                    order_date = EXCLUDED.order_date,
                    customer_id = EXCLUDED.customer_id,
                    store_id = EXCLUDED.store_id,
                    product_id = EXCLUDED.product_id,
                    quantity = EXCLUDED.quantity,
                    unit_price = EXCLUDED.unit_price,
                    store_discount = EXCLUDED.store_discount,
                    payment_gateway_discount = EXCLUDED.payment_gateway_discount,
                    tax_amount = EXCLUDED.tax_amount,
                    amount_paid = EXCLUDED.amount_paid,
                    transaction_type = EXCLUDED.transaction_type;
            """
            execute_values(cur, fact_sql, fact_records, page_size=5000)

        logger.info("Successfully loaded %d records into fact_sales.", len(fact_records))
        return len(fact_records)

    def post_load_audit(self, conn) -> Dict[str, Any]:
        """Step 6: Execute PostgreSQL stored procedure to audit load integrity dynamically."""
        logger.info("Running post-load data quality audit...")
        with conn.cursor() as cur:
            # Call the stored audit function
            cur.execute("SELECT * FROM retail.run_data_quality_audit('ETL_RUN_AUDIT');")
            audit_rows = cur.fetchall()

            # Dynamic database row counts
            cur.execute("SELECT COUNT(*) FROM retail.stg_store_sales;")
            stg_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM retail.fact_sales;")
            fact_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM retail.dim_customer;")
            cust_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM retail.dim_store;")
            store_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM retail.dim_product;")
            prod_count = cur.fetchone()[0]

        source_count = len(self.raw_df)
        dup_count = len(self.dup_df)
        clean_count = len(self.clean_df)
        recon_errors = len(self.recon_errors_df)

        metrics = {
            "source_rows": source_count,
            "staging_rows": stg_count,
            "duplicate_rows": dup_count,
            "clean_rows": clean_count,
            "fact_rows": fact_count,
            "customers": cust_count,
            "stores": store_count,
            "products": prod_count,
            "reconciliation_errors": recon_errors,
            "status": "SUCCESS",
        }
        self.audit_metrics = metrics
        self._print_audit_summary(metrics)
        return metrics

    @staticmethod
    def _print_audit_summary(m: Dict[str, Any]) -> None:
        """Print the required interview audit summary box."""
        print("\n" + "=" * 32)
        print("========== ETL AUDIT ==========")
        print("=" * 32)
        print(f"Source rows              : {m['source_rows']}")
        print(f"Staging rows             : {m['staging_rows']}")
        print(f"Duplicate rows           : {m['duplicate_rows']}")
        print(f"Clean rows               : {m['clean_rows']}")
        print(f"Fact rows                : {m['fact_rows']}")
        print(f"Customers                : {m['customers']}")
        print(f"Stores                   : {m['stores']}")
        print(f"Products                 : {m['products']}")
        print(f"Reconciliation errors    : {m['reconciliation_errors']}")
        print("")
        print(f"ETL STATUS               : {m['status']}")
        print("=" * 32 + "\n")

    def run(self) -> Dict[str, Any]:
        """Execute the end-to-end ETL workflow with transactional integrity."""
        logger.info("Initializing Retail ETL Execution Pipeline.")

        # Ensure database tables and stored procedures exist
        execute_sql_file(Config.SQL_DIR / "01_schema.sql")
        execute_sql_file(Config.SQL_DIR / "02_stored_procedures.sql")

        # Step 1: Extract
        self.extract()

        # Step 2: Transform, Clean, Deduplicate, Reconcile
        self.transform()

        # Step 3, 4, 5: Safe Atomic Database Load
        conn = get_connection()
        try:
            conn.autocommit = False
            self.load_staging(conn)
            self.load_dimensions(conn)
            self.load_fact(conn)
            conn.commit()
            logger.info("Transaction committed successfully.")
        except Exception as err:
            conn.rollback()
            logger.error("ETL loading failed! Transaction rolled back completely: %s", err)
            raise
        finally:
            conn.close()

        # Step 6: Post-load Audit
        audit_conn = get_connection()
        try:
            return self.post_load_audit(audit_conn)
        finally:
            audit_conn.close()
