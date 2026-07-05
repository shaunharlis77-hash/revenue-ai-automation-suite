from typing import Literal

from pydantic import BaseModel, Field, field_validator


Confidence = Literal["high", "medium", "low"]

REQUIRED_TEXT_FIELDS = (
    "proposal_id",
    "rep_name",
    "contact_name",
    "company",
    "deal_stage_recommendation",
    "lead_priority",
    "requested_package_type",
    "budget_context",
    "implementation_timeline",
    "current_crm",
)


class ProposalDraftRequest(BaseModel):
    proposal_id: str
    lead_id: str | None = None
    meeting_id: str | None = None
    follow_up_id: str | None = None
    rep_name: str
    contact_name: str
    company: str
    deal_stage_recommendation: str
    lead_priority: str
    pain_points: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    requested_package_type: str
    budget_context: str
    implementation_timeline: str
    current_crm: str
    risk_areas: list[str] = Field(default_factory=list)

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="before")
    @classmethod
    def required_text_must_not_be_blank(cls, value: object) -> str:
        if value is None:
            raise ValueError("required text field must not be blank")

        cleaned_value = str(value).strip()
        if not cleaned_value:
            raise ValueError("required text field must not be blank")

        return cleaned_value


class ProposalDraftResponse(BaseModel):
    proposal_id: str
    proposal_title: str
    executive_summary: str
    problem_statement: str
    recommended_package: str
    scope_items: list[str]
    implementation_considerations: list[str]
    assumptions: list[str]
    exclusions: list[str]
    risk_notes: list[str]
    review_reasons: list[str]
    confidence: Confidence
    human_review_required: bool
    next_action: str
    reasoning: str
