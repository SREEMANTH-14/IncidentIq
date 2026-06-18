import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import ConfigSettings, get_settings
from app.rag.chunker import SourceDocument, create_chunks_from_documents
from app.rag.vector_store import IncidentIQVectorStore

logger = logging.getLogger("IncidentIQ.RAG.Ingest")


def configure_ingestion_logging() -> None:
    """
    Configures basic logging for command-line ingestion.

    Later, the FastAPI app will use structured JSON logging.
    For this ingestion script, simple readable logs are enough.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def read_text_file(file_path: Path) -> str:
    """
    Reads a UTF-8 text file.
    """

    with file_path.open("r", encoding="utf-8") as file:
        content = file.read()

    return content


def extract_markdown_title(content: str, fallback_title: str) -> str:
    """
    Extracts the first markdown H1 title.

    If no H1 title is found, it uses the fallback title.
    """

    lines = content.splitlines()

    for line in lines:
        cleaned_line = line.strip()

        if cleaned_line.startswith("# "):
            title = cleaned_line.replace("# ", "", 1).strip()

            if title:
                return title

    return fallback_title


def load_runbook_documents(runbook_data_directory: Path) -> list[SourceDocument]:
    """
    Loads markdown runbooks from data/runbooks.

    Each runbook becomes one SourceDocument before chunking.
    """

    documents: list[SourceDocument] = []

    if not runbook_data_directory.exists():
        logger.warning("Runbook directory does not exist: %s", runbook_data_directory)
        return documents

    markdown_files = sorted(runbook_data_directory.glob("*.md"))

    for file_path in markdown_files:
        content = read_text_file(file_path)

        fallback_title = file_path.stem.replace("_", " ").title()
        title = extract_markdown_title(
            content=content,
            fallback_title=fallback_title,
        )

        source_id = f"runbook-{file_path.stem}"

        metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path),
            "source_type": "runbook",
        }

        document = SourceDocument(
            source_id=source_id,
            source_type="runbook",
            title=title,
            content=content,
            metadata=metadata,
        )

        documents.append(document)

    logger.info("Loaded %s runbook documents.", len(documents))

    return documents


def get_required_string(
    record: dict[str, Any],
    field_name: str,
    record_index: int,
) -> str:
    """
    Reads a required string field from an incident record.

    This avoids silently ingesting invalid historical incident data.
    """

    raw_value = record.get(field_name)

    if raw_value is None:
        raise ValueError(
            f"Missing field '{field_name}' in incident record index {record_index}."
        )

    value = str(raw_value).strip()

    if not value:
        raise ValueError(
            f"Empty field '{field_name}' in incident record index {record_index}."
        )

    return value


def format_historical_incident_content(
    incident: dict[str, Any], record_index: int
) -> str:
    """
    Converts one historical incident JSON object into searchable text.

    This format helps the RAG system retrieve by title, severity, category,
    description, and resolution.
    """

    incident_id = get_required_string(incident, "id", record_index)
    title = get_required_string(incident, "title", record_index)
    description = get_required_string(incident, "description", record_index)
    severity = get_required_string(incident, "severity", record_index)
    category = get_required_string(incident, "category", record_index)
    resolution = get_required_string(incident, "resolution", record_index)
    resolved_at = get_required_string(incident, "resolved_at", record_index)

    content_parts = [
        f"# Historical Incident {incident_id}: {title}",
        "",
        f"Incident ID: {incident_id}",
        f"Severity: {severity}",
        f"Category: {category}",
        f"Resolved At: {resolved_at}",
        "",
        "## Description",
        description,
        "",
        "## Resolution",
        resolution,
    ]

    content = "\n".join(content_parts)
    return content


def load_historical_incident_documents(
    incident_data_file_path: Path,
) -> list[SourceDocument]:
    """
    Loads historical incident records from data/incidents/incidents.json.

    Each incident becomes one SourceDocument before chunking.
    """

    documents: list[SourceDocument] = []

    if not incident_data_file_path.exists():
        logger.warning("Incident data file does not exist: %s", incident_data_file_path)
        return documents

    with incident_data_file_path.open("r", encoding="utf-8") as file:
        incident_records = json.load(file)

    if not isinstance(incident_records, list):
        raise ValueError("Incident data file must contain a JSON array.")

    for index, incident in enumerate(incident_records):
        if not isinstance(incident, dict):
            raise ValueError(f"Incident record index {index} must be a JSON object.")

        incident_id = get_required_string(incident, "id", index)
        title = get_required_string(incident, "title", index)
        severity = get_required_string(incident, "severity", index)
        category = get_required_string(incident, "category", index)
        resolved_at = get_required_string(incident, "resolved_at", index)

        content = format_historical_incident_content(
            incident=incident,
            record_index=index,
        )

        metadata = {
            "incident_id": incident_id,
            "severity": severity,
            "category": category,
            "resolved_at": resolved_at,
            "source_type": "historical_incident",
        }

        document = SourceDocument(
            source_id=incident_id,
            source_type="historical_incident",
            title=title,
            content=content,
            metadata=metadata,
        )

        documents.append(document)

    logger.info("Loaded %s historical incident documents.", len(documents))

    return documents


def load_source_documents(settings: ConfigSettings) -> list[SourceDocument]:
    """
    Loads all IncidentIQ RAG source documents.

    Sources:
    - Historical incidents from incidents.json
    - DevOps runbooks from markdown files
    """

    incident_data_file_path = settings.get_incident_data_file_path()
    runbook_data_directory = settings.get_runbook_data_directory()

    historical_incident_documents = load_historical_incident_documents(
        incident_data_file_path=incident_data_file_path,
    )

    runbook_documents = load_runbook_documents(
        runbook_data_directory=runbook_data_directory,
    )

    documents: list[SourceDocument] = []
    documents.extend(historical_incident_documents)
    documents.extend(runbook_documents)

    logger.info("Total source documents loaded: %s", len(documents))

    return documents


def ingest_knowledge_base(reset_collection: bool = True) -> int:
    """
    Ingests IncidentIQ source documents into ChromaDB.

    Steps:
    1. Load source documents.
    2. Split documents into chunks.
    3. Generate embeddings.
    4. Store chunks in persistent ChromaDB.
    """

    settings = get_settings()
    settings.create_required_directories()

    source_documents = load_source_documents(settings=settings)

    if not source_documents:
        logger.warning("No source documents found for ingestion.")
        return 0

    rag_chunks = create_chunks_from_documents(
        documents=source_documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    vector_store = IncidentIQVectorStore(settings=settings)

    if reset_collection:
        vector_store.reset_collection()

    stored_count = vector_store.add_chunks(rag_chunks)

    logger.info("IncidentIQ RAG ingestion completed.")
    logger.info("Stored chunk count: %s", stored_count)
    logger.info("ChromaDB collection count: %s", vector_store.get_collection_count())

    return stored_count


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for ingestion.

    By default, ingestion resets the ChromaDB collection.
    Use --no-reset when you do not want to delete existing records.
    """

    parser = argparse.ArgumentParser(
        description="Ingest IncidentIQ RAG data into ChromaDB."
    )

    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not reset ChromaDB collection before ingestion.",
    )

    arguments = parser.parse_args()
    return arguments


def main() -> None:
    """
    Command-line entry point for RAG ingestion.
    """

    configure_ingestion_logging()

    arguments = parse_arguments()

    reset_collection = True

    if arguments.no_reset:
        reset_collection = False

    stored_count = ingest_knowledge_base(reset_collection=reset_collection)

    logger.info("RAG ingestion command completed with %s stored chunks.", stored_count)


if __name__ == "__main__":
    main()
