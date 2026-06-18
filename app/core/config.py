from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigSettings(BaseSettings):
    """
    ConfigSettings loads all IncidentIQ settings from environment variables.

    The values are loaded from:
    1. Actual environment variables
    2. The local .env file

    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------
    # IncidentIQ Application Settings
    # ---------------------------------------------------------

    app_name: str = Field(
        default="IncidentIQ",
        description="Application name.",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version.",
    )
    app_env: str = Field(
        default="local",
        description="Application environment such as local, docker, test, or production.",
    )
    debug: bool = Field(
        default=True,
        description="Enables debug mode for local development.",
    )

    # ---------------------------------------------------------
    # API Settings
    # ---------------------------------------------------------

    api_host: str = Field(
        default="0.0.0.0",
        description="FastAPI host.",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="FastAPI port.",
    )

    # ---------------------------------------------------------
    # LLM Settings
    # ---------------------------------------------------------

    llm_provider: str = Field(
        default="mock",
        description="LLM provider. Supported values: mock, ollama.",
    )
    mock_llm: bool = Field(
        default=True,
        description="When true, deterministic mock LLM responses are used.",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama server.",
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Ollama model name used for local LLM inference.",
    )

    # ---------------------------------------------------------
    # RAG / ChromaDB Settings
    # ---------------------------------------------------------

    chroma_persist_dir: str = Field(
        default="storage/chroma",
        description="Persistent ChromaDB directory.",
    )
    chroma_collection_name: str = Field(
        default="incidentiq_knowledge_base",
        description="ChromaDB collection name for IncidentIQ RAG data.",
    )
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="SentenceTransformer embedding model name.",
    )

    # ---------------------------------------------------------
    # RAG Chunking Settings
    # ---------------------------------------------------------

    chunk_size: int = Field(
        default=800,
        ge=100,
        le=5000,
        description="Maximum character size of each RAG chunk.",
    )
    chunk_overlap: int = Field(
        default=120,
        ge=0,
        le=1000,
        description="Character overlap between RAG chunks.",
    )
    retrieval_top_k: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of top RAG chunks to retrieve.",
    )

    # ---------------------------------------------------------
    # Data Paths
    # ---------------------------------------------------------

    incident_data_path: str = Field(
        default="data/incidents/incidents.json",
        description="Path to generated historical incident JSON data.",
    )
    runbook_data_dir: str = Field(
        default="data/runbooks",
        description="Directory containing markdown runbooks.",
    )

    # ---------------------------------------------------------
    # Observability Settings
    # ---------------------------------------------------------

    enable_json_logs: bool = Field(
        default=True,
        description="Enables structured JSON logs.",
    )
    log_level: str = Field(
        default="INFO",
        description="Application logging level.",
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enables metrics endpoint.",
    )

    @field_validator("app_name", "app_version", "app_env")
    @classmethod
    def validate_app_text_fields(cls, value: str) -> str:
        """
        Ensures basic application text settings are not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Application setting cannot be empty.")

        return cleaned_value

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        """
        Ensures only supported LLM providers are used.

        For this project, we support:
        - mock
        - ollama

        """

        cleaned_value = value.strip().lower()

        allowed_providers = {"mock", "ollama"}

        if cleaned_value not in allowed_providers:
            raise ValueError("LLM_PROVIDER must be either 'mock' or 'ollama'.")

        return cleaned_value

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, value: str) -> str:
        """
        Ensures the Ollama base URL is not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("OLLAMA_BASE_URL cannot be empty.")

        return cleaned_value

    @field_validator("ollama_model")
    @classmethod
    def validate_ollama_model(cls, value: str) -> str:
        """
        Ensures the Ollama model name is not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("OLLAMA_MODEL cannot be empty.")

        return cleaned_value

    @field_validator(
        "chroma_persist_dir", "chroma_collection_name", "embedding_model_name"
    )
    @classmethod
    def validate_rag_text_fields(cls, value: str) -> str:
        """
        Ensures RAG and ChromaDB text settings are not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("RAG setting cannot be empty.")

        return cleaned_value

    @field_validator("incident_data_path", "runbook_data_dir")
    @classmethod
    def validate_data_paths(cls, value: str) -> str:
        """
        Ensures configured data paths are not empty.
        """

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Data path setting cannot be empty.")

        return cleaned_value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """
        Ensures log level is one of the commonly supported Python logging levels.
        """

        cleaned_value = value.strip().upper()

        allowed_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        if cleaned_value not in allowed_log_levels:
            raise ValueError(
                "LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
            )

        return cleaned_value

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "ConfigSettings":
        """
        Ensures chunk overlap is smaller than chunk size.

        This prevents invalid RAG chunking configuration.
        """

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

        return self

    def get_chroma_persist_path(self) -> Path:
        """
        Returns the ChromaDB persistent directory as a Path object.
        """

        return Path(self.chroma_persist_dir)

    def get_incident_data_file_path(self) -> Path:
        """
        Returns the historical incident JSON file path as a Path object.
        """

        return Path(self.incident_data_path)

    def get_runbook_data_directory(self) -> Path:
        """
        Returns the runbook data directory as a Path object.
        """

        return Path(self.runbook_data_dir)

    def create_required_directories(self) -> None:
        """
        Creates directories needed by IncidentIQ. 
        
        This method is called at application startup to ensure all necessary
        directories exist before the application starts processing incidents.
        """

        chroma_path = self.get_chroma_persist_path()
        runbook_path = self.get_runbook_data_directory()
        incident_file_path = self.get_incident_data_file_path()
        incident_directory = incident_file_path.parent

        chroma_path.mkdir(parents=True, exist_ok=True)
        runbook_path.mkdir(parents=True, exist_ok=True)
        incident_directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> ConfigSettings:
    """
    Returns a cached ConfigSettings instance.

    lru_cache prevents reading and parsing environment variables repeatedly.
    This is the recommended pattern for FastAPI configuration.
    """

    settings = ConfigSettings()
    return settings
