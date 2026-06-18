from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentName(str, Enum):
    """
    AgentName keeps the official agent role names from the IncidentIQ use case.

    These values match the assessment document's Use Case 1 agent names.
    """

    ORCHESTRATOR = "Orchestrator"
    TRIAGE_AGENT = "Triage Agent"
    KNOWLEDGE_AGENT = "Knowledge Agent"
    REMEDIATION_AGENT = "Remediation Agent"
    NOTIFIER_AGENT = "Notifier Agent"


class IncidentSeverity(str, Enum):
    """
    IncidentSeverity represents the P1-P4 severity classification required
    by the Triage Agent.
    """

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentCategory(str, Enum):
    """
    IncidentCategory represents the incident category extracted by the
    Triage Agent.
    """

    DATABASE = "database"
    NETWORK = "network"
    APPLICATION = "application"
    INFRA = "infra"
    UNKNOWN = "unknown"


class ToolExecutionStatus(str, Enum):
    """
    ToolExecutionStatus represents the result of a mocked DevOps tool call.
    """

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentExecutionStatus(str, Enum):
    """
    AgentExecutionStatus represents whether an agent completed successfully.
    """

    SUCCESS = "success"
    FAILED = "failed"


class TriageResult(BaseModel):
    """
    TriageResult is the structured output from the Triage Agent.

    This model is also the best place to use LangChain's
    .with_structured_output() later because it has clear fields:
    severity, category, entities, and reasoning_summary.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName = Field(
        default=AgentName.TRIAGE_AGENT,
        description="Name of the agent producing this contract.",
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Classified incident severity. Must be P1, P2, P3, or P4.",
    )
    category: IncidentCategory = Field(
        ...,
        description="Classified incident category.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Extracted entities such as service name, pod name, error code, namespace, or metric.",
    )
    reasoning_summary: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Short explanation for severity and category classification.",
    )

    @field_validator("entities")
    @classmethod
    def clean_entities(cls, values: list[str]) -> list[str]:
        """
        Removes empty entity values and keeps entity names clean.
        """

        cleaned_entities: list[str] = []

        for value in values:
            cleaned_value = value.strip()

            if cleaned_value:
                cleaned_entities.append(cleaned_value)

        return cleaned_entities

    @field_validator("reasoning_summary")
    @classmethod
    def validate_reasoning_summary(cls, value: str) -> str:
        """
        Ensures the triage reasoning is not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("reasoning_summary cannot be empty.")

        return cleaned_value


class KnowledgeSource(BaseModel):
    """
    KnowledgeSource represents one retrieved RAG document chunk.

    The Knowledge Agent will return a list of these sources after searching
    ChromaDB over runbooks and historical incidents.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(
        ...,
        min_length=1,
        description="Unique source identifier from the vector store.",
    )
    source_type: str = Field(
        ...,
        min_length=1,
        description="Type of source.",
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Human-readable source title.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Retrieved source content used for grounding.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Source metadata such as file path, category, or severity.",
    )

    @field_validator("source_id", "source_type", "title", "content")
    @classmethod
    def validate_source_text(cls, value: str) -> str:
        """
        Ensures retrieved source fields are clean and useful.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("KnowledgeSource text field cannot be empty.")

        return cleaned_value


class KnowledgeResult(BaseModel):
    """
    KnowledgeResult is the A2A output contract from the Knowledge Agent.

    It carries RAG retrieval results from runbooks and historical incidents
    to the Remediation Agent and Notifier Agent.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName = Field(
        default=AgentName.KNOWLEDGE_AGENT,
        description="Name of the agent producing this contract.",
    )
    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Search query used for RAG retrieval.",
    )
    sources: list[KnowledgeSource] = Field(
        default_factory=list,
        description="Retrieved runbook and historical incident sources.",
    )
    grounded_summary: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Short summary grounded in retrieved sources.",
    )

    @field_validator("query", "grounded_summary")
    @classmethod
    def validate_knowledge_text(cls, value: str) -> str:
        """
        Ensures knowledge result text fields are not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("KnowledgeResult text field cannot be empty.")

        return cleaned_value


class RemediationStep(BaseModel):
    """
    RemediationStep represents one recommended fix step.

    The Remediation Agent creates these steps based on the incident,
    Triage Result, and Knowledge Result.
    """

    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(
        ...,
        ge=1,
        description="Step number in the remediation plan.",
    )
    action: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Recommended remediation action.",
    )
    is_safe_to_automate: bool = Field(
        default=False,
        description="Whether this action is safe for mocked automation.",
    )
    tool_name: str | None = Field(
        default=None,
        description="Mocked DevOps tool name if automation is possible.",
    )

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        """
        Ensures remediation action text is useful.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Remediation action cannot be empty.")

        return cleaned_value

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, value: str | None) -> str | None:
        """
        Cleans optional tool name when a remediation step maps to a mocked tool.
        """

        if value is None:
            return value

        cleaned_value = value.strip()

        if not cleaned_value:
            return None

        return cleaned_value


class ToolExecutionResult(BaseModel):
    """
    ToolExecutionResult represents the result of a mocked DevOps tool invocation.

    These results prove that the Remediation Agent can invoke tools/functions.
    """

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the mocked DevOps tool.",
    )
    status: ToolExecutionStatus = Field(
        ...,
        description="Tool execution status.",
    )
    message: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Human-readable tool execution result.",
    )
    output: dict[str, str] = Field(
        default_factory=dict,
        description="Structured mocked tool output.",
    )

    @field_validator("tool_name", "message")
    @classmethod
    def validate_tool_text(cls, value: str) -> str:
        """
        Ensures tool result text fields are clean.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("ToolExecutionResult text field cannot be empty.")

        return cleaned_value


class RemediationPlan(BaseModel):
    """
    RemediationPlan is the A2A output contract from the Remediation Agent.

    It contains suggested remediation steps and any mocked DevOps tool calls
    performed for safe actions.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName = Field(
        default=AgentName.REMEDIATION_AGENT,
        description="Name of the agent producing this contract.",
    )
    summary: str = Field(
        ...,
        min_length=5,
        max_length=1500,
        description="Short summary of the remediation strategy.",
    )
    steps: list[RemediationStep] = Field(
        default_factory=list,
        description="Ordered remediation steps.",
    )
    tools_executed: list[ToolExecutionResult] = Field(
        default_factory=list,
        description="Mocked DevOps tool calls executed by the Remediation Agent.",
    )
    requires_human_approval: bool = Field(
        default=False,
        description="Whether risky actions require human approval.",
    )

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        """
        Ensures remediation plan summary is not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Remediation summary cannot be empty.")

        return cleaned_value


class NotificationMessage(BaseModel):
    """
    NotificationMessage is the final A2A contract from the Notifier Agent.

    It formats the incident response into a Slack/email-ready message.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName = Field(
        default=AgentName.NOTIFIER_AGENT,
        description="Name of the agent producing this contract.",
    )
    subject: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Slack/email-ready notification subject.",
    )
    body: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Slack/email-ready notification body.",
    )
    recommended_channel: str = Field(
        default="slack",
        min_length=3,
        max_length=50,
        description="Recommended notification channel. Example: slack or email.",
    )

    @field_validator("subject", "body", "recommended_channel")
    @classmethod
    def validate_notification_text(cls, value: str) -> str:
        """
        Ensures notification message fields are clean.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("NotificationMessage text field cannot be empty.")

        return cleaned_value


class AgentError(BaseModel):
    """
    AgentError is used when an agent fails and the system needs to return
    a structured error instead of an unhandled exception.
    """

    model_config = ConfigDict(extra="forbid")

    agent_name: AgentName = Field(
        ...,
        description="Agent where the error occurred.",
    )
    status: AgentExecutionStatus = Field(
        default=AgentExecutionStatus.FAILED,
        description="Agent execution status.",
    )
    error_message: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Readable error message.",
    )

    @field_validator("error_message")
    @classmethod
    def validate_error_message(cls, value: str) -> str:
        """
        Ensures agent error messages are useful.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("error_message cannot be empty.")

        return cleaned_value
