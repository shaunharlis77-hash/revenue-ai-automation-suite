from fastapi import APIRouter, HTTPException

from app.models.audit import AuditEvent
from app.services.audit_trail import get_audit_event, list_audit_events


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def list_events() -> list[AuditEvent]:
    return list_audit_events()


@router.get("/events/{event_id}")
def get_event(event_id: str) -> AuditEvent:
    try:
        return get_audit_event(event_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
