from typing import Literal

from pydantic import BaseModel, Field, field_validator


MessageChannel = Literal["email", "whatsapp"]
Tone = Literal["professional", "concise", "warm"]
Confidence = Literal["high", "medium", "low"]

REQUIRED_TEXT_FIELDS = (
    "follow_up_id",
    "rep_name",
    "contact_name",
    "company",
    "lead_priority",
    "deal_stage_recommendation",
    "follow_up_due",
    "message_channel",
    "tone",
)


class FollowUpDraftRequest(BaseModel):
    follow_up_id: str
    lead_id: str | None = None
    meeting_id: str | None = None
    rep_name: str
    contact_name: str
    company: str
    lead_priority: str
    deal_stage_recommendation: str
    pain_points: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    follow_up_due: str
    message_channel: MessageChannel
    tone: Tone

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="before")
    @classmethod
    def required_text_must_not_be_blank(cls, value: object) -> str:
        if value is None:
            raise ValueError("required text field must not be blank")

        cleaned_value = str(value).strip()
        if not cleaned_value:
            raise ValueError("required text field must not be blank")

        return cleaned_value


class FollowUpDraftResponse(BaseModel):
    follow_up_id: str
    draft_subject: str
    draft_body: str
    message_channel: MessageChannel
    tone: Tone
    source_context_summary: str
    review_required: bool
    review_reasons: list[str]
    risk_notes: list[str]
    recommended_send_timing: str
    next_action: str
    confidence: Confidence
    reasoning: str
