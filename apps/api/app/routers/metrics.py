from fastapi import APIRouter

from app.models.workflow_logs import WorkflowMetricsResponse
from app.services.workflow_logs import get_workflow_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dashboard")
def dashboard_metrics() -> WorkflowMetricsResponse:
    return get_workflow_metrics()
