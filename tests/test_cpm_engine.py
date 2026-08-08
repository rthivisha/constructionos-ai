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
    # T1: "Excavation and Site Preparation"
    # Division: DIV-CIVIL -> L&T Construction
    # Daily Operating Cost: 150000, Delay Penalty: 50000, Critical Path: 1
    impact = get_task_impact("Excavation and Site Preparation")
    
    assert impact["assigned_crew"] == "L&T Construction"
    assert impact["daily_operating_cost"] == 150000.0
    assert impact["contractor_penalty_rate"] == 50000.0
    assert impact["critical_path"] is True
    assert impact["fallback_mode_active"] is False

    # T3: "Electrical Conduit Laying"
    # Division: DIV-ELEC -> Siemens Mobility
    # Daily Operating Cost: 120000, Delay Penalty: 40000, Critical Path: 0
    impact_t3 = get_task_impact("Electrical Conduit Laying")
    assert impact_t3["assigned_crew"] == "Siemens Mobility"
    assert impact_t3["daily_operating_cost"] == 120000.0
    assert impact_t3["contractor_penalty_rate"] == 40000.0
    assert impact_t3["critical_path"] is False

    # Check case-insensitivity
    impact_case = get_task_impact("  excavation and site preparation  ")
    assert impact_case["assigned_crew"] == "L&T Construction"

    # Invalid task raises ValueError
    with pytest.raises(ValueError):
        get_task_impact("Non-existent task name")

def test_recalculate_schedule_critical_delay():
    # Delay T1 (Excavation) by 5 days.
    # T1 is critical, baseline project duration is 75 days (T1=15, T2=20, T4=25, T6=15)
    # T1 delayed by 5 days -> new project duration should be 80 days (project delay = 5 days)
    res = recalculate_schedule("T1", 5)
    
    assert res["halted_task_id"] == "T1"
    assert res["delay_days"] == 5
    assert res["baseline_project_duration"] == 75
    assert res["new_project_duration"] == 80
    assert res["project_delay"] == 5
    assert res["fallback_mode_active"] is False

    # Let's inspect the cost breakdown
    breakdown = res["breakdown"]
    
    # Check shifted tasks
    # Delaying T1 shifts T1, T2, T3, T4, T5, T6 (virtually every task shifts since T1 is the root)
    shifted_ids = {t["task_id"] for t in breakdown["shifted_tasks"]}
    assert "T1" in shifted_ids
    assert "T2" in shifted_ids
    assert "T6" in shifted_ids

    # Check penalized tasks
    # T1 finish shifts 15 -> 20 (exceeds original 15) -> Penalized
    # T2 finish shifts 35 -> 40 (exceeds original 35) -> Penalized
    # T4 finish shifts 60 -> 65 (exceeds original 60) -> Penalized
    # T6 finish shifts 75 -> 80 (exceeds original 75) -> Penalized
    penalized_ids = {t["task_id"] for t in breakdown["penalized_tasks"]}
    assert "T1" in penalized_ids
    assert "T2" in penalized_ids
    assert "T4" in penalized_ids
    assert "T6" in penalized_ids

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
    # Delay T3 (Electrical Conduit Laying) by 5 days.
    # T3 (duration 10, starts at 35, ends 45, slack 3).
    # Delaying T3 by 5 days: duration becomes 15.
    # Early finish of T3 becomes 50 (originally 45).
    # T5 depends on T3, start shifts 45 -> 50, duration 12, finish shifts 57 -> 62 (exceeds original 57 by 5 days).
    # T6 depends on T4 (ends 60) and T5 (ends 62). So T6 starts at 62 (originally 60), finish shifts 75 -> 77.
    # Project delay = 77 - 75 = 2 days.
    # Shifted tasks should be: T3, T5, T6 (since their dates changed). T1, T2, T4 are unchanged.
    res = recalculate_schedule("T3", 5)

    assert res["baseline_project_duration"] == 75
    assert res["new_project_duration"] == 77
    assert res["project_delay"] == 2

    breakdown = res["breakdown"]
    shifted_ids = {t["task_id"] for t in breakdown["shifted_tasks"]}
    assert shifted_ids == {"T3", "T5", "T6"}

    # Penalized tasks: new finish > baseline finish
    # T3: baseline finish 45, new finish 50 (exceeds by 5)
    # T5: baseline finish 57, new finish 62 (exceeds by 5)
    # T6: baseline finish 75, new finish 77 (exceeds by 2)
    penalized_tasks = {t["task_id"]: t for t in breakdown["penalized_tasks"]}
    assert set(penalized_tasks.keys()) == {"T3", "T5", "T6"}
    
    assert penalized_tasks["T3"]["delay_days"] == 5
    assert penalized_tasks["T5"]["delay_days"] == 5
    assert penalized_tasks["T6"]["delay_days"] == 2

    # Verify costs
    sum_operating_cost = sum(t["daily_operating_cost"] for t in breakdown["shifted_tasks"])
    assert breakdown["operating_cost_exposure"] == 5 * sum_operating_cost
    
    expected_penalty_exposure = (
        5 * penalized_tasks["T3"]["daily_delay_penalty"] +
        5 * penalized_tasks["T5"]["daily_delay_penalty"] +
        2 * penalized_tasks["T6"]["daily_delay_penalty"]
    )
    assert breakdown["penalty_exposure"] == expected_penalty_exposure
    assert res["total_financial_exposure"] == (5 * sum_operating_cost) + expected_penalty_exposure

def test_recalculate_schedule_zero_delay():
    res = recalculate_schedule("T1", 0)
    assert res["project_delay"] == 0
    assert res["total_financial_exposure"] == 0.0

def test_recalculate_schedule_invalid_parameters():
    with pytest.raises(ValueError):
        recalculate_schedule("T1", -5)
    with pytest.raises(ValueError):
        recalculate_schedule("NON_EXISTENT", 5)

def test_fallback_mode_triggered():
    # Set the DB path to a non-existent database file
    backend.db.DB_PATH = "this_file_definitely_does_not_exist.db"
    
    # Trigger get_task_impact and recalculate_schedule, verify fallback is true
    # and they still complete successfully using seed_project_state.json
    try:
        impact = get_task_impact("Excavation and Site Preparation")
        assert impact["fallback_mode_active"] is True
        assert impact["assigned_crew"] == "L&T Construction"
        
        res = recalculate_schedule("T1", 5)
        assert res["fallback_mode_active"] is True
        assert res["project_delay"] == 5
    finally:
        # Restore DB path
        backend.db.DB_PATH = TEST_DB_PATH

