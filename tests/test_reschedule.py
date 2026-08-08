"""
Tests for propose_reschedule() and POST /api/schedule/apply-reschedule.

Required coverage:
(a) A 2-day T-101 halt produces a correctly computed T-102 shift.
(b) Reallocation only ever proposes moves within the same contractor, never across.
(c) Calling the pipeline twice on the same event does NOT double-apply anything,
    since nothing is persisted until apply-reschedule is explicitly called.
"""
import os
import tempfile
import sqlite3
import pytest

# ─── Isolate the test DB ──────────────────────────────────────────────────────
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db
from backend.db import init_db
from backend.tools.cpm_engine import recalculate_schedule, propose_reschedule


@pytest.fixture(autouse=True)
def setup_test_db():
    """Fresh isolated DB before every test."""
    backend.db.DB_PATH = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
    init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


# ─── Seed data helpers ────────────────────────────────────────────────────────

def _seed_extra_tasks(tasks: list[dict]):
    """
    Insert additional schedule_tasks rows into the test DB.
    Used to set up multi-contractor / multi-slack scenarios.
    """
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    for t in tasks:
        conn.execute(
            "INSERT OR REPLACE INTO schedule_tasks "
            "(task_id, division_id, task_name, duration, is_critical_path, dependencies) "
            "VALUES (?, ?, ?, ?, ?, ?);",
            (t["task_id"], t["division_id"], t["task_name"],
             t["duration"], t["is_critical_path"], t.get("dependencies", ""))
        )
    conn.commit()
    conn.close()


def _get_task_duration(task_id: str) -> int:
    conn = sqlite3.connect(TEST_DB_PATH)
    row = conn.execute(
        "SELECT duration FROM schedule_tasks WHERE task_id = ?;", (task_id,)
    ).fetchone()
    conn.close()
    assert row is not None, f"task {task_id} not found"
    return row[0]


# ─── Test (a): 2-day T-101 halt → correct T-102 shift proposal ───────────────

def test_two_day_t101_halt_produces_t102_shift():
    """
    T-101 (Tower Crane Lift) is the root critical task.
    T-104 (Electrical Conduit Laying, DIV-B, Afcons) depends on T-101 and
    has slack in the delayed schedule.

    After a 2-day T-101 delay:
    - Baseline: T-101(0-10) → T-102(10-25) → T-103(25-33), T-104(10-15, slack=18)
    - Delayed:  T-101 duration becomes 12 → T-101(0-12) → T-102(12-27) → ...
      T-104(12-17, slack still available)

    propose_reschedule should:
    - Report the delay_days = 2
    - Find T-104 as the only non-critical task
    - BUT T-104 is under Afcons (DIV-B) and T-101 is under L&T (DIV-A),
      so T-104 is EXCLUDED by the same-contractor rule.
    - Therefore proposed_reschedule is empty and net_delay_reduction_days == 0.

    To verify a POSITIVE shift, we add a non-critical DIV-A task (L&T, same contractor)
    with enough slack. We insert T-105 (DIV-A, duration=3, depends on nothing,
    is_critical_path=0). After a 2-day T-101 delay it will have slack.
    """
    # Add a non-critical L&T task so there IS a valid candidate
    _seed_extra_tasks([{
        "task_id": "T-105",
        "division_id": "DIV-A",       # L&T Construction — same as T-101
        "task_name": "Site Fencing",
        "duration": 3,
        "is_critical_path": 0,
        "dependencies": "",
    }])

    cpm_result = recalculate_schedule("T-101", 2)

    # Confirm the CPM ran correctly
    assert cpm_result["delay_days"] == 2
    assert cpm_result["project_delay"] == 2

    # T-105 is non-critical with baseline project duration 33 → slack = 33 - 3 = 30
    # After T-101 delay of 2 → project duration 35 → T-105 slack = 35 - 3 = 32
    t105_delayed_slack = cpm_result["tasks"]["T-105"]["delayed"]["slack"]
    assert t105_delayed_slack > 0, "T-105 must have positive slack in delayed schedule"

    proposal = propose_reschedule(cpm_result)

    assert proposal["halted_task_id"] == "T-101"
    assert proposal["feasible"] is True
    assert proposal["net_delay_reduction_days"] == 2

    # The calculation_detail must show the actual slack value used, not a hardcoded constant
    detail = proposal["calculation_detail"]
    assert "slack=" in detail
    assert "2d" in detail or "absorbs 2" in detail

    # Only T-105 (same L&T contractor) should be in the proposal
    proposed_ids = {p["task_id"] for p in proposal["proposed_reschedule"]}
    assert "T-105" in proposed_ids
    # T-104 (Afcons, different contractor) must NOT appear
    assert "T-104" not in proposed_ids

    # All proposed entries must be marked proposed_shift
    for entry in proposal["proposed_reschedule"]:
        assert entry["status"] == "proposed_shift"
        assert entry["days_absorbed"] > 0
        assert entry["contractor"] == "L&T Construction"


# ─── Test (b): Same-contractor-only rule is strictly enforced ─────────────────

def test_reallocation_never_crosses_contractors():
    """
    When the only non-critical task belongs to a DIFFERENT contractor than
    the halted task, propose_reschedule must return feasible=False and an
    empty proposed_reschedule — it must NOT propose cross-contractor moves.

    Scenario:
    - Halt T-101 (DIV-A, L&T) for 5 days.
    - The only non-critical task is T-104 (DIV-B, Afcons) — different contractor.
    - propose_reschedule must return feasible=False.
    """
    # Default seed has T-101(DIV-A, L&T, critical) and T-104(DIV-B, Afcons, non-critical).
    # No additional tasks added — so there are no same-contractor non-critical candidates.
    cpm_result = recalculate_schedule("T-101", 5)

    proposal = propose_reschedule(cpm_result)

    assert proposal["feasible"] is False, (
        "Must not be feasible when the only non-critical task is under a different contractor"
    )
    assert proposal["net_delay_reduction_days"] == 0
    assert proposal["proposed_reschedule"] == []

    # Confirm no Afcons tasks slipped in
    for entry in proposal.get("proposed_reschedule", []):
        assert entry["contractor"] != "Afcons Infrastructure", (
            f"Cross-contractor proposal leaked: {entry}"
        )


# ─── Test (c): Calling the pipeline twice does NOT double-apply ───────────────

def test_double_pipeline_call_does_not_persist():
    """
    Running propose_reschedule twice on the same cpm_result must NOT modify
    the database — it is a pure computation that returns a proposal only.

    Verification:
    1. Record the duration of every task before any calls.
    2. Call propose_reschedule twice.
    3. Assert all task durations are IDENTICAL to step 1.

    The apply-reschedule endpoint (tested separately) is the ONLY mechanism
    that writes to the DB; it must be explicitly invoked.
    """
    def _snapshot_durations() -> dict:
        conn = sqlite3.connect(TEST_DB_PATH)
        rows = conn.execute("SELECT task_id, duration FROM schedule_tasks;").fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

    # Baseline snapshot
    before = _snapshot_durations()

    cpm_result = recalculate_schedule("T-101", 3)

    # Call propose_reschedule twice — simulating the pipeline being called twice
    proposal_1 = propose_reschedule(cpm_result)
    proposal_2 = propose_reschedule(cpm_result)

    # Snapshot after both calls
    after = _snapshot_durations()

    # Durations must be unchanged
    assert before == after, (
        f"propose_reschedule mutated the database!\n"
        f"Before: {before}\nAfter:  {after}"
    )

    # Both calls must return identical, deterministic proposals
    assert proposal_1["net_delay_reduction_days"] == proposal_2["net_delay_reduction_days"]
    assert proposal_1["proposed_reschedule"] == proposal_2["proposed_reschedule"]
    assert proposal_1["feasible"] == proposal_2["feasible"]


# ─── Test (d): apply-reschedule endpoint writes correctly and only once ────────

def test_apply_reschedule_persists_correctly():
    """
    Verify the apply-reschedule route actually persists exactly what was proposed
    and that calling it ONCE produces the correct new duration.

    Uses the FastAPI TestClient to call the endpoint directly.
    """
    from fastapi.testclient import TestClient
    from backend.main import app

    # Patch DB path for the route as well
    import backend.db as _db
    _db.DB_PATH = TEST_DB_PATH

    client = TestClient(app)

    # Add a same-contractor non-critical task for a realistic proposal
    _seed_extra_tasks([{
        "task_id": "T-105",
        "division_id": "DIV-A",
        "task_name": "Site Fencing",
        "duration": 3,
        "is_critical_path": 0,
        "dependencies": "",
    }])

    before_duration = _get_task_duration("T-105")

    # Build the apply payload mimicking what propose_reschedule would return
    payload = {
        "halted_task_id": "T-101",
        "delay_days": 2,
        "proposed_reschedule": [
            {"task_id": "T-105", "days_absorbed": 2}
        ]
    }

    response = client.post("/api/schedule/apply-reschedule", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["status"] == "applied"
    assert body["applied_count"] == 1
    assert body["applied"][0]["task_id"] == "T-105"
    assert body["applied"][0]["days_absorbed"] == 2
    assert body["applied"][0]["new_duration"] == before_duration + 2

    # Confirm DB was actually written
    after_duration = _get_task_duration("T-105")
    assert after_duration == before_duration + 2
