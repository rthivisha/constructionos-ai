import os
import tempfile
import sqlite3
import pytest
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

import backend.db
import backend.tools.cpm_engine

# Create temporary DB file for isolation
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

# Import FastAPI application
from backend.main import app
from backend.agents.event_types import EventType

client = TestClient(app)

class MockResponse:
    def __init__(self, text):
        self.text = text


def seed_test_data():
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule_tasks;")
    cursor.execute("DELETE FROM divisions;")
    cursor.execute("DELETE FROM contractors;")
    cursor.execute("DELETE FROM project_meta;")
    cursor.execute("DELETE FROM regulatory_kb;")
    
    # Meta
    cursor.execute("INSERT INTO project_meta (name, location, total_budget, spent_to_date) VALUES (?, ?, ?, ?);",
                   ("Metro Line Extension - Phase 2", "Bengaluru, India", 50000000.0, 12000000.0))
    # Contractors
    cursor.execute("INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
                   ("L&T Construction", "Structural work", 150000.0, 50000.0, 120))
    # Divisions
    cursor.execute("INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
                   ("DIV-CIVIL", "Civil & Structural", "L&T Construction"))
    # Tasks
    cursor.execute("INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
                   ("T-101", "DIV-CIVIL", "Tower Crane Lift", 10, 1, ""))
    cursor.execute("INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
                   ("T-102", "DIV-CIVIL", "Central Station Foundation Concreting", 15, 1, "T-101"))
    
    # Seed regulatory rule matching WORK_AT_HEIGHT
    cursor.execute("INSERT INTO regulatory_kb (code, description, trigger_condition) VALUES (?, ?, ?);",
                   ("BOCW_SEC_40", "Safety harness and scaffolding mandatory.", EventType.WORK_AT_HEIGHT.value))
    
    conn.commit()
    conn.close()

@pytest.fixture(autouse=True)
def setup_test_db():
    # Force mock database path across modules
    backend.db.DB_PATH = TEST_DB_PATH
    backend.tools.cpm_engine.DB_PATH = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
            
    backend.db.init_db()
    seed_test_data()
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

# --- Pipeline Tests ---

@patch('backend.routes.events.observe_event')
@patch('backend.routes.events.assess_safety')
@patch('backend.routes.events.assess_finance')
@patch('backend.routes.events.assess_tradeoff')
def test_pipeline_happy_path(mock_tradeoff, mock_finance, mock_safety, mock_observe):
    # Mock return values for happy path
    mock_observe.return_value = {
        "event_type": "excavation",
        "task_id": "T-102",
        "severity": 4,
        "task_not_matched": False,
        "parse_error": False
    }
    mock_safety.return_value = {
        "hard_stop": False,
        "triggered_rules": [],
        "brief": "Safety check complete, no regulatory violation.",
        "fallback_mode_active": False,
        "parse_error": False
    }
    mock_finance.return_value = {
        "status": "success",
        "task_id": "T-102",
        "delay_days_used": 2,
        "delay_source": "severity_fallback",
        "cpm_result": {
            "assigned_crew": "L&T Construction",
            "project_delay": 2,
            "total_financial_exposure": 400000.0,
            "parse_error": False
        },
        "summary": "Financial delay estimation complete."
    }
    mock_tradeoff.return_value = {
        "decision": "continue",
        "reasoning": "Work continues because cost is low and no safety stops are triggered.",
        "rejected_alternative": "halt",
        "rejected_because": "halting is not economically justified."
    }

    response = client.post("/api/events", json={"event_text": "Minor soil unstable at drainage excavation."})
    assert response.status_code == 200
    
    data = response.json()
    assert data["observation"]["task_id"] == "T-102"
    assert data["safety_assessment"]["hard_stop"] is False
    assert data["financial_assessment"]["status"] == "success"
    assert data["tradeoff_reconciliation"]["decision"] == "continue"

@patch('backend.routes.events.observe_event')
@patch('backend.routes.events.assess_safety')
@patch('backend.routes.events.assess_finance')
def test_pipeline_finance_crashes(mock_finance, mock_safety, mock_observe):
    # Mock observe and safety to succeed normally
    mock_observe.return_value = {
        "event_type": "excavation",
        "task_id": "T-102",
        "severity": 4,
        "task_not_matched": False,
        "parse_error": False
    }
    mock_safety.return_value = {
        "hard_stop": False,
        "triggered_rules": [],
        "brief": "Safety check complete, no stop.",
        "fallback_mode_active": False,
        "parse_error": False
    }
    
    # Mock Finance Agent to raise an exception during concurrent gather execution
    mock_finance.side_effect = ValueError("Simulated Finance crash!")

    response = client.post("/api/events", json={"event_text": "Finance crashes but safety passes."})
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify Finance assessment is marked unavailable instead of crash
    assert data["financial_assessment"]["status"] == "unavailable"
    
    # Verify Trade-off agent makes decision based on Safety alone
    tradeoff = data["tradeoff_reconciliation"]
    assert tradeoff["decision"] == "continue"
    assert "exposure could not be assessed" in tradeoff["reasoning"].lower()
    assert tradeoff["rejected_alternative"] == "halt"

@patch('backend.routes.events.observe_event')
@patch('backend.routes.events.assess_safety')
@patch('backend.routes.events.assess_finance')
def test_pipeline_safety_crashes(mock_finance, mock_safety, mock_observe):
    # Mock observe and finance to succeed normally
    mock_observe.return_value = {
        "event_type": "excavation",
        "task_id": "T-102",
        "severity": 4,
        "task_not_matched": False,
        "parse_error": False
    }
    mock_finance.return_value = {
        "status": "success",
        "task_id": "T-102",
        "delay_days_used": 2,
        "delay_source": "severity_fallback",
        "cpm_result": {
            "assigned_crew": "L&T Construction",
            "project_delay": 2,
            "total_financial_exposure": 400000.0,
            "parse_error": False
        },
        "summary": "Financial estimation succeeds."
    }
    
    # Mock Safety Agent to raise an exception during concurrent gather execution
    mock_safety.side_effect = ValueError("Simulated Safety crash!")

    response = client.post("/api/events", json={"event_text": "Safety crashes but finance passes."})
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify Safety assessment is marked unavailable
    assert data["safety_assessment"]["status"] == "unavailable"
    
    # Verify tradeoff defaults to fail-safe halt
    tradeoff = data["tradeoff_reconciliation"]
    assert tradeoff["decision"] == "halt"
    assert "unavailable" in tradeoff["reasoning"].lower()
    assert tradeoff["rejected_alternative"] == "continue"

@patch('backend.routes.events.observe_event')
@patch('backend.routes.events.assess_safety')
@patch('backend.routes.events.assess_finance')
def test_pipeline_both_crash_simultaneously(mock_finance, mock_safety, mock_observe):
    # Mock observe to succeed
    mock_observe.return_value = {
        "event_type": "excavation",
        "task_id": "T-102",
        "severity": 4,
        "task_not_matched": False,
        "parse_error": False
    }
    
    # Both Safety and Finance raise exceptions concurrently
    mock_safety.side_effect = ValueError("Simulated Safety crash!")
    mock_finance.side_effect = ValueError("Simulated Finance crash!")

    response = client.post("/api/events", json={"event_text": "Double crash."})
    assert response.status_code == 200
    
    data = response.json()
    
    assert data["safety_assessment"]["status"] == "unavailable"
    assert data["financial_assessment"]["status"] == "unavailable"
    
    # Trade-off agent must still make a safe halt decision
    tradeoff = data["tradeoff_reconciliation"]
    assert tradeoff["decision"] == "halt"
    assert "unavailable" in tradeoff["reasoning"].lower()

@patch('google.genai.Client')
def test_pipeline_e2e_integration_no_mocked_dicts(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Configure mock responses for all Gemini calls in order:
    # 1. Observe Agent
    # 2. Safety Agent Compliance Brief
    # 3. Safety Agent Advisory Considerations
    # 4. Finance Agent Delay Extraction
    # 5. Finance Agent Financial Brief
    # 6. Trade-off Agent Reconciliation Decision
    mock_client.models.generate_content.side_effect = [
        MockResponse(json.dumps({
            "event_type": "excavation",
            "matched_task_id": "T-102",
            "severity": 4
        })),
        MockResponse("Compliance looks fine, caution advised."),
        MockResponse("- Verify shoring stability.\n- Monitor trench atmospheric hazards."),
        MockResponse(json.dumps({
            "delay_days": 3
        })),
        MockResponse("Project schedule will shift by 3 days with marginal cost."),
        MockResponse(json.dumps({
            "decision": "continue",
            "reasoning": "No safety stop and financial exposure is minor.",
            "rejected_alternative": "halt",
            "rejected_because": "cost of halting is higher than continuing."
        }))
    ]

    
    response = client.post("/api/events", json={"event_text": "Minor soil unstable at drainage excavation."})
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify the real, unmocked output schemas were successfully processed and matched
    assert data["observation"]["event_type"] == "excavation"
    assert data["observation"]["task_id"] == "T-102"
    assert data["observation"]["severity"] == 4
    
    assert data["safety_assessment"]["hard_stop"] is False
    assert data["safety_assessment"]["parse_error"] is False
    
    assert data["financial_assessment"]["status"] == "success"
    assert data["financial_assessment"]["delay_days_used"] == 3
    assert data["financial_assessment"]["delay_source"] == "extracted_from_text"
    assert data["financial_assessment"]["cpm_result"]["project_delay"] == 3
    
    assert data["tradeoff_reconciliation"]["decision"] == "continue"
    assert data["tradeoff_reconciliation"]["rejected_alternative"] == "halt"

