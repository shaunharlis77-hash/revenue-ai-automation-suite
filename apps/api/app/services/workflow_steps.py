from datetime import datetime, timezone
from uuid import uuid4

from app.models.workflow_steps import StepSeverity, WorkflowStepEvent
from app.services.database import decode_json, encode_json, get_connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_step_started(
    workflow_run_id: str,
    workflow_name: str,
    step_name: str,
    step_order: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata_json: dict | None = None,
) -> WorkflowStepEvent | None:
    timestamp = utc_now()
    return create_step_event(
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        step_name=step_name,
        step_status="started",
        step_order=step_order,
        entity_type=entity_type,
        entity_id=entity_id,
        started_at=timestamp,
        severity="info",
        metadata_json=metadata_json or {},
    )


def log_step_success(
    workflow_run_id: str,
    workflow_name: str,
    step_name: str,
    step_order: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata_json: dict | None = None,
) -> WorkflowStepEvent | None:
    timestamp = utc_now()
    return create_step_event(
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        step_name=step_name,
        step_status="success",
        step_order=step_order,
        entity_type=entity_type,
        entity_id=entity_id,
        started_at=timestamp,
        completed_at=timestamp,
        duration_ms=0,
        severity="info",
        metadata_json=metadata_json or {},
    )


def log_step_failure(
    workflow_run_id: str,
    workflow_name: str,
    step_name: str,
    error: Exception | str,
    step_order: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    failure_reason: str | None = None,
    retryable: bool = False,
    recommended_fix: str | None = None,
    severity: StepSeverity = "error",
    metadata_json: dict | None = None,
) -> WorkflowStepEvent | None:
    timestamp = utc_now()
    error_message = str(error)
    error_type = type(error).__name__ if isinstance(error, Exception) else "Error"
    event = create_step_event(
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        step_name=step_name,
        step_status="failed",
        step_order=step_order,
        entity_type=entity_type,
        entity_id=entity_id,
        started_at=timestamp,
        completed_at=timestamp,
        duration_ms=0,
        severity=severity,
        error_type=error_type,
        error_message=error_message,
        failure_reason=failure_reason or error_message,
        retryable=retryable,
        recommended_fix=recommended_fix
        or "Check the workflow input, database availability, and related audit or review write path.",
        metadata_json=metadata_json or {},
    )
    if event is not None:
        try:
            from app.services.notifications import handle_failed_step_event

            handle_failed_step_event(event)
        except Exception:
            pass
    return event


def log_step_skipped(
    workflow_run_id: str,
    workflow_name: str,
    step_name: str,
    reason: str,
    step_order: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata_json: dict | None = None,
) -> WorkflowStepEvent | None:
    timestamp = utc_now()
    return create_step_event(
        workflow_run_id=workflow_run_id,
        workflow_name=workflow_name,
        step_name=step_name,
        step_status="skipped",
        step_order=step_order,
        entity_type=entity_type,
        entity_id=entity_id,
        started_at=timestamp,
        completed_at=timestamp,
        duration_ms=0,
        severity="warning",
        failure_reason=reason,
        metadata_json=metadata_json or {},
    )


def list_step_events() -> list[WorkflowStepEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM workflow_step_events ORDER BY id ASC"
        ).fetchall()
    return [step_event_from_row(row) for row in rows]


def list_step_events_by_workflow_run_id(
    workflow_run_id: str,
) -> list[WorkflowStepEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM workflow_step_events
            WHERE workflow_run_id = ?
            ORDER BY id ASC
            """,
            (workflow_run_id,),
        ).fetchall()
    return [step_event_from_row(row) for row in rows]


def create_step_event(**values) -> WorkflowStepEvent | None:
    step_event_id = str(uuid4())
    created_at = utc_now()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO workflow_step_events (
                    step_event_id, workflow_run_id, workflow_name, step_name,
                    step_status, step_order, entity_type, entity_id, started_at,
                    completed_at, duration_ms, severity, error_type,
                    error_message, failure_reason, retryable, recommended_fix,
                    created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_event_id,
                    values["workflow_run_id"],
                    values["workflow_name"],
                    values["step_name"],
                    values["step_status"],
                    values.get("step_order"),
                    values.get("entity_type"),
                    values.get("entity_id"),
                    values.get("started_at"),
                    values.get("completed_at"),
                    values.get("duration_ms"),
                    values.get("severity", "info"),
                    values.get("error_type"),
                    values.get("error_message"),
                    values.get("failure_reason"),
                    int(values.get("retryable", False)),
                    values.get("recommended_fix"),
                    created_at,
                    encode_json(values.get("metadata_json", {})),
                ),
            )
            connection.commit()
    except Exception:
        return None

    return WorkflowStepEvent(
        step_event_id=step_event_id,
        created_at=created_at,
        **values,
    )


def step_event_from_row(row) -> WorkflowStepEvent:
    return WorkflowStepEvent(
        id=row["id"],
        step_event_id=row["step_event_id"],
        workflow_run_id=row["workflow_run_id"],
        workflow_name=row["workflow_name"],
        step_name=row["step_name"],
        step_status=row["step_status"],
        step_order=row["step_order"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        duration_ms=row["duration_ms"],
        severity=row["severity"],
        error_type=row["error_type"],
        error_message=row["error_message"],
        failure_reason=row["failure_reason"],
        retryable=bool(row["retryable"]),
        recommended_fix=row["recommended_fix"],
        created_at=row["created_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )
