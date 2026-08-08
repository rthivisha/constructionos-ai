import requests, json

scenarios = [
    ('SCENARIO 1 — Crane Failure (T-101)',
     'Tower Crane Lift Failure at T-101: mechanical failure in the hoist system during structural steel lifting operations, all work halted.'),
    ('SCENARIO 2 — Heavy Weather (T-103)',
     'Heavy monsoon weather warning issued for the site. Strong winds and heavy rainfall expected over the next 48 hours, affecting all open-site operations.'),
]

for title, text in scenarios:
    r = requests.post('http://localhost:8000/api/events', json={'event_text': text})
    data = r.json()
    print(f'\n{"="*70}\n{title}\n{"="*70}')
    # Print only key fields for brevity
    obs = data['observation']
    saf = data['safety_assessment']
    fin = data['financial_assessment']
    trd = data['tradeoff_reconciliation']
    print(f"OBSERVATION:  event_type={obs['event_type']} | task_id={obs['task_id']} | severity={obs['severity']} | parse_error={obs['parse_error']}")
    print(f"SAFETY:       hard_stop={saf['hard_stop']} | rules={[r['code'] for r in saf['triggered_rules']]}")
    print(f"SAFETY BRIEF: {saf['brief']}")
    print(f"FINANCE:      status={fin['status']} | task={fin['task_id']} | delay={fin['delay_days_used']}d | exposure=₹{fin['cpm_result']['total_financial_exposure']:,}")
    print(f"FINANCE SUM:  {fin['summary']}")
    print(f"TRADEOFF:     decision={trd['decision']}")
    print(f"REASONING:    {trd['reasoning']}")
