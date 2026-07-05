from fastapi import APIRouter

from app.models.workflow_logs import WorkflowMetricsResponse
from app.services.dashboard_metrics import (
    get_admin_dashboard_metrics,
    get_sales_manager_dashboard_metrics,
)
from app.services.workflow_logs import get_workflow_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard")
def dashboard_metrics() -> WorkflowMetricsResponse:
    return get_workflow_metrics()


@router.get("/sales-manager-dashboard")
def sales_manager_dashboard_metrics() -> dict:
    return get_sales_manager_dashboard_metrics()


@router.get("/admin-dashboard")
def admin_dashboard_metrics() -> dict:
    return get_admin_dashboard_metrics()
