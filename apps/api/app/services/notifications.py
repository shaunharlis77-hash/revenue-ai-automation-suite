from datetime import datetime, timezone
from uuid import uuid4
from urllib import request as url_request
import json

from app.config.settings import get_settings
from app.models.audit import AuditEventCreate
from app.models.notifications import NotificationEvent
from app.models.review_queue import ReviewItem
from app.models.workflow_steps import WorkflowStepEvent
from app.services.audit_trail import create_audit_event
from app.services.database import decode_json, encode_json, get_connection


WORKFLOW_NAME = "notifications"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def handle_failed_step_event(event: WorkflowStepEvent) -> NotificationEvent | None:
    settings = get_settings()
    if not settings.notifications_enabled:
        return None

    payload = safe_payload_from_step(event)
    notification = create_and_route_notification(payload)
    log_notification_attempt_step(notification, "failure_notification_attempted")
    return notification


def create_review_notification(item: ReviewItem) -> NotificationEvent | None:
    settings = get_settings()
    if not settings.notifications_enabled:
        return None

    payload = safe_payload_from_review_item(item)
    notification = create_and_route_notification(payload)
    create_review_notification_audit(item, notification)
    log_notification_attempt_step(notification, "review_notification_create")
    return notification


def list_notification_events() -> list[NotificationEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM notification_events ORDER BY id ASC"
        ).fetchall()
    return [notification_from_row(row) for row in rows]


def recent_notification_events(limit: int = 20) -> list[NotificationEvent]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM notification_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [notification_from_row(row) for row in rows]


def create_notification_event(
    payload: dict,
    delivery_status: str,
    webhook_configured: bool,
) -> NotificationEvent:
    notification_id = payload["notification_id"]
    created_at = utc_now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO notification_events (
                notification_id, notification_type, workflow_run_id, workflow_name, step_name,
                severity, error_type, safe_error_message, retryable,
                recommended_fix, entity_type, entity_id, crm_record_id,
                review_item_id, recipient_role, recipient_id, recipient_name,
                recipient_email, routed_owner_id, routed_owner_name,
                manager_fallback_used, title, message, recommended_action,
                delivery_status, webhook_configured, created_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                payload["notification_type"],
                payload["workflow_run_id"],
                payload["workflow_name"],
                payload.get("step_name"),
                payload["severity"],
                payload.get("error_type"),
                payload.get("safe_error_message"),
                int(payload.get("retryable", False)),
                payload.get("recommended_fix"),
                payload.get("entity_type"),
                payload.get("entity_id"),
                payload.get("crm_record_id"),
                payload.get("review_item_id"),
                payload["recipient_role"],
                payload.get("recipient_id"),
                payload.get("recipient_name"),
                payload.get("recipient_email"),
                payload.get("routed_owner_id"),
                payload.get("routed_owner_name"),
                int(payload.get("manager_fallback_used", False)),
                payload["title"],
                payload["message"],
                payload.get("recommended_action"),
                delivery_status,
                int(webhook_configured),
                created_at,
                encode_json(payload.get("metadata_json", {})),
            ),
        )
        connection.commit()
    return NotificationEvent(
        notification_id=notification_id,
        notification_type=payload["notification_type"],
        workflow_run_id=payload["workflow_run_id"],
        workflow_name=payload["workflow_name"],
        step_name=payload.get("step_name"),
        severity=payload["severity"],
        error_type=payload.get("error_type"),
        safe_error_message=payload.get("safe_error_message"),
        retryable=bool(payload.get("retryable", False)),
        recommended_fix=payload.get("recommended_fix"),
        entity_type=payload.get("entity_type"),
        entity_id=payload.get("entity_id"),
        crm_record_id=payload.get("crm_record_id"),
        review_item_id=payload.get("review_item_id"),
        recipient_role=payload["recipient_role"],
        recipient_id=payload.get("recipient_id"),
        recipient_name=payload.get("recipient_name"),
        recipient_email=payload.get("recipient_email"),
        routed_owner_id=payload.get("routed_owner_id"),
        routed_owner_name=payload.get("routed_owner_name"),
        manager_fallback_used=bool(payload.get("manager_fallback_used", False)),
        title=payload["title"],
        message=payload["message"],
        recommended_action=payload.get("recommended_action"),
        delivery_status=delivery_status,
        webhook_configured=webhook_configured,
        created_at=created_at,
        metadata_json=payload.get("metadata_json", {}),
    )


def safe_payload_from_step(event: WorkflowStepEvent) -> dict:
    return {
        "notification_id": f"notification_{uuid4()}",
        "notification_type": "workflow_step_failed",
        "workflow_run_id": event.workflow_run_id,
        "workflow_name": event.workflow_name,
        "step_name": event.step_name,
        "severity": event.severity,
        "error_type": event.error_type,
        "safe_error_message": scrub_secret_text(event.error_message or ""),
        "retryable": event.retryable,
        "recommended_fix": scrub_secret_text(event.recommended_fix or ""),
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "crm_record_id": str(event.metadata_json.get("crm_record_id") or "")
        if event.metadata_json
        else None,
        "review_item_id": str(event.metadata_json.get("review_item_id") or "")
        if event.metadata_json
        else None,
        "recipient_role": "admin_ops",
        "manager_fallback_used": False,
        "title": f"Workflow step failed: {event.step_name}",
        "message": scrub_secret_text(
            f"{event.workflow_name} failed at {event.step_name}: {event.failure_reason or event.error_message or 'No safe detail provided.'}"
        ),
        "recommended_action": scrub_secret_text(
            event.recommended_fix
            or "Review operational logs and retry only after the failure is understood."
        ),
        "created_at": event.created_at,
        "metadata_json": {"source": "workflow_step_event"},
    }


def safe_payload_from_review_item(item: ReviewItem) -> dict:
    metadata = item.metadata_json or {}
    owner_id = text(metadata.get("assigned_owner_id") or metadata.get("routed_owner_id"))
    owner_name = text(
        metadata.get("assigned_owner_name")
        or metadata.get("routed_owner_name")
        or item.assigned_to
    )
    owner_email = text(metadata.get("assigned_owner_email") or metadata.get("routed_owner_email"))
    has_owner = bool(owner_id or owner_name or owner_email or item.assigned_to)
    risky_without_owner = item.risk_level in {"high", "critical"} and not has_owner

    if has_owner:
        notification_type = "review_required"
        recipient_role = "assigned_owner" if owner_id or owner_name else "routed_rep"
        manager_fallback_used = False
    else:
        notification_type = "review_assignment_needed"
        recipient_role = "manager"
        manager_fallback_used = True

    title = review_title(item, manager_fallback_used)
    message = review_message(item, manager_fallback_used)
    recommended_action = (
        "Assign an owner and review the blocked update."
        if manager_fallback_used and risky_without_owner
        else "Review and approve, reject, or request edits."
    )
    return {
        "notification_id": f"notification_{uuid4()}",
        "notification_type": notification_type,
        "workflow_run_id": item.workflow_run_id or f"review:{item.review_item_id}",
        "workflow_name": item.workflow_name,
        "step_name": "review_notification_create",
        "severity": "warning" if manager_fallback_used or item.risk_level in {"high", "critical"} else "info",
        "error_type": None,
        "safe_error_message": None,
        "retryable": False,
        "recommended_fix": None,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "crm_record_id": text(metadata.get("crm_record_id")),
        "review_item_id": item.review_item_id,
        "recipient_role": recipient_role,
        "recipient_id": owner_id or None,
        "recipient_name": owner_name or None,
        "recipient_email": owner_email or None,
        "routed_owner_id": owner_id or None,
        "routed_owner_name": owner_name or None,
        "manager_fallback_used": manager_fallback_used,
        "title": title,
        "message": message,
        "recommended_action": recommended_action,
        "metadata_json": {
            "source": "review_queue",
            "review_type": item.review_type,
            "priority": item.priority,
            "risk_level": item.risk_level,
            "manager_fallback_used": manager_fallback_used,
        },
    }


def create_and_route_notification(payload: dict) -> NotificationEvent:
    settings = get_settings()
    webhook_configured = bool(settings.n8n_failure_webhook_url.strip())
    delivery_status = "queued_no_webhook"
    if webhook_configured:
        try:
            post_webhook(settings.n8n_failure_webhook_url, external_payload(payload))
            delivery_status = "sent"
        except Exception as error:
            delivery_status = "failed"
            payload.setdefault("metadata_json", {})["webhook_failure_reason"] = safe_error(error)
    return create_notification_event(
        payload=payload,
        delivery_status=delivery_status,
        webhook_configured=webhook_configured,
    )


def post_webhook(url: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    request = url_request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with url_request.urlopen(request, timeout=5) as response:
        if response.status >= 400:
            raise RuntimeError(f"notification webhook failed with status {response.status}")


def create_review_notification_audit(item: ReviewItem, notification: NotificationEvent) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=item.workflow_run_id,
            workflow_name=item.workflow_name,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            event_type="manager_fallback_notification_created"
            if notification.manager_fallback_used
            else "review_notification_created",
            event_source="notifications",
            actor="system",
            output_reference=notification.notification_id,
            guardrails_triggered=item.review_reasons,
            human_review_required=True,
            metadata_json={
                "business_action": "notification created for human review",
                "status": notification.delivery_status,
                "review_item_id": item.review_item_id,
                "crm_record_id": notification.crm_record_id,
                "manager_fallback_used": notification.manager_fallback_used,
                "recipient_role": notification.recipient_role,
            },
        )
    )


def log_notification_attempt_step(
    notification: NotificationEvent, step_name: str
) -> None:
    step_event_id = f"notification_step_{uuid4()}"
    created_at = utc_now()
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
                notification.workflow_run_id,
                WORKFLOW_NAME,
                step_name,
                "success",
                None,
                notification.entity_type,
                notification.entity_id,
                created_at,
                created_at,
                0,
                "info" if notification.delivery_status == "sent" else "warning",
                None,
                None,
                None,
                0,
                "Configure N8N_FAILURE_WEBHOOK_URL to send external failure notifications."
                if notification.delivery_status == "queued_no_webhook"
                else None,
                created_at,
                encode_json(
                    {
                        "notification_id": notification.notification_id,
                        "notification_type": notification.notification_type,
                        "review_item_id": notification.review_item_id,
                        "delivery_status": notification.delivery_status,
                        "manager_fallback_used": notification.manager_fallback_used,
                    }
                ),
            ),
        )
        connection.commit()


def notification_from_row(row) -> NotificationEvent:
    return NotificationEvent(
        id=row["id"],
        notification_id=row["notification_id"],
        notification_type=row["notification_type"],
        workflow_run_id=row["workflow_run_id"],
        workflow_name=row["workflow_name"],
        step_name=row["step_name"],
        severity=row["severity"],
        error_type=row["error_type"],
        safe_error_message=row["safe_error_message"],
        retryable=bool(row["retryable"]),
        recommended_fix=row["recommended_fix"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        crm_record_id=row["crm_record_id"],
        review_item_id=row["review_item_id"],
        recipient_role=row["recipient_role"],
        recipient_id=row["recipient_id"],
        recipient_name=row["recipient_name"],
        recipient_email=row["recipient_email"],
        routed_owner_id=row["routed_owner_id"],
        routed_owner_name=row["routed_owner_name"],
        manager_fallback_used=bool(row["manager_fallback_used"]),
        title=row["title"],
        message=row["message"],
        recommended_action=row["recommended_action"],
        delivery_status=row["delivery_status"],
        webhook_configured=bool(row["webhook_configured"]),
        created_at=row["created_at"],
        metadata_json=decode_json(row["metadata_json"], {}),
    )


def scrub_secret_text(value: str) -> str:
    lowered = value.lower()
    if (
        "token" in lowered
        or "secret" in lowered
        or "authorization" in lowered
        or "http://" in lowered
        or "https://" in lowered
    ):
        return "A safe error occurred. Sensitive details were redacted."
    return value


def external_payload(payload: dict) -> dict:
    safe_keys = {
        "notification_id",
        "notification_type",
        "workflow_run_id",
        "workflow_name",
        "step_name",
        "severity",
        "error_type",
        "safe_error_message",
        "retryable",
        "recommended_fix",
        "entity_type",
        "entity_id",
        "crm_record_id",
        "review_item_id",
        "recipient_role",
        "recipient_id",
        "recipient_name",
        "recipient_email",
        "routed_owner_id",
        "routed_owner_name",
        "manager_fallback_used",
        "title",
        "message",
        "recommended_action",
        "created_at",
    }
    return {key: scrub_secret_text(str(value)) if isinstance(value, str) else value for key, value in payload.items() if key in safe_keys}


def review_title(item: ReviewItem, manager_fallback_used: bool) -> str:
    if manager_fallback_used:
        return "Review item needs assignment"
    if item.review_type == "proposal_outline":
        return "Proposal outline ready for review"
    if item.priority in {"critical", "high"}:
        return "Review required for high-priority lead"
    return f"Review required: {item.title}"


def review_message(item: ReviewItem, manager_fallback_used: bool) -> str:
    company = item.company or "A sales item"
    if manager_fallback_used:
        return f"{company} was flagged for review, but no owner is assigned."
    if item.review_type == "proposal_outline":
        return "AI prepared a proposal outline that requires approval before CRM/deal-stage update."
    if item.review_type == "follow_up_draft":
        return f"{company} has a follow-up draft pending review before CRM update."
    return f"{company} has a review item pending before the proposed action is applied."


def text(value: object) -> str:
    return str(value or "").strip()


def safe_error(error: Exception) -> str:
    return scrub_secret_text(str(error))
