from uuid import uuid4

from app.models.audit import AuditEventCreate
from app.models.crm_hygiene import CRMHygieneRequest
from app.models.demo_lifecycle import (
    FollowUpOutcomeRequest,
    FollowUpOutcomeResponse,
    FullDemoStoryResponse,
    MeetingAttachmentRequest,
    MeetingLifecycleResponse,
)
from app.models.follow_up import FollowUpDraftRequest
from app.models.lead_intake import LeadIntakeRequest
from app.models.meeting_summary import MeetingSummaryRequest
from app.models.proposal import ProposalDraftRequest
from app.models.review_queue import ReviewDecisionRequest, ReviewItem, ReviewItemCreate
from app.models.workflow_logs import WorkflowRunStartRequest, WorkflowRunSuccessRequest
from app.services.audit_trail import create_audit_event, list_audit_events
from app.services.crm_hygiene import check_crm_hygiene
from app.services.database import decode_json, encode_json, get_connection, reset_persistence_tables
from app.services.follow_up import draft_follow_up
from app.services.lead_intake import intake_lead
from app.services.meeting_summary import summarize_meeting
from app.services.mock_crm_adapter import append_crm_activity, get_lead_record, get_lead_record_activities
from app.services.notifications import list_notification_events
from app.services.proposal import draft_proposal
from app.services.review_queue import approve_review_item, create_review_item, list_review_items
from app.services.workflow_logs import mark_workflow_success, start_workflow_run
from app.services.workflow_steps import list_step_events, log_step_failure, log_step_started, log_step_success


WORKFLOW_NAME = "full_demo_story"


def attach_meeting_to_crm_record(
    crm_record_id: str,
    request: MeetingAttachmentRequest,
    workflow_run_id: str | None = None,
) -> str:
    record = get_lead_record(crm_record_id)
    run_id = workflow_run_id or f"meeting_attach_{uuid4()}"
    log_step_started(
        run_id,
        WORKFLOW_NAME,
        "meeting_attachment_started",
        entity_type="crm_record",
        entity_id=crm_record_id,
    )
    activity = append_crm_activity(
        crm_record_id=record.crm_record_id,
        lead_id=record.lead_id,
        activity_type="meeting_attached",
        activity_title=request.meeting_title,
        activity_body=request.notes or request.transcript or "Meeting attached to CRM record.",
        activity_status="created",
        workflow_run_id=run_id,
        metadata_json={
            "meeting_timestamp": request.meeting_timestamp,
            "attendees": request.attendees,
            "owner": request.owner,
            "source": request.source,
            "demo_lifecycle": True,
        },
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            entity_type="crm_record",
            entity_id=crm_record_id,
            event_type="meeting_attached",
            event_source="demo_lifecycle",
            actor="system",
            output_reference=activity.crm_activity_id,
            metadata_json={"source": request.source},
        )
    )
    log_step_success(
        run_id,
        WORKFLOW_NAME,
        "meeting_attachment_completed",
        entity_type="crm_record",
        entity_id=crm_record_id,
        metadata_json={"crm_activity_id": activity.crm_activity_id},
    )
    return activity.crm_activity_id


def process_meeting_and_writeback(
    crm_record_id: str,
    request: MeetingAttachmentRequest,
) -> MeetingLifecycleResponse:
    record = get_lead_record(crm_record_id)
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="meeting_lifecycle_writeback",
            input_reference=crm_record_id,
        )
    )
    meeting_activity_id = attach_meeting_to_crm_record(
        crm_record_id, request, workflow_run.workflow_run_id
    )
    meeting = MeetingSummaryRequest(
        meeting_id=f"meeting_{uuid4()}",
        lead_id=record.lead_id,
        deal_id=record.hubspot_deal_id or f"deal_{record.lead_id}",
        rep_name=request.owner or "Alex Rivera",
        contact_name=record.contact_name or "Maya Chen",
        company=record.company,
        meeting_date=request.meeting_timestamp,
        meeting_source=request.source,
        source_platform=request.source,
        transcript_type="meeting_minutes",
        transcript=request.transcript or request.notes or "",
    )
    summary = summarize_meeting(meeting)
    summary_activity = append_crm_activity(
        crm_record_id=record.crm_record_id,
        lead_id=record.lead_id,
        activity_type="meeting_summary_created",
        activity_title="Meeting summary prepared",
        activity_body=summary.crm_note,
        activity_status="created",
        workflow_run_id=workflow_run.workflow_run_id,
        metadata_json={
            "meeting_id": summary.meeting_id,
            "deal_stage_recommendation": summary.deal_stage_recommendation,
            "next_steps": summary.next_steps,
        },
    )
    review_item_ids: list[str] = []
    if summary.human_review_required:
        item = create_review_item(
            ReviewItemCreate(
                workflow_run_id=workflow_run.workflow_run_id,
                workflow_name="meeting_lifecycle_writeback",
                entity_type="crm_record",
                entity_id=crm_record_id,
                company=record.company,
                contact_name=record.contact_name,
                review_type="deal_stage_change",
                title=f"Review meeting stage recommendation for {record.company}",
                priority=record.priority,
                risk_level="medium",
                review_reasons=[summary.reasoning],
                proposed_action=f"Review deal stage recommendation: {summary.deal_stage_recommendation}",
                proposed_output=summary.crm_note,
                metadata_json={
                    "crm_record_id": crm_record_id,
                    "meeting_id": summary.meeting_id,
                    "demo_lifecycle": True,
                },
            )
        )
        review_item_ids.append(item.review_item_id)
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=workflow_run.workflow_run_id,
            workflow_name="meeting_lifecycle_writeback",
            entity_type="crm_record",
            entity_id=crm_record_id,
            event_type="meeting_summary_crm_writeback",
            event_source="demo_lifecycle",
            actor="system",
            output_reference=summary_activity.crm_activity_id,
            human_review_required=summary.human_review_required,
            metadata_json={"deal_stage_recommendation": summary.deal_stage_recommendation},
        )
    )
    mark_workflow_success(
        workflow_run.workflow_run_id,
        WorkflowRunSuccessRequest(
            output_summary="Meeting attached and CRM summary activity created.",
            human_review_required=summary.human_review_required,
            next_action="Rep reviews stage recommendation and next steps.",
        ),
    )
    return MeetingLifecycleResponse(
        workflow_run_id=workflow_run.workflow_run_id,
        crm_record_id=crm_record_id,
        meeting_activity_id=meeting_activity_id,
        meeting_summary_status="written_to_crm_activity",
        meeting_summary_activity_id=summary_activity.crm_activity_id,
        deal_stage_recommendation=summary.deal_stage_recommendation,
        review_item_ids=review_item_ids,
    )


def capture_follow_up_outcome(
    crm_record_id: str, request: FollowUpOutcomeRequest
) -> FollowUpOutcomeResponse:
    record = get_lead_record(crm_record_id)
    workflow_run = start_workflow_run(
        WorkflowRunStartRequest(
            workflow_name="follow_up_outcome_capture",
            input_reference=crm_record_id,
        )
    )
    activity = append_crm_activity(
        crm_record_id=record.crm_record_id,
        lead_id=record.lead_id,
        activity_type="follow_up_outcome_captured",
        activity_title=f"Follow-up outcome: {request.outcome}",
        activity_body=request.notes or "Follow-up outcome captured.",
        activity_status="created",
        workflow_run_id=workflow_run.workflow_run_id,
        metadata_json={
            "outcome": request.outcome,
            "next_step": request.next_step,
            "next_step_due_date": request.next_step_due_date,
        },
    )
    task_id: str | None = None
    if request.next_step:
        task = append_crm_activity(
            crm_record_id=record.crm_record_id,
            lead_id=record.lead_id,
            activity_type="crm_task_created",
            activity_title="Rep next-step reminder",
            activity_body=request.next_step,
            activity_status="created",
            workflow_run_id=workflow_run.workflow_run_id,
            metadata_json={"due": request.next_step_due_date},
        )
        task_id = task.crm_activity_id
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=workflow_run.workflow_run_id,
            workflow_name="follow_up_outcome_capture",
            entity_type="crm_record",
            entity_id=crm_record_id,
            event_type="follow_up_outcome_captured",
            event_source="demo_lifecycle",
            actor="system",
            output_reference=activity.crm_activity_id,
            metadata_json={"outcome": request.outcome},
        )
    )
    log_step_success(
        workflow_run.workflow_run_id,
        "follow_up_outcome_capture",
        "follow_up_outcome_written_to_crm",
        entity_type="crm_record",
        entity_id=crm_record_id,
        metadata_json={"outcome": request.outcome},
    )
    mark_workflow_success(
        workflow_run.workflow_run_id,
        WorkflowRunSuccessRequest(
            output_summary=f"Follow-up outcome captured: {request.outcome}.",
            next_action=request.next_step,
        ),
    )
    return FollowUpOutcomeResponse(
        workflow_run_id=workflow_run.workflow_run_id,
        crm_record_id=crm_record_id,
        outcome=request.outcome,
        activity_id=activity.crm_activity_id,
        next_step_task_id=task_id,
    )


def run_full_demo_story(reset_demo: bool = False) -> FullDemoStoryResponse:
    if reset_demo:
        reset_persistence_tables()

    before = snapshot_counts()
    demo_run_id = f"demo_run_{uuid4()}"

    lead = intake_lead(
        LeadIntakeRequest(
            first_name="Maya",
            last_name="Chen",
            email=f"maya.chen.{str(uuid4())[:8]}@northstar-analytics.com",
            company="Northstar Analytics",
            job_title="VP of Sales",
            company_website="https://northstar-analytics.com",
            company_size="201-500",
            industry="Software",
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
            notes=f"Phase 7 demo run {demo_run_id}",
        )
    )
    crm_record_id = lead.crm_record.crm_record_id

    meeting = process_meeting_and_writeback(
        crm_record_id,
        MeetingAttachmentRequest(
            meeting_title="Northstar discovery call",
            meeting_timestamp="2026-07-08T15:00:00Z",
            source="demo",
            owner="Alex Rivera",
            attendees=["Maya Chen", "Alex Rivera"],
            notes=(
                "Maya confirmed approved budget and a this-month timeline. "
                "Main pains are manual qualification, lead routing, slow response times, "
                "and unclear ownership. Next step is to send a workflow outline and schedule technical discovery."
            ),
        ),
    )

    follow_up = draft_follow_up(
        FollowUpDraftRequest(
            follow_up_id=f"follow_up_{uuid4()}",
            lead_id=lead.lead_id,
            meeting_id=meeting.meeting_activity_id,
            rep_name="Alex Rivera",
            contact_name="Maya Chen",
            company="Northstar Analytics",
            lead_priority=lead.priority,
            deal_stage_recommendation=meeting.deal_stage_recommendation,
            pain_points=["Manual qualification", "Lead routing", "Slow response times"],
            objections=[],
            buying_signals=["Approved budget", "Clear timeline", "Technical discovery requested"],
            next_steps=["Send workflow outline", "Schedule technical discovery"],
            follow_up_due="today",
            message_channel="email",
            tone="professional",
        )
    )
    follow_up_review = latest_review_item_for_entity("follow_up", follow_up.follow_up_id)
    add_review_metadata(follow_up_review.review_item_id, {"crm_record_id": crm_record_id, "demo_run_id": demo_run_id})
    follow_up_review = approve_review_item(
        follow_up_review.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Approved after rep review. Do not auto-send.",
        ),
    )
    outcome = capture_follow_up_outcome(
        crm_record_id,
        FollowUpOutcomeRequest(
            outcome="requested_proposal",
            notes="Maya replied and requested a lightweight package outline.",
            next_step="Prepare proposal outline for review.",
            next_step_due_date="2026-07-09",
        ),
    )

    proposal = draft_proposal(
        ProposalDraftRequest(
            proposal_id=f"proposal_{uuid4()}",
            lead_id=lead.lead_id,
            meeting_id=meeting.meeting_activity_id,
            follow_up_id=follow_up.follow_up_id,
            rep_name="Alex Rivera",
            contact_name="Maya Chen",
            company="Northstar Analytics",
            deal_stage_recommendation=meeting.deal_stage_recommendation,
            lead_priority=lead.priority,
            pain_points=["Manual qualification", "Lead routing", "Slow response times"],
            objections=[],
            buying_signals=["Approved budget", "Technical discovery requested"],
            next_steps=["Review package outline", "Confirm implementation requirements"],
            requested_package_type="Lead scoring and routing package",
            budget_context="Approved budget",
            implementation_timeline="this month",
            current_crm="HubSpot",
            risk_areas=[],
        )
    )
    proposal_review = latest_review_item_for_entity("proposal", proposal.proposal_id)
    add_review_metadata(proposal_review.review_item_id, {"crm_record_id": crm_record_id, "demo_run_id": demo_run_id})
    proposal_review = approve_review_item(
        proposal_review.review_item_id,
        ReviewDecisionRequest(
            actor="sales_manager",
            decision_reason="Approved internal outline for package discussion.",
        ),
    )
    proposal_activity = append_crm_activity(
        crm_record_id=crm_record_id,
        lead_id=lead.lead_id,
        activity_type="proposal_sent",
        activity_title="Proposal outline marked ready",
        activity_body=proposal.executive_summary,
        activity_status="applied",
        workflow_run_id=proposal_review.workflow_run_id or demo_run_id,
        metadata_json={"proposal_id": proposal.proposal_id, "status": "approved"},
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=proposal_review.workflow_run_id,
            workflow_name="proposal_lifecycle_writeback",
            entity_type="crm_record",
            entity_id=crm_record_id,
            event_type="proposal_status_updated",
            event_source="demo_lifecycle",
            actor="system",
            output_reference=proposal_activity.crm_activity_id,
            metadata_json={"proposal_status": "approved"},
        )
    )

    hygiene = check_crm_hygiene(
        CRMHygieneRequest(
            record_id=crm_record_id,
            lead_id=lead.lead_id,
            deal_id=lead.crm_record.hubspot_deal_id or "demo_deal",
            company="Northstar Analytics",
            contact_name="Maya Chen",
            deal_stage="qualified_discovery",
            lead_priority=lead.priority,
            owner=None,
            last_activity_date="2026-06-01",
            next_step=None,
            next_step_due_date="2026-07-09",
            follow_up_due="2026-07-09",
            proposal_status="approved",
            human_review_status="complete",
            crm_fields={"owner": None, "next_step": None},
            open_risks=["stale activity risk for demo visibility"],
            days_in_stage=45,
            deal_value_band="mid_market",
        )
    )
    append_crm_activity(
        crm_record_id=crm_record_id,
        lead_id=lead.lead_id,
        activity_type="hygiene_check_completed",
        activity_title=f"CRM hygiene check: {hygiene.risk_level}",
        activity_body=hygiene.reasoning,
        activity_status="created",
        workflow_run_id=demo_run_id,
        metadata_json={"hygiene_score": hygiene.hygiene_score},
    )
    log_step_failure(
        demo_run_id,
        WORKFLOW_NAME,
        "demo_notification_failure_diagnostic",
        "Simulated failed notification path for demo diagnostics.",
        entity_type="crm_record",
        entity_id=crm_record_id,
        failure_reason="Demo-safe simulated failure so Operational Logs and Notifications show diagnostics.",
        retryable=False,
        recommended_fix="Check n8n failure notification webhook configuration.",
        severity="warning",
    )

    after = snapshot_counts()
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=demo_run_id,
            workflow_name=WORKFLOW_NAME,
            entity_type="crm_record",
            entity_id=crm_record_id,
            event_type="demo_story_completed",
            event_source="demo_lifecycle",
            actor="system",
            output_reference=crm_record_id,
            human_review_required=False,
            metadata_json={
                "business_action": "full demo story completed",
                "status": "completed",
                "follow_up_outcome": outcome.outcome,
                "proposal_status": "approved",
                "hygiene_status": hygiene.risk_level,
            },
        )
    )
    log_step_success(
        demo_run_id,
        WORKFLOW_NAME,
        "demo_story_completed",
        entity_type="crm_record",
        entity_id=crm_record_id,
        metadata_json={
            "status": "completed",
            "crm_record_id": crm_record_id,
        },
    )
    after = snapshot_counts()
    return FullDemoStoryResponse(
        demo_run_id=demo_run_id,
        crm_record_id=crm_record_id,
        lead_score=lead.lead_score,
        priority=lead.priority,
        route=lead.recommended_route,
        hubspot_contact_id=lead.crm_record.hubspot_contact_id,
        hubspot_company_id=lead.crm_record.hubspot_company_id,
        hubspot_deal_id=lead.crm_record.hubspot_deal_id,
        meeting_summary_status=meeting.meeting_summary_status,
        follow_up_review_item_id=follow_up_review.review_item_id,
        follow_up_approval_status=follow_up_review.status,
        follow_up_outcome=outcome.outcome,
        proposal_review_item_id=proposal_review.review_item_id,
        proposal_status="approved",
        hygiene_status=hygiene.risk_level,
        audit_events_created=after["audit_events"] - before["audit_events"],
        workflow_step_events_created=after["workflow_steps"] - before["workflow_steps"],
        review_items_created=after["review_items"] - before["review_items"],
        notifications_sent_or_queued=after["notifications"] - before["notifications"],
    )


def latest_review_item_for_entity(entity_type: str, entity_id: str) -> ReviewItem:
    matches = [
        item
        for item in list_review_items()
        if item.entity_type == entity_type and item.entity_id == entity_id
    ]
    if not matches:
        raise ValueError(f"No review item found for {entity_type}:{entity_id}")
    return matches[-1]


def add_review_metadata(review_item_id: str, metadata: dict) -> None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT metadata_json FROM review_items WHERE review_item_id = ?",
            (review_item_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"review item not found: {review_item_id}")
        current = decode_json(row["metadata_json"], {})
        current.update(metadata)
        connection.execute(
            "UPDATE review_items SET metadata_json = ? WHERE review_item_id = ?",
            (encode_json(current), review_item_id),
        )
        connection.commit()


def snapshot_counts() -> dict[str, int]:
    return {
        "audit_events": len(list_audit_events()),
        "workflow_steps": len(list_step_events()),
        "review_items": len(list_review_items()),
        "notifications": len(list_notification_events()),
    }


def crm_activity_count(crm_record_id: str) -> int:
    return len(get_lead_record_activities(crm_record_id))
