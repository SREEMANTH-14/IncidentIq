from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncidentPayload(BaseModel):
    """
    IncidentPayload represents the incoming production incident sent to
    the IncidentIQ POST /process endpoint. FastAPI validates this model
    before sending the incident to the Orchestrator and Triage Agent.
    """

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique incident identifier.",
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Short incident title.",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed incident description including errors, symptoms, and impact.",
    )
    service: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Affected service name.",
    )
    environment: str = Field(
        default="production",
        min_length=2,
        max_length=50,
        description="Affected environment.",
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional incident metrics such as error rate, latency, CPU, memory, or DB usage.",
    )

    @field_validator("incident_id", "title", "description", "service", "environment")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """
        Ensures important text fields are not empty or only spaces.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Value cannot be empty.")

        return cleaned_value

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        """
        Normalizes environment values so downstream agents receive consistent text.
        """

        cleaned_value = value.strip().lower()
        return cleaned_value
