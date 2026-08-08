import os
import tempfile
import pytest

# Monkeypatch the database path to use a temporary DB for tests, preventing pollution
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB_PATH = test_db_file.name
test_db_file.close()

import backend.db
backend.db.DB_PATH = TEST_DB_PATH

from fastapi.testclient import TestClient
from backend.main import app
from backend.db import init_db, get_db_connection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
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

def test_get_project_setup_happy_path():
    response = client.get("/api/project-setup")
    assert response.status_code == 200
    data = response.json()
    assert "project_meta" in data
    assert data["project_meta"]["name"] == "Metro Line Extension - Phase 2"
    assert len(data["contractors"]) > 0

def test_update_project_meta_happy_path():
    new_meta = {
        "name": "Updated Station Construction",
        "location": "Mumbai, India",
        "total_budget": 65000000.0,
        "spent_to_date": 14000000.0
    }
    response = client.put("/api/project-setup/meta", json=new_meta)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify it updated in DB
    get_res = client.get("/api/project-setup")
    assert get_res.json()["project_meta"]["name"] == "Updated Station Construction"

def test_negative_cost_rejected():
    # Test that contractor with negative daily cost is rejected (Pydantic validation check)
    bad_contractors = [
        {
            "name": "Bad Contractor",
            "scope": "Scaffolding",
            "daily_operating_cost": -100.0,  # Negative cost
            "daily_delay_penalty": 2000.0,
            "active_workers": 10
        }
    ]
    response = client.put("/api/project-setup/contractors", json=bad_contractors)
    # Pydantic validation error returns 422 Unprocessable Entity
    assert response.status_code == 422

def test_missing_contractor_reference_blocked():
    # Division references "NonExistent Contractor", should return 400
    bad_divisions = [
        {
            "id": "DIV-TEST",
            "name": "Testing Division",
            "lead_contractor": "NonExistent Contractor"
        }
    ]
    response = client.put("/api/project-setup/divisions", json=bad_divisions)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]

def test_missing_task_dependency_blocked():
    # Task references a dependency "T-NONEXIST" that is not in the list of tasks, should return 400
    bad_tasks = [
        {
            "task_id": "T100",
            "division_id": "DIV-CIVIL",
            "task_name": "Test Task 1",
            "duration": 5,
            "is_critical_path": 1,
            "dependencies": "T-NONEXIST"
        }
    ]
    response = client.put("/api/project-setup/tasks", json=bad_tasks)
    assert response.status_code == 400
    assert "references non-existent dependency" in response.json()["detail"]

def test_dependency_cycle_blocked():
    # Circular dependency: T100 -> T200 -> T100, should return 400
    cyclic_tasks = [
        {
            "task_id": "T100",
            "division_id": "DIV-CIVIL",
            "task_name": "Test Task 1",
            "duration": 5,
            "is_critical_path": 1,
            "dependencies": "T200"
        },
        {
            "task_id": "T200",
            "division_id": "DIV-CIVIL",
            "task_name": "Test Task 2",
            "duration": 10,
            "is_critical_path": 1,
            "dependencies": "T100"
        }
    ]
    response = client.put("/api/project-setup/tasks", json=cyclic_tasks)
    assert response.status_code == 400
    assert "cycle detected" in response.json()["detail"].lower()

def test_symmetric_delete_blocks():
    # Verify that trying to delete a contractor currently referenced by an active division fails
    # Let's get initial setup list of contractors and try to save list excluding "L&T Construction"
    setup_data = client.get("/api/project-setup").json()
    initial_contractors = setup_data["contractors"]
    
    # Exclude "L&T Construction" (which is used by DIV-CIVIL)
    filtered_contractors = [c for c in initial_contractors if c["name"] != "L&T Construction"]
    
    response = client.put("/api/project-setup/contractors", json=filtered_contractors)
    assert response.status_code == 400
    assert "Cannot delete contractor" in response.json()["detail"]

    # Verify trying to delete a division currently referenced by active tasks fails
    initial_divisions = setup_data["divisions"]
    # Exclude "DIV-CIVIL" (referenced by task T1 and T2)
    filtered_divisions = [d for d in initial_divisions if d["id"] != "DIV-CIVIL"]
    
    div_response = client.put("/api/project-setup/divisions", json=filtered_divisions)
    assert div_response.status_code == 400
    assert "Cannot delete division" in div_response.json()["detail"]
