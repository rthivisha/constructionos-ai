import pytest
import sqlite3
import json
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
import backend.db
from backend.db import get_cached_response, save_cached_response, clear_query_cache
from backend.config import call_gemini_with_retry, is_rate_limit_error

client = TestClient(app)

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_caching.db")

@pytest.fixture(autouse=True)
def setup_teardown_db(monkeypatch):
    monkeypatch.setattr(backend.db, "DB_PATH", TEST_DB_PATH)
    monkeypatch.setenv("DATABASE_URL", "")
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    backend.db.init_db()
    clear_query_cache()
    yield
    clear_query_cache()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

@patch('google.genai.Client')
def test_exact_match_caching(mock_client_class, monkeypatch):
    """Verify that identical queries hit the exact-match cache."""
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")
    
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    class MockGenAIResp:
        def __init__(self, text):
            self.text = text
            
    def side_effect(model, contents, config=None, **kwargs):
        prompt = str(contents)
        if "matched_task_id" in prompt or "extract structured fields" in prompt:
            return MockGenAIResp(json.dumps({
                "event_type": "work_at_height",
                "matched_task_id": "T-101",
                "severity": 8
            }))
        elif "FIXED FACTS" in prompt or "plain_reason" in prompt:
            return MockGenAIResp(json.dumps({
                "plain_reason": "Safety crane failure stop.",
                "override_risk": "High risk under BOCW_SEC_40.",
                "exception_mitigation": "NOT COMPLIANCE — emergency steps only."
            }))
        elif "construction-safety" in prompt or "advisory" in prompt:
            return MockGenAIResp("- Check crane hoist cables.\n- Verify rigger qualifications.")
        elif "extract the number of delay days" in prompt or "delay_days" in prompt:
            return MockGenAIResp(json.dumps({"delay_days": 3}))
        elif "financial impact" in prompt or "financial summary" in prompt:
            return MockGenAIResp("Delay of 3 days incurs standard standby charges.")
        elif "Trade-off" in prompt or "decision" in prompt or "reconciliation" in prompt:
            return MockGenAIResp(json.dumps({
                "decision": "halt",
                "reasoning": "Mandatory safety stop takes precedence.",
                "rejected_alternative": "continue",
                "rejected_because": "risk too high"
            }))
        return MockGenAIResp("{}")
        
    mock_client.models.generate_content.side_effect = side_effect

    event_text = "Tower Crane Lift Failure at T-101: mechanical failure in the hoist system."
    
    # 1st request -> cached: False
    res1 = client.post("/api/events", json={"event_text": event_text})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1.get("cached") is False
    assert data1.get("fallback_mode_active") is False
    
    # Check cache table directly
    conn = backend.db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT normalized_input_hash, full_pipeline_response FROM query_cache;")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    # 2nd request with exact same text (normalized) -> cached: True
    res2 = client.post("/api/events", json={"event_text": f"  {event_text.upper()}  "})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("cached") is True

def test_fallback_mode_never_cached(monkeypatch):
    """Verify that a degraded mock or fallback response is never written to query_cache."""
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    event_text = "Severe storm on jobsite with heavy rainfall."
    
    res = client.post("/api/events", json={"event_text": event_text})
    assert res.status_code == 200
    data = res.json()
    assert data.get("fallback_mode_active") is True
    
    # Verify query_cache table remains empty
    conn = backend.db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM query_cache;")
    row = cursor.fetchone()
    count = row["count"] if isinstance(row, dict) else row[0]
    conn.close()
    assert count == 0

def test_cache_invalidation_on_project_setup_update():
    """Verify modifying project setup data flushes query_cache."""
    # Seed a cache entry
    save_cached_response(
        normalized_hash="dummy_hash_12345",
        original_text="test query",
        response={"observation": {"task_id": "T-101"}, "status": "success"}
    )
    
    cached = get_cached_response("dummy_hash_12345")
    assert cached is not None
    
    # Perform a project-setup update (e.g. PUT /api/project-setup/meta)
    meta_payload = {
        "name": "Updated Test Project",
        "location": "Site A",
        "total_budget": 50000000.0,
        "spent_to_date": 12000000.0
    }
    res = client.put("/api/project-setup/meta", json=meta_payload)
    assert res.status_code == 200
    
    # Verify cache is cleared
    cached_after = get_cached_response("dummy_hash_12345")
    assert cached_after is None

def test_retry_exponential_backoff():
    """Verify call_gemini_with_retry retries on 429 and succeeds or raises."""
    mock_client = MagicMock()
    
    # Simulate two 429 errors then a success
    rate_limit_err = Exception("429 Resource exhausted: quota exceeded")
    success_response = MagicMock(text='{"result": "ok"}')
    mock_client.models.generate_content.side_effect = [rate_limit_err, rate_limit_err, success_response]
    
    result = call_gemini_with_retry(
        client=mock_client,
        model="test-model",
        contents="test-prompt",
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=1.5
    )
    assert result == success_response
    assert mock_client.models.generate_content.call_count == 3

