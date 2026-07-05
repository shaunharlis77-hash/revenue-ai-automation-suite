from typing import Literal

from pydantic import BaseModel, Field


StepStatus = Literal["started", "success", "failed", "skipped"]
StepSeverity = Literal["info", "warning", "error", "critical"]


class WorkflowStepEvent(BaseModel):
    id: int | None = None
    step_event_id: str
    workflow_run_id: str
    workflow_name: str
    step_name: str
    step_status: StepStatus
    step_order: int | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    severity: StepSeverity = "info"
    error_type: str | None = None
    error_message: str | None = None
    failure_reason: str | None = None
    retryable: bool = False
    recommended_fix: str | None = None
    created_at: str
    metadata_json: dict = Field(default_factory=dict)

