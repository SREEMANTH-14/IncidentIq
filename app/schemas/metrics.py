from pydantic import BaseModel, ConfigDict, Field


class HTTPRouteMetric(BaseModel):
    """
    HTTPRouteMetric represents request statistics for one API route.
    """

    model_config = ConfigDict(extra="forbid")

    method: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    average_duration_ms: float = Field(..., ge=0)


class AgentWorkflowMetrics(BaseModel):
    """
    AgentWorkflowMetrics represents IncidentIQ workflow-level metrics.
    """

    model_config = ConfigDict(extra="forbid")

    total_incidents_processed: int = Field(..., ge=0)
    incidents_by_severity: dict[str, int] = Field(default_factory=dict)
    incidents_by_category: dict[str, int] = Field(default_factory=dict)
    workflow_path_counts: dict[str, int] = Field(default_factory=dict)
    total_mocked_tool_executions: int = Field(..., ge=0)


class MetricsResponse(BaseModel):
    """
    MetricsResponse is returned by GET /metrics.
    """

    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    uptime_seconds: float = Field(..., ge=0)
    total_http_requests: int = Field(..., ge=0)
    total_http_errors: int = Field(..., ge=0)
    average_http_duration_ms: float = Field(..., ge=0)
    routes: list[HTTPRouteMetric] = Field(default_factory=list)
    workflow_metrics: AgentWorkflowMetrics
