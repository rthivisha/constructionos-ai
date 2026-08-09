import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.observe_agent import observe_event
from backend.agents.safety_agent import assess_safety
from backend.agents.finance_agent import assess_finance, simulate_delay_range
from backend.agents.tradeoff_agent import assess_tradeoff
from backend.tools.cpm_engine import propose_reschedule

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

class EventPayload(BaseModel):
    event_text: str

@router.post("")
async def process_site_event(payload: EventPayload):
    """
    Ingests a raw site event report, matches tasks, performs safety compliance checks
    and financial CPM delay recalculations in parallel, and reconciles tradeoffs.
    """
    logger.info(f"Ingesting new site event: '{payload.event_text[:60]}...'")
    
    # 1. Observation Stage (Extract events and task IDs)
    try:
        observe_output = observe_event(payload.event_text)
    except Exception as e:
        logger.error(f"Observe Agent crashed on input: {e}")
        # Standard fallback if Observe Agent fails completely
        observe_output = {
            "event_type": None,
            "task_id": None,
            "severity": None,
            "task_not_matched": True,
            "parse_error": True
        }

    # 2. Parallel Assessment Stage (Safety and Finance runs concurrently)
    safety_task = asyncio.to_thread(assess_safety, observe_output, payload.event_text)
    finance_task = asyncio.to_thread(assess_finance, observe_output, payload.event_text)
    
    results = await asyncio.gather(safety_task, finance_task, return_exceptions=True)
    
    safety_res = results[0]
    finance_res = results[1]
    
    # 3. Handle Parallel Path Failures (mapping exception objects to unavailable states)
    if isinstance(safety_res, Exception):
        logger.error(f"Safety Agent execution crashed during gather: {safety_res}")
        safety_res = {
            "hard_stop": False,
            "triggered_rules": [],
            "plain_reason": f"Safety assessment unavailable: Agent crashed with error: {safety_res}",
            "override_risk": "",
            "exception_mitigation": "",
            "fallback_mode_active": False,
            "parse_error": False,
            "status": "unavailable"
        }
        
    if isinstance(finance_res, Exception):
        logger.error(f"Finance Agent execution crashed during gather: {finance_res}")
        finance_res = {
            "status": "unavailable",
            "task_id": observe_output.get("task_id"),
            "delay_days_used": None,
            "delay_source": None,
            "cpm_result": {
                "parse_error": False,
                "status": "unavailable"
            },
            "summary": f"Financial assessment unavailable: Agent crashed with error: {finance_res}"
        }

    # 4. Reconciliation Stage (Weigh Safety vs Finance trade-offs)
    try:
        tradeoff_res = await asyncio.to_thread(assess_tradeoff, safety_res, finance_res, payload.event_text)
    except Exception as e:
        logger.error(f"Trade-off Agent execution crashed: {e}")
        # Fallback decision is always halt on pipeline tradeoff errors to prioritize safety
        tradeoff_res = {
            "decision": "halt",
            "reasoning": f"Reconciliation pipeline error: Trade-off agent failed to execute: {e}",
            "rejected_alternative": "continue",
            "rejected_because": "system orchestration pipeline failure, defaulting to a safe halt."
        }

    # 5. Propose a reschedule if CPM produced a valid result (proposal only, no DB write)
    reschedule_proposal = None
    try:
        cpm_result = finance_res.get("cpm_result") if isinstance(finance_res, dict) else None
        if (
            cpm_result
            and isinstance(cpm_result, dict)
            and cpm_result.get("halted_task_id")
            and not cpm_result.get("parse_error", False)
        ):
            reschedule_proposal = propose_reschedule(cpm_result)
        else:
            reschedule_proposal = {
                "feasible": False,
                "net_delay_reduction_days": 0,
                "calculation_detail": "No valid CPM result available — reschedule proposal skipped.",
                "proposed_reschedule": [],
            }
    except Exception as e:
        logger.warning(f"propose_reschedule failed (non-fatal): {e}")
        reschedule_proposal = {
            "feasible": False,
            "net_delay_reduction_days": 0,
            "calculation_detail": f"Reschedule proposal error: {e}",
            "proposed_reschedule": [],
        }

    # 6. P3: Avoided-loss calculation
    # Only computed when propose_reschedule actually ran and produced a recovery plan.
    # avoided_loss = baseline_exposure (do-nothing) - (recovery_plan_cost + remaining_exposure)
    # Never fabricated when the proposal did not run.
    avoided_loss = None
    try:
        baseline_exposure = (
            finance_res.get("cpm_result", {}).get("total_financial_exposure")
            if isinstance(finance_res, dict) else None
        )
        if (
            reschedule_proposal
            and reschedule_proposal.get("feasible")
            and baseline_exposure is not None
        ):
            remaining_penalty = reschedule_proposal.get("estimated_remaining_penalty", 0.0)
            # Recovery plan cost = recovery_overtime from cost_breakdown (currently 0 until applied)
            recovery_plan_cost = (
                (finance_res.get("cost_breakdown") or {}).get("recovery_overtime", {}).get("amount", 0.0)
            )
            recovery_total = recovery_plan_cost + remaining_penalty
            avoided = baseline_exposure - recovery_total
            avoided_loss = {
                "baseline_exposure": baseline_exposure,
                "recovery_plan_cost": recovery_plan_cost,
                "remaining_penalty_after_reallocation": remaining_penalty,
                "recovery_total": recovery_total,
                "avoided_loss": round(avoided, 2),
                "note": (
                    "avoided_loss = baseline_exposure − (recovery_plan_cost + remaining_penalty). "
                    "recovery_plan_cost is ₹0 until apply-reschedule is explicitly called."
                ),
            }
    except Exception as e:
        logger.warning(f"avoided_loss computation failed (non-fatal): {e}")

    # 7. P2: What-if delay range simulation
    delay_simulation = None
    try:
        halted_tid = (
            finance_res.get("task_id")
            if isinstance(finance_res, dict) and finance_res.get("status") == "success"
            else None
        )
        if halted_tid:
            delay_simulation = simulate_delay_range(halted_tid)
    except Exception as e:
        logger.warning(f"simulate_delay_range failed (non-fatal): {e}")

    # 8. Return aggregated pipeline execution output
    return {
        "observation": observe_output,
        "safety_assessment": safety_res,
        "financial_assessment": finance_res,
        "tradeoff_reconciliation": tradeoff_res,
        "proposed_reschedule": reschedule_proposal,
        "avoided_loss": avoided_loss,
        "delay_simulation": delay_simulation,
    }
