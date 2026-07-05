from fastapi import APIRouter

from app.models.notifications import NotificationEvent, NotificationTestFailureRequest
from app.services.notifications import list_notification_events, recent_notification_events
from app.services.workflow_steps import log_step_failure


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications() -> list[NotificationEvent]:
    return list_notification_events()


@router.get("/recent")
def list_recent_notifications() -> list[NotificationEvent]:
    return recent_notification_events()


@router.post("/test-failure")
def create_test_failure_notification(
    request: NotificationTestFailureRequest,
) -> dict:
    log_step_failure(
        request.workflow_run_id,
        request.workflow_name,
        request.step_name,
        "Simulated safe failure notification test.",
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        failure_reason="Simulated failure for notification routing.",
        retryable=False,
        recommended_fix="Confirm notification routing and n8n webhook configuration.",
        severity="error",
    )
    return {"status": "created", "workflow_run_id": request.workflow_run_id}
