import sys
from pathlib import Path
from uuid import uuid4


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.lead_intake import intake_lead  # noqa: E402
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_logs import list_workflow_runs  # noqa: E402
from app.services.workflow_steps import list_step_events_by_workflow_run_id  # noqa: E402


TEST_RUN_ID = uuid4().hex[:8]


def main() -> int:
    checks = [
        ("clean lead updates CRM record automatically", check_clean_lead),
        ("high-priority lead applies update with review visibility", check_high_priority_lead),
        ("risky lead blocks sensitive CRM update pending review", check_risky_lead),
        ("lead intake failure creates operational diagnostics", check_failure_observability),
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


def check_clean_lead() -> None:
    request = clean_lead()
    result = intake_lead(request)
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)
    review_items = workflow_review_items(result.workflow_run_id)

    assert result.lead_id, "expected response lead_id"
    assert result.crm_record.crm_record_id, "expected crm_record_id"
    assert result.crm_record.lead_id == result.lead_id, (
        f"expected CRM record lead_id {result.lead_id}, got {result.crm_record.lead_id}"
    )
    assert result.crm_record.company == request.company, (
        f"expected company {request.company!r}, got {result.crm_record.company!r}"
    )
    assert result.crm_update_status == "applied", (
        "expected crm_update_status applied but got "
        f"{result.crm_update_status}. {result_context(result)}"
    )
    assert result.review_created is False, (
        f"expected review_created false but got {result.review_created}. "
        f"{result_context(result)}"
    )
    assert result.crm_record.crm_update_status == "applied", (
        "expected CRM record crm_update_status applied but got "
        f"{result.crm_record.crm_update_status}. {result_context(result)}"
    )
    assert not review_items, (
        f"expected no review item but found {len(review_items)} for workflow_run_id "
        f"{result.workflow_run_id}. {result_context(result)}"
    )
    assert result.lead_score is not None, "expected lead_score"
    assert result.priority, "expected priority"
    assert result.confidence, "expected confidence"
    assert result.recommended_route, "expected recommended_route"
    assert_has_event(events, "workflow_started")
    assert_has_event(events, "lead_received")
    assert_has_event(events, "lead_enriched")
    assert_has_event(events, "lead_scored")
    assert_has_event(events, "route_recommended")
    assert_has_event(events, "crm_update_applied")
    assert_has_event(events, "workflow_completed")
    assert_step_names(
        steps,
        [
            "workflow_started",
            "input_validated",
            "lead_received",
            "lead_enriched",
            "lead_scored",
            "route_recommended",
            "crm_update_evaluated",
            "crm_update_applied",
            "review_item_created_if_required",
            "audit_events_written",
            "workflow_completed",
        ],
    )
    review_step = find_step(steps, "review_item_created_if_required")
    assert review_step.step_status in {"skipped", "success"}, (
        "expected review_item_created_if_required to be skipped or success but got "
        f"{review_step.step_status}"
    )


def check_high_priority_lead() -> None:
    result = intake_lead(high_priority_lead())
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)
    review_items = workflow_review_items(result.workflow_run_id)

    assert result.lead_id, "expected response lead_id"
    assert result.crm_record.crm_record_id, "expected crm_record_id"
    assert result.crm_update_status == "applied_with_review_visibility", (
        "expected applied_with_review_visibility but got "
        f"{result.crm_update_status}. {result_context(result)}"
    )
    assert result.review_created is True, (
        f"expected review item created but got {result.review_created}. "
        f"{result_context(result)}"
    )
    assert result.priority in {"high", "critical"}, (
        f"expected priority high or critical but got {result.priority}. "
        f"{result_context(result)}"
    )
    assert result.recommended_route, "expected recommended_route"
    assert result.crm_record.crm_update_status == "applied_with_review_visibility", (
        "expected CRM record applied_with_review_visibility but got "
        f"{result.crm_record.crm_update_status}. {result_context(result)}"
    )
    assert review_items, f"expected review item created but found none. {result_context(result)}"
    assert_has_event(events, "crm_update_applied_with_review_visibility")
    assert has_event(events, "guardrail_triggered") or has_event(events, "review_created"), (
        "expected guardrail_triggered or review_created audit event but found none"
    )
    assert_has_event(events, "review_created")
    assert_has_event(events, "workflow_completed")
    assert_step_status(steps, "crm_update_applied", "success")
    assert_step_status(steps, "review_item_created_if_required", "success")
    assert_step_status(steps, "audit_events_written", "success")
    assert_step_status(steps, "workflow_completed", "success")


def check_risky_lead() -> None:
    result = intake_lead(risky_lead())
    events = workflow_audit_events(result.workflow_run_id)
    steps = workflow_steps(result.workflow_run_id)
    review_items = workflow_review_items(result.workflow_run_id)

    assert result.crm_update_status == "blocked_pending_review", (
        f"expected blocked_pending_review but got {result.crm_update_status}. "
        f"{result_context(result)}"
    )
    assert result.review_created is True, (
        f"expected review_created true. {result_context(result)}"
    )
    assert result.crm_record.crm_update_status == "blocked_pending_review", (
        "expected CRM record blocked_pending_review but got "
        f"{result.crm_record.crm_update_status}. {result_context(result)}"
    )
    assert "suspicious_or_test_submission" in result.crm_record.risk_flags, (
        f"expected suspicious risk flag, got {result.crm_record.risk_flags}. "
        f"{result_context(result)}"
    )
    assert review_items, (
        f"expected review item for risky lead but found none. {result_context(result)}"
    )
    assert_has_event(events, "crm_update_blocked")
    assert_has_event(events, "guardrail_triggered")
    assert_step_status(steps, "crm_update_blocked", "success")


def check_failure_observability() -> None:
    try:
        intake_lead(failing_enrichment_lead())
    except RuntimeError:
        pass

    failed_run = next(
        run
        for run in reversed(list_workflow_runs())
        if run.workflow_name == "lead_intake_enrichment" and run.status == "failed"
    )
    steps = workflow_steps(failed_run.workflow_run_id)
    failed_step = next(step for step in steps if step.step_status == "failed")

    assert failed_run.failure_step == "lead_enriched", (
        f"expected workflow failure_step lead_enriched but got {failed_run.failure_step}"
    )
    assert failed_step.step_name == "lead_enriched", (
        f"expected failed step lead_enriched but got {failed_step.step_name}"
    )
    assert failed_step.error_type == "RuntimeError", (
        f"expected error_type RuntimeError but got {failed_step.error_type}"
    )
    assert failed_step.error_message, "expected failed step error_message"
    assert failed_step.failure_reason, "expected failed step failure_reason"
    assert failed_step.retryable is True, "expected failed step retryable true"
    assert failed_step.recommended_fix, "expected failed step recommended_fix"


def clean_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Nadia",
        last_name="Patel",
        email=f"nadia.patel+{TEST_RUN_ID}@localgrowth.example",
        company="Local Growth Studio",
        job_title="Operations Manager",
        company_website="https://localgrowth.example",
        company_size="51-200",
        industry="Marketing Services",
        region="EMEA",
        source="webinar",
        message=(
            "We are evaluating CRM cleanup for our sales team. Timing is flexible, "
            "and we are gathering options."
        ),
        pain_points=["CRM cleanup"],
        urgency="60_days",
        budget_context="Planned budget",
        requested_demo=False,
        crm_system="HubSpot",
        notes="Clean lead verification case.",
    )


def high_priority_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Maya",
        last_name="Chen",
        email=f"maya.chen+{TEST_RUN_ID}@northstaranalytics.example",
        company="Northstar Analytics",
        job_title="VP of Sales",
        company_website="https://northstaranalytics.example",
        company_size="201-500",
        industry="Analytics",
        region="North America",
        source="demo_request",
        message=(
            "We want a demo this week. Our reps are spending too much time "
            "qualifying inbound leads and we need better routing before the next campaign launch."
        ),
        pain_points=["Lead routing", "Inbound volume", "Manual qualification"],
        urgency="this_week",
        budget_context="Approved budget",
        requested_demo=True,
        crm_system="HubSpot",
        notes="High-priority verification case.",
    )


def risky_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Test",
        last_name="User",
        email=f"student.test+{TEST_RUN_ID}@example.com",
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
        notes="Risky lead test.",
    )


def failing_enrichment_lead() -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Failure",
        last_name="Case",
        email=f"failure.case+{TEST_RUN_ID}@example.com",
        company="Failure Demo Co",
        job_title="VP of Sales",
        company_size="201-500",
        industry="Software",
        region="North America",
        source="demo_request",
        message="Please simulate_enrichment_failure for this test.",
        pain_points=["Lead routing"],
        urgency="this_week",
        budget_context="Approved budget",
        requested_demo=True,
        crm_system="HubSpot",
        notes="Failure observability test.",
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


def has_event(events, event_type: str) -> bool:
    return any(event.event_type == event_type for event in events)


def assert_has_event(events, event_type: str) -> None:
    event_types = [event.event_type for event in events]
    assert event_type in event_types, (
        f"expected audit event {event_type} but found {event_types}"
    )


def assert_step_names(events, expected_steps: list[str]) -> None:
    names = [event.step_name for event in events]
    for expected_step in expected_steps:
        assert expected_step in names, (
            f"expected step event {expected_step} but found {names}"
        )
    assert all(event.created_at for event in events), "expected created_at on every step event"


def find_step(events, step_name: str):
    for event in events:
        if event.step_name == step_name:
            return event
    names = [event.step_name for event in events]
    raise AssertionError(f"expected step event {step_name} but found {names}")


def assert_step_status(events, step_name: str, expected_status: str) -> None:
    step = find_step(events, step_name)
    assert step.step_status == expected_status, (
        f"expected step {step_name} status {expected_status} but got {step.step_status}"
    )


def result_context(result) -> str:
    return (
        f"crm_update_status={result.crm_update_status}, "
        f"priority={result.priority}, "
        f"confidence={result.confidence}, "
        f"enrichment_confidence={result.enrichment.enrichment_confidence}, "
        f"enrichment_risk_flags={result.enrichment.enrichment_risk_flags}, "
        f"review_created={result.review_created}, "
        f"review_reasons={result.review_reasons}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
