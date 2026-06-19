import logging
import uuid

from app.core.trace import normalize_trace_id

from app.core.config import ConfigSettings, get_settings
from app.graph.state import (
    IncidentIQGraphState,
    get_required_notification_message,
    get_required_triage_result,
)
from app.graph.workflow import IncidentIQWorkflow
from app.schemas.incident import IncidentPayload
from app.schemas.responses import IncidentProcessResponse

logger = logging.getLogger("IncidentIQ.Agents.Orchestrator")


class Orchestrator:
    """
    Orchestrator routes between agents based on severity."
    POST /process API will call Orchestrator.process_incident()
    """

    def __init__(
        self,
        settings: ConfigSettings | None = None,
        workflow: IncidentIQWorkflow | None = None,
    ) -> None:
        """
        Initializes the Orchestrator.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

        if workflow is None:
            self.workflow = IncidentIQWorkflow(settings=self.settings)
        else:
            self.workflow = workflow

    def process_incident(
        self,
        incident_payload: IncidentPayload,
        trace_id: str | None = None,
    ) -> IncidentProcessResponse:
        """
        Processes one IncidentIQ incident through the LangGraph workflow.

        Input:
        - IncidentPayload from POST /process
        - optional trace_id

        Output:
        - IncidentProcessResponse for the API layer
        """

        active_trace_id = normalize_trace_id(trace_id=trace_id)

        logger.info(
            "Orchestrator started trace_id=%s incident_id=%s",
            active_trace_id,
            incident_payload.incident_id,
        )

        final_state = self.workflow.run(
            incident_payload=incident_payload,
            trace_id=active_trace_id,
        )

        response = self._build_process_response(
            trace_id=active_trace_id,
            final_state=final_state,
        )

        logger.info(
            "Orchestrator completed trace_id=%s incident_id=%s workflow_path=%s",
            active_trace_id,
            incident_payload.incident_id,
            response.workflow_path,
        )

        return response

    def _build_process_response(
        self,
        trace_id: str,
        final_state: IncidentIQGraphState,
    ) -> IncidentProcessResponse:
        """
        Builds the API response from the final LangGraph state.
        """

        incident_payload = final_state.get("incident_payload")

        if incident_payload is None:
            raise ValueError("incident_payload missing from final graph state.")

        triage_result = get_required_triage_result(state=final_state)
        notification_message = get_required_notification_message(state=final_state)
        knowledge_result = final_state.get("knowledge_result")
        remediation_plan = final_state.get("remediation_plan")
        workflow_path = final_state.get("workflow_path", [])

        response = IncidentProcessResponse(
            trace_id=trace_id,
            incident_id=incident_payload.incident_id,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
            remediation_plan=remediation_plan,
            notification_message=notification_message,
            workflow_path=workflow_path,
        )

        return response


def run_orchestrator(
    incident_payload: IncidentPayload,
    trace_id: str | None = None,
) -> IncidentProcessResponse:
    """
    FastAPI routes and tests will call this function.
    """

    orchestrator = Orchestrator()
    response = orchestrator.process_incident(
        incident_payload=incident_payload,
        trace_id=trace_id,
    )

    return response
