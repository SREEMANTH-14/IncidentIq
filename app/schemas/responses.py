from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.agent_messages import (
    KnowledgeResult,
    NotificationMessage,
    RemediationPlan,
    TriageResult,
)


class HealthResponse(BaseModel):
    """
    HealthResponse is returned by GET /health.

    """

    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        default="healthy",
        description="Application health status.",
    )
    app_name: str = Field(
        default="IncidentIQ",
        description="Application name.",
    )
    version: str = Field(
        default="1.0.0",
        description="Application version.",
    )


class IncidentProcessResponse(BaseModel):
    """
    IncidentProcessResponse is returned by POST /process.

    It combines all important A2A outputs from the IncidentIQ agent workflow.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str = Field(
        ...,
        min_length=8,
        description="Unique trace ID for request logging and debugging.",
    )
    incident_id: str = Field(
        ...,
        min_length=3,
        description="Unique incident identifier.",
    )
    triage_result: TriageResult = Field(
        ...,
        description="Structured output from the Triage Agent.",
    )
    knowledge_result: KnowledgeResult | None = Field(
        default=None,
        description="RAG output from the Knowledge Agent.",
    )
    remediation_plan: RemediationPlan | None = Field(
        default=None,
        description="Output from the Remediation Agent.",
    )
    notification_message: NotificationMessage = Field(
        ...,
        description="Slack/email-ready response from the Notifier Agent.",
    )
    workflow_path: list[str] = Field(
        default_factory=list,
        description="Ordered list of agents executed by LangGraph.",
    )

    @field_validator("trace_id", "incident_id")
    @classmethod
    def validate_response_text(cls, value: str) -> str:
        """
        Ensures response identifiers are clean.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Response identifier cannot be empty.")

        return cleaned_value


class IncidentResourceResponse(BaseModel):
    """
    IncidentResourceResponse is returned by GET /incidents/{incident_id}.

    """

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(
        ...,
        min_length=3,
        description="Unique incident identifier.",
    )
    response: IncidentProcessResponse = Field(
        ...,
        description="Stored incident processing response.",
    )


class ErrorResponse(BaseModel):
    """
    ErrorResponse provides a consistent error format for API failures.
    """

    model_config = ConfigDict(extra="forbid")

    trace_id: str | None = Field(
        default=None,
        description="Trace ID for debugging, if available.",
    )
    error_code: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Machine-readable error code.",
    )
    message: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Human-readable error message.",
    )

    @field_validator("error_code", "message")
    @classmethod
    def validate_error_text(cls, value: str) -> str:
        """
        Ensures API error fields are clean.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("ErrorResponse text field cannot be empty.")

        return cleaned_value
