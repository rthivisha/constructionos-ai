import json
import time
import re
import os
from fastapi.testclient import TestClient
from backend.main import app
import backend.db

client = TestClient(app)

scenarios = [
    (
        "SCENARIO 1 — Crane Failure (T-101, hard_stop=TRUE, HALT)",
        "Tower Crane Lift Failure at T-101: mechanical failure in the hoist system during structural steel lifting operations, all work halted."
    ),
    (
        "SCENARIO 2 — Heavy Weather (T-103, hard_stop=TRUE, HALT)",
        "Heavy monsoon weather warning issued for the site. Strong winds and heavy rainfall expected over the next 48 hours, affecting all open-site operations."
    ),
    (
        "SCENARIO 3 — Ambiguous Input (excavation, task_not_matched, UNKNOWN)",
        "Excavation crew reported minor soil instability and trench wall movement near an unspecified work area, task ID unverified."
    ),
    (
        "SCENARIO 4 — Material Delivery Delay (T-104, hard_stop=FALSE, CONTINUE)",
        "Minor electrical conduit material delivery delayed by one day due to supplier backlog. Work area is completely safe with no hazards. T-104 is not on critical path."
    ),
    (
        "SCENARIO 5 — Toxic Gas & Ventilation Incident (T-104, hard_stop=TRUE, HALT)",
        "Workers report a strong chemical odor and mild dizziness near the ventilation shaft during electrical conduit installation, work area not yet cleared."
    ),
]

def main():
    backend.db.init_db()
    backend.db.clear_query_cache()

    print("=" * 100)
    print("STEP 3: LIVE GEMINI PIPELINE EXECUTION & FULL UNREDACTED OUTPUT VERIFICATION")
    print("=" * 100)

    results = {}
    mock_detected = False

    for idx, (title, text) in enumerate(scenarios, 1):
        print(f"\n{'='*100}")
        print(f"RUNNING {title}")
        print(f"INPUT TEXT: {text}")
        print(f"{'='*100}")
        
        t0 = time.time()
        res = client.post("/api/events", json={"event_text": text})
        elapsed = time.time() - t0
        
        assert res.status_code == 200, f"HTTP Error {res.status_code}: {res.text}"
        data = res.json()
        results[f"scenario_{idx}"] = data

        raw_json_str = json.dumps(data, indent=2)
        print(f"\n--- FULL JSON OUTPUT (Scenario {idx}) [Latency: {elapsed:.2f}s] ---")
        print(raw_json_str)
        print("--- END OUTPUT ---\n")

        # Check for [MOCK] prefix
        if "[MOCK]" in raw_json_str:
            mock_detected = True
            print(f"WARNING: '[MOCK]' prefix detected in output of Scenario {idx}!")
        else:
            print(f"CONFIRMED: Zero '[MOCK]' prefix in output of Scenario {idx}.")
        
        # Pacing sleep to stay within API rate limits
        time.sleep(3)

    print("\n" + "=" * 100)
    print("TESTING CACHE HIT WITH ALTERED CASING & SPACING (Scenario 1 input)")
    print("=" * 100)
    
    altered_text = "   TOWER  CRANE Lift Failure at   T-101: mechanical failure in the hoist system during structural steel lifting operations, ALL WORK HALTED.   "
    print(f"Altered Input: {repr(altered_text)}")
    
    t0 = time.time()
    res_cache_hit = client.post("/api/events", json={"event_text": altered_text})
    cache_elapsed = time.time() - t0
    
    assert res_cache_hit.status_code == 200
    hit_data = res_cache_hit.json()
    print(f"Latency: {cache_elapsed:.4f}s")
    print(f"Response cached field: {hit_data.get('cached')}")
    print(f"Response fallback_mode_active: {hit_data.get('fallback_mode_active')}")
    assert hit_data.get("cached") is True, "Expected cached == True on normalized match!"
    print("CONFIRMED: Exact-match query cache hit successful!")

    print("\n" + "=" * 100)
    print("TESTING CACHE MISS WITH NOVEL QUERY")
    print("=" * 100)
    
    novel_text = "Excavation trench collapse warning near sector 4 foundation works with 3 workers evacuated."
    print(f"Novel Input: {repr(novel_text)}")
    
    t0 = time.time()
    res_miss = client.post("/api/events", json={"event_text": novel_text})
    miss_elapsed = time.time() - t0
    
    assert res_miss.status_code == 200
    miss_data = res_miss.json()
    print(f"Latency: {miss_elapsed:.2f}s")
    print(f"Response cached field: {miss_data.get('cached')}")
    print(f"Decision: {miss_data.get('tradeoff_reconciliation', {}).get('decision')}")
    assert miss_data.get("cached") is False, "Expected cached == False on novel query!"
    print("CONFIRMED: Cache miss triggered real pipeline execution successfully!")

    print("\n" + "=" * 100)
    print("TESTING CACHE INVALIDATION ON PROJECT DATA UPDATE")
    print("=" * 100)
    
    # Check cache has rows
    conn = backend.db.get_db_connection()
    count_before = conn.cursor().execute("SELECT COUNT(*) as cnt FROM query_cache;").fetchone()
    c_val = count_before["cnt"] if isinstance(count_before, dict) else count_before[0]
    conn.close()
    print(f"Rows in query_cache before invalidation: {c_val}")
    
    meta_update = {
        "name": "Live Verified Bengaluru Metro Extension",
        "location": "Bengaluru, Karnataka",
        "total_budget": 75000000.0,
        "spent_to_date": 18000000.0
    }
    put_res = client.put("/api/project-setup/meta", json=meta_update)
    assert put_res.status_code == 200
    
    conn = backend.db.get_db_connection()
    count_after = conn.cursor().execute("SELECT COUNT(*) as cnt FROM query_cache;").fetchone()
    c_after = count_after["cnt"] if isinstance(count_after, dict) else count_after[0]
    conn.close()
    print(f"Rows in query_cache after PUT /api/project-setup/meta: {c_after}")
    assert c_after == 0, "Expected 0 rows in query_cache after invalidation!"
    print("CONFIRMED: Global cache invalidation successfully cleared the query_cache table.")

    # Save outputs for inspection
    with open("live_verification_outputs.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved full verification outputs to live_verification_outputs.json")

if __name__ == "__main__":
    main()
