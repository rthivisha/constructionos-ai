import os
import tempfile
import json
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# Isolated temporary DB setup
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db
import backend.tools.cpm_engine

# Override the DB paths dynamically in the fixture
from backend.db import init_db
from backend.agents.safety_agent import assess_safety
from backend.agents.finance_agent import assess_finance
from backend.agents.event_types import EventType

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
    
    # Seed regulatory KB matching work_at_height and toxic_gas
    cursor.execute("INSERT INTO regulatory_kb (code, description, trigger_condition) VALUES (?, ?, ?);",
                   ("BOCW_SEC_40", "Safety harness and scaffolding mandatory.", EventType.WORK_AT_HEIGHT.value))
    cursor.execute("INSERT INTO regulatory_kb (code, description, trigger_condition) VALUES (?, ?, ?);",
                   ("FA_SEC_87", "Factories Act Section 87: Exposure to toxic gases or chemical handling requires PPE and continuous ventilation.", EventType.TOXIC_GAS.value))
    
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

# --- SAFETY AGENT TESTS ---

@patch('backend.agents.safety_agent.genai.Client')
def test_safety_agent_hard_stop(mock_genai):
    mock_client = MagicMock()
    mock_genai.return_value = mock_client
    # Now expects a JSON response with three structured fields
    mock_client.models.generate_content.return_value = MockResponse(
        json.dumps({
            "plain_reason": "Scaffolding rules require height safety — operations halted.",
            "override_risk": "Continuing under BOCW_SEC_40 risks fatal falls and prosecution.",
            "exception_mitigation": "NOT COMPLIANCE — emergency exception steps only: (1) Safety officer sign-off. (2) Ensure harnesses present."
        })
    )
    
    observe_output = {
        "event_type": EventType.WORK_AT_HEIGHT.value,
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_safety(observe_output, "Worker fell from scaffold.")
    
    assert res["hard_stop"] is True
    assert len(res["triggered_rules"]) == 1
    assert res["triggered_rules"][0]["code"] == "BOCW_SEC_40"
    # Check the new structured fields instead of brief
    assert "safety" in res["plain_reason"].lower() or "height" in res["plain_reason"].lower() or "halted" in res["plain_reason"].lower()
    assert "BOCW_SEC_40" in res["override_risk"]
    assert res["parse_error"] is False

@patch('backend.agents.safety_agent.genai.Client')
def test_safety_agent_no_hard_stop(mock_genai):
    mock_client = MagicMock()
    mock_genai.return_value = mock_client
    mock_client.models.generate_content.return_value = MockResponse("Excavation at shallow depth holds no stop.")
    
    observe_output = {
        "event_type": EventType.EXCAVATION.value,
        "task_id": "T-101",
        "severity": 3,
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_safety(observe_output, "Excavation shallow depth.")
    assert res["hard_stop"] is False
    assert len(res["triggered_rules"]) == 0
    assert res["parse_error"] is False

def test_safety_agent_parse_error_halt():
    observe_output = {
        "event_type": None,
        "task_id": None,
        "severity": None,
        "task_not_matched": True,
        "parse_error": True
    }
    res = assess_safety(observe_output)
    assert res["parse_error"] is True
    assert res["hard_stop"] is False
    # plain_reason replaces brief for parse_error path
    assert "observe agent failed" in res["plain_reason"].lower()

# --- FINANCE AGENT TESTS ---

@patch('backend.agents.finance_agent.genai.Client')
def test_finance_agent_happy_path_extraction(mock_genai):
    mock_client = MagicMock()
    mock_genai.return_value = mock_client
    
    # 1. Mock delay extraction to return 5 days
    # 2. Mock brief explanation response
    mock_client.models.generate_content.side_effect = [
        MockResponse(json.dumps({"delay_days": 5})),  # Delay extraction
        MockResponse("The financial exposure of 5 days delay is estimated.")  # Financial brief
    ]
    
    observe_output = {
        "event_type": EventType.WORK_AT_HEIGHT.value,
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_finance(observe_output, "Crane lift is delayed by 5 days.")
    
    assert res["status"] == "success"
    assert res["task_id"] == "T-101"
    assert res["delay_days_used"] == 5
    assert res["delay_source"] == "extracted_from_text"
    assert res["cpm_result"]["assigned_crew"] == "L&T Construction"
    assert res["cpm_result"]["project_delay"] == 5
    assert res["cpm_result"]["total_financial_exposure"] > 0
    assert "exposure" in res["summary"].lower() or "financial" in res["summary"].lower()
    assert res["cpm_result"]["parse_error"] is False
    # New P1 keys must be present
    assert set(res.keys()) == {"status", "task_id", "delay_days_used", "delay_source", "cpm_result", "summary", "cost_breakdown", "cost_coverage", "calculation_id", "fallback_mode_active"}

@patch('backend.agents.finance_agent.genai.Client')
def test_finance_agent_happy_path_fallback(mock_genai):
    mock_client = MagicMock()
    mock_genai.return_value = mock_client
    
    # Mock delay extraction returns null/None, so fallback applies
    mock_client.models.generate_content.side_effect = [
        MockResponse(json.dumps({"delay_days": None})),
        MockResponse("The financial exposure using severity fallback is calculated.")
    ]
    
    observe_output = {
        "event_type": EventType.WORK_AT_HEIGHT.value,
        "task_id": "T-101",
        "severity": 8,  # severity 8 maps to default delay of 3 days
        "task_not_matched": False,
        "parse_error": False
    }
    
    res = assess_finance(observe_output, "Some event description with no days mentioned.")
    
    assert res["status"] == "success"
    assert res["delay_days_used"] == 3
    assert res["delay_source"] == "severity_fallback"
    assert res["cpm_result"]["project_delay"] == 3
    assert res["cpm_result"]["parse_error"] is False
    # New P1 keys must be present
    assert set(res.keys()) == {"status", "task_id", "delay_days_used", "delay_source", "cpm_result", "summary", "cost_breakdown", "cost_coverage", "calculation_id", "fallback_mode_active"}

def test_finance_agent_insufficient_data():
    observe_output = {
        "event_type": EventType.WORK_AT_HEIGHT.value,
        "task_id": None,
        "severity": 5,
        "task_not_matched": True,
        "parse_error": False
    }
    
    res = assess_finance(observe_output)
    
    assert res["status"] == "insufficient_data"
    assert res["task_id"] is None
    assert res["cpm_result"]["total_financial_exposure"] is None
    assert "skipped" in res["summary"].lower() or "no task" in res["summary"].lower()
    # New P1 keys must be present (all None for insufficient_data)
    assert set(res.keys()) == {"status", "task_id", "delay_days_used", "delay_source", "cpm_result", "summary", "cost_breakdown", "cost_coverage", "calculation_id", "fallback_mode_active"}
    assert res["cost_breakdown"] is None

def test_finance_agent_parse_error_halt():
    observe_output = {
        "event_type": None,
        "task_id": None,
        "severity": None,
        "task_not_matched": True,
        "parse_error": True
    }
    res = assess_finance(observe_output)
    assert res["status"] == "error"
    assert res["cpm_result"]["parse_error"] is True
    assert "observe agent failed" in res["summary"].lower()
    # New P1 keys must be present (all None for parse error path)
    assert set(res.keys()) == {"status", "task_id", "delay_days_used", "delay_source", "cpm_result", "summary", "cost_breakdown", "cost_coverage", "calculation_id", "fallback_mode_active"}
    assert res["cost_breakdown"] is None


# --- INDEPENDENCE VERIFICATION ---

@patch('backend.agents.safety_agent.genai.Client')
@patch('backend.agents.safety_agent.get_project_state')
def test_agents_independence(mock_get_state, mock_genai):
    # This test programmatically checks that:
    # 1. Safety Agent does NOT call any CPM/finance recalculation functions
    # 2. Finance Agent does NOT evaluate regulatory rules or make hard stops
    
    # Mock project state for Safety Agent
    mock_get_state.return_value = ({
        "regulatory_kb": [{"code": "BOCW_SEC_40", "description": "Desc", "trigger_condition": "work_at_height"}]
    }, False)
    
    mock_client = MagicMock()
    mock_genai.return_value = mock_client
    mock_client.models.generate_content.return_value = MockResponse("Brief")
    
    # Mock CPM recalculate_schedule to spy on it
    with patch('backend.agents.finance_agent.recalculate_schedule') as mock_recalc, \
         patch('backend.agents.finance_agent.get_task_impact') as mock_impact:
         
        # Run Safety Agent
        observe_output = {
            "event_type": "work_at_height",
            "task_id": "T-101",
            "severity": 5,
            "task_not_matched": False,
            "parse_error": False
        }
        assess_safety(observe_output, "Raw text")
        
        # Verify finance tools were NOT called
        mock_recalc.assert_not_called()
        mock_impact.assert_not_called()

    # Mock Safety Agent assess_safety to verify it is NOT called during Finance Agent run
    with patch('backend.agents.finance_agent.get_task_impact') as mock_impact_run, \
         patch('backend.agents.finance_agent.recalculate_schedule') as mock_recalc_run, \
         patch('backend.agents.finance_agent.genai.Client') as mock_genai_finance:
         
        # Mock returns
        mock_impact_run.return_value = {
            "assigned_crew": "L&T Construction",
            "daily_operating_cost": 150000.0,
            "contractor_penalty_rate": 50000.0,
            "critical_path": True
        }
        mock_recalc_run.return_value = {
            "baseline_project_duration": 75,
            "new_project_duration": 80,
            "project_delay": 5,
            "total_financial_exposure": 1000000.0,
            "breakdown": {"operating_cost_exposure": 750000.0, "penalty_exposure": 250000.0},
            "tasks": {},
            "fallback_mode_active": False
        }
        
        mock_client_fin = MagicMock()
        mock_genai_finance.return_value = mock_client_fin
        mock_client_fin.models.generate_content.side_effect = [
            MockResponse(json.dumps({"delay_days": 5})),
            MockResponse("Finance brief text")
        ]
        
        # Run Finance Agent
        res_finance = assess_finance(observe_output, "Crane delay raw text")
        
        # Verify that the Finance Agent result does not contain Safety keys like hard_stop or triggered_rules
        assert "hard_stop" not in res_finance
        assert "triggered_rules" not in res_finance

def test_safety_agent_advisory_isolation():
    # Verify that even when advisory considerations are generated, they do not influence hard_stop.
    # Case 1: Active Safety event (e.g. work_at_height) that matches regulatory rules in DB -> hard_stop should be True
    observe_output_match = {
        "event_type": "work_at_height",
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    # Using offline fallback (mocking API key empty)
    with patch('backend.agents.safety_agent.get_api_key', return_value=""):
        res_match = assess_safety(observe_output_match, "Worker at height report.")
        assert res_match["hard_stop"] is True
        assert "harness" in res_match["advisory_considerations"].lower()
        assert "derived deterministically" in res_match["advisory_disclaimer"]

    # Case 2: Active Safety event (e.g. excavation) with NO rules matching in DB (as we seeded none for excavation) -> hard_stop should be False
    observe_output_no_match = {
        "event_type": "excavation",
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    with patch('backend.agents.safety_agent.get_api_key', return_value=""):
        res_no_match = assess_safety(observe_output_no_match, "Excavation digging report.")
        assert res_no_match["hard_stop"] is False
        assert "shoring" in res_no_match["advisory_considerations"].lower()
        assert "derived deterministically" in res_no_match["advisory_disclaimer"]


def test_safety_agent_5tier_filter_output():
    observe_output_blocked = {
        "event_type": "work_at_height",
        "task_id": "T-101",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    with patch('backend.agents.safety_agent.get_api_key', return_value=""):
        res = assess_safety(observe_output_blocked, "Crane lift work at height report.")
        assert res["safety_status"] == "BLOCKED"
        assert res["blocked_action"] == "continue_high_elevation_rigging_and_lifting"
        assert "BOCW_SEC_40" in res["regulatory_rule_violated"]
        assert len(res["mandatory_field_controls"]) >= 3
        assert res["counterfactual_analysis_target"]["simulation_type"] == "COUNTERFACTUAL_EXPOSURE"
        assert res["counterfactual_analysis_target"]["action_to_simulate"] == res["blocked_action"]
        assert len(res["suggested_compliant_alternatives"]) >= 2


def test_safety_agent_toxic_gas_hard_stop():
    observe_output_toxic = {
        "event_type": EventType.TOXIC_GAS.value,
        "task_id": "T-104",
        "severity": 8,
        "task_not_matched": False,
        "parse_error": False
    }
    with patch('backend.agents.safety_agent.get_api_key', return_value=""):
        res = assess_safety(observe_output_toxic, "Strong chemical odor and dizziness near ventilation shaft.")
        assert res["hard_stop"] is True
        assert len(res["triggered_rules"]) == 1
        assert res["triggered_rules"][0]["code"] == "FA_SEC_87"
        assert res["safety_status"] == "BLOCKED"
        assert res["blocked_action"] == "continue_confined_space_work"
        assert "FA_SEC_87" in res["regulatory_rule_violated"]
        assert "ventilation" in res["advisory_considerations"].lower() or "ppe" in res["advisory_considerations"].lower()


def test_safety_agent_material_shortage_no_hard_stop():
    observe_output_material = {
        "event_type": EventType.MATERIAL_SHORTAGE.value,
        "task_id": "T-104",
        "severity": 2,
        "task_not_matched": False,
        "parse_error": False
    }
    with patch('backend.agents.safety_agent.get_api_key', return_value=""):
        res = assess_safety(observe_output_material, "Minor electrical conduit supplier delivery delay.")
        assert res["hard_stop"] is False
        assert len(res["triggered_rules"]) == 0
        assert res["safety_status"] == "CLEAR"
        assert res["blocked_action"] == "none"
        assert "procurement" in res["advisory_considerations"].lower() or "material" in res["advisory_considerations"].lower()

