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

from app.config.settings import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditEventCreate  # noqa: E402
from app.models.workflow_logs import (  # noqa: E402
    WorkflowRunStartRequest,
    WorkflowRunSuccessRequest,
)
from app.services.audit_trail import create_audit_event  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.workflow_logs import mark_workflow_success, start_workflow_run  # noqa: E402


def main() -> int:
    get_settings.cache_clear()
    reset_persistence_tables()
    client = TestClient(app)

    checks = [
        ("route works with empty database", lambda: check_empty_database(client)),
        ("metrics use persisted workflow data", lambda: check_persisted_usage(client)),
        ("response does not expose secrets", lambda: check_no_secret(client)),
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


def check_empty_database(client: TestClient) -> None:
    response = client.get("/metrics/sales-manager-dashboard")
    assert response.status_code == 200
    data = response.json()

    for section in [
        "sales_overview",
        "lead_and_pipeline_health",
        "drop_off_zone_stats",
        "team_activity_and_ai_adoption",
        "ai_impact",
        "sales_execution_risks",
        "recent_revenue_activity",
    ]:
        assert section in data, f"missing {section}"

    assert data["sales_overview"]["total_leads_processed"] == 0
    assert data["ai_impact"]["estimated_time_saved_minutes"] == 0
    assert data["team_activity_and_ai_adoption"]["rep_adoption_status"] == "not_enough_rep_level_data"
    assert (
        data["drop_off_zone_stats"]["meeting_completed_no_follow_up"]["status"]
        == "not_enough_data"
    )


def check_persisted_usage(client: TestClient) -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="follow_up_drafting",
            input_reference="follow_up_metrics_001",
        )
    )
    mark_workflow_success(
        run.workflow_run_id,
        WorkflowRunSuccessRequest(
            output_summary="Follow-up draft created.",
            human_review_required=True,
            next_action="Review the draft before sending.",
        ),
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name="follow_up_drafting",
            entity_type="follow_up",
            entity_id="follow_up_metrics_001",
            event_type="follow_up_draft_created",
            event_source="test",
            actor="test_runner",
            human_review_required=True,
            metadata_json={"test_case": "sales_manager_dashboard_metrics"},
        )
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name="follow_up_drafting",
            entity_type="follow_up",
            entity_id="follow_up_metrics_001",
            event_type="follow_up_draft_created",
            event_source="test",
            actor="test_runner",
            human_review_required=True,
            metadata_json={"test_case": "sales_manager_dashboard_metrics"},
        )
    )

    data = client.get("/metrics/sales-manager-dashboard").json()
    adoption = data["team_activity_and_ai_adoption"]
    impact = data["ai_impact"]
    raw_review_required_events = 2

    assert adoption["ai_assisted_workflows_used"] >= 1
    assert adoption["adoption_rate_percent"] > 0
    assert adoption["workflow_usage_breakdown"]["follow_up_drafting"] >= 1
    assert impact["estimated_time_saved_minutes"] >= 8
    assert "estimation_method" in impact
    assert data["sales_overview"]["follow_ups_drafted"] >= 1
    assert impact["human_review_required_count"] == 1
    assert impact["human_review_required_count"] != raw_review_required_events


def check_no_secret(client: TestClient) -> None:
    payload = json.dumps(client.get("/metrics/sales-manager-dashboard").json())
    assert "secret-value-that-must-not-appear" not in payload


if __name__ == "__main__":
    raise SystemExit(main())
