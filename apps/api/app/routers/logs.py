from fastapi import APIRouter, HTTPException

from app.models.placeholders import PlaceholderResponse
from app.models.workflow_logs import (
    WorkflowRunFailureRequest,
    WorkflowRunLog,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.models.workflow_steps import WorkflowStepEvent
from app.services.workflow_logs import (
    get_recent_workflow_runs,
    list_workflow_runs,
    mark_workflow_failure,
    mark_workflow_success,
    start_workflow_run,
)
from app.services.workflow_steps import (
    list_step_events,
    list_step_events_by_workflow_run_id,
)

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("")
def list_logs() -> list[WorkflowRunLog]:
    return list_workflow_runs()


@router.get("/recent")
def list_recent_logs() -> list[WorkflowRunLog]:
    return get_recent_workflow_runs()


@router.get("/workflow-steps")
def list_workflow_step_events() -> list[WorkflowStepEvent]:
    return list_step_events()


@router.get("/workflow-steps/{workflow_run_id}")
def list_workflow_step_events_for_run(
    workflow_run_id: str,
) -> list[WorkflowStepEvent]:
    return list_step_events_by_workflow_run_id(workflow_run_id)


@router.post("/workflow-run")
def create_workflow_run(request: WorkflowRunStartRequest) -> WorkflowRunLog:
    return start_workflow_run(request)


@router.post("/workflow-run/{workflow_run_id}/success")
def complete_workflow_run(
    workflow_run_id: str, request: WorkflowRunSuccessRequest
) -> WorkflowRunLog:
    try:
        return mark_workflow_success(workflow_run_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/workflow-run/{workflow_run_id}/failure")
def fail_workflow_run(
    workflow_run_id: str, request: WorkflowRunFailureRequest
) -> WorkflowRunLog:
    try:
        return mark_workflow_failure(workflow_run_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/ai-action")
def create_ai_action_log() -> PlaceholderResponse:
    return PlaceholderResponse(endpoint="POST /logs/ai-action")
