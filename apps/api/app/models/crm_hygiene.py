from typing import Literal

from pydantic import BaseModel, Field, field_validator


RiskLevel = Literal["low", "medium", "high", "critical"]
Confidence = Literal["high", "medium", "low"]

REQUIRED_TEXT_FIELDS = (
    "record_id",
    "company",
    "contact_name",
    "deal_stage",
    "lead_priority",
    "proposal_status",
    "human_review_status",
    "deal_value_band",
)


class CRMHygieneRequest(BaseModel):
    record_id: str
    lead_id: str | None = None
    deal_id: str | None = None
    company: str
    contact_name: str
    deal_stage: str
    lead_priority: str
    owner: str | None = None
    last_activity_date: str | None = None
    next_step: str | None = None
    next_step_due_date: str | None = None
    follow_up_due: str | None = None
    proposal_status: str
    human_review_status: str
    crm_fields: dict[str, str | None] = Field(default_factory=dict)
    open_risks: list[str] = Field(default_factory=list)
    days_in_stage: int
    deal_value_band: str

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="before")
    @classmethod
    def required_text_must_not_be_blank(cls, value: object) -> str:
        if value is None:
            raise ValueError("required text field must not be blank")

        cleaned_value = str(value).strip()
        if not cleaned_value:
            raise ValueError("required text field must not be blank")

        return cleaned_value

    @field_validator("days_in_stage")
    @classmethod
    def days_in_stage_must_not_be_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("days_in_stage must not be negative")
        return value


class CRMHygieneResponse(BaseModel):
    record_id: str
    hygiene_score: int
    risk_level: RiskLevel
    issues: list[str]
    missing_fields: list[str]
    stale_activity: bool
    recommended_actions: list[str]
    human_review_required: bool
    next_action: str
    confidence: Confidence
    reasoning: str
