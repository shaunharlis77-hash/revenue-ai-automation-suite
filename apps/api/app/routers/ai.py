from fastapi import APIRouter

from app.models.crm_hygiene import CRMHygieneRequest, CRMHygieneResponse
from app.models.follow_up import FollowUpDraftRequest, FollowUpDraftResponse
from app.models.lead_scoring import LeadScoringRequest, LeadScoringResponse
from app.models.meeting_summary import MeetingSummaryRequest, MeetingSummaryResponse
from app.models.placeholders import PlaceholderResponse
from app.models.proposal import ProposalDraftRequest, ProposalDraftResponse
from app.services.crm_hygiene import check_crm_hygiene as check_crm_hygiene_service
from app.services.follow_up import draft_follow_up as draft_follow_up_service
from app.services.lead_scoring import score_lead as score_lead_service
from app.services.meeting_summary import summarize_meeting as summarize_meeting_service
from app.services.proposal import draft_proposal as draft_proposal_service

router = APIRouter(prefix="/ai", tags=["ai"])


def placeholder(endpoint: str) -> PlaceholderResponse:
    return PlaceholderResponse(endpoint=endpoint)


@router.post("/score-lead")
def score_lead(lead: LeadScoringRequest) -> LeadScoringResponse:
    return score_lead_service(lead)


@router.post("/summarize-meeting")
def summarize_meeting(meeting: MeetingSummaryRequest) -> MeetingSummaryResponse:
    return summarize_meeting_service(meeting)


@router.post("/draft-follow-up")
def draft_follow_up(request: FollowUpDraftRequest) -> FollowUpDraftResponse:
    return draft_follow_up_service(request)


@router.post("/check-crm-hygiene")
def check_crm_hygiene(request: CRMHygieneRequest) -> CRMHygieneResponse:
    return check_crm_hygiene_service(request)


@router.post("/draft-proposal")
def draft_proposal(request: ProposalDraftRequest) -> ProposalDraftResponse:
    return draft_proposal_service(request)


@router.post("/ask-sales-kb")
def ask_sales_kb() -> PlaceholderResponse:
    return placeholder("POST /ai/ask-sales-kb")
