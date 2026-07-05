from datetime import datetime, timezone
from uuid import uuid4

from app.models.audit import AuditEvent, AuditEventCreate
from app.services.database import decode_json, encode_json, get_connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_audit_event(event: AuditEventCreate) -> AuditEvent:
    event_id = str(uuid4())
    created_at = utc_now()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, workflow_run_id, workflow_name, entity_type, entity_id,
                    event_type, event_source, actor, input_reference, output_reference,
                    guardrails_triggered, human_review_required, decision,
                    decision_reason, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event.workflow_run_id,
                    event.workflow_name,
                    event.entity_type,
                    event.entity_id,
                    event.event_type,
                    event.event_source,
                    event.actor,
                    event.input_reference,
                    event.output_reference,
                    encode_json(event.guardrails_triggered),
                    int(event.human_review_required),
                    event.decision,
                    event.decision_reason,
                    created_at,
                    encode_json(event.metadata_json),
                ),
            )
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"failed to create audit event: {error}") from error

    return get_audit_event(event_id)


def list_audit_events() -> list[AuditEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY id ASC"
        ).fetchall()
    return [audit_event_from_row(row) for row in rows]


def get_audit_event(event_id: str) -> AuditEvent:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"audit event not found: {event_id}")
    return audit_event_from_row(row)


def audit_event_from_row(row) -> AuditEvent:
    return AuditEvent(
        id=row["id"],
        event_id=row["event_id"],
        workflow_run_id=row["workflow_run_id"],
        workflow_name=row["workflow_name"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        event_type=row["event_type"],
        event_source=row["event_source"],
        actor=row["actor"],
        input_reference=row["input_reference"],
        output_reference=row["output_reference"],
        guardrails_triggered=decode_json(row["guardrails_triggered"], []),
        human_review_required=bool(row["human_review_required"]),
        decision=row["decision"],
        decision_reason=row["decision_reason"],
        created_at=row["created_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )
