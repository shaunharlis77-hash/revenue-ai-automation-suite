from typing import Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal["pending", "approved", "rejected"]
ReviewType = Literal[
    "follow_up_draft",
    "proposal_outline",
    "deal_stage_change",
    "crm_update",
    "lead_routing",
    "high_risk_deal",
    "missing_data_issue",
]


class ReviewItemCreate(BaseModel):
    workflow_run_id: str | None = None
    workflow_name: str
    entity_type: str
    entity_id: str
    company: str | None = None
    contact_name: str | None = None
    review_type: ReviewType
    title: str
    priority: str = "medium"
    risk_level: str = "medium"
    review_reasons: list[str] = Field(default_factory=list)
    proposed_action: str
    proposed_output: str | None = None
    assigned_to: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class ReviewDecisionRequest(BaseModel):
    actor: str = "system"
    decision_reason: str


class ReviewItem(BaseModel):
    id: int
    review_item_id: str
    workflow_run_id: str | None = None
    workflow_name: str
    entity_type: str
    entity_id: str
    company: str | None = None
    contact_name: str | None = None
    review_type: ReviewType
    title: str
    status: ReviewStatus
    priority: str
    risk_level: str
    review_reasons: list[str]
    proposed_action: str
    proposed_output: str | None = None
    decision: str | None = None
    decision_reason: str | None = None
    assigned_to: str | None = None
    created_at: str
    updated_at: str
    metadata_json: dict
