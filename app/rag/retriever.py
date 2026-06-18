import argparse
import logging
from typing import Any

from app.core.config import ConfigSettings, get_settings
from app.rag.vector_store import IncidentIQVectorStore
from app.schemas.agent_messages import KnowledgeSource

logger = logging.getLogger("IncidentIQ.RAG.Retriever")


class IncidentIQRetriever:
    """
    IncidentIQRetriever searches the ChromaDB knowledge base.

    It is used by the Knowledge Agent to retrieve:
    - DevOps runbooks
    - Similar historical incidents

    The returned records are converted into KnowledgeSource contracts so that
    A2A communication remains strongly typed and validated.
    """

    def __init__(
        self,
        settings: ConfigSettings | None = None,
        vector_store: IncidentIQVectorStore | None = None,
    ) -> None:
        """
        Initializes the retriever.

        If a vector_store is not provided, the retriever creates one using
        the configured ChromaDB path and embedding model.
        """

        if settings is None:
            self.settings = get_settings()
        else:
            self.settings = settings

        if vector_store is None:
            self.vector_store = IncidentIQVectorStore(settings=self.settings)
        else:
            self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[KnowledgeSource]:
        """
        Retrieves relevant RAG sources for the given query.

        Steps:
        1. Validate query.
        2. Convert query to embedding.
        3. Search ChromaDB.
        4. Convert ChromaDB results into KnowledgeSource contracts.
        """

        cleaned_query = query.strip()

        if not cleaned_query:
            raise ValueError("RAG retrieval query cannot be empty.")

        if top_k is None:
            result_limit = self.settings.retrieval_top_k
        else:
            result_limit = top_k

        if result_limit <= 0:
            raise ValueError("top_k must be greater than zero.")

        collection_count = self.vector_store.get_collection_count()

        if collection_count == 0:
            logger.warning(
                "ChromaDB collection is empty. Run python -m app.rag.ingest first."
            )
            return []

        query_embeddings = self.vector_store.embed_texts([cleaned_query])

        if not query_embeddings:
            logger.warning("Unable to create embedding for query.")
            return []

        query_embedding = query_embeddings[0]
        collection = self.vector_store.get_collection()

        chroma_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=result_limit,
            include=["documents", "metadatas", "distances"],
        )

        knowledge_sources = self._convert_chroma_results_to_sources(
            chroma_results=chroma_results,
        )

        logger.info(
            "Retrieved %s sources for query=%s",
            len(knowledge_sources),
            cleaned_query,
        )

        return knowledge_sources

    def retrieve_for_incident(
        self,
        title: str,
        description: str,
        service: str,
        severity: str | None = None,
        category: str | None = None,
        entities: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[KnowledgeSource]:
        """
        Builds a rich incident search query and retrieves relevant sources.

        The Knowledge Agent will use this method because it can combine:
        - incident title
        - description
        - affected service
        - Triage Agent severity
        - Triage Agent category
        - extracted entities
        """

        query = self.build_incident_query(
            title=title,
            description=description,
            service=service,
            severity=severity,
            category=category,
            entities=entities,
        )

        sources = self.retrieve(
            query=query,
            top_k=top_k,
        )

        return sources

    def build_incident_query(
        self,
        title: str,
        description: str,
        service: str,
        severity: str | None = None,
        category: str | None = None,
        entities: list[str] | None = None,
    ) -> str:
        """
        Builds a searchable RAG query from incident and triage information.

        A richer query improves retrieval quality.
        """

        query_parts: list[str] = []

        cleaned_title = title.strip()
        cleaned_description = description.strip()
        cleaned_service = service.strip()

        if cleaned_title:
            query_parts.append(f"Incident title: {cleaned_title}")

        if cleaned_description:
            query_parts.append(f"Description: {cleaned_description}")

        if cleaned_service:
            query_parts.append(f"Affected service: {cleaned_service}")

        if severity is not None:
            cleaned_severity = severity.strip()

            if cleaned_severity:
                query_parts.append(f"Severity: {cleaned_severity}")

        if category is not None:
            cleaned_category = category.strip()

            if cleaned_category:
                query_parts.append(f"Category: {cleaned_category}")

        if entities is not None:
            cleaned_entities: list[str] = []

            for entity in entities:
                cleaned_entity = entity.strip()

                if cleaned_entity:
                    cleaned_entities.append(cleaned_entity)

            if cleaned_entities:
                joined_entities = ", ".join(cleaned_entities)
                query_parts.append(f"Extracted entities: {joined_entities}")

        query = "\n".join(query_parts)

        if not query.strip():
            raise ValueError("Unable to build incident retrieval query.")

        return query

    def _convert_chroma_results_to_sources(
        self,
        chroma_results: dict[str, Any],
    ) -> list[KnowledgeSource]:
        """
        Converts ChromaDB query results into KnowledgeSource contracts.

        ChromaDB returns nested lists because each query can have multiple
        result sets. We send one query at a time, so we read index 0.
        """

        documents_nested = chroma_results.get("documents")
        metadatas_nested = chroma_results.get("metadatas")
        distances_nested = chroma_results.get("distances")
        ids_nested = chroma_results.get("ids")

        if not documents_nested:
            return []

        documents = documents_nested[0]

        metadatas: list[Any] = []
        distances: list[Any] = []
        result_ids: list[Any] = []

        if metadatas_nested:
            metadatas = metadatas_nested[0]

        if distances_nested:
            distances = distances_nested[0]

        if ids_nested:
            result_ids = ids_nested[0]

        knowledge_sources: list[KnowledgeSource] = []

        for index, document_content in enumerate(documents):
            if document_content is None:
                continue

            cleaned_content = str(document_content).strip()

            if not cleaned_content:
                continue

            metadata = self._get_metadata_at_index(
                metadatas=metadatas,
                index=index,
            )

            result_id = self._get_result_id_at_index(
                result_ids=result_ids,
                index=index,
            )

            distance = self._get_distance_at_index(
                distances=distances,
                index=index,
            )

            enriched_metadata = self._build_enriched_metadata(
                metadata=metadata,
                distance=distance,
            )

            source_id = self._get_metadata_value(
                metadata=enriched_metadata,
                key="source_id",
                fallback=result_id,
            )

            source_type = self._get_metadata_value(
                metadata=enriched_metadata,
                key="source_type",
                fallback="unknown",
            )

            title = self._get_metadata_value(
                metadata=enriched_metadata,
                key="title",
                fallback=source_id,
            )

            knowledge_source = KnowledgeSource(
                source_id=source_id,
                source_type=source_type,
                title=title,
                content=cleaned_content,
                metadata=enriched_metadata,
            )

            knowledge_sources.append(knowledge_source)

        return knowledge_sources

    def _get_metadata_at_index(
        self,
        metadatas: list[Any],
        index: int,
    ) -> dict[str, str]:
        """
        Safely reads metadata from a ChromaDB result index.
        """

        if index >= len(metadatas):
            return {}

        raw_metadata = metadatas[index]

        if raw_metadata is None:
            return {}

        metadata: dict[str, str] = {}

        if isinstance(raw_metadata, dict):
            for key, value in raw_metadata.items():
                if value is None:
                    continue

                metadata[str(key)] = str(value)

        return metadata

    def _get_result_id_at_index(
        self,
        result_ids: list[Any],
        index: int,
    ) -> str:
        """
        Safely reads the ChromaDB result ID for a result index.
        """

        fallback_result_id = f"retrieved-source-{index + 1}"

        if index >= len(result_ids):
            return fallback_result_id

        raw_result_id = result_ids[index]

        if raw_result_id is None:
            return fallback_result_id

        result_id = str(raw_result_id).strip()

        if not result_id:
            return fallback_result_id

        return result_id

    def _get_distance_at_index(
        self,
        distances: list[Any],
        index: int,
    ) -> float | None:
        """
        Safely reads vector distance from ChromaDB result index.
        """

        if index >= len(distances):
            return None

        raw_distance = distances[index]

        if raw_distance is None:
            return None

        try:
            distance = float(raw_distance)
        except (TypeError, ValueError):
            return None

        return distance

    def _build_enriched_metadata(
        self,
        metadata: dict[str, str],
        distance: float | None,
    ) -> dict[str, str]:
        """
        Adds retrieval score details into metadata.

        ChromaDB cosine distance is lower when results are more similar.
        For readability, we also add an approximate relevance score.
        """

        enriched_metadata: dict[str, str] = {}

        for key, value in metadata.items():
            enriched_metadata[key] = value

        if distance is not None:
            relevance_score = self._convert_distance_to_relevance_score(distance)

            enriched_metadata["distance"] = f"{distance:.4f}"
            enriched_metadata["relevance_score"] = f"{relevance_score:.4f}"

        return enriched_metadata

    def _convert_distance_to_relevance_score(self, distance: float) -> float:
        """
        Converts cosine distance into an approximate 0-to-1 relevance score.

        This is used only for display and debugging.
        """

        relevance_score = 1.0 - distance

        if relevance_score < 0.0:
            relevance_score = 0.0

        if relevance_score > 1.0:
            relevance_score = 1.0

        return relevance_score

    def _get_metadata_value(
        self,
        metadata: dict[str, str],
        key: str,
        fallback: str,
    ) -> str:
        """
        Reads a metadata value safely and falls back when missing.
        """

        raw_value = metadata.get(key)

        if raw_value is None:
            return fallback

        value = str(raw_value).strip()

        if not value:
            return fallback

        return value


def configure_retriever_logging() -> None:
    """
    Configures readable logging for command-line retriever testing.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for retriever testing.

    Example:
    python -m app.rag.retriever "database connection pool exhausted"
    """

    parser = argparse.ArgumentParser(
        description="Search IncidentIQ ChromaDB RAG knowledge base."
    )

    parser.add_argument(
        "query",
        nargs="+",
        help="Search query for IncidentIQ RAG retrieval.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Number of sources to retrieve.",
    )

    arguments = parser.parse_args()
    return arguments


def main() -> None:
    """
    Command-line entry point for testing the RAG retriever.
    """

    configure_retriever_logging()

    arguments = parse_arguments()
    query = " ".join(arguments.query)

    retriever = IncidentIQRetriever()
    sources = retriever.retrieve(
        query=query,
        top_k=arguments.top_k,
    )

    if not sources:
        logger.info("No sources retrieved.")
        return

    for source in sources:
        preview = source.content[:300].replace("\n", " ")

        logger.info(
            "Retrieved source_id=%s source_type=%s title=%s metadata=%s",
            source.source_id,
            source.source_type,
            source.title,
            source.metadata,
        )
        logger.info("Content preview: %s", preview)


if __name__ == "__main__":
    main()
