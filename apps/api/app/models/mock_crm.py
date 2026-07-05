from typing import Literal

from pydantic import BaseModel, Field


CRMActivityType = Literal[
    "lead_created",
    "lead_enriched",
    "lead_scored",
    "route_assigned",
    "crm_update_applied",
    "crm_update_blocked",
    "review_visibility_created",
]
CRMActivityStatus = Literal["created", "applied", "blocked", "info"]


class CRMActivity(BaseModel):
    id: int | None = None
    crm_activity_id: str
    crm_record_id: str
    lead_id: str
    activity_type: CRMActivityType
    activity_title: str
    activity_body: str
    activity_status: CRMActivityStatus
    source_workflow: str
    workflow_run_id: str
    created_at: str
    metadata_json: dict = Field(default_factory=dict)
