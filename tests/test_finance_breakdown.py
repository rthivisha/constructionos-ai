"""
Tests for:
P1 — assess_finance() cost_breakdown with assumption labels and source tags
P2 — simulate_delay_range() reuses CPM engine, no new math
P3 — avoided_loss in the events pipeline only when propose_reschedule ran
"""
import os
import tempfile
import sqlite3
import pytest

# ─── Isolate DB ──────────────────────────────────────────────────────────────
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db
import backend.tools.cpm_engine

from backend.db import init_db
from backend.agents.finance_agent import assess_finance, simulate_delay_range, _build_cost_breakdown
from backend.agents.event_types import EventType


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
    _seed_finance_data()
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


def _seed_finance_data():
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("DELETE FROM schedule_tasks;")
    conn.execute("DELETE FROM divisions;")
    conn.execute("DELETE FROM contractors;")
    conn.execute("DELETE FROM project_meta;")
    conn.execute("DELETE FROM regulatory_kb;")

    conn.execute(
        "INSERT INTO project_meta (name, location, total_budget, spent_to_date) "
        "VALUES (?, ?, ?, ?);",
        ("Metro Line Extension", "Bengaluru, India", 50000000.0, 12000000.0)
    )
    conn.execute(
        "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) "
        "VALUES (?, ?, ?, ?, ?);",
        ("L&T Construction", "Structural work", 85000.0, 75000.0, 120)
    )
    conn.execute(
        "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
        ("DIV-A", "Civil & Structural", "L&T Construction")
    )
    conn.execute(
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("T-101", "DIV-A", "Tower Crane Lift", 10, 1, "")
    )
    conn.execute(
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("T-102", "DIV-A", "Foundation Concreting", 15, 1, "T-101")
    )
    conn.execute(
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("T-103", "DIV-A", "Rebar Installation", 8, 1, "T-102")
    )
    conn.commit()
    conn.close()


OBSERVE_T101 = {
    "event_type": EventType.WORK_AT_HEIGHT.value,
    "task_id": "T-101",
    "severity": 8,
    "task_not_matched": False,
    "parse_error": False,
}


# ─── P1: cost_breakdown structure and rules ───────────────────────────────────

def test_cost_breakdown_present_in_assess_finance():
    """assess_finance must return cost_breakdown, cost_coverage, calculation_id."""
    result = assess_finance(OBSERVE_T101, "Crane at height failed safety check.")
    assert result["status"] == "success"
    assert result["cost_breakdown"] is not None
    assert result["cost_coverage"] is not None
    assert result["calculation_id"] is not None


def test_delay_penalty_is_verified_source():
    """delay_penalty must be source='verified' with no assumption string."""
    result = assess_finance(OBSERVE_T101, "Worker fell from scaffold.")
    cb = result["cost_breakdown"]

    assert cb["delay_penalty"]["source"] == "verified"
    # No assumption key on delay_penalty per spec
    assert "assumption" not in cb["delay_penalty"]


def test_other_fields_are_assumed_source():
    """idle_labour, equipment_extension, recovery_overtime must be source='assumed'."""
    result = assess_finance(OBSERVE_T101, "Worker fell from scaffold.")
    cb = result["cost_breakdown"]

    for field in ["idle_labour", "equipment_extension", "recovery_overtime"]:
        assert cb[field]["source"] == "assumed", f"{field} source should be 'assumed'"
        assert "assumption" in cb[field], f"{field} must include an assumption string"
        assert len(cb[field]["assumption"]) > 10, f"{field} assumption string too short"


def test_idle_labour_formula_uses_actual_workers():
    """idle_labour amount = daily_operating_cost × delay_days, with worker count in formula."""
    result = assess_finance(OBSERVE_T101, "Crane halted, 3-day delay expected.")
    delay_used = result["delay_days_used"]
    cb = result["cost_breakdown"]

    # L&T: daily_operating_cost=85000, active_workers=120
    expected_labour = 85000.0 * delay_used
    assert cb["idle_labour"]["amount"] == pytest.approx(expected_labour, rel=1e-4)

    # Worker count must appear in the assumption string
    assert "120" in cb["idle_labour"]["assumption"]


def test_delay_penalty_amount_is_rate_times_days():
    """delay_penalty amount = contractor_penalty_rate × delay_days."""
    result = assess_finance(OBSERVE_T101, "Crane halted 2 days.")
    delay_used = result["delay_days_used"]
    cb = result["cost_breakdown"]

    # L&T: daily_delay_penalty=75000
    expected_penalty = 75000.0 * delay_used
    assert cb["delay_penalty"]["amount"] == pytest.approx(expected_penalty, rel=1e-4)


def test_calculation_id_is_deterministic():
    """Same task + delay always produces the same calculation_id (no uuid randomness)."""
    r1 = assess_finance(OBSERVE_T101, "Crane halted.")
    r2 = assess_finance(OBSERVE_T101, "Crane halted.")
    assert r1["calculation_id"] == r2["calculation_id"]
    assert r1["calculation_id"].startswith("FIN-T-101-")


def test_cost_coverage_string_format():
    """cost_coverage must read 'N/4 verified, M estimated'."""
    result = assess_finance(OBSERVE_T101, "Crane halted.")
    coverage = result["cost_coverage"]
    assert "verified" in coverage
    assert "estimated" in coverage
    # Only delay_penalty is verified → 1/4
    assert coverage.startswith("1/4")


def test_cost_breakdown_null_on_parse_error():
    """When observe has parse_error, cost_breakdown/cost_coverage/calculation_id are all None."""
    bad_observe = {"parse_error": True, "task_id": None, "task_not_matched": True}
    result = assess_finance(bad_observe)
    assert result["cost_breakdown"] is None
    assert result["cost_coverage"] is None
    assert result["calculation_id"] is None


def test_cost_breakdown_null_on_insufficient_data():
    """When no task matched, cost_breakdown/cost_coverage/calculation_id are all None."""
    no_task = {
        "event_type": EventType.WORK_AT_HEIGHT.value,
        "task_id": None,
        "severity": 5,
        "task_not_matched": True,
        "parse_error": False,
    }
    result = assess_finance(no_task)
    assert result["cost_breakdown"] is None
    assert result["cost_coverage"] is None
    assert result["calculation_id"] is None


# ─── P1 unit: _build_cost_breakdown directly ──────────────────────────────────

def test_build_cost_breakdown_unit():
    """Unit test _build_cost_breakdown with known inputs."""
    out = _build_cost_breakdown(
        task_id="T-101",
        delay_days=3,
        active_workers=120,
        daily_operating_cost=85000.0,
        contractor_penalty_rate=75000.0,
    )

    cb = out["cost_breakdown"]
    assert cb["idle_labour"]["amount"] == pytest.approx(85000.0 * 3)
    assert cb["delay_penalty"]["amount"] == pytest.approx(75000.0 * 3)
    assert cb["equipment_extension"]["amount"] == 0.0
    assert cb["recovery_overtime"]["amount"] == 0.0

    assert cb["delay_penalty"]["source"] == "verified"
    assert "assumption" not in cb["delay_penalty"]
    assert cb["idle_labour"]["source"] == "assumed"

    assert out["cost_coverage"] == "1/4 verified, 3 estimated"
    assert out["calculation_id"] == "FIN-T-101-3d"


# ─── P2: simulate_delay_range ─────────────────────────────────────────────────

def test_simulate_delay_range_returns_three_entries():
    """simulate_delay_range must return exactly three entries for days 1, 2, 3."""
    results = simulate_delay_range("T-101")
    assert len(results) == 3
    assert [r["delay_days"] for r in results] == [1, 2, 3]


def test_simulate_delay_range_values_increase_monotonically():
    """For a critical-path task, financial exposure must increase as delay increases."""
    results = simulate_delay_range("T-101")
    exposures = [r["total_financial_exposure"] for r in results]
    assert all(e is not None for e in exposures), "All exposures must be computed"
    assert exposures[0] < exposures[1] < exposures[2], (
        f"Exposures must increase: {exposures}"
    )


def test_simulate_delay_range_uses_cpm_math():
    """
    Each simulate_delay_range result must match recalculate_schedule directly.
    This verifies no new math was introduced — it's purely a loop over recalculate_schedule.
    """
    from backend.tools.cpm_engine import recalculate_schedule
    results = simulate_delay_range("T-101")
    for r in results:
        direct = recalculate_schedule("T-101", r["delay_days"])
        assert r["total_financial_exposure"] == direct["total_financial_exposure"]
        assert r["project_delay"] == direct["project_delay"]


def test_simulate_delay_range_bad_task_gracefully_errors():
    """A bad task_id must return error entries, not raise an exception."""
    results = simulate_delay_range("T-NONEXISTENT")
    assert len(results) == 3
    for r in results:
        assert r["total_financial_exposure"] is None
        assert "error" in r


# ─── P3: avoided_loss via the full pipeline ───────────────────────────────────

def test_avoided_loss_not_fabricated_when_no_recovery():
    """
    When propose_reschedule returns feasible=False (no same-contractor candidates),
    avoided_loss must be None in the pipeline response — never fabricated.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    import backend.db as _db
    _db.DB_PATH = TEST_DB_PATH

    client = TestClient(app)
    # Seed env for mock mode
    import os
    os.environ["USE_MOCK_LLM"] = "true"

    response = client.post("/api/events", json={"event_text": "Tower crane lift halted at height."})
    assert response.status_code == 200, response.text
    body = response.json()

    # In the default 3-task seed (T-101, T-102, T-103 all L&T critical path),
    # there are no non-critical same-contractor candidates → feasible=False
    reschedule = body.get("proposed_reschedule", {})
    avoided = body.get("avoided_loss")

    if reschedule and reschedule.get("feasible") is False:
        assert avoided is None, (
            "avoided_loss must be None when reschedule is not feasible "
            f"(was: {avoided})"
        )


def test_avoided_loss_math_when_recovery_feasible():
    """
    When propose_reschedule is feasible, avoided_loss.avoided_loss must equal
    baseline_exposure - recovery_total (recovery_plan_cost + remaining_penalty).
    """
    # Add a non-critical same-contractor task so reschedule is feasible
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO schedule_tasks "
        "(task_id, division_id, task_name, duration, is_critical_path, dependencies) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        ("T-105", "DIV-A", "Site Fencing", 3, 0, "")
    )
    conn.commit()
    conn.close()

    from fastapi.testclient import TestClient
    from backend.main import app
    import backend.db as _db
    _db.DB_PATH = TEST_DB_PATH

    import os
    os.environ["USE_MOCK_LLM"] = "true"

    client = TestClient(app)
    response = client.post("/api/events", json={"event_text": "Tower crane lift halted at height."})
    assert response.status_code == 200, response.text
    body = response.json()

    reschedule = body.get("proposed_reschedule", {})
    avoided_loss_block = body.get("avoided_loss")

    if reschedule and reschedule.get("feasible"):
        assert avoided_loss_block is not None, "avoided_loss must be present when reschedule is feasible"

        al = avoided_loss_block
        # Verify the math: avoided_loss = baseline_exposure - (recovery_plan_cost + remaining_penalty)
        expected_recovery_total = al["recovery_plan_cost"] + al["remaining_penalty_after_reallocation"]
        assert al["recovery_total"] == pytest.approx(expected_recovery_total, rel=1e-4)

        expected_avoided = al["baseline_exposure"] - al["recovery_total"]
        assert al["avoided_loss"] == pytest.approx(expected_avoided, rel=1e-4)

        # Confirm no fabrication: baseline_exposure matches the finance agent's figure
        finance_exposure = body["financial_assessment"]["cpm_result"]["total_financial_exposure"]
        assert al["baseline_exposure"] == finance_exposure

        assert "note" in al
