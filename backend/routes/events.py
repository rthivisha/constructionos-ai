import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.observe_agent import observe_event
from backend.agents.safety_agent import assess_safety
from backend.agents.finance_agent import assess_finance
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
            "brief": f"Safety assessment unavailable: Agent crashed with error: {safety_res}",
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

    # 6. Return aggregated pipeline execution output
    return {
        "observation": observe_output,
        "safety_assessment": safety_res,
        "financial_assessment": finance_res,
        "tradeoff_reconciliation": tradeoff_res,
        "proposed_reschedule": reschedule_proposal,
    }
