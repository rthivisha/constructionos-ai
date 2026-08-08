import logging
import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.agents.observe_agent import get_api_key
from backend.tools.cpm_engine import get_project_state, get_task_impact, recalculate_schedule

# Configure logging
logger = logging.getLogger(__name__)

# Severity to Default Delay Days mapping (documented ranges)
SEVERITY_TO_DEFAULT_DELAY_DAYS = {
    1: 1,
    2: 1,
    3: 2,
    4: 2,
    5: 3,
    6: 4,
    7: 5,
    8: 7,
    9: 10,
    10: 14
}

# Pydantic schema for extracting delay from raw text
class DelayExtractionSchema(BaseModel):
    delay_days: Optional[int] = Field(None, description="The delay in days explicitly mentioned in the text. Set to null if not explicitly mentioned.")

def assess_finance(observe_output: Dict[str, Any], raw_event_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Estimates project schedule delays and calculates marginal financial exposure
    (operating cost increases and penalties) for the affected tasks.
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
                "fallback_mode_active": False,
                "parse_error": True
            },
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
                "fallback_mode_active": False,
                "parse_error": False
            },
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
                "fallback_mode_active": state_fallback,
                "parse_error": False
            },
            "summary": f"Financial evaluation failed: task ID '{task_id}' not found in active schedule."
        }

    task_name = task["task_name"]

    # 4. Extract or estimate delay duration
    delay_days = None
    delay_source = None
    api_key = get_api_key()

    if api_key and raw_event_text:
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
                model='gemini-2.0-flash',
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
                "fallback_mode_active": state_fallback,
                "parse_error": False
            },
            "summary": f"Financial evaluation failed: CPM math calculation error: {e}"
        }

    # 6. Generate financial summary brief using Gemini
    brief = ""
    if api_key:
        client = genai.Client(api_key=api_key)
        prompt_brief = f"""
You are the Finance Agent for ConstructionOS AI.
Your task is to draft a financial impact brief detailing a project schedule disruption.

The financial and CPM schedule impacts have already been calculated as fixed facts:
- Affected Task: {task_name} (ID: {task_id})
- Task Delay: {delay_days} days (Source: {delay_source})
- Project delay: {schedule_result['project_delay']} days (New Duration: {schedule_result['new_project_duration']} days, Baseline: {schedule_result['baseline_project_duration']} days)
- Marginal Financial Exposure: {schedule_result['total_financial_exposure']} INR
  - Operating Cost Increase: {schedule_result['breakdown']['operating_cost_exposure']} INR
  - Delay Penalty: {schedule_result['breakdown']['penalty_exposure']} INR
- Contractor: {impact['assigned_crew']} (Daily cost: {impact['daily_operating_cost']} INR, Penalty: {impact['contractor_penalty_rate']} INR/day)

Raw Jobsite Report Context:
"{raw_event_text or 'No raw text provided.'}"

Please write a brief summary explaining these financial impacts. Your narrative must be entirely consistent with the facts above. Keep the summary under 120 words.
"""
        try:
            res = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt_brief
            )
            brief = res.text.strip()
        except Exception as e:
            logger.error(f"Gemini brief generation failed: {e}")
            brief = f"Financial evaluation complete. Marginal exposure is {schedule_result['total_financial_exposure']} INR with project delay of {schedule_result['project_delay']} days."
    else:
        brief = f"Financial evaluation complete. Marginal exposure is {schedule_result['total_financial_exposure']} INR with project delay of {schedule_result['project_delay']} days."

    # Return structured schema
    return {
        "status": "success",
        "task_id": task_id,
        "delay_days_used": delay_days,
        "delay_source": delay_source,
        "cpm_result": {
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
            "fallback_mode_active": schedule_result["fallback_mode_active"] or state_fallback,
            "parse_error": False
        },
        "summary": brief
    }
