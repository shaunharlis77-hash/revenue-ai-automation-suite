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
from app.models.review_queue import ReviewItemCreate  # noqa: E402
from app.models.workflow_logs import (  # noqa: E402
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
)
from app.services.audit_trail import create_audit_event  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.review_queue import create_review_item  # noqa: E402
from app.services.workflow_logs import mark_workflow_failure, start_workflow_run  # noqa: E402
from app.services.workflow_steps import log_step_failure  # noqa: E402


def main() -> int:
    get_settings.cache_clear()
    reset_persistence_tables()
    client = TestClient(app)

    checks = [
        ("route works with empty database", lambda: check_empty_database(client)),
        ("operational and governance metrics use persisted data", lambda: check_persisted_admin_data(client)),
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
    response = client.get("/metrics/admin-dashboard")
    assert response.status_code == 200
    data = response.json()

    for section in [
        "system_status",
        "review_queue_health",
        "audit_health",
        "operational_health",
        "hubspot_sync_health",
        "workflow_health",
        "action_links",
    ]:
        assert section in data, f"missing {section}"

    assert data["system_status"]["adapter_mode"] == "mock"
    assert data["system_status"]["hubspot_enabled"] is False
    assert data["system_status"]["total_workflow_runs"] == 0
    assert data["review_queue_health"]["pending"] == 0
    assert len(data["action_links"]) >= 6


def check_persisted_admin_data(client: TestClient) -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="crm_hygiene_deal_risk_monitor",
            input_reference="crm_record_metrics_001",
        )
    )
    mark_workflow_failure(
        run.workflow_run_id,
        WorkflowRunFailureRequest(
            failure_step="crm_hygiene_checked",
            failure_reason="Metrics test failure.",
            input_reference="crm_record_metrics_001",
            human_review_required=True,
            next_action="Review the failed check.",
        ),
    )
    log_step_failure(
        run.workflow_run_id,
        "crm_hygiene_deal_risk_monitor",
        "crm_hygiene_checked",
        "Metrics test failure.",
        entity_type="crm_record",
        entity_id="crm_record_metrics_001",
        failure_reason="Metrics test failure.",
        retryable=False,
        recommended_fix="Check the CRM hygiene input record.",
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name="crm_hygiene_deal_risk_monitor",
            entity_type="crm_record",
            entity_id="crm_record_metrics_001",
            event_type="guardrail_triggered",
            event_source="test",
            actor="test_runner",
            guardrails_triggered=["high_risk_deal_review_required"],
            human_review_required=True,
            metadata_json={"test_case": "admin_dashboard_metrics"},
        )
    )
    create_review_item(
        ReviewItemCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name="crm_hygiene_deal_risk_monitor",
            entity_type="crm_record",
            entity_id="crm_record_metrics_001",
            company="Northstar Analytics",
            contact_name="Maya Chen",
            review_type="high_risk_deal",
            title="Review high-risk deal",
            priority="high",
            risk_level="high",
            review_reasons=["High-risk deal requires review."],
            proposed_action="Review CRM hygiene issue.",
            proposed_output="High-risk record needs attention.",
            metadata_json={"test_case": "admin_dashboard_metrics"},
        )
    )

    data = client.get("/metrics/admin-dashboard").json()

    assert data["system_status"]["failed_workflow_runs"] >= 1
    assert data["review_queue_health"]["pending"] >= 1
    assert data["audit_health"]["total_audit_events"] >= 1
    assert data["operational_health"]["failed_step_events"] >= 1
    assert data["operational_health"]["non_retryable_failures"] >= 1
    assert len(data["operational_health"]["recommended_fixes"]) >= 1
    assert any(
        item["workflow_name"] == "crm_hygiene_deal_risk_monitor"
        for item in data["workflow_health"]
    )


def check_no_secret(client: TestClient) -> None:
    payload = json.dumps(client.get("/metrics/admin-dashboard").json())
    assert "secret-value-that-must-not-appear" not in payload


if __name__ == "__main__":
    raise SystemExit(main())
