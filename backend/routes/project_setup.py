from fastapi import APIRouter, HTTPException, Depends
from typing import List
import sqlite3
from backend.db import get_db_connection, clear_query_cache
from backend.models import ProjectMeta, Contractor, Division, RegulatoryKb, ScheduleTask, ProjectSetupState

router = APIRouter(prefix="/api/project-setup", tags=["project-setup"])

# Helper function to execute bulk delete and insert in a transaction
def execute_bulk_update(table_name: str, query: str, rows: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table_name};")
        cursor.executemany(query, rows)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database write failure: {e}")
    finally:
        conn.close()

@router.get("", response_model=ProjectSetupState)
def get_project_setup():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch project_meta (assume there is at least 1 row)
        cursor.execute("SELECT name, location, total_budget, spent_to_date FROM project_meta LIMIT 1;")
        meta_row = cursor.fetchone()
        if not meta_row:
            raise HTTPException(status_code=404, detail="Project metadata not configured.")
        meta = ProjectMeta(**dict(meta_row))

        # Fetch contractors
        cursor.execute("SELECT name, scope, daily_operating_cost, daily_delay_penalty, active_workers FROM contractors;")
        contractors = [Contractor(**dict(row)) for row in cursor.fetchall()]

        # Fetch divisions
        cursor.execute("SELECT id, name, lead_contractor FROM divisions;")
        divisions = [Division(**dict(row)) for row in cursor.fetchall()]

        # Fetch regulatory_kb
        cursor.execute("SELECT code, description, trigger_condition FROM regulatory_kb;")
        regulatory_kb = [RegulatoryKb(**dict(row)) for row in cursor.fetchall()]

        # Fetch schedule_tasks
        cursor.execute("SELECT task_id, division_id, task_name, duration, is_critical_path, dependencies FROM schedule_tasks;")
        schedule_tasks = [ScheduleTask(**dict(row)) for row in cursor.fetchall()]

        return ProjectSetupState(
            project_meta=meta,
            contractors=contractors,
            divisions=divisions,
            regulatory_kb=regulatory_kb,
            schedule_tasks=schedule_tasks
        )
    finally:
        conn.close()

@router.put("/meta")
def update_project_meta(meta: ProjectMeta):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if row exists, if so update it, otherwise insert it
        cursor.execute("SELECT id FROM project_meta LIMIT 1;")
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE project_meta SET name = ?, location = ?, total_budget = ?, spent_to_date = ? WHERE id = ?;",
                (meta.name, meta.location, meta.total_budget, meta.spent_to_date, row["id"])
            )
        else:
            cursor.execute(
                "INSERT INTO project_meta (name, location, total_budget, spent_to_date) VALUES (?, ?, ?, ?);",
                (meta.name, meta.location, meta.total_budget, meta.spent_to_date)
            )
        conn.commit()
        # Invalidate query cache
        clear_query_cache()
        return {"status": "success", "message": "Metadata updated successfully"}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database failure: {e}")
    finally:
        conn.close()

@router.put("/contractors")
def update_contractors(contractors: List[Contractor]):
    # Validate symmetric delete checks
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, lead_contractor FROM divisions;")
    active_divisions = cursor.fetchall()
    conn.close()

    new_names = {c.name for c in contractors}
    for div in active_divisions:
        if div["lead_contractor"] not in new_names:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete contractor '{div['lead_contractor']}' because it is currently referenced by division '{div['name']}' ({div['id']})."
            )

    rows = [(c.name, c.scope, c.daily_operating_cost, c.daily_delay_penalty, c.active_workers) for c in contractors]
    execute_bulk_update(
        "contractors",
        "INSERT INTO contractors (name, scope, daily_operating_cost, daily_delay_penalty, active_workers) VALUES (?, ?, ?, ?, ?);",
        rows
    )
    # Invalidate query cache
    clear_query_cache()
    return {"status": "success", "message": f"Successfully updated {len(contractors)} contractors."}

@router.put("/divisions")
def update_divisions(divisions: List[Division]):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Validate contractor exists
    cursor.execute("SELECT name FROM contractors;")
    contractor_names = {row["name"] for row in cursor.fetchall()}
    
    # Validate symmetric delete checks (existing tasks must point to a valid division ID)
    cursor.execute("SELECT task_id, task_name, division_id FROM schedule_tasks;")
    active_tasks = cursor.fetchall()
    conn.close()

    for div in divisions:
        if div.lead_contractor not in contractor_names:
            raise HTTPException(
                status_code=400,
                detail=f"Lead contractor '{div.lead_contractor}' for division '{div.name}' does not exist. Please create the contractor first."
            )

    new_division_ids = {d.id for d in divisions}
    for task in active_tasks:
        if task["division_id"] not in new_division_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete division '{task['division_id']}' because it is currently referenced by task '{task['task_name']}' ({task['task_id']})."
            )

    rows = [(d.id, d.name, d.lead_contractor) for d in divisions]
    execute_bulk_update(
        "divisions",
        "INSERT INTO divisions (id, name, lead_contractor) VALUES (?, ?, ?);",
        rows
    )
    # Invalidate query cache
    clear_query_cache()
    return {"status": "success", "message": f"Successfully updated {len(divisions)} divisions."}

@router.put("/regulatory")
def update_regulatory_kb(regulatory_kb: List[RegulatoryKb]):
    rows = [(r.code, r.description, r.trigger_condition.value) for r in regulatory_kb]
    execute_bulk_update(
        "regulatory_kb",
        "INSERT INTO regulatory_kb (code, description, trigger_condition) VALUES (?, ?, ?);",
        rows
    )
    # Invalidate query cache
    clear_query_cache()
    return {"status": "success", "message": f"Successfully updated {len(regulatory_kb)} regulatory rules."}

@router.put("/tasks")
def update_schedule_tasks(tasks: List[ScheduleTask]):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Validate division references
    cursor.execute("SELECT id FROM divisions;")
    division_ids = {row["id"] for row in cursor.fetchall()}
    conn.close()

    task_ids = {t.task_id for t in tasks}

    # Verify every division_id exists
    for t in tasks:
        if t.division_id not in division_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Division '{t.division_id}' referenced by task '{t.task_name}' ({t.task_id}) does not exist."
            )

    # Verify dependencies exist and check for cycles
    adj = {}
    for t in tasks:
        deps = [d.strip() for d in t.dependencies.split(",") if d.strip()]
        for dep in deps:
            if dep not in task_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task '{t.task_name}' ({t.task_id}) references non-existent dependency task '{dep}'."
                )
        adj[t.task_id] = deps

    # DFS Cycle Detection
    visited = set()
    rec_stack = set()

    def has_cycle(node):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in adj:
        if node not in visited:
            if has_cycle(node):
                raise HTTPException(
                    status_code=400,
                    detail="Dependency cycle detected in schedule tasks. Circular dependencies are not allowed."
                )

    rows = [(t.task_id, t.division_id, t.task_name, t.duration, t.is_critical_path, t.dependencies) for t in tasks]
    execute_bulk_update(
        "schedule_tasks",
        "INSERT INTO schedule_tasks (task_id, division_id, task_name, duration, is_critical_path, dependencies) VALUES (?, ?, ?, ?, ?, ?);",
        rows
    )
    # Invalidate query cache
    clear_query_cache()
    return {"status": "success", "message": f"Successfully updated {len(tasks)} tasks."}

