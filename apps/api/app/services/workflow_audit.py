from app.models.audit import AuditEventCreate
from app.models.crm_hygiene import CRMHygieneRequest, CRMHygieneResponse
from app.models.follow_up import FollowUpDraftRequest, FollowUpDraftResponse
from app.models.lead_scoring import LeadScoringRequest, LeadScoringResponse
from app.models.meeting_summary import MeetingSummaryRequest, MeetingSummaryResponse
from app.models.proposal import ProposalDraftRequest, ProposalDraftResponse
from app.models.review_queue import ReviewItemCreate
from app.models.workflow_logs import WorkflowRunLog
from app.services.audit_trail import create_audit_event
from app.services.review_queue import create_review_item


def audit_started(run: WorkflowRunLog, entity_type: str, entity_id: str) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="workflow_started",
            event_source="workflow_service",
            input_reference=run.input_reference,
            metadata_json={"status": "started"},
        )
    )


def audit_completed(
    run: WorkflowRunLog,
    entity_type: str,
    entity_id: str,
    output_reference: str,
    human_review_required: bool,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="workflow_completed",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=output_reference,
            human_review_required=human_review_required,
            metadata_json={"status": "completed"},
        )
    )


def audit_guardrail(
    run: WorkflowRunLog,
    entity_type: str,
    entity_id: str,
    guardrails: list[str],
    output_reference: str | None = None,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="guardrail_triggered",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=output_reference,
            guardrails_triggered=guardrails,
            human_review_required=True,
        )
    )


def audit_workflow_failure(
    run: WorkflowRunLog,
    entity_type: str,
    entity_id: str,
    failure_step: str,
    failure_reason: str,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="workflow_failed",
            event_source="workflow_service",
            input_reference=run.input_reference,
            human_review_required=True,
            metadata_json={
                "failure_step": failure_step,
                "failure_reason": failure_reason,
            },
        )
    )


def record_lead_scoring_audit(
    run: WorkflowRunLog, lead: LeadScoringRequest, result: LeadScoringResponse
) -> None:
    entity_id = lead.lead_id or lead.email
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="lead",
            entity_id=entity_id,
            event_type="lead_scored",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.lead_id,
            human_review_required=result.human_review_required,
            metadata_json={"lead_score": result.lead_score, "priority": result.priority},
        )
    )
    if result.human_review_required:
        audit_guardrail(
            run,
            "lead",
            entity_id,
            ["human_review_required"],
            output_reference=result.lead_id,
        )
        create_review_item(
            ReviewItemCreate(
                workflow_run_id=run.workflow_run_id,
                workflow_name=run.workflow_name,
                entity_type="lead",
                entity_id=entity_id,
                company=lead.company,
                contact_name=lead.name,
                review_type="crm_update",
                title=f"Review lead scoring route for {lead.company}",
                priority=result.priority,
                risk_level="high" if result.priority in {"critical", "high"} else "medium",
                review_reasons=[result.reasoning],
                proposed_action=result.next_best_action,
                proposed_output=result.recommended_route,
                metadata_json={"lead_score": result.lead_score},
            )
        )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="lead",
            entity_id=entity_id,
            event_type="crm_update_recommended",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.lead_id,
            human_review_required=result.human_review_required,
            metadata_json={"recommended_route": result.recommended_route},
        )
    )


def record_meeting_summary_audit(
    run: WorkflowRunLog,
    meeting: MeetingSummaryRequest,
    result: MeetingSummaryResponse,
) -> None:
    entity_id = meeting.meeting_id or meeting.deal_id or meeting.company
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="meeting",
            entity_id=entity_id,
            event_type="meeting_summary_created",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.meeting_id,
            human_review_required=result.human_review_required,
            metadata_json={"confidence": result.confidence},
        )
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="meeting",
            entity_id=entity_id,
            event_type="next_steps_extracted",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.meeting_id,
            human_review_required=result.human_review_required,
            metadata_json={"next_steps": result.next_steps},
        )
    )

    review_required_actions = [
        action
        for action in result.recommended_actions
        if action.automation_status == "review_required"
    ]
    if review_required_actions:
        audit_guardrail(
            run,
            "meeting",
            entity_id,
            ["review_required_actions"],
            output_reference=result.meeting_id,
        )
    for action in review_required_actions:
        create_meeting_review_item(run, meeting, result, action.action_type, action.description)

    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="meeting",
            entity_id=entity_id,
            event_type="crm_update_recommended",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.meeting_id,
            human_review_required=result.human_review_required,
            metadata_json={"deal_stage_recommendation": result.deal_stage_recommendation},
        )
    )


def create_meeting_review_item(
    run: WorkflowRunLog,
    meeting: MeetingSummaryRequest,
    result: MeetingSummaryResponse,
    action_type: str,
    action_description: str,
) -> None:
    review_type_by_action = {
        "draft_follow_up": "follow_up_draft",
        "recommend_deal_stage": "deal_stage_change",
        "draft_proposal_outline": "proposal_outline",
        "schedule_review": "crm_update",
    }
    review_type = review_type_by_action.get(action_type, "crm_update")
    create_review_item(
        ReviewItemCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="meeting",
            entity_id=meeting.meeting_id or meeting.deal_id or meeting.company,
            company=meeting.company,
            contact_name=meeting.contact_name,
            review_type=review_type,
            title=f"Review meeting action for {meeting.company}",
            priority="high" if result.human_review_required else "medium",
            risk_level="high" if result.human_review_required else "medium",
            review_reasons=[result.reasoning],
            proposed_action=action_description,
            proposed_output=result.crm_note,
            metadata_json={"action_type": action_type},
        )
    )


def record_follow_up_audit(
    run: WorkflowRunLog,
    request: FollowUpDraftRequest,
    result: FollowUpDraftResponse,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="follow_up",
            entity_id=request.follow_up_id,
            event_type="follow_up_draft_created",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.follow_up_id,
            human_review_required=True,
            metadata_json={"confidence": result.confidence},
        )
    )
    audit_guardrail(
        run,
        "follow_up",
        request.follow_up_id,
        ["no_auto_send", "customer_facing_review_required"],
        output_reference=result.follow_up_id,
    )
    create_review_item(
        ReviewItemCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="follow_up",
            entity_id=request.follow_up_id,
            company=request.company,
            contact_name=request.contact_name,
            review_type="follow_up_draft",
            title=f"Review follow-up draft for {request.company}",
            priority=request.lead_priority,
            risk_level="medium" if result.confidence != "low" else "high",
            review_reasons=result.review_reasons,
            proposed_action=result.next_action,
            proposed_output=result.draft_body,
            metadata_json={"message_channel": result.message_channel, "tone": result.tone},
        )
    )


def record_proposal_audit(
    run: WorkflowRunLog,
    request: ProposalDraftRequest,
    result: ProposalDraftResponse,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="proposal",
            entity_id=request.proposal_id,
            event_type="proposal_outline_created",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.proposal_id,
            human_review_required=True,
            metadata_json={"confidence": result.confidence},
        )
    )
    guardrails = [
        reason
        for reason in result.review_reasons
        if any(term in reason.lower() for term in ("pricing", "security", "legal", "implementation", "budget"))
    ]
    if guardrails:
        audit_guardrail(run, "proposal", request.proposal_id, guardrails, result.proposal_id)
    create_review_item(
        ReviewItemCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="proposal",
            entity_id=request.proposal_id,
            company=request.company,
            contact_name=request.contact_name,
            review_type="proposal_outline",
            title=result.proposal_title,
            priority=request.lead_priority,
            risk_level="high" if result.confidence == "low" else "medium",
            review_reasons=result.review_reasons,
            proposed_action=result.next_action,
            proposed_output=result.executive_summary,
            metadata_json={"recommended_package": result.recommended_package},
        )
    )


def record_crm_hygiene_audit(
    run: WorkflowRunLog,
    request: CRMHygieneRequest,
    result: CRMHygieneResponse,
) -> None:
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=run.workflow_run_id,
            workflow_name=run.workflow_name,
            entity_type="crm_record",
            entity_id=request.record_id,
            event_type="crm_hygiene_checked",
            event_source="workflow_service",
            input_reference=run.input_reference,
            output_reference=result.record_id,
            human_review_required=result.human_review_required,
            metadata_json={"hygiene_score": result.hygiene_score, "risk_level": result.risk_level},
        )
    )
    guardrails = crm_hygiene_guardrails(result)
    if guardrails:
        audit_guardrail(run, "crm_record", request.record_id, guardrails, result.record_id)
    if result.human_review_required:
        create_review_item(
            ReviewItemCreate(
                workflow_run_id=run.workflow_run_id,
                workflow_name=run.workflow_name,
                entity_type="crm_record",
                entity_id=request.record_id,
                company=request.company,
                contact_name=request.contact_name,
                review_type=crm_review_type(result),
                title=f"Review CRM hygiene issues for {request.company}",
                priority=request.lead_priority,
                risk_level=result.risk_level,
                review_reasons=result.issues,
                proposed_action=result.next_action,
                proposed_output="; ".join(result.recommended_actions),
                metadata_json={"missing_fields": result.missing_fields},
            )
        )


def crm_hygiene_guardrails(result: CRMHygieneResponse) -> list[str]:
    guardrails: list[str] = []
    if result.risk_level in {"high", "critical"}:
        guardrails.append(f"{result.risk_level}_risk")
    if result.missing_fields:
        guardrails.append("missing_required_crm_data")
    if any("owner" in issue.lower() for issue in result.issues):
        guardrails.append("missing_owner")
    if any("next step" in issue.lower() for issue in result.issues):
        guardrails.append("missing_next_step")
    if any("proposal" in issue.lower() for issue in result.issues):
        guardrails.append("overdue_review")
    return guardrails


def crm_review_type(result: CRMHygieneResponse) -> str:
    if result.risk_level in {"high", "critical"}:
        return "high_risk_deal"
    if result.missing_fields:
        return "missing_data_issue"
    return "crm_update"
