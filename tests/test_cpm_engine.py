import os
import tempfile
import pytest
import sqlite3

# Monkeypatch DB path for cpm_engine to use a temporary DB for isolation
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db

from backend.db import init_db
from backend.tools.cpm_engine import get_task_impact, recalculate_schedule, get_project_state

@pytest.fixture(autouse=True)
def setup_test_db():
    backend.db.DB_PATH = TEST_DB_PATH
    # Fresh database initialization before each test
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    init_db()
    yield
    # Cleanup after test run
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

def test_get_task_impact_database_mode():
    # T-101: "Tower Crane Lift"
    # Division: DIV-A -> L&T Construction
    # Daily Operating Cost: 85000, Delay Penalty: 75000, Critical Path: 1
    impact = get_task_impact("Tower Crane Lift")
    
    assert impact["assigned_crew"] == "L&T Construction"
    assert impact["daily_operating_cost"] == 85000.0
    assert impact["contractor_penalty_rate"] == 75000.0
    assert impact["critical_path"] is True
    assert impact["fallback_mode_active"] is False

    # T-104: "Electrical Conduit Laying"
    # Division: DIV-B -> Afcons Infrastructure
    # Daily Operating Cost: 120000, Delay Penalty: 60000, Critical Path: 0
    impact_t104 = get_task_impact("Electrical Conduit Laying")
    assert impact_t104["assigned_crew"] == "Afcons Infrastructure"
    assert impact_t104["daily_operating_cost"] == 120000.0
    assert impact_t104["contractor_penalty_rate"] == 60000.0
    assert impact_t104["critical_path"] is False

    # Check case-insensitivity
    impact_case = get_task_impact("  tower crane lift  ")
    assert impact_case["assigned_crew"] == "L&T Construction"

    # Invalid task raises ValueError
    with pytest.raises(ValueError):
        get_task_impact("Non-existent task name")

def test_recalculate_schedule_critical_delay():
    # Delay T-101 (Tower Crane Lift) by 5 days.
    # T-101 is critical, baseline project duration is 33 days (T-101=10, T-102=15, T-103=8)
    # T-101 delayed by 5 days -> new project duration should be 38 days (project delay = 5 days)
    res = recalculate_schedule("T-101", 5)
    
    assert res["halted_task_id"] == "T-101"
    assert res["delay_days"] == 5
    assert res["baseline_project_duration"] == 33
    assert res["new_project_duration"] == 38
    assert res["project_delay"] == 5
    assert res["fallback_mode_active"] is False

    # Let's inspect the cost breakdown
    breakdown = res["breakdown"]
    
    # Check shifted tasks
    # Delaying T-101 shifts T-101, T-102, T-103, T-104 (all tasks shift since T-101 is the root)
    shifted_ids = {t["task_id"] for t in breakdown["shifted_tasks"]}
    assert "T-101" in shifted_ids
    assert "T-102" in shifted_ids
    assert "T-103" in shifted_ids
    assert "T-104" in shifted_ids

    # Check penalized tasks
    penalized_ids = {t["task_id"] for t in breakdown["penalized_tasks"]}
    assert "T-101" in penalized_ids
    assert "T-102" in penalized_ids
    assert "T-103" in penalized_ids
    assert "T-104" in penalized_ids

    # Verify mathematical correctness of the exposure
    # Sum of operating cost of shifted tasks * delay_days
    sum_operating_cost = sum(t["daily_operating_cost"] for t in breakdown["shifted_tasks"])
    expected_operating_exposure = 5 * sum_operating_cost
    assert breakdown["operating_cost_exposure"] == expected_operating_exposure

    # Penalty exposure: sum of task delay * penalty_rate for penalized tasks
    expected_penalty_exposure = 0.0
    for p in breakdown["penalized_tasks"]:
        expected_penalty_exposure += p["delay_days"] * p["daily_delay_penalty"]
    assert breakdown["penalty_exposure"] == expected_penalty_exposure
    assert res["total_financial_exposure"] == expected_operating_exposure + expected_penalty_exposure

def test_recalculate_schedule_non_critical_delay():
    # Delay T-104 (Electrical Conduit Laying) by 5 days.
    # T-104 (duration 5, starts at 10, ends 15, slack 18).
    # Delaying T-104 by 5 days: duration becomes 10.
    # Early finish of T-104 becomes 20 (originally 15).
    # This is less than baseline project duration (33), so project delay is 0.
    # Shifted tasks should be: T-104 (its dates changed).
    res = recalculate_schedule("T-104", 5)

    assert res["baseline_project_duration"] == 33
    assert res["new_project_duration"] == 33
    assert res["project_delay"] == 0

    breakdown = res["breakdown"]
    shifted_ids = {t["task_id"] for t in breakdown["shifted_tasks"]}
    assert shifted_ids == {"T-104"}

    # Penalized tasks: new finish > baseline finish
    # T-104: baseline finish 15, new finish 20 (exceeds by 5)
    penalized_tasks = {t["task_id"]: t for t in breakdown["penalized_tasks"]}
    assert set(penalized_tasks.keys()) == {"T-104"}
    
    assert penalized_tasks["T-104"]["delay_days"] == 5

    # Verify costs
    sum_operating_cost = sum(t["daily_operating_cost"] for t in breakdown["shifted_tasks"])
    assert breakdown["operating_cost_exposure"] == 5 * sum_operating_cost
    
    expected_penalty_exposure = 5 * penalized_tasks["T-104"]["daily_delay_penalty"]
    assert breakdown["penalty_exposure"] == expected_penalty_exposure
    assert res["total_financial_exposure"] == (5 * sum_operating_cost) + expected_penalty_exposure

def test_recalculate_schedule_zero_delay():
    res = recalculate_schedule("T-101", 0)
    assert res["project_delay"] == 0
    assert res["total_financial_exposure"] == 0.0

def test_recalculate_schedule_invalid_parameters():
    with pytest.raises(ValueError):
        recalculate_schedule("T-101", -5)
    with pytest.raises(ValueError):
        recalculate_schedule("NON_EXISTENT", 5)

def test_fallback_mode_triggered():
    # Set the DB path to a non-existent database file
    backend.db.DB_PATH = "this_file_definitely_does_not_exist.db"
    
    # Trigger get_task_impact and recalculate_schedule, verify fallback is true
    try:
        impact = get_task_impact("Tower Crane Lift")
        assert impact["fallback_mode_active"] is True
        assert impact["assigned_crew"] == "L&T Construction"
        
        res = recalculate_schedule("T-101", 5)
        assert res["fallback_mode_active"] is True
        assert res["project_delay"] == 5
    finally:
        # Restore DB path
        backend.db.DB_PATH = TEST_DB_PATH
