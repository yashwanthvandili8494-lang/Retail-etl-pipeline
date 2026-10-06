#!/usr/bin/env python3
"""Retail ETL Pipeline - Main Execution Entrypoint."""

import sys
import logging
from pathlib import Path

# Ensure UTF-8 console output encoding on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import Config
from src.etl import RetailETLPipeline


def setup_logging():
    """Configure structured console logging for ETL execution."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    """Execute end-to-end Retail ETL pipeline."""
    setup_logging()
    logger = logging.getLogger("run_etl")
    logger.info("==================================================")
    logger.info("Starting Retail ETL Pipeline Execution")
    logger.info("Source Data File: %s", Config.DATA_FILE)
    logger.info("Target DB Host:   %s:%d (%s)", Config.DB_HOST, Config.DB_PORT, Config.DB_NAME)
    logger.info("==================================================")

    try:
        pipeline = RetailETLPipeline(data_file=Config.DATA_FILE)
        audit_summary = pipeline.run()

        logger.info("ETL Pipeline completed successfully with status: %s", audit_summary.get("status"))
        sys.exit(0)
    except FileNotFoundError as fnf_err:
        logger.error("Data extraction aborted: %s", fnf_err)
        sys.exit(1)
    except Exception as err:
        logger.exception("ETL Pipeline execution failed catastrophically: %s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()
