from fastapi import APIRouter, HTTPException

from app.models.hubspot import (
    HubSpotPropertySetupResponse,
    HubSpotStatusResponse,
    HubSpotSyncResult,
)
from app.services.hubspot_adapter import (
    ensure_custom_properties,
    get_hubspot_status,
    sync_lead_to_hubspot,
)


router = APIRouter(prefix="/hubspot", tags=["hubspot"])


@router.get("/status")
def status() -> HubSpotStatusResponse:
    return get_hubspot_status()


@router.post("/setup-properties")
def setup_properties() -> HubSpotPropertySetupResponse:
    return ensure_custom_properties()


@router.post("/sync/lead/{lead_id}")
def sync_lead(lead_id: str) -> HubSpotSyncResult:
    try:
        return sync_lead_to_hubspot(lead_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
