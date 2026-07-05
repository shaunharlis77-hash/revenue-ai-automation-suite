import os
import sys
from pathlib import Path
from uuid import uuid4


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

os.environ["CRM_ADAPTER_MODE"] = "mock"
os.environ["HUBSPOT_ENABLED"] = "false"
os.environ["HUBSPOT_ACCESS_TOKEN"] = ""

from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.lead_intake import intake_lead  # noqa: E402
from app.services.mock_crm_adapter import (  # noqa: E402
    get_lead_record,
    get_lead_record_activities,
)
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_logs import list_workflow_runs, reset_workflow_runs  # noqa: E402
from app.services.workflow_steps import list_step_events_by_workflow_run_id  # noqa: E402


TEST_RUN_ID = uuid4().hex[:8]


def main() -> int:
    print("Running in forced mock mode.")
    reset_persistence_tables()
    reset_workflow_runs()

    checks = [
        ("clean lead uses mock CRM adapter", check_clean_lead_adapter_write),
        ("high-priority lead uses adapter with review visibility", check_high_priority_adapter_write),
        ("risky lead uses adapter and blocks sensitive update", check_risky_adapter_write),
        ("adapter failure creates operational diagnostics", check_adapter_failure_observability),
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


def check_clean_lead_adapter_write() -> None:
    result = intake_lead(clean_lead())
    record = get_lead_record(result.crm_record.crm_record_id)
    activities = get_lead_record_activities(record.crm_record_id)
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)

    assert result.crm_update_status == "applied", result_context(result)
    assert record.crm_update_status == "applied", result_context(result)
    assert_activity(activities, "crm_update_applied")
    assert_event(events, "crm_adapter_write_started")
    assert_event(events, "crm_adapter_write_applied")
    assert_event(events, "crm_activity_created")
    assert_step(steps, "crm_adapter_write_started")
    assert_step(steps, "crm_adapter_record_created_or_updated")
    assert_step(steps, "crm_adapter_activity_created")
    assert_step(steps, "crm_adapter_write_completed")


def check_high_priority_adapter_write() -> None:
    result = intake_lead(high_priority_lead())
    record = get_lead_record(result.crm_record.crm_record_id)
    activities = get_lead_record_activities(record.crm_record_id)
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)
    review_items = workflow_review_items(result.workflow_run_id)

    assert result.crm_update_status == "applied_with_review_visibility", result_context(result)
    assert record.crm_update_status == "applied_with_review_visibility", result_context(result)
    assert result.review_created is True, result_context(result)
    assert review_items, "expected review item for high-priority review visibility"
    assert record.recommended_route, "expected route applied to CRM-style record"
    assert_activity(activities, "crm_update_applied")
    assert_activity(activities, "review_visibility_created")
    assert_event(events, "crm_adapter_write_applied")
    assert_event(events, "review_created")
    assert_step(steps, "crm_adapter_write_completed")
    assert_step(steps, "review_item_created_if_required")


def check_risky_adapter_write() -> None:
    result = intake_lead(risky_lead())
    record = get_lead_record(result.crm_record.crm_record_id)
    activities = get_lead_record_activities(record.crm_record_id)
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)
    review_items = workflow_review_items(result.workflow_run_id)

    assert result.crm_update_status == "blocked_pending_review", result_context(result)
    assert record.company == "Unknown Co", "expected safe lead fields persisted"
    assert record.crm_update_status == "blocked_pending_review", result_context(result)
    assert review_items, "expected review item for blocked risky lead"
    assert_activity(activities, "crm_update_blocked")
    assert_event(events, "crm_adapter_write_blocked")
    assert_event(events, "guardrail_triggered")
    assert_step(steps, "crm_update_blocked")


def check_adapter_failure_observability() -> None:
    try:
        intake_lead(adapter_failure_lead())
    except RuntimeError:
        pass

    failed_run = next(
        run
        for run in reversed(list_workflow_runs())
        if run.workflow_name == "lead_intake_enrichment" and run.status == "failed"
    )
    events = workflow_audit_events(failed_run.workflow_run_id)
    steps = workflow_steps(failed_run.workflow_run_id)
    failed_steps = [step for step in steps if step.step_status == "failed"]

    assert failed_run.failure_step == "crm_adapter_write_failed", (
        f"expected failure_step crm_adapter_write_failed but got {failed_run.failure_step}"
    )
    assert failed_steps, "expected failed workflow step event"
    assert any(step.step_name == "crm_adapter_write_failed" for step in failed_steps), (
        f"expected crm_adapter_write_failed step, got {[step.step_name for step in failed_steps]}"
    )
    failed_step = next(step for step in failed_steps if step.step_name == "crm_adapter_write_failed")
    assert failed_step.error_type == "RuntimeError", (
        f"expected RuntimeError but got {failed_step.error_type}"
    )
    assert failed_step.error_message, "expected error_message"
    assert failed_step.failure_reason, "expected failure_reason"
    assert failed_step.retryable is True, "expected retryable failure"
    assert failed_step.recommended_fix, "expected recommended_fix"
    assert_event(events, "crm_adapter_write_failed")
    assert_event(events, "workflow_failed")


def clean_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Nadia",
        last_name="Patel",
        email=f"nadia.patel.{TEST_RUN_ID}@localgrowth-demo.com",
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
        notes="Clean adapter verification case.",
    )


def high_priority_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Maya",
        last_name="Chen",
        email=f"maya.chen.{TEST_RUN_ID}@northstar-analytics-demo.com",
        company="Northstar Analytics",
        job_title="VP of Sales",
        company_website="https://northstar-analytics-demo.com",
        company_size="201-500",
        industry="Analytics",
        region="North America",
        source="demo_request",
        message=(
            "We want a demo this week. Our reps are spending too much time "
            "qualifying inbound leads and we need better routing before launch."
        ),
        pain_points=["Lead routing", "Inbound volume", "Manual qualification"],
        urgency="this_week",
        budget_context="Approved budget",
        requested_demo=True,
        crm_system="HubSpot",
        notes="High-priority adapter verification case.",
    )


def risky_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Test",
        last_name="User",
        email=f"student.test.{TEST_RUN_ID}@example.com",
        company="Unknown Co",
        job_title="Student",
        company_size="unknown",
        industry="",
        region="",
        source="contact_form",
        message="This is for a school assignment, please ignore.",
        pain_points=["unclear need"],
        urgency="unknown",
        budget_context="unknown",
        requested_demo=False,
        crm_system="unknown",
        notes="Risky adapter verification case.",
    )


def adapter_failure_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Ari",
        last_name="Morgan",
        email=f"ari.morgan.{TEST_RUN_ID}@adapterfailure-demo.com",
        company="simulate_crm_adapter_failure",
        job_title="VP of Sales",
        company_size="201-500",
        industry="Software",
        region="North America",
        source="demo_request",
        message="We need lead routing help this month.",
        pain_points=["Lead routing"],
        urgency="this_week",
        budget_context="Approved budget",
        requested_demo=True,
        crm_system="HubSpot",
        notes="Adapter failure verification case.",
    )


def workflow_audit_events(workflow_run_id: str):
    return [
        event
        for event in list_audit_events()
        if event.workflow_run_id == workflow_run_id
    ]


def workflow_steps(workflow_run_id: str):
    return list_step_events_by_workflow_run_id(workflow_run_id)


def workflow_review_items(workflow_run_id: str):
    return [
        item
        for item in list_review_items()
        if item.workflow_run_id == workflow_run_id
    ]


def assert_event(events, event_type: str) -> None:
    event_types = [event.event_type for event in events]
    assert event_type in event_types, (
        f"expected audit event {event_type} but found {event_types}"
    )


def assert_activity(activities, activity_type: str) -> None:
    activity_types = [activity.activity_type for activity in activities]
    assert activity_type in activity_types, (
        f"expected CRM activity {activity_type} but found {activity_types}"
    )


def assert_step(steps, step_name: str) -> None:
    step_names = [step.step_name for step in steps]
    assert step_name in step_names, (
        f"expected workflow step {step_name} but found {step_names}"
    )


def result_context(result) -> str:
    return (
        f"crm_update_status={result.crm_update_status}, "
        f"priority={result.priority}, "
        f"confidence={result.confidence}, "
        f"review_created={result.review_created}, "
        f"review_reasons={result.review_reasons}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
