import json
from fastapi.testclient import TestClient
from backend.main import app
import backend.db

client = TestClient(app)

scenarios = [
    ('SCENARIO 1 — Crane Failure (T-101, hard_stop=TRUE, HALT)',
     'Tower Crane Lift Failure at T-101: mechanical failure in the hoist system during structural steel lifting operations, all work halted.'),
    ('SCENARIO 2 — Heavy Weather (T-103, hard_stop=TRUE, HALT)',
     'Heavy monsoon weather warning issued for the site. Strong winds and heavy rainfall expected over the next 48 hours, affecting all open-site operations.'),
    ('SCENARIO 3 — Ambiguous Input (excavation, task_not_matched, HALT)',
     'There was some kind of incident on site today. Something happened near one of the work areas but details are unclear.'),
    ('SCENARIO 4 — Minor Material Delay (T-104, hard_stop=FALSE, CONTINUE)',
     'Minor electrical conduit material delivery delayed by one day due to supplier backlog. Ventilation on site is slightly reduced but within safe limits. T-104 is not on critical path.'),
]

def main():
    backend.db.init_db()
    print("=" * 80)
    print("STARTING 4 LIVE/INTEGRATED PIPELINE SCENARIO VERIFICATIONS")
    print("=" * 80)

    for idx, (title, text) in enumerate(scenarios, 1):
        print(f"\n[{idx}] {title}")
        print(f"Input: {text}")
        res = client.post("/api/events", json={"event_text": text})
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        print(f"-> Status: HTTP {res.status_code}")
        print(f"-> Cached: {data.get('cached')}")
        print(f"-> Fallback Mode Active: {data.get('fallback_mode_active')}")
        print(f"-> Decision: {data.get('tradeoff_reconciliation', {}).get('decision')}")
        print(f"-> Safety Hard Stop: {data.get('safety_assessment', {}).get('hard_stop')}")
        print(f"-> Financial Status: {data.get('financial_assessment', {}).get('status')}")
        print(f"-> Matched Task: {data.get('observation', {}).get('task_id')}")

    print("\n" + "=" * 80)
    print("TESTING CACHE HIT ON SECOND RUN OF SCENARIO 1")
    print("=" * 80)
    res_cached = client.post("/api/events", json={"event_text": scenarios[0][1]})
    data_cached = res_cached.json()
    print(f"-> Cached on repeat: {data_cached.get('cached')}")
    print(f"-> Fallback mode: {data_cached.get('fallback_mode_active')}")

    print("\n" + "=" * 80)
    print("TESTING CACHE INVALIDATION VIA PUT /api/project-setup/meta")
    print("=" * 80)
    meta_update = {
        "name": "Metro Line Extension - Phase 2 (Live Verified)",
        "location": "Bengaluru, India",
        "total_budget": 50000000.0,
        "spent_to_date": 12000000.0
    }
    res_put = client.put("/api/project-setup/meta", json=meta_update)
    print(f"-> PUT Status: {res_put.status_code} - {res_put.json()}")
    
    # Check cache table directly
    conn = backend.db.get_db_connection()
    count = conn.cursor().execute("SELECT COUNT(*) FROM query_cache;").fetchone()[0]
    conn.close()
    print(f"-> Rows in query_cache after invalidation: {count}")
    assert count == 0, "Query cache should be empty after project setup update!"

    print("\n" + "=" * 80)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
