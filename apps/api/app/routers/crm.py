from fastapi import APIRouter, HTTPException

from app.models.lead_intake import CRMLeadRecord
from app.models.mock_crm import CRMActivity
from app.services.mock_crm_adapter import (
    get_lead_record,
    get_lead_record_activities,
    get_lead_records,
)


router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/leads")
def list_crm_leads() -> list[CRMLeadRecord]:
    return get_lead_records()


@router.get("/leads/{crm_record_id}")
def get_crm_lead(crm_record_id: str) -> CRMLeadRecord:
    try:
        return get_lead_record(crm_record_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/leads/{crm_record_id}/activities")
def list_crm_lead_activities(crm_record_id: str) -> list[CRMActivity]:
    try:
        get_lead_record(crm_record_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return get_lead_record_activities(crm_record_id)
