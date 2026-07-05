from datetime import datetime, timezone
from uuid import uuid4

from app.models.audit import AuditEventCreate
from app.models.review_queue import (
    ReviewDecisionRequest,
    ReviewItem,
    ReviewItemCreate,
)
from app.services.audit_trail import create_audit_event
from app.services.database import decode_json, encode_json, get_connection
from app.services.workflow_steps import (
    log_step_failure,
    log_step_started,
    log_step_success,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_review_item(request: ReviewItemCreate) -> ReviewItem:
    review_item_id = str(uuid4())
    timestamp = utc_now()

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO review_items (
                    review_item_id, workflow_run_id, workflow_name, entity_type,
                    entity_id, company, contact_name, review_type, title, status,
                    priority, risk_level, review_reasons, proposed_action,
                    proposed_output, assigned_to, created_at, updated_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_item_id,
                    request.workflow_run_id,
                    request.workflow_name,
                    request.entity_type,
                    request.entity_id,
                    request.company,
                    request.contact_name,
                    request.review_type,
                    request.title,
                    "pending",
                    request.priority,
                    request.risk_level,
                    encode_json(request.review_reasons),
                    request.proposed_action,
                    request.proposed_output,
                    request.assigned_to,
                    timestamp,
                    timestamp,
                    encode_json(request.metadata_json),
                ),
            )
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"failed to create review item: {error}") from error

    item = get_review_item(review_item_id)
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=item.workflow_run_id,
            workflow_name=item.workflow_name,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            event_type="review_created",
            event_source="review_queue",
            actor="system",
            output_reference=item.review_item_id,
            guardrails_triggered=item.review_reasons,
            human_review_required=True,
            metadata_json={"review_type": item.review_type},
        )
    )
    return item


def list_review_items() -> list[ReviewItem]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM review_items ORDER BY id ASC"
        ).fetchall()
    return [review_item_from_row(row) for row in rows]


def get_review_item(review_item_id: str) -> ReviewItem:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM review_items WHERE review_item_id = ?",
            (review_item_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"review item not found: {review_item_id}")
    return review_item_from_row(row)


def approve_review_item(
    review_item_id: str, request: ReviewDecisionRequest
) -> ReviewItem:
    return decide_review_item(review_item_id, "approved", request)


def reject_review_item(
    review_item_id: str, request: ReviewDecisionRequest
) -> ReviewItem:
    return decide_review_item(review_item_id, "rejected", request)


def decide_review_item(
    review_item_id: str, decision: str, request: ReviewDecisionRequest
) -> ReviewItem:
    timestamp = utc_now()
    workflow_run_id = f"review_decision:{review_item_id}"
    workflow_name = "review_queue"
    entity_type = "review_item"
    entity_id = review_item_id

    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM review_items WHERE review_item_id = ?",
                (review_item_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"review item not found: {review_item_id}")

            workflow_run_id = row["workflow_run_id"] or workflow_run_id
            workflow_name = row["workflow_name"]
            entity_type = row["entity_type"]
            entity_id = row["entity_id"]
            log_step_started(
                workflow_run_id,
                workflow_name,
                "review_decision_started",
                1,
                entity_type,
                entity_id,
                {"review_item_id": review_item_id, "decision": decision},
            )
            log_step_success(
                workflow_run_id,
                workflow_name,
                "review_item_loaded",
                2,
                entity_type,
                entity_id,
                {"review_item_id": review_item_id},
            )

            connection.execute(
                """
                UPDATE review_items
                SET status = ?, decision = ?, decision_reason = ?, updated_at = ?
                WHERE review_item_id = ?
                """,
                (
                    decision,
                    decision,
                    request.decision_reason,
                    timestamp,
                    review_item_id,
                ),
            )
            connection.commit()
            log_step_success(
                workflow_run_id,
                workflow_name,
                "review_item_status_updated",
                3,
                entity_type,
                entity_id,
                {"review_item_id": review_item_id, "decision": decision},
            )
    except ValueError:
        raise
    except Exception as error:
        log_step_failure(
            workflow_run_id,
            workflow_name,
            "review_item_status_updated",
            error,
            entity_type=entity_type,
            entity_id=entity_id,
            failure_reason=str(error),
            retryable=True,
            recommended_fix="Check database availability and the review item status update path.",
            metadata_json={"review_item_id": review_item_id, "decision": decision},
        )
        raise RuntimeError(f"failed to update review item: {error}") from error

    item = get_review_item(review_item_id)
    try:
        create_audit_event(
            AuditEventCreate(
                workflow_run_id=item.workflow_run_id,
                workflow_name=item.workflow_name,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                event_type="review_approved" if decision == "approved" else "review_rejected",
                event_source="review_queue",
                actor=request.actor,
                output_reference=item.review_item_id,
                guardrails_triggered=item.review_reasons,
                human_review_required=False,
                decision=decision,
                decision_reason=request.decision_reason,
                metadata_json={"review_type": item.review_type},
            )
        )
        log_step_success(
            workflow_run_id,
            workflow_name,
            "audit_event_written",
            4,
            entity_type,
            entity_id,
            {"review_item_id": review_item_id, "decision": decision},
        )
        log_step_success(
            workflow_run_id,
            workflow_name,
            "review_decision_completed",
            5,
            entity_type,
            entity_id,
            {"review_item_id": review_item_id, "decision": decision},
        )
    except Exception as error:
        log_step_failure(
            workflow_run_id,
            workflow_name,
            "audit_event_written",
            error,
            entity_type=entity_type,
            entity_id=entity_id,
            failure_reason=str(error),
            retryable=True,
            recommended_fix="Check audit event persistence for review decisions.",
            metadata_json={"review_item_id": review_item_id, "decision": decision},
        )
        raise
    return item


def review_item_from_row(row) -> ReviewItem:
    return ReviewItem(
        id=row["id"],
        review_item_id=row["review_item_id"],
        workflow_run_id=row["workflow_run_id"],
        workflow_name=row["workflow_name"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        company=row["company"],
        contact_name=row["contact_name"],
        review_type=row["review_type"],
        title=row["title"],
        status=row["status"],
        priority=row["priority"],
        risk_level=row["risk_level"],
        review_reasons=decode_json(row["review_reasons"], []),
        proposed_action=row["proposed_action"],
        proposed_output=row["proposed_output"],
        decision=row["decision"],
        decision_reason=row["decision_reason"],
        assigned_to=row["assigned_to"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )
