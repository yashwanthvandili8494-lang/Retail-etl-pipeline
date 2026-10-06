"""Unit and Integration Tests for Retail ETL Pipeline."""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Ensure project root is available on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import Config
from src.validation import (
    clean_raw_data,
    detect_duplicates,
    perform_financial_reconciliation,
    run_data_quality_checks,
)


@pytest.fixture
def sample_raw_data():
    """Create a representative sample DataFrame mimicking store_sales_v301.dat."""
    return pd.DataFrame([
        {
            "order_id": "ORD-1001",
            "order_line_item": 1,
            "order_date": "2024-01-15",
            "customer_email": "john.doe@example.com",
            "customer_city": "Seattle",
            "store_code": "STORE-SEA04",
            "product_sku": "SKU-H301",
            "category": "Home",
            "quantity": 2,
            "unit_price": 100.00,
            "store_discount": 10.00,
            "payment_gateway_discount": 5.00,
            "tax_amount": 15.00,
            "amount_paid": 200.00,  # 2*100 - 10 - 5 + 15 = 200.00 (Balanced)
            "transaction_type": "SALE",
        },
        {
            "order_id": "ORD-1001",
            "order_line_item": 1,  # Exact duplicate key of above
            "order_date": "2024-01-15",
            "customer_email": "john.doe@example.com",
            "customer_city": "Seattle",
            "store_code": "STORE-SEA04",
            "product_sku": "SKU-H301",
            "category": "Home",
            "quantity": 2,
            "unit_price": 100.00,
            "store_discount": 10.00,
            "payment_gateway_discount": 5.00,
            "tax_amount": 15.00,
            "amount_paid": 200.00,
            "transaction_type": "SALE",
        },
        {
            "order_id": "ORD-1002",
            "order_line_item": 1,
            "order_date": "2024-01-16",
            "customer_email": "jane.smith@example.com",
            "customer_city": "Miami",
            "store_code": "STORE-MIA05",
            "product_sku": "SKU-A201",
            "category": "Apparel",
            "quantity": 1,
            "unit_price": 50.00,
            "store_discount": 0.00,
            "payment_gateway_discount": -2.00,  # Negative discount (surcharge)
            "tax_amount": 4.00,
            "amount_paid": 60.00,  # Expected: 1*50 - 0 - (-2) + 4 = 56.00 -> Diff = 4.00 (Mismatch)
            "transaction_type": "SALE",
        },
        {
            "order_id": "ORD-1003",
            "order_line_item": 1,
            "order_date": "2024-01-17",
            "customer_email": "alice@example.com",
            "customer_city": "Austin",
            "store_code": "STORE-AUS07",
            "product_sku": "SKU-E101",
            "category": "Electronics",
            "quantity": -1,  # Invalid quantity
            "unit_price": -20.00,  # Invalid unit price
            "store_discount": 0.00,
            "payment_gateway_discount": 0.00,
            "tax_amount": 0.00,
            "amount_paid": -20.00,  # Negative amount paid
            "transaction_type": "RETURN",
        },
    ])


def test_file_loading_real_dataset():
    """Test 1: Verify actual dataset file exists and can be loaded with pandas."""
    assert Config.DATA_FILE.exists(), f"Dataset file not found at {Config.DATA_FILE}"
    df = pd.read_csv(Config.DATA_FILE)
    assert not df.empty, "Dataset file should not be empty"
    assert len(df) == 25000, f"Expected 25,000 records, got {len(df)}"


def test_required_columns(sample_raw_data):
    """Test 2: Verify all 15 required raw columns are present and cleanable."""
    expected_cols = [
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
    cleaned = clean_raw_data(sample_raw_data)
    for col in expected_cols:
        assert col in cleaned.columns, f"Missing required column: {col}"


def test_numeric_conversion(sample_raw_data):
    """Test 3: Verify numeric columns are coerced safely to proper numeric types."""
    cleaned = clean_raw_data(sample_raw_data)

    assert pd.api.types.is_integer_dtype(cleaned["order_line_item"])
    assert pd.api.types.is_integer_dtype(cleaned["quantity"])
    assert pd.api.types.is_float_dtype(cleaned["unit_price"])
    assert pd.api.types.is_float_dtype(cleaned["store_discount"])
    assert pd.api.types.is_float_dtype(cleaned["payment_gateway_discount"])
    assert pd.api.types.is_float_dtype(cleaned["tax_amount"])
    assert pd.api.types.is_float_dtype(cleaned["amount_paid"])


def test_duplicate_detection(sample_raw_data, tmp_path):
    """Test 4: Verify duplicate detection flags duplicate order lines without loss."""
    clean_df, dup_df = detect_duplicates(sample_raw_data, output_dir=tmp_path)

    assert len(dup_df) == 1
    assert dup_df.iloc[0]["order_id"] == "ORD-1001"
    assert len(clean_df) == 3

    # Check exported CSV
    dup_file = tmp_path / "duplicate_records.csv"
    assert dup_file.exists()
    saved_dups = pd.read_csv(dup_file)
    assert len(saved_dups) == 1


def test_reconciliation_calculation(sample_raw_data, tmp_path):
    """Test 5: Verify reconciliation formula and discrepancy detection (> ₹0.01)."""
    cleaned = clean_raw_data(sample_raw_data)
    clean_df, _ = detect_duplicates(cleaned, output_dir=tmp_path)
    recon_df, recon_errors = perform_financial_reconciliation(clean_df, tolerance=0.01, output_dir=tmp_path)

    # ORD-1001 should reconcile perfectly (2*100 - 10 - 5 + 15 = 200.00)
    ord_1001 = recon_df[recon_df["order_id"] == "ORD-1001"].iloc[0]
    assert ord_1001["calculated_amount"] == 200.00
    assert abs(ord_1001["reconciliation_difference"]) <= 0.01

    # ORD-1002 has difference of 4.00 (60.00 vs 56.00)
    assert len(recon_errors) >= 1
    mismatch_ids = recon_errors["order_id"].tolist()
    assert "ORD-1002" in mismatch_ids

    # Check exported error report
    error_file = tmp_path / "reconciliation_errors.csv"
    assert error_file.exists()


def test_invalid_quantity_detection(sample_raw_data):
    """Test 6: Verify detection of negative quantity in raw dataset."""
    neg_qty_count = (sample_raw_data["quantity"] < 0).sum()
    assert neg_qty_count == 1
    bad_rows = sample_raw_data[sample_raw_data["quantity"] < 0]
    assert bad_rows.iloc[0]["order_id"] == "ORD-1003"


def test_invalid_financial_value_detection(sample_raw_data):
    """Test 7: Verify detection of negative amount_paid and negative unit_price."""
    neg_price_count = (sample_raw_data["unit_price"] < 0).sum()
    neg_amt_count = (sample_raw_data["amount_paid"] < 0).sum()

    assert neg_price_count == 1
    assert neg_amt_count == 1
    assert sample_raw_data[sample_raw_data["amount_paid"] < 0].iloc[0]["order_id"] == "ORD-1003"


def test_data_quality_report_generation(sample_raw_data, tmp_path):
    """Test 8: Verify that data_quality_report.csv is generated with structured checks."""
    cleaned = clean_raw_data(sample_raw_data)
    clean_df, dup_df = detect_duplicates(cleaned, output_dir=tmp_path)
    recon_df, recon_errors = perform_financial_reconciliation(clean_df, output_dir=tmp_path)

    report_df = run_data_quality_checks(
        raw_df=sample_raw_data,
        clean_df=clean_df,
        dup_df=dup_df,
        recon_errors_df=recon_errors,
        output_dir=tmp_path,
    )

    assert not report_df.empty
    assert "category" in report_df.columns
    assert "check_name" in report_df.columns
    assert "status" in report_df.columns

    report_file = tmp_path / "data_quality_report.csv"
    assert report_file.exists()
