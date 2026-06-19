import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.responses import ErrorResponse, IncidentResourceResponse
from app.services.incident_service import incident_result_store

logger = logging.getLogger("IncidentIQ.API.IncidentsRoute")

router = APIRouter()


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResourceResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Retrieve processed incident",
    description="Returns a previously processed IncidentIQ response by incident ID.",
)
def get_incident(incident_id: str) -> IncidentResourceResponse:
    """
    This retrieves the response saved after POST /process.
    """

    cleaned_incident_id = incident_id.strip()

    if not cleaned_incident_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "trace_id": None,
                "error_code": "INVALID_INCIDENT_ID",
                "message": "incident_id cannot be empty.",
            },
        )

    try:
        response = incident_result_store.get_response(
            incident_id=cleaned_incident_id,
        )
    except ValueError as error:
        logger.warning("Invalid incident_id=%s error=%s", incident_id, str(error))

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "trace_id": None,
                "error_code": "INVALID_INCIDENT_ID",
                "message": str(error),
            },
        ) from error

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "trace_id": None,
                "error_code": "INCIDENT_NOT_FOUND",
                "message": f"Incident {cleaned_incident_id} was not found.",
            },
        )

    resource_response = IncidentResourceResponse(
        incident_id=cleaned_incident_id,
        response=response,
    )

    return resource_response
