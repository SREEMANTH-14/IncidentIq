import logging

from app.core.config import ConfigSettings, get_settings
from app.rag.retriever import IncidentIQRetriever
from app.schemas.agent_messages import (
    AgentName,
    KnowledgeResult,
    KnowledgeSource,
    TriageResult,
)
from app.schemas.incident import IncidentPayload

logger = logging.getLogger("IncidentIQ.Agents.KnowledgeAgent")


class KnowledgeAgent:
    """
    Knowledge Agent for IncidentIQ.

    "Knowledge Agent RAG retrieval over runbooks and historical incidents."
    """

    def __init__(
        self,
        settings: ConfigSettings | None = None,
        retriever: IncidentIQRetriever | None = None,
    ) -> None:
        """
        Initializes the Knowledge Agent.

        The retriever can be injected during testing. In normal application
        usage, the agent creates IncidentIQRetriever automatically.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

        if retriever is None:
            self.retriever = IncidentIQRetriever(settings=self.settings)
        else:
            self.retriever = retriever

    def run(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
    ) -> KnowledgeResult:
        """
        Runs the Knowledge Agent.

        Input:
        - IncidentPayload from POST /process
        - TriageResult from the Triage Agent

        Output:
        - KnowledgeResult containing retrieved RAG sources and grounded summary
        """

        logger.info(
            "Knowledge Agent started for incident_id=%s severity=%s category=%s",
            incident_payload.incident_id,
            triage_result.severity.value,
            triage_result.category.value,
        )

        rag_query = self._build_rag_query(
            incident_payload=incident_payload,
            triage_result=triage_result,
        )

        sources = self.retriever.retrieve_for_incident(
            title=incident_payload.title,
            description=incident_payload.description,
            service=incident_payload.service,
            severity=triage_result.severity.value,
            category=triage_result.category.value,
            entities=triage_result.entities,
            top_k=self.settings.retrieval_top_k,
        )

        grounded_summary = self._build_grounded_summary(
            incident_payload=incident_payload,
            triage_result=triage_result,
            sources=sources,
        )

        knowledge_result = KnowledgeResult(
            agent_name=AgentName.KNOWLEDGE_AGENT,
            query=rag_query,
            sources=sources,
            grounded_summary=grounded_summary,
        )

        logger.info(
            "Knowledge Agent completed for incident_id=%s retrieved_sources=%s",
            incident_payload.incident_id,
            len(sources),
        )

        return knowledge_result

    def _build_rag_query(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
    ) -> str:
        """
        Builds a RAG query using incident details and triage output.

        This query is stored in KnowledgeResult.
        """

        query_parts: list[str] = []

        query_parts.append(f"Incident title: {incident_payload.title}")
        query_parts.append(f"Description: {incident_payload.description}")
        query_parts.append(f"Affected service: {incident_payload.service}")
        query_parts.append(f"Environment: {incident_payload.environment}")
        query_parts.append(f"Severity: {triage_result.severity.value}")
        query_parts.append(f"Category: {triage_result.category.value}")

        if triage_result.entities:
            joined_entities = ", ".join(triage_result.entities)
            query_parts.append(f"Extracted entities: {joined_entities}")

        if incident_payload.metrics:
            metric_names = []

            for metric_name in incident_payload.metrics.keys():
                metric_names.append(str(metric_name))

            joined_metric_names = ", ".join(metric_names)
            query_parts.append(f"Metric names: {joined_metric_names}")

        rag_query = "\n".join(query_parts)
        rag_query = self._limit_text(rag_query, max_length=1900)

        return rag_query

    def _build_grounded_summary(
        self,
        incident_payload: IncidentPayload,
        triage_result: TriageResult,
        sources: list[KnowledgeSource],
    ) -> str:
        """
        Builds a grounded summary from retrieved sources.

        This method does not hallucinate. It summarizes only:
        - incident details
        - triage result
        - retrieved source titles and metadata

        The Remediation Agent will later use this summary and sources to
        propose remediation steps.
        """

        if not sources:
            summary = (
                f"No matching runbooks or historical incidents were retrieved for "
                f"{incident_payload.service}. The incident is classified as "
                f"{triage_result.severity.value} and category "
                f"{triage_result.category.value}. Manual review is recommended."
            )

            return summary

        source_summaries = self._build_source_summaries(sources=sources)

        summary_parts: list[str] = []

        summary_parts.append(
            f"Retrieved {len(sources)} grounded sources for "
            f"{incident_payload.service}."
        )
        summary_parts.append(
            f"The incident is classified as {triage_result.severity.value} "
            f"and category {triage_result.category.value}."
        )
        summary_parts.append(
            "Most relevant knowledge sources include: " f"{source_summaries}."
        )

        if triage_result.category.value == "database":
            summary_parts.append(
                "The retrieved knowledge should be checked for database pool usage, "
                "slow queries, replica lag, Redis/cache pressure, and safe restart or scaling guidance."
            )
        elif triage_result.category.value == "network":
            summary_parts.append(
                "The retrieved knowledge should be checked for DNS, TLS, gateway, ingress, "
                "service mesh, provider connectivity, and failover guidance."
            )
        elif triage_result.category.value == "infra":
            summary_parts.append(
                "The retrieved knowledge should be checked for pod health, OOMKilled events, "
                "disk usage, CPU throttling, node capacity, and Kubernetes/OpenShift remediation."
            )
        elif triage_result.category.value == "application":
            summary_parts.append(
                "The retrieved knowledge should be checked for deployment issues, application exceptions, "
                "rate limits, rollback guidance, and feature flag safeguards."
            )
        else:
            summary_parts.append(
                "The retrieved knowledge should be reviewed to identify the most likely operational cause."
            )

        summary = " ".join(summary_parts)
        summary = self._limit_text(summary, max_length=1900)

        return summary

    def _build_source_summaries(self, sources: list[KnowledgeSource]) -> str:
        """
        Builds a compact source list for the grounded summary.

        Example output:
        Database Connection Pool Exhaustion Runbook (runbook, score 0.8321),
        INC-001 historical incident (historical_incident, score 0.8012)
        """

        source_summary_parts: list[str] = []

        for source in sources:
            source_type = source.source_type
            title = source.title
            relevance_score = source.metadata.get("relevance_score")

            if relevance_score is None:
                source_summary = f"{title} ({source_type})"
            else:
                source_summary = f"{title} ({source_type}, score {relevance_score})"

            source_summary_parts.append(source_summary)

        source_summaries = ", ".join(source_summary_parts)

        return source_summaries

    def _limit_text(self, text: str, max_length: int) -> str:
        """
        Limits long text safely so it fits Pydantic field constraints.

        KnowledgeResult has max length constraints, so this avoids validation
        failures when incident descriptions are long.
        """

        cleaned_text = text.strip()

        if len(cleaned_text) <= max_length:
            return cleaned_text

        shortened_text = cleaned_text[:max_length]
        shortened_text = shortened_text.rstrip()
        shortened_text = f"{shortened_text}..."

        return shortened_text


def run_knowledge_agent(
    incident_payload: IncidentPayload,
    triage_result: TriageResult,
) -> KnowledgeResult:
    """
    Convenience function for running the Knowledge Agent.
    """

    agent = KnowledgeAgent()
    knowledge_result = agent.run(
        incident_payload=incident_payload,
        triage_result=triage_result,
    )

    return knowledge_result
