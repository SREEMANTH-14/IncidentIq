import logging
from functools import lru_cache

from fastapi import APIRouter, Header, HTTPException, status

from app.agents.orchestrator import Orchestrator
from app.schemas.incident import IncidentPayload
from app.schemas.responses import ErrorResponse, IncidentProcessResponse
from app.services.incident_service import incident_result_store
from app.core.trace import get_trace_id, normalize_trace_id
from app.services.metrics_service import application_metrics

logger = logging.getLogger("IncidentIQ.API.ProcessRoute")

router = APIRouter()


@lru_cache
def get_orchestrator() -> Orchestrator:
    """
    Returns a cached Orchestrator instance.This prevents reloading the LangGraph workflow, ChromaDB retriever,
    and embedding model on every request.
    """

    orchestrator = Orchestrator()
    return orchestrator


@router.post(
    "/process",
    response_model=IncidentProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Process an incident",
    description=(
        "Runs the IncidentIQ LangGraph workflow for a production incident. "
        "The workflow includes Triage Agent, Knowledge Agent, Remediation Agent, "
        "and Notifier Agent with conditional routing."
    ),
)
def process_incident(
    incident_payload: IncidentPayload,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> IncidentProcessResponse:
    """
    Main IncidentIQ endpoint required by the assessment.

    Flow:
    1. FastAPI validates IncidentPayload.
    2. Orchestrator runs the LangGraph workflow.
    3. Final IncidentProcessResponse is saved.
    4. Response is returned to the caller.
    """

    if x_trace_id is None:
        active_trace_id = get_trace_id()
    else:
        active_trace_id = normalize_trace_id(trace_id=x_trace_id)

    try:
        orchestrator = get_orchestrator()

        response = orchestrator.process_incident(
            incident_payload=incident_payload,
            trace_id=active_trace_id,
        )

        incident_result_store.save_response(response=response)
        application_metrics.record_incident_process(response=response)

        return response

    except ValueError as error:
        logger.warning(
            "Validation error while processing incident_id=%s error=%s",
            incident_payload.incident_id,
            str(error),
            extra={
                "incident_id": incident_payload.incident_id,
                "error_code": "INCIDENT_PROCESS_VALIDATION_ERROR",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "trace_id": active_trace_id,
                "error_code": "INCIDENT_PROCESS_VALIDATION_ERROR",
                "message": str(error),
            },
        ) from error

    except Exception as error:
        logger.exception(
            "Unexpected error while processing incident_id=%s",
            incident_payload.incident_id,
            extra={
                "incident_id": incident_payload.incident_id,
                "error_code": "INCIDENT_PROCESSING_FAILED",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "trace_id": active_trace_id,
                "error_code": "INCIDENT_PROCESSING_FAILED",
                "message": f"Incident processing failed: {str(error)}",
            },
        ) from error
