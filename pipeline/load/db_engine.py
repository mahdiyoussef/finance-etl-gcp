"""Database engine and connection management for SQL Server warehouse storage.

Supports Microsoft SQL Server endpoints configured via environment variables
(SQL_SERVER_ENDPOINT, SQL_SERVER_HOST, SQL_SERVER_PORT, SQL_SERVER_DATABASE,
SQL_SERVER_USER, SQL_SERVER_PASSWORD) with automatic connection pooling and
dialect-aware DDL / DML operations.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.settings import (
    DATABASE_URL,
    SQL_SERVER_DATABASE,
    SQL_SERVER_DRIVER,
    SQL_SERVER_ENDPOINT,
    SQL_SERVER_HOST,
    SQL_SERVER_PASSWORD,
    SQL_SERVER_PORT,
    SQL_SERVER_TRUST_CERTIFICATE,
    SQL_SERVER_USER,
    get_sql_server_connection_string,
)

logger = logging.getLogger(__name__)

# ── DDL Definitions ──────────────────────────────────────────────────────────

SQLSERVER_INIT_DDL = """
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'customers')
CREATE TABLE customers (
  customer_id VARCHAR(64) PRIMARY KEY,
  customer_name NVARCHAR(255) NOT NULL,
  segment VARCHAR(64) NOT NULL,
  region VARCHAR(64) NOT NULL
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'invoices')
CREATE TABLE invoices (
  invoice_id VARCHAR(64) PRIMARY KEY,
  customer_id VARCHAR(64) NOT NULL,
  invoice_date DATE NOT NULL,
  due_date DATE NOT NULL,
  amount_local DECIMAL(18, 2) NOT NULL,
  currency VARCHAR(3) NOT NULL DEFAULT 'USD',
  fx_rate DECIMAL(18, 4) NOT NULL DEFAULT 1.0,
  amount_usd DECIMAL(18, 2) NOT NULL,
  status VARCHAR(32) NOT NULL,
  paid_date DATE NULL
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ticket_events')
CREATE TABLE ticket_events (
  event_id VARCHAR(64) PRIMARY KEY,
  ticket_id VARCHAR(64) NOT NULL,
  customer_id VARCHAR(64) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  category VARCHAR(64) NOT NULL,
  priority VARCHAR(32) NOT NULL,
  event_ts DATETIME2 NOT NULL
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'quarantine')
CREATE TABLE quarantine (
  source VARCHAR(128) NOT NULL,
  record NVARCHAR(MAX) NOT NULL,
  error NVARCHAR(MAX) NOT NULL
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tickets_latest')
CREATE TABLE tickets_latest (
  ticket_id VARCHAR(64) PRIMARY KEY,
  customer_id VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  category VARCHAR(64) NOT NULL,
  priority VARCHAR(32) NOT NULL,
  created_at DATETIME2 NOT NULL,
  closed_at DATETIME2 NULL
);
"""

SQLITE_INIT_DDL = """
CREATE TABLE IF NOT EXISTS customers (
  customer_id TEXT PRIMARY KEY,
  customer_name TEXT NOT NULL,
  segment TEXT NOT NULL,
  region TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
  invoice_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  invoice_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  amount_local REAL NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  fx_rate REAL NOT NULL DEFAULT 1.0,
  amount_usd REAL NOT NULL,
  status TEXT NOT NULL,
  paid_date TEXT
);

CREATE TABLE IF NOT EXISTS ticket_events (
  event_id TEXT PRIMARY KEY,
  ticket_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  event_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine (
  source TEXT NOT NULL,
  record TEXT NOT NULL,
  error TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets_latest (
  ticket_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  status TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  created_at TEXT NOT NULL,
  closed_at TEXT
);
"""


@dataclass
class DatabaseEndpointConfig:
    """Configuration contract for SQL Server endpoint."""

    endpoint: str = SQL_SERVER_ENDPOINT
    host: str = SQL_SERVER_HOST
    port: int = SQL_SERVER_PORT
    database: str = SQL_SERVER_DATABASE
    user: str = SQL_SERVER_USER
    password: str = SQL_SERVER_PASSWORD
    driver: str = SQL_SERVER_DRIVER
    trust_certificate: str = SQL_SERVER_TRUST_CERTIFICATE
    url: str = DATABASE_URL

    @classmethod
    def from_env(cls) -> DatabaseEndpointConfig:
        """Construct configuration directly from environment variables."""
        return cls()


class WarehouseConnection:
    """Dialect-agnostic connection wrapper for SQL Server and local storage."""

    def __init__(self, raw_connection: Any, dialect: str = "sqlserver"):
        self.raw_connection = raw_connection
        self.dialect = dialect
        self._total_changes = 0

    @property
    def total_changes(self) -> int:
        """Return cumulative rows affected (similar to sqlite3.total_changes)."""
        if hasattr(self.raw_connection, "total_changes"):
            return self.raw_connection.total_changes
        return self._total_changes

    def execute(self, sql: str, params: tuple | list | None = None) -> Any:
        """Execute a single query with optional parameters."""
        cursor = self.raw_connection.cursor()
        if params is not None:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if hasattr(cursor, "rowcount") and cursor.rowcount > 0:
            self._total_changes += cursor.rowcount
        return cursor

    def executemany(self, sql: str, param_seq: list[Any]) -> Any:
        """Execute a query against a sequence of parameter sets."""
        cursor = self.raw_connection.cursor()
        cursor.executemany(sql, param_seq)
        if hasattr(cursor, "rowcount") and cursor.rowcount > 0:
            self._total_changes += cursor.rowcount
        elif hasattr(self.raw_connection, "total_changes"):
            pass
        else:
            self._total_changes += len(param_seq)
        return cursor

    def executescript(self, script: str) -> None:
        """Execute multiple SQL statements sequentially."""
        if hasattr(self.raw_connection, "executescript"):
            self.raw_connection.executescript(script)
        else:
            cursor = self.raw_connection.cursor()
            for statement in script.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
            self.commit()

    def commit(self) -> None:
        """Commit pending transaction."""
        self.raw_connection.commit()

    def close(self) -> None:
        """Close connection."""
        self.raw_connection.close()


def _datediff_compat(unit: str, d1: Any, d2: Any) -> int | None:
    """SQLite compatibility function emulating SQL Server DATEDIFF(day, d1, d2)."""
    if not d1 or not d2:
        return None
    from datetime import date
    try:
        dt1 = date.fromisoformat(str(d1)[:10])
        dt2 = date.fromisoformat(str(d2)[:10])
        return (dt2 - dt1).days
    except Exception:
        return 0


def create_warehouse_connection(
    database: Path | str | None = None,
    config: DatabaseEndpointConfig | None = None,
) -> WarehouseConnection:
    """Connect to SQL Server endpoint, or initialize a local database.

    Args:
        database: Optional file path or connection URI override.
        config: SQL Server endpoint configuration. Uses environment settings
            if omitted.

    Returns:
        A WarehouseConnection instance ready for schema setup and queries.
    """
    cfg = config or DatabaseEndpointConfig.from_env()

    # If database is explicitly provided as a file path or sqlite URI
    if database is not None:
        db_path = str(database)
        if db_path.endswith(".db") or db_path.startswith("sqlite") or ":memory:" in db_path or "/" in db_path:
            target = Path(db_path) if not db_path.startswith("sqlite") and db_path != ":memory:" else None
            if target and target.parent:
                target.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.create_function("datediff", 3, _datediff_compat)
            wrapper = WarehouseConnection(conn, dialect="sqlite")
            wrapper.executescript(SQLITE_INIT_DDL)
            return wrapper

    # Attempt connection to SQL Server via pyodbc or pymssql
    try:
        import pyodbc  # type: ignore[import-not-found]

        conn_str = get_sql_server_connection_string()
        logger.info("Connecting to SQL Server at %s:%s...", cfg.host, cfg.port)
        raw_conn = pyodbc.connect(conn_str, timeout=5)
        wrapper = WarehouseConnection(raw_conn, dialect="sqlserver")
        wrapper.executescript(SQLSERVER_INIT_DDL)
        return wrapper
    except Exception as pyodbc_err:
        try:
            import pymssql  # type: ignore[import-not-found]

            logger.info("Connecting to SQL Server via pymssql at %s:%s...", cfg.host, cfg.port)
            raw_conn = pymssql.connect(
                server=cfg.host,
                port=cfg.port,
                user=cfg.user,
                password=cfg.password,
                database=cfg.database,
                timeout=5,
            )
            wrapper = WarehouseConnection(raw_conn, dialect="sqlserver")
            wrapper.executescript(SQLSERVER_INIT_DDL)
            return wrapper
        except Exception as pymssql_err:
            logger.debug(
                "SQL Server connection unavailable (%s, %s); falling back to local database.",
                pyodbc_err,
                pymssql_err,
            )

    # Fallback to local SQLite when running in test / offline development mode
    fallback_path = Path(os.environ.get("LOCAL_DATA_ROOT", "data/demo")) / "finance.db"
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(fallback_path)
    conn.create_function("datediff", 3, _datediff_compat)
    wrapper = WarehouseConnection(conn, dialect="sqlite")
    wrapper.executescript(SQLITE_INIT_DDL)
    return wrapper
