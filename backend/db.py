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

if __name__ == "__main__":
    init_db()
