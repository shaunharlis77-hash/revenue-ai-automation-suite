from pydantic import BaseModel, Field


class MeetingAttachmentRequest(BaseModel):
    meeting_title: str
    meeting_timestamp: str
    transcript: str | None = None
    notes: str | None = None
    attendees: list[str] = Field(default_factory=list)
    owner: str | None = None
    source: str = "demo"


class MeetingLifecycleResponse(BaseModel):
    workflow_run_id: str
    crm_record_id: str
    meeting_activity_id: str
    meeting_summary_status: str
    meeting_summary_activity_id: str
    deal_stage_recommendation: str
    review_item_ids: list[str]


class FollowUpOutcomeRequest(BaseModel):
    outcome: str
    notes: str | None = None
    next_step: str | None = None
    next_step_due_date: str | None = None


class FollowUpOutcomeResponse(BaseModel):
    workflow_run_id: str
    crm_record_id: str
    outcome: str
    activity_id: str
    next_step_task_id: str | None = None


class FullDemoStoryResponse(BaseModel):
    demo_run_id: str
    crm_record_id: str
    lead_score: int
    priority: str
    route: str
    hubspot_contact_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_deal_id: str | None = None
    meeting_summary_status: str
    follow_up_review_item_id: str
    follow_up_approval_status: str
    follow_up_outcome: str
    proposal_review_item_id: str
    proposal_status: str
    hygiene_status: str
    audit_events_created: int
    workflow_step_events_created: int
    review_items_created: int
    notifications_sent_or_queued: int
