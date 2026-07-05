import os
import sys
from pathlib import Path


os.environ["CRM_ADAPTER_MODE"] = "mock"
os.environ["HUBSPOT_ENABLED"] = "false"
os.environ["HUBSPOT_ACCESS_TOKEN"] = ""
os.environ["N8N_FAILURE_WEBHOOK_URL"] = ""
os.environ["NOTIFICATIONS_ENABLED"] = "true"

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.services.database import reset_persistence_tables  # noqa: E402
from app.models.review_queue import ReviewItemCreate  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.notifications import list_notification_events  # noqa: E402
from app.services.review_queue import create_review_item  # noqa: E402
from app.services.workflow_steps import list_step_events, log_step_failure  # noqa: E402


def main() -> int:
    reset_persistence_tables()
    checks = [
        ("failed workflow step creates notification event", check_notification_created),
        ("queued_no_webhook behavior works without n8n", check_queued_no_webhook),
        ("payload contains safe diagnostic fields", check_safe_payload_fields),
        ("notification attempt creates operational step event", check_attempt_step),
        ("review item with routed owner creates owner notification", check_owner_review_notification),
        ("unassigned risky review item creates manager fallback notification", check_manager_fallback_notification),
        ("proposal review creates review notification", check_proposal_review_notification),
        ("notification creation writes audit event", check_notification_audit_events),
        ("notification creation writes workflow step event", check_review_notification_step_event),
        ("no token or secrets exposed", check_no_secret_exposure),
    ]

    log_step_failure(
        "notification_test_run",
        "notification_test_workflow",
        "hubspot_task_create",
        "HubSpot validation failed for task payload.",
        entity_type="crm_record",
        entity_id="crm_demo_record",
        failure_reason="Optional task creation failed during validation.",
        retryable=False,
        recommended_fix="Check HubSpot task payload required properties and scopes.",
        severity="error",
    )
    create_review_item(
        ReviewItemCreate(
            workflow_run_id="owner_review_run",
            workflow_name="follow_up_drafting",
            entity_type="follow_up",
            entity_id="follow_up_owner_001",
            company="Northstar Analytics",
            contact_name="Maya Chen",
            review_type="follow_up_draft",
            title="Review follow-up draft for Northstar Analytics",
            priority="high",
            risk_level="medium",
            review_reasons=["Customer-facing follow-up requires review."],
            proposed_action="Review and approve the draft.",
            proposed_output="Prepared follow-up draft.",
            assigned_to="Alex Rivera",
            metadata_json={
                "crm_record_id": "crm_owner_001",
                "assigned_owner_id": "owner_001",
                "assigned_owner_name": "Alex Rivera",
                "assigned_owner_email": "alex.rivera@example.com",
            },
        )
    )
    create_review_item(
        ReviewItemCreate(
            workflow_run_id="manager_review_run",
            workflow_name="lead_intake_enrichment",
            entity_type="lead",
            entity_id="lead_risky_001",
            company="Risky Revenue Co",
            contact_name=None,
            review_type="crm_update",
            title="Review risky CRM update",
            priority="high",
            risk_level="high",
            review_reasons=["Risky CRM update requires review."],
            proposed_action="Assign owner and review blocked update.",
            proposed_output="Blocked pending review.",
            metadata_json={"crm_record_id": "crm_risky_001"},
        )
    )
    create_review_item(
        ReviewItemCreate(
            workflow_run_id="proposal_review_run",
            workflow_name="proposal_outline_drafting",
            entity_type="proposal",
            entity_id="proposal_001",
            company="Northstar Analytics",
            contact_name="Maya Chen",
            review_type="proposal_outline",
            title="Proposal outline ready for review",
            priority="high",
            risk_level="medium",
            review_reasons=["Proposal outline requires approval."],
            proposed_action="Review proposal outline.",
            proposed_output="Prepared proposal outline.",
            assigned_to="Alex Rivera",
            metadata_json={"crm_record_id": "crm_owner_001"},
        )
    )

    passed = 0
    failed = 0
    for name, check in checks:
        try:
            check()
            passed += 1
            print(f"PASS {name}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL {name}: {error}")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def notification():
    events = list_notification_events()
    assert events, "expected notification event"
    return next(event for event in events if event.notification_type == "workflow_step_failed")


def check_notification_created() -> None:
    assert notification().workflow_name == "notification_test_workflow"
    assert notification().notification_type == "workflow_step_failed"
    assert notification().recipient_role == "admin_ops"


def check_queued_no_webhook() -> None:
    item = notification()
    assert item.delivery_status == "queued_no_webhook"
    assert item.webhook_configured is False


def check_safe_payload_fields() -> None:
    item = notification()
    assert item.workflow_run_id == "notification_test_run"
    assert item.step_name == "hubspot_task_create"
    assert item.severity == "error"
    assert item.error_type == "Error"
    assert item.safe_error_message
    assert item.recommended_fix
    assert item.entity_type == "crm_record"
    assert item.entity_id == "crm_demo_record"


def check_attempt_step() -> None:
    steps = list_step_events()
    assert any(step.step_name == "failure_notification_attempted" for step in steps)


def check_owner_review_notification() -> None:
    events = list_notification_events()
    match = next(
        event
        for event in events
        if event.review_item_id and event.entity_id == "follow_up_owner_001"
    )
    assert match.notification_type == "review_required"
    assert match.recipient_role == "assigned_owner"
    assert match.recipient_name == "Alex Rivera"
    assert match.manager_fallback_used is False
    assert match.delivery_status == "queued_no_webhook"


def check_manager_fallback_notification() -> None:
    events = list_notification_events()
    match = next(
        event
        for event in events
        if event.review_item_id and event.entity_id == "lead_risky_001"
    )
    assert match.notification_type == "review_assignment_needed"
    assert match.recipient_role == "manager"
    assert match.manager_fallback_used is True
    assert "Assign an owner" in str(match.recommended_action)


def check_proposal_review_notification() -> None:
    events = list_notification_events()
    match = next(
        event
        for event in events
        if event.review_item_id and event.entity_id == "proposal_001"
    )
    assert match.title == "Proposal outline ready for review"
    assert match.notification_type == "review_required"


def check_notification_audit_events() -> None:
    event_types = [event.event_type for event in list_audit_events()]
    assert "review_notification_created" in event_types
    assert "manager_fallback_notification_created" in event_types


def check_review_notification_step_event() -> None:
    steps = list_step_events()
    assert any(step.step_name == "review_notification_create" for step in steps)


def check_no_secret_exposure() -> None:
    text = " ".join(str(item.model_dump()) for item in list_notification_events()).lower()
    assert "secret" not in text
    assert "access_token" not in text
    assert "authorization" not in text
    assert "webhook_url" not in text
    assert "http://" not in text
    assert "https://" not in text


if __name__ == "__main__":
    raise SystemExit(main())
