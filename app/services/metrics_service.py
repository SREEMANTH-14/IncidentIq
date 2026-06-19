import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from app.core.config import ConfigSettings
from app.schemas.metrics import (
    AgentWorkflowMetrics,
    HTTPRouteMetric,
    MetricsResponse,
)
from app.schemas.responses import IncidentProcessResponse

logger = logging.getLogger("IncidentIQ.Services.MetricsService")


@dataclass(slots=True)
class RouteMetricCounter:
    """
    Internal counter for one HTTP route.
    """

    method: str
    path: str
    count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0


class ApplicationMetrics:
    """
    ApplicationMetrics stores simple in-memory metrics.

    This is intentionally dependency-free. It avoids adding Prometheus
    packages while still exposing a useful /metrics endpoint.
    """

    def __init__(self) -> None:
        """
        Initializes all metric counters.
        """

        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)

        self._total_http_requests = 0
        self._total_http_errors = 0
        self._total_http_duration_ms = 0.0

        self._route_counters: dict[str, RouteMetricCounter] = {}

        self._total_incidents_processed = 0
        self._incidents_by_severity: dict[str, int] = {}
        self._incidents_by_category: dict[str, int] = {}
        self._workflow_path_counts: dict[str, int] = {}
        self._total_mocked_tool_executions = 0

    def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """
        Records one completed HTTP request.
        """

        normalized_method = method.upper()
        normalized_path = self._normalize_path(path=path)
        route_key = f"{normalized_method} {normalized_path}"

        with self._lock:
            route_counter = self._route_counters.get(route_key)

            if route_counter is None:
                route_counter = RouteMetricCounter(
                    method=normalized_method,
                    path=normalized_path,
                )
                self._route_counters[route_key] = route_counter

            route_counter.count = route_counter.count + 1
            route_counter.total_duration_ms = (
                route_counter.total_duration_ms + duration_ms
            )

            self._total_http_requests = self._total_http_requests + 1
            self._total_http_duration_ms = self._total_http_duration_ms + duration_ms

            if status_code >= 400:
                route_counter.error_count = route_counter.error_count + 1
                self._total_http_errors = self._total_http_errors + 1

        logger.debug(
            "HTTP metrics recorded method=%s path=%s status_code=%s duration_ms=%s",
            normalized_method,
            normalized_path,
            status_code,
            duration_ms,
        )

    def record_incident_process(
        self,
        response: IncidentProcessResponse,
    ) -> None:
        """
        Records metrics after POST /process completes successfully.
        """

        severity = response.triage_result.severity.value
        category = response.triage_result.category.value
        workflow_path = " -> ".join(response.workflow_path)

        if response.remediation_plan is None:
            tool_execution_count = 0
        else:
            tool_execution_count = len(response.remediation_plan.tools_executed)

        with self._lock:
            self._total_incidents_processed = self._total_incidents_processed + 1

            self._increment_counter(
                counters=self._incidents_by_severity,
                key=severity,
            )

            self._increment_counter(
                counters=self._incidents_by_category,
                key=category,
            )

            self._increment_counter(
                counters=self._workflow_path_counts,
                key=workflow_path,
            )

            self._total_mocked_tool_executions = (
                self._total_mocked_tool_executions + tool_execution_count
            )

        logger.info(
            "Incident workflow metrics recorded incident_id=%s severity=%s category=%s",
            response.incident_id,
            severity,
            category,
            extra={
                "incident_id": response.incident_id,
                "severity": severity,
                "category": category,
                "workflow_path": workflow_path,
                "mocked_tool_executions": tool_execution_count,
            },
        )

    def build_metrics_response(
        self,
        settings: ConfigSettings,
    ) -> MetricsResponse:
        """
        Builds the JSON metrics response for GET /metrics.
        """

        with self._lock:
            uptime_seconds = self._calculate_uptime_seconds()

            if self._total_http_requests > 0:
                average_http_duration_ms = (
                    self._total_http_duration_ms / self._total_http_requests
                )
            else:
                average_http_duration_ms = 0.0

            route_metrics = self._build_route_metrics_locked()

            workflow_metrics = AgentWorkflowMetrics(
                total_incidents_processed=self._total_incidents_processed,
                incidents_by_severity=dict(self._incidents_by_severity),
                incidents_by_category=dict(self._incidents_by_category),
                workflow_path_counts=dict(self._workflow_path_counts),
                total_mocked_tool_executions=self._total_mocked_tool_executions,
            )

            response = MetricsResponse(
                app_name=settings.app_name,
                version=settings.app_version,
                uptime_seconds=round(uptime_seconds, 2),
                total_http_requests=self._total_http_requests,
                total_http_errors=self._total_http_errors,
                average_http_duration_ms=round(average_http_duration_ms, 2),
                routes=route_metrics,
                workflow_metrics=workflow_metrics,
            )

        return response

    def build_prometheus_metrics(
        self,
        settings: ConfigSettings,
    ) -> str:
        """
        Builds a lightweight Prometheus-style text response.

        This is useful for demos and Kubernetes/OpenShift observability.
        """

        metrics_response = self.build_metrics_response(settings=settings)
        lines: list[str] = []

        lines.append("# HELP incidentiq_uptime_seconds Application uptime in seconds.")
        lines.append("# TYPE incidentiq_uptime_seconds gauge")
        lines.append(f"incidentiq_uptime_seconds {metrics_response.uptime_seconds}")

        lines.append("# HELP incidentiq_http_requests_total Total HTTP requests.")
        lines.append("# TYPE incidentiq_http_requests_total counter")
        lines.append(
            f"incidentiq_http_requests_total {metrics_response.total_http_requests}"
        )

        lines.append("# HELP incidentiq_http_errors_total Total HTTP errors.")
        lines.append("# TYPE incidentiq_http_errors_total counter")
        lines.append(
            f"incidentiq_http_errors_total {metrics_response.total_http_errors}"
        )

        lines.append(
            "# HELP incidentiq_incidents_processed_total Total processed incidents."
        )
        lines.append("# TYPE incidentiq_incidents_processed_total counter")
        lines.append(
            "incidentiq_incidents_processed_total "
            f"{metrics_response.workflow_metrics.total_incidents_processed}"
        )

        lines.append(
            "# HELP incidentiq_mocked_tool_executions_total Total mocked tool executions."
        )
        lines.append("# TYPE incidentiq_mocked_tool_executions_total counter")
        lines.append(
            "incidentiq_mocked_tool_executions_total "
            f"{metrics_response.workflow_metrics.total_mocked_tool_executions}"
        )

        for route in metrics_response.routes:
            method_label = self._escape_label_value(route.method)
            path_label = self._escape_label_value(route.path)

            lines.append(
                "incidentiq_route_requests_total"
                f'{{method="{method_label}",path="{path_label}"}} {route.count}'
            )

            lines.append(
                "incidentiq_route_errors_total"
                f'{{method="{method_label}",path="{path_label}"}} {route.error_count}'
            )

            lines.append(
                "incidentiq_route_average_duration_ms"
                f'{{method="{method_label}",path="{path_label}"}} '
                f"{route.average_duration_ms}"
            )

        for (
            severity,
            count,
        ) in metrics_response.workflow_metrics.incidents_by_severity.items():
            severity_label = self._escape_label_value(severity)
            lines.append(
                "incidentiq_incidents_by_severity_total"
                f'{{severity="{severity_label}"}} {count}'
            )

        for (
            category,
            count,
        ) in metrics_response.workflow_metrics.incidents_by_category.items():
            category_label = self._escape_label_value(category)
            lines.append(
                "incidentiq_incidents_by_category_total"
                f'{{category="{category_label}"}} {count}'
            )

        metrics_text = "\n".join(lines)
        metrics_text = f"{metrics_text}\n"

        return metrics_text

    def reset(self) -> None:
        """
        Resets all metrics.

        This is useful for tests.
        """

        with self._lock:
            self._started_at = datetime.now(timezone.utc)
            self._total_http_requests = 0
            self._total_http_errors = 0
            self._total_http_duration_ms = 0.0
            self._route_counters.clear()
            self._total_incidents_processed = 0
            self._incidents_by_severity.clear()
            self._incidents_by_category.clear()
            self._workflow_path_counts.clear()
            self._total_mocked_tool_executions = 0

    def _build_route_metrics_locked(self) -> list[HTTPRouteMetric]:
        """
        Builds route metrics.

        This method must be called while holding self._lock.
        """

        route_metrics: list[HTTPRouteMetric] = []

        for route_key in sorted(self._route_counters.keys()):
            counter = self._route_counters[route_key]

            if counter.count > 0:
                average_duration_ms = counter.total_duration_ms / counter.count
            else:
                average_duration_ms = 0.0

            route_metric = HTTPRouteMetric(
                method=counter.method,
                path=counter.path,
                count=counter.count,
                error_count=counter.error_count,
                average_duration_ms=round(average_duration_ms, 2),
            )

            route_metrics.append(route_metric)

        return route_metrics

    def _calculate_uptime_seconds(self) -> float:
        """
        Calculates app uptime in seconds.

        This method must be called while holding self._lock.
        """

        current_time = datetime.now(timezone.utc)
        uptime = current_time - self._started_at

        return uptime.total_seconds()

    def _increment_counter(
        self,
        counters: dict[str, int],
        key: str,
    ) -> None:
        """
        Increments a named counter dictionary.
        """

        current_value = counters.get(key)

        if current_value is None:
            counters[key] = 1
        else:
            counters[key] = current_value + 1

    def _normalize_path(
        self,
        path: str,
    ) -> str:
        """
        Normalizes dynamic routes so metrics do not create one entry per ID.
        """

        if path.startswith("/incidents/"):
            return "/incidents/{incident_id}"

        return path

    def _escape_label_value(
        self,
        value: str,
    ) -> str:
        """
        Escapes label values for Prometheus-style text output.
        """

        escaped_value = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        escaped_value = escaped_value.replace("\n", "\\n")

        return escaped_value


application_metrics = ApplicationMetrics()
