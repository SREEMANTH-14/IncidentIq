import logging

from app.schemas.responses import IncidentProcessResponse

logger = logging.getLogger("IncidentIQ.Services.IncidentService")


class IncidentResultStore:
    """
    This supports the required resource retrieval endpoint:
    GET /incidents/{incident_id}
    """

    def __init__(self) -> None:
        """
        Initializes the in-memory incident response store.
        """

        self._responses: dict[str, IncidentProcessResponse] = {}

    def save_response(self, response: IncidentProcessResponse) -> None:
        """
        Saves the final IncidentIQ processing response by incident_id.
        """

        incident_id = response.incident_id.strip()

        if not incident_id:
            raise ValueError("incident_id cannot be empty.")

        self._responses[incident_id] = response

        logger.info(
            "Saved incident response incident_id=%s trace_id=%s",
            incident_id,
            response.trace_id,
        )

    def get_response(self, incident_id: str) -> IncidentProcessResponse | None:
        """
        Retrieves a processed incident response by incident_id.
        """

        cleaned_incident_id = incident_id.strip()

        if not cleaned_incident_id:
            raise ValueError("incident_id cannot be empty.")

        response = self._responses.get(cleaned_incident_id)

        return response

    def list_incident_ids(self) -> list[str]:
        """
        Returns all stored incident IDs.

        """

        incident_ids = list(self._responses.keys())

        return incident_ids

    def clear(self) -> None:
        """
        Clears all stored incident responses.

        """

        self._responses.clear()


incident_result_store = IncidentResultStore()
