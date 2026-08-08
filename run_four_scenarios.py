import requests, json

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

for title, text in scenarios:
    r = requests.post('http://localhost:8000/api/events', json={'event_text': text})
    print(f'\n{"="*70}')
    print(f'{title}')
    print(f'{"="*70}')
    print(json.dumps(r.json(), indent=2))
