from typing import TypedDict

from app.schemas.agent_messages import (
    KnowledgeResult,
    NotificationMessage,
    RemediationPlan,
    TriageResult,
)
from app.schemas.incident import IncidentPayload


class IncidentIQGraphState(TypedDict, total=False):
    """
    IncidentIQGraphState is the shared state passed between LangGraph nodes.

    Each node reads from this state and writes its own output.

    Flow:
    - Triage Agent writes triage_result
    - Knowledge Agent writes knowledge_result
    - Remediation Agent writes remediation_plan
    - Notifier Agent writes notification_message
    """

    trace_id: str
    incident_payload: IncidentPayload
    triage_result: TriageResult
    knowledge_result: KnowledgeResult
    remediation_plan: RemediationPlan
    notification_message: NotificationMessage
    workflow_path: list[str]


def append_workflow_path(
    state: IncidentIQGraphState,
    agent_name: str,
) -> list[str]:
    """
    Appends an agent name to the workflow path.
    """

    current_workflow_path = state.get("workflow_path", [])
    updated_workflow_path = list(current_workflow_path)
    updated_workflow_path.append(agent_name)

    return updated_workflow_path


def get_required_incident_payload(
    state: IncidentIQGraphState,
) -> IncidentPayload:
    """
    Reads IncidentPayload from graph state.

    Raises a clear error when the state is invalid.
    """

    incident_payload = state.get("incident_payload")

    if incident_payload is None:
        raise ValueError("incident_payload is required in IncidentIQGraphState.")

    return incident_payload


def get_required_triage_result(
    state: IncidentIQGraphState,
) -> TriageResult:
    """
    Reads TriageResult from graph state.

    Raises a clear error when the Triage Agent has not executed.
    """

    triage_result = state.get("triage_result")

    if triage_result is None:
        raise ValueError("triage_result is required in IncidentIQGraphState.")

    return triage_result


def get_required_knowledge_result(
    state: IncidentIQGraphState,
) -> KnowledgeResult:
    """
    Reads KnowledgeResult from graph state.

    Raises a clear error when the Knowledge Agent has not executed.
    """

    knowledge_result = state.get("knowledge_result")

    if knowledge_result is None:
        raise ValueError("knowledge_result is required in IncidentIQGraphState.")

    return knowledge_result


def get_required_notification_message(
    state: IncidentIQGraphState,
) -> NotificationMessage:
    """
    Reads NotificationMessage from graph state.

    Raises a clear error when the Notifier Agent has not executed.
    """

    notification_message = state.get("notification_message")

    if notification_message is None:
        raise ValueError("notification_message is required in IncidentIQGraphState.")

    return notification_message
