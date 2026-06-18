import json
import logging
import re
from typing import Any

from app.core.config import ConfigSettings, get_settings
from app.schemas.agent_messages import (
    AgentName,
    IncidentCategory,
    IncidentSeverity,
    TriageResult,
)
from app.schemas.incident import IncidentPayload

logger = logging.getLogger("IncidentIQ.Agents.TriageAgent")


class TriageAgent:
    """
    Triage Agent for IncidentIQ.

    "Triage Agent Classifies severity (P1-P4), category, extracts entities.
    Structured output."

    This agent supports two modes:
    1. Mock mode:
       Deterministic rules are used for fast local development and stable demo.
    2. Ollama mode:
       LangChain ChatOllama is used with .with_structured_output(TriageResult).
    """

    def __init__(self, settings: ConfigSettings | None = None) -> None:
        """
        Initializes the Triage Agent with project settings.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

    def run(self, incident_payload: IncidentPayload) -> TriageResult:
        """
        Runs the Triage Agent.

        The method returns TriageResult, which is the A2A contract consumed
        by the Orchestrator, Knowledge Agent, Remediation Agent, and Notifier Agent.
        """

        logger.info(
            "Triage Agent started for incident_id=%s service=%s",
            incident_payload.incident_id,
            incident_payload.service,
        )

        if self.settings.mock_llm:
            triage_result = self._run_mock_triage(incident_payload=incident_payload)
        else:
            if self.settings.llm_provider == "ollama":
                triage_result = self._run_ollama_structured_triage(
                    incident_payload=incident_payload
                )
            else:
                logger.warning(
                    "Unsupported llm_provider=%s. Falling back to mock triage.",
                    self.settings.llm_provider,
                )
                triage_result = self._run_mock_triage(incident_payload=incident_payload)

        logger.info(
            "Triage Agent completed for incident_id=%s severity=%s category=%s",
            incident_payload.incident_id,
            triage_result.severity.value,
            triage_result.category.value,
        )

        return triage_result

    def _run_mock_triage(self, incident_payload: IncidentPayload) -> TriageResult:
        """
        Runs deterministic rule-based triage.

        """

        combined_text = self._build_combined_text(incident_payload=incident_payload)

        category = self._classify_category(combined_text=combined_text)
        severity = self._classify_severity(
            incident_payload=incident_payload,
            combined_text=combined_text,
            category=category,
        )
        entities = self._extract_entities(
            incident_payload=incident_payload,
            combined_text=combined_text,
        )
        reasoning_summary = self._build_reasoning_summary(
            incident_payload=incident_payload,
            severity=severity,
            category=category,
        )

        triage_result = TriageResult(
            agent_name=AgentName.TRIAGE_AGENT,
            severity=severity,
            category=category,
            entities=entities,
            reasoning_summary=reasoning_summary,
        )

        return triage_result

    def _run_ollama_structured_triage(
        self,
        incident_payload: IncidentPayload,
    ) -> TriageResult:
        """
        Runs LLM-based triage using Ollama and LangChain structured output.

        This method intentionally uses:
        .with_structured_output(TriageResult)

        """

        try:
            from langchain_ollama import ChatOllama
        except ImportError as error:
            logger.warning(
                "langchain-ollama is not installed. Falling back to mock triage."
            )
            logger.debug("Import error detail: %s", str(error))

            triage_result = self._run_mock_triage(incident_payload=incident_payload)

            return triage_result

        prompt = self._build_triage_prompt(incident_payload=incident_payload)

        llm = ChatOllama(
            model=self.settings.ollama_model,
            base_url=self.settings.ollama_base_url,
            temperature=0,
        )

        structured_llm = llm.with_structured_output(TriageResult)

        try:
            result = structured_llm.invoke(prompt)
        except Exception as error:
            logger.exception(
                "Ollama structured triage failed. Falling back to mock triage."
            )
            logger.debug("Ollama error detail: %s", str(error))

            triage_result = self._run_mock_triage(incident_payload=incident_payload)

            return triage_result

        if isinstance(result, TriageResult):
            return result

        if isinstance(result, dict):
            triage_result = TriageResult.model_validate(result)
            return triage_result

        logger.warning(
            "Unexpected structured LLM result type=%s. Falling back to mock triage.",
            type(result).__name__,
        )

        triage_result = self._run_mock_triage(incident_payload=incident_payload)

        return triage_result

    def _build_combined_text(self, incident_payload: IncidentPayload) -> str:
        """
        Builds one searchable text block from the incident payload.

        This helps category classification, severity classification, and
        entity extraction.
        """

        metrics_json = json.dumps(incident_payload.metrics, sort_keys=True)

        combined_text = (
            f"{incident_payload.title}\n"
            f"{incident_payload.description}\n"
            f"{incident_payload.service}\n"
            f"{incident_payload.environment}\n"
            f"{metrics_json}"
        )

        return combined_text.lower()

    def _classify_category(self, combined_text: str) -> IncidentCategory:
        """
        Classifies incident category using deterministic keyword rules.

        Categories required by IncidentIQ:
        - database
        - network
        - application
        - infra
        """

        database_keywords = [
            "database",
            "db",
            "sql",
            "sqltimeoutexception",
            "connection pool",
            "redis",
            "cache",
            "query",
            "slow query",
            "replica lag",
            "elasticsearch",
            "kafka",
        ]

        network_keywords = [
            "dns",
            "coredns",
            "tls",
            "certificate",
            "network",
            "ingress",
            "gateway",
            "503",
            "timeout connecting",
            "name resolution",
            "service mesh",
            "partition",
        ]

        infra_keywords = [
            "oomkilled",
            "pod",
            "node",
            "disk",
            "cpu throttling",
            "memory",
            "crashloopbackoff",
            "imagepullbackoff",
            "pending",
            "kubernetes",
            "openshift",
            "volume",
        ]

        application_keywords = [
            "null pointer",
            "exception",
            "deployment",
            "rollback",
            "rate limit",
            "http 429",
            "webhook",
            "api error",
            "feature flag",
            "checkout",
            "billing",
        ]

        if self._contains_any_keyword(combined_text, database_keywords):
            return IncidentCategory.DATABASE

        if self._contains_any_keyword(combined_text, network_keywords):
            return IncidentCategory.NETWORK

        if self._contains_any_keyword(combined_text, infra_keywords):
            return IncidentCategory.INFRA

        if self._contains_any_keyword(combined_text, application_keywords):
            return IncidentCategory.APPLICATION

        return IncidentCategory.UNKNOWN

    def _classify_severity(
        self,
        incident_payload: IncidentPayload,
        combined_text: str,
        category: IncidentCategory,
    ) -> IncidentSeverity:
        """
        Classifies incident severity as P1, P2, P3, or P4.

        Rules are intentionally simple and explainable for demo purposes.
        The order is important:
        1. Non-production and informational issues should become P4.
        2. Critical production keywords and severe metrics should become P1.
        3. Major degradation should become P2.
        4. Informational production alerts with no customer impact should become P4.
        5. Remaining production issues default to P3.
        """

        environment = incident_payload.environment.lower()
        metrics = incident_payload.metrics

        # Staging or development issues are usually P4 unless they clearly
        # describe a critical production impact.
        if environment != "production":
            if self._contains_any_keyword(combined_text, ["staging", "development", "dev"]):
                return IncidentSeverity.P4

        # Informational alerts with no customer impact should be P4.
        # This check must come before the UNKNOWN category fallback.
        if self._has_p4_keywords(combined_text=combined_text):
            return IncidentSeverity.P4

        # Critical production outage keywords should be treated as P1.
        if self._has_p1_keywords(combined_text=combined_text):
            return IncidentSeverity.P1

        error_rate = self._read_float_metric(
            metrics=metrics,
            possible_keys=["error_rate", "error_rate_percent", "errors_percent"],
        )
        latency_ms = self._read_float_metric(
            metrics=metrics,
            possible_keys=["latency_ms", "p95_latency_ms", "p99_latency_ms"],
        )
        db_pool_usage = self._read_float_metric(
            metrics=metrics,
            possible_keys=["db_pool_usage", "db_pool_usage_percent", "pool_usage"],
        )
        cpu_usage = self._read_float_metric(
            metrics=metrics,
            possible_keys=["cpu_usage", "cpu_usage_percent"],
        )
        memory_usage = self._read_float_metric(
            metrics=metrics,
            possible_keys=["memory_usage", "memory_usage_percent"],
        )

        # Severe metric thresholds indicate P1.
        if db_pool_usage is not None:
            if db_pool_usage >= 95:
                return IncidentSeverity.P1

        if error_rate is not None:
            if error_rate >= 10:
                return IncidentSeverity.P1

        if latency_ms is not None:
            if latency_ms >= 2000:
                return IncidentSeverity.P1

        # Major degradation keywords indicate P2.
        if self._has_p2_keywords(combined_text=combined_text):
            return IncidentSeverity.P2

        if cpu_usage is not None:
            if cpu_usage >= 90:
                return IncidentSeverity.P2

        if memory_usage is not None:
            if memory_usage >= 90:
                return IncidentSeverity.P2

        # If we still do not understand the category, treat it as P3.
        # This is placed after P4 checks so informational alerts are not
        # incorrectly classified as P3.
        if category == IncidentCategory.UNKNOWN:
            return IncidentSeverity.P3

        # Default production issue is P3.
        if environment == "production":
            return IncidentSeverity.P3

        return IncidentSeverity.P4
    def _extract_entities(
        self,
        incident_payload: IncidentPayload,
        combined_text: str,
    ) -> list[str]:
        """
        Extracts simple incident entities.

        These entities help the Knowledge Agent build better RAG queries.
        """

        entities: list[str] = []

        self._append_unique_entity(
            entities=entities,
            entity=incident_payload.service,
        )

        self._append_unique_entity(
            entities=entities,
            entity=incident_payload.environment,
        )

        for metric_name in incident_payload.metrics.keys():
            self._append_unique_entity(
                entities=entities,
                entity=str(metric_name),
            )

        known_terms = [
            "SQLTimeoutException",
            "OOMKilled",
            "CrashLoopBackOff",
            "ImagePullBackOff",
            "CoreDNS",
            "Redis",
            "HTTP 429",
            "TLS",
            "DNS",
            "503",
            "connection pool",
            "certificate",
            "rollback",
            "deployment",
            "replica lag",
            "service mesh",
        ]

        for term in known_terms:
            if term.lower() in combined_text:
                self._append_unique_entity(
                    entities=entities,
                    entity=term,
                )

        error_code_entities = self._extract_error_codes(
            text=incident_payload.description,
        )

        for error_code in error_code_entities:
            self._append_unique_entity(
                entities=entities,
                entity=error_code,
            )

        return entities

    def _extract_error_codes(self, text: str) -> list[str]:
        """
        Extracts basic HTTP-style and exception-style error codes from text.
        """

        entities: list[str] = []

        http_code_matches = re.findall(r"\b[1-5][0-9]{2}\b", text)

        for match in http_code_matches:
            self._append_unique_entity(
                entities=entities,
                entity=match,
            )

        exception_matches = re.findall(r"\b[A-Za-z]+Exception\b", text)

        for match in exception_matches:
            self._append_unique_entity(
                entities=entities,
                entity=match,
            )

        return entities

    def _build_reasoning_summary(
        self,
        incident_payload: IncidentPayload,
        severity: IncidentSeverity,
        category: IncidentCategory,
    ) -> str:
        """
        Builds a short human-readable explanation for the triage decision.
        """

        summary = (
            f"{incident_payload.service} in {incident_payload.environment} "
            f"was classified as {severity.value} because the incident title and "
            f"description indicate a {category.value} issue with production impact "
            f"or operational risk."
        )

        return summary

    def _build_triage_prompt(self, incident_payload: IncidentPayload) -> str:
        """
        Builds the prompt for Ollama structured triage.

        The output schema is enforced by .with_structured_output(TriageResult).
        """

        metrics_json = json.dumps(
            incident_payload.metrics,
            indent=2,
            sort_keys=True,
        )

        prompt = f"""
You are the Triage Agent for IncidentIQ.

Your task:
1. Classify incident severity as P1, P2, P3, or P4.
2. Classify category as database, network, application, infra, or unknown.
3. Extract important entities such as service name, pod name, error code,
   exception name, namespace, metric names, database, DNS, Redis, gateway,
   certificate, deployment, or Kubernetes/OpenShift terms.
4. Return only the structured output requested by the schema.

Severity guidance:
- P1: Critical production outage, customer transactions failing, payment/login/checkout unavailable,
      high error rate, major dependency failure, TLS outage, DNS outage, or data path outage.
- P2: Major degradation, high latency, repeated pod restarts, rate limits, partial customer impact.
- P3: Medium issue, internal degradation, delayed jobs, non-critical service impact.
- P4: Informational, staging/development only, no customer impact.

Incident:
Incident ID: {incident_payload.incident_id}
Title: {incident_payload.title}
Description: {incident_payload.description}
Service: {incident_payload.service}
Environment: {incident_payload.environment}
Metrics:
{metrics_json}
"""

        return prompt.strip()

    def _contains_any_keyword(
        self,
        text: str,
        keywords: list[str],
    ) -> bool:
        """
        Checks whether text contains any keyword.
        """

        for keyword in keywords:
            if keyword.lower() in text:
                return True

        return False

    def _has_p1_keywords(self, combined_text: str) -> bool:
        """
        Detects P1 severity keywords.
        """

        p1_keywords = [
            "outage",
            "unavailable",
            "customer transactions fail",
            "checkout failed",
            "checkout failures",
            "payment failed",
            "payment failures",
            "login unavailable",
            "tls handshake error",
            "certificate expired",
            "dns resolution failure",
            "production api down",
            "data loss",
            "major incident",
        ]

        return self._contains_any_keyword(combined_text, p1_keywords)

    def _has_p2_keywords(self, combined_text: str) -> bool:
        """
        Detects P2 severity keywords.
        """

        p2_keywords = [
            "degraded",
            "high latency",
            "latency increased",
            "partial impact",
            "repeated restarts",
            "oomkilled",
            "http 429",
            "rate limit",
            "queue depth",
            "consumer lag",
            "crashloopbackoff",
            "503",
        ]

        return self._contains_any_keyword(combined_text, p2_keywords)

    def _has_p4_keywords(self, combined_text: str) -> bool:
        """
        Detects P4 severity keywords.
        """

        p4_keywords = [
            "informational",
            "no customer impact",
            "staging only",
            "development only",
            "within slo",
            "minor increase",
        ]

        return self._contains_any_keyword(combined_text, p4_keywords)

    def _read_float_metric(
        self,
        metrics: dict[str, Any],
        possible_keys: list[str],
    ) -> float | None:
        """
        Reads a numeric metric from possible metric keys.

        Returns None when no valid numeric metric is available.
        """

        for key in possible_keys:
            if key not in metrics:
                continue

            raw_value = metrics.get(key)

            if raw_value is None:
                continue

            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError):
                continue

            return numeric_value

        return None

    def _append_unique_entity(
        self,
        entities: list[str],
        entity: str,
    ) -> None:
        """
        Appends an entity only when it is not empty and not already present.
        """

        cleaned_entity = entity.strip()

        if not cleaned_entity:
            return

        existing_entities_lower = []

        for existing_entity in entities:
            existing_entities_lower.append(existing_entity.lower())

        if cleaned_entity.lower() in existing_entities_lower:
            return

        entities.append(cleaned_entity)


def run_triage_agent(incident_payload: IncidentPayload) -> TriageResult:
    """
    Convenience function for running the Triage Agent.

    LangGraph nodes can call this function later.
    """

    agent = TriageAgent()
    triage_result = agent.run(incident_payload=incident_payload)

    return triage_result
