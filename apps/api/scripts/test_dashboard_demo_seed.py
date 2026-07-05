import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

os.environ["CRM_ADAPTER_MODE"] = "mock"
os.environ["HUBSPOT_ENABLED"] = "false"
os.environ["HUBSPOT_ACCESS_TOKEN"] = "secret-value-that-must-not-appear"
os.environ["N8N_FAILURE_WEBHOOK_URL"] = "https://secret-webhook-url.invalid/path"

from app.config.settings import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.mock_crm_adapter import get_lead_records  # noqa: E402
from app.services.notifications import list_notification_events  # noqa: E402
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_steps import list_step_events  # noqa: E402
from scripts.seed_dashboard_demo_data import seed_dashboard_demo_data  # noqa: E402


def main() -> int:
    get_settings.cache_clear()
    reset_persistence_tables()
    summary = seed_dashboard_demo_data(count=16, reset_demo=True)
    client = TestClient(app)

    checks = [
        ("seed creates CRM/demo records", lambda: check_records(summary)),
        ("seed creates audit events", check_audit_events),
        ("seed creates workflow step events", check_step_events),
        ("seed creates review items", check_review_items),
        ("seed creates notifications", check_notifications),
        ("dashboards return non-empty metrics", lambda: check_dashboards(client)),
        ("seed stays in mock mode", lambda: check_mock_mode(client)),
        ("responses do not expose secrets", lambda: check_no_secrets(client)),
    ]

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


def check_records(summary: dict[str, int]) -> None:
    records = get_lead_records()
    priorities = {record.priority for record in records}
    statuses = {record.crm_update_status for record in records}

    assert len(records) >= 12, f"expected at least 12 CRM records, got {len(records)}"
    assert summary["crm_records"] == len(records)
    assert {"high", "medium"} & priorities, f"expected varied priorities, got {priorities}"
    assert "applied" in statuses or "applied_with_review_visibility" in statuses
    assert "blocked_pending_review" in statuses
    assert all(record.adapter_mode == "mock" for record in records)


def check_audit_events() -> None:
    events = list_audit_events()
    event_types = {event.event_type for event in events}

    assert len(events) >= 30, f"expected rich audit history, got {len(events)}"
    assert "lead_scored" in event_types
    assert "follow_up_draft_created" in event_types
    assert "proposal_outline_created" in event_types
    assert "crm_hygiene_checked" in event_types
    assert "review_created" in event_types


def check_step_events() -> None:
    events = list_step_events()
    statuses = {event.step_status for event in events}
    failed = [event for event in events if event.step_status == "failed"]

    assert len(events) >= 50, f"expected rich operational history, got {len(events)}"
    assert "success" in statuses
    assert failed, "expected at least one controlled failure diagnostic"
    assert any(event.recommended_fix for event in failed)


def check_review_items() -> None:
    items = list_review_items()
    statuses = {item.status for item in items}
    review_types = {item.review_type for item in items}

    assert len(items) >= 8, f"expected review items, got {len(items)}"
    assert "pending" in statuses
    assert "approved" in statuses
    assert "rejected" in statuses
    assert "follow_up_draft" in review_types
    assert "proposal_outline" in review_types


def check_notifications() -> None:
    notifications = list_notification_events()
    notification_types = {item.notification_type for item in notifications}
    recipient_roles = {item.recipient_role for item in notifications}

    assert notifications, "expected queued notifications"
    assert "workflow_step_failed" in notification_types
    assert "review_required" in notification_types
    assert "review_assignment_needed" in notification_types
    assert "admin_ops" in recipient_roles
    assert "manager" in recipient_roles
    assert any(role in recipient_roles for role in {"assigned_owner", "routed_rep"})
    assert all(item.delivery_status == "queued_no_webhook" for item in notifications)


def check_dashboards(client: TestClient) -> None:
    sales = client.get("/metrics/sales-manager-dashboard").json()
    admin = client.get("/metrics/admin-dashboard").json()

    assert sales["sales_overview"]["total_leads_processed"] >= 12
    assert sales["sales_overview"]["follow_ups_drafted"] >= 1
    assert sales["sales_overview"]["proposals_recommended"] >= 1
    assert sales["ai_impact"]["estimated_time_saved_minutes"] > 0
    assert sales["drop_off_zone_stats"]["total_drop_off_signals"] > 0
    assert admin["system_status"]["total_workflow_runs"] > 0
    assert admin["review_queue_health"]["pending"] >= 1
    assert admin["audit_health"]["total_audit_events"] >= 1
    assert admin["operational_health"]["failed_step_events"] >= 1


def check_mock_mode(client: TestClient) -> None:
    data = client.get("/metrics/admin-dashboard").json()
    assert data["system_status"]["adapter_mode"] == "mock"
    assert data["system_status"]["hubspot_enabled"] is False


def check_no_secrets(client: TestClient) -> None:
    payload = json.dumps(
        {
            "sales": client.get("/metrics/sales-manager-dashboard").json(),
            "admin": client.get("/metrics/admin-dashboard").json(),
            "notifications": [item.model_dump() for item in list_notification_events()],
        }
    )
    forbidden = [
        "secret-value-that-must-not-appear",
        "secret-webhook-url",
        "HUBSPOT_ACCESS_TOKEN",
    ]
    for value in forbidden:
        assert value not in payload, f"secret leaked: {value}"


if __name__ == "__main__":
    raise SystemExit(main())
