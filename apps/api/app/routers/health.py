from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()

    return {
        "project": settings.project_name,
        "status": "ok",
        "environment": settings.environment,
        "message": "Foundation API is running. No external services are connected.",
    }

