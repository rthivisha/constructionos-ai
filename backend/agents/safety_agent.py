import logging
import json
from typing import Dict, Any, Optional
from google import genai

from backend.agents.observe_agent import get_api_key
from backend.tools.cpm_engine import get_project_state

# Configure logging
logger = logging.getLogger(__name__)

def assess_safety(observe_output: Dict[str, Any], raw_event_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates safety compliance by matching the event type against active regulatory rules.
    Issues a HARD_STOP if any matching rule is found.
    """
    # 1. Handle upstream parse errors
    if observe_output.get("parse_error"):
        logger.warning("Safety assessment halted due to upstream parse error.")
        return {
            "hard_stop": False,
            "triggered_rules": [],
            "brief": "Safety assessment halted: Observe Agent failed to parse the event.",
            "fallback_mode_active": False,
            "parse_error": True
        }

    event_type = observe_output.get("event_type")
    severity = observe_output.get("severity")

    # 2. Load active regulatory knowledge base rules
    state, fallback_mode = get_project_state()
    rules = state.get("regulatory_kb", [])

    # 3. Match rules based on trigger condition
    triggered_rules = []
    for rule in rules:
        if rule.get("trigger_condition") == event_type:
            triggered_rules.append({
                "code": rule.get("code"),
                "description": rule.get("description")
            })

    # HARD_STOP is True if any rule trigger condition matches the event type
    hard_stop = len(triggered_rules) > 0

    # 4. Generate explanation brief using Gemini (treating the decision as fixed facts)
    api_key = get_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured. Safety Agent using offline fallback brief.")
        brief = (
            f"Safety evaluation complete. Hard stop: {hard_stop}. "
            f"Triggered rules: {', '.join([r['code'] for r in triggered_rules]) if triggered_rules else 'none'}."
        )
    else:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
You are the Safety Agent for ConstructionOS AI.
Your task is to draft a compliance assessment brief explaining a safety event evaluation.

The safety evaluation results are already decided as fixed facts:
- HARD_STOP: {hard_stop} (if True, this is an absolute, non-overridable stop signal for operations)
- Triggered Rules: {json.dumps(triggered_rules)}
- Event Category: {event_type}
- Event Severity: {severity}/10

Raw Jobsite Report Context:
"{raw_event_text or 'No raw text provided.'}"

Please write a brief summary explaining these facts, emphasizing why a hard stop was or was not issued, and reference relevant regulatory norms (such as BOCW Act or Factories Act) as context.
WARNING: Your narrative must be entirely consistent with the fixed facts above (HARD_STOP is {hard_stop}). Do not contradict or re-evaluate them. Keep it concise (under 120 words).
"""
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            brief = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini brief generation failed: {e}")
            brief = (
                f"Safety evaluation complete (brief generation failed). Hard stop: {hard_stop}. "
                f"Triggered rules: {', '.join([r['code'] for r in triggered_rules]) if triggered_rules else 'none'}."
            )

    return {
        "hard_stop": hard_stop,
        "triggered_rules": triggered_rules,
        "brief": brief,
        "fallback_mode_active": fallback_mode,
        "parse_error": False
    }
