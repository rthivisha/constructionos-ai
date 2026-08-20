import pytest
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.agents.tradeoff_agent import assess_tradeoff
from backend.main import app
import backend.db

class MockGeminiResponse:
    def __init__(self, text: str):
        self.text = text

def test_tradeoff_safety_unavailable():
    """Safety unavailable must safely fail-halt."""
    res = assess_tradeoff(safety_output=None, finance_output=None)
    assert res["decision"] == "halt"
    assert res["rejected_alternative"] == "continue"
    assert "safety compliance cannot be verified" in res["rejected_because"].lower()

def test_tradeoff_blocked_status():
    """BLOCKED status must halt unconditionally."""
    safety_output = {
        "hard_stop": True,
        "safety_status": "BLOCKED",
        "triggered_rules": [{"code": "BOCW_SEC_40", "description": "Mandatory harness"}],
        "mandatory_field_controls": ["Safety harness inspection", "Scaffold tag check"],
        "status": "success",
        "parse_error": False
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=False)
    assert res["decision"] == "halt"
    assert res["rejected_alternative"] == "continue"

    # Even if controls_verified was mistakenly sent True, BLOCKED must still halt
    res_forced = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=True)
    assert res_forced["decision"] == "halt"

def test_tradeoff_escalate_status():
    """ESCALATE status must halt unconditionally."""
    safety_output = {
        "hard_stop": True,
        "safety_status": "ESCALATE",
        "triggered_rules": [{"code": "CRANE_FATAL_RISK", "description": "Fatal structural failure"}],
        "mandatory_field_controls": ["Third-party structural audit"],
        "status": "success",
        "parse_error": False
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=False)
    assert res["decision"] == "halt"

def test_tradeoff_conditional_unverified():
    """CONDITIONAL status with controls_verified=False must return pending_verification with control list."""
    safety_output = {
        "hard_stop": True,
        "safety_status": "CONDITIONAL",
        "triggered_rules": [{"code": "BOCW_RULE_41", "description": "Conditional restart after equipment repair"}],
        "mandatory_field_controls": [
            "Mechanical load test certification",
            "Operator re-briefing signoff",
            "Exclusion zone verification"
        ],
        "status": "success",
        "parse_error": False
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=False)
    assert res["decision"] == "pending_verification"
    assert res["rejected_alternative"] == "continue"
    assert "Mechanical load test certification" in res["reasoning"]
    assert "Operator re-briefing signoff" in res["reasoning"]
    assert "Exclusion zone verification" in res["reasoning"]
    assert "required safety controls not yet verified by site manager" in res["rejected_because"]

def test_tradeoff_conditional_verified_finance_unavailable():
    """CONDITIONAL status with controls_verified=True and finance unavailable must continue under verified conditional clearance."""
    safety_output = {
        "hard_stop": True,
        "safety_status": "CONDITIONAL",
        "triggered_rules": [{"code": "BOCW_RULE_41", "description": "Conditional restart after equipment repair"}],
        "mandatory_field_controls": ["Mechanical load test certification"],
        "status": "success",
        "parse_error": False
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=True)
    assert res["decision"] == "continue"
    assert res["rejected_alternative"] == "halt"
    assert "proceeding under verified conditional clearance" in res["reasoning"].lower()

def test_tradeoff_conditional_verified_finance_valid():
    """CONDITIONAL status with controls_verified=True and valid finance must weigh and continue under verified clearance."""
    safety_output = {
        "hard_stop": True,
        "safety_status": "CONDITIONAL",
        "triggered_rules": [{"code": "BOCW_RULE_41", "description": "Conditional restart"}],
        "mandatory_field_controls": ["Mechanical load test certification"],
        "status": "success",
        "parse_error": False
    }
    finance_output = {
        "status": "success",
        "task_id": "T-101",
        "delay_days_used": 2,
        "parse_error": False,
        "cpm_result": {
            "total_financial_exposure": 350000.0,
            "critical_path": True
        }
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=finance_output, controls_verified=True)
    assert res["decision"] == "continue"
    assert res["rejected_alternative"] == "halt"
    assert "proceeding under verified conditional clearance" in res["reasoning"].lower()

def test_tradeoff_safe_finance_unavailable():
    """SAFE status with finance unavailable continues on safety alone."""
    safety_output = {
        "hard_stop": False,
        "safety_status": "SAFE",
        "triggered_rules": [],
        "mandatory_field_controls": [],
        "status": "success",
        "parse_error": False
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=None, controls_verified=False)
    assert res["decision"] == "continue"
    assert res["rejected_alternative"] == "halt"

def test_tradeoff_safe_finance_valid():
    """SAFE status with valid finance weighs cost/schedule and continues."""
    safety_output = {
        "hard_stop": False,
        "safety_status": "SAFE",
        "triggered_rules": [],
        "mandatory_field_controls": [],
        "status": "success",
        "parse_error": False
    }
    finance_output = {
        "status": "success",
        "task_id": "T-103",
        "delay_days_used": 1,
        "parse_error": False,
        "cpm_result": {
            "total_financial_exposure": 150000.0,
            "critical_path": False
        }
    }
    res = assess_tradeoff(safety_output=safety_output, finance_output=finance_output, controls_verified=False)
    assert res["decision"] == "continue"
    assert res["rejected_alternative"] == "halt"


def test_api_events_conditional_flow():
    """
    Test full API /api/events pipeline:
    1. First call with controls_verified=False triggers pending_verification.
    2. Second call with controls_verified=True triggers continue with conditional clearance.
    3. Verify cache keys are separated and do not collide.
    """
    client = TestClient(app)
    
    # Mock observe, safety, and finance to simulate a CONDITIONAL restart scenario
    mock_observe = {
        "event_type": "crane_restart_inspection",
        "task_id": "T-101",
        "severity": 6,
        "task_not_matched": False,
        "parse_error": False,
        "fallback_mode_active": False
    }
    mock_safety = {
        "hard_stop": True,
        "safety_status": "CONDITIONAL",
        "blocked_action": "Crane Hoisting Operations",
        "mandatory_field_controls": [
            "Load test sensor calibration check",
            "Operator visual clearance inspection"
        ],
        "triggered_rules": [{"code": "BOCW_RULE_41", "description": "Crane restart verification required"}],
        "plain_reason": "Conditional clearance requires physical inspection of load test sensors.",
        "fallback_mode_active": False,
        "parse_error": False,
        "status": "success"
    }
    mock_finance = {
        "status": "success",
        "task_id": "T-101",
        "delay_days_used": 1,
        "fallback_mode_active": False,
        "parse_error": False,
        "cpm_result": {
            "assigned_crew": "L&T Construction",
            "daily_operating_cost": 150000.0,
            "contractor_penalty_rate": 50000.0,
            "critical_path": True,
            "total_financial_exposure": 200000.0,
            "fallback_mode_active": False
        },
        "summary": "Project delay cost exposure: 200,000 INR."
    }

    with patch("backend.routes.events.observe_event", return_value=mock_observe), \
         patch("backend.routes.events.assess_safety", return_value=mock_safety), \
         patch("backend.routes.events.assess_finance", return_value=mock_finance):

        # Step 1: Human has not yet verified controls (controls_verified = False)
        resp1 = client.post("/api/events", json={
            "event_text": "Crane hoist maintenance completed on T-101 awaiting resumption.",
            "controls_verified": False
        })
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["controls_verified"] is False
        assert data1["safety_assessment"]["safety_status"] == "CONDITIONAL"
        assert data1["tradeoff_reconciliation"]["decision"] == "pending_verification"
        assert "Load test sensor calibration check" in data1["tradeoff_reconciliation"]["reasoning"]

        # Step 2: Site Manager clicks 'Confirm Controls Verified' (controls_verified = True)
        resp2 = client.post("/api/events", json={
            "event_text": "Crane hoist maintenance completed on T-101 awaiting resumption.",
            "controls_verified": True
        })
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["controls_verified"] is True
        assert data2["safety_assessment"]["safety_status"] == "CONDITIONAL"
        assert data2["tradeoff_reconciliation"]["decision"] == "continue"
        assert "proceeding under verified conditional clearance" in data2["tradeoff_reconciliation"]["reasoning"].lower()
