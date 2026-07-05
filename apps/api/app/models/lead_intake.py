from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


CRMUpdateStatus = Literal[
    "applied",
    "blocked_pending_review",
    "applied_with_review_visibility",
]
EnrichmentConfidence = Literal["high", "medium", "low"]


class LeadIntakeRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str
    company: str
    job_title: str | None = None
    company_website: str | None = None
    company_size: str | None = None
    industry: str | None = None
    region: str | None = None
    source: str
    message: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    urgency: str | None = None
    budget_context: str | None = None
    requested_demo: bool = False
    crm_system: str | None = None
    notes: str | None = None

    @field_validator("email", "company", "source", mode="before")
    @classmethod
    def required_text_must_not_be_blank(cls, value: object) -> str:
        cleaned_value = str(value or "").strip()
        if not cleaned_value:
            raise ValueError("required text field must not be blank")
        return cleaned_value

    @model_validator(mode="after")
    def message_or_notes_required(self):
        if not (self.message or "").strip() and not (self.notes or "").strip():
            raise ValueError("message or notes is required")
        return self


class LeadEnrichmentResult(BaseModel):
    company_size_band: str
    industry_normalized: str
    region_normalized: str
    persona: str
    likely_team: str
    lead_source_type: str
    crm_match_status: str
    fit_notes: list[str]
    enrichment_confidence: EnrichmentConfidence
    enrichment_risk_flags: list[str]
    buying_signals: list[str]


class CRMLeadRecord(BaseModel):
    id: int | None = None
    crm_record_id: str
    lead_id: str
    company: str
    contact_name: str | None = None
    email: str
    source: str
    enriched_persona: str
    company_size_band: str
    industry_normalized: str
    region_normalized: str
    lead_score: int
    priority: str
    confidence: str
    urgency: str
    recommended_route: str
    next_best_action: str
    crm_update_status: CRMUpdateStatus
    human_review_required: bool
    risk_flags: list[str]
    created_at: str
    updated_at: str
    metadata_json: dict = Field(default_factory=dict)


class LeadIntakeResponse(BaseModel):
    lead_id: str
    crm_record: CRMLeadRecord
    enrichment: LeadEnrichmentResult
    lead_score: int
    priority: str
    confidence: str
    urgency: str
    recommended_route: str
    next_best_action: str
    crm_update_status: CRMUpdateStatus
    review_created: bool
    review_reasons: list[str]
    workflow_run_id: str
    reasoning: str
