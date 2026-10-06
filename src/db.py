"""Database utility and connection management for Retail ETL Pipeline."""

import logging
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.extras import execute_values
from src.config import Config

logger = logging.getLogger(__name__)


def get_connection():
    """Create and return a new PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connect_timeout=10,
        )
        return conn
    except psycopg2.Error as err:
        logger.error("Failed to connect to PostgreSQL database %s: %s", Config.DB_NAME, err)
        raise


@contextmanager
def get_db_cursor(commit: bool = True) -> Generator[tuple, None, None]:
    """Context manager for managing PostgreSQL connection and cursor safely.

    Automatically rolls back on exception, commits on success if requested,
    and cleanly closes cursor and connection.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield conn, cur
        if commit:
            conn.commit()
    except Exception as err:
        conn.rollback()
        logger.error("Database transaction rolled back due to error: %s", err)
        raise
    finally:
        conn.close()


def execute_sql_file(file_path, conn=None) -> None:
    """Execute SQL statements from a file safely within a transaction."""
    logger.info("Executing SQL script: %s", file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        logger.info("Successfully executed SQL script: %s", file_path)
    except Exception as err:
        conn.rollback()
        logger.error("Error executing SQL script %s: %s", file_path, err)
        raise
    finally:
        if should_close:
            conn.close()


def bulk_insert_rows(
    table_name: str,
    columns: list[str],
    rows: list[tuple],
    page_size: int = 5000,
    on_conflict_clause: str = "",
) -> int:
    """Efficient batch insert using psycopg2.extras.execute_values."""
    if not rows:
        return 0

    col_names = ", ".join(columns)
    sql = f"INSERT INTO {table_name} ({col_names}) VALUES %s {on_conflict_clause}"

    with get_db_cursor(commit=True) as (conn, cur):
        execute_values(cur, sql, rows, page_size=page_size)
        return len(rows)
