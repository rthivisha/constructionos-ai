# ConstructionOS AI — Project Overview

## 1. Product Identity
ConstructionOS AI is a manually-orchestrated multi-agent system that observes
site disruption events, independently assesses safety and financial impact,
and produces a reconciled decision with an explicit trade-off justification.

Problem in one sentence: site managers currently discover schedule-impacting
disruptions 2-3 weeks after they happen, because safety, scheduling, and cost
are assessed independently and manually, not in real time.

## 2. Core Workflow (4 stages)

| Stage | Mechanism | Outcome |
|---|---|---|
| Detect | Raw site event submitted (form input, simulating IoT/report feed) | Structured event: task, event_type, severity (1-10) |
| Analyze | Safety Agent and Finance Agent independently assess the same event, in parallel, with no visibility into each other's output | Two independent, potentially conflicting assessments |
| Negotiate | Trade-off Agent reconciles both assessments | A decision plus explicit statement of what was rejected and why |
| Execute | Mock Gantt/task state updates, stakeholder notifications drafted, audit log entry written | Updated project state + exportable decision record |

## 3. Agent Architecture

| Agent | Responsible for | NOT responsible for |
|---|---|---|
| Observe Agent | Parsing raw event into structured fields | Judging severity impact or cost — extraction only |
| Safety Agent | Independent safety/compliance assessment against [Indian regulatory framework — CONFIRM: BOCW Act / Factories Act / state labour dept norms] | Cost estimation, scheduling, final decision |
| Finance Agent | Independent cost-per-day-delayed and critical-path impact, using get_task_impact against mock task data | Safety judgment, final decision |
| Trade-off Agent | Reconciling Safety and Finance into one decision with stated rejection | Re-deriving safety or cost figures itself — must use upstream outputs only |

**Governing constraint — HARD_STOP:** if Safety Agent flags a hard stop, the
Trade-off Agent cannot override it for cost reasons under any circumstance.
This is non-negotiable system behavior, not a tunable preference — future
code changes must not quietly weaken this.


## 5. Tech Stack (source of truth)

 Next.js/Tailwind.css/FastAPI (backend)/json 

- AI layer: native `google-genai` SDK, `gemini-2.0-flash`. No ADK. No LangChain.
  These are explicit constraints, not preferences.
- State: in-memory JSON / SQLite — explicitly a demo-day tradeoff, not a
  production decision.

## 6. Non-Goals
- Not a full construction ERP.
- Not handling multi-project portfolios.
- Not integrating any real government compliance API — simulated compliance
  checks against [confirmed Indian framework] only.
- Not ingesting live IoT/SMS feeds in the demo — form-based input only,
  explicitly stated as such to judges.

## 7. Glossary
- **HARD_STOP** — Safety Agent's non-overridable halt signal.
- **Trade-off Agent** — reconciles Safety and Finance outputs into one decision.
- **Critical path** — task sequence where a delay directly delays the whole project.
- **Schedule Task Schema**: The live project database seeds tasks using the Metro Rail Line 4 schema:
  * **T-101**: Tower Crane Lift (Division: `DIV-A`, Contractor: `L&T Construction`)
  * **T-102**: Central Station Foundation Concreting (Division: `DIV-A`, Contractor: `L&T Construction`, depends on `T-101`)
  * **T-103**: South Ramp Drainage Excavation (Division: `DIV-C`, Contractor: `TATA Projects`, depends on `T-102`)
  * **T-104**: Electrical Conduit Laying (Division: `DIV-B`, Contractor: `Afcons Infrastructure`, depends on `T-101`, non-critical task added for schedule delay verification)
- **Contractor SLAs**:
  * **L&T Construction**: Daily Operating Cost ₹85,000, Daily Delay Penalty ₹75,000
  * **Afcons Infrastructure**: Daily Operating Cost ₹120,000, Daily Delay Penalty ₹60,000
  * **TATA Projects**: Daily Operating Cost ₹30,000, Daily Delay Penalty ₹35,000


# #workflow: 
**ConstructionOS AI** is an autonomous site operations engine that coordinates specialized AI agents to detect, analyze, and resolve job-site disruptions in real time.
### Key Capabilities
 1. Detect
   Real-Time Intelligence
   Monitors site activity continuously to spot delays, material shortages, equipment issues, and hazards instantly.
 2. Analyze
   Multi-Agent Collaboration
   Specialized agents (Safety, Inventory, Schedule) evaluate the disruption's impact on cost, time, and risk.
 3. Negotiate
   Trade-Off Resolution
   Weighs options automatically to select the optimal path balancing speed, budget, and compliance.
 4. Execute
   Automated Workflow
   Triggers actions immediately—adjusting crew schedules, reordering supplies, and updating logs without manual delays.
### Primary Impact
 * **Zero-Downtime Operations:** Keeps labor and machinery active by resolving bottlenecks before they cause idle time.
 * **Proactive Risk Mitigation:** Identifies safety hazards early to prevent accidents and compliance violations.
 * **Cost & Timeline Control:** Reallocates resources automatically to protect project margins and delivery dates.