import os
import tempfile
import sqlite3
import pytest

# ─── Isolate the test DB ──────────────────────────────────────────────────────
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db
import backend.tools.cpm_engine

# Override database path for testing
backend.db.DB_PATH = TEST_DB_PATH
backend.tools.cpm_engine.DB_PATH = TEST_DB_PATH

from backend.db import init_db
from backend.agents.finance_agent import assess_finance, simulate_delay_range, calculate_avoided_loss
from backend.tools.cpm_engine import recalculate_schedule
from backend.config import ASSUMED_DAILY_WAGE_PER_WORKER


def seed_test_data():
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule_tasks;")
    cursor.execute("DELETE FROM divisions;")
    cursor.execute("DELETE FROM contractors;")
    cursor.execute("DELETE FROM project_meta;")
    cursor.execute("DELETE FROM regulatory_kb;")
    
    # Project Meta
    cursor.execute(
        "INSERT INTO project_meta (name, location, total_budget, spent_to_date) VALUES (?, ?, ?, ?);",
        ("Test Project", "Delhi, India", 100000000.0, 20000000.0)
    )
    
    # Contractors
    cursor.execute(
        "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
        ("L&T Construction", "Structural work", 85000.0, 75000.0, 120)
    )
    cursor.execute(
        "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
        ("Afcons Infrastructure", "Electrical work", 120000.0, 60000.0, 45)
    )
    
    # Divisions
    cursor.execute(
        "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
        ("DIV-A", "Civil", "L&T Construction")
    )
    cursor.execute(
        "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
        ("DIV-B", "Electrical", "Afcons Infrastructure")
    )
    
    # Tasks
    cursor.execute(
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
        ("T-101", "DIV-A", "Tower Crane Lift", 10, 1, "")
    )
    cursor.execute(
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
        ("T-104", "DIV-B", "Electrical Conduit Laying", 5, 0, "T-101")
    )
    
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    backend.db.DB_PATH = TEST_DB_PATH
    backend.tools.cpm_engine.DB_PATH = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    init_db()
    seed_test_data()
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


def test_cost_breakdown_formulas_match_manually_computed_t101():
    """
    T-101 scenario has L&T Construction.
    - active_workers = 120
    - assumed wage rate = 1500
    - delay_days = 3
    Manually computed values:
    - idle_labour: 120 * 1500 * 3 = 540,000
    - equipment_extension: 85,000 - 180,000 = -95,000 -> clamped to 0.0 with warning!
    - delay_penalty: 75,000 * 3 = 225,000
    - halted_task_total: 540,000 + 0 + 225,000 = 765,000
    """
    observe_output = {
        "event_type": "work_at_height",
        "task_id": "T-101",
        "severity": 8, # maps to 3 delay days
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_finance(observe_output)
    
    assert res["status"] == "success"
    assert res["delay_days_used"] == 3
    
    cb = res["cost_breakdown"]
    
    # Verify Option A scoping keys
    assert cb["scope"] == "halted_task_only"
    assert cb["halted_task_total"] == 765000.0
    assert res["cpm_result"]["scope"] == "project_cascade"
    
    # Idle labour check
    assert cb["idle_labour"]["amount"] == 120 * 1500 * 3
    assert cb["idle_labour"]["source"] == "assumed_wage_rate"
    
    # Equipment extension checks (negative case clamped and warned)
    assert cb["equipment_extension"]["amount"] == 0.0
    assert cb["equipment_extension"]["source"] == "assumed_residual"
    assert "warning" in cb["equipment_extension"]
    
    # Delay penalty check
    assert cb["delay_penalty"]["amount"] == 75000 * 3
    
    assert res["cost_coverage"] == "1/3 verified, 2 estimated"


def test_positive_equipment_extension_residual():
    """
    T-104 scenario has Afcons Infrastructure.
    - active_workers = 45
    - daily_operating_cost = 120,000
    - assumed wage rate = 1500
    - delay_days = 2 (derived from severity 5)
    Manually computed values:
    - idle_labour: 45 * 1500 * 2 = 135,000
    - daily equipment residual: 120,000 - 67,500 = 52,500
    - equipment_extension amount: 52,500 * 2 = 105,000
    - delay_penalty: 60,000 * 2 = 120,000
    - halted_task_total: 135,000 + 105,000 + 120,000 = 360,000
    """
    observe_output = {
        "event_type": "electrical",
        "task_id": "T-104",
        "severity": 5, # maps to 2 delay days
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_finance(observe_output)
    
    assert res["status"] == "success"
    assert res["delay_days_used"] == 2
    
    cb = res["cost_breakdown"]
    
    assert cb["scope"] == "halted_task_only"
    assert cb["halted_task_total"] == 360000.0
    assert cb["equipment_extension"]["amount"] == 52500 * 2
    assert "warning" not in cb["equipment_extension"]


def test_calculation_id_increments_and_is_stable():
    observe_output_1 = {
        "event_type": "work_at_height",
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    observe_output_2 = {
        "event_type": "electrical",
        "task_id": "T-104",
        "severity": 5,
        "task_not_matched": False,
        "parse_error": False
    }
    
    res_1a = assess_finance(observe_output_1)
    id_1a = res_1a["calculation_id"]
    
    res_1b = assess_finance(observe_output_1)
    id_1b = res_1b["calculation_id"]
    assert id_1a == id_1b
    
    res_2 = assess_finance(observe_output_2)
    id_2 = res_2["calculation_id"]
    assert id_1a != id_2
    
    num1 = int(id_1a.split("-")[1])
    num2 = int(id_2.split("-")[1])
    assert abs(num2 - num1) == 1


def test_simulate_delay_range_no_drift():
    task_id = "T-101"
    sim = simulate_delay_range(task_id)
    assert set(sim.keys()) == {"1_day", "2_day", "3_day"}
    
    cpm_1 = recalculate_schedule(task_id, 1)
    cpm_2 = recalculate_schedule(task_id, 2)
    cpm_3 = recalculate_schedule(task_id, 3)
    
    assert sim["1_day"] == cpm_1["total_financial_exposure"]
    assert sim["2_day"] == cpm_2["total_financial_exposure"]
    assert sim["3_day"] == cpm_3["total_financial_exposure"]


def test_avoided_loss_absent_when_propose_reschedule_not_run():
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)
    
    payload = {"event_text": "An ambiguous jobsite report mentioning nothing matching the schedule."}
    response = client.post("/api/events", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "avoided_loss" not in body
    
    payload_t101 = {"event_text": "Tower Crane Lift is delayed by 2 days."}
    response_t101 = client.post("/api/events", json=payload_t101)
    assert response_t101.status_code == 200
    body_t101 = response_t101.json()
    assert "avoided_loss" in body_t101
    
    al = body_t101["avoided_loss"]
    assert "avoided_loss" in al
    assert "baseline_exposure" in al
