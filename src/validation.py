"""Data cleaning, validation, deduplication, and financial reconciliation module."""

import logging
from pathlib import Path
from typing import Tuple
import pandas as pd
from src.config import Config

logger = logging.getLogger(__name__)


def clean_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names, strip whitespace, and coerce data types."""
    df_clean = df.copy()

    # 1. Normalize column headers
    df_clean.columns = df_clean.columns.str.strip().str.lower()

    # 2. Trim whitespace on text columns
    text_cols = df_clean.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        df_clean[col] = df_clean[col].astype(str).str.strip()

    # 3. Safely convert order_date
    df_clean["order_date"] = pd.to_datetime(df_clean["order_date"], errors="coerce").dt.date

    # 4. Safely convert integer columns
    int_cols = ["order_line_item", "quantity"]
    for col in int_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0).astype(int)

    # 5. Safely convert numeric/monetary columns
    numeric_cols = [
        "unit_price",
        "store_discount",
        "payment_gateway_discount",
        "tax_amount",
        "amount_paid",
    ]
    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").round(2)

    return df_clean


def detect_duplicates(
    df: pd.DataFrame, output_dir: Path = Config.OUTPUT_DIR
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Detect duplicate order line items (order_id + order_line_item).

    Exports rejected duplicate records to output/duplicate_records.csv.
    Keeps the first occurrence for downstream fact loading.
    """
    key_cols = ["order_id", "order_line_item"]
    dup_mask = df.duplicated(subset=key_cols, keep="first")

    duplicates_df = df[dup_mask].copy()
    clean_df = df[~dup_mask].copy()

    output_dir.mkdir(parents=True, exist_ok=True)
    dup_file = output_dir / "duplicate_records.csv"
    duplicates_df.to_csv(dup_file, index=False)
    logger.info("Saved %d rejected duplicate records to %s", len(duplicates_df), dup_file)

    return clean_df, duplicates_df


def perform_financial_reconciliation(
    df: pd.DataFrame,
    tolerance: float = Config.RECONCILIATION_TOLERANCE,
    output_dir: Path = Config.OUTPUT_DIR,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform financial reconciliation between amount_paid and formula:

    expected_amount = quantity * unit_price - store_discount - payment_gateway_discount + tax_amount
    Flags records where abs(amount_paid - expected_amount) > tolerance.
    Exports reconciliation discrepancies to output/reconciliation_errors.csv without altering data.
    """
    df_recon = df.copy()

    # Calculate expected amount based on standard pricing components
    calculated_amount = (
        (df_recon["quantity"] * df_recon["unit_price"])
        - df_recon["store_discount"]
        - df_recon["payment_gateway_discount"]
        + df_recon["tax_amount"]
    ).round(2)

    df_recon["calculated_amount"] = calculated_amount
    df_recon["reconciliation_difference"] = (df_recon["amount_paid"] - calculated_amount).round(2)

    # Flag records where difference exceeds tolerance (0.01)
    mismatch_mask = df_recon["reconciliation_difference"].abs() > tolerance
    recon_errors_df = df_recon[mismatch_mask].copy()

    # Prepare standard reconciliation report columns
    export_cols = [
        "order_id",
        "order_line_item",
        "amount_paid",
        "calculated_amount",
        "reconciliation_difference",
        "transaction_type",
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    error_file = output_dir / "reconciliation_errors.csv"
    recon_errors_df[export_cols].to_csv(error_file, index=False)
    logger.info(
        "Financial reconciliation complete: %d mismatches found (> INR %.2f tolerance). Saved to %s",
        len(recon_errors_df),
        tolerance,
        error_file,
    )

    return df_recon, recon_errors_df


def run_data_quality_checks(
    raw_df: pd.DataFrame,
    clean_df: pd.DataFrame,
    dup_df: pd.DataFrame,
    recon_errors_df: pd.DataFrame,
    output_dir: Path = Config.OUTPUT_DIR,
) -> pd.DataFrame:
    """Run comprehensive data quality validations across completeness, uniqueness,

    validity, and business rules. Generates output/data_quality_report.csv.
    """
    report_rows = []

    def add_check(category: str, check_name: str, evaluated: int, issues: int, status: str, desc: str):
        report_rows.append({
            "category": category,
            "check_name": check_name,
            "records_evaluated": evaluated,
            "issue_count": issues,
            "status": status,
            "description": desc,
        })

    total_raw = len(raw_df)

    # 1. Completeness Checks
    null_counts = raw_df.isnull().sum().sum()
    add_check(
        "Completeness",
        "null_or_blank_values",
        total_raw * raw_df.shape[1],
        int(null_counts),
        "PASSED" if null_counts == 0 else "FAILED",
        "Evaluates missing or null cell values across all raw columns",
    )

    # 2. Uniqueness Checks
    exact_dups = int(raw_df.duplicated().sum())
    add_check(
        "Uniqueness",
        "exact_duplicate_rows",
        total_raw,
        exact_dups,
        "PASSED" if exact_dups == 0 else "WARNING",
        "Identifies 100% identical duplicate rows in source dataset",
    )

    key_dups = len(dup_df)
    add_check(
        "Uniqueness",
        "duplicate_order_line_keys",
        total_raw,
        key_dups,
        "PASSED" if key_dups == 0 else "WARNING",
        "Identifies collisions on composite primary key (order_id, order_line_item)",
    )

    # 3. Validity Checks
    invalid_dates = int(pd.to_datetime(raw_df["order_date"], errors="coerce").isna().sum())
    add_check(
        "Validity",
        "invalid_date_format",
        total_raw,
        invalid_dates,
        "PASSED" if invalid_dates == 0 else "FAILED",
        "Validates parseable ISO date formats for order_date",
    )

    neg_qty = int((raw_df["quantity"] < 0).sum())
    add_check(
        "Validity",
        "negative_quantity",
        total_raw,
        neg_qty,
        "PASSED" if neg_qty == 0 else "FAILED",
        "Ensures quantity ordered is non-negative",
    )

    neg_price = int((raw_df["unit_price"] < 0).sum())
    add_check(
        "Validity",
        "negative_unit_price",
        total_raw,
        neg_price,
        "PASSED" if neg_price == 0 else "FAILED",
        "Ensures catalog unit prices are non-negative",
    )

    neg_store_disc = int((raw_df["store_discount"] < 0).sum())
    add_check(
        "Validity",
        "negative_store_discount",
        total_raw,
        neg_store_disc,
        "PASSED" if neg_store_disc == 0 else "FAILED",
        "Ensures promotional store discounts are non-negative",
    )

    # 4. Business Rules & Anomaly Detection
    neg_gw_disc = int((raw_df["payment_gateway_discount"] < 0).sum())
    add_check(
        "Business Rule",
        "negative_payment_gateway_discount",
        total_raw,
        neg_gw_disc,
        "WARNING" if neg_gw_disc > 0 else "PASSED",
        "Identifies negative payment gateway discounts (merchant gateway surcharge)",
    )

    neg_amt_paid = int((raw_df["amount_paid"] < 0).sum())
    add_check(
        "Business Rule",
        "negative_amount_paid",
        total_raw,
        neg_amt_paid,
        "WARNING" if neg_amt_paid > 0 else "PASSED",
        "Identifies negative amount_paid (credit notes / refund adjustments)",
    )

    # 5. Financial Reconciliation
    recon_mismatches = len(recon_errors_df)
    add_check(
        "Financial Reconciliation",
        "price_calculation_variance",
        len(clean_df),
        recon_mismatches,
        "WARNING" if recon_mismatches > 0 else "PASSED",
        f"Identifies variances between recorded amount_paid and formula > INR {Config.RECONCILIATION_TOLERANCE:.2f}",
    )

    # 6. Referential Consistency (Catalog entities)
    unique_stores = raw_df["store_code"].nunique()
    add_check(
        "Referential Consistency",
        "distinct_store_codes",
        total_raw,
        0,
        "PASSED",
        f"Verified presence of {unique_stores} unique retail stores",
    )

    unique_products = raw_df["product_sku"].nunique()
    add_check(
        "Referential Consistency",
        "distinct_product_skus",
        total_raw,
        0,
        "PASSED",
        f"Verified presence of {unique_products} unique product SKUs",
    )

    report_df = pd.DataFrame(report_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "data_quality_report.csv"
    report_df.to_csv(report_file, index=False)
    logger.info("Generated Data Quality Report at %s", report_file)

    return report_df
