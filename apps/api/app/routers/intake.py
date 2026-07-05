from fastapi import APIRouter, HTTPException

from app.models.lead_intake import CRMLeadRecord, LeadIntakeRequest, LeadIntakeResponse
from app.services.lead_intake import intake_lead
from app.services.mock_crm_adapter import (
    get_lead_record_for_intake,
    get_lead_records,
)


router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/lead")
def create_lead_intake(request: LeadIntakeRequest) -> LeadIntakeResponse:
    try:
        return intake_lead(request)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/leads")
def list_leads() -> list[CRMLeadRecord]:
    return get_lead_records()


@router.get("/leads/{lead_id}")
def get_lead(lead_id: str) -> CRMLeadRecord:
    try:
        return get_lead_record_for_intake(lead_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
