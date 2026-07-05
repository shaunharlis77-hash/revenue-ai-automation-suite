from fastapi import APIRouter, HTTPException

from app.models.demo_lifecycle import (
    FollowUpOutcomeRequest,
    FollowUpOutcomeResponse,
    FullDemoStoryResponse,
    MeetingAttachmentRequest,
    MeetingLifecycleResponse,
)
from app.services.demo_lifecycle import (
    capture_follow_up_outcome,
    process_meeting_and_writeback,
    run_full_demo_story,
)


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/records/{crm_record_id}/meeting")
def attach_meeting(
    crm_record_id: str,
    request: MeetingAttachmentRequest,
) -> MeetingLifecycleResponse:
    try:
        return process_meeting_and_writeback(crm_record_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/records/{crm_record_id}/follow-up-outcome")
def follow_up_outcome(
    crm_record_id: str,
    request: FollowUpOutcomeRequest,
) -> FollowUpOutcomeResponse:
    try:
        return capture_follow_up_outcome(crm_record_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/full-story/run")
def run_demo_story(reset_demo: bool = False) -> FullDemoStoryResponse:
    return run_full_demo_story(reset_demo=reset_demo)
