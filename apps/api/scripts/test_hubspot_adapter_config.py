import os
import sys
from pathlib import Path
from uuid import uuid4


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.config.settings import get_settings  # noqa: E402
from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.crm_adapter_factory import current_adapter_mode, get_crm_adapter  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.hubspot_adapter import get_hubspot_status  # noqa: E402
from app.services.lead_intake import intake_lead  # noqa: E402
from app.services.mock_crm_adapter import get_lead_record_activities  # noqa: E402
from app.services.workflow_logs import list_workflow_runs, reset_workflow_runs  # noqa: E402
from app.services.workflow_steps import list_step_events_by_workflow_run_id  # noqa: E402


TEST_RUN_ID = uuid4().hex[:8]


def main() -> int:
    checks = [
        ("mock mode remains the safe default", check_mock_mode_default),
        ("HubSpot disabled uses mock adapter safely", check_hubspot_disabled_uses_mock),
        ("missing HubSpot token fails safely with diagnostics", check_missing_token_failure),
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
        finally:
            restore_safe_env()

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def check_mock_mode_default() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    restore_safe_env()
    adapter = get_crm_adapter()
    status = get_hubspot_status()
    result = intake_lead(clean_lead("mock-default"))
    activities = get_lead_record_activities(result.crm_record.crm_record_id)

    assert adapter.__name__.endswith("mock_crm_adapter"), adapter.__name__
    assert current_adapter_mode() == "mock"
    assert status.status == "disabled_mock_mode", status
    assert result.crm_update_status == "applied"
    assert result.crm_record.adapter_mode == "mock"
    assert result.crm_record.hubspot_sync_status == "skipped_mock_mode"
    assert activities, "expected local CRM activities in mock mode"


def check_hubspot_disabled_uses_mock() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    set_env(CRM_ADAPTER_MODE="hubspot", HUBSPOT_ENABLED="false", HUBSPOT_ACCESS_TOKEN="")
    adapter = get_crm_adapter()
    status = get_hubspot_status()
    result = intake_lead(clean_lead("hubspot-disabled"))

    assert adapter.__name__.endswith("mock_crm_adapter"), adapter.__name__
    assert current_adapter_mode() == "mock"
    assert status.status == "disabled_mock_mode", status
    assert result.crm_record.adapter_mode == "mock"
    assert result.crm_record.hubspot_sync_status == "skipped_mock_mode"


def check_missing_token_failure() -> None:
    reset_persistence_tables()
    reset_workflow_runs()
    set_env(CRM_ADAPTER_MODE="hubspot", HUBSPOT_ENABLED="true", HUBSPOT_ACCESS_TOKEN="")

    try:
        intake_lead(clean_lead("missing-token"))
    except RuntimeError as error:
        assert "access token is missing" in str(error).lower(), str(error)
    else:
        raise AssertionError("expected missing token to fail safely")

    failed_run = next(
        run
        for run in reversed(list_workflow_runs())
        if run.workflow_name == "lead_intake_enrichment" and run.status == "failed"
    )
    steps = list_step_events_by_workflow_run_id(failed_run.workflow_run_id)
    events = [
        event
        for event in list_audit_events()
        if event.workflow_run_id == failed_run.workflow_run_id
    ]

    assert failed_run.failure_step == "crm_adapter_write_failed", failed_run.failure_step
    assert any(step.step_name == "hubspot_sync_failed" for step in steps), [
        step.step_name for step in steps
    ]
    failed_step = next(step for step in steps if step.step_name == "hubspot_sync_failed")
    assert failed_step.retryable is False
    assert "HUBSPOT_ACCESS_TOKEN" in (failed_step.recommended_fix or "")
    assert any(event.event_type == "hubspot_sync_failed" for event in events), [
        event.event_type for event in events
    ]
    assert all("Bearer " not in str(event.metadata_json) for event in events), (
        "audit metadata should not include bearer token values"
    )


def clean_lead(label: str) -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Nadia",
        last_name="Patel",
        email=f"nadia.patel.{TEST_RUN_ID}.{label}@example.com",
        company="Local Growth Studio",
        job_title="Operations Manager",
        company_website="https://localgrowth-demo.com",
        company_size="51-200",
        industry="Marketing Services",
        region="EMEA",
        source="webinar",
        message="We are evaluating CRM cleanup for our sales team and gathering options.",
        pain_points=["CRM cleanup"],
        urgency="60_days",
        budget_context="Planned budget",
        requested_demo=False,
        crm_system="HubSpot",
        notes="HubSpot adapter config verification case.",
    )


def set_env(**values: str) -> None:
    for key, value in values.items():
        os.environ[key] = value
    get_settings.cache_clear()


def restore_safe_env() -> None:
    set_env(
        CRM_ADAPTER_MODE="mock",
        HUBSPOT_ENABLED="false",
        HUBSPOT_ACCESS_TOKEN="",
        HUBSPOT_PORTAL_ID="",
        HUBSPOT_DEFAULT_PIPELINE="",
        HUBSPOT_DEFAULT_DEAL_STAGE="",
        HUBSPOT_OWNER_ID="",
    )


if __name__ == "__main__":
    raise SystemExit(main())
