"""Configuration module for Retail ETL Pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve root directory of project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration settings."""

    # Database connection parameters
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "retail_etl")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # File and directory paths
    DATA_FILE: Path = BASE_DIR / os.getenv("DATA_FILE_PATH", "data/store_sales_v301.dat")
    OUTPUT_DIR: Path = BASE_DIR / os.getenv("OUTPUT_DIR", "output")
    SQL_DIR: Path = BASE_DIR / "sql"

    # Reconciliation precision tolerance (in Currency units e.g., ₹)
    RECONCILIATION_TOLERANCE: float = 0.01

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
