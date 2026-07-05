from fastapi import FastAPI

from app.config.settings import get_settings
from app.routers.ai import router as ai_router
from app.routers.audit import router as audit_router
from app.routers.crm import router as crm_router
from app.routers.demo import router as demo_router
from app.routers.health import router as health_router
from app.routers.hubspot import router as hubspot_router
from app.routers.intake import router as intake_router
from app.routers.logs import router as logs_router
from app.routers.metrics import router as metrics_router
from app.routers.notifications import router as notifications_router
from app.routers.review import router as review_router

settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    description="Foundation API for future revenue AI automation workflows.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(ai_router)
app.include_router(intake_router)
app.include_router(crm_router)
app.include_router(demo_router)
app.include_router(hubspot_router)
app.include_router(logs_router)
app.include_router(metrics_router)
app.include_router(audit_router)
app.include_router(review_router)
app.include_router(notifications_router)
