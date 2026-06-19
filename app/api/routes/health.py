from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.responses import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns IncidentIQ application health status.",
)
def get_health() -> HealthResponse:
    """
    Health endpoint required by the assessment.

    This endpoint confirms that the FastAPI application is running.
    """

    settings = get_settings()

    response = HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
    )

    return response
