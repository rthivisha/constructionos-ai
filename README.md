# ConstructionOS: Multi-Agent Civil & Operations Intelligence Platform

**ConstructionOS** is an AI-powered operations control platform built with a **Next.js (App Router)** frontend and a high-performance **FastAPI (Python)** backend. It ingests real-time construction site event feeds, evaluates regulatory safety compliance, quantifies financial and critical-path schedule exposure, and dispatches automated field directives through an interactive 4-stage pipeline execution trace.

---

## 🌟 Key Features

* **4-Stage Interactive Pipeline Execution Trace**
  * **Stage 1: Observation & Intake** — Categorizes site incidents, validates task IDs against schedule tables, displays severity score gauges (e.g., `8/10`), and renders raw stream logs.
  * **Stage 2: Safety & Regulatory Compliance** — Evaluates hard-stop triggers (e.g., `HALT TRIGGERED`), matches active rule breaches (e.g., `BOCW_SEC_40`), and details risk and safety rationales.
  * **Stage 3: Cost & Schedule Impact** — Quantifies local task standby costs versus cascaded project-wide delay penalties.
  * **Stage 4: Resolution & Field Directives** — Features executive trade-off reconciliations, automated WhatsApp field alert broadcasts, and formal contractual memo generation (with PDF export support).
* **Unrestricted Free Stage Navigation**
  * Switch between any agent stage at any time without forcing a sequential progression.
  * Trace views remain persistent until a new site event query is executed or explicitly reset.
* **FastAPI Multi-Agent Backend**
  * Asynchronous pipeline execution handling multi-agent orchestration (`observation`, `safety`, `finance`, and `resolution` agents).
  * Auto-generated OpenAPI / Swagger docs for seamless frontend-backend type synchronization.
* **Persistent Bottom AI Command Input (`PromptInput`)**
  * Global input bar available across all pages (`@/components/ui/ai-chat-input.tsx`).
  * Supports model selection (`GPT 5.5`, `Gemini 3.5 Flash`, `Opus 4.8`, `GLM 5.2`), voice input with dynamic visualizer bars, spring transitions, and attachment uploads.
* **Multi-Contractor Architecture**
  * Dynamic metadata interpolation for contractors (e.g., **L&T Construction**, **TATA Projects**).

---

## 📁 Repository Structure

```text
ConstructionOS/
├── backend/                      # FastAPI Python Backend
│   ├── app/
│   │   ├── main.py               # FastAPI entry point & CORS configuration
│   │   ├── api/                  # API endpoints and route definitions
│   │   ├── agents/               # Multi-agent reasoning logic
│   │   ├── models/               # Pydantic schemas & response models
│   │   └── services/             # Schedule/compliance engine & DB queries
│   ├── requirements.txt          # Python dependencies
│   └── uvicorn_config.py
├── frontend/                     # Next.js App Router Frontend
│   ├── app/
│   │   ├── layout.tsx            # Global layout with Sidebar & persistent AI Chat Input
│   │   ├── page.tsx              # Project Metadata Page
│   │   ├── observation/page.tsx  # Stage 1: Observation View
│   │   ├── safety/page.tsx       # Stage 2: Safety & Compliance View
│   │   └── finance/page.tsx      # Stage 3: Cost & Finance View
│   ├── components/
│   │   ├── sidebar.tsx           # Primary Navigation Sidebar
│   │   ├── EventInput.tsx        # Query execution & backend API caller
│   │   ├── ReasoningTrace.tsx    # 4-Stage Stepper Wizard Component
│   │   └── ui/
│   │       └── ai-chat-input.tsx # AI Prompt Input Primitive
│   └── lib/
│       ├── mockData.ts           # Fallback baseline data
│       └── utils.ts              # Tailwind class merge helper (cn)
├── package.json
└── README.md


✅ Quick Start

You need two terminals running simultaneously.

#Terminal 1 — Backend:

cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

#Terminal 2 — Frontend
cd frontend
npm install
npm run dev

Then open:

http://localhost:3000



┌─────────────────────────┐
                               │ Raw Site Event Request  │
                               └────────────┬────────────┘
                                            │ (POST /api/run-pipeline)
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Backend Engine                                                                 │
│                                                                                        │
│   ┌──────────────────────┐      ┌──────────────────────┐      ┌────────────────────┐   │
│   │ Stage 1: Observation │ ───► │ Stage 2: Safety      │ ───► │ Stage 3: Finance   │   │
│   │ Agent (Task Match)   │      │ Agent (BOCW Rules)   │      │ Agent (Cost Delay) │   │
│   └──────────────────────┘      └──────────────────────┘      └─────────┬──────────┘   │
│                                                                         │              │
│                                                                         ▼              │
│                                                         ┌──────────────────────────┐   │
│                                                         │ Stage 4: Resolution      │   │
│                                                         │ Agent (Directives/Memos) │   │
│                                                         └──────────────────────────┘   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼ (JSON Response)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Next.js Frontend (4-Stage Interactive Stepper Trace)                                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
