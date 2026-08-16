import unittest
from unittest.mock import MagicMock, patch
import backend.db
from backend.db import PostgresCursorWrapper, PostgresConnectionWrapper, is_postgres, get_database_url

class TestPostgresCompatibility(unittest.TestCase):
    def test_sql_translation_placeholders(self):
        mock_pg_cursor = MagicMock()
        wrapper = PostgresCursorWrapper(mock_pg_cursor)
        
        # Test ? -> %s translation
        wrapper.execute("SELECT * FROM contractors WHERE name = ? AND active_workers = ?;", ("L&T", 50))
        mock_pg_cursor.execute.assert_called_once_with(
            "SELECT * FROM contractors WHERE name = %s AND active_workers = %s;",
            ("L&T", 50)
        )

    def test_sql_translation_query_cache_upsert(self):
        mock_pg_cursor = MagicMock()
        wrapper = PostgresCursorWrapper(mock_pg_cursor)
        
        sql = "INSERT OR REPLACE INTO query_cache (normalized_input_hash, original_input_text, full_pipeline_response) VALUES (?, ?, ?);"
        wrapper.execute(sql, ("hash123", "input text", '{"status": "ok"}'))
        
        called_sql = mock_pg_cursor.execute.call_args[0][0]
        self.assertIn("ON CONFLICT (normalized_input_hash) DO UPDATE", called_sql)
        self.assertIn("%s", called_sql)
        self.assertNotIn("?", called_sql)

    def test_sql_translation_finance_calculations_upsert(self):
        mock_pg_cursor = MagicMock()
        wrapper = PostgresCursorWrapper(mock_pg_cursor)
        
        sql = "INSERT OR REPLACE INTO finance_calculations (task_id, delay_days) VALUES (?, ?);"
        wrapper.execute(sql, ("T-101", 2))
        
        called_sql = mock_pg_cursor.execute.call_args[0][0]
        self.assertIn("ON CONFLICT (task_id, delay_days) DO NOTHING", called_sql)
        self.assertIn("%s", called_sql)
        self.assertNotIn("?", called_sql)

    def test_postgres_connection_wrapper_cursor(self):
        mock_pg_conn = MagicMock()
        conn_wrapper = PostgresConnectionWrapper(mock_pg_conn)
        
        with patch("psycopg2.extras.RealDictCursor"):
            cursor = conn_wrapper.cursor()
            self.assertIsInstance(cursor, PostgresCursorWrapper)
        
        conn_wrapper.commit()
        mock_pg_conn.commit.assert_called_once()
        
        conn_wrapper.rollback()
        mock_pg_conn.rollback.assert_called_once()
        
        conn_wrapper.close()
        mock_pg_conn.close.assert_called_once()

    def test_is_postgres_detection(self):
        with patch("backend.db.get_database_url", return_value="postgresql://user:pass@host:5432/dbname"):
            self.assertTrue(is_postgres())
        
        with patch("backend.db.get_database_url", return_value="postgres://user:pass@host:5432/dbname"):
            self.assertTrue(is_postgres())
            
        with patch("backend.db.get_database_url", return_value=None):
            self.assertFalse(is_postgres())
