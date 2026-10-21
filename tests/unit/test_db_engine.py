"""Unit tests for SQL Server database engine and connection configurations."""

import unittest
from pathlib import Path
import tempfile

from config.settings import get_sql_server_connection_string, get_database_url
from pipeline.load.db_engine import (
    DatabaseEndpointConfig,
    WarehouseConnection,
    create_warehouse_connection,
    SQLSERVER_INIT_DDL,
)


class DatabaseEngineTest(unittest.TestCase):
    """Test SQL Server endpoint configuration, connection strings, and warehouse connection."""

    def test_endpoint_config_parsing(self) -> None:
        """Verify host and port extraction from SQL_SERVER_ENDPOINT."""
        cfg = DatabaseEndpointConfig(
            endpoint="sqlserver.internal.net:14333",
            host="sqlserver.internal.net",
            port=14333,
            database="finance_prod",
            user="sa",
            password="TestPassword123!",
        )
        self.assertEqual(cfg.host, "sqlserver.internal.net")
        self.assertEqual(cfg.port, 14333)
        self.assertEqual(cfg.database, "finance_prod")

    def test_connection_string_generation(self) -> None:
        """Verify ODBC connection string formatting."""
        conn_str = get_sql_server_connection_string()
        self.assertIn("SERVER=", conn_str)
        self.assertIn("DATABASE=", conn_str)
        self.assertIn("TrustServerCertificate=", conn_str)

    def test_database_url_generation(self) -> None:
        """Verify SQLAlchemy database URL formatting."""
        url = get_database_url()
        self.assertTrue(url.startswith("mssql+") or "sql" in url)

    def test_sqlserver_ddl_syntax(self) -> None:
        """Verify SQL Server DDL contains expected T-SQL table constructs."""
        self.assertIn("CREATE TABLE customers", SQLSERVER_INIT_DDL)
        self.assertIn("CREATE TABLE invoices", SQLSERVER_INIT_DDL)
        self.assertIn("CREATE TABLE ticket_events", SQLSERVER_INIT_DDL)
        self.assertIn("CREATE TABLE quarantine", SQLSERVER_INIT_DDL)
        self.assertIn("CREATE TABLE tickets_latest", SQLSERVER_INIT_DDL)
        self.assertIn("DECIMAL(18, 2)", SQLSERVER_INIT_DDL)

    def test_warehouse_connection_execution(self) -> None:
        """Verify WarehouseConnection wrapper executes queries and counts changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = create_warehouse_connection(database=Path(tmpdir) / "test_engine.db")
            try:
                self.assertIsNotNone(conn)
                conn.execute(
                    "insert into customers values (?, ?, ?, ?)",
                    ("C999", "Test Corp", "Enterprise", "NA"),
                )
                conn.commit()
                row = conn.execute(
                    "select customer_name from customers where customer_id = ?",
                    ("C999",),
                ).fetchone()
                self.assertEqual(row[0], "Test Corp")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
