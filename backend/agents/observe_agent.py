import os
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.agents.event_types import EventType
from backend.tools.cpm_engine import get_project_state
from backend.config import MODEL_NAME, use_mock_llm

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic schema for structured output from Gemini
class ObserveResponseSchema(BaseModel):
    event_type: EventType = Field(description="Must be one of the shared EventType enum values")
    matched_task_id: Optional[str] = Field(None, description="The task ID (e.g., T-101, T-102) from the provided task list that is a clear and direct match for this event. Set to null if there is no clear match or if there is a tie / ambiguity between multiple tasks.")
    severity: int = Field(..., ge=1, le=10, description="Severity rating from 1 to 10")

def get_api_key() -> str:
    """
    Resolves the GEMINI_API_KEY from environment variables or by parsing
    the backend/.env or root .env file fallbacks.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key

    # Direct file fallback checking
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    workspace_dir = os.path.dirname(backend_dir)
    
    for dotenv_path in [
        os.path.join(backend_dir, ".env"),
        os.path.join(workspace_dir, ".env"),
        os.path.join(os.getcwd(), ".env"),
        ".env"
    ]:
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("GEMINI_API_KEY="):
                            value = stripped.split("=", 1)[1].strip('"').strip("'")
                            return value
            except Exception as e:
                logger.warning(f"Failed to read dotenv file at {dotenv_path}: {e}")
                
    return ""


# ---------------------------------------------------------------------------
# MOCK LLM responses for demo scenarios (USE_MOCK_LLM=true)
# ---------------------------------------------------------------------------
def _mock_observe(event_text: str) -> Dict[str, Any]:
    """
    Deterministic mock for the Observe Agent.
    Pattern-matched against the four approved demo scenarios.
    Zero Gemini API calls.

    Scenario 1 — Crane Failure (T-101):   work_at_height, severity 8
    Scenario 2 — Heavy Weather (T-103):   extreme_weather, severity 6
    Scenario 3 — Ambiguous Input:         excavation, task_not_matched=True, severity 3
    Scenario 4 — Minor Material Delay (T-104): toxic_gas category (no KB rule), severity 2, non-critical task
    """
    text = event_text.lower()

    # Scenario 1: Tower Crane Lift Failure (T-101) — work_at_height, critical
    if "crane" in text or "hoist" in text or "tower crane" in text or "mechanical failure" in text:
        logger.info("[MOCK] Observe Agent → crane failure scenario (T-101)")
        return {
            "event_type": "work_at_height",
            "task_id": "T-101",
            "severity": 8,
            "task_not_matched": False,
            "parse_error": False
        }

    # Scenario 2: Heavy Weather (T-103) — extreme_weather, critical
    if any(w in text for w in ["weather", "rain", "wind", "storm", "monsoon", "flood", "cyclone", "heat"]):
        logger.info("[MOCK] Observe Agent → heavy weather scenario (T-103)")
        return {
            "event_type": "extreme_weather",
            "task_id": "T-103",
            "severity": 6,
            "task_not_matched": False,
            "parse_error": False
        }

    # Scenario 4: Minor Material Delay (T-104) — toxic_gas category (no KB rule), non-critical
    # Matched before ambiguous so specific keywords win
    if any(w in text for w in ["conduit", "electrical", "material", "delivery", "ventilation", "minor", "supply"]):
        logger.info("[MOCK] Observe Agent → minor material delay scenario (T-104, no KB rule)")
        return {
            "event_type": "toxic_gas",
            "task_id": "T-104",
            "severity": 2,
            "task_not_matched": False,
            "parse_error": False
        }

    # Scenario 3: Intentionally Ambiguous Input — excavation, no task match
    logger.info("[MOCK] Observe Agent → ambiguous input scenario (no task match)")
    return {
        "event_type": "excavation",
        "task_id": None,
        "severity": 3,
        "task_not_matched": True,
        "parse_error": False
    }


def observe_event(event_text: str) -> Dict[str, Any]:
    """
    Parses and categorizes a raw site event report using Gemini,
    validates the task match against active database tasks,
    and returns a structured output.
    In mock mode (USE_MOCK_LLM=true), returns deterministic results with no API calls.
    """
    # --- MOCK MODE ---
    if use_mock_llm():
        logger.info("[MOCK MODE] Observe Agent running without Gemini API call.")
        return _mock_observe(event_text)

    # Fetch available tasks from database/seed fallback
    state, _ = get_project_state()
    tasks = state.get("schedule_tasks", [])
    
    # Format tasks list for prompt context
    tasks_list_str = "\n".join([f"- ID: {t['task_id']}, Name: {t['task_name']}" for t in tasks])
    
    prompt = f"""
You are the Observe Agent for ConstructionOS AI.
Your task is to analyze a raw job-site event report and extract structured details.

Here is the list of available tasks currently active on the site:
{tasks_list_str}

Please categorize the event into one of the EventType enum values:
- "excavation": covers excavation, digging, shoring, side slumping, structural foundation, mud, trenching.
- "work_at_height": covers height, scaffolding, falls, roof work, ladders, harness safety.
- "toxic_gas": covers gas leaks, carbon monoxide, ventilation, chemical fumes, PPE breathing.
- "extreme_weather": covers high wind, heavy rain, monsoon, heat waves, temperature stops.

Match the event to the correct 'matched_task_id' from the list above.
CRITICAL INSTRUCTIONS FOR TASK ID MATCHING:
- Match a task ONLY if the event description has a clear, direct, and unambiguous link to that task.
- If the event is ambiguous, matches multiple tasks equally (a tie), or does not match any available task, you MUST return null for matched_task_id. Do not guess.

Raw event description:
"{event_text}"
"""

    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not configured.")
        
    client = genai.Client(api_key=api_key)
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ObserveResponseSchema,
            ),
        )
        
        # Parse the structured JSON response
        data = json.loads(response.text)
        
        # Create validation object to ensure all fields conform
        parsed_data = ObserveResponseSchema(**data)
        
    except Exception as e:
        logger.error(f"Gemini API invocation or parsing failed: {e}")
        # Return distinct error fallback state
        return {
            "event_type": None,
            "task_id": None,
            "severity": None,
            "task_not_matched": True,
            "parse_error": True
        }

    # Validate matched_task_id against database tasks list
    matched_id = parsed_data.matched_task_id
    valid_task_ids = {t["task_id"] for t in tasks}
    
    if matched_id and matched_id in valid_task_ids:
        task_id = matched_id
        task_not_matched = False
    else:
        task_id = None
        task_not_matched = True
        
    return {
        "event_type": parsed_data.event_type.value,
        "task_id": task_id,
        "severity": parsed_data.severity,
        "task_not_matched": task_not_matched,
        "parse_error": False
    }
