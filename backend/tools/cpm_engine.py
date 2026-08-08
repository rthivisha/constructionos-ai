import os
import json
import sqlite3
import logging
import warnings
from typing import Tuple, List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Locate DB and seed files relative to this file
# This file is located at: backend/tools/cpm_engine.py
# Database is at: backend/constructionos.db
# Seed JSON is at: backend/mock_data/seed_project_state.json
import backend.db

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
SEED_PATH = os.path.join(BACKEND_DIR, "mock_data", "seed_project_state.json")


def get_project_state() -> Tuple[Dict[str, Any], bool]:
    """
    Retrieves the project state from the SQLite database.
    If the database is missing, empty, or fails to connect,
    it falls back to seed_project_state.json and logs/prints a visible warning.
    
    Returns:
        Tuple[project_state_dict, fallback_mode_active]
    """
    fallback_mode_active = False
    db_ok = False

    # Check if database exists and has tasks
    if os.path.exists(backend.db.DB_PATH):
        try:
            conn = sqlite3.connect(backend.db.DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Simple check to see if database has tables and rows
            cursor.execute("SELECT COUNT(*) FROM schedule_tasks;")
            count = cursor.fetchone()[0]
            if count > 0:
                db_ok = True
            conn.close()
        except Exception:
            db_ok = False

    if db_ok:
        try:
            conn = sqlite3.connect(backend.db.DB_PATH)

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch tasks
            cursor.execute("SELECT task_id, division_id, task_name, duration, is_critical_path, dependencies FROM schedule_tasks;")
            tasks = [dict(row) for row in cursor.fetchall()]
            
            # Fetch divisions
            cursor.execute("SELECT id, name, lead_contractor FROM divisions;")
            divisions = [dict(row) for row in cursor.fetchall()]
            
            # Fetch contractors
            cursor.execute("SELECT name, scope, daily_operating_cost, daily_delay_penalty, active_workers FROM contractors;")
            contractors = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return {
                "schedule_tasks": tasks,
                "divisions": divisions,
                "contractors": contractors
            }, False
        except Exception as e:
            logger.warning(f"Error querying SQLite database: {e}. Falling back to JSON.")
            db_ok = False

    # Fallback to seed_project_state.json
    fallback_mode_active = True
    warning_msg = (
        "WARNING: SQLite database not found or empty. Falling back to seed_project_state.json. "
        "Live edits from the setup page will be ignored!"
    )
    print(warning_msg)
    logger.warning(warning_msg)
    warnings.warn(warning_msg, RuntimeWarning)

    if os.path.exists(SEED_PATH):
        try:
            with open(SEED_PATH, "r") as f:
                data = json.load(f)
                return data, True
        except Exception as e:
            raise FileNotFoundError(f"Failed to read seed JSON file from {SEED_PATH}: {e}")
    else:
        raise FileNotFoundError(f"Neither SQLite database nor seed JSON file was found at {SEED_PATH}")

def get_task_impact(task_name: str) -> Dict[str, Any]:
    """
    Looks up task_name in the project state (via divisions and contractors)
    and returns its crew assignment, daily cost, penalty rate, and critical path status.
    
    Args:
        task_name: The name of the task to query.
        
    Returns:
        A dictionary containing assigned_crew, daily_operating_cost, contractor_penalty_rate,
        critical_path status, and fallback_mode_active flag.
    """
    state, fallback_mode_active = get_project_state()
    
    task = None
    # Exact match first
    for t in state.get("schedule_tasks", []):
        if t["task_name"] == task_name:
            task = t
            break
            
    # Case-insensitive/stripped match fallback
    if not task:
        for t in state.get("schedule_tasks", []):
            if t["task_name"].strip().lower() == task_name.strip().lower():
                task = t
                break
                
    if not task:
        raise ValueError(f"Task with name '{task_name}' not found in the project schedule.")

    # Resolve division_id -> divisions.lead_contractor -> contractors.name
    div_id = task["division_id"]
    division = next((d for d in state.get("divisions", []) if d["id"] == div_id), None)
    if not division:
        raise ValueError(f"Division '{div_id}' referenced by task '{task_name}' does not exist.")

    contractor_name = division["lead_contractor"]
    contractor = next((c for c in state.get("contractors", []) if c["name"] == contractor_name), None)
    if not contractor:
        raise ValueError(f"Contractor '{contractor_name}' referenced by division '{div_id}' does not exist.")

    return {
        "assigned_crew": contractor["name"],
        "daily_operating_cost": float(contractor["daily_operating_cost"]),
        "contractor_penalty_rate": float(contractor["daily_delay_penalty"]),
        "critical_path": bool(task["is_critical_path"]),
        "fallback_mode_active": fallback_mode_active
    }

def _parse_deps(dep_str: str) -> List[str]:
    if not dep_str:
        return []
    return [d.strip() for d in dep_str.split(",") if d.strip()]

def _topological_sort(tasks: List[Dict[str, Any]]) -> List[str]:
    adj = {t["task_id"]: [] for t in tasks}
    in_degree = {t["task_id"]: 0 for t in tasks}
    
    for t in tasks:
        tid = t["task_id"]
        deps = _parse_deps(t.get("dependencies", ""))
        for dep in deps:
            if dep in adj:
                adj[dep].append(tid)
                in_degree[tid] += 1
                
    # Kahn's algorithm
    queue = [tid for tid in in_degree if in_degree[tid] == 0]
    order = []
    
    while queue:
        queue.sort()  # deterministic processing order
        u = queue.pop(0)
        order.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if len(order) < len(tasks):
        raise ValueError("Circular dependencies detected in schedule tasks.")
        
    return order

def _run_cpm(tasks: List[Dict[str, Any]], topological_order: List[str], custom_durations: Dict[str, int] = None) -> Tuple[Dict[str, Dict[str, Any]], int]:
    task_map = {t["task_id"]: t for t in tasks}
    
    # Durations mapping
    durations = {}
    for t in tasks:
        tid = t["task_id"]
        if custom_durations and tid in custom_durations:
            durations[tid] = custom_durations[tid]
        else:
            durations[tid] = int(t["duration"])
            
    # Forward Pass
    es = {}
    ef = {}
    for tid in topological_order:
        t = task_map[tid]
        deps = _parse_deps(t.get("dependencies", ""))
        if not deps:
            es[tid] = 0
        else:
            es[tid] = max(ef[dep] for dep in deps)
        ef[tid] = es[tid] + durations[tid]
        
    project_duration = max(ef.values()) if ef else 0
    
    # Backward Pass
    ls = {}
    lf = {}
    for tid in topological_order:
        lf[tid] = project_duration
        
    for tid in reversed(topological_order):
        t = task_map[tid]
        deps = _parse_deps(t.get("dependencies", ""))
        ls[tid] = lf[tid] - durations[tid]
        for dep in deps:
            if dep in lf:
                lf[dep] = min(lf[dep], ls[tid])
                
    # Slack and critical status calculation
    schedule = {}
    for tid in topological_order:
        ls[tid] = lf[tid] - durations[tid]
        slack = lf[tid] - ef[tid]
        schedule[tid] = {
            "task_id": tid,
            "task_name": task_map[tid]["task_name"],
            "duration": durations[tid],
            "early_start": es[tid],
            "early_finish": ef[tid],
            "late_start": ls[tid],
            "late_finish": lf[tid],
            "slack": slack,
            "is_critical": int(slack == 0)
        }
        
    return schedule, project_duration

def recalculate_schedule(halted_task_id: str, delay_days: int) -> Dict[str, Any]:
    """
    Recalculates the master CPM schedule after applying a delay to halted_task_id.
    Computes marginal financial exposure (operating cost + penalties) for shifted and penalized tasks.
    
    Args:
        halted_task_id: The ID of the task experiencing the delay.
        delay_days: Number of days of delay. Must be non-negative.
        
    Returns:
        Structured JSON-like dictionary containing updated CPM schedules, exposures, and breakdown.
    """
    if delay_days < 0:
        raise ValueError("delay_days must be non-negative.")
        
    state, fallback_mode_active = get_project_state()
    tasks = state.get("schedule_tasks", [])
    divisions = state.get("divisions", [])
    contractors = state.get("contractors", [])
    
    # Ensure halted task exists
    halted_task = next((t for t in tasks if t["task_id"] == halted_task_id), None)
    if not halted_task:
        raise ValueError(f"Halted task '{halted_task_id}' not found in the schedule.")
        
    topological_order = _topological_sort(tasks)
    
    # Run Baseline CPM
    baseline_schedule, baseline_duration = _run_cpm(tasks, topological_order)
    
    # Run Delayed CPM
    custom_durations = {t["task_id"]: int(t["duration"]) for t in tasks}
    custom_durations[halted_task_id] += delay_days
    delayed_schedule, delayed_duration = _run_cpm(tasks, topological_order, custom_durations)
    
    # Identify shifted tasks (dates shifted early_start or early_finish)
    # Identify penalized tasks (new early_finish exceeds baseline early_finish)
    shifted_tasks_list = []
    penalized_tasks_list = []
    
    total_operating_cost_daily = 0.0
    total_penalty_exposure = 0.0
    
    # Build details map for contractors
    contractor_map = {c["name"]: c for c in contractors}
    division_map = {d["id"]: d for d in divisions}
    
    for tid in topological_order:
        t = next(task for task in tasks if task["task_id"] == tid)
        base = baseline_schedule[tid]
        delayed = delayed_schedule[tid]
        
        # Resolve contractor info
        div_id = t["division_id"]
        div = division_map.get(div_id)
        if not div:
            raise ValueError(f"Division '{div_id}' for task '{tid}' not found.")
        cname = div["lead_contractor"]
        contractor = contractor_map.get(cname)
        if not contractor:
            raise ValueError(f"Contractor '{cname}' for division '{div_id}' not found.")
            
        daily_operating_cost = float(contractor["daily_operating_cost"])
        daily_delay_penalty = float(contractor["daily_delay_penalty"])
        
        # Check if dates shifted
        is_shifted = (base["early_start"] != delayed["early_start"]) or (base["early_finish"] != delayed["early_finish"])
        if is_shifted:
            total_operating_cost_daily += daily_operating_cost
            shifted_tasks_list.append({
                "task_id": tid,
                "task_name": t["task_name"],
                "contractor": contractor["name"],
                "daily_operating_cost": daily_operating_cost,
                "baseline_start": base["early_start"],
                "baseline_end": base["early_finish"],
                "new_start": delayed["early_start"],
                "new_end": delayed["early_finish"]
            })
            
        # Check if new end date exceeds original end date
        exceeds_end = delayed["early_finish"] > base["early_finish"]
        if exceeds_end:
            task_delay_days = delayed["early_finish"] - base["early_finish"]
            task_penalty = task_delay_days * daily_delay_penalty
            total_penalty_exposure += task_penalty
            penalized_tasks_list.append({
                "task_id": tid,
                "task_name": t["task_name"],
                "contractor": contractor["name"],
                "daily_delay_penalty": daily_delay_penalty,
                "baseline_end": base["early_finish"],
                "new_end": delayed["early_finish"],
                "delay_days": task_delay_days,
                "penalty_exposure": task_penalty
            })
            
    # Calculate marginal operating cost exposure
    operating_cost_exposure = delay_days * total_operating_cost_daily
    total_financial_exposure = operating_cost_exposure + total_penalty_exposure
    
    # Prepare result
    result = {
        "halted_task_id": halted_task_id,
        "delay_days": delay_days,
        "baseline_project_duration": baseline_duration,
        "new_project_duration": delayed_duration,
        "project_delay": delayed_duration - baseline_duration,
        "fallback_mode_active": fallback_mode_active,
        "total_financial_exposure": total_financial_exposure,
        "breakdown": {
            "operating_cost_exposure": operating_cost_exposure,
            "penalty_exposure": total_penalty_exposure,
            "shifted_tasks": shifted_tasks_list,
            "penalized_tasks": penalized_tasks_list
        },
        "tasks": {
            tid: {
                "task_id": tid,
                "task_name": baseline_schedule[tid]["task_name"],
                "baseline": {
                    "start": baseline_schedule[tid]["early_start"],
                    "end": baseline_schedule[tid]["early_finish"],
                    "late_start": baseline_schedule[tid]["late_start"],
                    "late_finish": baseline_schedule[tid]["late_finish"],
                    "slack": baseline_schedule[tid]["slack"],
                    "is_critical": baseline_schedule[tid]["is_critical"]
                },
                "delayed": {
                    "start": delayed_schedule[tid]["early_start"],
                    "end": delayed_schedule[tid]["early_finish"],
                    "late_start": delayed_schedule[tid]["late_start"],
                    "late_finish": delayed_schedule[tid]["late_finish"],
                    "slack": delayed_schedule[tid]["slack"],
                    "is_critical": delayed_schedule[tid]["is_critical"]
                }
            } for tid in topological_order
        }
    }
    
    return result
