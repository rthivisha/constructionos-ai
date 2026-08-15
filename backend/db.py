import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constructionos.db")
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data", "seed_project_state.json")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_meta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        lead_contractor TEXT NOT NULL,
        FOREIGN KEY(lead_contractor) REFERENCES contractors(name) ON UPDATE CASCADE ON DELETE RESTRICT
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
        division_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        duration INTEGER NOT NULL,
        is_critical_path INTEGER NOT NULL,
        dependencies TEXT NOT NULL,
        FOREIGN KEY(division_id) REFERENCES divisions(id) ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS finance_calculations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        delay_days INTEGER NOT NULL,
        UNIQUE(task_id, delay_days)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS site_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_text TEXT NOT NULL,
        filename TEXT,
        file_path TEXT,
        content_type TEXT,
        pipeline_response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_cache (
        normalized_input_hash TEXT PRIMARY KEY,
        original_input_text TEXT NOT NULL,
        full_pipeline_response TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # Check if project_meta is empty -> Seed the database
    cursor.execute("SELECT COUNT(*) FROM project_meta;")
    if cursor.fetchone()[0] == 0:
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
                print("Database successfully seeded from seed_project_state.json")
            except Exception as e:
                conn.rollback()
                print(f"Error seeding database: {e}")
                raise e
        else:
            print(f"Seed file not found at {SEED_PATH}")
    
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

def get_cached_response(normalized_hash: str):
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
            return json.loads(row["full_pipeline_response"])
        return None
    except Exception as e:
        print(f"Warning: Failed to retrieve cached query response: {e}")
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
        print(f"Warning: Failed to save query response to cache: {e}")
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
        print(f"[CACHE INVALIDATION] Cleared query_cache table ({deleted_count} rows removed).")
        return deleted_count
    except Exception as e:
        print(f"Warning: Failed to clear query_cache: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()

