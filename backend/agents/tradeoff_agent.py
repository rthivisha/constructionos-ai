import logging
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.agents.observe_agent import get_api_key
from backend.config import MODEL_NAME, use_mock_llm

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic schema for Gemini structured tradeoff output
class TradeoffResponseSchema(BaseModel):
    decision: str = Field(..., description="Must be exactly 'continue' or 'halt'.")
    reasoning: str = Field(..., description="Detailed explanation of the trade-offs weighed.")
    rejected_alternative: str = Field(..., description="Must be exactly the other option ('continue' if decision is 'halt', 'halt' if decision is 'continue').")
    rejected_because: str = Field(..., description="Concise explanation of why the rejected alternative was discarded.")

def assess_tradeoff(
    safety_output: Optional[Dict[str, Any]],
    finance_output: Optional[Dict[str, Any]],
    raw_event_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reconciles Safety and Finance assessments into a single justified decision.
    Safety HARD_STOP overrides all other considerations.
    If Finance is unavailable/insufficient/errored, safety alone dictates the choice.
    """
    # 1. Determine Safety status
    safety_valid = False
    hard_stop = False
    triggered_rules = []
    
    if isinstance(safety_output, dict) and not safety_output.get("parse_error") and safety_output.get("status") != "unavailable":
        safety_valid = True
        hard_stop = safety_output.get("hard_stop", False)
        triggered_rules = safety_output.get("triggered_rules", [])


    # 2. Determine Finance status
    finance_valid = False
    if isinstance(finance_output, dict):
        status = finance_output.get("status")
        parse_error = finance_output.get("parse_error", False)
        # Treated as unavailable if it is not success, or has error/insufficient_data/parse_error
        if status == "success" and not parse_error:
            finance_valid = True

    # 3. Path A: Safety is unavailable (FAIL-SAFE HALT)
    if not safety_valid:
        logger.warning("Safety output unavailable/invalid. Defaulting to safe halt.")
        return {
            "decision": "halt",
            "reasoning": "Safety assessment is unavailable due to an agent error or parse failure. Operation must halt to prevent unmitigated safety hazards.",
            "rejected_alternative": "continue",
            "rejected_because": "safety compliance cannot be verified, rendering operations unsafe to proceed."
        }

    # 4. Path B: Safety HARD_STOP is True (DEMAND HALT - NON-NEGOTIABLE)
    if hard_stop:
        logger.info("Safety HARD_STOP triggered. Halting operations.")
        rules_str = ", ".join([r.get("code", "") for r in triggered_rules])
        default_reasoning = f"Operations halted due to a non-negotiable regulatory HARD_STOP rule check (rules: {rules_str})."
        
        api_key = get_api_key()
        if api_key and not use_mock_llm():
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are the Trade-off Agent for ConstructionOS AI.
Your task is to write a narrative rationale explaining a mandatory project halt.

Fixed facts:
- Decision: halt
- Rejection reason: Regulatory safety HARD_STOP triggered ({rules_str}).
- Raw jobsite event report: "{raw_event_text or 'No raw text provided.'}"

Write a narrative reasoning explaining the halt. Highlight the importance of regulatory compliance.
WARNING: Do not contradict the decision to halt. Keep it under 100 words.
"""
            try:
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                default_reasoning = response.text.strip()
            except Exception as e:
                logger.error(f"Gemini tradeoff reasoning failed: {e}")

        return {
            "decision": "halt",
            "reasoning": default_reasoning,
            "rejected_alternative": "continue",
            "rejected_because": "regulatory hard stop is non-negotiable and safety compliance is absolute."
        }

    # 5. Path C: Safety is active (no hard_stop) but Finance is unavailable/insufficient/errored
    if not finance_valid:
        logger.info("Safety has no hard stop, but Finance is unavailable. Continuing on safety alone.")
        default_reasoning = "No regulatory safety hard stop was triggered. Operations are allowed to continue. Financial delay cost exposure could not be assessed."
        
        api_key = get_api_key()
        if api_key and not use_mock_llm():
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are the Trade-off Agent for ConstructionOS AI.
Your task is to write a narrative rationale explaining a continuation decision.

Fixed facts:
- Decision: continue
- Rejection reason: No safety hard stops active; financial exposure data unavailable.
- Raw jobsite event report: "{raw_event_text or 'No raw text provided.'}"

Explain that the decision was made on safety information alone because financial cost exposure could not be assessed.
WARNING: Do not contradict the decision to continue. Keep it under 100 words.
"""
            try:
                response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
                default_reasoning = response.text.strip()
            except Exception as e:
                logger.error(f"Gemini tradeoff reasoning failed: {e}")

        return {
            "decision": "continue",
            "reasoning": default_reasoning,
            "rejected_alternative": "halt",
            "rejected_because": "no safety hazard was detected and financial exposure is unknown, meaning there is no justification to halt."
        }

    # 6. Path D: Both agents are active and safety is not a hard stop (GEMINI TRADE-OFF WEIGHING)
    # We call Gemini to weigh the financial exposure against the event details and make a choice.
    api_key = get_api_key()
    if not api_key or use_mock_llm():
        # Mock / offline Path D: safety clear, finance valid, weigh and continue.
        # This produces an explicit "continue" with stated justification — not a conservative default.
        exposure = finance_output.get("cpm_result", {}).get("total_financial_exposure", 0)
        delay_days = finance_output.get("delay_days_used", 0)
        task_id = finance_output.get("task_id", "unknown")
        critical = finance_output.get("cpm_result", {}).get("critical_path", False)
        prefix = "[MOCK] " if use_mock_llm() else ""
        logger.info("Path D: No safety hard stop, finance valid. Mock continuing with explicit justification.")
        return {
            "decision": "continue",
            "reasoning": (
                f"{prefix}Trade-off assessment complete. No regulatory hard stop was triggered for this event category. "
                f"Task {task_id} is {'on' if critical else 'not on'} the critical path. "
                f"Estimated delay: {delay_days} day(s). Marginal financial exposure: ₹{exposure:,.0f} INR. "
                f"The delay impact is within tolerable bounds and poses no regulatory safety violation. "
                f"Halting operations would incur additional mobilisation and demobilisation costs with no safety-compliance benefit. "
                f"Decision: continue with heightened monitoring."
            ),
            "rejected_alternative": "halt",
            "rejected_because": (
                f"no regulatory violation was triggered and the financial exposure (₹{exposure:,.0f} INR) "
                f"does not justify a halt — halting would add demobilisation costs with no safety compliance benefit."
            )
        }

    client = genai.Client(api_key=api_key)
    
    # Pack parameters for Gemini
    event_severity = safety_output.get("severity", 1)
    event_category = safety_output.get("event_type", "unknown")
    cpm_res = finance_output.get("cpm_result", {})
    delay_days = finance_output.get("delay_days_used", 0)
    financial_exposure = cpm_res.get("total_financial_exposure", 0)
    critical_path = cpm_res.get("critical_path", False)
    
    prompt = f"""
You are the Trade-off Agent for ConstructionOS AI.
Your task is to reconcile Safety and Finance reports for a jobsite event and make a final recommendation: either "continue" (keep working and absorb the delay/cost) or "halt" (stop work to investigate/rectify).

Event details:
- Category: {event_category}
- Safety Severity: {event_severity}/10 (No regulatory hard stop active)
- Affected Task: {finance_output.get('task_id')}
- Estimated Task Delay: {delay_days} days (Task on Critical Path: {critical_path})
- Project Delay Cost Exposure: {financial_exposure} INR
- Raw site report: "{raw_event_text or 'No raw text provided.'}"

Weigh the trade-offs:
- Halting cost vs Safety threat. If safety severity is high (e.g. 7+) or cost/delay risk of continuing is unacceptably high due to safety negligence, you may recommend "halt".
- Otherwise, if the risk is manageable and there are no regulatory violations, recommend "continue".

Your decision and reasoning must follow the schema strictly.
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TradeoffResponseSchema,
            ),
        )
        data = json.loads(response.text)
        return {
            "decision": data.get("decision", "continue"),
            "reasoning": data.get("reasoning", ""),
            "rejected_alternative": data.get("rejected_alternative", "halt"),
            "rejected_because": data.get("rejected_because", "")
        }
    except Exception as e:
        logger.error(f"Structured Gemini tradeoff query failed: {e}")
        return {
            "decision": "continue",
            "reasoning": f"Work continues since safety hard stop is not triggered. Estimated delay cost exposure: {financial_exposure} INR. (AI reasoning failed).",
            "rejected_alternative": "halt",
            "rejected_because": "cost of halting outweighs the safety risk when no regulatory violations are triggered."
        }
