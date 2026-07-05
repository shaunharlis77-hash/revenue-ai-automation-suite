from typing import Literal

from pydantic import BaseModel, Field


AuditEventType = Literal[
    "workflow_started",
    "workflow_completed",
    "workflow_failed",
    "demo_story_completed",
    "lead_received",
    "lead_enriched",
    "lead_scored",
    "route_recommended",
    "meeting_summary_created",
    "meeting_attached",
    "meeting_summary_crm_writeback",
    "next_steps_extracted",
    "follow_up_draft_created",
    "follow_up_outcome_captured",
    "proposal_outline_created",
    "proposal_status_updated",
    "crm_hygiene_checked",
    "guardrail_triggered",
    "review_created",
    "review_notification_created",
    "manager_fallback_notification_created",
    "review_approved",
    "review_rejected",
    "crm_update_recommended",
    "crm_update_blocked",
    "crm_update_applied",
    "crm_update_applied_with_review_visibility",
    "crm_adapter_write_started",
    "crm_adapter_write_applied",
    "crm_adapter_write_blocked",
    "crm_activity_created",
    "crm_adapter_write_failed",
    "hubspot_sync_started",
    "hubspot_contact_upserted",
    "hubspot_company_upserted",
    "hubspot_deal_upserted",
    "hubspot_task_created",
    "hubspot_note_created",
    "hubspot_records_associated",
    "hubspot_sync_completed",
    "hubspot_sync_failed",
    "hubspot_sync_blocked",
]


class AuditEventCreate(BaseModel):
    workflow_run_id: str | None = None
    workflow_name: str
    entity_type: str
    entity_id: str
    event_type: AuditEventType
    event_source: str = "api"
    actor: str = "system"
    input_reference: str | None = None
    output_reference: str | None = None
    guardrails_triggered: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    decision: str | None = None
    decision_reason: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class AuditEvent(BaseModel):
    id: int
    event_id: str
    workflow_run_id: str | None = None
    workflow_name: str
    entity_type: str
    entity_id: str
    event_type: AuditEventType
    event_source: str
    actor: str
    input_reference: str | None = None
    output_reference: str | None = None
    guardrails_triggered: list[str]
    human_review_required: bool
    decision: str | None = None
    decision_reason: str | None = None
    created_at: str
    metadata_json: dict
