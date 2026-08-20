import requests
import json

URL = "http://localhost:8000/api/events"

scenarios = [
    {
        "name": "Scenario 1 (T-101 Halt)",
        "event_text": "Tower crane lift halted at height. We need to inspect the cables."
    },
    {
        "name": "Scenario 2 (T-103 Halt)",
        "event_text": "Heavy weather/rain has made T-103 too wet to proceed."
    },
    {
        "name": "Scenario 3 (Ambiguous)",
        "event_text": "An ambiguous jobsite report mentioning nothing matching the schedule."
    },
    {
        "name": "Scenario 4 (T-104 Continue)",
        "event_text": "Minor material delay on electrical conduits."
    }
]

def main():
    print("Querying scenarios from running API server...\n")
    for s in scenarios:
        print(f"=== {s['name']} ===")
        print(f"Input: '{s['event_text']}'")
        try:
            r = requests.post(URL, json={"event_text": s["event_text"]})
            if r.status_code == 200:
                data = r.json()
                
                # Extract safety assessment
                safety = data.get("safety_assessment", {})
                safety_status = safety.get("safety_status")
                hard_stop = safety.get("hard_stop")
                blocked_act = safety.get("blocked_action")
                print(f"Safety Assessment: Status={safety_status}, HardStop={hard_stop}, BlockedAction={blocked_act}")
                
                # Extract financial assessment
                fin = data.get("financial_assessment", {})
                if fin and fin.get("status") == "success":
                    cb = fin.get("cost_breakdown", {})
                    cpm = fin.get("cpm_result", {})
                    
                    print(f"Cost Breakdown (Halted Task Only):")
                    print(f"  - Scope: {cb.get('scope')}")
                    print(f"  - Halted Task Total: Rs. {cb.get('halted_task_total'):,}")
                    print(f"  - Idle Labour: Rs. {cb.get('idle_labour', {}).get('amount'):,} ({cb.get('idle_labour', {}).get('formula')})")
                    print(f"  - Equip Extension: Rs. {cb.get('equipment_extension', {}).get('amount'):,}")
                    if cb.get('equipment_extension', {}).get('warning'):
                        print(f"    ⚠ Warning: {cb.get('equipment_extension', {}).get('warning')}")
                    print(f"  - Delay Penalty: Rs. {cb.get('delay_penalty', {}).get('amount'):,} ({cb.get('delay_penalty', {}).get('formula')})")
                    
                    print(f"CPM Result (Full Project Impact):")
                    print(f"  - Scope: {cpm.get('scope')}")
                    print(f"  - Total Financial Exposure: Rs. {cpm.get('total_financial_exposure'):,}")
                    if cpm.get('breakdown'):
                        print(f"    - Ops Cost Exposure: Rs. {cpm['breakdown'].get('operating_cost_exposure'):,}")
                        print(f"    - Penalty Exposure: Rs. {cpm['breakdown'].get('penalty_exposure'):,}")
                    
                    print(f"Calculation ID: {fin.get('calculation_id')}")
                    print(f"Cost Coverage: {fin.get('cost_coverage')}")
                elif fin and fin.get("status") == "insufficient_data":
                    print("Financial Assessment: INSUFFICIENT DATA (evaluation skipped)")
                else:
                    print(f"Financial Assessment State: {fin.get('status') or 'Error'}")
            else:
                print(f"Error: HTTP {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Connection error: {e}")
        print()

if __name__ == "__main__":
    main()
