from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from backend.agents.event_types import EventType

class ProjectMeta(BaseModel):
    name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    total_budget: float = Field(..., description="Total project budget, must be non-negative")
    spent_to_date: float = Field(..., description="Spent to date, must be non-negative")

    @field_validator("total_budget", "spent_to_date")
    @classmethod
    def check_non_negative_floats(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Value must be non-negative")
        return value

class Contractor(BaseModel):
    name: str = Field(..., min_length=1)
    scope: str
    daily_operating_cost: float = Field(..., description="Daily operating cost, must be non-negative")
    daily_delay_penalty: float = Field(..., description="Daily delay penalty, must be non-negative")
    active_workers: int = Field(..., description="Active workers count, must be non-negative")

    @field_validator("daily_operating_cost", "daily_delay_penalty")
    @classmethod
    def check_non_negative_costs(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Cost must be non-negative")
        return value

    @field_validator("active_workers")
    @classmethod
    def check_non_negative_workers(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Workers count must be non-negative")
        return value

class Division(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    lead_contractor: str = Field(..., min_length=1)

class RegulatoryKb(BaseModel):
    code: str = Field(..., min_length=1)
    description: str
    trigger_condition: EventType

class ScheduleTask(BaseModel):
    task_id: str = Field(..., min_length=1)
    division_id: str = Field(..., min_length=1)
    task_name: str = Field(..., min_length=1)
    duration: int = Field(..., description="Task duration in days, must be non-negative")
    is_critical_path: int = Field(..., description="Is critical path, must be 0 or 1")
    dependencies: str = Field("", description="Comma-separated list of dependent task IDs")

    @field_validator("duration")
    @classmethod
    def check_non_negative_duration(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Duration must be non-negative")
        return value

    @field_validator("is_critical_path")
    @classmethod
    def check_is_critical_path_binary(cls, value: int) -> int:
        if value not in (0, 1):
            raise ValueError("is_critical_path must be 0 or 1")
        return value

class ProjectSetupState(BaseModel):
    project_meta: ProjectMeta
    contractors: List[Contractor]
    divisions: List[Division]
    regulatory_kb: List[RegulatoryKb]
    schedule_tasks: List[ScheduleTask]
