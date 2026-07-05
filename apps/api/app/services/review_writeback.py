from app.models.audit import AuditEventCreate
from app.models.review_queue import ReviewItem
from app.services.audit_trail import create_audit_event
from app.services.mock_crm_adapter import append_crm_activity, get_lead_record
from app.services.workflow_steps import log_step_success


def apply_review_approval_writeback(item: ReviewItem, actor: str) -> None:
    crm_record_id = str(item.metadata_json.get("crm_record_id") or "")
    if not crm_record_id:
        return

    record = get_lead_record(crm_record_id)
    if item.review_type == "follow_up_draft":
        activity_type = "follow_up_draft_approved"
        title = "Follow-up draft approved"
        body = item.proposed_output or item.proposed_action
    elif item.review_type == "proposal_outline":
        activity_type = "proposal_outline_approved"
        title = "Proposal outline approved"
        body = item.proposed_output or item.proposed_action
    elif item.review_type == "deal_stage_change":
        activity_type = "crm_task_created"
        title = "Deal stage recommendation approved"
        body = item.proposed_action
    else:
        activity_type = "crm_task_created"
        title = "Review-approved CRM action"
        body = item.proposed_action

    append_crm_activity(
        crm_record_id=record.crm_record_id,
        lead_id=record.lead_id,
        activity_type=activity_type,
        activity_title=title,
        activity_body=body,
        activity_status="applied",
        workflow_run_id=item.workflow_run_id or f"review:{item.review_item_id}",
        metadata_json={
            "review_item_id": item.review_item_id,
            "review_type": item.review_type,
            "actor": actor,
            "demo_lifecycle": True,
        },
    )
    create_audit_event(
        AuditEventCreate(
            workflow_run_id=item.workflow_run_id,
            workflow_name=item.workflow_name,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            event_type="crm_update_applied",
            event_source="review_writeback",
            actor=actor,
            output_reference=record.crm_record_id,
            decision="approved",
            decision_reason=item.decision_reason,
            metadata_json={
                "review_item_id": item.review_item_id,
                "crm_record_id": record.crm_record_id,
                "review_type": item.review_type,
            },
        )
    )
    log_step_success(
        item.workflow_run_id or f"review:{item.review_item_id}",
        item.workflow_name,
        "review_approved_crm_writeback_applied",
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        metadata_json={
            "review_item_id": item.review_item_id,
            "crm_record_id": record.crm_record_id,
        },
    )
