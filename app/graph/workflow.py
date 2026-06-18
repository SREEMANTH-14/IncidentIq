import logging

from langgraph.graph import END, StateGraph

from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.notifier_agent import NotifierAgent
from app.agents.remediation_agent import RemediationAgent
from app.agents.triage_agent import TriageAgent
from app.core.config import ConfigSettings, get_settings
from app.graph.state import (
    IncidentIQGraphState,
    append_workflow_path,
    get_required_incident_payload,
    get_required_knowledge_result,
    get_required_triage_result,
)
from app.schemas.agent_messages import AgentName, IncidentSeverity

logger = logging.getLogger("IncidentIQ.Graph.Workflow")


class IncidentIQWorkflow:
    """
    IncidentIQWorkflow builds and executes the LangGraph workflow.

    Workflow:
    1. Triage Agent
    2. Conditional route:
       - P4 goes directly to Notifier Agent
       - P1/P2/P3 goes to Knowledge Agent
    3. Conditional route after Knowledge Agent:
       - P1/P2 goes to Remediation Agent
       - P3 goes to Notifier Agent
    4. Remediation Agent goes to Notifier Agent
    5. Notifier Agent ends the workflow
    """

    def __init__(
        self,
        settings: ConfigSettings | None = None,
        triage_agent: TriageAgent | None = None,
        knowledge_agent: KnowledgeAgent | None = None,
        remediation_agent: RemediationAgent | None = None,
        notifier_agent: NotifierAgent | None = None,
    ) -> None:
        """
        Initializes all IncidentIQ agents and compiles the LangGraph workflow.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

        if triage_agent is None:
            self.triage_agent = TriageAgent(settings=self.settings)
        else:
            self.triage_agent = triage_agent

        if knowledge_agent is None:
            self.knowledge_agent = KnowledgeAgent(settings=self.settings)
        else:
            self.knowledge_agent = knowledge_agent

        if remediation_agent is None:
            self.remediation_agent = RemediationAgent(settings=self.settings)
        else:
            self.remediation_agent = remediation_agent

        if notifier_agent is None:
            self.notifier_agent = NotifierAgent(settings=self.settings)
        else:
            self.notifier_agent = notifier_agent

        self.compiled_graph = self._build_graph()

    def run(
        self,
        incident_payload,
        trace_id: str,
    ) -> IncidentIQGraphState:
        """
        Runs the IncidentIQ LangGraph workflow for one incident.

        Input:
        - incident_payload
        - trace_id

        Output:
        - Final IncidentIQGraphState containing all executed agent outputs
        """

        logger.info(
            "IncidentIQ LangGraph workflow started trace_id=%s incident_id=%s",
            trace_id,
            incident_payload.incident_id,
        )

        initial_state: IncidentIQGraphState = {
            "trace_id": trace_id,
            "incident_payload": incident_payload,
            "workflow_path": [],
        }

        final_state = self.compiled_graph.invoke(initial_state)

        logger.info(
            "IncidentIQ LangGraph workflow completed trace_id=%s incident_id=%s workflow_path=%s",
            trace_id,
            incident_payload.incident_id,
            final_state.get("workflow_path", []),
        )

        return final_state

    def _build_graph(self):
        """
        Builds and compiles the LangGraph StateGraph and  conditional routing is defined.
        """

        workflow = StateGraph(IncidentIQGraphState)

        workflow.add_node("triage_agent", self._triage_node)
        workflow.add_node("knowledge_agent", self._knowledge_node)
        workflow.add_node("remediation_agent", self._remediation_node)
        workflow.add_node("notifier_agent", self._notifier_node)

        workflow.set_entry_point("triage_agent")

        workflow.add_conditional_edges(
            "triage_agent",
            self._route_after_triage,
            {
                "knowledge_agent": "knowledge_agent",
                "notifier_agent": "notifier_agent",
            },
        )

        workflow.add_conditional_edges(
            "knowledge_agent",
            self._route_after_knowledge,
            {
                "remediation_agent": "remediation_agent",
                "notifier_agent": "notifier_agent",
            },
        )

        workflow.add_edge("remediation_agent", "notifier_agent")
        workflow.add_edge("notifier_agent", END)

        compiled_graph = workflow.compile()

        return compiled_graph

    def _triage_node(
        self,
        state: IncidentIQGraphState,
    ) -> IncidentIQGraphState:
        """
        LangGraph node for the Triage Agent.
        """

        incident_payload = get_required_incident_payload(state=state)

        logger.info(
            "Executing LangGraph node: %s incident_id=%s",
            AgentName.TRIAGE_AGENT.value,
            incident_payload.incident_id,
        )

        triage_result = self.triage_agent.run(
            incident_payload=incident_payload,
        )

        updated_state: IncidentIQGraphState = {
            "triage_result": triage_result,
            "workflow_path": append_workflow_path(
                state=state,
                agent_name=AgentName.TRIAGE_AGENT.value,
            ),
        }

        return updated_state

    def _knowledge_node(
        self,
        state: IncidentIQGraphState,
    ) -> IncidentIQGraphState:
        """
        LangGraph node for the Knowledge Agent.
        """

        incident_payload = get_required_incident_payload(state=state)
        triage_result = get_required_triage_result(state=state)

        logger.info(
            "Executing LangGraph node: %s incident_id=%s",
            AgentName.KNOWLEDGE_AGENT.value,
            incident_payload.incident_id,
        )

        knowledge_result = self.knowledge_agent.run(
            incident_payload=incident_payload,
            triage_result=triage_result,
        )

        updated_state: IncidentIQGraphState = {
            "knowledge_result": knowledge_result,
            "workflow_path": append_workflow_path(
                state=state,
                agent_name=AgentName.KNOWLEDGE_AGENT.value,
            ),
        }

        return updated_state

    def _remediation_node(
        self,
        state: IncidentIQGraphState,
    ) -> IncidentIQGraphState:
        """
        LangGraph node for the Remediation Agent.
        """

        incident_payload = get_required_incident_payload(state=state)
        triage_result = get_required_triage_result(state=state)
        knowledge_result = get_required_knowledge_result(state=state)

        logger.info(
            "Executing LangGraph node: %s incident_id=%s",
            AgentName.REMEDIATION_AGENT.value,
            incident_payload.incident_id,
        )

        remediation_plan = self.remediation_agent.run(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
        )

        updated_state: IncidentIQGraphState = {
            "remediation_plan": remediation_plan,
            "workflow_path": append_workflow_path(
                state=state,
                agent_name=AgentName.REMEDIATION_AGENT.value,
            ),
        }

        return updated_state

    def _notifier_node(
        self,
        state: IncidentIQGraphState,
    ) -> IncidentIQGraphState:
        """
        LangGraph node for the Notifier Agent.
        """

        incident_payload = get_required_incident_payload(state=state)
        triage_result = get_required_triage_result(state=state)
        knowledge_result = state.get("knowledge_result")
        remediation_plan = state.get("remediation_plan")

        logger.info(
            "Executing LangGraph node: %s incident_id=%s",
            AgentName.NOTIFIER_AGENT.value,
            incident_payload.incident_id,
        )

        notification_message = self.notifier_agent.run(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
            remediation_plan=remediation_plan,
        )

        updated_state: IncidentIQGraphState = {
            "notification_message": notification_message,
            "workflow_path": append_workflow_path(
                state=state,
                agent_name=AgentName.NOTIFIER_AGENT.value,
            ),
        }

        return updated_state

    def _route_after_triage(
        self,
        state: IncidentIQGraphState,
    ) -> str:
        """
        Conditional routing after the Triage Agent.

        P4 informational alerts skip Knowledge and Remediation and go
        directly to the Notifier Agent.

        P1/P2/P3 incidents go to the Knowledge Agent.
        """

        triage_result = get_required_triage_result(state=state)

        if triage_result.severity == IncidentSeverity.P4:
            logger.info(
                "Routing after Triage Agent: severity=%s next=notifier_agent",
                triage_result.severity.value,
            )
            return "notifier_agent"

        logger.info(
            "Routing after Triage Agent: severity=%s next=knowledge_agent",
            triage_result.severity.value,
        )

        return "knowledge_agent"

    def _route_after_knowledge(
        self,
        state: IncidentIQGraphState,
    ) -> str:
        """
        Conditional routing after the Knowledge Agent.

        P1/P2 incidents go to Remediation Agent.
        P3 incidents go directly to Notifier Agent.
        """

        triage_result = get_required_triage_result(state=state)

        if triage_result.severity == IncidentSeverity.P1:
            logger.info(
                "Routing after Knowledge Agent: severity=%s next=remediation_agent",
                triage_result.severity.value,
            )
            return "remediation_agent"

        if triage_result.severity == IncidentSeverity.P2:
            logger.info(
                "Routing after Knowledge Agent: severity=%s next=remediation_agent",
                triage_result.severity.value,
            )
            return "remediation_agent"

        logger.info(
            "Routing after Knowledge Agent: severity=%s next=notifier_agent",
            triage_result.severity.value,
        )

        return "notifier_agent"
