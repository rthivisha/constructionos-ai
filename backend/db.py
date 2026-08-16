import os
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constructionos.db")
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data", "seed_project_state.json")

def get_database_url() -> Optional[str]:
    """
    Returns DATABASE_URL from environment or .env if set.
    """
    if "DATABASE_URL" in os.environ:
        val = os.environ["DATABASE_URL"]
        return val.strip() if val and val.strip() else None
    
    for dotenv_path in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        ".env"
    ]:
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r") as f:
                    for line in f:
                        s = line.strip()
                        if s.startswith("DATABASE_URL="):
                            val = s.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
    return None

def is_postgres() -> bool:
    url = get_database_url()
    return bool(url and (url.startswith("postgresql://") or url.startswith("postgres://")))


class PostgresCursorWrapper:
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor

    def _translate_sql(self, sql: str) -> str:
        # Translate '?' placeholders to '%s' for psycopg2
        # Translate INSERT OR REPLACE to PostgreSQL ON CONFLICT syntax for query_cache
        translated = sql.replace("?", "%s")
        if "INSERT OR REPLACE INTO query_cache" in translated:
            translated = (
                "INSERT INTO query_cache (normalized_input_hash, original_input_text, full_pipeline_response) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (normalized_input_hash) DO UPDATE SET "
                "original_input_text = EXCLUDED.original_input_text, "
                "full_pipeline_response = EXCLUDED.full_pipeline_response, "
                "created_at = CURRENT_TIMESTAMP;"
            )
        elif "INSERT OR REPLACE INTO finance_calculations" in translated:
            translated = (
                "INSERT INTO finance_calculations (task_id, delay_days) "
                "VALUES (%s, %s) "
                "ON CONFLICT (task_id, delay_days) DO NOTHING;"
            )
        return translated

    def execute(self, sql: str, params=None):
        translated = self._translate_sql(sql)
        if params is not None:
            return self._cursor.execute(translated, params)
        return self._cursor.execute(translated)

    def executemany(self, sql: str, seq_of_params):
        translated = self._translate_sql(sql)
        return self._cursor.executemany(translated, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class PostgresConnectionWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        import psycopg2.extras
        pg_cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursorWrapper(pg_cursor)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, sql: str, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur


def get_db_connection():
    """
    Returns a unified connection object supporting cursor(), commit(), rollback(), close().
    If DATABASE_URL is set (e.g. Supabase / PostgreSQL), connects to PostgreSQL.
    Otherwise, connects to SQLite (backend/constructionos.db).
    """
    db_url = get_database_url()
    if db_url and is_postgres():
        import psycopg2
        pg_conn = psycopg2.connect(db_url)
        return PostgresConnectionWrapper(pg_conn)
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """
    Initializes database tables and seeds mock state if project_meta is empty.
    Compatible with both PostgreSQL and SQLite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    is_pg = is_postgres()
    auto_id_type = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    timestamp_type = "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP" if is_pg else "DATETIME DEFAULT CURRENT_TIMESTAMP"

    # Create tables
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS project_meta (
        id {auto_id_type},
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        total_budget REAL NOT NULL,
        spent_to_date REAL NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contractors (
        name TEXT PRIMARY KEY,
        scope TEXT NOT NULL,
        daily_operating_cost REAL NOT NULL,
        daily_delay_penalty REAL NOT NULL,
        active_workers INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS divisions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lead_contractor TEXT NOT NULL REFERENCES contractors(name) ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS regulatory_kb (
        code TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        trigger_condition TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_tasks (
        task_id TEXT PRIMARY KEY,
        division_id TEXT NOT NULL REFERENCES divisions(id) ON UPDATE CASCADE ON DELETE RESTRICT,
        task_name TEXT NOT NULL,
        duration INTEGER NOT NULL,
        is_critical_path INTEGER NOT NULL,
        dependencies TEXT NOT NULL
    );
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS finance_calculations (
        id {auto_id_type},
        task_id TEXT NOT NULL,
        delay_days INTEGER NOT NULL,
        UNIQUE(task_id, delay_days)
    );
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS site_events (
        id {auto_id_type},
        event_text TEXT NOT NULL,
        filename TEXT,
        file_path TEXT,
        content_type TEXT,
        pipeline_response TEXT,
        timestamp {timestamp_type}
    );
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS query_cache (
        normalized_input_hash TEXT PRIMARY KEY,
        original_input_text TEXT NOT NULL,
        full_pipeline_response TEXT NOT NULL,
        created_at {timestamp_type}
    );
    """)

    conn.commit()

    # Check if project_meta is empty -> Seed the database
    cursor.execute("SELECT COUNT(*) as count FROM project_meta;")
    row = cursor.fetchone()
    count = row["count"] if isinstance(row, dict) else row[0]
    
    if count == 0:
        if os.path.exists(SEED_PATH):
            with open(SEED_PATH, "r") as f:
                seed_data = json.load(f)

            try:
                # Seed project_meta
                meta = seed_data["project_meta"]
                cursor.execute(
                    "INSERT INTO project_meta (name, location, total_budget, spent_to_date) VALUES (?, ?, ?, ?);",
                    (meta["name"], meta["location"], meta["total_budget"], meta["spent_to_date"])
                )

                # Seed contractors
                for contractor in seed_data["contractors"]:
                    cursor.execute(
                        "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
                        (contractor["name"], contractor["scope"], contractor["daily_operating_cost"], contractor["daily_delay_penalty"], contractor["active_workers"])
                    )

                # Seed divisions
                for division in seed_data["divisions"]:
                    cursor.execute(
                        "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
                        (division["id"], division["name"], division["lead_contractor"])
                    )

                # Seed regulatory_kb
                for reg in seed_data["regulatory_kb"]:
                    cursor.execute(
                        "INSERT INTO regulatory_kb (code, description, trigger_condition) VALUES (?, ?, ?);",
                        (reg["code"], reg["description"], reg["trigger_condition"])
                    )

                # Seed schedule_tasks
                for task in seed_data["schedule_tasks"]:
                    cursor.execute(
                        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
                        (task["task_id"], task["division_id"], task["task_name"], task["duration"], task["is_critical_path"], task["dependencies"])
                    )

                conn.commit()
                logger.info("Database successfully seeded from seed_project_state.json")
            except Exception as e:
                conn.rollback()
                logger.error(f"Error seeding database: {e}")
                raise e
        else:
            logger.warning(f"Seed file not found at {SEED_PATH}")
    
    conn.close()


# ===========================================================================
# Query Response Cache Helper Functions
# ===========================================================================
# SAFETY BOUNDARY CONSTRAINT:
# Only exact normalized-text matches (lowercase, trimmed, single whitespace,
# SHA-256 hashed) will be cached and served from query_cache.
# Fuzzy matching, approximate matching, or keyword similarity search are
# strictly forbidden so that safety-critical compliance evaluations are never
# served from an approximate match.
# ===========================================================================

def get_cached_response(normalized_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a cached full pipeline response by exact normalized SHA-256 hash.
    Returns parsed dictionary or None if cache miss.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT full_pipeline_response FROM query_cache WHERE normalized_input_hash = ?;",
            (normalized_hash,)
        )
        row = cursor.fetchone()
        if row:
            resp_str = row["full_pipeline_response"] if isinstance(row, dict) else row[0]
            return json.loads(resp_str)
        return None
    except Exception as e:
        logger.warning(f"Failed to retrieve cached query response: {e}")
        return None
    finally:
        conn.close()


def save_cached_response(normalized_hash: str, original_text: str, response: dict):
    """
    Saves a successful live pipeline response to query_cache.
    WARNING: Only genuine live-Gemini responses with fallback_mode_active=False
    and without parse errors should be saved here.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO query_cache (normalized_input_hash, original_input_text, full_pipeline_response)
            VALUES (?, ?, ?);
            """,
            (normalized_hash, original_text, json.dumps(response))
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save query response to cache: {e}")
        conn.rollback()
    finally:
        conn.close()


def clear_query_cache() -> int:
    """
    Clears all entries from the query_cache table.
    Invoked when any project-setup data (contractors, divisions, schedule_tasks, regulatory_kb)
    is modified to prevent serving stale financial or safety numbers.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_cache;")
        deleted_count = cursor.rowcount
        conn.commit()
        logger.info(f"[CACHE INVALIDATION] Cleared query_cache table ({deleted_count} rows removed).")
        return deleted_count
    except Exception as e:
        logger.warning(f"Failed to clear query_cache: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
