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

from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.demo_lifecycle import run_full_demo_story  # noqa: E402
from app.services.mock_crm_adapter import get_lead_record_activities  # noqa: E402
from app.services.notifications import list_notification_events  # noqa: E402
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_steps import list_step_events  # noqa: E402


def main() -> int:
    reset_persistence_tables()
    checks = [
        ("full demo story creates persisted CRM activity chain", check_crm_activity_chain),
        ("meeting writeback creates audit and operational events", check_meeting_writeback),
        ("follow-up approval and outcome write CRM activity", check_follow_up_lifecycle),
        ("proposal approval writeback creates CRM activity", check_proposal_lifecycle),
        ("CRM hygiene creates review visibility", check_hygiene_visibility),
        ("demo failure creates notification event without secrets", check_notification_event),
        ("full demo story creates review notifications", check_review_notifications),
        ("full demo story records demo completion audit and step", check_demo_completion_markers),
    ]
    result = run_full_demo_story(reset_demo=True)

    passed = 0
    failed = 0
    for name, check in checks:
        try:
            check(result)
            passed += 1
            print(f"PASS {name}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL {name}: {error}")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def check_crm_activity_chain(result) -> None:
    activities = get_lead_record_activities(result.crm_record_id)
    activity_types = {activity.activity_type for activity in activities}
    required = {
        "lead_created",
        "meeting_attached",
        "meeting_summary_created",
        "follow_up_draft_approved",
        "follow_up_outcome_captured",
        "proposal_outline_approved",
        "proposal_sent",
        "hygiene_check_completed",
    }
    missing = required - activity_types
    assert not missing, f"missing CRM activities: {sorted(missing)}"


def check_meeting_writeback(result) -> None:
    audit_types = {event.event_type for event in list_audit_events()}
    step_names = {event.step_name for event in list_step_events()}
    assert "meeting_summary_crm_writeback" in audit_types
    assert "meeting_attachment_completed" in step_names
    assert result.meeting_summary_status == "written_to_crm_activity"


def check_follow_up_lifecycle(result) -> None:
    assert result.follow_up_approval_status == "approved"
    assert result.follow_up_outcome == "requested_proposal"
    audit_types = {event.event_type for event in list_audit_events()}
    assert "follow_up_outcome_captured" in audit_types
    assert "crm_update_applied" in audit_types


def check_proposal_lifecycle(result) -> None:
    assert result.proposal_status == "approved"
    audit_types = {event.event_type for event in list_audit_events()}
    assert "proposal_status_updated" in audit_types


def check_hygiene_visibility(result) -> None:
    assert result.hygiene_status in {"medium", "high", "critical"}
    review_items = list_review_items()
    assert any(item.review_type == "high_risk_deal" for item in review_items)


def check_notification_event(result) -> None:
    notifications = list_notification_events()
    assert notifications, "expected a queued notification from demo failure"
    text = " ".join(
        " ".join(
            [
                str(item.safe_error_message),
                str(item.recommended_fix),
                str(item.metadata_json),
            ]
        )
        for item in notifications
    )
    assert "token" not in text.lower()
    assert "secret" not in text.lower()
    assert "http://" not in text.lower()
    assert "https://" not in text.lower()
    assert result.notifications_sent_or_queued >= 1


def check_review_notifications(result) -> None:
    notifications = list_notification_events()
    assert any(
        item.notification_type in {"review_required", "review_assignment_needed"}
        and item.review_item_id
        for item in notifications
    )
    assert any(item.recipient_role in {"assigned_owner", "routed_rep", "manager"} for item in notifications)
    step_names = {event.step_name for event in list_step_events()}
    assert "review_notification_create" in step_names


def check_demo_completion_markers(result) -> None:
    audit_types = {event.event_type for event in list_audit_events()}
    step_names = {event.step_name for event in list_step_events()}
    assert "demo_story_completed" in audit_types
    assert "demo_story_completed" in step_names


if __name__ == "__main__":
    raise SystemExit(main())
