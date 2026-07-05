from typing import Literal

from pydantic import BaseModel, field_validator


TranscriptType = Literal["full_transcript", "meeting_minutes", "rough_notes"]
Confidence = Literal["high", "medium", "low"]
AutomationStatus = Literal["auto_allowed", "review_required"]

REQUIRED_TEXT_FIELDS = (
    "rep_name",
    "contact_name",
    "company",
    "meeting_source",
    "source_platform",
    "transcript_type",
    "transcript",
)


class MeetingSummaryRequest(BaseModel):
    meeting_id: str | None = None
    lead_id: str | None = None
    deal_id: str | None = None
    rep_name: str
    contact_name: str
    company: str
    meeting_date: str | None = None
    meeting_source: str
    source_platform: str
    transcript_type: TranscriptType
    transcript: str

    @field_validator(*REQUIRED_TEXT_FIELDS, mode="before")
    @classmethod
    def required_text_must_not_be_blank(cls, value: object) -> str:
        if value is None:
            raise ValueError("required text field must not be blank")

        cleaned_value = str(value).strip()

        if not cleaned_value:
            raise ValueError("required text field must not be blank")

        return cleaned_value


class RecommendedAction(BaseModel):
    action_type: str
    description: str
    due: str
    automation_status: AutomationStatus


class MeetingSummaryResponse(BaseModel):
    meeting_id: str | None = None
    crm_note: str
    pain_points: list[str]
    objections: list[str]
    buying_signals: list[str]
    next_steps: list[str]
    follow_up_due: str
    deal_stage_recommendation: str
    proposal_needed: bool
    confidence: Confidence
    human_review_required: bool
    needs_more_info: bool
    recommended_actions: list[RecommendedAction]
    reasoning: str