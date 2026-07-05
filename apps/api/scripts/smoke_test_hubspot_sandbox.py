import sys
from argparse import ArgumentParser
from pathlib import Path
from uuid import uuid4


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.services.audit_trail import list_audit_events  # noqa: E402
from app.services.hubspot_adapter import get_hubspot_status  # noqa: E402
from app.services.lead_intake import intake_lead  # noqa: E402
from app.services.review_queue import list_review_items  # noqa: E402
from app.services.workflow_steps import list_step_events_by_workflow_run_id  # noqa: E402


def build_clean_request(run_id: str) -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Nadia",
        last_name="Patel",
        email=f"nadia.patel.{run_id}@localgrowthstudio.com",
        company="Local Growth Studio",
        job_title="Revenue Operations Manager",
        company_website="https://localgrowthstudio.com",
        company_size="51-200",
        industry="Software",
        region="North America",
        source="contact_form",
        message=(
            "We are reviewing ways to improve lead routing and follow up tracking "
            "for our sales team over the next month. We want a structured overview "
            "of how an internal workflow could help managers see ownership and next actions."
        ),
        pain_points=["Lead routing", "Follow-up tracking", "Manager visibility"],
        urgency="30_days",
        budget_context="Planned budget",
        requested_demo=False,
        crm_system="HubSpot",
        notes="Synthetic business inquiry for a controlled HubSpot sync.",
    )


def build_risky_request(run_id: str) -> LeadIntakeRequest:
    return LeadIntakeRequest(
        first_name="Casey",
        last_name="Morgan",
        email=f"student.assignment.{run_id}@learning-lab.com",
        company="Learning Lab",
        job_title="Student Researcher",
        company_website="https://learning-lab.com",
        company_size="1-10",
        industry="Education",
        region="North America",
        source="contact_form",
        message="This is a student school assignment. Please ignore this submission.",
        pain_points=[],
        urgency="unknown",
        budget_context="Unknown",
        requested_demo=False,
        crm_system="None",
        notes="Risky mode intentionally uses suspicious lead signals to prove blocking.",
    )


def print_result(result) -> None:
    audit_events = [
        event
        for event in list_audit_events()
        if event.workflow_run_id == result.workflow_run_id
    ]
    review_items = [
        item
        for item in list_review_items()
        if item.workflow_run_id == result.workflow_run_id
    ]
    step_events = list_step_events_by_workflow_run_id(result.workflow_run_id)
    guardrail_events = [
        event for event in audit_events if event.event_type == "guardrail_triggered"
    ]

    print(f"crm_update_status={result.crm_update_status}")
    print(f"hubspot_sync_status={result.crm_record.hubspot_sync_status}")
    print(f"review_created={result.review_created}")
    print(f"review_reasons={result.review_reasons}")
    print(f"risk_flags={result.crm_record.risk_flags}")
    print(f"hubspot_contact_id={result.crm_record.hubspot_contact_id}")
    print(f"hubspot_company_id={result.crm_record.hubspot_company_id}")
    print(f"hubspot_deal_id={result.crm_record.hubspot_deal_id}")
    print(f"hubspot_task_id={result.crm_record.hubspot_task_id}")
    print(f"hubspot_note_id={result.crm_record.hubspot_note_id}")
    print(f"hubspot_sync_error={result.crm_record.hubspot_sync_error}")
    print(f"crm_record_id={result.crm_record.crm_record_id}")
    print(f"workflow_run_id={result.workflow_run_id}")
    print(f"audit_events={len(audit_events)}")
    print(f"review_items={len(review_items)}")
    print(f"workflow_step_events={len(step_events)}")
    print(f"guardrail_audit_events={len(guardrail_events)}")
    print(f"priority={result.priority}")
    print(f"confidence={result.confidence}")
    print(f"enrichment_confidence={result.enrichment.enrichment_confidence}")


def main() -> int:
    parser = ArgumentParser(
        description="Create or block a synthetic HubSpot sandbox lead intake journey."
    )
    parser.add_argument(
        "--risky",
        action="store_true",
        help="Run a blocked guardrail case instead of the clean sync case.",
    )
    args = parser.parse_args()

    status = get_hubspot_status()
    print(f"adapter_mode={status.adapter_mode}")
    print(f"hubspot_enabled={status.hubspot_enabled}")
    print(f"token_configured={status.token_configured}")
    if (
        status.adapter_mode != "hubspot"
        or not status.hubspot_enabled
        or not status.token_configured
        or status.status != "ready"
    ):
        print("HubSpot sandbox smoke test skipped.")
        print(f"status={status.status}")
        print("Set CRM_ADAPTER_MODE=hubspot, HUBSPOT_ENABLED=true, and HUBSPOT_ACCESS_TOKEN intentionally.")
        return 0

    run_id = uuid4().hex[:8]
    print("WARNING: this will create or update synthetic HubSpot sandbox records.")
    print(f"run_id={run_id}")
    print(f"mode={'risky' if args.risky else 'clean'}")

    request = build_risky_request(run_id) if args.risky else build_clean_request(run_id)
    result = intake_lead(request)
    print_result(result)

    if args.risky:
        if result.crm_record.hubspot_sync_status != "blocked_pending_review":
            print("FAIL: risky mode should be blocked pending review.")
            return 1
        return 0

    expected_sync_statuses = {"synced", "partial_sync"}
    if result.crm_record.hubspot_sync_status not in expected_sync_statuses:
        print("FAIL: clean mode did not sync to HubSpot.")
        return 1
    if not result.crm_record.hubspot_contact_id:
        print("FAIL: clean mode did not return a HubSpot contact id.")
        return 1
    if not result.crm_record.hubspot_company_id:
        print("FAIL: clean mode did not return a HubSpot company id.")
        return 1
    if not result.crm_record.hubspot_deal_id:
        print("FAIL: clean mode did not return a HubSpot deal id.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
