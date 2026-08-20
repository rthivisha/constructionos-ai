import logging
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.agents.observe_agent import get_api_key
from backend.config import MODEL_NAME, use_mock_llm, call_gemini_with_retry

# Configure logging
logger = logging.getLogger(__name__)

# =========================================================================================
# CRITICAL SAFETY CONSTRAINT:
# controls_verified must remain an explicit human-confirmed flag originating from a site
# manager action in the UI. It must NEVER be inferred, assumed, defaulted to True, or
# self-certified by any LLM call, since an AI model confirming its own prerequisite defeats
# the entire purpose of the human safety verification gate.
# =========================================================================================

# Pydantic schema for Gemini structured tradeoff output
class TradeoffResponseSchema(BaseModel):
    decision: str = Field(..., description="Must be exactly 'continue' or 'halt'.")
    reasoning: str = Field(..., description="Detailed explanation of the trade-offs weighed.")
    rejected_alternative: str = Field(..., description="Must be exactly the other option ('continue' if decision is 'halt', 'halt' if decision is 'continue').")
    rejected_because: str = Field(..., description="Concise explanation of why the rejected alternative was discarded.")

def assess_tradeoff(
    safety_output: Optional[Dict[str, Any]],
    finance_output: Optional[Dict[str, Any]],
    raw_event_text: Optional[str] = None,
    controls_verified: bool = False
) -> Dict[str, Any]:
    """
    Reconciles Safety and Finance assessments into a single justified decision.
    Decision values:
      - 'halt': BLOCKED regulatory status, unmitigated hazard, or pipeline failure.
      - 'continue': SAFE status, or CONDITIONAL with verified field controls.
      - 'pending_verification': CONDITIONAL status where mandatory controls are not yet confirmed verified.

    Safety HARD_STOP overrides all other considerations.
    If Finance is unavailable/insufficient/errored, safety alone dictates the choice.
    """
    # 1. Determine Safety status
    safety_valid = False
    hard_stop = False
    safety_status = "UNKNOWN"
    triggered_rules = []
    mandatory_controls = []
    
    if isinstance(safety_output, dict) and not safety_output.get("parse_error") and safety_output.get("status") != "unavailable":
        safety_valid = True
        hard_stop = safety_output.get("hard_stop", False)
        safety_status = safety_output.get("safety_status", "SAFE" if not hard_stop else "BLOCKED")
        triggered_rules = safety_output.get("triggered_rules", [])
        mandatory_controls = safety_output.get("mandatory_field_controls", [])

    # 2. Determine Finance status
    finance_valid = False
    if isinstance(finance_output, dict):
        status = finance_output.get("status")
        parse_error = finance_output.get("parse_error", False)
        # Treated as unavailable if it is not success, or has error/insufficient_data/parse_error
        if status == "success" and not parse_error:
            finance_valid = True

    upstream_fallback = (
        bool(safety_output and safety_output.get("fallback_mode_active"))
        or bool(finance_output and finance_output.get("fallback_mode_active"))
        or use_mock_llm()
    )

    # 3. Path A: Safety is unavailable (FAIL-SAFE HALT)
    if not safety_valid:
        logger.warning("Safety output unavailable/invalid. Defaulting to safe halt.")
        return {
            "decision": "halt",
            "reasoning": "Safety assessment is unavailable due to an agent error or parse failure. Operation must halt to prevent unmitigated safety hazards.",
            "rejected_alternative": "continue",
            "rejected_because": "safety compliance cannot be verified, rendering operations unsafe to proceed.",
            "fallback_mode_active": True
        }

    # 4. Path B1: Safety is CONDITIONAL and controls are NOT yet verified by site manager
    if safety_status == "CONDITIONAL" and not controls_verified:
        logger.info("Safety status is CONDITIONAL and controls_verified is False. Returning pending_verification.")
        controls_list_str = "; ".join(mandatory_controls) if mandatory_controls else "mandatory safety control checklist"
        return {
            "decision": "pending_verification",
            "reasoning": (
                f"Operations are held pending site management verification. "
                f"Under regulatory compliance requirements, the following mandatory field controls remain unconfirmed: {controls_list_str}. "
                f"Work cannot proceed until a site manager physically verifies and signs off on these required controls."
            ),
            "rejected_alternative": "continue",
            "rejected_because": "required safety controls not yet verified by site manager.",
            "fallback_mode_active": upstream_fallback
        }

    # 5. Path B2: Safety is CONDITIONAL and controls ARE confirmed verified by site manager
    if safety_status == "CONDITIONAL" and controls_verified:
        logger.info("Safety status is CONDITIONAL and controls_verified is True. Proceeding under verified conditional clearance.")
        if not finance_valid:
            default_reasoning = (
                "Proceeding under verified conditional clearance: Required field controls have been confirmed by site management. "
                "No active regulatory hard stops remain, and operations are permitted to resume. Financial delay cost exposure could not be assessed."
            )
            agent_fallback = False
            api_key = get_api_key()
            if api_key and not use_mock_llm():
                client = genai.Client(api_key=api_key)
                prompt = f"""
You are the Trade-off Agent for ConstructionOS AI.
Your task is to write a narrative rationale explaining an operational continuation under verified conditional clearance.

Fixed facts:
- Decision: continue
- Note: Proceeding under verified conditional clearance. Mandatory field controls were confirmed verified by site management.
- Rejection reason: Required safety controls verified; financial exposure data unavailable.
- Raw jobsite event report: "{raw_event_text or 'No raw text provided.'}"

Explain that work is proceeding under verified conditional clearance because the required site controls were confirmed. Keep it under 100 words.
"""
                try:
                    response = call_gemini_with_retry(
                        client=client,
                        model=MODEL_NAME,
                        contents=prompt,
                        max_retries=3,
                        initial_delay=1.0,
                        backoff_factor=2.0
                    )
                    default_reasoning = response.text.strip()
                except Exception as e:
                    logger.error(f"Gemini tradeoff reasoning failed after retries: {e}")
                    agent_fallback = True
            else:
                agent_fallback = True

            return {
                "decision": "continue",
                "reasoning": default_reasoning,
                "rejected_alternative": "halt",
                "rejected_because": "required safety controls have been verified by site manager, allowing work to proceed.",
                "fallback_mode_active": upstream_fallback or agent_fallback
            }

        # Finance is valid for CONDITIONAL with controls_verified=True
        api_key = get_api_key()
        if not api_key or use_mock_llm():
            exposure = finance_output.get("cpm_result", {}).get("total_financial_exposure", 0)
            delay_days = finance_output.get("delay_days_used", 0)
            task_id = finance_output.get("task_id", "unknown")
            critical = finance_output.get("cpm_result", {}).get("critical_path", False)
            prefix = "[MOCK] " if use_mock_llm() else ""
            return {
                "decision": "continue",
                "reasoning": (
                    f"{prefix}Proceeding under verified conditional clearance: Required field controls have been confirmed by site management. "
                    f"Task {task_id} is {'on' if critical else 'not on'} the critical path with an estimated delay of {delay_days} day(s) "
                    f"(Marginal financial exposure: ₹{exposure:,.0f} INR). "
                    f"With mandatory safety controls verified, the operational delay is within tolerable limits. Decision: continue."
                ),
                "rejected_alternative": "halt",
                "rejected_because": (
                    f"mandatory field controls were verified by site management and the financial exposure (₹{exposure:,.0f} INR) "
                    f"does not justify halting operations."
                ),
                "fallback_mode_active": True
            }

        client = genai.Client(api_key=api_key)
        cpm_res = finance_output.get("cpm_result", {})
        delay_days = finance_output.get("delay_days_used", 0)
        financial_exposure = cpm_res.get("total_financial_exposure", 0)
        critical_path = cpm_res.get("critical_path", False)
        
        prompt = f"""
You are the Trade-off Agent for ConstructionOS AI.
Your task is to reconcile Safety and Finance reports for a jobsite event and make a final recommendation: either "continue" (keep working and absorb the delay/cost) or "halt" (stop work to investigate/rectify).

Event details:
- Safety Status: CONDITIONAL (Proceeding under verified conditional clearance: mandatory field controls confirmed by site manager)
- Affected Task: {finance_output.get('task_id')}
- Estimated Task Delay: {delay_days} days (Task on Critical Path: {critical_path})
- Project Delay Cost Exposure: {financial_exposure} INR
- Raw site report: "{raw_event_text or 'No raw text provided.'}"

Weigh the trade-offs:
- Halting cost vs Safety threat. Required field controls are verified, so work may proceed if financial exposure and delay are manageable.
- Your narrative reasoning MUST explicitly state that the project is "proceeding under verified conditional clearance".
- Keep response strictly compliant with schema.
"""
        try:
            response = call_gemini_with_retry(
                client=client,
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TradeoffResponseSchema,
                ),
                max_retries=3,
                initial_delay=1.0,
                backoff_factor=2.0
            )
            data = json.loads(response.text)
            reasoning_text = data.get("reasoning", "")
            if "proceeding under verified conditional clearance" not in reasoning_text.lower():
                reasoning_text = f"Proceeding under verified conditional clearance: {reasoning_text}"
            return {
                "decision": data.get("decision", "continue"),
                "reasoning": reasoning_text,
                "rejected_alternative": data.get("rejected_alternative", "halt"),
                "rejected_because": data.get("rejected_because", ""),
                "fallback_mode_active": upstream_fallback
            }
        except Exception as e:
            logger.error(f"Structured Gemini tradeoff query failed for conditional verified after retries: {e}")
            return {
                "decision": "continue",
                "reasoning": f"Proceeding under verified conditional clearance: Work continues since safety controls were verified by site management. Estimated delay cost exposure: {financial_exposure} INR.",
                "rejected_alternative": "halt",
                "rejected_because": "mandatory field controls have been verified by site management, permitting resumption.",
                "fallback_mode_active": True
            }

    # 6. Path B3: Safety HARD_STOP is True (BLOCKED / ESCALATE / Statutory Hard Stop - DEMAND HALT)
    if hard_stop or safety_status in ("BLOCKED", "ESCALATE"):
        logger.info(f"Safety HARD_STOP triggered (status={safety_status}). Halting operations.")
        rules_str = ", ".join([r.get("code", "") for r in triggered_rules])
        default_reasoning = f"Operations halted due to a non-negotiable regulatory HARD_STOP rule check (rules: {rules_str})."
        agent_fallback = False
        
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
                response = call_gemini_with_retry(
                    client=client,
                    model=MODEL_NAME,
                    contents=prompt,
                    max_retries=3,
                    initial_delay=1.0,
                    backoff_factor=2.0
                )
                default_reasoning = response.text.strip()
            except Exception as e:
                logger.error(f"Gemini tradeoff reasoning failed after retries: {e}")
                agent_fallback = True
        else:
            agent_fallback = True

        return {
            "decision": "halt",
            "reasoning": default_reasoning,
            "rejected_alternative": "continue",
            "rejected_because": "regulatory hard stop is non-negotiable and safety compliance is absolute.",
            "fallback_mode_active": upstream_fallback or agent_fallback
        }

    # 7. Path C: Safety is active (SAFE / no hard stop) but Finance is unavailable/insufficient/errored
    if not finance_valid:
        logger.info("Safety has no hard stop, but Finance is unavailable. Continuing on safety alone.")
        default_reasoning = "No regulatory safety hard stop was triggered. Operations are allowed to continue. Financial delay cost exposure could not be assessed."
        agent_fallback = False
        
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
                response = call_gemini_with_retry(
                    client=client,
                    model=MODEL_NAME,
                    contents=prompt,
                    max_retries=3,
                    initial_delay=1.0,
                    backoff_factor=2.0
                )
                default_reasoning = response.text.strip()
            except Exception as e:
                logger.error(f"Gemini tradeoff reasoning failed after retries: {e}")
                agent_fallback = True
        else:
            agent_fallback = True

        return {
            "decision": "continue",
            "reasoning": default_reasoning,
            "rejected_alternative": "halt",
            "rejected_because": "no safety hazard was detected and financial exposure is unknown, meaning there is no justification to halt.",
            "fallback_mode_active": upstream_fallback or agent_fallback
        }

    # 8. Path D: Both agents are active and safety is SAFE (GEMINI TRADE-OFF WEIGHING)
    api_key = get_api_key()
    if not api_key or use_mock_llm():
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
            ),
            "fallback_mode_active": True
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
        response = call_gemini_with_retry(
            client=client,
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TradeoffResponseSchema,
            ),
            max_retries=3,
            initial_delay=1.0,
            backoff_factor=2.0
        )
        data = json.loads(response.text)
        return {
            "decision": data.get("decision", "continue"),
            "reasoning": data.get("reasoning", ""),
            "rejected_alternative": data.get("rejected_alternative", "halt"),
            "rejected_because": data.get("rejected_because", ""),
            "fallback_mode_active": upstream_fallback
        }
    except Exception as e:
        logger.error(f"Structured Gemini tradeoff query failed after retries: {e}")
        return {
            "decision": "continue",
            "reasoning": f"Work continues since safety hard stop is not triggered. Estimated delay cost exposure: {financial_exposure} INR. (AI reasoning failed).",
            "rejected_alternative": "halt",
            "rejected_because": "cost of halting outweighs the safety risk when no regulatory violations are triggered.",
            "fallback_mode_active": True
        }

