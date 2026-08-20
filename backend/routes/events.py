import asyncio
import logging
import base64
import uuid
import os
import sqlite3
import json
import re
import hashlib
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.observe_agent import observe_event
from backend.agents.safety_agent import assess_safety
from backend.agents.finance_agent import assess_finance, simulate_delay_range, calculate_avoided_loss
from backend.agents.tradeoff_agent import assess_tradeoff
from backend.tools.cpm_engine import propose_reschedule
import backend.db
from backend.db import get_cached_response, save_cached_response

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

class AttachmentPayload(BaseModel):
    filename: str
    content_type: str
    data: str # Base64 encoded

class EventPayload(BaseModel):
    event_text: str
    attachment: Optional[AttachmentPayload] = None
    # CRITICAL SAFETY CONSTRAINT:
    # controls_verified must remain an explicit human-confirmed flag originating from a site
    # manager action in the UI. It must NEVER be inferred, assumed, defaulted to True, or
    # self-certified by any LLM call, since an AI model confirming its own prerequisite defeats
    # the entire purpose of the human safety verification gate.
    controls_verified: bool = False


# ===========================================================================
# Normalization & Safety Boundary
# ===========================================================================
# SAFETY BOUNDARY CONSTRAINT:
# Only exact normalized-text matches (lowercase, trimmed, single whitespace,
# SHA-256 hashed) with matching controls_verified state will be cached and
# served from query_cache. Fuzzy matching or keyword similarity search are
# strictly forbidden so that safety-critical compliance evaluations are never
# served from an approximate match.
# ===========================================================================

def normalize_event_text(text: str, controls_verified: bool = False) -> tuple[str, str]:
    """
    Normalizes event text by trimming, lowercasing, and collapsing whitespace,
    combined with controls_verified status, then generates a SHA-256 hash.
    """
    clean_text = re.sub(r'\s+', ' ', text.strip().lower())
    cache_key_raw = f"{clean_text}::controls_verified={controls_verified}"
    normalized_hash = hashlib.sha256(cache_key_raw.encode('utf-8')).hexdigest()
    return clean_text, normalized_hash


@router.post("")
async def process_site_event(payload: EventPayload):
    """
    Ingests a raw site event report, matches tasks, performs safety compliance checks
    and financial CPM delay recalculations in parallel, and reconciles tradeoffs.
    """
    logger.info(f"Ingesting new site event: '{payload.event_text[:60]}...'")
    
    # Process attachment if present
    attachment_metadata = None
    if payload.attachment:
        # 1. Restrict content_type to an explicit allowlist
        allowed_types = ["image/png", "image/jpeg", "application/pdf"]
        if payload.attachment.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{payload.attachment.content_type}'. Only PNG, JPEG, and PDF are allowed."
            )

        # 2. Decode base64 data
        try:
            b64_data = payload.attachment.data
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            decoded_bytes = base64.b64decode(b64_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file attachment data: {e}"
            )

        # 3. Enforce 5MB limit
        if len(decoded_bytes) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File size exceeds the maximum limit of 5MB."
            )

        # 4. Sanitize and generate unique filename with validated extension
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/pdf": ".pdf"
        }
        ext = ext_map[payload.attachment.content_type]
        unique_filename = f"{uuid.uuid4()}{ext}"

        # 5. Save to local backend/uploads folder
        current_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(os.path.dirname(current_dir), "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, unique_filename)
        
        try:
            with open(file_path, "wb") as f:
                f.write(decoded_bytes)
        except Exception as e:
            logger.error(f"Failed to save file to disk: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Could not store attachment: {e}"
            )

        # 6. Save metadata
        attachment_metadata = {
            "filename": os.path.basename(payload.attachment.filename),
            "url": f"/uploads/{unique_filename}",
            "content_type": payload.attachment.content_type
        }

    # Normalize input text and check exact-match response cache
    clean_text, normalized_hash = normalize_event_text(payload.event_text, payload.controls_verified)
    cached_response = get_cached_response(normalized_hash)
    if cached_response is not None:
        logger.info(f"Exact-match query_cache HIT for hash {normalized_hash[:10]}...")
        cached_response["cached"] = True
        if attachment_metadata:
            cached_response["attachment"] = attachment_metadata
        return cached_response
    
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
            "fallback_mode_active": True,
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
            "fallback_mode_active": True,
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
            "fallback_mode_active": True,
            "cpm_result": {
                "parse_error": False,
                "status": "unavailable",
                "fallback_mode_active": True
            },
            "summary": f"Financial assessment unavailable: Agent crashed with error: {finance_res}"
        }

    # 4. Reconciliation Stage (Weigh Safety vs Finance trade-offs)
    try:
        tradeoff_res = await asyncio.to_thread(
            assess_tradeoff,
            safety_res,
            finance_res,
            payload.event_text,
            payload.controls_verified
        )
    except Exception as e:
        logger.error(f"Trade-off Agent execution crashed: {e}")
        # Fallback decision is always halt on pipeline tradeoff errors to prioritize safety
        tradeoff_res = {
            "decision": "halt",
            "reasoning": f"Reconciliation pipeline error: Trade-off agent failed to execute: {e}",
            "rejected_alternative": "continue",
            "rejected_because": "system orchestration pipeline failure, defaulting to a safe halt.",
            "fallback_mode_active": True
        }

    # 5. Propose a reschedule if CPM produced a valid result (proposal only, no DB write)
    reschedule_proposal = None
    propose_reschedule_ran = False
    try:
        cpm_result = finance_res.get("cpm_result") if isinstance(finance_res, dict) else None
        if (
            cpm_result
            and isinstance(cpm_result, dict)
            and cpm_result.get("halted_task_id")
            and not cpm_result.get("parse_error", False)
        ):
            reschedule_proposal = propose_reschedule(cpm_result)
            propose_reschedule_ran = True
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
    # Only callable when propose_reschedule's output exists for this event.
    avoided_loss_result = None
    if propose_reschedule_ran and reschedule_proposal:
        try:
            baseline_exposure = (
                finance_res.get("cpm_result", {}).get("total_financial_exposure")
                if isinstance(finance_res, dict) else None
            )
            if baseline_exposure is not None:
                avoided_loss_result = calculate_avoided_loss(baseline_exposure, reschedule_proposal)
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

    # 8. Check overall fallback mode & errors
    is_fallback = bool(
        (isinstance(observe_output, dict) and observe_output.get("fallback_mode_active"))
        or (isinstance(safety_res, dict) and safety_res.get("fallback_mode_active"))
        or (isinstance(finance_res, dict) and finance_res.get("fallback_mode_active"))
        or (isinstance(finance_res, dict) and finance_res.get("cpm_result", {}).get("fallback_mode_active"))
        or (isinstance(tradeoff_res, dict) and tradeoff_res.get("fallback_mode_active"))
    )

    has_error = bool(
        (isinstance(observe_output, dict) and observe_output.get("parse_error"))
        or (isinstance(safety_res, dict) and (safety_res.get("parse_error") or safety_res.get("status") == "unavailable"))
        or (isinstance(finance_res, dict) and (finance_res.get("status") in ("error", "unavailable") or finance_res.get("cpm_result", {}).get("parse_error")))
    )

    # 9. Return aggregated pipeline execution output
    response_dict = {
        "observation": observe_output,
        "safety_assessment": safety_res,
        "financial_assessment": finance_res,
        "tradeoff_reconciliation": tradeoff_res,
        "proposed_reschedule": reschedule_proposal,
        "delay_simulation": delay_simulation,
        "controls_verified": payload.controls_verified,
        "fallback_mode_active": is_fallback,
        "cached": False
    }
    # Priority 3: avoided_loss must be entirely absent if propose_reschedule hasn't run
    if propose_reschedule_ran and avoided_loss_result is not None:
        response_dict["avoided_loss"] = avoided_loss_result

    if attachment_metadata:
        response_dict["attachment"] = attachment_metadata

    # 10. Cache Management (Exact-Match Storage)
    # USER CONSTRAINT:
    # Never cache a response where fallback_mode_active is true — only genuine live-Gemini successes
    # should be written to query_cache. A degraded mock-mode answer must not get permanently served after quota recovers.
    if not is_fallback and not has_error:
        logger.info(f"Caching successful live-Gemini response for hash {normalized_hash[:10]}...")
        save_cached_response(normalized_hash, payload.event_text, response_dict)
    else:
        logger.info(f"Skipping query_cache write: is_fallback={is_fallback}, has_error={has_error}")

    # 11. Save to database audit log (site_events table)
    try:
        conn = backend.db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO site_events (event_text, filename, file_path, content_type, pipeline_response)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                payload.event_text,
                attachment_metadata["filename"] if attachment_metadata else None,
                attachment_metadata["url"] if attachment_metadata else None,
                attachment_metadata["content_type"] if attachment_metadata else None,
                json.dumps(response_dict)
            )
        )
        conn.commit()
    except Exception as db_err:
        logger.error(f"Failed to record site event in database: {db_err}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    return response_dict

