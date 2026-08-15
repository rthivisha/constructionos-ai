import pytest
import sqlite3
import json
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.main import app
import backend.db
from backend.db import get_cached_response, save_cached_response, clear_query_cache
from backend.config import call_gemini_with_retry, is_rate_limit_error

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_db():
    # Ensure fresh DB state
    backend.db.init_db()
    clear_query_cache()
    yield
    clear_query_cache()

def test_exact_match_caching():
    """Verify that identical queries hit the exact-match cache."""
    event_text = "Tower Crane Lift Failure at T-101: mechanical failure in the hoist system."
    
    # 1st request -> cached: False
    res1 = client.post("/api/events", json={"event_text": event_text})
    assert res1.status_code == 200
    data1 = res1.json()
    assert "cached" in data1
    
    # Check cache table directly
    conn = sqlite3.connect(backend.db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT normalized_input_hash, full_pipeline_response FROM query_cache;")
    rows = cursor.fetchall()
    conn.close()

    # If live Gemini succeeded, data1['cached'] is False and it was saved in query_cache
    if not data1.get("fallback_mode_active"):
        assert len(rows) == 1
        # 2nd request with exact same text (normalized) -> cached: True
        res2 = client.post("/api/events", json={"event_text": f"  {event_text.upper()}  "})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2.get("cached") is True
    else:
        # If in fallback mode (e.g. mock or no API key), it MUST NOT be written to query_cache
        assert len(rows) == 0

def test_fallback_mode_never_cached(monkeypatch):
    """Verify that a degraded mock or fallback response is never written to query_cache."""
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    event_text = "Severe storm on jobsite with heavy rainfall."
    
    res = client.post("/api/events", json={"event_text": event_text})
    assert res.status_code == 200
    data = res.json()
    assert data.get("fallback_mode_active") is True
    
    # Verify query_cache table remains empty
    conn = sqlite3.connect(backend.db.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM query_cache;")
    count = cursor.fetchone()[0]
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

