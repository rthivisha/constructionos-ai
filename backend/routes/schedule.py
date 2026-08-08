"""
POST /api/schedule/apply-reschedule

Persists a proposed reschedule to the schedule_tasks table in the database.
This endpoint MUST only be called by an explicit site manager confirmation action.
Calling the main /api/events pipeline multiple times does NOT auto-apply anything —
persistence only happens when this endpoint is explicitly invoked.
"""
import logging
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

import backend.db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class RescheduleTaskEntry(BaseModel):
    task_id: str
    days_absorbed: int


class ApplyReschedulePayload(BaseModel):
    halted_task_id: str
    delay_days: int
    proposed_reschedule: List[RescheduleTaskEntry]


@router.post("/apply-reschedule")
def apply_reschedule(payload: ApplyReschedulePayload):
    """
    Persists a previously proposed reschedule to schedule_tasks.
    For each entry in proposed_reschedule, the duration is extended by days_absorbed
    (representing the slack consumed to absorb the delay) in the database.

    This is a deliberate human action — never called automatically by event ingestion.
    Calling /api/events twice does NOT trigger this endpoint; only an explicit POST
    to /api/schedule/apply-reschedule does.
    """
    if not payload.proposed_reschedule:
        raise HTTPException(status_code=400, detail="proposed_reschedule list is empty — nothing to apply.")

    conn = sqlite3.connect(backend.db.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    applied = []
    try:
        for entry in payload.proposed_reschedule:
            # Verify task exists before updating
            cursor.execute(
                "SELECT task_id, task_name, duration FROM schedule_tasks WHERE task_id = ?;",
                (entry.task_id,)
            )
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                conn.close()
                raise HTTPException(
                    status_code=404,
                    detail=f"Task '{entry.task_id}' not found in schedule_tasks — aborting apply."
                )

            task_id, task_name, current_duration = row
            new_duration = current_duration + entry.days_absorbed

            cursor.execute(
                "UPDATE schedule_tasks SET duration = ? WHERE task_id = ?;",
                (new_duration, entry.task_id)
            )

            applied.append({
                "task_id": task_id,
                "task_name": task_name,
                "previous_duration": current_duration,
                "days_absorbed": entry.days_absorbed,
                "new_duration": new_duration,
                "status": "applied",
            })

            logger.info(
                f"apply-reschedule: {task_id} ({task_name}) duration "
                f"{current_duration} -> {new_duration} (+{entry.days_absorbed}d absorbed)"
            )

        conn.commit()
        logger.info(
            f"apply-reschedule: committed {len(applied)} task update(s) "
            f"for halted_task_id={payload.halted_task_id}, delay={payload.delay_days}d"
        )
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"apply-reschedule DB error: {e}")
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")
    finally:
        conn.close()

    return {
        "status": "applied",
        "halted_task_id": payload.halted_task_id,
        "delay_days": payload.delay_days,
        "applied_count": len(applied),
        "applied": applied,
    }
