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
    # L&T Construction has active_workers=120, daily_operating_cost=85000 (assumed wage per day is 120 * 1500 = 180000 > 85000 -> triggers negative clamp!)
    # Afcons Infrastructure has active_workers=45, daily_operating_cost=120000 (assumed wage per day is 45 * 1500 = 67500 < 120000 -> positive equipment residual!)
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
    
    # Idle labour check
    assert cb["idle_labour"]["amount"] == 120 * 1500 * 3
    assert cb["idle_labour"]["source"] == "assumed_wage_rate"
    assert "120" in cb["idle_labour"]["formula"]
    assert "1500" in cb["idle_labour"]["formula"]
    assert "3" in cb["idle_labour"]["formula"]
    
    # Equipment extension checks (negative case clamped and warned)
    assert cb["equipment_extension"]["amount"] == 0.0
    assert cb["equipment_extension"]["source"] == "assumed_residual"
    assert "warning" in cb["equipment_extension"]
    assert "exceeds" in cb["equipment_extension"]["warning"]
    
    # Delay penalty check
    assert cb["delay_penalty"]["amount"] == 75000 * 3
    assert cb["delay_penalty"]["source"] == "verified"
    assert cb["delay_penalty"]["formula"] == "contractor_penalty_rate \u00d7 delay_days"
    
    # Recovery overtime check
    assert cb["recovery_overtime"]["amount"] == 0.0
    assert cb["recovery_overtime"]["source"] == "assumed"
    
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
    - equipment_extension amount: 52,500 * 2 = 105,000 (positive residual, no warning!)
    - delay_penalty: 60,000 * 2 = 120,000
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
    
    # Idle labour check
    assert cb["idle_labour"]["amount"] == 45 * 1500 * 2
    
    # Equipment extension check
    assert cb["equipment_extension"]["amount"] == 52500 * 2
    assert "warning" not in cb["equipment_extension"]
    
    # Delay penalty check
    assert cb["delay_penalty"]["amount"] == 60000 * 2


def test_calculation_id_increments_and_is_stable():
    """
    calculation_id must increment for different stored calculations
    and remain stable (same ID returned) on repeat calls.
    """
    observe_output_1 = {
        "event_type": "work_at_height",
        "task_id": "T-101",
        "severity": 8, # maps to 3 delay days
        "task_not_matched": False,
        "parse_error": False
    }
    
    observe_output_2 = {
        "event_type": "electrical",
        "task_id": "T-104",
        "severity": 5, # maps to 2 delay days
        "task_not_matched": False,
        "parse_error": False
    }
    
    # First call for T-101 (3 days)
    res_1a = assess_finance(observe_output_1)
    id_1a = res_1a["calculation_id"]
    assert id_1a.startswith("FIN-")
    
    # Repeat call for T-101 (3 days) -> Must be exactly same ID
    res_1b = assess_finance(observe_output_1)
    id_1b = res_1b["calculation_id"]
    assert id_1a == id_1b
    
    # Call for different calculation -> Must be different ID
    res_2 = assess_finance(observe_output_2)
    id_2 = res_2["calculation_id"]
    assert id_1a != id_2
    
    # Verify sequential numbers (e.g. FIN-1 and FIN-2 or sequential increment in DB)
    num1 = int(id_1a.split("-")[1])
    num2 = int(id_2.split("-")[1])
    assert abs(num2 - num1) == 1


def test_simulate_delay_range_no_drift():
    """
    simulate_delay_range's 1/2/3-day outputs must match calling recalculate_schedule directly.
    """
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
    """
    If propose_reschedule hasn't run for this event, the avoided_loss field must be entirely
    absent from the response (not zero, not null, absent).
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    
    client = TestClient(app)
    
    # Sending a request where observe agent fails or we don't have task/cpm matching,
    # so cpm_result has parse_error = True or halted_task_id is None.
    # To trigger it cleanly, let's pass a text that won't match a task or causes a parse error.
    # If the observation stage returns task_not_matched=True, then cpm_result won't have halted_task_id,
    # and propose_reschedule won't run.
    payload = {"event_text": "An ambiguous jobsite report mentioning nothing matching the schedule."}
    
    response = client.post("/api/events", json=payload)
    assert response.status_code == 200
    
    body = response.json()
    assert "avoided_loss" not in body
    
    # If it matched T-104 (non-critical path, Afcons contractor), cpm_result project_delay is 0.
    # So propose_reschedule will run but maybe return feasible=False?
    # Let's test that if propose_reschedule DOES run, avoided_loss IS present.
    payload_t101 = {"event_text": "Tower Crane Lift is delayed by 2 days."}
    response_t101 = client.post("/api/events", json=payload_t101)
    assert response_t101.status_code == 200
    body_t101 = response_t101.json()
    
    # propose_reschedule ran for T-101 (since it's a critical path task with delay_days > 0).
    # Therefore, avoided_loss must be present in the response.
    assert "avoided_loss" in body_t101
    
    # Check avoided_loss values match calculate_avoided_loss logic
    al = body_t101["avoided_loss"]
    assert "avoided_loss" in al
    assert "baseline_exposure" in al
    assert "remaining_exposure" in al
    assert "recovery_cost" in al
