import logging
import json
import re
import os
import sqlite3
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.agents.observe_agent import get_api_key
from backend.tools.cpm_engine import get_project_state, get_task_impact, recalculate_schedule
import backend.db
from backend.config import MODEL_NAME, use_mock_llm, ASSUMED_DAILY_WAGE_PER_WORKER

# Configure logging
logger = logging.getLogger(__name__)

# Severity to Default Delay Days mapping (documented ranges)
# 1-3: 1 day, 4-6: 2 days, 7-8: 3 days, 9-10: 4 days
SEVERITY_TO_DEFAULT_DELAY_DAYS = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 2,
    7: 3,
    8: 3,
    9: 4,
    10: 4
}

# Pydantic schema for extracting delay from raw text
class DelayExtractionSchema(BaseModel):
    delay_days: Optional[int] = Field(None, description="The delay in days explicitly mentioned in the text. Set to null if not explicitly mentioned.")


def _get_or_create_calculation_id(task_id: str, delay_days: int) -> str:
    """
    Returns a sequential integer calculation ID starting with FIN-, persisted in SQLite.
    If the DB is not found or fails, falls back to a stable in-memory cache for idempotency.
    """
    db_path = getattr(backend.db, "DB_PATH", None)
    if db_path and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS finance_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                delay_days INTEGER NOT NULL,
                UNIQUE(task_id, delay_days)
            );
            """)
            # Query first to avoid autoincrement leaks on INSERT conflicts
            cursor.execute(
                "SELECT id FROM finance_calculations WHERE task_id = ? AND delay_days = ?;",
                (task_id, delay_days)
            )
            row = cursor.fetchone()
            if row:
                conn.close()
                return f"FIN-{row[0]}"

            # Insert if not exists
            cursor.execute(
                "INSERT INTO finance_calculations (task_id, delay_days) VALUES (?, ?);",
                (task_id, delay_days)
            )
            conn.commit()
            
            cursor.execute(
                "SELECT id FROM finance_calculations WHERE task_id = ? AND delay_days = ?;",
                (task_id, delay_days)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"FIN-{row[0]}"
        except Exception as e:
            logger.warning(f"Error checking sequential calculation ID in database: {e}")

    # Fallback to local cache
    global _fallback_seq_ids
    if not hasattr(_get_or_create_calculation_id, "_fallback_seq_ids"):
        _get_or_create_calculation_id._fallback_seq_ids = {}
    key = (task_id, delay_days)
    if key not in _get_or_create_calculation_id._fallback_seq_ids:
        _get_or_create_calculation_id._fallback_seq_ids[key] = len(_get_or_create_calculation_id._fallback_seq_ids) + 1
    return f"FIN-{_get_or_create_calculation_id._fallback_seq_ids[key]}"


def assess_finance(observe_output: Dict[str, Any], raw_event_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Estimates project schedule delays and calculates marginal financial exposure
    (operating cost increases and penalties) for the affected tasks.

    Returns (in addition to existing fields):
      cost_breakdown: itemized breakdown with assumption labels and source tags
      cost_coverage: "1/3 verified, 2 estimated"
      calculation_id: FIN-{sequential integer, persisted in DB}
    """
    # 1. Handle upstream parse errors
    if observe_output.get("parse_error"):
        logger.warning("Financial assessment halted due to upstream parse error.")
        return {
            "status": "error",
            "task_id": None,
            "delay_days_used": None,
            "delay_source": None,
            "cpm_result": {
                "assigned_crew": None,
                "daily_operating_cost": None,
                "contractor_penalty_rate": None,
                "critical_path": None,
                "baseline_project_duration": None,
                "new_project_duration": None,
                "project_delay": None,
                "total_financial_exposure": None,
                "breakdown": None,
                "tasks": None,
                "halted_task_id": None,
                "fallback_mode_active": False,
                "parse_error": True
            },
            "cost_breakdown": None,
            "cost_coverage": None,
            "calculation_id": None,
            "summary": "Financial assessment halted: Observe Agent failed to parse the event."
        }

    # 2. Handle task_not_matched (insufficient data state)
    task_id = observe_output.get("task_id")
    if observe_output.get("task_not_matched") or not task_id:
        logger.info("No matched task ID. Returning insufficient data state.")
        return {
            "status": "insufficient_data",
            "task_id": None,
            "delay_days_used": None,
            "delay_source": None,
            "cpm_result": {
                "assigned_crew": None,
                "daily_operating_cost": None,
                "contractor_penalty_rate": None,
                "critical_path": None,
                "baseline_project_duration": None,
                "new_project_duration": None,
                "project_delay": None,
                "total_financial_exposure": None,
                "breakdown": None,
                "tasks": None,
                "halted_task_id": None,
                "fallback_mode_active": False,
                "parse_error": False
            },
            "cost_breakdown": None,
            "cost_coverage": None,
            "calculation_id": None,
            "summary": "Financial evaluation skipped: no task was matched in the event report."
        }

    severity = observe_output.get("severity", 1)

    # 3. Load project state to find task_name for get_task_impact lookup
    state, state_fallback = get_project_state()
    tasks_list = state.get("schedule_tasks", [])
    task = next((t for t in tasks_list if t["task_id"] == task_id), None)
    if not task:
        logger.error(f"Task ID '{task_id}' not found in active database tasks.")
        return {
            "status": "error",
            "task_id": task_id,
            "delay_days_used": None,
            "delay_source": None,
            "cpm_result": {
                "assigned_crew": None,
                "daily_operating_cost": None,
                "contractor_penalty_rate": None,
                "critical_path": None,
                "baseline_project_duration": None,
                "new_project_duration": None,
                "project_delay": None,
                "total_financial_exposure": None,
                "breakdown": None,
                "tasks": None,
                "halted_task_id": task_id,
                "fallback_mode_active": state_fallback,
                "parse_error": False
            },
            "cost_breakdown": None,
            "cost_coverage": None,
            "calculation_id": None,
            "summary": f"Financial evaluation failed: task ID '{task_id}' not found in active schedule."
        }

    task_name = task["task_name"]

    # 4. Extract or estimate delay duration
    delay_days = None
    delay_source = None
    api_key = get_api_key()

    if api_key and raw_event_text and not use_mock_llm():
        client = genai.Client(api_key=api_key)
        prompt_extraction = f"""
You are the Finance Agent for ConstructionOS AI.
Analyze the raw site event report and extract the number of delay days.

Raw report context:
"{raw_event_text}"

If the text explicitly mentions a delay duration in days (e.g. "delayed by 5 days", "stopped for 3 days", "4-day delay"), extract and return that number of days as an integer.
If no delay duration is explicitly mentioned in the text, return null.
"""
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_extraction,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DelayExtractionSchema,
                ),
            )
            data = json.loads(response.text)
            extracted_days = data.get("delay_days")
            if extracted_days is not None and extracted_days > 0:
                delay_days = int(extracted_days)
                delay_source = "extracted_from_text"
        except Exception as e:
            logger.warning(f"Failed to extract delay days via Gemini: {e}")

    # Fallback to documented severity mapping
    if delay_days is None:
        delay_days = SEVERITY_TO_DEFAULT_DELAY_DAYS.get(severity, 1)
        delay_source = "severity_fallback"

    # 5. Call CPM engine tools
    try:
        impact = get_task_impact(task_name)
        schedule_result = recalculate_schedule(task_id, delay_days)
    except Exception as e:
        logger.error(f"CPM engine calculations failed: {e}")
        return {
            "status": "error",
            "task_id": task_id,
            "delay_days_used": delay_days,
            "delay_source": delay_source,
            "cpm_result": {
                "assigned_crew": None,
                "daily_operating_cost": None,
                "contractor_penalty_rate": None,
                "critical_path": None,
                "baseline_project_duration": None,
                "new_project_duration": None,
                "project_delay": None,
                "total_financial_exposure": None,
                "breakdown": None,
                "tasks": None,
                "halted_task_id": task_id,
                "fallback_mode_active": state_fallback,
                "parse_error": False
            },
            "cost_breakdown": None,
            "cost_coverage": None,
            "calculation_id": None,
            "summary": f"Financial evaluation failed: CPM math calculation error: {e}"
        }

    # 6. Generate financial summary brief using Gemini
    brief = ""
    if api_key and not use_mock_llm():
        client = genai.Client(api_key=api_key)
        prompt_brief = (
            "You are the Finance Agent for ConstructionOS AI.\n"
            "Your task is to draft a financial impact brief detailing a project schedule disruption.\n\n"
            "The financial and CPM schedule impacts have already been calculated as fixed facts:\n"
            f"- Affected Task: {task_name} (ID: {task_id})\n"
            f"- Task Delay: {delay_days} days (Source: {delay_source})\n"
            f"- Project delay: {schedule_result['project_delay']} days "
            f"(New Duration: {schedule_result['new_project_duration']} days, "
            f"Baseline: {schedule_result['baseline_project_duration']} days)\n"
            f"- Marginal Financial Exposure: {schedule_result['total_financial_exposure']} INR\n"
            f"  - Operating Cost Increase: {schedule_result['breakdown']['operating_cost_exposure']} INR\n"
            f"  - Delay Penalty: {schedule_result['breakdown']['penalty_exposure']} INR\n"
            f"- Contractor: {impact['assigned_crew']} "
            f"(Daily cost: {impact['daily_operating_cost']} INR, "
            f"Penalty: {impact['contractor_penalty_rate']} INR/day)\n\n"
            f"Raw Jobsite Report Context:\n\"{raw_event_text or 'No raw text provided.'}\"\n\n"
            "Please write a brief summary explaining these financial impacts. "
            "Your narrative must be entirely consistent with the facts above. "
            "Keep the summary under 120 words."
        )
        try:
            res = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt_brief
            )
            brief = res.text.strip()
        except Exception as e:
            logger.error(f"Gemini brief generation failed: {e}")
            brief = (
                f"Financial evaluation complete. "
                f"Marginal exposure is {schedule_result['total_financial_exposure']} INR "
                f"with project delay of {schedule_result['project_delay']} days."
            )
    else:
        prefix = "[MOCK] " if use_mock_llm() else ""
        brief = (
            f"{prefix}Financial Impact Assessment: Task {task_id} ({task_name}) "
            f"delayed by {delay_days} day(s) (source: {delay_source}). "
            f"Project schedule extends from {schedule_result['baseline_project_duration']} "
            f"to {schedule_result['new_project_duration']} days "
            f"({schedule_result['project_delay']} day project delay). "
            f"Total marginal financial exposure: "
            f"\u20b9{schedule_result['total_financial_exposure']:,.0f} INR "
            f"(operating cost: \u20b9{schedule_result['breakdown']['operating_cost_exposure']:,.0f}, "
            f"penalties: \u20b9{schedule_result['breakdown']['penalty_exposure']:,.0f}). "
            f"Contractor: {impact['assigned_crew']}."
        )

    # 7. Build itemized cost breakdown (P1)
    contractor_row = next(
        (c for c in state.get("contractors", []) if c["name"] == impact["assigned_crew"]),
        {}
    )
    active_workers = int(contractor_row.get("active_workers", 0))
    breakdown_data = _build_cost_breakdown(
        task_id=task_id,
        delay_days=delay_days,
        active_workers=active_workers,
        daily_operating_cost=impact["daily_operating_cost"],
        contractor_penalty_rate=impact["contractor_penalty_rate"],
    )

    # Return structured schema
    return {
        "status": "success",
        "task_id": task_id,
        "delay_days_used": delay_days,
        "delay_source": delay_source,
        "cpm_result": {
            "scope": "project_cascade",
            "assigned_crew": impact["assigned_crew"],
            "daily_operating_cost": impact["daily_operating_cost"],
            "contractor_penalty_rate": impact["contractor_penalty_rate"],
            "critical_path": impact["critical_path"],
            "baseline_project_duration": schedule_result["baseline_project_duration"],
            "new_project_duration": schedule_result["new_project_duration"],
            "project_delay": schedule_result["project_delay"],
            "total_financial_exposure": schedule_result["total_financial_exposure"],
            "breakdown": schedule_result["breakdown"],
            "tasks": schedule_result["tasks"],
            "halted_task_id": task_id,
            "delay_days": delay_days,
            "fallback_mode_active": schedule_result["fallback_mode_active"] or state_fallback,
            "parse_error": False
        },
        "cost_breakdown": breakdown_data["cost_breakdown"],
        "cost_coverage": breakdown_data["cost_coverage"],
        "calculation_id": breakdown_data["calculation_id"],
        "summary": brief
    }


# ---------------------------------------------------------------------------
# P1 helper: itemized cost breakdown with explicit assumption labels
# ---------------------------------------------------------------------------
def _build_cost_breakdown(
    task_id: str,
    delay_days: int,
    active_workers: int,
    daily_operating_cost: float,
    contractor_penalty_rate: float,
) -> Dict[str, Any]:
    """
    Builds an itemized cost breakdown with explicit assumption labels and source tags.
    """
    # ── idle_labour ──────────────────────────────────────────────────────────
    idle_labour_amount = active_workers * ASSUMED_DAILY_WAGE_PER_WORKER * delay_days
    idle_labour = {
        "amount": round(idle_labour_amount, 2),
        "formula": f"{active_workers} workers \u00d7 \u20b9{ASSUMED_DAILY_WAGE_PER_WORKER}/day \u00d7 {delay_days} days",
        "source": "assumed_wage_rate"
    }

    # ── equipment_extension ──────────────────────────────────────────────────
    daily_labor_cost = active_workers * ASSUMED_DAILY_WAGE_PER_WORKER
    daily_equip_cost = daily_operating_cost - daily_labor_cost
    is_negative = daily_equip_cost < 0

    equip_amount = max(0.0, daily_equip_cost) * delay_days
    equipment_extension = {
        "amount": round(equip_amount, 2),
        "formula": "(daily_operating_cost - (active_workers \u00d7 assumed_wage)) \u00d7 delay_days \u2014 residual after estimated labour",
        "source": "assumed_residual"
    }
    if is_negative:
        equipment_extension["warning"] = "assumed wage rate exceeds contractor's recorded daily operating cost \u2014 labour/equipment split unreliable for this contractor"

    # ── delay_penalty ────────────────────────────────────────────────────────
    penalty_amount = contractor_penalty_rate * delay_days
    delay_penalty = {
        "amount": round(penalty_amount, 2),
        "formula": "contractor_penalty_rate \u00d7 delay_days",
        "source": "verified"
    }

    # ── recovery_overtime ────────────────────────────────────────────────────
    recovery_overtime = {
        "amount": 0.0,
        "formula": "populated only if propose_reschedule has run and reassigns crew hours; otherwise 0 and omitted from coverage count",
        "source": "assumed"
    }

    # Coverage count: recovery_overtime is omitted from count because it's 0.
    # Out of 3 counted fields, only delay_penalty is verified.
    cost_coverage = "1/3 verified, 2 estimated"
    calculation_id = _get_or_create_calculation_id(task_id, delay_days)
    
    # Halted task total exposure: sum of local direct costs
    halted_task_total = idle_labour["amount"] + equipment_extension["amount"] + delay_penalty["amount"] + recovery_overtime["amount"]

    return {
        "cost_breakdown": {
            "scope": "halted_task_only",
            "halted_task_total": round(halted_task_total, 2),
            "idle_labour": idle_labour,
            "equipment_extension": equipment_extension,
            "delay_penalty": delay_penalty,
            "recovery_overtime": recovery_overtime,
        },
        "cost_coverage": cost_coverage,
        "calculation_id": calculation_id,
    }


# ---------------------------------------------------------------------------
# P2: What-if delay range simulator
# ---------------------------------------------------------------------------
def simulate_delay_range(task_id: str) -> Dict[str, Any]:
    """
    Calls the existing recalculate_schedule from cpm_engine.py for delay_days = 1, 2, 3.
    Returns: {"1_day": total_financial_exposure, "2_day": ..., "3_day": ...}
    No new CPM logic — this must call the already-tested function three times, not reimplement anything.
    """
    res1 = recalculate_schedule(task_id, 1)
    res2 = recalculate_schedule(task_id, 2)
    res3 = recalculate_schedule(task_id, 3)
    return {
        "1_day": res1["total_financial_exposure"],
        "2_day": res2["total_financial_exposure"],
        "3_day": res3["total_financial_exposure"],
    }


# ---------------------------------------------------------------------------
# P3: Avoided-loss calculation
# ---------------------------------------------------------------------------
def calculate_avoided_loss(baseline_exposure: float, reschedule_output: dict) -> dict:
    """
    avoided_loss = baseline_exposure - (reschedule_output's remaining exposure + any recovery cost)
    """
    remaining_exposure = reschedule_output.get("estimated_remaining_penalty", 0.0)
    # Recovery cost is 0 since we do not have recovery overtime costs applied yet
    recovery_cost = 0.0
    avoided = baseline_exposure - (remaining_exposure + recovery_cost)
    return {
        "avoided_loss": round(avoided, 2),
        "baseline_exposure": baseline_exposure,
        "remaining_exposure": remaining_exposure,
        "recovery_cost": recovery_cost
    }
