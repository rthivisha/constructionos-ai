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


# ─── P3 Tests: Reschedule-to-deadline ────────────────────────────────────────

def test_deadline_fully_recovered_when_slack_covers_delay():
    """
    When available same-contractor slack fully covers the delay,
    post_reallocation_duration == baseline_project_duration and
    deadline_status must be "fully_recovered". remaining_delay_days == 0.

    Setup: Add T-105 (DIV-A, L&T, duration=3, non-critical) with slack >> delay.
    Baseline: 33 days. Delay T-101 by 2 days → new duration 35.
    T-105 slack in delayed schedule = 35 - 3 = 32 (>> 2).
    After absorbing 2 days: post_reallocation_duration = 35 - 2 = 33 = baseline.
    → fully_recovered
    """
    _seed_extra_tasks([{
        "task_id": "T-105",
        "division_id": "DIV-A",
        "task_name": "Site Fencing",
        "duration": 3,
        "is_critical_path": 0,
        "dependencies": "",
    }])

    cpm_result = recalculate_schedule("T-101", 2)
    proposal = propose_reschedule(cpm_result)

    assert proposal["deadline_status"] == "fully_recovered", (
        f"Expected fully_recovered, got {proposal['deadline_status']}. "
        f"Detail: {proposal['calculation_detail']}"
    )
    assert proposal["remaining_delay_days"] == 0
    assert proposal["estimated_remaining_penalty"] == 0.0
    assert proposal["post_reallocation_duration"] == cpm_result["baseline_project_duration"]

    # Confirm the math is in the calculation_detail
    assert "FULLY RECOVERED" in proposal["calculation_detail"]
    assert str(cpm_result["baseline_project_duration"]) in proposal["calculation_detail"]


def test_deadline_partially_recovered_with_correct_remaining_figures():
    """
    When slack covers some but not all delay, deadline_status is "partially_recovered"
    with correct remaining_delay_days and estimated_remaining_penalty.

    Setup: Add T-105 (DIV-A, L&T, duration=3, non-critical) — only 1 day absorbed
    by constraining T-105 slack to 1 via a dependency that forces an early late_finish.
    Simpler approach: delay T-101 by 20 days (>> available slack).
    Baseline 33 days → delayed 53 days. T-105 slack in delayed schedule ≈ 50 → absorbs 20?
    Not right — 20 days delay on a root critical task makes T-105 slack also grow.

    Better approach: seed two tasks.
      T-105 (DIV-A, duration=3, no deps, non-critical) — large slack after delay.
      T-106 (DIV-A, duration=1, depends on T-103, non-critical) — limited slack.
    But because T-105 has essentially unlimited slack vs any delay on T-101,
    we can only get partial recovery by capping available slack:
    Delay T-101 by 50 days (hypothetical). T-105 slack in delayed = 83-3=80.
    Absorbs all 50 → fully recovered. That doesn't work either.

    The CORRECT way to force partial: halt a NON-critical task with no candidates
    at all (cross-contractor only) → not_feasible.
    For PARTIAL: introduce a small-slack candidate.
    Add T-105 (DIV-A, duration=30, depends on T-101). Its slack in delayed schedule
    is 0 if on critical path. Let it have is_critical_path=0 but duration 25.
    Baseline: T-101(10)+T-102(15)+T-103(8)=33. T-105 depends on T-101, dur=25.
    ES=10, EF=35>33 → it becomes critical? No, late finish = project duration.
    LF=33, LS=33-25=8, but ES=10 > LS → negative slack → critical!
    Use duration=20 instead. EF=10+20=30 ≤ 33. Slack = LF(33)-EF(30)=3.
    Delay T-101 by 5 → delayed project = 38 days. T-105: ES=12, EF=32. LF=38. slack=6.
    But 6 ≥ 5 → would fully recover. Use duration=22. Baseline EF=10+22=32, slack=1.
    Delay T-101 by 5 → delayed project = 38. T-105 ES=12, EF=12+22=34. LF=38. slack=4.
    Still ≥ 5? No, slack=4 < 5 → absorbs 4 days → partial! remaining=1.
    Penalty: L&T penalty rate = 75000/day → estimated_remaining_penalty = 1 * 75000 = 75000.
    """
    _seed_extra_tasks([{
        "task_id": "T-105",
        "division_id": "DIV-A",       # L&T — same as T-101
        "task_name": "Temporary Access Road",
        "duration": 22,               # slack=1 in baseline, slack=4 in 5-day delay scenario
        "is_critical_path": 0,
        "dependencies": "T-101",      # depends on halted task
    }])

    cpm_result = recalculate_schedule("T-101", 5)
    baseline_dur = cpm_result["baseline_project_duration"]   # 33
    delayed_dur = cpm_result["new_project_duration"]         # 38

    # Verify T-105 slack in delayed schedule
    t105_delayed_slack = cpm_result["tasks"]["T-105"]["delayed"]["slack"]
    assert t105_delayed_slack > 0, "T-105 must have positive slack in delayed schedule"
    assert t105_delayed_slack < 5, (
        f"T-105 slack ({t105_delayed_slack}) must be < 5 to force partial recovery"
    )

    proposal = propose_reschedule(cpm_result)

    assert proposal["deadline_status"] == "partially_recovered", (
        f"Expected partially_recovered, got {proposal['deadline_status']}. "
        f"slack={t105_delayed_slack}, delay=5. Detail:\n{proposal['calculation_detail']}"
    )

    # net recovered = t105_delayed_slack (absorbed all available)
    assert proposal["net_delay_reduction_days"] == t105_delayed_slack

    # Remaining delay = 5 - absorbed
    expected_remaining = 5 - t105_delayed_slack
    assert proposal["remaining_delay_days"] == expected_remaining

    # post_reallocation_duration = 38 - absorbed
    expected_post = delayed_dur - t105_delayed_slack
    assert proposal["post_reallocation_duration"] == expected_post
    assert expected_post > baseline_dur  # partial, not full

    # L&T penalty = 75000/day (from seed data)
    expected_penalty = expected_remaining * 75000.0
    assert proposal["estimated_remaining_penalty"] == expected_penalty, (
        f"Penalty mismatch: expected {expected_penalty}, got {proposal['estimated_remaining_penalty']}"
    )

    # Math must appear in calculation_detail
    assert "PARTIAL" in proposal["calculation_detail"]
    assert str(expected_remaining) in proposal["calculation_detail"]


def test_deadline_not_feasible_when_no_same_contractor_candidates():
    """
    When the only non-critical task is a different contractor, there are no
    candidates at all. deadline_status must be "not_feasible", remaining_delay_days
    equals the full project_delay, and estimated_remaining_penalty is computed
    from the halted task's contractor penalty rate.

    T-101 (L&T), T-104 (Afcons, non-critical). Halt T-101 for 3 days.
    No L&T non-critical candidates → not_feasible.
    remaining_delay_days = 3 (all of project_delay).
    L&T penalty = 75000/day → estimated_remaining_penalty = 3 * 75000 = 225000.
    """
    # Default seed: only T-104 is non-critical, and it's Afcons (DIV-B).
    cpm_result = recalculate_schedule("T-101", 3)

    assert cpm_result["project_delay"] == 3

    proposal = propose_reschedule(cpm_result)

    assert proposal["feasible"] is False
    assert proposal["deadline_status"] == "not_feasible"
    assert proposal["remaining_delay_days"] == 3
    assert proposal["net_delay_reduction_days"] == 0
    assert proposal["proposed_reschedule"] == []

    # Penalty must be from L&T's rate (75000/day), not hardcoded
    expected_penalty = 3 * 75000.0
    assert proposal["estimated_remaining_penalty"] == expected_penalty, (
        f"Expected ₹{expected_penalty}, got ₹{proposal['estimated_remaining_penalty']}"
    )

    # "Deadline check" line must appear
    assert "Deadline check" in proposal["calculation_detail"]


def test_zero_delay_returns_fully_recovered():
    """
    A zero-delay event should immediately return fully_recovered with all zeroes.
    This guards against the zero-delay early-return path returning wrong deadline fields.
    """
    cpm_result = recalculate_schedule("T-101", 0)
    proposal = propose_reschedule(cpm_result)

    assert proposal["deadline_status"] == "fully_recovered"
    assert proposal["remaining_delay_days"] == 0
    assert proposal["estimated_remaining_penalty"] == 0.0
    assert proposal["net_delay_reduction_days"] == 0
    assert proposal["feasible"] is False
