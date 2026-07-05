from pydantic import BaseModel, Field


class NotificationEvent(BaseModel):
    id: int | None = None
    notification_id: str
    notification_type: str = "workflow_step_failed"
    workflow_run_id: str
    workflow_name: str
    step_name: str | None = None
    severity: str
    error_type: str | None = None
    safe_error_message: str | None = None
    retryable: bool = False
    recommended_fix: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    crm_record_id: str | None = None
    review_item_id: str | None = None
    recipient_role: str = "admin_ops"
    recipient_id: str | None = None
    recipient_name: str | None = None
    recipient_email: str | None = None
    routed_owner_id: str | None = None
    routed_owner_name: str | None = None
    manager_fallback_used: bool = False
    title: str
    message: str
    recommended_action: str | None = None
    delivery_status: str
    webhook_configured: bool
    created_at: str
    metadata_json: dict = Field(default_factory=dict)


class NotificationTestFailureRequest(BaseModel):
    workflow_run_id: str = "demo_notification_test"
    workflow_name: str = "demo_failure_notification"
    step_name: str = "simulated_failed_step"
    entity_type: str = "demo"
    entity_id: str = "demo_failure"
