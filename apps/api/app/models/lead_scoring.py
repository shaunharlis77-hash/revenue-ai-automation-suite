from typing import Literal

from pydantic import BaseModel, field_validator


Priority = Literal["critical", "high", "medium", "low", "disqualify"]
Confidence = Literal["high", "medium", "low"]
Urgency = Literal["critical", "high", "medium", "low", "unknown", "none"]

REQUIRED_TEXT_FIELDS = (
    "name",
    "email",
    "company",
    "role",
    "company_size",
    "source",
    "message",
    "timeline",
    "budget",
    "current_crm",
)


class LeadScoringRequest(BaseModel):
    lead_id: str | None = None
    name: str
    email: str
    company: str
    role: str
    company_size: str
    source: str
    message: str
    timeline: str
    budget: str
    current_crm: str
    created_at: str | None = None

    @field_validator(*REQUIRED_TEXT_FIELDS)
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("required text field must not be blank")
        return cleaned_value


class LeadScoringResponse(BaseModel):
    lead_id: str | None = None
    lead_score: int
    priority: Priority
    persona: str
    pain_points: list[str]
    urgency: Urgency
    recommended_route: str
    next_best_action: str
    confidence: Confidence
    human_review_required: bool
    reasoning: str
