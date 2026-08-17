# ConstructionOS: Multi-Agent Civil & Operations Intelligence Platform

**Live Demo:** 🚀 [https://constructionos-ai-pearl.vercel.app/](https://constructionos-ai-pearl.vercel.app/)

**ConstructionOS** is an AI-powered operations control platform that automatically coordinates construction site **safety compliance**, **financial risk**, and **automated field alerts** in real time using a multi-agent AI pipeline.

The system ingests site disruption events (equipment failure, weather, material shortage) and orchestrates four independent AI agents that assess safety, calculate financial impact, reconcile tradeoffs, and propose optimized reschedules—all within 2–3 seconds.

---

## 🌟 Key Features

* **4-Stage Interactive Pipeline Execution Trace**
  * **Stage 1: Observation & Intake** — Categorizes site incidents, validates task IDs against schedule tables, displays severity score gauges (e.g., `8/10`), and renders raw stream logs.
  * **Stage 2: Safety & Regulatory Compliance** — Evaluates hard-stop triggers (e.g., `HALT TRIGGERED`), matches active rule breaches (e.g., `BOCW_SEC_40`), and details risk and safety rationales.
  * **Stage 3: Cost & Schedule Impact** — Quantifies local task standby costs versus cascaded project-wide delay penalties using Critical Path Method (CPM) calculations.
  * **Stage 4: Resolution & Field Directives** — Reconciles safety and cost tradeoffs into a single executive decision with explicit justification.

* **Unrestricted Free Stage Navigation**
  * Switch between any agent stage at any time without forcing sequential progression.
  * Trace views remain persistent until a new site event query is executed or explicitly reset.

* **FastAPI Multi-Agent Backend**
  * Asynchronous pipeline execution handling multi-agent orchestration (Observe, Safety, Finance, Trade-off agents).
  * Parallel safety and finance assessments for minimal latency.
  * Auto-generated OpenAPI/Swagger docs at `/docs`.
  * Graceful fallbacks (mock mode, seed JSON) when APIs are unavailable.

* **Robust Data Management**
  * PostgreSQL or SQLite support (automatic fallback).
  * Exact-match SHA-256 caching (never fuzzy compliance decisions).
  * Immutable audit trail of all decisions.

* **Production-Ready Safety Constraints**
  * Hard-stop mechanism: safety violations cannot be overridden by cost savings (enforced in Python, not LLM).
  * Regulatory knowledge base (BOCW Act, Factory Act, Indian compliance rules).
  * 5-tier safety filter with mandatory field controls and compliant alternatives.

---

## 📁 Repository Structure

```text
constructionos-ai/
├── backend/                      # FastAPI Python Backend (69% Python)
│   ├── agents/
│   │   ├── observe_agent.py       # Event extraction & task matching
│   │   ├── safety_agent.py        # Regulatory compliance evaluation
│   │   ├── finance_agent.py       # CPM delay & cost calculations
│   │   └── tradeoff_agent.py      # Reconciliation & decision logic
│   ├── routes/
│   │   ├── events.py              # Site event ingestion pipeline
│   │   ├── project_setup.py       # Project metadata initialization
│   │   └── schedule.py            # Task & schedule retrieval
│   ├── tools/
│   │   └── cpm_engine.py          # Critical Path Method engine
│   ├── db.py                      # PostgreSQL/SQLite abstraction
│   ├── config.py                  # Model & retry configuration
│   ├── models.py                  # Pydantic schemas
│   ├── main.py                    # FastAPI entrypoint
│   ├── requirements.txt           # Python dependencies
│   └── mock_data/
│       └── seed_project_state.json # Demo data (L&T, TATA Projects, etc.)
│
├── frontend/                      # Next.js App Router Frontend (30% TypeScript)
│   ├── app/
│   │   ├── layout.tsx             # Global layout with Sidebar & AI input
│   │   ├── page.tsx               # Project metadata dashboard
│   │   ├── observation/page.tsx   # Stage 1 view
│   │   ├── safety/page.tsx        # Stage 2 view
│   │   ├── finance/page.tsx       # Stage 3 view
│   │   └── resolution/page.tsx    # Stage 4 view
│   ├── components/
│   │   ├── ReasoningTrace.tsx     # 4-stage stepper wizard
│   │   ├── EventInput.tsx         # Query executor
│   │   ├── Sidebar.tsx            # Navigation
│   │   └── ui/
│   │       └── ai-chat-input.tsx  # AI prompt input primitive
│   └── lib/
│       ├── mockData.ts            # Fallback data
│       └── utils.ts               # Tailwind helpers
│
├── tests/                         # Pytest suite
│   ├── test_observe_agent.py      # Event extraction tests
│   ├── test_safety_agent.py       # Compliance evaluation tests
│   ├── test_finance_agent.py      # CPM calculation tests
│   └── conftest.py                # Shared fixtures
│
├── docs/
│   ├── API.md                     # OpenAPI documentation
│   └── ARCHITECTURE.md            # System design
│
├── .env.example                   # Environment variable template
├── docker-compose.yml             # Local PostgreSQL setup
├── Dockerfile                     # Production container
├── requirements.txt               # Root Python deps
└── README.md
```

---

## 🎯 How It Works

### The Problem
Construction site managers discover schedule-impacting disruptions **2–3 weeks after they happen** because safety, scheduling, and cost are assessed independently and manually—not in real time.

### The Solution
When a site event occurs:

1. **Observe Agent** (Stage 1)
   - Extracts event type, severity (1–10), and matches task ID
   - Validates against live project schedule
   - Falls back to mock if LLM unavailable

2. **Safety Agent** (Stage 2) — *Runs in parallel*
   - Matches event type against regulatory KB (BOCW, Factory Act)
   - Triggers hard-stop if violation detected
   - Hard-stop **cannot be overridden** by cost
   - Generates mandatory field controls and compliant alternatives

3. **Finance Agent** (Stage 3) — *Runs in parallel*
   - Estimates delay duration (extracted or severity-mapped)
   - Runs CPM engine: recalculates schedule, identifies shifted/penalized tasks
   - Quantifies marginal exposure (operating cost + penalties)
   - Result: ₹30k–₹225k exposure, depending on contractor and delay

4. **Trade-off Agent** (Stage 4)
   - Reconciles safety and cost into a single decision
   - If hard_stop=True, decision is always "halt" (safety wins)
   - Otherwise, weighs risk vs. cost
   - Includes: decision, reasoning, rejected alternative, why it was rejected

5. **Propose Reschedule** (Optional)
   - Reallocates float/slack from non-critical tasks
   - Only within same contractor (no cross-project reallocation)
   - Returns deadline status: fully_recovered, partially_recovered, or not_feasible

**Result:** Full 4-stage trace returned to frontend in <3 seconds. User audits reasoning and can override with context.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, uvicorn, Python 3.9+ |
| **AI/ML** | Google Gemini 2.0 Flash (native SDK, no LangChain) |
| **Database** | PostgreSQL (prod) / SQLite (dev) |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript |
| **Styling** | TailwindCSS 4, Lucide icons, Motion animations |
| **Validation** | Pydantic v2 (structured schemas) |
| **Testing** | pytest, pytest-asyncio |
| **Caching** | SHA-256 exact-match (never fuzzy) |
| **Deployment** | Vercel (frontend), Render (backend), Supabase PostgreSQL |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+, Node.js 18+
- PostgreSQL (optional; SQLite works for dev)
- Google Gemini API key (free tier available)

### Backend Setup

```bash
# 1. Clone & navigate
git clone https://github.com/rthivisha/constructionos-ai
cd constructionos-ai/backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env: set GEMINI_API_KEY, DATABASE_URL (optional), USE_MOCK_LLM=true for testing

# 5. Run migrations (SQLite auto-initializes)
python -m backend.db

# 6. Start server
uvicorn backend.main:app --reload --port 8000
```

Visit Swagger docs: **http://localhost:8000/docs**

### Frontend Setup

```bash
cd ../frontend

npm install
npm run dev
```

Visit app: **http://localhost:3000**

### Test the API

```bash
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{"event_text": "Tower crane mechanical failure, harness check pending"}'
```

Expected response: Full 4-stage trace with hard_stop=True.

---

## 🧪 Running Tests

ConstructionOS includes a comprehensive pytest suite to validate agent logic without API quota.

### Install Test Dependencies

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov
```

### Run All Tests

```bash
pytest -v
```

### Run Specific Test Suite

```bash
pytest tests/test_safety_agent.py -v
pytest tests/test_finance_agent.py -v
pytest tests/test_observe_agent.py -v
```

### Run with Coverage Report

```bash
pytest --cov=backend --cov-report=html
open htmlcov/index.html  # View coverage in browser
```

### Example Test Structure

```bash
tests/
├── conftest.py                  # Shared fixtures
├── test_observe_agent.py        # Scenario 1-5 validation
├── test_safety_agent.py         # Hard-stop logic
└── test_finance_agent.py        # CPM calculations
```

### Sample Test (Scenario 1: Crane Failure)

```python
# tests/test_observe_agent.py
def test_crane_failure_scenario():
    """Verify crane failure event is correctly categorized as work_at_height."""
    event_text = "Tower crane mechanical failure. No harness certification on site."
    result = observe_event(event_text)
    
    assert result["event_type"] == "work_at_height"
    assert result["task_id"] == "T-101"  # Tower Crane Lift task
    assert result["severity"] == 8
    assert result["task_not_matched"] == False
```

### Running in Mock Mode (No API Quota)

```bash
export USE_MOCK_LLM=true
pytest -v
```

All tests pass deterministically using hardcoded demo scenarios. Perfect for CI/CD.

---

---

## 🔒 Safety-Critical Features

### Hard-Stop Mechanism
```python
# Hard-stops are NEVER mocked or negotiable
if hard_stop:
    return {"decision": "halt", "reasoning": "Safety non-negotiable under BOCW Act"}
```

### Exact-Match Caching
```python
# Only identical normalized queries are served from cache
clean_text = re.sub(r'\s+', ' ', text.strip().lower())
normalized_hash = hashlib.sha256(clean_text.encode()).hexdigest()
```

### Audit Trail
Every decision is logged to `site_events` table with:
- Raw event text
- Full pipeline response
- Timestamp
- Fallback status

---

## 📈 Performance Benchmarks

| Scenario | Latency | Cache Hit |
|----------|---------|-----------|
| Live Gemini (first call) | 2–3s | No |
| Cached response (exact match) | <100ms | Yes |
| Mock mode (USE_MOCK_LLM=true) | ~50ms | N/A |
| API quota exhausted | <100ms | Falls back to mock |

---

## 📚 Documentation

- **[API.md](./docs/API.md)** — OpenAPI/Swagger reference
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** — System design & data flow
- **[DATABASE.md](./docs/DATABASE.md)** — Schema & migrations

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Write tests (see `tests/` for examples)
4. Commit with clear messages
5. Open a PR with description

---

## 📝 Real-World Use Cases

**Scenario 1: Crane Failure**
- Event: "Tower crane mechanical failure"
- Observation: task_id=T-101, severity=8
- Safety: hard_stop=True (BOCW_SEC_40 triggered)
- Finance: 3-day delay, ₹225,000 exposure
- Decision: HALT (safety overrides cost)

**Scenario 2: Material Shortage**
- Event: "Electrical conduit delivery delayed"
- Observation: task_id=T-104, severity=2
- Safety: hard_stop=False (no rule match)
- Finance: 1-day delay, ₹50,000 exposure
- Decision: Continue (non-critical task, low cost)

**Scenario 3: Toxic Gas Incident**
- Event: "Chemical odor near ventilation shaft, dizziness"
- Observation: task_id=T-104, severity=8
- Safety: hard_stop=True (FA_SEC_87 triggered)
- Finance: 4-day delay, ₹240,000 exposure
- Decision: HALT (mandatory hard-stop)

---

## 🎓 What You'll Learn

- **Multi-Agent AI Architecture:** How to design agents that reason independently yet reconcile constraints
- **LLM Integration:** Structured outputs, retry logic, fallbacks without framework abstractions
- **Production Safety:** Hard constraints, audit trails, deterministic caching for compliance
- **Full-Stack Systems:** FastAPI + Next.js, PostgreSQL/SQLite abstraction, real-time updates
- **Critical Path Method:** Schedule optimization and financial exposure calculation
- **Testing AI Systems:** Deterministic mocking, scenario-based evaluation, coverage reporting

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

---

## 👨‍💻 About the Builder

**Thivisha** — Full-stack AI engineer building intelligent systems that matter. 

Specialized in:
- **Multi-agent AI architectures** (reasoning pipelines, constraint satisfaction)
- **Production LLM integration** (Gemini, structured schemas, graceful failures)
- **Full-stack engineering** (FastAPI + Next.js, PostgreSQL, Docker)
- **Safety-critical systems** (hard constraints, audit trails, deterministic behavior)

ConstructionOS demonstrates end-to-end ownership: from agent design → backend architecture → frontend UX → production deployment.

**Other Projects:**
- **RiverSense AI:** Environmental DNA analysis for Indian river health monitoring (DNABERT, Kraken2, Biothon 2026 Top 50)
- **VivaAI:** AI-powered interview platform (FastAPI, WebRTC, SarvamAI)

---

## 📞 Get in Touch

- **GitHub:** [@rthivisha](https://github.com/rthivisha)
- **Email:** [your.email@example.com](mailto:your.rthivisha67@example.com)
- **LinkedIn:** [linkedin.com/in/thivisha](https://linkedin.com/in/thivisha)

---

## 🙏 Acknowledgments

- **BOCW Act & Indian Labor Standards** — Regulatory framework for construction safety
- **Google Gemini API** — Structured output & agentic capabilities
- **FastAPI & Next.js communities** — Production-grade tooling

---

**Star this repo if you find it useful! 🌟**
