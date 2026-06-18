import logging

from app.core.config import ConfigSettings, get_settings
from app.schemas.agent_messages import (
    AgentName,
    IncidentCategory,
    IncidentSeverity,
    KnowledgeResult,
    RemediationPlan,
    RemediationStep,
    ToolExecutionResult,
    TriageResult,
)
from app.schemas.incident import IncidentPayload
from app.tools import execute_mocked_devops_tool, skip_mocked_devops_tool

logger = logging.getLogger("IncidentIQ.Agents.RemediationAgent")


class RemediationAgent:
    """
    This agent receives:
    - IncidentPayload
    - TriageResult
    - KnowledgeResult
    It returns:
    - RemediationPlan
    The Remediation Agent uses mocked DevOps tools only.
    It does not execute real Kubernetes, OpenShift, Docker, shell, cloud,
    database, or production commands.
    """

    def __init__(self, settings: ConfigSettings | None = None) -> None:
        """
        Initializes the Remediation Agent with project settings.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

    def run(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
    ) -> RemediationPlan:
        """
        Runs the Remediation Agent.

        Input:
        - IncidentPayload from POST /process
        - TriageResult from the Triage Agent
        - KnowledgeResult from the Knowledge Agent

        Output:
        - RemediationPlan with remediation steps and mocked tool results
        """

        logger.info(
            "Remediation Agent started for incident_id=%s severity=%s category=%s",
            incident_payload.incident_id,
            triage_result.severity.value,
            triage_result.category.value,
        )

        remediation_steps = self._build_remediation_steps(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
        )

        tool_results = self._execute_safe_tools(
            incident_payload=incident_payload,
            triage_result=triage_result,
            remediation_steps=remediation_steps,
        )

        requires_human_approval = self._requires_human_approval(
            remediation_steps=remediation_steps,
            tool_results=tool_results,
        )

        summary = self._build_remediation_summary(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
            remediation_steps=remediation_steps,
            tool_results=tool_results,
            requires_human_approval=requires_human_approval,
        )

        remediation_plan = RemediationPlan(
            agent_name=AgentName.REMEDIATION_AGENT,
            summary=summary,
            steps=remediation_steps,
            tools_executed=tool_results,
            requires_human_approval=requires_human_approval,
        )

        logger.info(
            "Remediation Agent completed for incident_id=%s steps=%s tools_executed=%s requires_human_approval=%s",
            incident_payload.incident_id,
            len(remediation_steps),
            len(tool_results),
            requires_human_approval,
        )

        return remediation_plan
    
    def _format_retrieved_source_context(
        self,
        knowledge_result: KnowledgeResult,
    ) -> str:
        """
        Builds a short readable context from retrieved RAG sources.

        This ensures the Remediation Agent actually uses the Knowledge Agent
        output while generating remediation steps.
        """

        if not knowledge_result.sources:
            return "No retrieved runbook or historical incident source is available."

        source_titles: list[str] = []

        for source in knowledge_result.sources:
            source_title = f"{source.title} ({source.source_type})"
            source_titles.append(source_title)

        joined_sources = ", ".join(source_titles)

        context = f"Retrieved sources: {joined_sources}"
        context = self._limit_text(context, max_length=600)

        return context

    def _build_remediation_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
    ) -> list[RemediationStep]:
        """
        Builds remediation steps based on incident severity, category,
        and retrieved RAG knowledge.

        The steps are deterministic and explainable so the demo remains stable.
        """

        steps: list[RemediationStep] = []
        step_number = 1

        if triage_result.severity == IncidentSeverity.P4:
            step = RemediationStep(
                step_number=step_number,
                action=(
                    "Observe the alert and keep it as informational because "
                    "there is no confirmed customer impact."
                ),
                is_safe_to_automate=False,
                tool_name=None,
            )
            steps.append(step)

            return steps

        step = RemediationStep(
            step_number=step_number,
            action=(
                f"Check mocked health status for {incident_payload.service} "
                f"in {incident_payload.environment}."
            ),
            is_safe_to_automate=True,
            tool_name="check_service_health",
        )
        steps.append(step)
        step_number = step_number + 1

        category_steps = self._build_category_specific_steps(
            incident_payload=incident_payload,
            triage_result=triage_result,
            knowledge_result=knowledge_result,
            starting_step_number=step_number,
        )

        steps.extend(category_steps)
        step_number = step_number + len(category_steps)

        if self._should_notify_oncall(triage_result=triage_result):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Notify the on-call engineer for {incident_payload.service} "
                    f"because severity is {triage_result.severity.value}."
                ),
                is_safe_to_automate=True,
                tool_name="notify_oncall",
            )
            steps.append(step)

        return steps

    def _build_category_specific_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds category-specific remediation steps.

        Categories are from the Triage Agent:
        - database
        - network
        - application
        - infra
        - unknown
        """

        if triage_result.category == IncidentCategory.DATABASE:
            steps = self._build_database_steps(
                incident_payload=incident_payload,
                triage_result=triage_result,
                knowledge_result=knowledge_result,
                starting_step_number=starting_step_number,
            )
            return steps

        if triage_result.category == IncidentCategory.NETWORK:
            steps = self._build_network_steps(
                incident_payload=incident_payload,
                triage_result=triage_result,
                knowledge_result=knowledge_result,
                starting_step_number=starting_step_number,
            )
            return steps

        if triage_result.category == IncidentCategory.APPLICATION:
            steps = self._build_application_steps(
                incident_payload=incident_payload,
                triage_result=triage_result,
                knowledge_result=knowledge_result,
                starting_step_number=starting_step_number,
            )
            return steps

        if triage_result.category == IncidentCategory.INFRA:
            steps = self._build_infra_steps(
                incident_payload=incident_payload,
                triage_result=triage_result,
                knowledge_result=knowledge_result,
                starting_step_number=starting_step_number,
            )
            return steps

        steps = self._build_unknown_category_steps(
            incident_payload=incident_payload,
            knowledge_result=knowledge_result,
            starting_step_number=starting_step_number,
        )

        return steps

    def _build_database_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds remediation steps for database incidents.

        Uses KnowledgeResult so the plan is connected to retrieved runbooks
        and historical incidents.
        """

        steps: list[RemediationStep] = []
        step_number = starting_step_number
        source_context = self._format_retrieved_source_context(
            knowledge_result=knowledge_result
        )

        step = RemediationStep(
            step_number=step_number,
            action=(
                f"Review database-specific retrieved knowledge for "
                f"{incident_payload.service} in {incident_payload.environment}. "
                f"{source_context}."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        step = RemediationStep(
            step_number=step_number,
            action=(
                "Check database connection pool usage, active sessions, slow query dashboard, "
                "replica lag, Redis/cache pressure, and recent database-related deployment changes."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        if self._is_high_severity(triage_result=triage_result):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Temporarily scale {incident_payload.service} to reduce request pressure "
                    "while the database bottleneck is investigated."
                ),
                is_safe_to_automate=True,
                tool_name="scale_deployment",
            )
            steps.append(step)
            step_number = step_number + 1

            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Restart {incident_payload.service} only if connection leak symptoms "
                    "are confirmed from logs or pool metrics."
                ),
                is_safe_to_automate=True,
                tool_name="restart_service",
            )
            steps.append(step)

        return steps

    def _build_network_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds remediation steps for network incidents.

        Uses IncidentPayload and KnowledgeResult so there are no unused parameters.
        """

        steps: list[RemediationStep] = []
        step_number = starting_step_number
        source_context = self._format_retrieved_source_context(
            knowledge_result=knowledge_result
        )

        step = RemediationStep(
            step_number=step_number,
            action=(
                f"Review network-specific retrieved knowledge for "
                f"{incident_payload.service} in {incident_payload.environment}. "
                f"{source_context}."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        step = RemediationStep(
            step_number=step_number,
            action=(
                "Validate DNS resolution, TLS certificate status, ingress or gateway health, "
                "service mesh telemetry, provider connectivity, and recent network policy changes."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        if self._is_high_severity(triage_result=triage_result):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"For {incident_payload.service}, shift traffic to a healthy endpoint "
                    "or availability zone only if a safe fallback is already configured."
                ),
                is_safe_to_automate=False,
                tool_name=None,
            )
            steps.append(step)

        return steps

    def _build_application_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds remediation steps for application incidents.

        Uses retrieved source context to keep remediation grounded.
        """

        steps: list[RemediationStep] = []
        step_number = starting_step_number
        source_context = self._format_retrieved_source_context(
            knowledge_result=knowledge_result
        )

        step = RemediationStep(
            step_number=step_number,
            action=(
                f"Review application-specific retrieved knowledge for "
                f"{incident_payload.service} in {incident_payload.environment}. "
                f"{source_context}."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        step = RemediationStep(
            step_number=step_number,
            action=(
                "Check recent deployments, feature flags, application logs, error rate, "
                "new exceptions, dependency latency, rate limits, and webhook failures."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        if self._incident_mentions_deployment_risk(
            incident_payload=incident_payload,
            knowledge_result=knowledge_result,
        ):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Rollback {incident_payload.service} to the previous stable version "
                    "only after human approval because rollback can impact active users."
                ),
                is_safe_to_automate=False,
                tool_name="rollback_deployment",
            )
            steps.append(step)
            step_number = step_number + 1

        if self._is_high_severity(triage_result=triage_result):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Restart {incident_payload.service} if application health checks "
                    "confirm stuck workers, bad runtime state, or repeated failures."
                ),
                is_safe_to_automate=True,
                tool_name="restart_service",
            )
            steps.append(step)

        return steps

    def _build_infra_steps(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds remediation steps for infrastructure incidents.

        Uses KnowledgeResult so infrastructure remediation is grounded in RAG.
        """

        steps: list[RemediationStep] = []
        step_number = starting_step_number
        source_context = self._format_retrieved_source_context(
            knowledge_result=knowledge_result
        )

        step = RemediationStep(
            step_number=step_number,
            action=(
                f"Review infrastructure-specific retrieved knowledge for "
                f"{incident_payload.service} in {incident_payload.environment}. "
                f"{source_context}."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        step = RemediationStep(
            step_number=step_number,
            action=(
                "Check Kubernetes/OpenShift pod status, restart count, node capacity, "
                "events, memory limits, CPU throttling, disk usage, and persistent volume health."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)
        step_number = step_number + 1

        if self._is_high_severity(triage_result=triage_result):
            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Scale {incident_payload.service} if enough cluster capacity is available "
                    "and autoscaling has not already recovered the service."
                ),
                is_safe_to_automate=True,
                tool_name="scale_deployment",
            )
            steps.append(step)
            step_number = step_number + 1

            step = RemediationStep(
                step_number=step_number,
                action=(
                    f"Restart unhealthy {incident_payload.service} pods if they are stuck "
                    "or repeatedly failing health checks."
                ),
                is_safe_to_automate=True,
                tool_name="restart_service",
            )
            steps.append(step)

        return steps

    def _build_unknown_category_steps(
        self,
        incident_payload: IncidentPayload,
        knowledge_result: KnowledgeResult,
        starting_step_number: int,
    ) -> list[RemediationStep]:
        """
        Builds safe remediation steps when category is unknown.

        Uses both IncidentPayload and KnowledgeResult so the recommendation still
        includes service context and retrieved knowledge.
        """

        steps: list[RemediationStep] = []
        source_context = self._format_retrieved_source_context(
            knowledge_result=knowledge_result
        )

        step = RemediationStep(
            step_number=starting_step_number,
            action=(
                f"Review telemetry and retrieved knowledge for {incident_payload.service} "
                f"in {incident_payload.environment} because the category is unknown. "
                f"{source_context}."
            ),
            is_safe_to_automate=False,
            tool_name=None,
        )
        steps.append(step)

        return steps

    def _execute_safe_tools(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        remediation_steps: list[RemediationStep],
    ) -> list[ToolExecutionResult]:
        """
        Executes mocked DevOps tools for steps marked as safe to automate.

        Risky steps with tool names are skipped and returned as skipped tool
        results so reviewers can see human-in-the-loop style control.
        """

        tool_results: list[ToolExecutionResult] = []

        for step in remediation_steps:
            if step.tool_name is None:
                continue

            if step.is_safe_to_automate:
                tool_arguments = self._build_tool_arguments(
                    tool_name=step.tool_name,
                    incident_payload=incident_payload,
                    triage_result=triage_result,
                )

                result = execute_mocked_devops_tool(
                    tool_name=step.tool_name,
                    tool_arguments=tool_arguments,
                )

                tool_results.append(result)
            else:
                result = skip_mocked_devops_tool(
                    tool_name=step.tool_name,
                    reason=(
                        f"Step {step.step_number} requires human approval before "
                        f"executing {step.tool_name}."
                    ),
                )

                tool_results.append(result)

        return tool_results

    def _build_tool_arguments(
        self,
        tool_name: str,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
    ) -> dict[str, object]:
        """
        Builds arguments for each mocked DevOps tool.

        All tools receive only safe, validated data from IncidentPayload
        and TriageResult.
        """

        if tool_name == "check_service_health":
            return {
                "service": incident_payload.service,
                "environment": incident_payload.environment,
            }

        if tool_name == "restart_service":
            return {
                "service": incident_payload.service,
                "environment": incident_payload.environment,
            }

        if tool_name == "scale_deployment":
            replicas = self._select_replica_count(triage_result=triage_result)

            return {
                "service": incident_payload.service,
                "environment": incident_payload.environment,
                "replicas": replicas,
            }

        if tool_name == "rollback_deployment":
            return {
                "service": incident_payload.service,
                "environment": incident_payload.environment,
                "target_version": "previous-stable",
            }

        if tool_name == "notify_oncall":
            notification_message = (
                f"{triage_result.severity.value} incident for "
                f"{incident_payload.service}: {incident_payload.title}"
            )

            return {
                "service": incident_payload.service,
                "environment": incident_payload.environment,
                "severity": triage_result.severity.value,
                "message": notification_message,
            }

        return {}

    def _select_replica_count(self, triage_result: TriageResult) -> int:
        """
        Selects a safe mocked replica count based on severity.
        """

        if triage_result.severity == IncidentSeverity.P1:
            return 4

        if triage_result.severity == IncidentSeverity.P2:
            return 3

        return 2

    def _requires_human_approval(
        self,
        remediation_steps: list[RemediationStep],
        tool_results: list[ToolExecutionResult],
    ) -> bool:
        """
        Determines whether the plan contains actions requiring human approval.
        """

        for step in remediation_steps:
            if step.tool_name is not None:
                if not step.is_safe_to_automate:
                    return True

        for tool_result in tool_results:
            if tool_result.status.value == "skipped":
                return True

        return False

    def _build_remediation_summary(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        knowledge_result: KnowledgeResult,
        remediation_steps: list[RemediationStep],
        tool_results: list[ToolExecutionResult],
        requires_human_approval: bool,
    ) -> str:
        """
        Builds a concise remediation summary for the final response.
        """

        executed_tool_names: list[str] = []

        for tool_result in tool_results:
            if tool_result.status.value == "success":
                executed_tool_names.append(tool_result.tool_name)

        if executed_tool_names:
            executed_tools_text = ", ".join(executed_tool_names)
        else:
            executed_tools_text = "none"

        source_count = len(knowledge_result.sources)
        step_count = len(remediation_steps)

        approval_text = "No human approval is required for executed mocked actions."

        if requires_human_approval:
            approval_text = (
                "Some recommended actions require human approval before execution."
            )

        summary = (
            f"Prepared {step_count} remediation steps for {incident_payload.service}. "
            f"The incident is classified as {triage_result.severity.value} "
            f"and category {triage_result.category.value}. "
            f"The plan was grounded using {source_count} retrieved knowledge sources. "
            f"Mocked tools executed successfully: {executed_tools_text}. "
            f"{approval_text}"
        )

        summary = self._limit_text(summary, max_length=1400)

        return summary

    def _is_high_severity(self, triage_result: TriageResult) -> bool:
        """
        Returns True for P1 and P2 incidents.
        """

        if triage_result.severity == IncidentSeverity.P1:
            return True

        if triage_result.severity == IncidentSeverity.P2:
            return True

        return False

    def _should_notify_oncall(self, triage_result: TriageResult) -> bool:
        """
        Decides whether on-call notification should be sent.

        P1 and P2 incidents should notify on-call.
        P3 and P4 incidents do not auto-notify in this demo.
        """

        if triage_result.severity == IncidentSeverity.P1:
            return True

        if triage_result.severity == IncidentSeverity.P2:
            return True

        return False

    def _incident_mentions_deployment_risk(
        self,
        incident_payload: IncidentPayload,
        knowledge_result: KnowledgeResult,
    ) -> bool:
        """
        Detects whether rollback should be recommended with human approval.
        """

        combined_text_parts: list[str] = [
            incident_payload.title,
            incident_payload.description,
            knowledge_result.grounded_summary,
        ]

        for source in knowledge_result.sources:
            combined_text_parts.append(source.title)
            combined_text_parts.append(source.content)

        combined_text = " ".join(combined_text_parts)
        combined_text = combined_text.lower()

        deployment_keywords = [
            "deployment",
            "rollback",
            "release",
            "new version",
            "feature flag",
            "bad deployment",
            "health checks fail",
            "exception after deployment",
        ]

        for keyword in deployment_keywords:
            if keyword in combined_text:
                return True

        return False

    def _limit_text(self, text: str, max_length: int) -> str:
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


def run_remediation_agent(
    incident_payload: IncidentPayload,
    triage_result: TriageResult,
    knowledge_result: KnowledgeResult,
) -> RemediationPlan:
    """
    Convenience function for running the Remediation Agent.

    LangGraph nodes can call this function later.
    """

    agent = RemediationAgent()
    remediation_plan = agent.run(
        incident_payload=incident_payload,
        triage_result=triage_result,
        knowledge_result=knowledge_result,
    )

    return remediation_plan
