from typing import Literal

from pydantic import BaseModel, Field


HubSpotSyncStatus = Literal[
    "not_enabled",
    "synced",
    "partial_sync",
    "blocked_pending_review",
    "failed",
    "skipped_mock_mode",
]


class HubSpotStatusResponse(BaseModel):
    adapter_mode: str
    hubspot_enabled: bool
    token_configured: bool
    portal_id: str | None = None
    default_pipeline_configured: bool
    default_deal_stage_configured: bool
    owner_id_configured: bool
    status: str


class HubSpotObjectIds(BaseModel):
    contact_id: str | None = None
    company_id: str | None = None
    deal_id: str | None = None
    task_id: str | None = None
    note_id: str | None = None


class HubSpotSyncResult(BaseModel):
    status: HubSpotSyncStatus
    object_ids: HubSpotObjectIds = Field(default_factory=HubSpotObjectIds)
    error: str | None = None
    retryable: bool = False
    recommended_fix: str | None = None
    metadata_json: dict = Field(default_factory=dict)


class HubSpotPropertyDefinition(BaseModel):
    object_type: str
    name: str
    label: str
    field_type: str = "text"
    property_type: str = "string"
    group_name: str = "contactinformation"
    options: list[dict] = Field(default_factory=list)


class HubSpotPropertySetupResponse(BaseModel):
    status: str
    hubspot_enabled: bool
    token_configured: bool
    created: list[str] = Field(default_factory=list)
    skipped_existing: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    failed_details: list[str] = Field(default_factory=list)
