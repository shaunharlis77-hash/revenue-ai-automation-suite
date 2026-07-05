from typing import Literal

from pydantic import BaseModel


WorkflowStatus = Literal["started", "success", "failed"]


class WorkflowRunLog(BaseModel):
    workflow_run_id: str
    workflow_name: str
    status: WorkflowStatus
    started_at: str
    completed_at: str | None = None
    failed_at: str | None = None
    failure_step: str | None = None
    failure_reason: str | None = None
    input_reference: str | None = None
    output_summary: str | None = None
    human_review_required: bool = False
    next_action: str | None = None
    created_at: str


class WorkflowRunStartRequest(BaseModel):
    workflow_name: str
    input_reference: str | None = None


class WorkflowRunSuccessRequest(BaseModel):
    output_summary: str
    human_review_required: bool = False
    next_action: str | None = None


class WorkflowRunFailureRequest(BaseModel):
    failure_step: str
    failure_reason: str
    input_reference: str | None = None
    human_review_required: bool = True
    next_action: str | None = "Review the failed workflow run."


class WorkflowMetricsResponse(BaseModel):
    total_workflow_runs: int
    successful_runs: int
    failed_runs: int
    human_review_required_count: int
    runs_by_workflow_name: dict[str, int]
    recent_failures: list[WorkflowRunLog]
