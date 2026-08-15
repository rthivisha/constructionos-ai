import os
import tempfile
import json
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

# Monkeypatch DB path for observe_agent to use a temporary DB for isolation
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db

from backend.db import init_db
from backend.agents.observe_agent import observe_event
from backend.agents.event_types import EventType


class MockResponse:
    def __init__(self, text):
        self.text = text

def seed_test_tasks():
    # Helper to insert custom tasks T-101, T-102, T-103 into the test DB
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    # Clean tables first
    cursor.execute("DELETE FROM schedule_tasks;")
    cursor.execute("DELETE FROM divisions;")
    cursor.execute("DELETE FROM contractors;")
    cursor.execute("DELETE FROM project_meta;")
    
    # Seed project meta
    cursor.execute(
        "INSERT INTO project_meta (name, location, total_budget, spent_to_date) VALUES (?, ?, ?, ?);",
        ("Metro Line Extension - Phase 2", "Bengaluru, India", 50000000.0, 12000000.0)
    )
    
    # Seed contractors
    contractors = [
        ("L&T Construction", "Structural and civil works", 150000.0, 50000.0, 120),
        ("Siemens Mobility", "Electrical grid and signaling systems", 120000.0, 40000.0, 45),
        ("Tanya Structural", "Piping, water supply, and utility relocation", 60000.0, 20000.0, 30)
    ]
    for c in contractors:
        cursor.execute(
            "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
            c
        )
        
    # Seed divisions
    divisions = [
        ("DIV-CIVIL", "Civil & Structural", "L&T Construction"),
        ("DIV-ELEC", "Electrical & Signaling", "Siemens Mobility"),
        ("DIV-PIPE", "Piping & Plumbing", "Tanya Structural")
    ]
    for d in divisions:
        cursor.execute(
            "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
            d
        )
        
    # Seed tasks (as specified by user instructions)
    tasks = [
        ("T-101", "DIV-CIVIL", "Tower Crane Lift", 10, 1, ""),
        ("T-102", "DIV-CIVIL", "Central Station Foundation Concreting", 15, 1, "T-101"),
        ("T-103", "DIV-PIPE", "South Ramp Drainage Excavation", 8, 0, "T-102")
    ]
    for t in tasks:
        cursor.execute(
            "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
            t
        )
        
    conn.commit()
    conn.close()

@pytest.fixture(autouse=True)
def setup_test_db():
    backend.db.DB_PATH = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
            
    init_db()
    seed_test_tasks()
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


@patch('backend.agents.observe_agent.genai.Client')
def test_observe_event_crane_failure_success(mock_genai_client_class):
    # Prepare mock client response
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # Gemini outputs valid structured JSON matching T-101
    mock_client.models.generate_content.return_value = MockResponse(
        json.dumps({
            "event_type": "work_at_height",
            "matched_task_id": "T-101",
            "severity": 8
        })
    )
    
    event_report = "The tower crane lift system experienced a mechanical failure during structural material hoisting, halting all lifts."
    result = observe_event(event_report)
    
    # Assert correct extraction and matching
    assert result["event_type"] == EventType.WORK_AT_HEIGHT.value
    assert result["task_id"] == "T-101"
    assert result["severity"] == 8
    assert result["task_not_matched"] is False
    assert result["parse_error"] is False

@patch('backend.agents.observe_agent.genai.Client')
def test_observe_event_ambiguous_input(mock_genai_client_class):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # Gemini outputs null/None for matched_task_id due to ambiguity
    mock_client.models.generate_content.return_value = MockResponse(
        json.dumps({
            "event_type": "extreme_weather",
            "matched_task_id": None,
            "severity": 5
        })
    )
    
    event_report = "We need to coordinate the labor crews between the drainage excavation and the foundation concreting, but heavy rain has made the soil unstable."
    result = observe_event(event_report)
    
    # Assert correct fallback due to ambiguity
    assert result["event_type"] == EventType.EXTREME_WEATHER.value
    assert result["task_id"] is None
    assert result["severity"] == 5
    assert result["task_not_matched"] is True
    assert result["parse_error"] is False

@patch('backend.agents.observe_agent.genai.Client')
def test_observe_event_invalid_task_id_from_gemini(mock_genai_client_class):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # Gemini outputs a task_id that does not exist in our database list (e.g. T-999)
    mock_client.models.generate_content.return_value = MockResponse(
        json.dumps({
            "event_type": "excavation",
            "matched_task_id": "T-999",
            "severity": 6
        })
    )
    
    event_report = "Some minor issue near a non-existent task."
    result = observe_event(event_report)
    
    # Assert validation catches invalid ID and sets task_not_matched to True
    assert result["event_type"] == EventType.EXCAVATION.value
    assert result["task_id"] is None
    assert result["task_not_matched"] is True
    assert result["parse_error"] is False

@patch('backend.agents.observe_agent.genai.Client')
def test_observe_event_malformed_or_invalid_gemini_response(mock_genai_client_class):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # 1. Test malformed JSON syntax response triggers fallback mode
    mock_client.models.generate_content.return_value = MockResponse("{malformed-json")
    result_malformed = observe_event("Raw event text report.")
    assert result_malformed["fallback_mode_active"] is True
    assert result_malformed["event_type"] is not None

    # 2. Test schema-invalid JSON response triggers fallback mode
    mock_client.models.generate_content.return_value = MockResponse(
        json.dumps({
            "event_type": "non_existent_event_type",
            "matched_task_id": "T-101",
            "severity": 15
        })
    )
    result_invalid = observe_event("Raw event text report.")
    assert result_invalid["fallback_mode_active"] is True
    assert result_invalid["event_type"] is not None



