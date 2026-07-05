import argparse
import os
import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

os.environ["CRM_ADAPTER_MODE"] = "mock"
os.environ["HUBSPOT_ENABLED"] = "false"
os.environ["HUBSPOT_ACCESS_TOKEN"] = ""
os.environ["N8N_FAILURE_WEBHOOK_URL"] = ""

from app.config.settings import get_settings  # noqa: E402
from app.models.audit import AuditEventCreate  # noqa: E402
from app.models.crm_hygiene import CRMHygieneRequest  # noqa: E402
from app.models.follow_up import FollowUpDraftRequest  # noqa: E402
from app.models.lead_intake import LeadIntakeRequest  # noqa: E402
from app.models.proposal import ProposalDraftRequest  # noqa: E402
from app.models.review_queue import ReviewDecisionRequest, ReviewItemCreate  # noqa: E402
from app.services.audit_trail import create_audit_event, list_audit_events  # noqa: E402
from app.services.crm_hygiene import check_crm_hygiene  # noqa: E402
from app.services.database import encode_json, get_connection, reset_persistence_tables  # noqa: E402
from app.services.follow_up import draft_follow_up  # noqa: E402
from app.services.lead_intake import intake_lead  # noqa: E402
from app.services.mock_crm_adapter import get_lead_records  # noqa: E402
from app.services.notifications import list_notification_events  # noqa: E402
from app.services.proposal import draft_proposal  # noqa: E402
from app.services.review_queue import (  # noqa: E402
    approve_review_item,
    create_review_item,
    list_review_items,
    reject_review_item,
)
from app.services.workflow_logs import (  # noqa: E402
    WorkflowRunFailureRequest,
    WorkflowRunStartRequest,
    mark_workflow_failure,
    start_workflow_run,
)
from app.services.workflow_steps import list_step_events, log_step_failure  # noqa: E402


SALES_TEAM = [
    {
        "id": "rep_maya_chen",
        "name": "Maya Chen",
        "email": "maya.chen@northstar-analytics.com",
    },
    {
        "id": "rep_daniel_brooks",
        "name": "Daniel Brooks",
        "email": "daniel.brooks@brooks-revenue.com",
    },
    {
        "id": "rep_priya_nair",
        "name": "Priya Nair",
        "email": "priya.nair@flowlineops.com",
    },
    {
        "id": "rep_ethan_jacobs",
        "name": "Ethan Jacobs",
        "email": "ethan.jacobs@velocityworks.com",
    },
]


COMPANIES = [
    ("Northstar Analytics", "Maya", "Chen", "VP of Sales", "201-500", "Software"),
    ("Flowline Ops", "Priya", "Nair", "Head of Revenue Operations", "51-200", "Technology"),
    ("Local Growth Studio", "Nadia", "Patel", "Founder", "11-50", "Marketing"),
    ("RapidScale Cloud", "Marcus", "Reed", "Director of Commercial Operations", "501-1000", "Software"),
    ("Beacon Manufacturing", "Elena", "Torres", "Sales Operations Manager", "201-500", "Manufacturing"),
    ("Summit Enablement", "Owen", "Grant", "Growth Manager", "51-200", "Consulting"),
    ("ClearPath Logistics", "Ari", "Morgan", "Revenue Operations Manager", "201-500", "Logistics"),
    ("Harbor Health Systems", "Leah", "Stone", "VP of Sales", "501-1000", "Healthcare"),
]


def main() -> int:
    args = parse_args()
    seed_dashboard_demo_data(args.count, args.reset_demo)
    return 0


def seed_dashboard_demo_data(count: int = 40, reset_demo: bool = False) -> dict[str, int]:
    get_settings.cache_clear()
    if reset_demo:
        reset_persistence_tables()

    count = max(1, count)
    responses = seed_lead_intake(count)
    seed_follow_ups(responses)
    seed_proposals(responses)
    seed_crm_hygiene(responses)
    create_owner_assigned_review_items(responses)
    decide_some_reviews()
    add_mock_sync_history()
    add_operational_failure()
    add_missing_next_step_examples()

    records = get_lead_records()
    reviews = list_review_items()
    audits = list_audit_events()
    steps = list_step_events()
    notifications = list_notification_events()

    print("Dashboard demo data seeded in forced mock mode.")
    print(f"requested_count={count}")
    print(f"crm_records={len(records)}")
    print(f"audit_events={len(audits)}")
    print(f"workflow_step_events={len(steps)}")
    print(f"review_items={len(reviews)}")
    print(f"notifications={len(notifications)}")
    print("hubspot_calls=0")
    return {
        "requested_count": count,
        "crm_records": len(records),
        "audit_events": len(audits),
        "workflow_step_events": len(steps),
        "review_items": len(reviews),
        "notifications": len(notifications),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed local dashboard demo data without calling HubSpot."
    )
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Local/demo only: clear persisted demo tables before seeding.",
    )
    return parser.parse_args()


def seed_lead_intake(count: int):
    responses = []
    for index in range(count):
        try:
            responses.append(intake_lead(build_lead_request(index)))
        except Exception:
            # One controlled failure case is added separately so bulk history
            # stays predictable for dashboard presentation.
            continue
    return responses


def build_lead_request(index: int) -> LeadIntakeRequest:
    company, first_name, last_name, role, size, industry = COMPANIES[index % len(COMPANIES)]
    variant = index % 8
    rep = SALES_TEAM[index % len(SALES_TEAM)]
    local = f"{first_name.lower()}.{last_name.lower()}.{index + 1}"

    if variant in {0, 3}:
        return LeadIntakeRequest(
            first_name=first_name,
            last_name=last_name,
            email=f"{local}@{domain_for(company)}",
            company=company,
            job_title=role,
            company_website=f"https://www.{domain_for(company)}",
            company_size=size,
            industry=industry,
            region="North America",
            source="demo_request",
            message=(
                "We need help with lead scoring, routing, follow-up automation, "
                "and inbound volume before the next sales campaign."
            ),
            pain_points=["Lead scoring", "Lead routing", "Inbound volume"],
            urgency="this_week" if variant == 0 else "urgent",
            budget_context="Approved budget",
            requested_demo=True,
            crm_system="HubSpot",
            notes=f"Routed owner: {rep['name']}.",
        )

    if variant in {1, 5}:
        return LeadIntakeRequest(
            first_name=first_name,
            last_name=last_name,
            email=f"{local}@{domain_for(company)}",
            company=company,
            job_title=role,
            company_website=f"https://www.{domain_for(company)}",
            company_size=size,
            industry=industry,
            region="North America",
            source="pricing_page",
            message=(
                "We are comparing options for CRM cleanup, lead handoff quality, "
                "and manager visibility. Budget is planned for this quarter."
            ),
            pain_points=["CRM cleanup", "Lead handoff quality", "Manager visibility"],
            urgency="30_days",
            budget_context="Planned budget",
            requested_demo=False,
            crm_system="Salesforce" if variant == 1 else "Pipedrive",
            notes=f"Assigned to {rep['name']} for qualification.",
        )

    if variant == 2:
        return LeadIntakeRequest(
            first_name=first_name,
            last_name=last_name,
            email=f"{local}@{domain_for(company)}",
            company=company,
            job_title="Operations Manager",
            company_website=f"https://www.{domain_for(company)}",
            company_size=size,
            industry=industry,
            region="North America",
            source="contact_form",
            message="Can you send a short overview of how sales workflow automation works?",
            pain_points=[],
            urgency="unknown",
            budget_context="unknown",
            requested_demo=False,
            crm_system="unknown",
            notes=f"Light qualification owner: {rep['name']}.",
        )

    if variant == 4:
        return LeadIntakeRequest(
            first_name=first_name,
            last_name=last_name,
            email=f"{local}@{domain_for(company)}",
            company=company,
            job_title=role,
            company_website=f"https://www.{domain_for(company)}",
            company_size=size,
            industry=industry,
            region="North America",
            source="partner_referral",
            message=(
                "Our reps need cleaner handoffs and a lightweight way to identify "
                "which inbound leads need same-day attention."
            ),
            pain_points=["Lead handoff quality", "Rep workload"],
            urgency="30_days",
            budget_context="Planned budget",
            requested_demo=False,
            crm_system="HubSpot",
            notes=f"Partner referred lead. Owner {rep['name']}.",
        )

    if variant == 6:
        return LeadIntakeRequest(
            first_name=first_name,
            last_name=last_name,
            email=f"{local}@{domain_for(company)}",
            company=company,
            job_title=role,
            company_website=f"https://www.{domain_for(company)}",
            company_size="unknown",
            industry=industry,
            region="North America",
            source="contact_form",
            message="We may need help later but are still defining the process.",
            pain_points=[],
            urgency="unknown",
            budget_context="unknown",
            requested_demo=False,
            crm_system="unknown",
            notes="Missing company size and timing should reduce confidence.",
        )

    return LeadIntakeRequest(
        first_name="Jamie",
        last_name="Rivera",
        email=f"jamie.rivera.{index + 1}@academy-mail.com",
        company="Academy Research Group",
        job_title="Student Researcher",
        company_website="https://www.academy-mail.com",
        company_size="1-10",
        industry="Education",
        region="North America",
        source="contact_form",
        message="I am a student working on a school assignment. Please ignore this sales request.",
        pain_points=[],
        urgency="none",
        budget_context="none",
        requested_demo=False,
        crm_system="unknown",
        notes="Intentionally suspicious local seed record for blocked-review demo.",
    )


def seed_follow_ups(responses) -> None:
    for index, response in enumerate(responses[: max(6, len(responses) // 4)]):
        company = response.crm_record.company
        contact = response.crm_record.contact_name or "Sales Contact"
        draft_follow_up(
            FollowUpDraftRequest(
                follow_up_id=f"demo_follow_up_{index + 1:03d}",
                lead_id=response.lead_id,
                meeting_id=f"demo_meeting_{index + 1:03d}",
                rep_name=SALES_TEAM[index % len(SALES_TEAM)]["name"],
                contact_name=contact,
                company=company,
                lead_priority=response.priority,
                deal_stage_recommendation="qualified_discovery",
                pain_points=["Lead routing", "Follow-up automation"],
                objections=["pricing concern"] if index % 5 == 1 else [],
                buying_signals=["Clear next step", "CRM context"],
                next_steps=[]
                if index % 6 == 0
                else ["Send recap", "Schedule workflow review"],
                follow_up_due="today" if response.priority in {"high", "critical"} else "next_week",
                message_channel="email",
                tone="professional",
            )
        )


def seed_proposals(responses) -> None:
    for index, response in enumerate(responses[: max(4, len(responses) // 6)]):
        draft_proposal(
            ProposalDraftRequest(
                proposal_id=f"demo_proposal_{index + 1:03d}",
                lead_id=response.lead_id,
                meeting_id=f"demo_meeting_{index + 1:03d}",
                follow_up_id=f"demo_follow_up_{index + 1:03d}",
                rep_name=SALES_TEAM[index % len(SALES_TEAM)]["name"],
                contact_name=response.crm_record.contact_name or "Sales Contact",
                company=response.crm_record.company,
                deal_stage_recommendation="solution_review",
                lead_priority=response.priority,
                pain_points=["Lead scoring", "CRM cleanup", "Routing"],
                objections=["security review needed"] if index % 4 == 2 else [],
                buying_signals=["Budget context shared", "Stakeholder review requested"],
                next_steps=["Review package outline", "Confirm rollout plan"],
                requested_package_type="Sales workflow automation package",
                budget_context="Approved budget" if index % 3 != 1 else "Budget sensitivity",
                implementation_timeline="30 days" if index % 4 != 3 else "urgent",
                current_crm="HubSpot",
                risk_areas=["security"] if index % 4 == 2 else [],
            )
        )


def seed_crm_hygiene(responses) -> None:
    records = get_lead_records()
    for index, record in enumerate(records[: max(8, len(records) // 3)]):
        owner = SALES_TEAM[index % len(SALES_TEAM)]["name"]
        risky = index % 4 in {1, 2}
        critical = index % 9 == 0
        check_crm_hygiene(
            CRMHygieneRequest(
                record_id=record.crm_record_id,
                lead_id=record.lead_id,
                deal_id=f"deal_demo_{index + 1:03d}",
                company=record.company,
                contact_name=record.contact_name or "Sales Contact",
                deal_stage="qualified_discovery" if not critical else "solution_review",
                lead_priority=record.priority,
                owner=None if critical else owner,
                last_activity_date="2026-06-01" if risky or critical else "2026-07-01",
                next_step=None if risky or critical else "Send recap and confirm next meeting",
                next_step_due_date=None if risky else "2026-07-08",
                follow_up_due=None if record.priority in {"high", "critical"} and risky else "2026-07-08",
                proposal_status="pending" if index % 5 == 0 else "not_started",
                human_review_status="incomplete" if index % 5 == 0 else "not_required",
                crm_fields={
                    "owner": None if critical else owner,
                    "next_step": None if risky or critical else "Defined",
                    "budget": "approved" if index % 3 == 0 else None,
                    "timeline": "30 days" if not risky else None,
                },
                open_risks=["high_risk_deal_review_required"] if critical else [],
                days_in_stage=55 if critical else (36 if risky else 8),
                deal_value_band="enterprise" if critical else "mid_market",
            )
        )


def create_owner_assigned_review_items(responses) -> None:
    if not responses:
        return

    for index, response in enumerate(responses[:4]):
        rep = SALES_TEAM[index % len(SALES_TEAM)]
        create_review_item(
            ReviewItemCreate(
                workflow_run_id=response.workflow_run_id,
                workflow_name="lead_intake_enrichment",
                entity_type="lead",
                entity_id=response.lead_id,
                company=response.crm_record.company,
                contact_name=response.crm_record.contact_name,
                review_type="lead_routing",
                title=f"Manager visibility for {response.crm_record.company}",
                priority=response.priority,
                risk_level="medium",
                review_reasons=["High-priority routed lead should be visible to the owner."],
                proposed_action=response.next_best_action,
                proposed_output=response.recommended_route,
                assigned_to=rep["name"],
                metadata_json={
                    "demo_seed": True,
                    "crm_record_id": response.crm_record.crm_record_id,
                    "routed_owner_id": rep["id"],
                    "routed_owner_name": rep["name"],
                    "routed_owner_email": rep["email"],
                },
            )
        )

    create_review_item(
        ReviewItemCreate(
            workflow_run_id=responses[-1].workflow_run_id,
            workflow_name="crm_hygiene_deal_risk_monitor",
            entity_type="crm_record",
            entity_id=responses[-1].crm_record.crm_record_id,
            company=responses[-1].crm_record.company,
            contact_name=responses[-1].crm_record.contact_name,
            review_type="high_risk_deal",
            title="Unassigned high-risk CRM update needs review",
            priority="high",
            risk_level="high",
            review_reasons=["Risky sales item has no assigned owner."],
            proposed_action="Assign owner and review blocked update.",
            proposed_output="CRM update remains blocked pending review.",
            metadata_json={
                "demo_seed": True,
                "crm_record_id": responses[-1].crm_record.crm_record_id,
                "manager_fallback_expected": True,
            },
        )
    )


def decide_some_reviews() -> None:
    pending = list_review_items()
    for item in pending[:6]:
        approve_review_item(
            item.review_item_id,
            ReviewDecisionRequest(
                actor="demo_sales_manager",
                decision_reason="Approved for interview demo history.",
            ),
        )
    for item in list_review_items()[6:10]:
        reject_review_item(
            item.review_item_id,
            ReviewDecisionRequest(
                actor="demo_sales_manager",
                decision_reason="Rejected to show review quality control.",
            ),
        )


def add_mock_sync_history() -> None:
    records = get_lead_records()
    with get_connection() as connection:
        for index, record in enumerate(records[:8]):
            if index in {1, 5}:
                status = "partial_sync"
                error = "Mock optional activity failed after core record sync."
            elif index == 3:
                status = "failed"
                error = "Mock validation failure for optional external activity."
            else:
                status = "skipped_mock_mode"
                error = None
            connection.execute(
                """
                UPDATE crm_lead_records
                SET hubspot_sync_status = ?, hubspot_sync_error = ?,
                    metadata_json = ?
                WHERE crm_record_id = ?
                """,
                (
                    status,
                    error,
                    encode_json(
                        {
                            **record.metadata_json,
                            "demo_seed": True,
                            "mock_sync_history": status,
                        }
                    ),
                    record.crm_record_id,
                ),
            )
        connection.commit()

    for record in records[:3]:
        create_audit_event(
            AuditEventCreate(
                workflow_run_id=record.metadata_json.get("workflow_run_id"),
                workflow_name="hubspot_sync",
                entity_type="crm_record",
                entity_id=record.crm_record_id,
                event_type="hubspot_sync_failed"
                if record.hubspot_sync_status == "failed"
                else "hubspot_sync_completed",
                event_source="dashboard_demo_seed",
                actor="system",
                output_reference=record.crm_record_id,
                human_review_required=False,
                metadata_json={
                    "demo_seed": True,
                    "adapter_mode": "mock",
                    "safe_mock_history": True,
                },
            )
        )


def add_missing_next_step_examples() -> None:
    records = get_lead_records()
    with get_connection() as connection:
        for record in records[-4:]:
            connection.execute(
                """
                UPDATE crm_lead_records
                SET next_best_action = ?, metadata_json = ?
                WHERE crm_record_id = ?
                """,
                (
                    "missing",
                    encode_json(
                        {
                            **record.metadata_json,
                            "demo_seed": True,
                            "missing_next_step_demo": True,
                        }
                    ),
                    record.crm_record_id,
                ),
            )
        connection.commit()


def add_operational_failure() -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="dashboard_demo_seed_failure_check",
            input_reference="dashboard_demo_failure_001",
        )
    )
    log_step_failure(
        run.workflow_run_id,
        "dashboard_demo_seed_failure_check",
        "mock_external_activity_sync",
        RuntimeError("Demo failure: optional activity sync timed out."),
        entity_type="crm_record",
        entity_id="dashboard_demo_failure_001",
        failure_reason="Optional mock activity sync timed out during dashboard seed.",
        retryable=True,
        recommended_fix="Retry the optional activity sync after checking adapter health.",
        metadata_json={"demo_seed": True},
    )
    mark_workflow_failure(
        run.workflow_run_id,
        WorkflowRunFailureRequest(
            failure_step="mock_external_activity_sync",
            failure_reason="Optional mock activity sync timed out during dashboard seed.",
            input_reference="dashboard_demo_failure_001",
            human_review_required=False,
            next_action="Admin should inspect operational logs before retrying optional sync.",
        ),
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name="dashboard_demo_seed_failure_check",
            entity_type="crm_record",
            entity_id="dashboard_demo_failure_001",
            event_type="workflow_failed",
            event_source="dashboard_demo_seed",
            actor="system",
            human_review_required=False,
            metadata_json={
                "demo_seed": True,
                "business_impact": "No customer-facing action was taken.",
            },
        )
    )


def domain_for(company: str) -> str:
    return company.lower().replace(" ", "").replace("&", "and") + ".com"


if __name__ == "__main__":
    raise SystemExit(main())
