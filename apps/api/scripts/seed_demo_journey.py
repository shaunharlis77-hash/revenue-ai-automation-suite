import argparse
import sys
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.models.audit import AuditEventCreate  # noqa: E402
from app.models.crm_hygiene import CRMHygieneRequest  # noqa: E402
from app.models.follow_up import FollowUpDraftRequest  # noqa: E402
from app.models.lead_scoring import LeadScoringRequest  # noqa: E402
from app.models.meeting_summary import MeetingSummaryRequest  # noqa: E402
from app.models.proposal import ProposalDraftRequest  # noqa: E402
from app.models.review_queue import ReviewDecisionRequest  # noqa: E402
from app.models.workflow_logs import WorkflowRunFailureRequest, WorkflowRunStartRequest  # noqa: E402
from app.services.audit_trail import create_audit_event, list_audit_events  # noqa: E402
from app.services.crm_hygiene import check_crm_hygiene  # noqa: E402
from app.services.database import reset_persistence_tables  # noqa: E402
from app.services.follow_up import draft_follow_up  # noqa: E402
from app.services.lead_scoring import score_lead  # noqa: E402
from app.services.meeting_summary import summarize_meeting  # noqa: E402
from app.services.proposal import draft_proposal  # noqa: E402
from app.services.review_queue import (  # noqa: E402
    approve_review_item,
    list_review_items,
    reject_review_item,
)
from app.services.workflow_logs import (  # noqa: E402
    list_workflow_runs,
    mark_workflow_failure,
    reset_workflow_runs,
    start_workflow_run,
)
from app.services.workflow_steps import (  # noqa: E402
    list_step_events,
    log_step_failure,
    log_step_started,
)


DEMO_METADATA = {"demo_seed": True, "demo_journey": "northstar_analytics"}


def main() -> int:
    args = parse_args()
    if args.reset_local_demo:
        reset_persistence_tables()
        reset_workflow_runs()
        print("Reset local demo persistence tables before seeding.")

    print("Seeding synthetic Northstar Analytics demo journey...")

    lead_result = score_lead(lead_request())

    meeting_result = summarize_meeting(meeting_request())

    follow_up_result = draft_follow_up(
        follow_up_request(
            lead_priority=lead_result.priority,
            deal_stage_recommendation=meeting_result.deal_stage_recommendation,
            pain_points=meeting_result.pain_points,
            objections=meeting_result.objections,
            buying_signals=meeting_result.buying_signals,
            next_steps=meeting_result.next_steps,
            follow_up_due=meeting_result.follow_up_due,
        )
    )
    follow_up_run = latest_run("follow_up_drafting")

    proposal_result = draft_proposal(
        proposal_request(
            lead_priority=lead_result.priority,
            deal_stage_recommendation=meeting_result.deal_stage_recommendation,
            pain_points=meeting_result.pain_points,
            objections=["Pricing and budget review needed before any package discussion."],
            buying_signals=meeting_result.buying_signals,
            next_steps=meeting_result.next_steps,
            follow_up_id=follow_up_result.follow_up_id,
        )
    )
    proposal_run = latest_run("proposal_outline_drafting")

    healthy_hygiene_result = check_crm_hygiene(healthy_crm_request())

    risky_hygiene_result = check_crm_hygiene(risky_crm_request())
    risky_hygiene_run = latest_run("crm_hygiene_deal_risk_monitor")

    add_demo_guardrail_events(proposal_run, risky_hygiene_run)
    apply_demo_review_decisions(
        follow_up_run.workflow_run_id,
        proposal_run.workflow_run_id,
    )
    seed_failure_diagnostic()

    print_summary(
        lead_score=lead_result.lead_score,
        meeting_stage=meeting_result.deal_stage_recommendation,
        follow_up_confidence=follow_up_result.confidence,
        proposal_confidence=proposal_result.confidence,
        healthy_risk=healthy_hygiene_result.risk_level,
        risky_risk=risky_hygiene_result.risk_level,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed a synthetic end-to-end sales AI demo journey."
    )
    parser.add_argument(
        "--reset-local-demo",
        action="store_true",
        help=(
            "Local demo only: clears persistence tables before seeding. "
            "Default behavior is append-only."
        ),
    )
    return parser.parse_args()


def lead_request() -> LeadScoringRequest:
    return LeadScoringRequest(
        lead_id="demo_lead_northstar_maya",
        name="Maya Chen",
        email="maya.chen@northstaranalytics.example",
        company="Northstar Analytics",
        role="VP of Sales",
        company_size="201-500",
        source="demo_request",
        message=(
            "We want a demo this week. Our reps are spending too much time "
            "qualifying inbound leads and we need better routing before the next "
            "campaign launch."
        ),
        timeline="this_week",
        budget="approved",
        current_crm="HubSpot",
        created_at="2026-07-03T09:15:00Z",
    )


def meeting_request() -> MeetingSummaryRequest:
    return MeetingSummaryRequest(
        meeting_id="demo_meeting_northstar_discovery",
        lead_id="demo_lead_northstar_maya",
        deal_id="demo_deal_northstar_expansion",
        rep_name="Alex Rivera",
        contact_name="Maya Chen",
        company="Northstar Analytics",
        meeting_date="2026-07-07T10:00:00Z",
        meeting_source="manual_notes",
        source_platform="manual_notes",
        transcript_type="meeting_minutes",
        transcript=(
            "Maya said the team has rising inbound volume before a campaign launch. "
            "Reps are qualifying leads manually, routing is slow, and ownership is unclear. "
            "Budget is approved and the timeline is this month. Next step: send workflow "
            "outline and schedule technical discovery with revenue operations on Thursday."
        ),
    )


def follow_up_request(
    lead_priority: str,
    deal_stage_recommendation: str,
    pain_points: list[str],
    objections: list[str],
    buying_signals: list[str],
    next_steps: list[str],
    follow_up_due: str,
) -> FollowUpDraftRequest:
    return FollowUpDraftRequest(
        follow_up_id="demo_follow_up_northstar_discovery",
        lead_id="demo_lead_northstar_maya",
        meeting_id="demo_meeting_northstar_discovery",
        rep_name="Alex Rivera",
        contact_name="Maya Chen",
        company="Northstar Analytics",
        lead_priority=lead_priority,
        deal_stage_recommendation=deal_stage_recommendation,
        pain_points=pain_points,
        objections=objections,
        buying_signals=buying_signals,
        next_steps=next_steps,
        follow_up_due=follow_up_due,
        message_channel="email",
        tone="professional",
    )


def proposal_request(
    lead_priority: str,
    deal_stage_recommendation: str,
    pain_points: list[str],
    objections: list[str],
    buying_signals: list[str],
    next_steps: list[str],
    follow_up_id: str,
) -> ProposalDraftRequest:
    return ProposalDraftRequest(
        proposal_id="demo_proposal_northstar_package",
        lead_id="demo_lead_northstar_maya",
        meeting_id="demo_meeting_northstar_discovery",
        follow_up_id=follow_up_id,
        rep_name="Alex Rivera",
        contact_name="Maya Chen",
        company="Northstar Analytics",
        deal_stage_recommendation=deal_stage_recommendation,
        lead_priority=lead_priority,
        pain_points=pain_points,
        objections=objections,
        buying_signals=buying_signals,
        next_steps=next_steps,
        requested_package_type="Lead Scoring and Routing Pilot",
        budget_context="Approved budget, final package details need rep review.",
        implementation_timeline="this_month",
        current_crm="HubSpot",
        risk_areas=["pricing", "budget"],
    )


def healthy_crm_request() -> CRMHygieneRequest:
    return CRMHygieneRequest(
        record_id="demo_crm_northstar_healthy",
        lead_id="demo_lead_northstar_maya",
        deal_id="demo_deal_northstar_expansion",
        company="Northstar Analytics",
        contact_name="Maya Chen",
        deal_stage="qualified_discovery",
        lead_priority="high",
        owner="Alex Rivera",
        last_activity_date="2026-06-28",
        next_step="Send workflow outline and confirm technical discovery attendees.",
        next_step_due_date="2026-07-09",
        follow_up_due="Thursday",
        proposal_status="not_started",
        human_review_status="not_required",
        crm_fields={
            "industry": "Analytics",
            "company_size": "201-500",
            "current_crm": "HubSpot",
            "lead_source": "demo_request",
        },
        open_risks=[],
        days_in_stage=6,
        deal_value_band="mid_market",
    )


def risky_crm_request() -> CRMHygieneRequest:
    return CRMHygieneRequest(
        record_id="demo_crm_northstar_risky",
        lead_id="demo_lead_northstar_maya",
        deal_id="demo_deal_northstar_expansion",
        company="Northstar Analytics",
        contact_name="Maya Chen",
        deal_stage="solution_review",
        lead_priority="high",
        owner="",
        last_activity_date="2026-05-20",
        next_step="",
        next_step_due_date=None,
        follow_up_due="",
        proposal_status="pending",
        human_review_status="incomplete",
        crm_fields={
            "industry": None,
            "company_size": "201-500",
            "current_crm": "HubSpot",
            "lead_source": None,
        },
        open_risks=["pricing review needed", "implementation timeline needs validation"],
        days_in_stage=52,
        deal_value_band="mid_market",
    )


def add_demo_guardrail_events(proposal_run, risky_hygiene_run) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=proposal_run.workflow_run_id,
            workflow_name=proposal_run.workflow_name,
            entity_type="proposal",
            entity_id="demo_proposal_northstar_package",
            event_type="guardrail_triggered",
            event_source="demo_seed",
            actor="system",
            guardrails_triggered=["pricing_or_budget_review_required"],
            human_review_required=True,
            metadata_json=DEMO_METADATA,
        )
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=risky_hygiene_run.workflow_run_id,
            workflow_name=risky_hygiene_run.workflow_name,
            entity_type="crm_record",
            entity_id="demo_crm_northstar_risky",
            event_type="guardrail_triggered",
            event_source="demo_seed",
            actor="system",
            guardrails_triggered=["high_risk_deal_review_required"],
            human_review_required=True,
            metadata_json=DEMO_METADATA,
        )
    )


def apply_demo_review_decisions(follow_up_run_id: str, proposal_run_id: str) -> None:
    items = list_review_items()
    follow_up_item = next(
        (
            item
            for item in items
            if item.workflow_run_id == follow_up_run_id
            and item.status == "pending"
            and item.review_type == "follow_up_draft"
        ),
        None,
    )
    proposal_item = next(
        (
            item
            for item in items
            if item.workflow_run_id == proposal_run_id
            and item.status == "pending"
            and item.review_type == "proposal_outline"
        ),
        None,
    )

    if follow_up_item:
        approve_review_item(
            follow_up_item.review_item_id,
            ReviewDecisionRequest(
                actor="sales_manager",
                decision_reason="Demo approval: draft is accurate for rep review.",
            ),
        )

    if proposal_item:
        reject_review_item(
            proposal_item.review_item_id,
            ReviewDecisionRequest(
                actor="sales_manager",
                decision_reason=(
                    "Demo rejection: package outline needs pricing language cleaned up "
                    "before customer use."
                ),
            ),
        )


def seed_failure_diagnostic() -> None:
    run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="demo_notification_guardrail_check",
            input_reference="demo_notification_check_001",
        )
    )
    log_step_started(
        run.workflow_run_id,
        run.workflow_name,
        "workflow_started",
        1,
        "demo_diagnostic",
        "demo_notification_check_001",
        DEMO_METADATA,
    )
    log_step_failure(
        run.workflow_run_id,
        run.workflow_name,
        "notification_precheck",
        RuntimeError("Demo failure: notification channel is not configured."),
        2,
        "demo_diagnostic",
        "demo_notification_check_001",
        failure_reason="Notification was blocked because no real integration is connected.",
        retryable=False,
        recommended_fix=(
            "For the demo, leave notification disabled. Before production, configure "
            "an approved notification channel and retry the precheck."
        ),
        metadata_json=DEMO_METADATA,
    )
    mark_workflow_failure(
        run.workflow_run_id,
        WorkflowRunFailureRequest(
            failure_step="notification_precheck",
            failure_reason="Demo failure: notification channel is not configured.",
            input_reference="demo_notification_check_001",
            human_review_required=True,
            next_action="Maintainer should verify notification configuration before enabling sends.",
        ),
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="demo_diagnostic",
            entity_id="demo_notification_check_001",
            event_type="workflow_failed",
            event_source="demo_seed",
            actor="system",
            guardrails_triggered=["external_notification_not_configured"],
            human_review_required=True,
            metadata_json=DEMO_METADATA,
        )
    )


def latest_run(workflow_name: str):
    return next(
        run
        for run in reversed(list_workflow_runs())
        if run.workflow_name == workflow_name
    )


def print_summary(
    lead_score: int,
    meeting_stage: str,
    follow_up_confidence: str,
    proposal_confidence: str,
    healthy_risk: str,
    risky_risk: str,
) -> None:
    review_items = list_review_items()
    audit_events = list_audit_events()
    step_events = list_step_events()

    print("")
    print("Demo seed complete.")
    print(f"Lead score: {lead_score}")
    print(f"Meeting stage recommendation: {meeting_stage}")
    print(f"Follow-up confidence: {follow_up_confidence}")
    print(f"Proposal confidence: {proposal_confidence}")
    print(f"Healthy CRM risk: {healthy_risk}")
    print(f"Risky CRM risk: {risky_risk}")
    print(f"Review items in database: {len(review_items)}")
    print(f"Audit events in database: {len(audit_events)}")
    print(f"Workflow step events in database: {len(step_events)}")
    print("")
    print("Open after seeding:")
    print("  http://localhost:3000/review-queue")
    print("  http://localhost:3000/audit-trail")
    print("  http://localhost:8000/audit/events")
    print("  http://localhost:8000/review/items")
    print("  http://localhost:8000/logs/workflow-steps")


if __name__ == "__main__":
    raise SystemExit(main())
