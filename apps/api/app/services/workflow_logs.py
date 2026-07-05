from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from app.models.workflow_logs import (
    WorkflowMetricsResponse,
    WorkflowRunFailureRequest,
    WorkflowRunLog,
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.database import encode_json, get_connection


_workflow_runs: list[WorkflowRunLog] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_workflow_run(request: WorkflowRunStartRequest) -> WorkflowRunLog:
    timestamp = utc_now()
    run = WorkflowRunLog(
        workflow_run_id=str(uuid4()),
        workflow_name=request.workflow_name,
        status="started",
        started_at=timestamp,
        input_reference=request.input_reference,
        created_at=timestamp,
    )
    _workflow_runs.append(run)
    persist_workflow_run(run)
    return run


def mark_workflow_success(
    workflow_run_id: str, request: WorkflowRunSuccessRequest
) -> WorkflowRunLog:
    run = find_workflow_run(workflow_run_id)
    run.status = "success"
    run.completed_at = utc_now()
    run.failed_at = None
    run.failure_step = None
    run.failure_reason = None
    run.output_summary = request.output_summary
    run.human_review_required = request.human_review_required
    run.next_action = request.next_action
    persist_workflow_run_update(run)
    return run


def mark_workflow_failure(
    workflow_run_id: str, request: WorkflowRunFailureRequest
) -> WorkflowRunLog:
    run = find_workflow_run(workflow_run_id)
    run.status = "failed"
    run.completed_at = None
    run.failed_at = utc_now()
    run.failure_step = request.failure_step
    run.failure_reason = request.failure_reason
    if request.input_reference is not None:
        run.input_reference = request.input_reference
    run.human_review_required = request.human_review_required
    run.next_action = request.next_action
    persist_workflow_run_update(run)
    return run


def list_workflow_runs() -> list[WorkflowRunLog]:
    return list(_workflow_runs)


def get_recent_workflow_runs(limit: int = 10) -> list[WorkflowRunLog]:
    return list(reversed(_workflow_runs[-limit:]))


def get_workflow_metrics() -> WorkflowMetricsResponse:
    runs_by_workflow = Counter(run.workflow_name for run in _workflow_runs)
    recent_failures = [
        run for run in reversed(_workflow_runs) if run.status == "failed"
    ][:5]

    return WorkflowMetricsResponse(
        total_workflow_runs=len(_workflow_runs),
        successful_runs=sum(1 for run in _workflow_runs if run.status == "success"),
        failed_runs=sum(1 for run in _workflow_runs if run.status == "failed"),
        human_review_required_count=sum(
            1 for run in _workflow_runs if run.human_review_required
        ),
        runs_by_workflow_name=dict(runs_by_workflow),
        recent_failures=recent_failures,
    )


def reset_workflow_runs() -> None:
    _workflow_runs.clear()
    with get_connection() as connection:
        connection.execute("DELETE FROM workflow_step_events")
        connection.execute("DELETE FROM workflow_runs")
        connection.commit()


def find_workflow_run(workflow_run_id: str) -> WorkflowRunLog:
    for run in _workflow_runs:
        if run.workflow_run_id == workflow_run_id:
            return run
    raise ValueError(f"workflow run not found: {workflow_run_id}")


def persist_workflow_run(run: WorkflowRunLog) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO workflow_runs (
                    workflow_run_id, workflow_name, status, input_reference,
                    output_summary, human_review_required, next_action,
                    started_at, completed_at, failed_at, failure_step,
                    failure_reason, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                workflow_run_values(run),
            )
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"failed to persist workflow run: {error}") from error


def persist_workflow_run_update(run: WorkflowRunLog) -> None:
    persist_workflow_run(run)


def workflow_run_values(run: WorkflowRunLog) -> tuple:
    return (
        run.workflow_run_id,
        run.workflow_name,
        run.status,
        run.input_reference,
        run.output_summary,
        int(run.human_review_required),
        run.next_action,
        run.started_at,
        run.completed_at,
        run.failed_at,
        run.failure_step,
        run.failure_reason,
        run.created_at,
        encode_json({}),
    )
