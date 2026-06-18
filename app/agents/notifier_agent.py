import logging

from app.core.config import ConfigSettings, get_settings
from app.schemas.agent_messages import (
    AgentName,
    IncidentSeverity,
    KnowledgeResult,
    NotificationMessage,
    RemediationPlan,
    ToolExecutionResult,
    TriageResult,
)
from app.schemas.incident import IncidentPayload

logger = logging.getLogger("IncidentIQ.Agents.NotifierAgent")


class NotifierAgent:
    """
    Notifier Agent for IncidentIQ.
    This agent receives outputs from previous agents and creates a final
    notification message that can be posted to Slack, email, PagerDuty,
    or an incident management channel.
    """

    def __init__(self, settings: ConfigSettings | None = None) -> None:
        """
        Initializes the Notifier Agent with project settings.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

    def run(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult | None = None,
        remediation_plan: RemediationPlan | None = None,
    ) -> NotificationMessage:
        """
        Runs the Notifier Agent.

        Input:
        - IncidentPayload from POST /process
        - TriageResult from the Triage Agent
        - KnowledgeResult from the Knowledge Agent, when available
        - RemediationPlan from the Remediation Agent, when available

        Output:
        - NotificationMessage containing subject, body, and recommended channel
        """

        logger.info(
            "Notifier Agent started for incident_id=%s severity=%s",
            incident_payload.incident_id,
            triage_result.severity.value,
        )

        subject = self._build_subject(
            incident_payload=incident_payload,
            triage_result=triage_result,
        )

        body = self._build_body(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
            remediation_plan=remediation_plan,
        )

        recommended_channel = self._select_recommended_channel(
            triage_result=triage_result,
        )

        notification_message = NotificationMessage(
            agent_name=AgentName.NOTIFIER_AGENT,
            subject=subject,
            body=body,
            recommended_channel=recommended_channel,
        )

        logger.info(
            "Notifier Agent completed for incident_id=%s recommended_channel=%s",
            incident_payload.incident_id,
            recommended_channel,
        )

        return notification_message

    def _build_subject(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
    ) -> str:
        """
        Builds a short Slack/email-ready subject line.
        """

        subject = (
            f"[{triage_result.severity.value}] IncidentIQ: "
            f"{incident_payload.service} - {incident_payload.title}"
        )

        subject = self._limit_text(subject, max_length=190)

        return subject

    def _build_body(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult | None,
        remediation_plan: RemediationPlan | None,
    ) -> str:
        """
        Builds the final Slack/email-ready incident response body.

        The body is intentionally structured so it is easy to read in a
        live demo and easy for reviewers to understand.
        """

        sections: list[str] = []

        incident_section = self._build_incident_section(
            incident_payload=incident_payload,
        )
        sections.append(incident_section)

        triage_section = self._build_triage_section(
            triage_result=triage_result,
        )
        sections.append(triage_section)

        knowledge_section = self._build_knowledge_section(
            knowledge_result=knowledge_result,
        )
        sections.append(knowledge_section)

        remediation_section = self._build_remediation_section(
            remediation_plan=remediation_plan,
            triage_result=triage_result,
        )
        sections.append(remediation_section)

        next_action_section = self._build_next_action_section(
            triage_result=triage_result,
            remediation_plan=remediation_plan,
        )
        sections.append(next_action_section)

        body = "\n\n".join(sections)
        body = self._limit_text(body, max_length=4800)

        return body

    def _build_incident_section(
        self,
        incident_payload: IncidentPayload,
    ) -> str:
        """
        Builds the incident summary section.
        """

        metrics_text = self._format_metrics(
            metrics=incident_payload.metrics,
        )

        section = (
            "## Incident Summary\n"
            f"- Incident ID: {incident_payload.incident_id}\n"
            f"- Title: {incident_payload.title}\n"
            f"- Service: {incident_payload.service}\n"
            f"- Environment: {incident_payload.environment}\n"
            f"- Description: {incident_payload.description}\n"
            f"- Metrics: {metrics_text}"
        )

        return section

    def _build_triage_section(
        self,
        triage_result: TriageResult,
    ) -> str:
        """
        Builds the triage result section.
        """

        entities_text = self._format_entities(
            entities=triage_result.entities,
        )

        section = (
            "## Triage Agent Result\n"
            f"- Severity: {triage_result.severity.value}\n"
            f"- Category: {triage_result.category.value}\n"
            f"- Extracted Entities: {entities_text}\n"
            f"- Reasoning: {triage_result.reasoning_summary}"
        )

        return section

    def _build_knowledge_section(
        self,
        knowledge_result: KnowledgeResult | None,
    ) -> str:
        """
        Builds the Knowledge Agent RAG source section.

        This section shows grounding by listing retrieved runbooks and
        historical incidents.
        """

        if knowledge_result is None:
            section = (
                "## Knowledge Agent Result\n"
                "- No RAG retrieval was executed for this workflow path."
            )

            return section

        if not knowledge_result.sources:
            section = (
                "## Knowledge Agent Result\n"
                f"- Grounded Summary: {knowledge_result.grounded_summary}\n"
                "- Retrieved Sources: No matching runbooks or historical incidents found."
            )

            return section

        source_lines: list[str] = []

        for index, source in enumerate(knowledge_result.sources, start=1):
            relevance_score = source.metadata.get("relevance_score")

            if relevance_score is None:
                source_line = (
                    f"{index}. {source.title} "
                    f"({source.source_type}, source_id={source.source_id})"
                )
            else:
                source_line = (
                    f"{index}. {source.title} "
                    f"({source.source_type}, source_id={source.source_id}, "
                    f"score={relevance_score})"
                )

            source_lines.append(source_line)

        joined_sources = "\n".join(source_lines)

        section = (
            "## Knowledge Agent Result\n"
            f"- Grounded Summary: {knowledge_result.grounded_summary}\n"
            "- Retrieved Sources:\n"
            f"{joined_sources}"
        )

        return section

    def _build_remediation_section(
        self,
        remediation_plan: RemediationPlan | None,
        triage_result: TriageResult,
    ) -> str:
        """
        Builds the Remediation Agent section.

        P4 incidents may skip the Remediation Agent in the final LangGraph
        workflow, so remediation_plan can be None.
        """

        if remediation_plan is None:
            if triage_result.severity == IncidentSeverity.P4:
                section = (
                    "## Remediation Agent Result\n"
                    "- Remediation Agent was skipped because this is a P4 informational alert.\n"
                    "- No mocked DevOps tools were executed."
                )
            else:
                section = (
                    "## Remediation Agent Result\n"
                    "- Remediation Agent output is not available for this workflow path."
                )

            return section

        step_lines = self._format_remediation_steps(
            remediation_plan=remediation_plan,
        )

        tool_lines = self._format_tool_results(
            tool_results=remediation_plan.tools_executed,
        )

        approval_text = "No"

        if remediation_plan.requires_human_approval:
            approval_text = "Yes"

        section = (
            "## Remediation Agent Result\n"
            f"- Summary: {remediation_plan.summary}\n"
            f"- Requires Human Approval: {approval_text}\n"
            "- Recommended Steps:\n"
            f"{step_lines}\n"
            "- Mocked Tool Results:\n"
            f"{tool_lines}"
        )

        return section

    def _build_next_action_section(
        self,
        triage_result: TriageResult,
        remediation_plan: RemediationPlan | None,
    ) -> str:
        """
        Builds the final recommended next action section.
        """

        if triage_result.severity == IncidentSeverity.P1:
            action = (
                "Treat this as a critical incident. Keep incident commander, "
                "service owner, and on-call engineer engaged until service health is restored."
            )
        elif triage_result.severity == IncidentSeverity.P2:
            action = (
                "Treat this as a major degradation. Continue investigation, "
                "monitor customer impact, and keep on-call engineer informed."
            )
        elif triage_result.severity == IncidentSeverity.P3:
            action = (
                "Track this as a medium-priority operational issue. Validate telemetry "
                "and schedule remediation if the issue persists."
            )
        else:
            action = (
                "Keep this as informational. Continue monitoring and reopen only if "
                "customer impact or SLO breach appears."
            )

        if remediation_plan is not None:
            if remediation_plan.requires_human_approval:
                action = f"{action} Human approval is required before executing risky actions."

        section = "## Recommended Next Action\n" f"- {action}"

        return section

    def _format_metrics(
        self,
        metrics: dict[str, object],
    ) -> str:
        """
        Formats incident metrics for the notification body.
        """

        if not metrics:
            return "No metrics provided"

        metric_parts: list[str] = []

        for key, value in metrics.items():
            metric_part = f"{key}={value}"
            metric_parts.append(metric_part)

        metrics_text = ", ".join(metric_parts)

        return metrics_text

    def _format_entities(
        self,
        entities: list[str],
    ) -> str:
        """
        Formats extracted entities for display.
        """

        if not entities:
            return "No entities extracted"

        entities_text = ", ".join(entities)

        return entities_text

    def _format_remediation_steps(
        self,
        remediation_plan: RemediationPlan,
    ) -> str:
        """
        Formats remediation steps for display.
        """

        if not remediation_plan.steps:
            return "No remediation steps were generated."

        step_lines: list[str] = []

        for step in remediation_plan.steps:
            automation_text = "manual"

            if step.is_safe_to_automate:
                automation_text = "safe mocked automation"

            if step.tool_name is None:
                tool_text = "no tool"
            else:
                tool_text = step.tool_name

            step_line = (
                f"{step.step_number}. {step.action} "
                f"[mode={automation_text}, tool={tool_text}]"
            )

            step_lines.append(step_line)

        formatted_steps = "\n".join(step_lines)

        return formatted_steps

    def _format_tool_results(
        self,
        tool_results: list[ToolExecutionResult],
    ) -> str:
        """
        Formats mocked DevOps tool results for display.
        """

        if not tool_results:
            return "No mocked tools executed."

        tool_lines: list[str] = []

        for index, tool_result in enumerate(tool_results, start=1):
            tool_line = (
                f"{index}. {tool_result.tool_name} - "
                f"{tool_result.status.value}: {tool_result.message}"
            )

            tool_lines.append(tool_line)

        formatted_tools = "\n".join(tool_lines)

        return formatted_tools

    def _select_recommended_channel(
        self,
        triage_result: TriageResult,
    ) -> str:
        """
        Selects a notification channel based on severity.
        """

        if triage_result.severity == IncidentSeverity.P1:
            return "pagerduty_slack_email"

        if triage_result.severity == IncidentSeverity.P2:
            return "slack_email"

        return "slack"

    def _limit_text(
        self,
        text: str,
        max_length: int,
    ) -> str:
        """
        Limits long text safely so it fits Pydantic field constraints.
        """

        cleaned_text = text.strip()

        if len(cleaned_text) <= max_length:
            return cleaned_text

        shortened_text = cleaned_text[:max_length]
        shortened_text = shortened_text.rstrip()
        shortened_text = f"{shortened_text}..."

        return shortened_text


def run_notifier_agent(
    incident_payload: IncidentPayload,
    triage_result: TriageResult,
    knowledge_result: KnowledgeResult | None = None,
    remediation_plan: RemediationPlan | None = None,
) -> NotificationMessage:
    """
    Convenience function for running the Notifier Agent.

    LangGraph nodes can call this function later.
    """

    agent = NotifierAgent()
    notification_message = agent.run(
        incident_payload=incident_payload,
        triage_result=triage_result,
        knowledge_result=knowledge_result,
        remediation_plan=remediation_plan,
    )

    return notification_message
