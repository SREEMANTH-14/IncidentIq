from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.schemas.metrics import MetricsResponse
from app.services.metrics_service import application_metrics

router = APIRouter()


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Application metrics",
    description=(
        "Returns IncidentIQ runtime metrics including HTTP request counts, "
        "error counts, average durations, workflow counts, severity counts, "
        "category counts, and mocked tool execution counts."
    ),
)
def get_metrics() -> MetricsResponse:
    """
    Returns JSON metrics for IncidentIQ.
    """

    settings = get_settings()
    metrics_response = application_metrics.build_metrics_response(
        settings=settings,
    )

    return metrics_response


@router.get(
    "/metrics/prometheus",
    response_class=Response,
    summary="Prometheus-style metrics",
    description="Returns lightweight Prometheus-style text metrics.",
)
def get_prometheus_metrics() -> Response:
    """
    Returns Prometheus-style text metrics.
    """

    settings = get_settings()
    metrics_text = application_metrics.build_prometheus_metrics(
        settings=settings,
    )

    response = Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )

    return response
